/**
 * notifications.js
 * Kết nối toàn bộ giao diện trang thông báo với backend API.
 *
 * APIs sử dụng:
 *  GET  /api/v1/notifications/               → danh sách thông báo
 *  GET  /api/v1/notifications/unread-count/  → số chưa đọc
 *  POST /api/v1/notifications/<id>/read/     → đánh dấu 1 đã đọc
 *  POST /api/v1/notifications/read-all/      → đánh dấu tất cả đã đọc
 *  DELETE /api/v1/notifications/<id>/        → xóa 1 thông báo
 */

// ─────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────

function getCsrfToken() {
    const name = 'csrftoken';
    const match = document.cookie
        .split(';')
        .map(c => c.trim())
        .find(c => c.startsWith(name + '='));
    return match ? decodeURIComponent(match.split('=')[1]) : '';
}

/**
 * Trả chuỗi thời gian tương đối (2 phút trước, 3 giờ trước…)
 */
function timeAgo(isoString) {
    const now = new Date();
    const past = new Date(isoString);
    const diffMs = now - past;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'Vừa xong';
    if (diffMin < 60) return `${diffMin} phút trước`;
    if (diffHour < 24) return `${diffHour} giờ trước`;
    if (diffDay < 7) return `${diffDay} ngày trước`;
    return past.toLocaleDateString('vi-VN');
}

/**
 * Lấy icon + màu badge theo loại thông báo
 */
function getTypeMeta(notifType) {
    const map = {
        like: { icon: 'bi-heart-fill', color: 'bg-danger' },
        follow: { icon: 'bi-person-plus-fill', color: '', bgColor: 'rgb(140, 225, 178)' },
        follow_request: { icon: 'bi-person-plus-fill', color: '', bgColor: 'rgb(140, 225, 178)' },
        comment: { icon: 'bi-chat-fill', color: 'bg-warning' },
        reply: { icon: 'bi-chat-quote-fill', color: 'bg-warning' },
        system: { icon: 'bi-gear-fill', color: 'bg-secondary' },
        verify_result: { icon: 'bi-patch-check-fill', color: 'bg-primary' },
        new_song: { icon: 'bi-music-note-beamed', color: '', bgColor: 'rgb(140, 225, 178)' },
    };
    return map[notifType] || { icon: 'bi-bell-fill', color: 'bg-secondary' };
}

/**
 * Tạo phần tử HTML cho 1 thông báo
 */
function buildNotificationEl(notif) {
    const isUnread = !notif.is_read;
    const meta = getTypeMeta(notif.notif_type);

    // Avatar
    let avatarHtml;
    if (notif.sender && notif.sender.avatar) {
        avatarHtml = `<img src="${notif.sender.avatar}" alt="avatar"
                           class="rounded-circle object-fit-cover"
                           style="width:48px;height:48px;">`;
    } else {
        avatarHtml = `<div class="rounded-circle text-white d-flex align-items-center justify-content-center"
                           style="width:48px;height:48px;background:linear-gradient(135deg,#6c757d,#495057);">
                          <i class="bi bi-person-fill fs-4"></i>
                      </div>`;
    }

    // Badge nhỏ ở góc avatar
    const badgeHtml = `<div class="position-absolute bottom-0 end-0 ${meta.color} text-white rounded-circle
                                  d-flex align-items-center justify-content-center"
                            style="width:20px;height:20px;transform:translate(25%,25%);border:2px solid var(--bg-card); ${meta.bgColor ? `background-color: ${meta.bgColor};` : ''}">
                           <i class="${meta.icon}" style="font-size:0.65rem;"></i>
                       </div>`;

    // Dấu chấm chưa đọc
    const unreadDot = isUnread
        ? `<div class="position-absolute top-50 start-0 translate-middle rounded-circle bg-accent"
                  style="width:8px;height:8px;margin-left:12px;"></div>`
        : '';

    // Nút kết bạn lại nếu là follow hoặc nút xử lý yêu cầu nếu là follow_request
    let actionBtnHtml = '';
    if (notif.notif_type === 'follow' && notif.sender) {
        // Nếu tôi là nghệ sĩ, và người theo dõi tôi là người dùng bình thường -> KHÔNG hiện nút theo dõi lại
        const amIArtist = window.IS_ARTIST || false;
        const isSenderNormalUser = !notif.sender.is_artist;
        
        if (!(amIArtist && isSenderNormalUser)) {
            actionBtnHtml = `<button class="btn btn-sm btn-outline-secondary text-muted-custom rounded-circle
                               align-self-center me-2 d-flex align-items-center justify-content-center
                               follow-back-btn"
                       data-user-id="${notif.sender.id}"
                       style="width:32px;height:32px;" title="Theo dõi lại">
                   <i class="bi bi-person-plus-fill"></i>
               </button>`;
        }
    } else if (notif.notif_type === 'follow_request' && notif.sender) {
        actionBtnHtml = `<button class="btn btn-sm rounded-circle
                           align-self-center me-2 d-flex align-items-center justify-content-center
                           fr-action-btn"
                   data-sender-id="${notif.sender.id}"
                   data-sender-name="${notif.sender.display_name || notif.sender.username}"
                   data-sender-avatar="${notif.sender.avatar || ''}"
                   style="width:32px;height:32px; border: 1px solid rgba(255,255,255,0.2); color: rgba(255,255,255,0.7); background: transparent;" title="Xử lý yêu cầu kết bạn">
               <i class="bi bi-person-check-fill"></i>
           </button>`;
    }

    // Background khác nhau tuỳ đã đọc / chưa đọc
    const bg = isUnread ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.02)';
    const border = isUnread ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.03)';
    const opacity = isUnread ? '' : 'opacity-75';
    const avatarMargin = isUnread ? 'ms-2' : 'ms-4';

    const el = document.createElement('div');
    el.className = `notification-item d-flex align-items-start gap-3 p-3 rounded position-relative ${opacity}`;
    el.dataset.id = notif.id;
    el.dataset.read = notif.is_read ? '1' : '0';
    el.style.cssText = `background:${bg};border:1px solid ${border};cursor:pointer;transition:background 0.2s;`;

    el.innerHTML = `
        ${unreadDot}
        <div class="notification-avatar position-relative ${avatarMargin}">
            ${avatarHtml}
            ${badgeHtml}
        </div>
        <div class="notification-content flex-grow-1">
            <div class="text-white mb-1" style="font-size:0.95rem;">${notif.message}</div>
            <div class="text-muted-custom small">
                <i class="bi bi-clock me-1"></i>${timeAgo(notif.created_at)}
            </div>
        </div>
        ${actionBtnHtml}
        <button class="btn btn-sm btn-link text-muted-custom p-0 ${actionBtnHtml ? 'ms-1' : 'ms-2'} notification-delete-btn align-self-center"
                title="Xóa thông báo"
                style="opacity:0.5;transition:opacity 0.2s;"
                onmouseover="this.style.opacity='1'"
                onmouseout="this.style.opacity='0.5'">
            <i class="bi bi-x-lg"></i>
        </button>
    `;

    // Đánh dấu đã đọc khi click vào body
    el.addEventListener('click', (e) => {
        if (e.target.closest('.notification-delete-btn') || e.target.closest('.follow-back-btn') || e.target.closest('.fr-action-btn')) return;
        markRead(el, notif.id);
    });

    // Xóa thông báo
    el.querySelector('.notification-delete-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        deleteNotification(el, notif.id);
    });

    // Theo dõi lại
    const followBtn = el.querySelector('.follow-back-btn');
    if (followBtn) {
        followBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            followBack(followBtn, notif.sender.id);
        });
    }

    // Xử lý yêu cầu kết bạn (Mở Modal)
    const frActionBtn = el.querySelector('.fr-action-btn');
    if (frActionBtn) {
        frActionBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openFrModal(frActionBtn);
        });
    }

    return el;
}

// ─────────────────────────────────────────
// API Calls
// ─────────────────────────────────────────

async function fetchNotifications(page = 1) {
    const res = await fetch(`/api/v1/notifications/?page=${page}&page_size=30`, {
        headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) throw new Error('Lỗi tải thông báo');
    return res.json();
}

async function fetchUnreadCount() {
    const res = await fetch('/api/v1/notifications/unread-count/', {
        headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return 0;
    const data = await res.json();
    return data.data?.unread_count ?? 0;
}

async function apiMarkRead(notifId) {
    return fetch(`/api/v1/notifications/${notifId}/read/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    });
}

async function apiMarkAllRead() {
    return fetch('/api/v1/notifications/read-all/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    });
}

async function apiDelete(notifId) {
    return fetch(`/api/v1/notifications/${notifId}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCsrfToken() }
    });
}

// ─────────────────────────────────────────
// UI Actions
// ─────────────────────────────────────────

function markRead(el, notifId) {
    if (el.dataset.read === '1') return;
    apiMarkRead(notifId).then(res => {
        if (res.ok) {
            el.dataset.read = '1';
            el.style.background = 'rgba(255,255,255,0.02)';
            el.style.border = '1px solid rgba(255,255,255,0.03)';
            el.classList.add('opacity-75');
            el.classList.remove('opacity-100');
            // xóa chấm
            const dot = el.querySelector('.bg-accent');
            if (dot) dot.remove();
            // cập nhật badge trên icon chuông
            decrementBadge();
        }
    }).catch(err => console.warn('markRead error:', err));
}

function deleteNotification(el, notifId) {
    apiDelete(notifId).then(res => {
        // 200 hoặc 204 đều OK
        if (res.ok || res.status === 204) {
            // nếu chưa đọc thì giảm badge
            if (el.dataset.read === '0') decrementBadge();
            el.style.transition = 'opacity 0.3s, max-height 0.3s';
            el.style.opacity = '0';
            setTimeout(() => {
                el.remove();
                checkEmpty();
            }, 300);
        } else {
            console.warn('delete failed', res.status);
        }
    }).catch(err => console.warn('delete error:', err));
}

function followBack(btn, userId) {
    fetch(`/api/v1/social/users/${userId}/follow/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
    }).then(res => {
        if (res.ok) {
            btn.innerHTML = '<i class="bi bi-check-lg"></i>';
            btn.disabled = true;
            btn.title = 'Đã theo dõi';
            btn.classList.replace('btn-outline-secondary', 'btn-outline-success');
        }
    }).catch(err => console.warn('followBack error:', err));
}

let frActionModalInstance = null;
let currentFrActionBtn = null;

function openFrModal(btn) {
    const senderId = btn.dataset.senderId;
    const senderName = btn.dataset.senderName;
    const senderAvatar = btn.dataset.senderAvatar;

    const modalEl = document.getElementById('followRequestActionModal');
    if (!modalEl) return;

    document.getElementById('frModalName').textContent = senderName;
    const avatarEl = document.getElementById('frModalAvatar');
    if (senderAvatar) {
        avatarEl.src = senderAvatar;
    } else {
        avatarEl.src = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80'; // Default
    }
    document.getElementById('frModalSenderId').value = senderId;
    currentFrActionBtn = btn;

    if (!frActionModalInstance) {
        frActionModalInstance = new bootstrap.Modal(modalEl);

        // Setup event listeners for Accept/Reject buttons ONCE
        document.getElementById('frModalAccept').addEventListener('click', () => handleFrAction('accept'));
        document.getElementById('frModalReject').addEventListener('click', () => handleFrAction('reject'));
    }

    frActionModalInstance.show();
}

async function handleFrAction(action) {
    const senderId = document.getElementById('frModalSenderId').value;
    if (!senderId) return;

    try {
        // Fetch received requests to get the exact request_id
        const resList = await fetch('/api/v1/social/follow-requests/received/');
        if (!resList.ok) throw new Error('Cannot fetch requests');
        const data = await resList.json();
        const requestItem = data.data.items.find(r => r.sender.id === senderId);

        if (!requestItem) {
            alert('Yêu cầu kết bạn không tồn tại hoặc đã bị hủy!');
            frActionModalInstance.hide();
            if (currentFrActionBtn) {
                currentFrActionBtn.remove();
            }
            return;
        }

        const requestId = requestItem.id;
        // Call accept or reject
        const resAction = await fetch(`/api/v1/social/follow-requests/${requestId}/${action}/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' }
        });

        if (resAction.ok) {
            frActionModalInstance.hide();
            // Xóa luôn thông báo khỏi giao diện và CSDL để không hiện lại khi tải lại trang
            if (currentFrActionBtn) {
                const notifEl = currentFrActionBtn.closest('.notification-item');
                if (notifEl) {
                    const notifId = notifEl.dataset.id;
                    deleteNotification(notifEl, notifId);
                } else {
                    currentFrActionBtn.remove();
                }
            }
        } else {
            alert('Xử lý thất bại. Vui lòng thử lại.');
        }
    } catch (err) {
        console.error('FR Action Error:', err);
        alert('Lỗi kết nối. Vui lòng thử lại.');
    }
}

// ─────────────────────────────────────────
// Badge trên chuông
// ─────────────────────────────────────────

function renderBadge(count) {
    // Cập nhật tất cả icon chuông có badge
    document.querySelectorAll('.bell-badge').forEach(b => {
        b.textContent = count > 99 ? '99+' : count;
        b.style.display = count > 0 ? 'flex' : 'none';
    });
}

function decrementBadge() {
    document.querySelectorAll('.bell-badge').forEach(b => {
        const cur = parseInt(b.textContent) || 0;
        const next = Math.max(0, cur - 1);
        b.textContent = next > 99 ? '99+' : next;
        b.style.display = next > 0 ? 'flex' : 'none';
    });
}

// ─────────────────────────────────────────
// Render list
// ─────────────────────────────────────────

const LIST_CONTAINER_ID = 'notificationListContainer';
const EMPTY_MSG_ID = 'notificationEmptyMsg';

function renderList(items) {
    const container = document.getElementById(LIST_CONTAINER_ID);
    if (!container) return;

    container.innerHTML = '';

    if (!items || items.length === 0) {
        showEmpty();
        return;
    }

    hideEmpty();

    let unreadRendered = false;
    let readRendered = false;

    items.forEach(notif => {
        // Chèn divider giữa chưa đọc / đã đọc
        if (!notif.is_read && !unreadRendered) {
            unreadRendered = true;
        }
        if (notif.is_read && unreadRendered && !readRendered) {
            readRendered = true;
            const divider = document.createElement('hr');
            divider.className = 'border-secondary opacity-25 my-3';
            container.appendChild(divider);
        }

        container.appendChild(buildNotificationEl(notif));
    });

    // Đánh dấu đã đọc tất cả
    const markAllBtn = document.getElementById('markAllReadBtn');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', async () => {
            const res = await apiMarkAllRead();
            if (res.ok) {
                // update UI
                container.querySelectorAll('.notification-item').forEach(el => {
                    el.dataset.read = '1';
                    el.style.background = 'rgba(255,255,255,0.02)';
                    el.style.border = '1px solid rgba(255,255,255,0.03)';
                    el.classList.add('opacity-75');
                    const dot = el.querySelector('.bg-accent');
                    if (dot) dot.remove();
                });
                renderBadge(0);
            }
        }, { once: true });
    }
}

function showEmpty() {
    const container = document.getElementById(LIST_CONTAINER_ID);
    if (!container) return;
    container.innerHTML = `
        <div id="${EMPTY_MSG_ID}" class="text-center text-muted-custom py-5">
            <i class="bi bi-bell-slash fs-1 d-block mb-3" style="opacity:0.3;"></i>
            <div>Bạn chưa có thông báo nào.</div>
        </div>`;
}

function hideEmpty() {
    const msg = document.getElementById(EMPTY_MSG_ID);
    if (msg) msg.remove();
}

function checkEmpty() {
    const container = document.getElementById(LIST_CONTAINER_ID);
    if (!container) return;
    const items = container.querySelectorAll('.notification-item');
    if (items.length === 0) showEmpty();
}

// ─────────────────────────────────────────
// Loading skeleton
// ─────────────────────────────────────────

function showSkeleton(container) {
    container.innerHTML = Array.from({ length: 5 }, () => `
        <div class="d-flex align-items-start gap-3 p-3 rounded mb-2"
             style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);">
            <div class="rounded-circle bg-secondary flex-shrink-0"
                 style="width:48px;height:48px;opacity:0.2;animation:pulse 1.4s ease infinite;"></div>
            <div class="flex-grow-1">
                <div class="rounded bg-secondary mb-2"
                     style="height:14px;width:70%;opacity:0.15;animation:pulse 1.4s ease infinite;"></div>
                <div class="rounded bg-secondary"
                     style="height:12px;width:40%;opacity:0.1;animation:pulse 1.4s ease infinite;"></div>
            </div>
        </div>`).join('');
}

// ─────────────────────────────────────────
// Init
// ─────────────────────────────────────────

async function initNotificationsPage() {
    const container = document.getElementById(LIST_CONTAINER_ID);
    if (!container) return;

    showSkeleton(container);

    try {
        const [notifsData, unreadCount] = await Promise.all([
            fetchNotifications(),
            fetchUnreadCount(),
        ]);

        renderList(notifsData.data?.items ?? []);
        renderBadge(unreadCount);
    } catch (err) {
        console.error('Notification init error:', err);
        container.innerHTML = `
            <div class="text-center text-muted-custom py-5">
                <i class="bi bi-wifi-off fs-1 d-block mb-3" style="opacity:0.4;"></i>
                <div>Không thể tải thông báo. Vui lòng thử lại.</div>
                <button class="btn btn-sm btn-outline-secondary mt-3" onclick="initNotificationsPage()">
                    <i class="bi bi-arrow-clockwise me-1"></i> Thử lại
                </button>
            </div>`;
    }
}

// CSS animation pulse
const style = document.createElement('style');
style.textContent = `
@keyframes pulse {
    0%, 100% { opacity: 0.1; }
    50%       { opacity: 0.25; }
}`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', initNotificationsPage);
