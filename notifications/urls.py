from django.urls import path
from notifications.views import (
    NotificationListView,
    UnreadCountView,
    NotificationReadView,
    MarkAllReadView,
    NotificationDetailView,
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications-list'),
    path('unread-count/', UnreadCountView.as_view(), name='nontifications-unread-count'),
    path('read-all/', MarkAllReadView.as_view(), name='notifications-read-all'),
    path('<uuid:notification_id>/read/', NotificationReadView.as_view(), name='notifications-read'),
    path('<uuid:notification_id>/', NotificationDetailView.as_view(), name='notifications-detail'),
]
