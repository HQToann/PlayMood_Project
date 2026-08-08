import math
from django.db.models import Avg, Count, Q
from music.models import (
    Genre,
    Song,
    Like,
    Rating,
    Comment,
    ListenHistory,
    Report,
    Album,
    AlbumSong,
)
from music.exceptions import (
    SongNotFound,
    GenreNotFound,
    CommentNotFound,
    ReportNotFound,
)
from accounts.selectors import is_blocked

#GENRE
#trả danh sách tất cả thể laoij kèm số bài hát published
def list_genres() -> list:
    genres = Genre.objects.all().order_by('name')
    return [g.to_dict(include_song_count=True) for g in genres]

def get_genre_by_id(genre_id) -> Genre:
    try:
        return Genre.objects.get(id=genre_id)
    except Genre.DoesNotExist:
        raise GenreNotFound()
    
#lấy genre theo slug
def get_genre_by_slug(slug: str) -> Genre | None:
    return Genre.objects.filter(slug=slug).first()

#SONG
# Danh sách bài hát với filter + phân trang.

#     Business rules:
#     - Anonymous/user thường: chỉ thấy status=published
#     - Artist: thấy published + draft của chính mình
#     - Ẩn bài hát của người đã block viewer

#     Args:
#         filters: dict từ validate_list_songs_params()
#         viewer:  request.user (có thể AnonymousUser)

#     Returns:
#         dict gồm 'items' (list) và 'pagination' (dict)
def list_songs(filters: dict, viewer=None) -> dict:
    viewer_id = getattr(viewer, 'id', None)
    viewer_id_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    viewer_role = getattr(viewer, 'role', None)
    qs = Song.objects.select_related('artist', 'genre')

    #phân quyền theo role
    if viewer_id_auth and viewer_role == 'artist':
        #tác giả thấy các bài public, draft và hidden của chính mình
        qs = qs.filter(
            Q(status=Song.STATUS_PUBLISHED) |
            Q(status__in=[Song.STATUS_DRAFT, Song.STATUS_HIDDEN], artist_id=viewer_id)
        )
    elif viewer_id_auth and viewer_role == 'admin':
        pass #admin lấy tất cả
    else:
        qs = qs.filter(status=Song.STATUS_PUBLISHED)

    #ẩn tất cả bài hát của người đã block viewer
    if viewer_id_auth:
        from accounts.models import BlockList
        blocked_artist_ids = BlockList.objects.filter(
            blocked_id=viewer_id
        ).values_list('blocker_id', flat=True)
        qs = qs.exclude(artist_id__in=blocked_artist_ids)

    #filters
    if filters.get('q'):
        qs = qs.filter(title__icontains=filters['q'])

    if filters.get('genre'):
        genre = get_genre_by_slug(filters['genre'])
        if genre:
            qs = qs.filter(genre=genre)
    
    if filters.get('artist_id'):
        qs = qs.filter(artist_id=filters['artist_id'])

    #ordering
    ordering = filters.get('ordering', '-created_at')
    qs = qs.order_by(ordering)
    
    #phân trang
    page = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size

    items = [
        song.to_dict(viewer=viewer, include_stats=True)
        for song in qs[start:end]
    ]


    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total/page_size) if total > 0 else 1,
        },
    }


#danh sách bài hát trending (is_trending=True), sắp xếp theo play_count
def list_trending_songs(limit=20) -> dict:
    songs = (
        Song.objects
        .filter(status=Song.STATUS_PUBLISHED, is_trending=True)
        .select_related('artist', 'genre')
        .order_by('-play_count')[:limit]
    )
    return [s.to_dict(include_stats=True) for s in songs]


#lấy Song theo UUID chỉ dùng trong services (không check block) 
def get_song_by_id(song_id) -> Song:
    try:
        return Song.objects.select_related('artist', 'genre').get(id=song_id)
    except Song.DoesNotExist:
        raise SongNotFound


#Lấy Song để trả về cho client
#rules
#song status=hidden -> ẩn với mọi người
#song status=draft -> chỉ tác giả mới thấy
#viewer bị artist block -> ẩn
def get_song_detail(song_id, viewer=None) -> Song:
    try:
        song = Song.objects.select_related('artist', 'genre').get(id=song_id)
    except Song.DoesNotExist:
        raise SongNotFound()
    
    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    
    viewer_role = getattr(viewer, 'role', '')
    is_admin = (viewer_role == 'admin') or getattr(viewer, 'is_staff', False)
    is_author = (str(viewer_id) == str(song.artist_id))

    #hidden: chỉ admin và tác giả có thể xem
    if song.status == Song.STATUS_HIDDEN:
        if not viewer_is_auth or (not is_admin and not is_author):
            raise SongNotFound()
    
    #draft chỉ tác giả thấy
    if song.status == Song.STATUS_DRAFT:
        if not viewer_is_auth or str(viewer_id) != str(song.artist_id):
            raise SongNotFound()
        
    #block check
    if viewer_is_auth and is_blocked(viewer_id, song.artist_id):
        raise SongNotFound()
    

    return song

#trả like_count và is_liked của viewer
def get_song_like_count(song_id, viewer=None) -> dict:
    like_count = Like.objects.filter(song_id=song_id).count()
    is_liked = False
    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        is_liked = Like.objects.filter(song_id=song_id, user_id=viewer).exists()
        return {
            'like_count': like_count,
            'is_liked': is_liked,
        }
    

#lấy avg_rating, rating_count, my_rating
def get_song_rating_stats(song_id, viewer=None) -> dict:
    stats = Rating.objects.filter(song_id=song_id).aggregate(
        avg=Avg('score'),
        count=Count('id'),
    )
    my_rating = None
    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        r = Rating.objects.filter(song_id=song_id, user_id=viewer_id).first()
        my_rating = r.score if r else None

    return {
        'avg_rating': round(stats['avg'], 1) if stats['avg'] else None,
        'rating_count': stats['count'],
        'my_rating': my_rating,
    }


#lấy danh sách bình luận gốc kèm replied
#chỉ trả is_hidden=False
#replies được load cùng (prefecth)
def list_comments(song_id, viewer=None, page=1, page_size=20) -> dict:
    qs = (
        Comment.objects
        .filter(song_id=song_id, parent__isnull=True, is_hidden=False)
        .select_related('user')
        .prefetch_related('replies__user', 'replies__comment_likes', 'comment_likes')
        .order_by('created_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [
        c.to_dict(viewer=viewer, include_replies=True)
        for c in qs[start:start + page_size]
    ]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }



#lấy comment theo UUID
def get_comment_by_id(comment_id) -> Comment:
    try:
        return Comment.objects.select_related('user', 'song').get(id=comment_id, is_hidden=False)
    except Comment.DoesNotExist:
        raise CommentNotFound()
    


#lịch sử nghe của user, kèm thông tin bài hát
def list_listen_history(user, page=1, page_size=20) -> dict:
    # Lấy lần nghe gần nhất cho mỗi bài hát (dedup theo song_id)
    from django.db.models import Max
    latest_per_song = (
        ListenHistory.objects
        .filter(user=user)
        .values('song_id')
        .annotate(last_listened=Max('listened_at'))
    )

    # Lấy set id (song_id, last_listened) rồi query lại
    song_ids_ordered = [item['song_id'] for item in latest_per_song.order_by('-last_listened')]
    listened_at_map = {item['song_id']: item['last_listened'] for item in latest_per_song}

    total = len(song_ids_ordered)
    start = (page - 1) * page_size
    paged_ids = song_ids_ordered[start:start + page_size]

    # Fetch song details
    from .models import Song as SongModel
    songs_qs = SongModel.objects.filter(id__in=paged_ids).select_related('artist', 'genre')
    songs_map = {s.id: s for s in songs_qs}

    items = []
    for song_id in paged_ids:
        song = songs_map.get(song_id)
        if not song:
            continue
        items.append({
            'song': {
                'id': str(song.id),
                'title': song.title,
                'artist': {'display_name': song.artist.get_display_name()} if song.artist else None,
                'genre': {'name': song.genre.name} if song.genre else None,
                'cover_image': song.cover_image.url if song.cover_image else None,
                'duration': song.duration,
                'is_liked': song.likes.filter(user=user).exists() if user.is_authenticated else False
            },
            'listened_at': listened_at_map[song_id].isoformat(),
        })

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }



#report danh sách báo cáo của admin
def list_reports(filters: dict) -> dict:
    qs  = Report.objects.select_related('reporter', 'resolved_by')

    if filters.get('status'):
        qs = qs.filter(status=filters['status'])

    if filters.get('target_type'):
        qs = qs.filter(target_type=filters['target_type'])

    page = int(filters.get('page', 1))
    page_size = int(filters.get('page_size', 20))
    total = qs.count()
    start = (page - 1) * page_size


    return {
        'items': [r.to_dict() for r in qs[start:start + page_size]],
        'pagination': {
            'page': page, 'page_size': page_size, 'total': total,
            'total_pages': math.ceil(total/page_size) if total > 0 else 1,
        },
    }



#lấy Report theo UUID
def get_report_by_id(report_id) -> Report:
    try:
        return Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        raise ReportNotFound()


#lấy danh sách bài hát yêu thích của user
def list_user_liked_songs(target_user_id, viewer=None, limit=5) -> list:
    qs = (
        Like.objects.filter(user_id=target_user_id)
        .select_related('song', 'song__artist', 'song__genre')
        .order_by('-created_at')
    )
    
    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    
    items = []
    for like in qs:
        song = like.song
        
        # Chỉ hiển thị bài hát public, trừ khi viewer là admin hoặc tác giả
        if song.status != Song.STATUS_PUBLISHED:
            if not viewer_is_auth:
                continue
            is_admin = getattr(viewer, 'role', '') == 'admin' or getattr(viewer, 'is_staff', False)
            is_author = str(viewer_id) == str(song.artist_id)
            if song.status == Song.STATUS_HIDDEN and not (is_admin or is_author):
                continue
            if song.status == Song.STATUS_DRAFT and not is_author:
                continue
                
        # Kiểm tra block
        if viewer_is_auth and is_blocked(viewer_id, song.artist_id):
            continue
            
        song_dict = song.to_dict(viewer=viewer, include_stats=True)
        song_dict['liked_at'] = like.created_at.isoformat()
        items.append(song_dict)
        if len(items) >= limit:
            break
            
    return items


# ALBUM
def list_albums(artist=None, status=None, include_songs=True) -> list:
    """
    Liệt kê album, có thể lọc theo artist và/hoặc status.
    """
    qs = Album.objects.select_related('artist').prefetch_related('album_songs__song')
    if artist is not None:
        qs = qs.filter(artist=artist)
    if status is not None:
        qs = qs.filter(status=status)
    return [album.to_dict() for album in qs]


def get_album_by_id(album_id) -> Album:
    """Lấy album theo id, raise AlbumNotFound nếu không tìm thấy."""
    from music.exceptions import AlbumNotFound
    try:
        return Album.objects.select_related('artist').prefetch_related('album_songs__song').get(id=album_id)
    except Album.DoesNotExist:
        raise AlbumNotFound()