from django.db import transaction
from accounts.models import User
from .models import Post, PostMedia, PostReaction, Comment
from .exceptions import PostNotFound
from .validators import validate_post_creation, validate_reaction_type

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
        return {"action": "added", "reaction": reaction_type}
    
    if reaction.reaction_type == reaction_type:
        # 2. Đã thả cùng icon đó -> Xóa (Unlike)
        reaction.delete()
        return {"action": "removed", "reaction": None}
        
    # 3. Đã thả nhưng chọn icon khác -> Cập nhật
    reaction.reaction_type = reaction_type
    reaction.save()
    return {"action": "updated", "reaction": reaction_type}

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
            
    return Comment.objects.create(
        post=post,
        author=user,
        content=content,
        parent=parent_comment
    )
