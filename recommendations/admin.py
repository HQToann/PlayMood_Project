"""recommendations/admin.py"""

from django.contrib import admin
from recommendations.models import RecommendationDismissal


@admin.register(RecommendationDismissal)
class RecommendationDismissalAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'song__title')
    raw_id_fields = ('user', 'song')
