import logging
from accounts.models import User
from music.models import Song
from social.models import (
    Follow, 
    Mood, 
    FriendActivity,
)
from social.selectors import (
    is_following, 
    get_my_mood,
)
from social.exceptions import (
    CannotFollowSelf,
    FollowTargetNotFound,
    BlockedFollowError,
)
from accounts.exceptions import NotFound
from accounts.selectors import is_blocked


logger = logging.getLogger(__name__)


"""
toggle follow/unfollow
- không thể tự follow bản thân
- user bị target block không được follow
- target không tồn tại -> FollowTargetNotFound
- trả về dict gồm action ('followed'|'unfollowed') và
followers_count của target
"""
def toggle_follow(follower: User, following_id) -> dict:
    if str(follower.id) == str(following_id):
        raise CannotFollowSelf()
    try:
        following = User.objects.get(id=following_id, is_active=True)
    except User.DoesNotExist:
        raise FollowTargetNotFound()
    
    if is_blocked(viewer_id=follower.id, target_id=following.id):
        raise BlockedFollowError()
    
    follow_record, created = Follow.objects.get_or_create(follower=follower, following=following)

    if not created:
        follow_record.delete()
        action = 'unfollowed'
    else:
        action = 'followed'
    
    
    #Ghi FriendActivity không Block luồng chính nếu lỗi giống pattern record_play
    try: 
        create_friend_activity(user=follower, activity_type=FriendActivity.TYPE_LIKED, 
                             extra_text=f'Đã theo dõi {following.get_display_name()}')
    except Exception as e:
        logger.debug('FriendActivity log skipped on follow: %s', e)
    

    followers_count = Follow.objects.filter(following=following).count()
    return {
        'action': action,
        'followers_count': followers_count,
        'target_user_id': str(following_id)
    }



"""
Thiết lập cập nhật mood của user upsert (update_or_create)
- mỗi user chỉ có 1 mood đang hiển thị gọi lại sẽ thay đổi thẻ mood cũ
(không tạo bảo ghi mới riêng, không tích luỹ lịch sử mood)
- sau khi set, ghi 1 FriendActivity loại mood để hiển thị trên Feed
"""
def set_mood(user: User, data: dict) -> Mood:
    song = None
    if data.get('song_id'):
        try:
            song = Song.objects.get(id=data['song_id'])
        except Song.DoesNotExist:
            raise NotFound('Bài hát không tồn tại')
        
    mood, _created = Mood.objects.update_or_create(
        user=user,
        defaults={
            'status_text': data['status_text'],
            'song': song,
            'expires_at': data['expires_at'],
        },
    )

    try:
        create_friend_activity(
            user=user,
            activity_type=FriendActivity.TYPE_MOOD,
            song=song,
            extra_text=data['status_text'],
        )
    except Exception as e:
        logger.debug('FriendActivity log skipped on mood update: %s', e)

    logger.info('Mood updated: user=%s', user.username)

    return mood

def delete_mood(user: User) -> None:
    """Xoa Mood hien tai cua user."""
    Mood.objects.filter(user=user).delete()
    logger.info('Mood deleted: user=%s', user.username)


"""
tạo 1 bản ghi FriendActivity mới
- đây là entrypoint duy nhất được music/service.py::record_play()
signature này là hợp đồng giữa hai app, không đổi tên tham số nếu không muốn sửa lại cả music/service.py

tham số:
- user: User thực hiện hành động
- activity_type: 'playing' | 'liked' | 'mood' (Xem FriendActivity.TYPE_CHOICES)
- song: song liên quan (optinal, None cho mood không gắn bài hát)
- extra_text: nội dung bổ sung
"""
def create_friend_activity(user, activity_type: str, song=None, 
                           extra_text: str='') -> FriendActivity:
    activity = FriendActivity.objects.create(
        user=user,
        activity_type=activity_type,
        song=song,
        extra_text=extra_text,
    )

    return activity