import json
import math
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from accounts.exceptions import AppException
from . import services, selectors

def handle_exception(e):
    """Hàm tiện ích xử lý lỗi chung."""
    if isinstance(e, AppException):
        status_code = 400
        if getattr(e, 'error_code', '') == 'NOT_FOUND':
            status_code = 404
        elif getattr(e, 'error_code', '') in ['NOT_FRIENDS', 'PERMISSION_DENIED']:
            status_code = 403
            
        payload = {'code': getattr(e, 'error_code', 'ERROR'), 'message': getattr(e, 'message', str(e))}
        if hasattr(e, 'fields') and e.fields:
            payload['fields'] = e.fields
            
        return JsonResponse({'success': False, 'error': payload}, status=status_code)
    return JsonResponse({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class PostListView(View):
    """API lấy Bảng tin và Đăng bài viết mới."""
    
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            
            # Sử dụng Selector chống N+1
            qs = selectors.get_news_feed_queryset(request.user)
            
            total = qs.count()
            total_pages = math.ceil(total / page_size) if total > 0 else 1
            
            start = (page - 1) * page_size
            end = start + page_size
            
            # Serialize dữ liệu
            items = []
            for post in qs[start:end]:
                shared_song_data = None
                if post.shared_song:
                    shared_song_data = {
                        'id': str(post.shared_song.id),
                        'title': post.shared_song.title,
                        'artist': post.shared_song.artist.get_display_name() if post.shared_song.artist else 'Nghệ sĩ',
                        'cover_image': post.shared_song.cover_image.url if post.shared_song.cover_image and post.shared_song.cover_image.name else 'https://images.unsplash.com/photo-1614680376593-902f74a7460c'
                    }
                    
                # Group reactions from prefetched data
                reaction_counts = {}
                current_user_reaction = None
                for r in post.reactions.all():
                    reaction_counts[r.reaction_type] = reaction_counts.get(r.reaction_type, 0) + 1
                    if r.user_id == request.user.id:
                        current_user_reaction = r.reaction_type
                
                # Sort by count descending and get top 3
                top_reaction_types = [
                    k for k, v in sorted(reaction_counts.items(), key=lambda item: item[1], reverse=True)
                ][:3]
                    
                post_data = {
                    'id': str(post.id),
                    'author': post.author.to_dict(),
                    'content': post.content,
                    'created_at': post.created_at.isoformat(),
                    'reactions_count': len(post.reactions.all()), # Avoid extra query by using len() instead of count()
                    'top_reactions': top_reaction_types,
                    'current_user_reaction': current_user_reaction,
                    'comments_count': len(post.comments.all()), # Avoid extra query
                    'shared_song': shared_song_data,
                    'media': [
                        {'url': m.file_url, 'type': m.media_type} for m in post.media.all()
                    ]
                }
                items.append(post_data)
                
            return JsonResponse({
                'success': True,
                'data': {
                    'items': items,
                    'pagination': {
                        'current_page': page,
                        'total_pages': total_pages,
                        'has_next': page < total_pages
                    }
                }
            })
        except Exception as e:
            return handle_exception(e)

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': {'code': 'AUTH_REQUIRED', 'message': 'Vui lòng đăng nhập'}}, status=401)
            
        try:
            # Nhận multipart/form-data
            content = request.POST.get('content', '')
            visibility = request.POST.get('visibility', 'PUBLIC')
            shared_song_id = request.POST.get('shared_song_id')
            
            media_urls = []
            images = request.FILES.getlist('images')
            if images:
                from django.core.files.storage import default_storage
                import uuid
                for img in images:
                    ext = img.name.split('.')[-1]
                    filename = f"posts/{uuid.uuid4()}.{ext}"
                    path = default_storage.save(filename, img)
                    media_urls.append(default_storage.url(path))
            
            post = services.create_post(
                user=request.user, 
                data={'content': content, 'visibility': visibility}, 
                media_urls=media_urls,
                shared_song_id=shared_song_id
            )
            
            return JsonResponse({'success': True, 'data': {'id': str(post.id)}})
        except Exception as e:
            return handle_exception(e)

@method_decorator(csrf_exempt, name='dispatch')
class PostReactionView(View):
    """API Thả Cảm xúc."""
    def post(self, request, post_id):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False}, status=401)
        try:
            data = json.loads(request.body)
            reaction_type = data.get('reaction_type')
            
            result = services.toggle_reaction(request.user, post_id, reaction_type)
            
            # Fetch updated count and top reactions
            from .models import Post
            post = Post.objects.prefetch_related('reactions').get(id=post_id)
            reaction_counts = {}
            for r in post.reactions.all():
                reaction_counts[r.reaction_type] = reaction_counts.get(r.reaction_type, 0) + 1
            
            top_reaction_types = [
                k for k, v in sorted(reaction_counts.items(), key=lambda item: item[1], reverse=True)
            ][:3]
            
            result['top_reactions'] = top_reaction_types
            result['reactions_count'] = sum(reaction_counts.values())
            
            return JsonResponse({'success': True, 'data': result})
        except Exception as e:
            return handle_exception(e)

@method_decorator(csrf_exempt, name='dispatch')
class PostCommentView(View):
    """API Bình luận."""
    
    def get(self, request, post_id):
        try:
            from .models import Comment
            # Chỉ lấy các bình luận gốc (parent is null) và prefetch replies
            comments = Comment.objects.filter(post_id=post_id, parent__isnull=True).prefetch_related('replies', 'author', 'replies__author').order_by('created_at')
            
            comments_data = []
            for comment in comments:
                replies_data = []
                for reply in comment.replies.all():
                    replies_data.append({
                        'id': str(reply.id),
                        'author': reply.author.to_dict(),
                        'content': reply.content,
                        'created_at': reply.created_at.isoformat()
                    })
                comments_data.append({
                    'id': str(comment.id),
                    'author': comment.author.to_dict(),
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat(),
                    'replies': replies_data
                })
                
            return JsonResponse({'success': True, 'data': comments_data})
        except Exception as e:
            return handle_exception(e)
            
    def post(self, request, post_id):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False}, status=401)
        try:
            data = json.loads(request.body)
            content = data.get('content', '')
            parent_id = data.get('parent_id') # Nullable
            
            comment = services.create_comment(request.user, post_id, content, parent_id)
            
            return JsonResponse({'success': True, 'data': {'id': str(comment.id)}})
        except Exception as e:
            return handle_exception(e)
