from accounts.exceptions import ValidationError
from music.models import Song, Album
from playlists.models import Playlist
from posts.models import Post

def validate_message_content(content: str, image_url: str, shared_song_id: str = None, shared_album_id: str = None, shared_playlist_id: str = None, shared_post_id: str = None):
    """
    Kiểm tra tính hợp lệ của tin nhắn:
    Phải có ít nhất 1 trong thứ: text, hình ảnh, bài hát, album, playlist, post.
    """
    if not content and not image_url and not shared_song_id and not shared_album_id and not shared_playlist_id and not shared_post_id:
        raise ValidationError(
            'Tin nhắn không hợp lệ', 
            fields={'content': ['Tin nhắn phải có nội dung chữ, ảnh hoặc đính kèm']}
        )
    
    if shared_song_id:
        if not Song.objects.filter(id=shared_song_id).exists():
            raise ValidationError(
                'Bài hát không hợp lệ',
                fields={'shared_song_id': ['Bài hát đính kèm không tồn tại hoặc đã bị xoá']}
            )
            
    if shared_album_id:
        if not Album.objects.filter(id=shared_album_id).exists():
            raise ValidationError(
                'Album không hợp lệ',
                fields={'shared_album_id': ['Album đính kèm không tồn tại hoặc đã bị xoá']}
            )
            
    if shared_playlist_id:
        if not Playlist.objects.filter(id=shared_playlist_id).exists():
            raise ValidationError(
                'Playlist không hợp lệ',
                fields={'shared_playlist_id': ['Playlist đính kèm không tồn tại hoặc đã bị xoá']}
            )
            
    if shared_post_id:
        if not Post.objects.filter(id=shared_post_id).exists():
            raise ValidationError(
                'Bài viết không hợp lệ',
                fields={'shared_post_id': ['Bài viết đính kèm không tồn tại hoặc đã bị xoá']}
            )