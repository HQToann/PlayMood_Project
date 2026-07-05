# FRONTEND DESIGN PROMPT — Music Platform
**Nền tảng âm nhạc xã hội | Phong cách: Pastel Minimalist**

---

## 🎨 DESIGN SYSTEM — Bắt buộc áp dụng xuyên suốt

### Palette màu sắc (Pastel Minimalist)
```
--color-bg:           #FAF8F5   /* Nền chính — trắng ấm, không lạnh */
--color-surface:      #FFFFFF   /* Card, modal, panel */
--color-surface-2:    #F3EFF8   /* Nền phụ — tím pastel rất nhạt */
--color-border:       #EAE5F0   /* Viền nhẹ */

--color-primary:      #B39DDB   /* Tím lavender pastel — màu chủ đạo */
--color-primary-soft: #EDE7F6   /* Tím rất nhạt, hover/highlight */
--color-accent:       #F48FB1   /* Hồng peach pastel — accent */
--color-accent-soft:  #FCE4EC   /* Hồng rất nhạt */

--color-teal:         #80CBC4   /* Xanh teal pastel — trạng thái active */
--color-teal-soft:    #E0F2F1

--color-text-primary: #3D3552   /* Tím than — text chính */
--color-text-secondary: #7B6E8E /* Text phụ */
--color-text-muted:   #B0A8C0   /* Placeholder, caption */

--color-success:      #A5D6A7
--color-warning:      #FFE082
--color-error:        #EF9A9A

/* Player / Active */
--color-player-bg:    #2D2540   /* Nền player — tối, tương phản */
--color-player-text:  #F5F0FF
```

### Typography
```
Font chính (Display):  "Plus Jakarta Sans", sans-serif  → Tiêu đề, tên bài hát
Font phụ (Body):       "Inter", sans-serif               → Nội dung, UI
Font mono (Data):      "JetBrains Mono", monospace       → Counter, badge số

Scale:
  --text-xs:    11px / 1.4
  --text-sm:    13px / 1.5
  --text-base:  15px / 1.6
  --text-md:    17px / 1.5
  --text-lg:    21px / 1.4
  --text-xl:    28px / 1.3
  --text-2xl:   38px / 1.2
  --text-3xl:   52px / 1.1
```

### Spacing & Radius
```
Spacing scale: 4px base (4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96)

Border radius:
  --radius-sm:  6px    (chip, badge, input)
  --radius-md:  12px   (card nhỏ)
  --radius-lg:  20px   (card lớn, modal)
  --radius-xl:  32px   (card hero)
  --radius-pill: 9999px (button, tag)
```

### Shadows (nhẹ nhàng — không harsh)
```
--shadow-xs:  0 1px 2px rgba(61,53,82,0.04)
--shadow-sm:  0 2px 8px rgba(61,53,82,0.07)
--shadow-md:  0 4px 20px rgba(61,53,82,0.10)
--shadow-lg:  0 8px 40px rgba(61,53,82,0.14)
--shadow-player: 0 -4px 32px rgba(45,37,64,0.25)
```

### Motion
```
--duration-fast:   120ms ease-out
--duration-base:   200ms ease-out
--duration-slow:   350ms cubic-bezier(0.34,1.56,0.64,1)  ← spring cho modal/card
```

---

## 🗂️ LAYOUT TỔNG THỂ

### Cấu trúc Shell (Desktop ≥ 1024px)
```
┌─────────────────────────────────────────────────────────┐
│ HEADER (64px fixed top)                                 │
│  Logo | Search bar | Nav icons | Avatar                 │
├───────────────┬─────────────────────────────────────────┤
│ SIDEBAR LEFT  │ MAIN CONTENT                            │
│ (240px fixed) │ (flex-1, overflow-y scroll)             │
│               │                                         │
│  Navigation   │  <Page content here>                    │
│  Library      │                                         │
│               │                                         │
└───────────────┴─────────────────────────────────────────┤
│ PLAYER BAR (80px fixed bottom)                          │
│  Album art | Track info | Controls | Volume | Queue     │
└─────────────────────────────────────────────────────────┘
```

### Mobile (< 768px)
```
┌───────────────────────────┐
│ HEADER (56px)             │
│ Logo        Search  Avatar│
├───────────────────────────┤
│ MAIN CONTENT              │
│ (scroll)                  │
│                           │
├───────────────────────────┤
│ PLAYER BAR (72px)         │
│ Art | Info | Controls     │
├───────────────────────────┤
│ BOTTOM NAV (56px)         │
│ Home Feed Search Library  │
└───────────────────────────┘
```

---

## 📄 CHI TIẾT TỪNG TRANG / COMPONENT

---

### 1. AUTH PAGES (Không có sidebar, không có player)

**Stack:** 2 cột — trái: hình ảnh/branding, phải: form

**[TRANG ĐĂNG KÝ — `/register`]**
```
API: POST /api/v1/auth/register/
Body: { email, username, password, password_confirm }
Response 201: { user: {...}, message }
Response 400: { errors: { field: [...] } }

Fields:
- email (text, required)
- username (text, required, 3-30 ký tự, chỉ a-z0-9_)
- password (password, min 8 ký tự, phải có chữ hoa + số)
- password_confirm (password)

UI Flow:
1. Submit → show loading spinner trên button
2. 201 → auto login → redirect /home
3. 400 → highlight field lỗi với border --color-error + message

Link phụ: "Đã có tài khoản? Đăng nhập"
```

**[TRANG ĐĂNG NHẬP — `/login`]**
```
API: POST /api/v1/auth/login/
Body: { email, password }
Response 200: { user: {...} }
Response 400/401: { message }

Lấy CSRF trước: GET /api/v1/auth/csrf/

Fields:
- email (text)
- password (password, có nút show/hide)
- Checkbox "Ghi nhớ đăng nhập"

Link phụ: "Quên mật khẩu?" → /forgot-password
Link phụ: "Chưa có tài khoản? Đăng ký"
```

**[TRANG QUÊN MẬT KHẨU — `/forgot-password`]**
```
Step 1 — Nhập email:
  API: POST /api/v1/auth/password/reset/request/
  Body: { email }
  → Show success message (dù email có tồn tại hay không, để tránh enumeration)

Step 2 — Nhập mật khẩu mới (từ link email):
  Route: /reset-password?token=xxx
  API: POST /api/v1/auth/password/reset/confirm/
  Body: { token, new_password, new_password_confirm }
  → Redirect /login khi thành công
```

---

### 2. HOME — `/home`

**Layout:** Full width content, không có sidebar focus

**Sections (scroll dọc):**

**Section A — Trending Songs**
```
API: GET /api/v1/music/songs/trending/
Response: { songs: [ {id, title, cover_image, artist:{stage_name,id},
            listen_count, like_count, genres:[{name}] } ] }

UI: Horizontal scroll row (trên mobile), Grid 2 cột (tablet), 4 cột (desktop)
Card: Cover 1:1 → tên → nghệ sĩ → listen_count
Hover: Show nút Play nổi lên góc trên phải cover
Click card: → /songs/:id
Click nghệ sĩ: → /artists/:id
```

**Section B — Featured Playlists**
```
API: GET /api/v1/playlists/?is_public=true&ordering=-created_at&limit=8

Card: Cover 4:3 → title → owner.display_name → số bài
```

**Section C — Artists nổi bật**
```
API: GET /api/v1/artists/
Response: [ {user_id, stage_name, avatar, followers_count, top_song} ]

UI: Horizontal scroll — Avatar tròn, stage_name bên dưới, follower count nhỏ
Click → /artists/:user_id
```

**Section D — Thể loại (Genres)**
```
API: GET /api/v1/music/genres/
Response: [ {id, name, song_count} ]

UI: Grid pill/chip màu pastel gradient
Click genre chip → /search?genre=:id
```

---

### 3. SOCIAL FEED — `/feed`

**Layout:** 3 cột (desktop): Feed chính | Mood Box | Suggestions

**Main Feed**
```
API: GET /api/v1/social/feed/
Query: ?cursor=xxx (pagination con trỏ)
Response: {
  activities: [{
    id, activity_type,  // "listen" | "like" | "mood"
    user: {id, display_name, avatar},
    song: {id, title, cover_image, artist:{stage_name}},  // nullable
    status_text: string,  // cho mood
    created_at
  }],
  next_cursor
}

Render theo activity_type:
- "listen":  "[Avatar] [Name] vừa nghe [Cover nhỏ] [Song title]"
- "like":    "[Avatar] [Name] đã thích [Cover nhỏ] [Song title] ♥"
- "mood":    "[Avatar] [Name]: [status_text] [Cover nhỏ nếu có song]"

IntersectionObserver → auto load more khi scroll đến cuối
```

**Mood Box (sidebar phải)**
```
API GET mood hiện tại: GET /api/v1/social/me/mood/
API SET mood: POST /api/v1/social/me/mood/
Body: { status_text, song_id?, expires_hours }

UI:
- Textarea: "Bạn đang cảm thấy thế nào?"
- Optional: Search & attach 1 bài hát
- Select thời gian hết hạn: 1h / 4h / 12h / 24h
- Button "Cập nhật tâm trạng"
- Hiển thị mood hiện tại (nếu có, chưa hết hạn)
```

---

### 4. SEARCH — `/search`

**Header search bar** (global component): input focus → expand → show dropdown suggestions (songs + artists)

**Page kết quả:**
```
API SEARCH ALL: GET /api/v1/search/?q=:query
Response: {
  songs:     [{id, title, cover_image, artist, listen_count, genres}],
  artists:   [{user_id, stage_name, avatar, followers_count}],
  playlists: [{id, title, cover_image, owner, song_count, is_public}],
  users:     [{id, display_name, username, avatar, is_private}]
}

API SEARCH SONGS:     GET /api/v1/search/songs/?q=:q&genre=:id&ordering=:field
API SEARCH ARTISTS:   GET /api/v1/search/artists/?q=:q
API SEARCH PLAYLISTS: GET /api/v1/search/playlists/?q=:q
API SEARCH USERS:     GET /api/v1/search/users/?q=:q

Tabs: [Tất cả] [Bài hát] [Nghệ sĩ] [Playlist] [Người dùng]

Tab "Bài hát" có thêm bộ lọc:
  - Dropdown Genre
  - Sort: Mới nhất / Nhiều lượt nghe / Nhiều lượt thích / Đánh giá cao

Empty state: Illustration nhỏ + "Không tìm thấy kết quả cho '[query]'"
```

---

### 5. SONG DETAIL — `/songs/:id`

**Layout:** 2 cột (desktop): Left info panel (40%) | Right comments (60%)

**Left Panel**
```
API GET: GET /api/v1/music/songs/:id/
Response: {
  id, title, cover_image, allow_download,
  artist: {user_id, stage_name, avatar},
  genres: [{id, name}],
  listen_count, like_count, average_rating, rating_count,
  lyrics,
  my_like: bool,      // chỉ khi đã đăng nhập
  my_rating: 1-5      // chỉ khi đã đăng nhập
}

UI Elements:
- Cover image lớn (có ripple effect khi đang play)
- Nút Play lớn
- Title (--text-xl, font display)
- Stage name → link /artists/:user_id
- Genre chips
- Stats: 👁 listen_count  ♥ like_count  ⭐ average_rating

LIKE BUTTON:
  Toggle: POST/DELETE /api/v1/music/songs/:id/like/
  Optimistic update: icon đổi ngay, rollback nếu lỗi

RATING (1-5 sao):
  POST /api/v1/music/songs/:id/rate/  Body: { score: 1-5 }
  UI: 5 stars interactive, current rating hiển thị

DOWNLOAD (nếu allow_download=true):
  GET /api/v1/music/songs/:id/download/ → file blob

LYRICS:
  Collapsible accordion — mặc định đóng
  Nền --color-surface-2, font mono nhẹ, line-height rộng

REPORT button (icon ⚑):
  → Mở Modal Report (xem component chung bên dưới)
```

**Right Panel — Comments**
```
API GET: GET /api/v1/music/songs/:id/comments/
Response: {
  comments: [{
    id, content, created_at, like_count, my_like,
    user: {id, display_name, avatar},
    replies: [{id, content, created_at, user, like_count, my_like}]
  }],
  total_count
}

API POST comment: POST /api/v1/music/songs/:id/comments/
Body: { content, parent_id? }

LIKE comment: POST /api/v1/music/comments/:id/like/

DELETE comment: DELETE /api/v1/music/comments/:id/
(chỉ show nếu comment.user.id === currentUser.id)

UI:
- Input box cố định trên top (sticky)
- Thread 2 cấp: comment → replies (indent nhẹ, border-left lavender)
- Nút "Trả lời" mỗi comment
- Like button trên mỗi comment & reply
- Infinite scroll
```

**RECORD PLAY:**
```
Gọi API sau khi nghe được 30 giây:
POST /api/v1/music/songs/:id/play/
Body: {} 
(Gọi 1 lần mỗi session, dùng ref để track)
```

---

### 6. ARTIST PROFILE — `/artists/:user_id`

**Layout:** Hero cover full-width + content bên dưới
```
API GET: GET /api/v1/artists/:user_id/
Response: {
  user_id, stage_name, bio,
  avatar, cover_image,
  social_links: { website?, facebook?, youtube? },
  followers_count, following_count,
  is_following: bool,
  mood: { status_text, song?, expires_at } | null
}

API FOLLOW: POST /api/v1/social/users/:user_id/follow/
Response: { is_following: bool, followers_count: int }

API GET SONGS: GET /api/v1/music/songs/?artist=:user_id&status=published&ordering=-listen_count

UI Structure:
┌─────────────────────────────────────┐
│ COVER IMAGE (aspect 3:1, blur fade) │
│  ┌─────────────────────────────┐    │
│  │ AVATAR (120px, tròn, border)│    │
│  └─────────────────────────────┘    │
│  stage_name (--text-2xl, bold)      │
│  [X followers] [Y following]        │
│  [Follow / Đang theo dõi button]    │
└─────────────────────────────────────┘

Mood badge (nếu có):
  🎵 "[status_text]" — [song.title nếu có]
  Style: pill soft lavender

Tabs: [Nhạc] [Giới thiệu]

Tab Nhạc: Grid 2 cột bài hát (cover + title + listen_count)
Tab Giới thiệu: bio text + social links icons

Buttons social:
  🌐 Website  📘 Facebook  ▶ YouTube
```

---

### 7. USER PROFILE — `/users/:user_id`

```
API GET: GET /api/v1/accounts/users/:user_id/
Response: {
  id, display_name, username, bio, avatar, is_private,
  is_following, followers_count, following_count
}

API FOLLOW:   POST /api/v1/social/users/:user_id/follow/
API BLOCK:    POST /api/v1/accounts/users/:user_id/block/   Body: {action:"block"}
API UNBLOCK:  POST /api/v1/accounts/users/:user_id/block/   Body: {action:"unblock"}
API REPORT:   POST /api/v1/music/reports/  Body: { target_type:"user", target_id, reason }

Nếu is_private=true và chưa follow: hiện "Tài khoản này ở chế độ riêng tư"

Public Playlists của user:
  GET /api/v1/playlists/?owner=:user_id&is_public=true

Activity Feed:
  GET /api/v1/social/users/:user_id/activities/ (nếu không bị private)

Header actions (dropdown ⋯):
  - Block / Unblock
  - Báo cáo người dùng
```

---

### 8. PLAYLIST DETAIL — `/playlists/:id`

```
API GET: GET /api/v1/playlists/:id/
Response: {
  id, title, description, cover_image, is_public,
  owner: {id, display_name, avatar},
  song_count, created_at,
  songs: [{id, title, cover_image, artist:{stage_name}, duration, order}]
}

UI:
- Hero: Cover (square 240px) | Title | Owner | song_count | created_at
- Song list: số thứ tự | Cover nhỏ | Title | Artist | Duration | ♥
- Click row → play bài đó + queue cả playlist
- Like/Save playlist: POST /api/v1/playlists/:id/like/ (nếu có)

Nếu owner === currentUser:
  - Hiện Edit button → mở PlaylistEditModal
  - Drag handle ☰ trên mỗi row để reorder
```

---

### 9. MY LIBRARY — `/library`

**Tabs:** [Playlist của tôi] [Đã thích] [Lịch sử nghe]

**Tab: Playlist của tôi**
```
API GET: GET /api/v1/playlists/
Response: [{id, title, cover_image, song_count, is_public, updated_at}]

Button "+ Tạo playlist":
  → Modal: { title (required), description, is_public toggle }
  API: POST /api/v1/playlists/
  Body: { title, description, is_public }

Card mỗi playlist:
  Cover | Title | X bài | Trạng thái (Công khai/Riêng tư)
  Click ⋯ → Edit / Xóa
  
Edit Playlist Modal:
  API: PATCH /api/v1/playlists/:id/
  Upload cover: POST /api/v1/playlists/:id/cover/ (multipart)
  Toggle visibility: PATCH /api/v1/playlists/:id/visibility/  Body: {is_public}
  
  Quản lý bài hát trong playlist:
    Xem list: GET /api/v1/playlists/:id/songs/
    Xóa bài:  DELETE /api/v1/playlists/:id/songs/:song_id/
    Reorder:  POST /api/v1/playlists/:id/songs/reorder/
              Body: { song_ids: [uuid,...] }  // thứ tự mới
    Drag-and-drop với @dnd-kit/core hoặc react-beautiful-dnd
```

**Tab: Đã thích**
```
API: GET /api/v1/music/songs/?liked=true
Hiển thị như grid bài hát thông thường
```

**Tab: Lịch sử nghe**
```
API: GET /api/v1/music/me/history/
Response: [{song: {...}, listened_at}]
Grouped theo ngày: "Hôm nay", "Hôm qua", "Tuần này", "Tháng này"
```

---

### 10. ARTIST STUDIO — `/studio` (Chỉ role=artist)

**Guard:** Kiểm tra user.role === 'artist' → redirect /home nếu không phải

**Sub-routes:**
```
/studio              → Dashboard
/studio/songs        → Quản lý bài hát
/studio/upload       → Upload bài hát mới
/studio/profile      → Hồ sơ nghệ sĩ
```

**Dashboard Stats**
```
API: GET /api/v1/artists/me/stats/
Response: {
  total_songs, total_listens, total_likes,
  total_comments, unique_listeners,
  average_rating, follower_count
}

UI: Grid 3x2 stat cards
  Mỗi card: icon + số lớn + label nhỏ
  Màu: primary/accent xen kẽ soft background
```

**Upload Bài hát — `/studio/upload`**
```
API: POST /api/v1/music/songs/   (multipart/form-data)
Fields:
  - audio_file:    .mp3/.flac/.wav (required)
  - cover_image:   ảnh bìa (optional, có thể upload sau)
  - title:         string required
  - genre_ids:     array of UUID (chọn từ GET /api/v1/music/genres/)
  - lyrics:        text (optional)
  - allow_download: boolean (default false)
  - status:        "draft" | "published" (default "draft")

Response 201: { song: {...} }

UI Flow:
1. Drag & Drop zone cho audio file + preview tên file
2. Cover image upload (preview ngay)
3. Form fields
4. Save as Draft / Publish ngay

Progress bar upload (sử dụng XMLHttpRequest onprogress)
```

**Quản lý Bài hát — `/studio/songs`**
```
API: GET /api/v1/music/songs/?my=true
Response: songs list với status field

Table columns: Cover | Title | Status | Listens | Likes | Rating | Actions

Status badges:
  draft      → chip xám "Nháp"
  published  → chip xanh "Đã phát hành"
  hidden     → chip đỏ nhạt "Đã ẩn"

Actions per row:
  - Edit (modal hoặc /studio/songs/:id/edit)
  - Publish:  POST /api/v1/music/songs/:id/publish/
  - Hide:     POST /api/v1/music/songs/:id/hide/
  - Delete:   DELETE /api/v1/music/songs/:id/
              Xác nhận: Dialog "Xóa bài hát này? Không thể hoàn tác"
```

**Hồ sơ Nghệ sĩ — `/studio/profile`**
```
API GET: GET /api/v1/artists/me/
API UPDATE: PATCH /api/v1/artists/me/
Body: { stage_name, bio, social_links: {website,facebook,youtube} }

API UPLOAD COVER: POST /api/v1/artists/me/cover/   multipart

Fields:
  - Stage name
  - Bio (textarea, 500 ký tự max)
  - Website URL
  - Facebook URL
  - YouTube URL
  - Cover image (preview + upload)
```

---

### 11. ACCOUNT SETTINGS — `/settings`

**Tabs:** [Hồ sơ] [Bảo mật] [Quyền riêng tư] [Xác minh Nghệ sĩ]

**Tab: Hồ sơ**
```
API GET: GET /api/v1/accounts/me/
API UPDATE: PATCH /api/v1/accounts/me/
Body: { display_name, username, bio }

Avatar:
  POST /api/v1/accounts/me/avatar/  multipart
  Click vào avatar → file picker
  Preview → Crop (optional) → Upload
```

**Tab: Bảo mật**
```
Đổi mật khẩu:
  API: POST /api/v1/auth/password/change/
  Body: { old_password, new_password, new_password_confirm }
  Success toast: "Mật khẩu đã được cập nhật"
```

**Tab: Quyền riêng tư**
```
API: PATCH /api/v1/accounts/me/privacy/
Body: { is_private: bool }

Toggle switch: "Tài khoản riêng tư"
Description: "Chỉ người được duyệt mới thấy hoạt động của bạn"

Block List:
  GET /api/v1/accounts/me/  (trường blocked_users hoặc endpoint riêng)
  Hiển thị danh sách người bị chặn
  Nút "Bỏ chặn" mỗi người:
    POST /api/v1/accounts/users/:id/block/  Body: {action:"unblock"}
```

**Tab: Xác minh Nghệ sĩ**
```
Nếu chưa nộp:
  Form: { real_name, notes }
  Upload CCCD/CMND: file image
  API: POST /api/v1/accounts/artist-verification/
  
Nếu đã nộp:
  GET /api/v1/accounts/artist-verification/me/
  Hiển thị trạng thái: pending / approved / rejected
  Nếu rejected: hiện lý do + cho phép nộp lại
```

---

### 12. NOTIFICATIONS — Dropdown + `/notifications`

**Notification Bell (Header)**
```
API GET count: GET /api/v1/notifications/unread-count/
Response: { count: int }
Hiện badge đỏ nếu count > 0
Poll mỗi 30s (hoặc dùng WebSocket nếu có)

Click bell → Dropdown (max 5 notifications mới nhất):
  API: GET /api/v1/notifications/?limit=5
  Link "Xem tất cả" → /notifications
```

**Trang /notifications**
```
API: GET /api/v1/notifications/
Response: {
  notifications: [{
    id, notif_type, message, is_read,
    sender: {id, display_name, avatar} | null,
    target_type, target_id,
    created_at
  }],
  unread_count
}

notif_type values & icons:
  "follow"           → 👤 "[Name] đã theo dõi bạn"
  "like"             → ♥  "[Name] đã thích [Song]"
  "comment"          → 💬 "[Name] đã bình luận về [Song]"
  "reply"            → ↩  "[Name] đã trả lời bình luận của bạn"
  "system"           → 🔔 "[Message hệ thống]"
  "artist_approved"  → ✅ "Yêu cầu nghệ sĩ đã được chấp thuận"
  "artist_rejected"  → ❌ "Yêu cầu nghệ sĩ đã bị từ chối"

Mark read:
  Single: POST /api/v1/notifications/:id/read/
  All:    POST /api/v1/notifications/read-all/

Delete:
  DELETE /api/v1/notifications/:id/

Click notification → navigate đến target:
  target_type="song" → /songs/:target_id
  target_type="user" → /users/:target_id
  target_type="comment" → /songs/:song_id?comment=:target_id
```

---

### 13. GLOBAL MUSIC PLAYER (Fixed Bottom)

```
State quản lý: Zustand / Context

Thông tin cần lưu trong player state:
  currentSong, queue[], queueIndex, isPlaying, progress, duration, volume, isMuted

API gọi khi:
  - Mount: src = song.audio_file URL
  - Sau 30s: POST /api/v1/music/songs/:id/play/

Layout:
┌────────────────────────────────────────────────────────────┐
│ [Cover 48px] [Title + Artist]  [⏮ ⏸/▶ ⏭] [Progress bar] [🔉 Vol] [⋮ Queue] │
└────────────────────────────────────────────────────────────┘

Progress bar: draggable, màu --color-primary, background --color-border
Volume: slider + mute toggle

Queue sidebar (slide từ phải):
  Danh sách queue, current highlight bằng --color-primary-soft
  Click item → play luôn
  Drag reorder

Keyboard shortcuts:
  Space → play/pause
  ← / → → prev/next 5s
  M → mute
  ↑ / ↓ → volume
```

---

### 14. SHARED COMPONENTS

**Modal Report (Báo cáo vi phạm)**
```
API: POST /api/v1/music/reports/
Body: { target_type: "song"|"comment"|"user", target_id, reason }

Reasons (radio):
  - copyright  : Bản quyền
  - spam       : Spam
  - offensive  : Nội dung phản cảm
  - other      : Khác

Textarea (optional): "Mô tả thêm"
```

**Modal Follower/Following List**
```
Followers: GET /api/v1/social/users/:id/followers/
Following: GET /api/v1/social/users/:id/following/

Mỗi item: Avatar + display_name + Follow/Unfollow button (nếu không phải mình)
```

**Toast Notification System**
```
Vị trí: top-right
Types: success (xanh), error (đỏ), info (tím), warning (vàng)
Duration: 3000ms, có nút × để đóng sớm
Animate: slide in từ phải + fade out
```

**Permission Guards**
```
Các nút chỉ hiện khi đủ điều kiện:
- Upload song: user.role === 'artist'
- Edit/Delete comment: comment.user.id === currentUser.id
- Edit playlist: playlist.owner.id === currentUser.id
- Studio nav: user.role === 'artist'

Route guard: /studio/* → redirect /home nếu role !== 'artist'
Auth guard: /library, /settings, /notifications → redirect /login nếu chưa đăng nhập
```

---

### 15. ADMIN DASHBOARD — `/admin` (Chỉ role=admin)

**[Duyệt nghệ sĩ]**
```
GET /api/v1/accounts/admin/verifications/
Response: [{id, user:{display_name,email}, real_name, id_card_image, notes, created_at}]

Approve: POST /api/v1/accounts/admin/verifications/:id/approve/
Reject:  POST /api/v1/accounts/admin/verifications/:id/reject/  Body: {reason}
```

**[Xử lý báo cáo]**
```
GET /api/v1/music/admin/reports/
Response: [{id, reporter, target_type, target_id, reason, description, created_at, is_resolved}]

Resolve: POST /api/v1/music/admin/reports/:id/resolve/
Hide song: POST /api/v1/music/admin/songs/:id/hide/
Hide comment: POST /api/v1/music/admin/comments/:id/hide/
```

**[Trending management]**
```
Promote song: POST /api/v1/music/admin/songs/:id/trending/
```

**[Quản lý thể loại]**
```
GET    /api/v1/music/genres/
POST   /api/v1/music/genres/                    Body: {name}
PATCH  /api/v1/music/genres/:id/               Body: {name}
DELETE /api/v1/music/genres/:id/
```

---

## ⚙️ KỸ THUẬT IMPLEMENTATION

### Stack đề xuất
```
Framework:    React 18 + TypeScript
Routing:      React Router v6
State:        Zustand (player, auth) + React Query (server state)
Styling:      Tailwind CSS (custom tokens) hoặc CSS Modules
HTTP:         Axios (interceptor tự động gắn CSRF + credentials)
Upload:       XMLHttpRequest (progress tracking)
DnD:          @dnd-kit/core (playlist reorder)
Audio:        HTML5 <audio> element
Icons:        Lucide React
Fonts:        Google Fonts (Plus Jakarta Sans + Inter)
```

### Auth & CSRF Setup
```javascript
// Mỗi request đều cần:
axios.defaults.withCredentials = true

// Lấy CSRF trước khi POST/PUT/DELETE:
// GET /api/v1/auth/csrf/  → set-cookie: csrftoken
// Header: X-CSRFToken: <value từ cookie>

// Session check khi app load:
// GET /api/v1/auth/me/ → 200 (đã login) hoặc 401 (chưa login)
```

### Error Handling pattern
```javascript
// 400: show field errors inline
// 401: redirect /login
// 403: show "Không có quyền" toast
// 404: show not found page
// 429: show "Thử lại sau" toast
// 500: show "Lỗi hệ thống" toast
```

### Responsive Breakpoints
```
mobile:  < 640px  (1 cột, bottom nav, player compact)
tablet:  640-1023px (sidebar ẩn, hamburger menu)
desktop: ≥ 1024px (sidebar fixed, player full)
```

---

## 🎯 PHONG CÁCH THIẾT KẾ — Lưu ý quan trọng

1. **Pastel, không phải baby colors** — màu phải đủ contrast để đọc được (WCAG AA)
2. **Whitespace rộng** — padding generous, đừng nhồi nhét
3. **Cards không có shadow harsh** — dùng border nhẹ thay thế hoặc shadow rất nhạt
4. **Hover state tinh tế** — background shift sang --color-primary-soft
5. **Loading states** — Skeleton screens (không spinner trên card grid)
6. **Micro-animations** — heart bounce khi like, số đếm tăng dần
7. **Player bar** — màu tối tương phản để nổi bật với content bên trên
8. **Cover images** — luôn có fallback gradient pastel khi không có ảnh
9. **Empty states** — illustration SVG nhỏ + text hướng dẫn hành động
10. **Font display** — Plus Jakarta Sans chỉ dùng cho title/headline, không dùng cho body

---

*Prompt này được thiết kế để dùng như một "spec" đầy đủ — mỗi trang/component có thể yêu cầu riêng lẻ hoặc toàn bộ cùng lúc.*
