"""
artists/service.py

Tăng ghi cho app artists - mỗi logic CRUD ở đây
Quy ước:
    - Xử lý toàn bộ business logic ghi dữ liệu
    - Không trả HTTP response
    - Có thể gọi selectors để đọc, nhưng selectors không gọi ngược lại
    - Raises custom exception từ exceptions.py khi có lỗi nghiệp vụ
"""

import logging

from artists.models import ArtistProfile
from artists.selectors import check_profile_exists, get_artist_profile_by_user_id
from artists.exceptions import ArtistProfileAlreadyExists, NotArtistProfileOwner, UserNotArtist

logger = logging.getLogger(__name__)

def create_artist_profile(user, data: dict) -> ArtistProfile:
    """
    Tạo hồ sơ nghệ sĩ cho mỗi user.
    Business rules:
        - User phải có role='artist'
        - Mỗi user chỉ tạo được 1 ArtistProfile
    Raises:
        UserNotArtist: nếu user không có role='artist'
        ArtistProfileAlreadyExists: nếu user đã có profile
    """
    if user.role != 'artist':
        raise UserNotArtist()
    
    if check_profile_exists(user.id):
        raise ArtistProfileAlreadyExists()
    
    profile = ArtistProfile.objects.create(
        user=user,
        stage_name=data.get('stage_name', ''),
        bio=data.get('bio', ''),
        website_url=data.get('website_url', ''),
        facebook_url=data.get('facebook_url', ''),
        youtube_url=data.get('youtube_url', ''),
    )
    logger.info('ArtistProfile created: user=%s', user.username)
    return profile

def update_artist_profile(profile: ArtistProfile, user, data: dict) -> ArtistProfile:
    """
    Cập nhật hồ sơ nghệ sĩ - chỉ owner
    Raises:
        NotArtistProfileOwner: nếu user không phải chủ hồ sơ
    """
    if str(profile.user_id) != str(user.id):
        raise NotArtistProfileOwner()
    
    for field, value in data.items():
        setattr(profile, field, value)

    profile.save(update_fields=list(data.keys()) + ['updated_at'])
    logger.info('ArtistProfile updated: user=%s', profile.user.username)

def update_cover_image(profile: ArtistProfile, user, cover_file) -> ArtistProfile:
    """
    Cập nhật ảnh bìa nghệ sĩ - chỉ owner.
    File upload thẳng lên Cloud
    Path: cover/artists/<uuid>.<ext>
    Raises:
        NotArtistProfileOwner: nếu user không phải chủ hồ sơ
    """
    if str(profile.user_id) != str(user.id):
        raise NotArtistProfileOwner()
    
    # Xoá ảnh bìa củ
    if profile.cover_image:
        try:
            profile.cover_image.delete(save=False)
        except Exception as e:
            logger.warning('Failed to delete old cover for artist %s: %s', profile.user_id, e)
    
    profile.cover_image = cover_file
    profile.save(update_fields=['cover_image', 'updates_at'])
    logger.info('ArtistProfile cover updates: user=%s', profile.user.username)
    return profile

def get_or_create_my_profile(user) -> ArtistProfile:
    """
    Lấy ArtistProfile của chính user đang đăng nhập, tự động tạo rỗng nếu chưa có.
    Dùng cho endpoint GET/me/ của artist - tránh bắt artist phải gọi POST
        trước khi xem được trang cá nhân của chính họ
        
    Raises:
        UserNotArtist: nếu không có role='artist'
    """
    if user.role != 'artist':
        raise UserNotArtist()
    
    if check_profile_exists(user.id):
        return get_artist_profile_by_user_id(user.id)
    
    profile = ArtistProfile.objects.create(user=user)
    logger.info('ArtistProfile auto-created on first access: user=%s', user.username)
    return profile