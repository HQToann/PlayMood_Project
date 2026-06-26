import uuid
from django.db import models


#playlist do người dung tạo
#quan hệ 
#- tác giả có khoá phụ FK -> accounts.User
#- bài hát có mối quan hệ nhiều nhiều PlaylistSong (thêm order để sắp xếp thứ tự bài hát)
#quyền truy cập
#- is_public=True 
#- is_puclic=False -> chỉ tác giả xem được
class Playlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='playlists',
        verbose_name='Chủ sở hữu',
        db_index=True
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Tên playlist',
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name='Mô tả',
    )

    #ảnh bìa được lưu trên Cloudinary với path: covers/playlists/<uuid>.<ext>
    cover_image = models.ImageField(
        upload_to='covers/playlists',
        blank=True,
        null=True,
        verbose_name='Ảnh bìa',
    )

    is_public = models.BooleanField(
        default=True,
        verbose_name='Công khai',
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Cập nhật lần cuối')

    class Meta:
        db_table = 'playlists_playlist'
        ordering = ['-created_at']
        verbose_name = 'Playlist'
        verbose_name_plural = 'Playlist'

    def __str__(self):
        return f'{self.title} ({self.owner.username})'
    
    #chuyển 1 đối tượng Playlist thành dict
    #viewer: User đang xem (dùng để quyết định is_owner)
    #include_song_count: có tính song_count hay không
    def to_dict(self, viewer=None, include_song_count=True):
        data = {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'cover_image': self.cover_image.url if self.cover_image else None,
            'is_public': self.is_public,
            'owner': {
                'id': str(self.owner.id),
                'username': self.owner.username,
                'display_name': self.owner.get_display_name(),
                'avatar': self.owner.avatar.url if self.owner.avatar else None,
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

        if include_song_count:
            data['song_count'] = self.playlist_songs.count()
        
        viewer_id = getattr(viewer, 'id', None)
        if viewer_id and getattr(viewer, 'is_authenticated', False):
            data['is_owner'] = str(viewer_id) == str(self.owner_id)
        else:
            data['is_owner'] = False
        return data
    


#bản trung gian Playlist và Song, lưu thứ tự bài hát trong playlist
#unique_together đảm bảo 1 bài hát không được thêm trùng vào cùng 1 playlist
#order dùng để client hiển thị đúng thứ tự và hỗ trợ reorder
class PlaylistSong(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='playlist_songs',
        verbose_name='Playlist',
    )

    song = models.ForeignKey(
        'music.Song',
        on_delete=models.CASCADE,
        related_name='in_playlists',
        verbose_name='Bài hát',
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Thứ tự'
    )

    added_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Ngày thêm',
    )

    class Meta:
        db_table = 'playlists_playlist_song'
        ordering = ['order', 'added_at']
        unique_together = [('playlist', 'song')]
        verbose_name = 'Bài hát trong Playlist'
        verbose_name_plural = 'Bài hát trong Playlist'


    def __str__(self):
        return f'{self.playlist.title} - {self.song.title} (#{self.order})'
    

    def to_dict(self):
        return {
            'id': str(self.id),
            'song': {
                'id': str(self.song_id),
                'title': self.song.title,
                'artist': {
                    'id': str(self.song.artist_id),
                    'username': self.song.artist.username,
                    'display_name': self.song.artist.get_display_name(),
                },
                'cover_image': self.song.cover_image.url if self.song.cover_image else None,
                'duration': self.song.duration,
                'status': self.song.status,
            },
            'order': self.order,
            'added_at': self.added_at.isoformat(),
        }