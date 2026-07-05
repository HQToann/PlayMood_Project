import logging
from accounts.models import User
from music.models import Song
from social.models import Follow, FollowRequest, Mood, FriendActivity
from social.selectors import is_following, get_my_mood
from social.exceptions import CannotFollowSelf, FollowTargetNotFound, BlockedFollowError
from accounts.exceptions import NotFound
from accounts.selectors import is_blocked

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# FOLLOW / FRIEND REQUEST
# ─────────────────────────────────────────────

def toggle_follow(follower: User, following_id) -> dict:
    """
    Điều phối logic follow theo role của TARGET:
    - TARGET là Artist  → Follow 1 chiều ngay lập tức (TikTok style). Gửi notification 'follow'.
    - TARGET là User    → Gửi FollowRequest (chờ duyệt). Gửi notification 'follow_request'.
      Nếu đã gửi yêu cầu rồi → Hủy yêu cầu (cancel).
      Nếu đã là bạn bè rồi   → Hủy follow (unfollow cả 2 chiều).
    """
    if str(follower.id) == str(following_id):
        raise CannotFollowSelf()
    try:
        following = User.objects.get(id=following_id, is_active=True)
    except User.DoesNotExist:
        raise FollowTargetNotFound()

    if is_blocked(viewer_id=follower.id, target_id=following.id):
        raise BlockedFollowError()

    # ── Trường hợp TARGET là Nghệ sĩ: Follow 1 chiều ──────────────────────
    if following.role == User.ROLE_ARTIST:
        follow_obj, created = Follow.objects.get_or_create(
            follower=follower, following=following
        )
        if not created:
            follow_obj.delete()
            # Xóa cả chiều ngược lại (nếu có) để hủy hoàn toàn kết bạn
            Follow.objects.filter(follower=following, following=follower).delete()
            action = 'unfollowed'
        else:
            action = 'followed'
            # Gửi thông báo "X đã theo dõi bạn"
            _send_follow_notification(sender=follower, recipient=following)

    # ── Trường hợp TARGET là Người dùng thường: Follow Request ─────────────
    else:
        already_following = Follow.objects.filter(
            follower=follower, following=following
        ).exists()

        if already_following:
            # Hủy kết bạn (xóa cả 2 chiều)
            Follow.objects.filter(follower=follower, following=following).delete()
            Follow.objects.filter(follower=following, following=follower).delete()
            action = 'unfollowed'
        else:
            # Toggle Follow Request
            req_obj, req_created = FollowRequest.objects.get_or_create(
                sender=follower, receiver=following
            )
            if not req_created:
                req_obj.delete()
                action = 'request_cancelled'
                _delete_follow_request_notification(sender=follower, recipient=following)
            else:
                action = 'request_sent'
                # Gửi thông báo "X muốn kết bạn với bạn"
                _send_follow_request_notification(
                    sender=follower, recipient=following, request_id=req_obj.id
                )

    followers_count = Follow.objects.filter(following=following).count()
    return {
        'action': action,
        'followers_count': followers_count,
        'target_user_id': str(following_id),
        'is_following': Follow.objects.filter(follower=follower, following=following).exists(),
    }


def accept_follow_request(receiver: User, request_id: str) -> None:
    """
    Chấp nhận yêu cầu kết bạn:
    - Tạo Follow sender -> receiver (sender được theo dõi receiver)
    - Tạo Follow receiver -> sender (receiver follow ngược lại = thành bạn bè 2 chiều)
    - Xóa FollowRequest
    - Ghi FriendActivity
    """
    try:
        req = FollowRequest.objects.select_related('sender', 'receiver').get(
            id=request_id, receiver=receiver
        )
    except FollowRequest.DoesNotExist:
        raise NotFound("Yêu cầu kết bạn không tồn tại hoặc đã được xử lý.")

    sender = req.sender
    # Tạo follow 2 chiều
    Follow.objects.get_or_create(follower=sender, following=receiver)
    Follow.objects.get_or_create(follower=receiver, following=sender)
    req.delete()

    # Ghi activity
    try:
        create_friend_activity(
            user=receiver, activity_type=FriendActivity.TYPE_LIKED,
            extra_text=f'Đã kết bạn với {sender.get_display_name()}'
        )
    except Exception as e:
        logger.debug('FriendActivity log skipped on accept: %s', e)


def reject_follow_request(receiver: User, request_id: str) -> None:
    """Từ chối yêu cầu kết bạn (xóa FollowRequest)."""
    try:
        req = FollowRequest.objects.get(id=request_id, receiver=receiver)
        req.delete()
    except FollowRequest.DoesNotExist:
        raise NotFound("Yêu cầu kết bạn không tồn tại hoặc đã được xử lý.")


def cancel_follow_request(sender: User, request_id: str) -> None:
    """Hủy yêu cầu kết bạn đã gửi (do chính người gửi hủy)."""
    try:
        req = FollowRequest.objects.get(id=request_id, sender=sender)
        req.delete()
    except FollowRequest.DoesNotExist:
        raise NotFound("Yêu cầu kết bạn không tồn tại hoặc đã được xử lý.")


# ─────────────────────────────────────────────
# NOTIFICATION HELPERS (nội bộ, không gọi từ ngoài)
# ─────────────────────────────────────────────

def _send_follow_notification(sender: User, recipient: User):
    """Gửi thông báo 'X đã theo dõi bạn' (dùng cho follow 1 chiều - Artist)."""
    try:
        from notifications.models import Notification
        from notifications.services import create_notification
        create_notification(
            recipient=recipient,
            sender=sender,
            notif_type=Notification.TYPE_FOLLOW,
            message=f'{sender.get_display_name()} đã bắt đầu theo dõi bạn.',
            target_type='user',
            target_id=sender.id,
        )
    except Exception as e:
        logger.debug('Notification skipped on follow: %s', e)


def _send_follow_request_notification(sender: User, recipient: User, request_id):
    """Gửi thông báo 'X muốn kết bạn với bạn' (dùng cho follow request)."""
    try:
        from notifications.models import Notification
        from notifications.services import create_notification
        create_notification(
            recipient=recipient,
            sender=sender,
            notif_type=Notification.TYPE_FOLLOW_REQUEST,
            message=f'{sender.get_display_name()} muốn kết bạn với bạn.',
            target_type='user',
            target_id=sender.id,
        )
    except Exception as e:
        logger.debug('Notification skipped on follow request: %s', e)


def _delete_follow_request_notification(sender: User, recipient: User):
    """Xóa thông báo yêu cầu kết bạn khi người gửi hủy yêu cầu."""
    try:
        from notifications.models import Notification
        Notification.objects.filter(
            recipient=recipient,
            sender=sender,
            notif_type=Notification.TYPE_FOLLOW_REQUEST
        ).delete()
    except Exception as e:
        logger.debug('Failed to delete follow request notification: %s', e)


# ─────────────────────────────────────────────
# MOOD
# ─────────────────────────────────────────────

def set_mood(user: User, data: dict) -> Mood:
    """
    Upsert Mood của user. Sau khi set, ghi 1 FriendActivity loại mood.
    """
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
    """Xóa Mood hiện tại của user."""
    Mood.objects.filter(user=user).delete()
    logger.info('Mood deleted: user=%s', user.username)


# ─────────────────────────────────────────────
# FRIEND ACTIVITY
# ─────────────────────────────────────────────

def create_friend_activity(user, activity_type: str, song=None,
                           extra_text: str = '') -> FriendActivity:
    """
    Tạo 1 bản ghi FriendActivity mới.
    Entrypoint duy nhất được music/services.py::record_play() gọi.
    Không đổi tên tham số nếu không muốn sửa lại music/services.py.
    """
    activity = FriendActivity.objects.create(
        user=user,
        activity_type=activity_type,
        song=song,
        extra_text=extra_text,
    )
    return activity