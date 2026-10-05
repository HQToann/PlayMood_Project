from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    # Bảng tin và Tạo bài
    path('', views.PostListView.as_view(), name='post-list'),
    
    # Cảm xúc
    path('<uuid:post_id>/react/', views.PostReactionView.as_view(), name='post-react'),
    
    # Chi tiết (Sửa, Xóa)
    path('<uuid:post_id>/', views.PostDetailView.as_view(), name='post-detail'),
    
    # Ghim bài viết
    path('<uuid:post_id>/pin/', views.PostPinView.as_view(), name='post-pin'),
    
    # Bình luận
    path('<uuid:post_id>/comments/', views.PostCommentView.as_view(), name='post-comments'),
    
    # Cảm xúc bình luận
    path('comments/<uuid:comment_id>/react/', views.CommentReactionView.as_view(), name='comment-react'),
]
