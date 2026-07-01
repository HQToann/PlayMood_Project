"""
list_notifications() dùng select_related('sender') đề JOIN sẵn thông tin người gửi
trong 1 query SQL mỗi to_dict chỉ đụng vào self.sender (1 FK), không có vòng lặp query nào phát sinhtheem dù list
có bao nhiêu thông báo
"""

import math

from notifications.models import Notification
from notifications.exceptions import NotificationNotFound

def list_notifications(user, page=1, page_size=20, unread_only=False) -> dict:
    qs = Notification.objects.filter(recipient=user).select_related('sender')

    if unread_only:
        qs = qs.filter(is_read=False)

    qs = qs.order_by('-created_at')

    total = qs.count()
    start = (page - 1) * page_size
    items = [n.to_dict() for n in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_page': math.ceil(total / page_size) if total > 0 else 1,
        },
    } 


def count_unread(user) -> int:
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_notification_by_id(notification_id, user) -> Notification:
    """Lấy 1 thông báo - chỉ trả nếu thuộc về user (không lộ thông báo người khác)."""
    try:
        return Notification.objects.select_related('sender').get(id=notification_id, recipient=user)
    except Notification.DoesNotExist:
        raise NotificationNotFound()



