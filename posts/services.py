from django.db import transaction
from accounts.models import User
from .models import Post, PostMedia, PostReaction, Comment
from .exceptions import PostNotFound
from .validators import validate_post_creation, validate_reaction_type
from notifications.services import create_notification
from notifications.models import Notification

def create_post(user: User, data: dict, media_urls: list, shared_song_id: str = None) -> Post:
    """Tạo bài viết mới kèm hình ảnh và/hoặc bài hát."""
    content = data.get('content', '')
    visibility = data.get('visibility', 'PUBLIC')
    
    validate_post_creation(content, bool(media_urls), bool(shared_song_id))
    
    with transaction.atomic():
        post = Post.objects.create(
            author=user,
            content=content,
            visibility=visibility,
            shared_song_id=shared_song_id
        )
        
        # Lưu danh sách URL ảnh vào bảng PostMedia
        for index, url in enumerate(media_urls):
            PostMedia.objects.create(
                post=post,
                file_url=url,
                media_type='image',
                order=index
            )
            
    return post

def toggle_reaction(user: User, post_id: str, reaction_type: str) -> dict:
    """Xử lý Thả / Đổi / Hủy cảm xúc."""
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise PostNotFound()
        
    validate_reaction_type(reaction_type)
    
    # Tìm xem User đã thả cảm xúc bài này chưa
    reaction = PostReaction.objects.filter(post=post, user=user).first()
    
    if not reaction:
        # 1. Chưa thả -> Tạo mới
        PostReaction.objects.create(post=post, user=user, reaction_type=reaction_type)
        if post.author != user:
            create_notification(
                recipient=post.author,
                sender=user,
                notif_type=Notification.TYPE_LIKE,
                target_type=Notification.TARGET_USER,
                target_id=post.author.id,
                message=f"{user.get_display_name()} đã bày tỏ cảm xúc về bài viết của bạn."
            )
        action_res = {"action": "added", "reaction": reaction_type}
    
    elif reaction.reaction_type == reaction_type:
        # 2. Đã thả cùng icon đó -> Xóa (Unlike)
        reaction.delete()
        action_res = {"action": "removed", "reaction": None}
        
    else:
        # 3. Đã thả nhưng chọn icon khác -> Cập nhật
        reaction.reaction_type = reaction_type
        reaction.save()
        action_res = {"action": "updated", "reaction": reaction_type}

    # Bắn WebSocket cập nhật số đếm cho bảng tin
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    if channel_layer:
        # Tính toán lại số đếm
        reaction_counts = {}
        for r in post.reactions.all():
            reaction_counts[r.reaction_type] = reaction_counts.get(r.reaction_type, 0) + 1
        
        top_reaction_types = [
            k for k, v in sorted(reaction_counts.items(), key=lambda item: item[1], reverse=True)
        ][:3]
        
        async_to_sync(channel_layer.group_send)(
            'live_feed',
            {
                'type': 'feed_message',
                'message_type': 'reaction_update',
                'data': {
                    'post_id': str(post.id),
                    'reactions_count': sum(reaction_counts.values()),
                    'top_reactions': top_reaction_types,
                    # current_user_reaction không gửi vì nó phụ thuộc vào mỗi người
                }
            }
        )

    return action_res

def create_comment(user: User, post_id: str, content: str, parent_id: str = None) -> Comment:
    """Gửi bình luận hoặc trả lời."""
    if not content.strip():
        raise ValueError("Nội dung không được để trống")
        
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        raise PostNotFound()
        
    parent_comment = None
    if parent_id:
        try:
            parent_comment = Comment.objects.get(id=parent_id, post=post)
        except Comment.DoesNotExist:
            pass # Nếu truyền parent_id bậy, ta cứ cho thành bình luận gốc
            
    comment = Comment.objects.create(
        post=post,
        author=user,
        content=content,
        parent=parent_comment
    )

    # Gửi thông báo cho tác giả bài viết
    if post.author != user:
        create_notification(
            recipient=post.author,
            sender=user,
            notif_type=Notification.TYPE_COMMENT,
            target_type=Notification.TARGET_USER,
            target_id=post.author.id,
            message=f"{user.get_display_name()} đã bình luận bài viết của bạn: '{content[:20]}...'"
        )

    # Nếu đây là phản hồi (reply), gửi thông báo cho người được phản hồi
    if parent_comment and parent_comment.author != user:
        create_notification(
            recipient=parent_comment.author,
            sender=user,
            notif_type=Notification.TYPE_REPLY,
            target_type=Notification.TARGET_USER,
            target_id=parent_comment.author.id,
            message=f"{user.get_display_name()} đã trả lời bình luận của bạn."
        )

    # Bắn comment mới lên Live Feed WebSocket
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    if channel_layer:
        # Chuẩn bị dữ liệu comment
        c_data = {
            'id': str(comment.id),
            'post_id': str(post.id),
            'author': comment.author.to_dict(),
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'parent_id': str(comment.parent_id) if comment.parent_id else None,
            'reactions_count': 0,
            'top_reactions': [],
            'current_user_reaction': None
        }
        
        async_to_sync(channel_layer.group_send)(
            'live_feed',
            {
                'type': 'feed_message',
                'message_type': 'new_comment',
                'data': c_data
            }
        )

    return comment
