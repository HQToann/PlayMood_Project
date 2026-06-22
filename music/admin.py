"""music/admin.py"""
from django.contrib import admin
from music.models import Genre, Song, Like, Rating, Comment, CommentLike, ListenHistory, Report

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'genre', 'status', 'is_trending', 'playcount', 'created_at')
    list_filter = ('status', 'is_trending', 'genre')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('play_count', 'created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'artist', 'genre', 'status', 'is_trending', 'play_count', 'created_at')
    list_filter = ('status', 'is_trending', 'genre')
    search_fields = ('title', 'artist__username')
    readonly_fields = ('play_count', 'created_at', 'update_at')
    ordering = ('-created_at',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reporter', 'target_type', 'reason', 'status', 'created_at')
    list_filter = ('status', 'target_type', 'reason')
    readonly_fields = ('created_at',)

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'created_at')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'score', 'created_at')

@admin.register(ListenHistory)
class ListenHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'listened_at')