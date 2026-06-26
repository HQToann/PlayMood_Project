"""playlists/admin.py"""

from django.contrib import admin
from playlists.models import Playlist, PlaylistSong

class PlaylistSongInline(admin.TabularInline):
    model = PlaylistSong
    extra = 0
    fields = ('song', 'order', 'added_at')
    readonly_fields = ('added_at',)

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'is_public', 'created_at')
    list_filter = ('is_public',)
    search_fields = ('title', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PlaylistSongInline]

@admin.register(PlaylistSong)
class PlaylistSongAdmin(admin.ModelAdmin):
    list_display = ('playlist', 'song', 'order', 'added_at')
    search_fields = ('playlist__title', 'song__title')