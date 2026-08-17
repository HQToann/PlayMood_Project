from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, ArtistVerification, BlockList


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'created_at')
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

@admin.register(ArtistVerification)
class ArtistVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'real_name', 'status', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'real_name')
    readonly_fields = ('created_at', 'reviewed_by', 'reviewed_at')

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
class BlockListAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')
    readonly_fields = ('created_at',)
