from django.contrib import admin
from .models import Post, PostMedia, PostReaction, Comment

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('author__username', 'content')
    inlines = [PostMediaInline]

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at', 'parent')
    search_fields = ('author__username', 'content')

@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction_type', 'created_at')
    list_filter = ('reaction_type',)
