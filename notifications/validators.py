
#validate query params khi list thông báo: page, page_size, unread_only
def validate_list_notifications_params(params: dict) -> dict:
    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try: 
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    unread_only = str(params.get('unread_only', '')).strip().lower() in ('true', '1', 'yes')

    return {
        'page': page,
        'page_size': page_size,
        'unread_only': unread_only,
    }