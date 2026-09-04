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
        'comments'
    ).order_by('-created_at').distinct()
