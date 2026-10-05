"""recommendations/apps.py"""

from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recommendations'
    label = 'recommendations'
    verbose_name = 'Gợi ý bài hát'
