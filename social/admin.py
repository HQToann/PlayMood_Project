from django.contrib import admin
from social.models import (
    Follow,
    MoodTheme,
    MoodType,
    Mood,
    FriendActivity,
)

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')


@admin.register(MoodTheme)
class MoodThemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_hex', 'gradient_from', 'gradient_to', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(MoodType)
class MoodTypeAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'name', 'description', 'theme', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active', 'theme')
    search_fields = ('name', 'description')
    ordering = ('order', 'name')
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'emoji', 'description')
        }),
        ('Giao diện', {
            'fields': ('theme',),
            'description': 'Chọn bản màu hiển thị trên card cảm xúc.',
        }),
        ('Cài đặt', {
            'fields': ('order', 'is_active'),
        }),
    )


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_text', 'song', 'expires_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FriendActivity)
class FriendActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'song', 'created_at')
    list_filter = ('activity_type',)
