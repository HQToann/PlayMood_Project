from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    # Bảng tin và Tạo bài
    path('', views.PostListView.as_view(), name='post-list'),
    
    # Cảm xúc
    path('<uuid:post_id>/react/', views.PostReactionView.as_view(), name='post-react'),
    
    # Bình luận
    path('<uuid:post_id>/comments/', views.PostCommentView.as_view(), name='post-comments'),
]
