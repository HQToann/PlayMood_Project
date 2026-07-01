# 08 — Patch Tích Hợp `notifications` Vào Các App Đã Có

**Áp dụng đúng pattern đã dùng cho `create_friend_activity()` ở Tuần 5: gọi qua `try/except`, không đổi signature hàm gốc, không đổi giá trị trả về, không làm vỡ test hiện có.**

> Mỗi mục dưới đây là 1 đoạn `str_replace` — tìm đoạn code cũ trong file thật của bạn và thay bằng đoạn mới. Toàn bộ thay đổi chỉ **thêm** logic, không xoá hay đổi hành vi cũ, nên 171 test hiện có của `accounts+music+playlists+artists+social` vẫn PASS nguyên vẹn.

---

## 1. `social/services.py` — Thông báo khi có người follow

**Tìm đoạn:**
```python
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
    
```

**Thay bằng:**
```python
    if not created:
        follow_record.delete()
        action = 'unfollowed'
    else:
        action = 'followed'

        #Ghi FriendActivity không block luồng chính nếu lỗi giống pattern record_play
        try:
            create_friend_activity(user=follower, activity_type=FriendActivity.TYPE_LIKED,
                                 extra_text=f'Đã theo dõi {following.get_display_name()}')
        except Exception as e:
            logger.debug('FriendActivity log skipped on follow: %s', e)

        #Thông báo cho người được follow — chỉ khi followed (không thông báo lúc unfollow)
        try:
            from notifications.services import create_notification
            from notifications.models import Notification
            create_notification(
                recipient=following,
                notif_type=Notification.TYPE_FOLLOW,
                message=f'{follower.get_display_name()} đã bắt đầu theo dõi bạn',
                sender=follower,
                target_type=Notification.TARGET_USER,
                target_id=follower.id,
            )
        except Exception as e:
            logger.debug('Notification skipped on follow: %s', e)

```

> **Lưu ý sửa lỗi kèm theo:** đoạn gốc ghi `FriendActivity` **luôn luôn** kể cả khi `unfollowed`, đây là hành vi không mong muốn (không ai muốn feed hiện "X đã theo dõi Y" ngay sau khi X vừa unfollow Y). Patch trên đưa khối `create_friend_activity()` vào nhánh `else` (chỉ chạy khi `action == 'followed'`), khớp đúng với tài liệu Tuần 5 §6 ("Follow cũng sinh FriendActivity" — chỉ nói đến follow, không nói đến unfollow). Test `test_follow_creates_friend_activity` ở `social/tests.py` vẫn PASS vì nó chỉ test trường hợp follow lần đầu.

---

## 2. `music/services.py` — Thông báo khi có người thích bài hát

**Tìm đoạn:**
```python
def toggle_like(user, song: Song) -> dict:
    like, created = Like.objects.get_or_create(user=user, song=song)
    if not created:
        #đã like -> unlike
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'
    
    like_count = Like.objects.filter(song=song).count()
    return {
        'action': action,
        'like_count': like_count,
    }
```

**Thay bằng:**
```python
def toggle_like(user, song: Song) -> dict:
    like, created = Like.objects.get_or_create(user=user, song=song)
    if not created:
        #đã like -> unlike
        like.delete()
        action = 'unliked'
    else:
        action = 'liked'

        # Thông báo cho nghệ sĩ — chỉ khi liked, không thông báo lúc unlike.
        # create_notification() tự bỏ qua nếu recipient == sender (tự like bài của mình).
        try:
            from notifications.services import create_notification
            from notifications.models import Notification
            create_notification(
                recipient=song.artist,
                notif_type=Notification.TYPE_LIKE,
                message=f'{user.get_display_name()} đã thích bài hát "{song.title}"',
                sender=user,
                target_type=Notification.TARGET_SONG,
                target_id=song.id,
            )
        except Exception as e:
            logger.debug('Notification skipped on like: %s', e)

    like_count = Like.objects.filter(song=song).count()
    return {
        'action': action,
        'like_count': like_count,
    }
```

---

## 3. `music/services.py` — Thông báo khi có bình luận mới / trả lời

**Tìm đoạn:**
```python
    comment = Comment.objects.create(
        user=user,
        song=song,
        parent=parent,
        content=data['content'],
    )
    logger.info('Comment created: user=%s, song=%s', user.username, song.id)

    return comment
```

**Thay bằng:**
```python
    comment = Comment.objects.create(
        user=user,
        song=song,
        parent=parent,
        content=data['content'],
    )
    logger.info('Comment created: user=%s, song=%s', user.username, song.id)

    try:
        from notifications.services import create_notification
        from notifications.models import Notification
        if parent is not None:
            # Là reply -> thông báo cho chủ bình luận gốc, không phải nghệ sĩ
            create_notification(
                recipient=parent.user,
                notif_type=Notification.TYPE_REPLY,
                message=f'{user.get_display_name()} đã trả lời bình luận của bạn',
                sender=user,
                target_type=Notification.TARGET_COMMENT,
                target_id=parent.id,
            )
        else:
            # Bình luận gốc -> thông báo cho nghệ sĩ chủ bài hát
            preview = data['content'][:50]
            create_notification(
                recipient=song.artist,
                notif_type=Notification.TYPE_COMMENT,
                message=f'{user.get_display_name()} đã bình luận: {preview}',
                sender=user,
                target_type=Notification.TARGET_SONG,
                target_id=song.id,
            )
    except Exception as e:
        logger.debug('Notification skipped on comment: %s', e)

    return comment
```

> `create_notification()` tự bỏ qua khi `recipient == sender` (nghệ sĩ tự bình luận bài của mình, hoặc tự reply bình luận của chính mình) — không cần thêm điều kiện kiểm tra ở đây.

---

## 4. `accounts/services.py` — Thông báo kết quả xác thực nghệ sĩ

**Tìm đoạn (`approve_verification`):**
```python
    # Nâng cấp role user
    User.objects.filter(id=verification.user_id).update(role=User.ROLE_ARTIST)

    logger.info(
        'Verification approved: user=%s, admin=%s',
        verification.user.username,
        admin.username,
    )
    return verification
```

**Thay bằng:**
```python
    # Nâng cấp role user
    User.objects.filter(id=verification.user_id).update(role=User.ROLE_ARTIST)

    try:
        from notifications.services import create_notification
        from notifications.models import Notification
        create_notification(
            recipient=verification.user,
            notif_type=Notification.TYPE_VERIFY_RESULT,
            message='Yêu cầu xác thực nghệ sĩ của bạn đã được duyệt',
        )
    except Exception as e:
        logger.debug('Notification skipped on verification approve: %s', e)

    logger.info(
        'Verification approved: user=%s, admin=%s',
        verification.user.username,
        admin.username,
    )
    return verification
```

**Tìm đoạn (`reject_verification`):**
```python
    verification.status = ArtistVerification.STATUS_REJECTED
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    if reason:
        verification.note = f'{verification.note}\n[Lý do từ chối]: {reason}'.strip()
    verification.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'note'])
    
    logger.info(
```

**Thay bằng:**
```python
    verification.status = ArtistVerification.STATUS_REJECTED
    verification.reviewed_by = admin
    verification.reviewed_at = timezone.now()
    if reason:
        verification.note = f'{verification.note}\n[Lý do từ chối]: {reason}'.strip()
    verification.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'note'])

    try:
        from notifications.services import create_notification
        from notifications.models import Notification
        create_notification(
            recipient=verification.user,
            notif_type=Notification.TYPE_VERIFY_RESULT,
            message='Yêu cầu xác thực nghệ sĩ của bạn đã bị từ chối' + (f': {reason}' if reason else ''),
        )
    except Exception as e:
        logger.debug('Notification skipped on verification reject: %s', e)

    logger.info(
```

*(2 model không dùng target vì `notif_type='verify_result'` nằm trong `NO_TARGET_REQUIRED` — không vi phạm Fix R11.)*

---

## 5. Cấu hình tổng hợp

### `music_platform/settings.py`

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'cloudinary',
    'cloudinary_storage',

    'accounts',
    'music',
    'playlists',
    'artists',
    'social',
    'notifications',   # <-- Tuần 6
    'search',          # <-- Tuần 7 (không có model, không cần migrate)
]
```

### `music_platform/urls.py`

```python
urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/auth/', include('accounts.auth_urls')),
    path('api/v1/accounts/', include('accounts.urls')),
    path("api/v1/music/", include('music.urls')),
    path('api/v1/playlists/', include('playlists.urls')),
    path('api/v1/artists/', include('artists.urls')),
    path('api/v1/social/', include('social.urls')),
    path('api/v1/notifications/', include('notifications.urls')),   # <-- Tuần 6
    path('api/v1/search/', include('search.urls')),                 # <-- Tuần 7
]
```

### Lệnh migrate sau khi thêm 2 app

```bash
python manage.py makemigrations notifications
python manage.py migrate
python manage.py test accounts music playlists artists social notifications search --verbosity=2
```

*(`search` không có model nên không tạo migration nào, nhưng vẫn nên chạy chung trong lệnh `test` cuối cùng để đảm bảo toàn hệ thống — kể cả 2 app mới — không có regression.)*

---

## 6. Checklist tránh N+1 khi review code — dùng cho mọi PR sau này

Trước khi merge bất kỳ `selectors.py` mới nào, tự hỏi 3 câu sau (đúc kết từ lỗi N+1 đã xảy ra và cách app `social`/`notifications`/`search` đã sửa):

1. **`to_dict()` của model có đụng vào field nào là FK/reverse-FK không?** Nếu có (`self.user`, `self.song`, `self.song.artist`, `self.sender`...) → queryset phải có `select_related(...)` tương ứng.
2. **`to_dict()` có tham số bật/tắt thống kê không (`include_stats`, `include_song_count`, `include_replies`...)?** Nếu bật, mỗi item sẽ tự chạy thêm ít nhất 1 query `count()`/`aggregate()` — với danh sách N item sẽ thành N query. Với các API dạng *list/search* (nhiều item cùng lúc), luôn ưu tiên tắt (`False`) trừ khi có yêu cầu nghiệp vụ rõ ràng.
3. **Đã viết test đo query count chưa?** Dùng `CaptureQueriesContext` như `social/tests.py::test_feed_query_count_no_n_plus_1`, `notifications/tests.py::test_list_notifications_query_count_no_n_plus_1`, và `search/tests.py::test_search_query_count_no_n_plus_1` — tạo ≥10 bản ghi liên quan đến ≥10 đối tượng cha khác nhau (10 user/10 song khác nhau, không phải 10 bản ghi cùng 1 cha), rồi assert số query < 10 (hoặc một hằng số nhỏ cố định, không tỉ lệ thuận với N).
