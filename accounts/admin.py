from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from accounts.models import User, ArtistVerification, BlockList


from django.utils.html import format_html

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    
    list_display = ('avatar_thumbnail', 'username', 'email', 'role_badge', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_private')
    search_fields = ('username', 'email')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Thông tin bổ sung', {
            'fields': (
                'avatar',
                'bio',
                'role',
                'is_private',
            ),
        }),
    )

    def avatar_thumbnail(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" class="admin-thumbnail" />', obj.avatar.url)
        return format_html('<div class="admin-thumbnail bg-gray-700 flex items-center justify-center text-xs text-gray-400">No Img</div>')
    avatar_thumbnail.short_description = 'Avatar'

    def role_badge(self, obj):
        colors = {
            'artist': 'bg-purple-500/20 text-purple-500 border border-purple-500/20',
            'user': 'bg-blue-500/20 text-blue-400 border border-blue-500/20',
            'admin': 'bg-red-500/20 text-red-500 border border-red-500/20',
        }
        color_class = colors.get(obj.role, 'bg-gray-500/20 text-gray-400')
        return format_html('<span class="px-2 py-1 rounded-full text-xs font-medium {}">{}</span>', color_class, obj.get_role_display())
    role_badge.short_description = 'Vai trò'

@admin.register(ArtistVerification)
class ArtistVerificationAdmin(ModelAdmin):
    list_display = ('user', 'real_name', 'status_badge', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'real_name')
    readonly_fields = ('created_at', 'reviewed_by', 'reviewed_at')

    def status_badge(self, obj):
        colors = {
            'approved': 'bg-green-500/20 text-green-500 border border-green-500/20',
            'pending': 'bg-yellow-500/20 text-yellow-500 border border-yellow-500/20',
            'rejected': 'bg-red-500/20 text-red-500 border border-red-500/20',
        }
        color_class = colors.get(obj.status, 'bg-gray-500/20 text-gray-400')
        return format_html('<span class="px-2 py-1 rounded-full text-xs font-medium {}">{}</span>', color_class, obj.get_status_display())
    status_badge.short_description = 'Trạng thái'

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = ArtistVerification.objects.get(pk=obj.pk)
            # Nếu admin thay đổi trạng thái
            if old_obj.status != obj.status:
                obj.reviewed_by = request.user
                from django.utils import timezone
                obj.reviewed_at = timezone.now()

                from accounts.models import User
                # Nếu duyệt, nâng cấp role và tự động tạo profile
                if obj.status == ArtistVerification.STATUS_APPROVED:
                    User.objects.filter(id=obj.user_id).update(role=User.ROLE_ARTIST)
                    
                    from artists.services import create_artist_profile
                    # Lấy instance user mới nhất sau khi update
                    updated_user = User.objects.get(id=obj.user_id)
                    try:
                        create_artist_profile(updated_user, {'stage_name': obj.real_name})
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning('Lỗi tạo artist profile cho %s: %s', updated_user.username, str(e))
                else:
                    # Nếu từ chối hoặc huỷ duyệt, hạ role về user thường và xoá profile nghệ sĩ
                    User.objects.filter(id=obj.user_id).update(role=User.ROLE_USER)
                    from artists.models import ArtistProfile
                    ArtistProfile.objects.filter(user_id=obj.user_id).delete()
        
        super().save_model(request, obj, form, change)


@admin.register(BlockList)
class BlockListAdmin(ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_at',)
