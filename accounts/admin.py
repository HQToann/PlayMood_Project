from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, ArtistVerification, BlockList


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_private')
    search_fields = ('username', 'email', 'display_name')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {
            'fields': (
                'display_name',
                'avatar',
                'bio',
                'role',
                'is_private',
            ),
        }),
    )

@admin.register(ArtistVerification)
class ArtistVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'real_name', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'real_name')
    readonly_fields = ('created_at',)


@admin.register(BlockList)
class BlockListAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_at',)
