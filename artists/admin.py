from django.contrib import admin
from artists.models import ArtistProfile

@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display = ('get_display_name', 'user', 'stage_name', 'craeted_at')
    search_fields = ('stage_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
