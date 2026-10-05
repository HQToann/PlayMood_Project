"""
recommendations/services.py

Tầng ghi dữ liệu cho app recommendations.
"""

from music.models import Song
from music.exceptions import SongNotFound
from recommendations.models import RecommendationDismissal


def dismiss_recommendation(user, song_id) -> bool:
    """
    Đánh dấu "không quan tâm" 1 bài hát được gợi ý - toggle giống Like.

    Bài hát bị dismiss sẽ không xuất hiện lại trong for-you feed của user đó.

    Returns:
        True nếu vừa dismiss, False nếu vừa gỡ dismiss (bấm lại lần 2).
    """
    try:
        song = Song.objects.get(id=song_id, status=Song.STATUS_PUBLISHED)
    except Song.DoesNotExist:
        raise SongNotFound()

    existing = RecommendationDismissal.objects.filter(user=user, song=song).first()
    if existing:
        existing.delete()
        return False

    RecommendationDismissal.objects.create(user=user, song=song)
    return True
