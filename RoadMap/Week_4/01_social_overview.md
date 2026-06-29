# 01 — Tổng Quan App `social`

**Hệ thống Âm nhạc Django | Tuần 5: App `social` — Toàn bộ**

---

## 1. Phạm Vi Công Việc

Tuần 5 tập trung xây dựng hoàn chỉnh app `social` — lớp tương tác xã hội kết nối người dùng với nhau, biến hệ thống từ "nơi nghe nhạc cá nhân" thành "mạng xã hội âm nhạc" có khả năng theo dõi hoạt động của bạn bè.

### Vị trí trong tổng thể dự án

| App | Trạng thái |
|-----|-----------|
| `accounts` (Tuần 1) | Hoàn thành |
| `music` (Tuần 2) | Hoàn thành |
| `playlists` (Tuần 3) | Hoàn thành |
| `artists` (Tuần 4) | Hoàn thành |
| **`social` (Tuần 5)** | **Tuần này — 79 tests** |
| `notifications`, `search` | Chưa làm |

`social` phụ thuộc vào `User` (đã có), `Song` (đã có), và đặc biệt **tái sử dụng điểm tích hợp đã chuẩn bị sẵn từ Tuần 2** — hàm `record_play()` trong `music/services.py` đã gọi `create_friend_activity()` qua `try/except` từ trước, chỉ cần app `social` tồn tại đúng signature là cơ chế tự động kích hoạt mà không cần sửa lại code Tuần 2.

---

## 2. Các Module Trong App `social`

### 2.1 Follow — Theo dõi người dùng
- Toggle follow/unfollow giữa 2 user
- Danh sách followers/following, có phân trang
- Đếm số lượng followers/following công khai

### 2.2 Mood — Trạng thái tâm trạng
- Đặt trạng thái cảm xúc hiện tại, có thể đính kèm 1 bài hát đang nghe
- Tự động hết hạn sau một khoảng thời gian (`expires_at`)
- Cơ chế upsert — mỗi user chỉ có 1 Mood "đang hiển thị" tại một thời điểm

### 2.3 FriendActivity / Feed — Bảng tin hoạt động
- Ghi log mọi hoạt động đáng chú ý: nghe nhạc, follow, cập nhật mood
- Bảng tin (Feed) tổng hợp hoạt động của những người mình đang follow
- Tối ưu truy vấn nghiêm ngặt — không để xảy ra N+1 query

---

## 3. Mục Tiêu Nghiệp Vụ Cần Đạt

| # | Mục tiêu | Mô tả |
|---|----------|-------|
| 1 | Follow lẫn nhau | User có thể follow/unfollow người khác, không follow được bản thân |
| 2 | Mood kèm bài hát | User cập nhật trạng thái cảm xúc, tùy chọn gắn kèm bài hát đang nghe |
| 3 | Mood tự hết hạn | Mood có `expires_at`, hệ thống tự coi là không còn hiển thị sau khi hết hạn (không cần cronjob xóa ngay, tính `is_expired()` tại thời điểm đọc) |
| 4 | Feed tổng hợp | User xem được hoạt động mới nhất của tất cả người mình đang follow, sắp xếp theo thời gian |
| 5 | Tích hợp xuyên app | Khi user nghe nhạc (`music` app, Tuần 2) tự động sinh `FriendActivity` để hiện trên Feed — không cần sửa code Tuần 2 |
| 6 | Phân quyền Auth | Follow, đặt Mood, xem Feed cá nhân đều yêu cầu đăng nhập |
| 7 | Bảo mật & nhất quán Block Policy | Follow bị chặn nếu có quan hệ block (Fix R10); Feed/Mood/followers tự động ẩn nội dung của người đã block — đồng bộ với cách 4 app trước đã làm |
| 8 | Không N+1 query trên Feed | `list_feed()` phải dùng `select_related` để JOIN sẵn dữ liệu cần thiết, đảm bảo số lượng query ổn định bất kể Feed có bao nhiêu hoạt động |

---

## 4. Cấu Trúc Thư Mục App `social`

```
social/
├── __init__.py
├── apps.py
├── models.py          <- Follow, Mood, FriendActivity
├── exceptions.py      <- CannotFollowSelf, FollowTargetNotFound,
│                          BlockedFollowError, MoodNotFound
├── validators.py      <- validate_set_mood, validate_list_feed_params,
│                          validate_list_follow_params
├── selectors.py        <- is_following, list_followers/following,
│                          get_my_mood, get_user_mood,
│                          list_feed (trọng tâm tối ưu N+1), list_my_activities
├── services.py          <- toggle_follow, set_mood, delete_mood,
│                          create_friend_activity (hợp đồng với music app)
├── views.py            <- FollowToggleView, MyMoodView, FeedView...
├── urls.py             <- routes /api/v1/social/
├── admin.py
├── tests.py            <- 79 unit tests
└── migrations/
    └── 0001_initial.py
```

---

## 5. Dependency Giữa Các Tầng

```
HTTP Request
    |
views.py          <- nhan request, goi validator, goi service/selector, tra JSON
    |         |
validators.py   selectors.py / services.py
                    |
                 models.py  <-  DB (Follow, Mood, FriendActivity)
                    |
              music.models.Song (FK tuy chon tu Mood/FriendActivity)
              accounts.models.User (FK toi follower/following/user)
                    |
   <== music/services.py::record_play() GOI VAO social/services.py::create_friend_activity()
       (huong nguoc lai - tu Tuan 2 goi vao Tuan 5, qua try/except an toan)
```

**Quy tắc bất di bất dịch (giữ nguyên từ Tuần 1-4):**
- `views.py` **KHÔNG** import `Follow`, `Mood`, `FriendActivity`... trực tiếp để query
- `views.py` chỉ import từ `selectors.py`, `services.py`, `validators.py`, `exceptions.py`
- `selectors.py` chỉ đọc (SELECT), không ghi
- `services.py` chỉ ghi (INSERT/UPDATE/DELETE)

---

## 6. Điểm Kỹ Thuật Quan Trọng Cần Lưu Ý

| Vấn đề | Cách giải quyết |
|--------|-----------------|
| **Tích hợp ngược với app `music` (Tuần 2)** | `music/services.py::record_play()` đã gọi `from social.services import create_friend_activity` từ Tuần 2, bọc trong `try/except`. Signature `create_friend_activity(user, activity_type, song=None, extra_text='')` là **hợp đồng cố định** — không được đổi tên tham số, nếu không sẽ làm hỏng luồng ghi log lượt nghe |
| **Feed tránh N+1 query** | `list_feed()` dùng `select_related('user', 'song', 'song__artist')` để JOIN sẵn trong 1 query SQL — có test riêng (`test_feed_query_count_no_n_plus_1`) đo số lượng query thực tế bằng `CaptureQueriesContext`, đảm bảo không tăng theo số lượng activity |
| **Mood là OneToOneField** | Mỗi User chỉ có tối đa 1 Mood "đang hiển thị" — cập nhật Mood mới dùng `update_or_create()` (upsert), không tích lũy lịch sử Mood thành nhiều bản ghi rác |
| **Mood tự hết hạn không cần cronjob ngay** | `Mood.is_expired()` tính tại thời điểm đọc (`timezone.now() >= expires_at`) — `get_user_mood()` trả `None` nếu đã hết hạn, dữ liệu cũ vẫn còn trong DB nhưng coi như không tồn tại về mặt hiển thị. Việc dọn dẹp định kỳ (cronjob xóa Mood hết hạn) sẽ làm ở Tuần 7 |
| **Follow bị chặn 2 chiều theo Block Policy** | `toggle_follow()` gọi `is_blocked()` đã có từ `accounts/selectors.py` (Tuần 1) — nếu target đã block follower, follow bị raise `BlockedFollowError` (403), nhất quán với cách `music`/`playlists`/`artists` đã áp dụng Fix R10 |
| **Feed loại trừ cả 2 chiều** | Ngoài việc chỉ lấy hoạt động của người đang follow, `list_feed()` còn loại trừ hoạt động của bất kỳ ai đã **block** user hiện tại — đảm bảo tính nhất quán tuyệt đối với Block Policy toàn hệ thống |
| **Follow cũng sinh FriendActivity** | Khi A follow B thành công, hệ thống ghi 1 `FriendActivity` cho A (loại `liked`, dùng tạm cho hành động xã hội) — để follow cũng xuất hiện trên Feed của những người follow A |

---

## 7. Kế Hoạch Thực Thi (Đã Hoàn Thành & Verify)

```
[x] models.py        - Follow, Mood, FriendActivity voi to_dict()
[x] exceptions.py     - 4 custom exception
[x] validators.py     - 3 validator functions
[x] selectors.py      - 9 selector functions (trong tam: list_feed toi uu N+1)
[x] services.py       - 4 service functions (giu dung hop dong voi music app)
[x] views.py          - 8 View classes, 11 HTTP methods
[x] urls.py           - 8 endpoints
[x] admin.py          - Django Admin
[x] migrations        - 0001_initial.py da apply thanh cong
[x] tests.py          - 79 test cases, 100% PASS (bao gom test do N+1 query thuc te)
[x] Full regression   - 171/171 tests pass (accounts + music + playlists + artists + social)
[x] Integration test  - record_play() tu Tuan 2 da kich hoat dung create_friend_activity()
                        moi viet, khong sua lai bat ky dong nao trong music/services.py
```
