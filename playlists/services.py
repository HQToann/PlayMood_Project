"""
playlists/services.py

Tầng ghi cho app playlists — mọi logic Create/Update/Delete.

Quy ước:
  - Xử lý toàn bộ business logic ghi dữ liệu
  - Không trả HTTP response
  - Có thể gọi selectors để đọc, nhưng selectors không gọi ngược lại services
  - Raise custom exception từ exceptions.py khi có lỗi nghiệp vụ
  - Tên hàm bắt đầu bằng động từ: create_, update_, delete_, add_, remove_, reorder_
"""

import logging

from django.db import transaction

from playlists.models import Playlist, PlaylistSong
from playlists.selectors import (
    get_max_order,
    check_song_in_playlist,
    get_playlist_song,
    list_playlist_song_ids
)
from playlists.exceptions import (
    NotPlaylistOwner,
    SongAlreadyInPlaylist,
    InvalidReorderData,
)
from music.selectors import get_song_by_id

logger = logging.getLogger(__name__)

# Playlist CRUD
def create_playlist(owner, data: dict) -> Playlist:
    """
    Tạo playlist mới.
    Args:
        owner: User tạo playlist (chủ sở hữu)
        data: dict đã validate từ validators.validate_playlist_create()
        
    Returns:
        Playlist mới đã được lưu vào DB
    """
    
    playlist = Playlist.objects.create(
        owner = owner,
        title = data['title'],
        description = data.get('description', ''),
        is_public = data.get('is_public', True),
    )
    logger.info('Playlist created: %s (owner=%s)', playlist.title, owner.username)
    return playlist

def update_playlist(playlist: Playlist, user, data: dict) -> Playlist:
    """
    Cập nhật thông tin playlist (title, description) - chỉ owner.
    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    for field, value in data.items():
        setattr(playlist, field, value)

    playlist.save(update_fields=list(data.keys()) + ['updated_at'])
    logger.info('Playlist updated; %s', playlist.title)
    return playlist

def update_cover_image(playlist: Playlist, user, cover_file) -> Playlist:
    """
    Cập nhật ảnh bìa playlist - chỉ owner.
    File được up lên Clou qua DEFAULT_FILE_STORAGE.
    Path: covers/playlists/<uuid>.<ext>
    
    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    # Xoá ảnh củ trên Cloud nếu có
    if playlist.cover_image:
        try:
            playlist.cover_image.delete(save=False)
        except Exception as e:
            logger.warning('Failed to delete old cover for playlist %s: %s', playlist.id, e)

    playlist.cover_image = cover_file
    playlist.save(update_fields=['cover_image', 'updated_at'])
    logger.info('Playlist cover updated: %s', playlist.title)
    return playlist

def update_visibility(playlist: Playlist, user, is_public: bool) -> Playlist:
    """
    Đặt playlist công khai / riêng tư - chỉ owner.
    Raise:
        NotPlaylistOwner: nếu user không plai owner
    """

    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    playlist.is_public = is_public
    playlist.save(update_fields=['is_public', 'updated_at'])
    logger.info('Playlist visibility updated: %s -> is_public=%s', playlist.title, is_public)
    return playlist

def delete_playlist(playlist: Playlist, user) -> None:
    """
    Xoá playlist công khai/riêng tư - owner.
    Raises:
        NotPlaylistOwner: nếu user không phải owner
    """
    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    title = playlist.title
    playlist.delete()
    logger.info('Playlist deleted: %s', title)

# Quản lý bài hát trong Playlist

def add_song_to_playlist(playlist: Playlist, user, song_id) -> PlaylistSong:
    """
    Thêm bài hát vào playlist - owner.
    Bài hát mới luôn được thêm vào cuối danh sách (order = max_order + 1).
    
    Raises:
        NotPlaylistOwner: nếu user không phải owner
        SongNotFound: nếu song_id không tồn tại
        SongAlreadyInPlaylist: nếu bài hát đã có trong playlist
    """

    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    # Xác nhận bài hát tồn tại
    song = get_song_by_id(song_id)

    if check_song_in_playlist(playlist.id, song.id):
        raise SongAlreadyInPlaylist()
    
    next_order = get_max_order(playlist.id) + 1

    playlist_song = PlaylistSong.objects.create(
        playlist = playlist,
        song = song,
        order = next_order,
    )
    logger.info('Song added to playlist: %s -> %s (#%s)', song.title, playlist.title, next_order)
    return playlist_song

def remove_song_from_playlist(playlist: Playlist, user, song_id) -> None:
    """
    Xoá bài hát khỏi playlist - owner
    
    Raises:
        NotPlaylistOwner: Nếu user không phải owner
        SongNotInPlaylist: nếu bài hát không có trong playlist
    """

    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    playlist_song = get_playlist_song(playlist.id, song_id)
    playlist_song.delete()
    logger.info('Song removed from playlist: %s', playlist.title)

@transaction.atomic
def reorder_playlist_songs(playlist: Playlist, user, song_ids: list) -> None:
    """
    Sắp xếp lại thứ tự bài hát trong playlist - owner.
    
    Business rule quan trọng:
        song_ids gửi lên phải khớp chính xác (cùng tập hợp) với các bài hát
            hiện có trong playlist - không thiếu, không dư, không có ID lạ
        Nếu không khớp -> InvalidReorderData
        
    Dùng @transaction.atomic để đảm bảo toàn bộ update order là 1 đơn vị —
        nếu có lỗi giữa chừng, rollback toàn bộ, không để playlist ở trạng thái thứ tự nửa cũ nửa mới.
    """

    if str(playlist.owner_id) != str(user.id):
        raise NotPlaylistOwner()
    
    current_ids = set(str(sid) for sid in list_playlist_song_ids(playlist.id))
    incoming_ids = set(str(sid) for sid in song_ids)

    if current_ids != incoming_ids:
        raise InvalidReorderData(
            'Danh sách song_ids phải khớp chính xác với các bài hát hiện có trong playlist'
        )
    
    # Cập nhật order theo đúng vị trí trong danh sách gửi lên
    playlist_songs = {
        str(ps.song_id): ps
        for ps in PlaylistSong.objects.filter(playlist=playlist)
    }
    for new_order, sid in enumerate(song_ids, start=1):
        ps = playlist_songs[str(sid)]
        ps.order = new_order

    PlaylistSong.objects.bulk_update(playlist_songs.values(), ['order'])
    logger.info('Playlist reordered: %s (%s songs)', playlist.title, len(song_ids))