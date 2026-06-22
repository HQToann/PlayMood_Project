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
        #tác giả thấy các bài public và draft
        qs = qs.filter(
            Q(status=Song.STATUS_PUBLISHED) |
            Q(status=Song.STATUS_DRAFT, artist_id=viewer_id)
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
        ).values_list('blocked_id', flat=True)
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
        song.to_dict(viewer=viewer, include_start=True)
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

    #hidden không ai thấy kể cả tác giả
    if song.status == Song.STATUS_HIDDEN:
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
    stats = Rating.objects.filter(song_id=song_id).aaggregate(
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
    qs = {
        Comment.objects
        .filter(song_id=song_id, parent__isnull=True, is_hidden=False)
    }