from unfold.admin import ModelAdmin
"""music/admin.py"""
from django.contrib import admin
from music.models import Genre, Song, Like, Rating, Comment, CommentLike, ListenHistory, Report

@admin.register(Genre)
class GenreAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Song)
class SongAdmin(ModelAdmin):
    list_display = ('title', 'artist', 'genre', 'status', 'hidden_by_admin', 'is_appealed', 'created_at', 'play_count')
    list_filter = ('status', 'hidden_by_admin', 'is_appealed', 'is_trending', 'created_at', 'genre')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('play_count', 'created_at', 'updated_at')
    ordering = ('-created_at',)

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