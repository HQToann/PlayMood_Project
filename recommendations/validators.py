"""
recommendations/validators.py

Validate query params cho các endpoint recommendations.
"""

from accounts.exceptions import ValidationError


def validate_recommend_params(params: dict) -> dict:
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = min(50, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    return {'page': page, 'page_size': page_size}


def validate_similar_params(params: dict) -> dict:
    """Validate và parse tham số GET cho SimilarSongsView."""
    errors = {}

    try:
        limit = int(params.get('limit', 10))
        if not 1 <= limit <= 50:
            errors['limit'] = ['limit phải từ 1 đến 50']
        limit = min(50, max(1, limit))
    except (ValueError, TypeError):
        errors['limit'] = ['limit phải là số nguyên']
        limit = 10

    if errors:
        raise ValidationError('Tham số không hợp lệ', fields=errors)

    return {'limit': limit}


def validate_media_params(params: dict) -> dict:
    """Validate tham số GET cho RecommendedArtistsView và RecommendedPlaylistsView."""
    errors = {}

    try:
        limit = int(params.get('limit', 10))
        if not 1 <= limit <= 50:
            errors['limit'] = ['limit phải từ 1 đến 50']
        limit = min(50, max(1, limit))
    except (ValueError, TypeError):
        errors['limit'] = ['limit phải là số nguyên']
        limit = 10

    if errors:
        raise ValidationError('Tham số không hợp lệ', fields=errors)

    return {'limit': limit}


def validate_mood_params(params: dict) -> dict:
    """Validate tham số GET cho MoodBasedViews (hỗ trợ phân trang)."""
    errors = {}

    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = int(params.get('limit', 10))
        if not 1 <= limit <= 50:
            errors['limit'] = ['limit phải từ 1 đến 50']
        limit = min(50, max(1, limit))
    except (ValueError, TypeError):
        errors['limit'] = ['limit phải là số nguyên']
        limit = 10

    if errors:
        raise ValidationError('Tham số không hợp lệ', fields=errors)

    return {'page': page, 'limit': limit}
