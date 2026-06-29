"""
- get_artist_stats() tính thống kê tổng hợp từ nhiều bảng của app music (Song, Like
Rating, Comment, ListenHistory)
- không lưu cache trong DB - mỗi lần gọi đề query lại đảm bảo
chính xác
"""

import math
from django.db.models import Count, Avg, Sum, Q
from artists.models import ArtistProfile
from artists.exceptions import ArtistProfileNotFound
from accounts.models import User
from accounts.selectors import is_blocked
from music.models import (
    Song,
    Like,
    Rating,
    Comment,
    ListenHistory,
)

#lấy ArtistProfile theo user_id không kiểm tra quyền xem (chỉ dùng nội bộ trong service)
def get_artist_profile_by_user_id(user_id) -> ArtistProfile:
    try:
        return ArtistProfile.objects.select_related('user').get(user_id=user_id)
    except ArtistProfile.DoesNotExist:
        raise ArtistProfileNotFound()
    

"""
- lấy Artistprofile trả về cho client có kiểm tra block policy
- nếu viewer bị target(nghệ sĩ) block: trả 404 
- get_publuc_profile() trong accounts/selectors.py và get_song_detail()
trong music/selectors.py, không để lộ thông tin bị block
"""
def get_artist_profile_detail(user_id, viewer=None) -> ArtistProfile:
    try:
        profile = ArtistProfile.objects.select_related('user').get(user_id=user_id)
    except ArtistProfile.DoesNotExist:
        raise ArtistProfileNotFound()
    
    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth and is_blocked(viewer_id, profile.user_id):
        raise ArtistProfileNotFound()
    
    return profile


#Kiểm tra user đã có ArtistProfile chưa
def check_profile_exists(user_id) -> bool:
    return ArtistProfile.objects.filter(user_id=user_id).exists()


"""
- danh sách nghệ sĩ (có ArtistProfile), tìm theo stage_name/username, phân trang
- Block policy ẩn nghệ sĩ đã block viewer, tương tự list_song() trong music/selectors.py
"""
def list_artists(filters: dict, viewer=None) -> dict:
    qs = ArtistProfile.objects.select_related('user')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))

    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_user_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(user_id__in=blocked_user_ids)

    if filters.get('q'):
        qs = qs.filter(Q(stage_name__icontains=filters['q']) |
                       Q(user__username__icontains=filters['q']))
        
    qs = qs.order_by('-created_at')
    page = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total = qs.count()
    start = (page - 1) * page_size
    items = [p.to_dict(viewer=viewer) for p in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }



#thống kê tổng hợp của nghệ sĩ
def get_artist_stats(artist_user_id) -> dict:
    #chỉ tính trên baiif hát published, bài daraft/hidde không tính vào thống kê công khai
    songs_qs = Song.objects.filter(artist_id=artist_user_id, status=Song.STATUS_PUBLISHED)
    total_songs = songs_qs.count()

    #Sum play_count của tất cả baiif hát dùng Sum() aggregate, tránh query N+1
    play_count_agg = songs_qs.aggregate(total=Sum('play_count'))
    total_play_count = play_count_agg['total'] or 0

    #Tổng số like trên toàn bộ bài hát của nghệ sĩ (qua FK song__artist_id)
    total_likes = Like.objects.filter(song__artist_id=artist_user_id, song__status=Song.STATUS_PUBLISHED).count()

    #tổng số comment không bị ẩn trên toàn bộ bai hát của nghệ sĩ
    total_comments = Comment.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
        is_hidden=False,
    ).count()

    #số lượng người nghệ sĩ duy nhất (distinct user_id trong ListenHistory)
    total_listeners = ListenHistory.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
    ).values('user_id').distinct().count()

    #điểm đánh giá trung bình + tổng số lượt đánh giá
    rating_agg = Rating.objects.filter(
        song__artist_id=artist_user_id,
        song__status=Song.STATUS_PUBLISHED,
    ).aggregate(avg=Avg('score'), count=Count('id'))


    return {
        'total_songs': total_songs,
        'total_play_count': total_play_count,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'total_listeners': total_listeners,
        'avg_rating': round(rating_agg['avg'], 1) if rating_agg['avg'] else None,
        'rating_count': rating_agg['count'],
    }



"""
- top bài hát của nghệ sĩ theo lượt nghe dùng cho thống kê chii tiết
- chỉ tính bài hát published, sắp xếp giảm dẫn thep play_count
"""
def list_artist_top_songs(artist_user_id, limit=10) -> list:
    songs = (
        Song.objects
        .filter(artist_id=artist_user_id, status=Song.STATUS_PUBLISHED)
        .order_by('-play_count')[:limit]
    )

    return [
        {
            'id': str(s.id),
            'title': s.title,
            'play_count': s.play_count,
            'like_count': s.likes.count(),
            'cover_image': s.cover_image.url if s.cover_image else None,
        }
        for s in songs
    ]