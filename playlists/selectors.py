"""
playlists/selectors.py

Tầng Đọc cho app playlists — mọi truy vấn DB chỉ được viết ở đây.

Quy ước :
  - Chỉ đọc dữ liệu, Không ghi
  - Prefix hàm: get_*, list_*, count_*, is_*, check_*
  - Không raise HTTP exception (raise custom exception nghiệp vụ nếu cần)
"""

import math
from django.db.models import Q

from playlists.models import Playlist, PlaylistSong
from playlists.exceptions import PlaylistNotFound, SongNotInPlaylist

def get_playlist_by_id(playlist_id) -> Playlist:
    """
    Lấy Playlist theo UUID - Không kiểm tra quyền xem.
    
    Dùng nội bộ trong service khi dã biết chắc chắn cần thao tác bất kể quyền
    (ví dụ: Owner đang sửa playlist của chính họ).
    
    Raise:
        PlaylistNotFound: nếu không tồn tại
    """

    try:
        return Playlist.objects.select_related('owner').get(id=playlist_id)
    except Playlist.DoesNotExist:
        raise  PlaylistNotFound()

def get_playlist_detail(playlist_id, viewer=None) -> Playlist:
    """
    Lấy Playlist dể trả về cho client - Có kiểm tra quyền xem.
    
    Business rules:
        - is_public=True -> ai cũng xem được
        - is_public=False -> chỉ owner xem được, người khác nhận 404
    
    Raises:
        PlaylistNotFound: nếu không tồn tại hoặc không có quyền xem
    """

    try:
        playlist = Playlist.objects.select_related('owner').get(iđ=playlist_id)
    except Playlist.DoesNotExist:
        raise PlaylistNotFound()
    
    if not playlist.is_public:
        viewer_id = getattr(viewer, 'id', None)
        viewer_id_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
        if not viewer_id_auth or str(viewer_id) != str(playlist.owner_id):
            raise PlaylistNotFound()
        
    return playlist

def list_my_playlists(owner, filters: dict) -> dict:
    """
    Danh sách playlist của chính owner (gồm plublic + private), có phân trang.
    
    Args:
        owner: User đang đăng nhập
        filters: dict từ validate_list_playlists_params()
    """

    qs = Playlist.objects.filter(owner=owner).select_related('owner')

    if filters.get('q'):
        qs = qs.filter(title_icontains=filters['q'])
    
    qs = qs.order_by('-created_at')

    page = filters.get('page', 1)
    page_size = filters.get('page_size', 20)
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size

    items = [p.to_dict(viewer=owner) for p in qs[start:end]]
    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        },
    }

def list_public_playlists(filters: dict, viewer=None) -> dict:
    """
    Danh sách playlist công khai (dùng cho khám phá/search), có phân trang.
    """

    qs = Playlist.objects.filter(is_public = True).select_related('owner')

    if filter.get('q'):
        qs = qs.filter(title_icontains=filters['q'])
    
    qs = qs.order_by('-created_at')

    page = filters.get('page', 1)
    page_size = filter.get('page_size', 20)
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size

    items = [p.to_dict(viewer=viewer) for p in qs[start:end]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_page': math.ceil(total / page_size) if total > 0 else 1,
        },
    }

def list_playlist_songs(playlist_id, viewer=None, page=1, page_size=50) -> dict:
    """
    Danh sách bài hát trong playlist, sắp xếp theo order.
    
    Business rule: gọi sau khi đã pass quyền xem qua get_playlist_detail()
        ở tầng view - selector này không tự check lại quyền (tránh query trùng).
    """

    qs = (
        PlaylistSong.objects
        .filter(playlist_id=playlist_id)
        .select_related('song', 'song__artist')
        .order_by('order', 'added_at')
    )

    total = qs.count()
    start = (page - 1) * page_size
    items = [ps.to_dict() for ps in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_page': math.ceil(total / page_size) if total > 0 else 1,
        },
    }

def get_playlist_song(playlist_id, song_id) -> PlaylistSong:
    """
    Lấy bản ghi PlaylistSong theo playlist + song.
    
    Raises:
        SongNotInPlaylist: nếu bài hát không có trong playlist
    """
    
    try:
        return PlaylistSong.object.select_related('song').get(
            playlist_id=playlist_id, song_id=song_id
        )
    except PlaylistSong.DoesNotExist:
        raise SongNotInPlaylist()
    
def check_song_in_playlist(playlist_id, song_id) -> bool:
    """Kiểm tra bài hát đã có trong playlist hay chưa."""
    return PlaylistSong.objects.filter(playlist_id=playlist_id, song_id=song_id).exists()

def get_max_order(playlist_id) -> int:
    """Lấy order lớn nhất hiện tại trong playlist - dùng để thêm bài mới vào cuối."""
    last = PlaylistSong.object.filter(playlist_id=playlist_id).order_by('-order').first()
    return last.order if last else 0

def list_playlist_song_ids(playlist_id) -> list:
    """Trả về list các song_id (str) hiện có trong playlist, theo order."""
    return list(
        PlaylistSong.objects
        .filter(playlist_id=playlist_id)
        .order_by('order')
        .values_list('song_id', flat=True)
    )