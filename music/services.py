import logging
import uuid as uuid_lib
from datetime import timedelta
from django.db.models import F
from django.utils import timezone
from music.models import (
    Genre,
    Song,
    Like, Rating,
    Comment,
    CommentLike,
    ListenHistory,
    Report,
)
from music.selectors import (
    get_genre_by_id,
    get_song_by_id,
    get_comment_by_id,
    get_report_by_id,
)
from music.exceptions import (
    NotSongOwner,
    SongAlreadyPublished,
    BlockedByArtist,
    GenreHasSongs,
    NotCommentOwner,
    InvalidParentComment,
)
from accounts.exceptions import (
    ValidationError,
    NotFound,
    PermissionDenied,
)
from accounts.selectors import is_blocked

logger = logging.getLogger(__name__)


#genre
#tạo thẻ loại mới
def create_genre(data: dict) -> Genre:
    from music.models import Genre as G

    if G.objects.filter(name__iexact=data['name']).exists():
        raise ValidationError(
            'Thể loại đã tồn tại',
            fields={
                'name': ['Tên thể loại này đã tồn tại']
            },
        )
    
    genre = G.objects.create(
        name=data['name'],
        description=data.get('description', ''),
    )
    logger.info('Genre created: %s', genre.name)
    return genre


#cập nhật thể loại
def update_genre(genre: Genre, data: dict) -> Genre:
    from music.models import Genre as G
    if G.objects.filter(name__iexact=data['name']).exclude(id=genre.id).exists():
        raise ValidationError(
            'Thể loại đã tồn tại',
            fields={
                'name': ['Tên thể loại này đã tồn tại'],
            },
        )
    
    genre.name = data['name']
    genre.description = data.get('description', genre.description)
    genre.slug = ''
    genre.save()
    return genre


#xoá thể loại, sẽ bị chặn nếu còn bài hát liên kết
def delete_genre(genre: Genre) -> dict:
    if genre.songs.exists():
        raise GenreHasSongs()
    genre.delete()



#SONG
#tạo bài hát mới và upload file lên Cloudinary
#file được Django storage tự xử lý khi gán vào FileField
#path pattern: audio/<artist_id>/<uuid>.<ext>
def create_song(artist, data: dict, files: dict) -> Song:
    genre = get_genre_by_id(data['genre_id'])
    song = Song(
        title = data['title'],
        artist = artist,
        genre = genre,
        lyrics = data.get('lyrics', ''),
        duration = data['duration'],
        allow_download = data.get('allow_download', False),
        released_at = data.get('released_at', None),
        status = Song.STATUS_DRAFT,
    )

    #gán file -> Django storage tự upload lên Cloudinary
    song.audio_file = files['audio_file']
    if 'cover_image' in files:
        song.cover_image = files['cover_image']

    song.save()
    logger.info('Song created: %s (artist=%s)', song.title, artist.username)

    return song

#cập nhật thông tin bào hát
def update_song(song: Song, artist, data: dict, files: dict) -> Song:
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()
    
    #cập nhật dữ liệu nếu có
    for field in ('title', 'lyrics', 'allow_download'):
        if field in data:
            setattr(song, field, data[field])

    if 'genre_id' in data:
        song.genre = get_genre_by_id(data['genre_id'])
    
    #xoá cover cũ trên cloudinary nếu có
    if 'cover_image' in files:
        if song.cover_image:
            try:
                song.cover_image.delete(save=False)
            except Exception:
                pass
        
        song.cover_image = files['cover_image']
    
    song.save()
    logger.info('Song updated: %s', song.title)
    return song


#xoá bài hát
def delete_song(song: Song, artist) -> None:
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()
    
    #xoá file
    try:
        if song.audio_file:
            song.audio_file.delete(save=False)
        if song.cover_image:
            song.cover_image.delete(save=False)
    except Exception as e:
        logger.warning('Failed to delete Cloudinary files for song %s: %s', song.id, e)

    song.delete()
    logger.info('Song deleted: %s', song.id)


#phát hành bài hát draft -> published
def publish_song(song: Song, artist) -> Song:
    from music.exceptions import NotSongOwner, SongAlreadyPublished, AdminHiddenSongCannotBePublished

    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()
    
    if song.hidden_by_admin:
        raise AdminHiddenSongCannotBePublished()
    
    if song.status not in [Song.STATUS_DRAFT, Song.STATUS_HIDDEN]:
        raise SongAlreadyPublished()
    
    song.status = Song.STATUS_PUBLISHED
    if not song.released_at:
        song.released_at = timezone.now()
    song.save()
    
    # Gửi thông báo cho người theo dõi
    from notifications.services import create_notification
    from notifications.models import Notification
    
    # Lấy danh sách người theo dõi
    followers = artist.followers.select_related('follower').all()
    for follow in followers:
        create_notification(
            recipient=follow.follower,
            notif_type=Notification.TYPE_NEW_SONG,
            message=f"{artist.get_display_name()} vừa ra mắt bài hát mới: {song.title}",
            sender=artist,
            target_type=Notification.TARGET_SONG,
            target_id=song.id
        )

    logger.info('Song published: %s', song.title)
    return song



#nghệ sĩ ẩn bài hát của mình
def hide_song(song: Song, artist) -> Song:
    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()
    song.status = Song.STATUS_HIDDEN
    song.save(update_fields=['status', 'updated_at'])
    return song


#admin ẩn bài hát vi phạm
def admin_hide_song(song: Song) -> Song:
    song.status = Song.STATUS_HIDDEN
    song.save(update_fields=['status', 'updated_at'])
    return song



#admin bật tắt bài hát vi phạm
def admin_toggle_trending(song: Song) -> Song:
    song.is_trending = not song.is_trending
    song.save(update_fields=['is_trending', 'updated_at'])
    return song



#PLAY, listenhistory
#ghi lượt nghe bằng cách
#atomic F() increment
#deup 5 phút
#return: play_count hiện tại (sau khi tăng hợp lệ)
def record_play(user, song: Song) -> int:
    user_is_auth = getattr(user, 'is_authenticated', False) and getattr(user, 'id', None)

    if user_is_auth:
        # Kiểm tra đã nghe trong 1 phút chưa để tránh tính trùng (rút ngắn để dễ test)
        cutoff = timezone.now() - timedelta(minutes=1)
        already_played = ListenHistory.objects.filter(
            user=user,
            song=song,
            listened_at__gte=cutoff,
        ).exists()

        if not already_played:
            Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)
            ListenHistory.objects.create(user=user, song=song)

            try:
                from social.services import create_friend_activity
                create_friend_activity(user=user, activity_type='playing', song=song)
            except Exception as e:
                logger.debug('FriendActivity log skipped: %s', e)
    else:
        # Người dùng chưa đăng nhập: vẫn tăng play_count, không ghi lịch sử
        Song.objects.filter(id=song.id).update(play_count=F('play_count') + 1)

    # Lấy play_count mới nhất từ DB
    song.refresh_from_db(fields=['play_count'])
    return song.play_count


#xoá toàn bộ lịch sử nghe của user. trả số bản ghi đã xoá
def clear_listen_history(user) -> dict:
    deleted, _ = ListenHistory.objects.filter(user=user).delete()
    return deleted



#LIKE
#lấy toggle like/unlike bài hát
def toggle_like(user, song: Song) -> dict:
    like, created = Like.objects.get_or_create(user=user, song=song)
    if not created:
        #đã like -> unlike
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'
    
    like_count = Like.objects.filter(song=song).count()
    return {
        'action': action,
        'like_count': like_count,
    }



#RATING
#upsert rating mỗi user chỉ có 1 rating/bài
#gửi lặp lại sẽ cập nhật score cũ
def upsert_rating(user, song: Song, score: int) -> dict:
    from django.db.models import Avg, Count

    Rating.objects.update_or_create(
        user=user,
        song=song,
        defaults={'score': score},
    )

    stats = Rating.objects.filter(song=song).aggregate(avg=Avg('score'), count=Count('id'))

    return {
        'score': score,
        'avg_rating': round(stats['avg'], 1) if stats['avg'] else None,
        'rating_count': stats['count'],
    }




#COMMENT
#tạo bình luận mới
def create_comment(user, song: Song, data: dict) -> Comment:
    #block check
    if is_blocked(viewer_id=user.id, target_id=song.artist_id):
        raise BlockedByArtist()
    
    parent = None
    if data.get('parent_id'):
        try:
            parent = Comment.objects.get(
                id=data['parent_id'],
                song=song,
                is_hidden=False,
            )
        except Comment.DoesNotExist:
            raise InvalidParentComment('Bình luận không tồn tại hoặc thuộc bài hát khác')
        

        #không cho reply của reply 
        if parent.parent_id is not None:
            raise InvalidParentComment('Không thể trả lời bình luận đã là reply')


    comment = Comment.objects.create(
        user=user,
        song=song,
        parent=parent,
        content=data['content'],
    )
    logger.info('Comment created: user=%s, song=%s', user.username, song.id)

    return comment


#xoá bình luận 
def delete_comment(comment: Comment, user) -> None:
    if str(comment.user_id) != str(user.id):
        raise NotCommentOwner()
    comment.delete()

#admin ẩn bình luận vi phạm
def admin_hide_comment(comment: Comment) -> Comment:
    comment.is_hidden = True
    comment.save(update_fields=['is_hidden'])
    return comment

#lấy toggle like/unlike bình luận
def toggle_comment_like(user, comment: Comment) -> dict:
    like, created = CommentLike.objects.get_or_create(user=user, comment=comment)
    if not created:
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'
    like_count = CommentLike.objects.filter(comment=comment).count()
    return {
        'action': action,
        'like_count': like_count,
    }




#REPORT
#tạo báo cáo vi phạm
def create_report(reporter, data: dict) -> Report:
    report = Report.objects.create(
        reporter=reporter,
        target_type=data['target_type'],
        target_id=data['target_id'],
        reason=data['reason'],
        description=data.get('description', ''),
        status=Report.STATUS_PENDING, 
    )
    logger.info('Report created: %s/%s by %s', data['target_type'], data['target_id'], reporter.username)
    return report


#admin xử lý báo cáo
def resolve_report(report: Report, admin, action: str, note: str='') -> Report:
    if action not in (Report.STATUS_RESOLVED, report.STATUS_DISMISSED):
        raise ValidationError(
            'action không hợp lệ',
            fields={
                'action': ['action không pahir là "resolved" hoặc "dismissed"'],
            },
        )
    
    report.status = action
    report.resolved_by = admin
    report.resolved_note = note
    report.save(update_fields=[
        'status',
        'resolved_by',
        'resolved_note'
    ])
    return report


# ALBUM SERVICES
def create_album(artist, data: dict):
    """Tạo album mới (draft) cho nghệ sĩ."""
    from music.models import Album
    from accounts.exceptions import ValidationError

    title = data.get('title', '').strip()
    if not title:
        raise ValidationError('Tên album không được để trống', fields={'title': ['Bắt buộc']})

    album = Album.objects.create(
        title=title,
        artist=artist,
        description=data.get('description', ''),
        status=Album.STATUS_DRAFT,
    )
    logger.info('Album created: %s by %s', album.title, artist.username)
    return album


def update_album(album, artist, data: dict, cover_image=None):
    """Cập nhật thông tin album."""
    from music.exceptions import NotAlbumOwner
    from accounts.exceptions import ValidationError

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    title = data.get('title', album.title).strip()
    if not title:
        raise ValidationError('Tên album không được để trống', fields={'title': ['Bắt buộc']})

    album.title = title
    album.description = data.get('description', album.description)

    if cover_image:
        album.cover_image = cover_image

    album.save()
    logger.info('Album updated: %s', album.id)
    return album


def publish_album(album, artist):
    """Phát hành album (draft → published)."""
    from music.exceptions import NotAlbumOwner
    from django.utils import timezone

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    album.status = album.STATUS_PUBLISHED
    album.released_at = timezone.now()
    album.save(update_fields=['status', 'released_at'])
    logger.info('Album published: %s', album.id)
    return album


def unpublish_album(album, artist):
    """Ẩn album (published → draft)."""
    from music.exceptions import NotAlbumOwner

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    album.status = album.STATUS_DRAFT
    album.save(update_fields=['status'])
    return album


def delete_album(album, artist):
    """Xoá album."""
    from music.exceptions import NotAlbumOwner

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    album_id = str(album.id)
    album.delete()
    logger.info('Album deleted: %s', album_id)
    return {'deleted': album_id}


def add_song_to_album(album, song, artist):
    """Thêm bài hát vào album."""
    from music.models import AlbumSong
    from music.exceptions import NotAlbumOwner, SongAlreadyInAlbum, NotSongOwner

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    if str(song.artist_id) != str(artist.id):
        raise NotSongOwner()

    if AlbumSong.objects.filter(album=album, song=song).exists():
        raise SongAlreadyInAlbum()

    # Thứ tự = cuối danh sách
    max_order = album.album_songs.count()
    album_song = AlbumSong.objects.create(album=album, song=song, order=max_order)
    logger.info('Song %s added to album %s', song.id, album.id)
    return album_song


def remove_song_from_album(album, song, artist):
    """Xoá bài hát khỏi album."""
    from music.models import AlbumSong
    from music.exceptions import NotAlbumOwner

    if str(album.artist_id) != str(artist.id):
        raise NotAlbumOwner()

    deleted, _ = AlbumSong.objects.filter(album=album, song=song).delete()
    logger.info('Song %s removed from album %s', song.id, album.id)
    return {'removed': deleted > 0}