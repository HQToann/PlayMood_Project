from django.db.models import Count, Prefetch
from django.db import models
from accounts.models import User
from social.models import Follow
from .models import Post, PostMedia, PostReaction, Comment

def get_news_feed_queryset(user: User):
    """
    Lấy danh sách bài viết mà User được phép xem:
    - Bài của chính mình
    - Bài Public hoặc Friends của những người mình đang Follow
    """
    following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    
    return Post.objects.filter(
        # Hoặc là tác giả
        models.Q(author=user) | 
        # Hoặc là bạn bè đăng Public/Friends
        (models.Q(author__in=following_ids) & models.Q(visibility__in=['PUBLIC', 'FRIENDS']))
    ).select_related(
        'author', 'shared_post', 'shared_post__author', 'shared_song', 'shared_song__artist'
    ).prefetch_related(
        'media',
        'reactions',
        'comments',
        'tagged_users'
    ).order_by('-created_at').distinct()

def get_user_posts_queryset(user: User, target_user_id: str):
    """
    Lấy danh sách bài viết của một user cụ thể (hiển thị trên trang cá nhân).
    - Nếu user == target_user: lấy tất cả bài viết của mình.
    - Nếu user != target_user: 
      - Nếu là bạn bè (mutual follow): lấy bài PUBLIC + FRIENDS.
      - Nếu không phải bạn bè: lấy bài PUBLIC.
    Sắp xếp ưu tiên bài ghim (is_pinned) lên đầu.
    """
    qs = Post.objects.filter(author_id=target_user_id)
    
    if str(user.id) != str(target_user_id):
        # Kiểm tra xem có phải bạn bè không (mutual follow)
        is_following = Follow.objects.filter(follower=user, following_id=target_user_id).exists()
        is_follower = Follow.objects.filter(follower_id=target_user_id, following=user).exists()
        is_friend = is_following and is_follower
        
        if is_friend:
            qs = qs.filter(visibility__in=['PUBLIC', 'FRIENDS'])
        else:
            qs = qs.filter(visibility='PUBLIC')
            
    return qs.select_related(
        'author', 'shared_post', 'shared_post__author', 'shared_song', 'shared_song__artist'
    ).prefetch_related(
        'media',
        'reactions',
        'comments',
        'tagged_users'
    ).order_by('-is_pinned', '-created_at')
