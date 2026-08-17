from unfold.admin import ModelAdmin
from django.contrib import admin
from artists.models import ArtistProfile

@admin.register(ArtistProfile)
class ArtistProfileAdmin(ModelAdmin):
    list_display = ('get_display_name', 'user', 'stage_name', 'created_at')
    search_fields = ('stage_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
