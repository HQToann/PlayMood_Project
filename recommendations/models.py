"""
recommendations/models.py

Models cho app recommendations:
    - RecommendationDismissal: User đánh dấu "không quan tâm" một bài hát được
      gợi ý. Dùng làm tín hiệu phủ định (negative signal): loại bài hát đó khỏi
      các lần gợi ý sau cho user này.

Tất cả PK là UUIDField theo quy ước chung của hệ thống.
"""

import uuid

from django.db import models


class RecommendationDismissal(models.Model):
    """Bài hát bị user gạt bỏ khỏi danh sách gợi ý - toggle giống Like."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='dismissed_recommendations',
        verbose_name='Người dùng',
    )

    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        related_name='dismissed_by',
        verbose_name='Bài hát',
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày gạt bỏ',
    )

    class Meta:
        db_table = 'recommendations_dismissal'
        unique_together = [('user', 'song')]
        ordering = ['-created_at']
        verbose_name = 'Gợi ý bị gạt bỏ'
        verbose_name_plural = 'Gợi ý bị gạt bỏ'

    def __str__(self):
        return f'{self.user.username} dismiss {self.song.title}'
