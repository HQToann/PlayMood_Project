import logging

from notifications.models import Notification
from notifications.exceptions import NotificationNotFound

logger = logging.getLogger(__name__)

#2 loại duy nhất được phép không có target thông báo hệ thống/kết quả xác thực
NO_TARGET_REQUIRED = {Notification.TYPE_SYSTEM, Notification.TYPE_VERIFY_RESULT}


"""
tạo 1 notification mới
- không tự thông báo cho chính mình (recipient == sender -> bỏ qua, trả None)
"""
def create_notification(recipient, notif_type: str,
                        message: str, sender=None, 
                        target_type: str=None,
                        target_id=None):
    
    if sender is not None and str(getattr(sender, 'id', sender)) == str(recipient.id):
        return None
    
    if notif_type not in NO_TARGET_REQUIRED and (not target_type or not target_id):
        raise ValueError(f'notify_type="{notif_type}" bắt buộc phsit có tarhet_type và target_id')
    
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notif_type=notif_type,
        target_type=target_type,
        target_id=target_id,
        message=message,
    )

    logger.info('Notification created: recipient=%s type=%s', recipient.username, notif_type)

    return notification


#đánh dấu 1 thông báo đã đọc chỉ chủ sở hữu
def mark_read(notification: Notification, user) -> Notification:
    if str(notification.recipient_id) != str(user.id):
        raise NotificationNotFound()
    
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    
    return notification

def mark_all_read(user) -> int:
    """Đánh dấu tất cả thông báo chưa đọc của user thành đã đọc. Trả số bản ghi bị ảnh hưởng."""
    updated = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return updated


#xoá 1 thông báo - chỉ chủ sở hữu
def delete_notification(notification: Notification, user) -> None:
    if str(notification.recipient_id) != str(user.id):
        raise NotificationNotFound()
    notification.delete()
    