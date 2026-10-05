from unfold.admin import ModelAdmin
"""music/admin.py"""
from django.contrib import admin
from django.utils.html import format_html
from music.models import Genre, Song, Like, Rating, Comment, CommentLike, ListenHistory, Report


@admin.register(Genre)
class GenreAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Song)
class SongAdmin(ModelAdmin):
    list_display = ('cover_thumbnail', 'title', 'artist_link', 'genre', 'status_badge', 'is_appealed_badge', 'play_count')
    list_filter = ('status', 'hidden_by_admin', 'is_appealed', 'is_trending', 'created_at', 'genre')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('play_count', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def cover_thumbnail(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" class="admin-cover" />', obj.cover_image.url)
        return format_html('<div class="admin-cover bg-gray-700 flex items-center justify-center text-xs text-gray-400">No Img</div>')
    cover_thumbnail.short_description = 'Ảnh bìa'
    
    def artist_link(self, obj):
        return obj.artist.username
    artist_link.short_description = 'Nghệ sĩ'
    
    def status_badge(self, obj):
        colors = {
            'published': 'bg-green-500/20 text-green-500 border border-green-500/20',
            'draft': 'bg-gray-500/20 text-gray-400 border border-gray-500/20',
            'hidden': 'bg-red-500/20 text-red-500 border border-red-500/20',
        }
        color_class = colors.get(obj.status, 'bg-gray-500/20 text-gray-400')
        return format_html('<span class="px-2 py-1 rounded-full text-xs font-medium {}">{}</span>', color_class, obj.get_status_display())
    status_badge.short_description = 'Trạng thái'

    def is_appealed_badge(self, obj):
        if obj.is_appealed:
            return format_html('<span class="px-2 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-500 border border-yellow-500/20">Có khiếu nại</span>')
        return "-"
    is_appealed_badge.short_description = 'Khiếu nại'

@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display  = ('user', 'song', 'is_hidden', 'created_at')
    list_filter   = ('is_hidden',)
    search_fields = ('content', 'user__username')


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ('reporter', 'target_type', 'reason', 'status', 'created_at')
    list_filter = ('status', 'target_type', 'reason')
    readonly_fields = ('created_at',)

@admin.register(Like)
class LikeAdmin(ModelAdmin):
    list_display = ('user', 'song', 'created_at')

@admin.register(Rating)
class RatingAdmin(ModelAdmin):
    list_display = ('user', 'song', 'score', 'created_at')

@admin.register(ListenHistory)
class ListenHistoryAdmin(ModelAdmin):
    list_display = ('user', 'song', 'listened_at')