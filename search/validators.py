from accounts.exceptions import ValidationError

SEARCH_Q_MIN_LEN = 2
SEARCH_Q_MAX_LEN = 100

#validate q + page + page_size dùng chung cho songs/artists/playlists/users
def validate_search_params(params: dict, require_q: bool=True) -> dict:
    q = params.get('q', '').strip()

    errors = {}

    if require_q:
        if not q:
            errors['q'] = ['Từ khoá tìm kiếm là bắt buộc']
        elif len(q) < SEARCH_Q_MIN_LEN:
            errors['q'] = [f'Từ khoá tìm kiếm tối thiểu {SEARCH_Q_MIN_LEN} ký tự']
        elif len(q) > SEARCH_Q_MAX_LEN:
            errors['q'] = [f'Từ khoá tìm kiếm tối đa {SEARCH_Q_MAX_LEN} ký tự']


    try:
        page = max(1, int(params.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try: 
        page_size = min(100, max(1, int(params.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    if errors:
        raise ValidationError('Tham số tìm kiếm không hợp lệ', fields=errors)
        
    return {
        'q': q,
        'page': page,
        'page_size': page_size, 
    }


#Search bài hát cho phép q rỗng (duyệt theo genre/artist_id/ordering)
def validate_search_songs_params(params: dict) -> dict:
    result = validate_search_params(params, require_q=False)

    ordering = params.get('ordering', '-play_count')
    valid_orderings = {
        '-play_count',
        'play_count',
        '-released_at',
        'released_at',
        'title',
        '-title',
    }
    if ordering not in valid_orderings:
        ordering = '-play_count'

    result['genre'] = params.get('genre', '').strip()
    result['artist_id'] = params.get('artist_id', '').strip()
    result['ordering'] = ordering

    return result


def validate_search_all_params(params: dict) -> dict:
    resulf = validate_search_params(params, require_q=True)
    try:
        limit = min(10, max(1, int(params.get('limit', 5))))
    except (ValueError, TypeError):
        limit = 5
    resulf['limit'] = limit
    return resulf

    
