"""
social/selectors.py

Tăng đọc cho app social - mỗi try vấn DB được viết ở đây

Quy ước:
    - Chỉ đọc dữ liệu, không ghi
    - Prefix hàm: get_*, list_*, count_*, is_*, check_*
    - Không raises HTTP exception
"""

import math
from django.db.models import Q

from social.models import Follow, Mood, FriendActivity
from social.exceptions import MoodNotFound
from accounts.selectors import is_blocked

# Follow
def is_following(follower_id, following_id) -> bool:
    """
    Kiểm tra follower_id có đang theo dõi following_id hay không
    """
    return Follow.objects.filter(follower_id=follower_id, following_id=following_id).exists()

def get_follow_counts(user_id) -> dict:
    """
    Trả số lượng followers và following của một user
    """
    return {
        'followers_count': Follow.objects.filter(following_id=user_id).count(),
        'following_count': Follow.objects.filter(follower_id=user_id).count(),
    }

def list_followers(user_id, viewer=None, page=1, page_size=20) -> dict:
    """
    Danh sách người đang theo dõi user_id (followers)
    Ẩn người đã block viewer
    """
    qs = Follow.objects.filter(following_id=user_id).select_related('follower')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer:
        from accounts.models import BlockList
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(follower_id__in=blocked_ids)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for f in qs[start:start + page_size]:
        u = f.follower
        items.append(
            {
                'id': str(u.id),
                'username': u.username,
                'display_name': u.get_display_name(),
                'avatar': u.avatar.url if u.avatar else None,
                'followed_at': f.created_at.isoformat(),
            }
        )
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }

def list_following(user_id, viewer=None, page=1, page_size=20) -> dict:
    """
    Danh sách người user_id đang theo dõi (following)
    """
    qs = Follow.objects.filter(follower_id=user_id).select_related('following')

    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth:
        from accounts.models import BlockList
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(following_id__in=blocked_ids)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for f in qs[start:start + page_size]:
        u = f.following
        items.append(
            {
                'id': str(u.id),
                'username': u.username,
                'display_name': u.get_display_name(),
                'avatar': u.avatar.url if u.avatar else None,
                'followed_at': f.created_at.isoformat(),
            }
        )
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        }
    }

# Mood 
def get_my_mood(user) -> Mood:
    """
    Lấy Mood hiện tại của chính user
    Raises:
        MoodNotFound: nếu user chưa từng thiết lập Mood
    """
    try:
        return Mood.objects.select_related('user', 'song', 'song__artist').get(user=user)
    except Mood.DoesNotExist:
        raise MoodNotFound()
    
def get_user_mood(user_id, viewer=None) -> Mood | None:
    """
    Lấy Mood công khai của một user
    """
    viewer_id = getattr(viewer, 'id', None)
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth and is_blocked(viewer_id, user_id):
        return None
    
    mood = Mood.objects.select_related('user', 'song', 'song__artist').filter(user_id=user_id).first()
    if mood is None or mood.is_expired():
        return None
    return mood

# FriendActivity / Feed
def list_feed(user, page=1, page_size=20) -> dict:
    """
    Lấy Feed hoạt động của những user đang theo dõi (following)
    """

    following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)

    # Loại trừ hoạt động của người đã block user
    from accounts.models import BlockList
    blocked_ids = BlockList.objects.filter(blocked_id=user.id).values_list('blocker_id', flat=True)
    
    qs = (
        FriendActivity.objects
        .filter(user_id__in=following_ids)
        .exclude(user_id__in=blocked_ids)
        .select_related('user', 'song', 'song__artist') # tối ưu N+1, JOIN 1 lần
        .order_by('-created_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict() for a in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1
        },
    }

def list_my_activities(user, page=1, page_size=20) -> dict:
    """
    Lấy lịch sử hoạt động của chính user
    """
    qs = (
        FriendActivity.objects
        .filter(user=user)
        .select_related('user', 'song', 'song__artist')
        .order_by('-created_at')
    )
    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict() for a in qs[start:start + page_size]]
    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1
        },
    }


def list_friends(user, page=1, page_size=50, search_query="") -> dict:
    """
    Danh sách bạn bè: những người mà user follow và họ cũng follow lại (mutual follow).
    """
    # ID của những người user đang follow
    following_ids = set(
        Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    )
    # ID của những người đang follow user
    follower_ids = set(
        Follow.objects.filter(following=user).values_list('follower_id', flat=True)
    )
    # Giao nhau = bạn bè 2 chiều
    friend_ids = following_ids & follower_ids

    from accounts.models import User as UserModel
    qs = UserModel.objects.filter(id__in=friend_ids, is_active=True)
    
    if search_query:
        from django.db.models import Q
        qs = qs.filter(
            Q(username__icontains=search_query) |
            Q(display_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
        
    qs = qs.select_related('mood', 'mood__song', 'mood__song__artist').order_by('username')
    total = qs.count()
    start = (page - 1) * page_size
    items = []
    for u in qs[start:start + page_size]:
        mood_data = None
        if hasattr(u, 'mood') and u.mood and not u.mood.is_expired():
            mood_data = u.mood.to_dict()

        items.append({
            'id': str(u.id),
            'username': u.username,
            'display_name': u.get_display_name(),
            'avatar': u.avatar.url if u.avatar else None,
            'role': u.role,
            'mood': mood_data,
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