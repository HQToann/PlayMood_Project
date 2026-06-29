from django.contrib import admin
from social.models import (
    Follow,
    Mood,
    FriendActivity,
)

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_text', 'song', 'expires_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FriendActivity)
class FriendActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'song', 'created_at')
    list_filter = ('activity_type')
