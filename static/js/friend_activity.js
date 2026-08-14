// static/js/friend_activity.js

document.addEventListener('DOMContentLoaded', () => {
    if (!window.CURRENT_USER_ID) return;

    // ─── DOM Elements ──────────────────────────────────────────────────────
    const activityContainers = document.querySelectorAll('#friendsActivityContainer, #mobileFriendsActivityContainer');
    const searchInputs = document.querySelectorAll('#friendSearchInput, #mobileFriendSearchInput');
    const onlineCountElements = document.querySelectorAll('#onlineFriendsCount, #mobileOnlineFriendsCount');

    let allFriends = [];

    // ─── Load Friend Activity ───────────────────────────────────────────────
    async function loadFriendActivity(keyword = '') {
        try {
            const [followingRes, feedRes] = await Promise.all([
                fetch(`/api/v1/social/friends/?page_size=100${keyword ? '&q=' + encodeURIComponent(keyword) : ''}`),
                fetch(`/api/v1/social/feed/?page_size=100`)
            ]);
            const followingData = await followingRes.json();
            const feedData = await feedRes.json();

            if (!followingData.success) throw new Error("Failed to load following");

            // Lấy hoạt động mới nhất của mỗi người
            const latestActivities = {};
            if (feedData.success) {
                feedData.data.items.forEach(item => {
                    if (!latestActivities[item.user.id]) {
                        latestActivities[item.user.id] = item;
                    }
                });
            }

            const now = new Date();
            const THIRTY_MINUTES = 30 * 60 * 1000;

            const friendsData = followingData.data.items.map(friend => {
                const activity = latestActivities[friend.id];
                let isOnline = false;
                let activityText = '';
                let timeText = 'Không hoạt động';

                if (activity) {
                    const diff = now - new Date(activity.created_at);
                    if (diff < THIRTY_MINUTES) isOnline = true;

                    const diffMins = Math.floor(diff / 60000);
                    const diffHours = Math.floor(diffMins / 60);
                    const diffDays = Math.floor(diffHours / 24);

                    if (diffMins < 1) timeText = "Vừa xong";
                    else if (diffMins < 60) timeText = `${diffMins} phút trước`;
                    else if (diffHours < 24) timeText = `${diffHours} giờ trước`;
                    else timeText = `${diffDays} ngày trước`;

                    if (friend.mood) {
                        const moodEmoji = friend.mood.mood_type?.emoji ? `<span style="font-size: 1.1rem; margin-bottom: 2px; display: inline-block;">${friend.mood.mood_type.emoji}</span>` : `<i class="bi bi-emoji-smile text-warning"></i>`;
                        const statusText = friend.mood.status_text ? ` <span style="color: rgba(255,255,255,0.85);">${friend.mood.status_text}</span>` : '';
                        activityText = `${moodEmoji}${statusText}`;
                        if (activity && activity.activity_type === 'playing' && activity.song) {
                            activityText += `<br><div style="margin-top: 2px; display: flex; align-items: center;"><i class="bi bi-music-note-beamed text-info" style="font-size: 0.85rem; margin-right: 2px;"></i> <div class="marquee-wrapper" style="flex-grow: 1; min-width: 0; max-width: 120px; height: 16px;"><div class="marquee-left"><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${activity.song.title}</span><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${activity.song.title}</span></div></div></div>`;
                        } else if (friend.mood.song) {
                            activityText += `<br><div style="margin-top: 2px; display: flex; align-items: center;"><i class="bi bi-music-note-beamed text-info" style="font-size: 0.85rem; margin-right: 2px;"></i> <div class="marquee-wrapper" style="flex-grow: 1; min-width: 0; max-width: 120px; height: 16px;"><div class="marquee-left"><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${friend.mood.song.title}</span><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${friend.mood.song.title}</span></div></div></div>`;
                        }
                    } else if (activity) {
                        if (activity.activity_type === 'playing' && activity.song)
                            activityText = `<div style="display: flex; align-items: center;"><i class="bi bi-music-note-beamed text-info" style="font-size: 0.85rem; margin-right: 2px;"></i> <div class="marquee-wrapper" style="flex-grow: 1; min-width: 0; max-width: 120px; height: 16px;"><div class="marquee-left"><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${activity.song.title}</span><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${activity.song.title}</span></div></div></div>`;
                        else if (activity.activity_type === 'mood')
                            activityText = `<i class="bi bi-emoji-smile text-warning"></i> ${activity.extra_text}`;
                    }
                } else if (friend.mood) {
                    const moodEmoji = friend.mood.mood_type?.emoji ? `<span style="font-size: 1.1rem; margin-bottom: 2px; display: inline-block;">${friend.mood.mood_type.emoji}</span>` : `<i class="bi bi-emoji-smile text-warning"></i>`;
                    const statusText = friend.mood.status_text ? ` <span style="color: rgba(255,255,255,0.85);">${friend.mood.status_text}</span>` : '';
                    activityText = `${moodEmoji}${statusText}`;
                    if (friend.mood.song) {
                        activityText += `<br><div style="margin-top: 2px; display: flex; align-items: center;"><i class="bi bi-music-note-beamed text-info" style="font-size: 0.85rem; margin-right: 2px;"></i> <div class="marquee-wrapper" style="flex-grow: 1; min-width: 0; max-width: 120px; height: 16px;"><div class="marquee-left"><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${friend.mood.song.title}</span><span class="marquee-text text-white" style="font-size: 0.75rem; padding-right: 20px;">${friend.mood.song.title}</span></div></div></div>`;
                    }
                }

                return {
                    id: friend.id,
                    name: friend.display_name,
                    avatar: friend.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80',
                    isOnline, activityText, timeText,
                    lastActiveDate: activity ? new Date(activity.created_at) : new Date(0),
                    mood: friend.mood
                };
            });

            friendsData.sort((a, b) => {
                if (a.isOnline !== b.isOnline) return b.isOnline - a.isOnline;
                return b.lastActiveDate - a.lastActiveDate;
            });

            if (!keyword) {
                allFriends = friendsData;
            }
            renderFriends(friendsData, !!keyword);
        } catch (error) {
            console.error("Lỗi khi tải hoạt động bạn bè:", error);
            activityContainers.forEach(c => {
                if (c) c.innerHTML = '<div class="text-center text-muted-custom py-4 small">Lỗi tải dữ liệu.</div>';
            });
        }
    }

    function renderFriends(friendsList, isSearch = false) {
        let html = '';
        let onlineCount = 0;

        if (friendsList.length === 0) {
            html = `<div class="text-center text-muted-custom py-4 small">${isSearch ? 'Không tìm thấy bạn bè nào.' : 'Bạn chưa theo dõi ai.'}</div>`;
        } else {
            friendsList.forEach(friend => {
                if (friend.isOnline) onlineCount++;
                const opacityClass = friend.isOnline ? '' : 'opacity-75';
                const dotHtml = `<div class="online-dot" style="background-color: ${friend.isOnline ? 'rgb(140, 225, 178)' : 'white'}; border-color: #121929;"></div>`;
                const activityHtml = friend.activityText
                    ? `<div class="friend-song mt-1 text-muted-custom" style="font-size:0.75rem;" title="${friend.activityText.replace(/<[^>]*>?/gm, '')}">${friend.activityText}</div>`
                    : '';
                const grayscaleClass = friend.isOnline ? '' : 'grayscale';
                const timeHtml = `<div class="friend-time mt-1 text-muted-custom" style="font-size:0.7rem;">${friend.timeText}</div>`;

                html += `
                <div class="friend-item ${opacityClass}" style="display:flex;align-items:center;padding:10px 0;cursor:pointer;" data-user-id="${friend.id}" onclick="window.goToPage('/profile/${friend.id}/')">
                    <a href="/profile/${friend.id}/" class="friend-avatar text-decoration-none" style="width:40px;height:40px;position:relative;flex-shrink:0;margin-right:12px;" title="Xem hồ sơ" onclick="event.stopPropagation();">
                        <img src="${friend.avatar}" alt="Avatar" class="w-100 h-100 rounded-circle object-fit-cover ${grayscaleClass}">
                        ${dotHtml}
                    </a>
                    <div class="friend-info" style="flex-grow:1;overflow:hidden;">
                        <div class="d-flex justify-content-between align-items-center">
                            <a href="/profile/${friend.id}/" class="friend-name fw-semibold text-white text-decoration-none" style="font-size:0.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" onclick="event.stopPropagation();">${friend.name}</a>
                        </div>
                        ${activityHtml}${timeHtml}
                    </div>
                </div>`;
            });
        }

        activityContainers.forEach(c => { if (c) c.innerHTML = html; });
        onlineCountElements.forEach(el => {
            if (el) el.innerHTML = `${onlineCount} online <i class="bi bi-people"></i>`;
        });
    }

    // ─── API Friend Search ────────────────────────────────────────────────
    searchInputs.forEach(input => {
        if (!input) return;
        let searchTimeout = null;
        input.addEventListener('input', e => {
            clearTimeout(searchTimeout);
            const keyword = e.target.value.trim();
            if (keyword.length === 0) {
                renderFriends(allFriends, false);
                return;
            }
            
            activityContainers.forEach(c => {
                if (c) c.innerHTML = '<div class="text-center text-muted-custom py-4 small"><div class="spinner-border spinner-border-sm" role="status"></div><span class="ms-2">Đang tìm...</span></div>';
            });
            
            searchTimeout = setTimeout(() => {
                loadFriendActivity(keyword);
            }, 300);
        });
    });

    // ─── Load My Mood Badge ─────────────────────────────────────────────────
    async function loadMyMoodBadge() {
        const myMoodTag = document.getElementById('myMoodBadge');
        if (!myMoodTag) return;

        try {
            const res = await fetch('/api/v1/social/me/mood/');
            if (!res.ok) return;
            const data = await res.json();
            
            if (data.success && data.data) {
                const mood = data.data;
                myMoodTag.style.display = 'inline-block';
                if (mood.theme) {
                    myMoodTag.style.background = `linear-gradient(135deg, ${mood.theme.gradient_from}, ${mood.theme.gradient_to})`;
                }
                myMoodTag.style.color = '#fff';

                let contentHtml = '';
                if (mood.mood_type) {
                    contentHtml = `<span class="me-1">${mood.mood_type.emoji || '<i class="bi bi-emoji-smile"></i>'}</span> ${mood.mood_type.name}`;
                } else {
                    contentHtml = `<i class="bi bi-chat-fill me-1"></i> ${mood.status_text || 'Đang cảm thấy...'}`;
                }
                myMoodTag.innerHTML = contentHtml;
                myMoodTag.title = mood.status_text || 'Tâm trạng hiện tại của bạn';
            } else {
                myMoodTag.style.display = 'none';
            }
        } catch (error) {
            console.error("Lỗi khi tải mood badge:", error);
            myMoodTag.style.display = 'none';
        }
    }

    loadFriendActivity();
    loadMyMoodBadge();
    setInterval(loadFriendActivity, 60000);


    // ═══════════════════════════════════════════════════════════════════════
    // ADD FRIEND MODAL (Tìm kiếm & Follow)
    // ═══════════════════════════════════════════════════════════════════════
    const globalSearchInput = document.getElementById('globalUserSearchInput');
    const globalSearchResults = document.getElementById('globalUserSearchResults');
    let searchTimeout = null;

    if (globalSearchInput && globalSearchResults) {
        const addFriendModal = document.getElementById('addFriendModal');
        if (addFriendModal) {
            addFriendModal.addEventListener('show.bs.modal', () => {
                globalSearchInput.value = '';
                globalSearchResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Nhập từ khóa để tìm kiếm...</div>';
            });
        }

        globalSearchInput.addEventListener('input', e => {
            const query = e.target.value.trim();
            clearTimeout(searchTimeout);
            if (!query) {
                globalSearchResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Nhập từ khóa để tìm kiếm...</div>';
                return;
            }
            globalSearchResults.innerHTML = '<div class="text-center text-muted-custom py-3 small"><div class="spinner-border spinner-border-sm" role="status"></div><span class="ms-2">Đang tìm...</span></div>';

            searchTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/v1/search/users/?q=${encodeURIComponent(query)}&t=${Date.now()}`);
                    const data = await res.json();
                    if (data.success && data.data?.items) {
                        renderGlobalSearchResults(data.data.items);
                    } else {
                        globalSearchResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Không tìm thấy kết quả.</div>';
                    }
                } catch {
                    globalSearchResults.innerHTML = '<div class="text-center text-danger py-3 small">Lỗi kết nối.</div>';
                }
            }, 300);
        });
    }

    function renderGlobalSearchResults(users, container = globalSearchResults) {
        const filtered = users.filter(u => u.id !== window.CURRENT_USER_ID);
        if (!filtered.length) {
            container.innerHTML = '<div class="text-center text-muted-custom py-3 small">Không tìm thấy người dùng.</div>';
            return;
        }
        let html = '';
        filtered.forEach(user => {
            const avatar = user.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80';
            const isArtist = user.role === 'artist';
            const artistBadge = isArtist ? ' <i class="bi bi-patch-check-fill" style="color: var(--accent-color); font-size:0.8rem;"></i>' : '';

            let btnClass = 'btn-outline-light';
            let btnText = isArtist ? 'Theo dõi' : 'Kết bạn';
            let inlineStyle = 'flex-shrink:0;min-width:120px; ';

            if (user.follow_status === 'following') {
                btnClass = 'btn-following';
                btnText = 'Đang theo dõi';
                inlineStyle += 'background-color: rgb(140, 225, 178) !important; color: #121929 !important; border: none !important;';
            }
            else if (user.follow_status === 'requested') {
                btnClass = 'btn-requested';
                btnText = 'Đã gửi yêu cầu';
                inlineStyle += 'background-color: var(--accent-color) !important; color: var(--bg-app) !important; border: none !important;';
            }

            html += `
            <div class="d-flex align-items-center justify-content-between pb-3 mb-3 border-bottom border-secondary border-opacity-25">
                <div class="d-flex align-items-center gap-3" style="overflow:hidden;">
                    <img src="${avatar}" class="rounded-circle" style="width:45px;height:45px;object-fit:cover;flex-shrink:0;">
                    <div style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        <h6 class="mb-0 fw-bold">${user.display_name || user.username}${artistBadge}</h6>
                        <small class="text-secondary">@${user.username}</small>
                    </div>
                </div>
                <button class="btn btn-sm ${btnClass} rounded-pill px-3 fw-semibold search-follow-btn"
                    style="${inlineStyle}"
                    data-user-id="${user.id}"
                    data-follow-status="${user.follow_status || 'none'}">
                    ${btnText}
                </button>
            </div>`;
        });

        container.innerHTML = html;

        container.querySelectorAll('.search-follow-btn').forEach(btn => {
            btn.addEventListener('click', async function () {
                const userId = this.dataset.userId;
                const origHtml = this.innerHTML;
                const csrf = getCookie('csrftoken');

                this.disabled = true;
                this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

                try {
                    const res = await fetch(`/api/v1/social/users/${userId}/follow/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' }
                    });
                    const result = await res.json();
                    if (result.success) {
                        const action = result.data.action;
                        let newStatus = 'none', newClass = 'btn-outline-light', newText = 'Kết bạn';
                        if (action === 'followed') {
                            newStatus = 'following'; newClass = 'btn-following'; newText = 'Đang theo dõi';
                            this.style.cssText = 'flex-shrink:0;min-width:120px; background-color: rgb(140, 225, 178) !important; color: #121929 !important; border: none !important;';
                        }
                        else if (action === 'request_sent') {
                            newStatus = 'requested'; newClass = 'btn-requested'; newText = 'Đã gửi yêu cầu';
                            this.style.cssText = 'flex-shrink:0;min-width:120px; background-color: var(--accent-color) !important; color: var(--bg-app) !important; border: none !important;';
                        }
                        this.dataset.followStatus = newStatus;
                        this.className = `btn btn-sm ${newClass} rounded-pill px-3 fw-semibold search-follow-btn`;
                        this.innerText = newText;
                        if (action !== 'request_sent' && action !== 'followed') { this.style.cssText = 'flex-shrink:0;min-width:120px;'; }
                        if (action === 'followed' || action === 'unfollowed') loadFriendActivity();
                    } else {
                        alert(result.error?.message || 'Có lỗi xảy ra');
                        this.innerHTML = origHtml;
                    }
                } catch { alert('Lỗi kết nối mạng'); this.innerHTML = origHtml; }
                finally { this.disabled = false; }
            });
        });
    }


    // ═══════════════════════════════════════════════════════════════════════
    // RECEIVED REQUESTS MODAL (Yêu cầu nhận được)
    // ═══════════════════════════════════════════════════════════════════════
    const receivedModal = document.getElementById('receivedRequestsModal');
    if (receivedModal) {
        receivedModal.addEventListener('show.bs.modal', () => loadReceivedRequests());
    }

    async function loadReceivedRequests() {
        const container = document.getElementById('receivedRequestsList');
        if (!container) return;
        container.innerHTML = loadingHtml();
        try {
            const res = await fetch('/api/v1/social/follow-requests/received/');
            const data = await res.json();
            if (data.success) renderReceivedRequests(data.data.items, container);
            else container.innerHTML = emptyHtml('Không thể tải dữ liệu.');
        } catch { container.innerHTML = errorHtml(); }
    }

    function renderReceivedRequests(items, container) {
        if (!items.length) { container.innerHTML = emptyHtml('Bạn không có yêu cầu kết bạn nào.'); return; }
        let html = '';
        items.forEach(req => {
            const avatar = req.sender.avatar || defaultAvatar();
            html += `
            <div class="d-flex align-items-center justify-content-between pb-3 mb-2 border-bottom border-secondary border-opacity-25" id="recv-req-${req.id}" style="transition:opacity 0.3s;">
                <div class="d-flex align-items-center gap-3" style="overflow:hidden;">
                    <img src="${avatar}" class="rounded-circle" style="width:45px;height:45px;object-fit:cover;flex-shrink:0;">
                    <div>
                        <h6 class="mb-0 fw-bold">${req.sender.display_name || req.sender.username}</h6>
                        <small class="text-secondary">@${req.sender.username}</small>
                    </div>
                </div>
                <div class="d-flex gap-2" style="flex-shrink:0;">
                    <button class="btn btn-sm rounded-pill px-3 fw-semibold req-action-btn"
                        style="background:var(--accent-color);color:#121929;border:none;"
                        data-req-id="${req.id}" data-action="accept">Chấp nhận</button>
                    <button class="btn btn-sm btn-outline-danger rounded-pill px-3 fw-semibold req-action-btn"
                        data-req-id="${req.id}" data-action="reject">Từ chối</button>
                </div>
            </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.req-action-btn').forEach(btn => {
            btn.addEventListener('click', async function () {
                await handleRequestAction(this.dataset.reqId, this.dataset.action, `recv-req-${this.dataset.reqId}`, container, this);
                if (this.dataset.action === 'accept') loadFriendActivity();
            });
        });
    }


    // ═══════════════════════════════════════════════════════════════════════
    // SENT REQUESTS MODAL (Yêu cầu đã gửi)
    // ═══════════════════════════════════════════════════════════════════════
    const sentModal = document.getElementById('sentRequestsModal');
    if (sentModal) {
        sentModal.addEventListener('show.bs.modal', () => loadSentRequests());
    }

    async function loadSentRequests() {
        const container = document.getElementById('sentRequestsList');
        if (!container) return;
        container.innerHTML = loadingHtml();
        try {
            const res = await fetch('/api/v1/social/follow-requests/sent/');
            const data = await res.json();
            if (data.success) renderSentRequests(data.data.items, container);
            else container.innerHTML = emptyHtml('Không thể tải dữ liệu.');
        } catch { container.innerHTML = errorHtml(); }
    }

    function renderSentRequests(items, container) {
        if (!items.length) { container.innerHTML = emptyHtml('Bạn chưa gửi yêu cầu kết bạn nào.'); return; }
        let html = '';
        items.forEach(req => {
            const avatar = req.receiver.avatar || defaultAvatar();
            html += `
            <div class="d-flex align-items-center justify-content-between pb-3 mb-2 border-bottom border-secondary border-opacity-25" id="sent-req-${req.id}" style="transition:opacity 0.3s;">
                <div class="d-flex align-items-center gap-3" style="overflow:hidden;">
                    <img src="${avatar}" class="rounded-circle" style="width:45px;height:45px;object-fit:cover;flex-shrink:0;">
                    <div>
                        <h6 class="mb-0 fw-bold">${req.receiver.display_name || req.receiver.username}</h6>
                        <small class="text-secondary">@${req.receiver.username} · Chờ xác nhận</small>
                    </div>
                </div>
                <button class="btn btn-sm btn-outline-secondary rounded-pill px-3 fw-semibold req-cancel-btn"
                    data-req-id="${req.id}">Hủy yêu cầu</button>
            </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.req-cancel-btn').forEach(btn => {
            btn.addEventListener('click', async function () {
                await handleRequestAction(this.dataset.reqId, 'cancel', `sent-req-${this.dataset.reqId}`, container, this);
            });
        });
    }


    // ═══════════════════════════════════════════════════════════════════════
    // FRIENDS LIST MODAL (Danh sách bạn bè)
    // ═══════════════════════════════════════════════════════════════════════
    const friendsModal = document.getElementById('friendsListModal');
    if (friendsModal) {
        friendsModal.addEventListener('show.bs.modal', () => loadFriendsList());
    }

    async function loadFriendsList() {
        const container = document.getElementById('friendsListContainer');
        if (!container) return;
        container.innerHTML = loadingHtml();
        try {
            const res = await fetch('/api/v1/social/friends/');
            const data = await res.json();
            if (data.success) renderFriendsList(data.data.items, container);
            else container.innerHTML = emptyHtml('Không thể tải danh sách.');
        } catch { container.innerHTML = errorHtml(); }
    }

    function renderFriendsList(items, container) {
        if (!items.length) { container.innerHTML = emptyHtml('Bạn chưa có bạn bè nào.'); return; }
        let html = '';
        items.forEach(friend => {
            const avatar = friend.avatar || defaultAvatar();
            const isArtist = friend.role === 'artist';
            const badge = isArtist ? ' <i class="bi bi-patch-check-fill" style="color: var(--accent-color); font-size:0.8rem;"></i>' : '';
            html += `
            <div class="d-flex align-items-center justify-content-between pb-3 mb-2 border-bottom border-secondary border-opacity-25" id="friend-item-${friend.id}">
                <div class="d-flex align-items-center gap-3" style="overflow:hidden;">
                    <img src="${avatar}" class="rounded-circle" style="width:45px;height:45px;object-fit:cover;flex-shrink:0;">
                    <div>
                        <h6 class="mb-0 fw-bold">${friend.display_name || friend.username}${badge}</h6>
                        <small class="text-secondary">@${friend.username}</small>
                    </div>
                </div>
                <button class="btn btn-sm btn-outline-danger rounded-pill px-3 fw-semibold unfollow-btn"
                    data-user-id="${friend.id}">Hủy kết bạn</button>
            </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.unfollow-btn').forEach(btn => {
            btn.addEventListener('click', async function () {
                const userId = this.dataset.userId;
                const csrf = getCookie('csrftoken');
                this.disabled = true;
                this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
                try {
                    const res = await fetch(`/api/v1/social/users/${userId}/follow/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' }
                    });
                    const result = await res.json();
                    if (result.success) {
                        const item = document.getElementById(`friend-item-${userId}`);
                        if (item) { item.style.opacity = '0'; setTimeout(() => { item.remove(); checkEmpty(container, 'Bạn chưa có bạn bè nào.'); }, 300); }
                        loadFriendActivity();
                        // Refresh lại kết quả tìm kiếm nếu đang mở để cập nhật trạng thái nút
                        const searchInput = document.getElementById('globalUserSearchInput');
                        if (searchInput && searchInput.value.trim()) {
                            const q = searchInput.value.trim();
                            try {
                                const sRes = await fetch(`/api/v1/search/users/?q=${encodeURIComponent(q)}&t=${Date.now()}`);
                                const sData = await sRes.json();
                                if (sData.success && sData.data?.items) renderGlobalSearchResults(sData.data.items);
                            } catch { }
                        }
                    } else { alert(result.error?.message || 'Có lỗi xảy ra'); this.disabled = false; this.innerText = 'Hủy kết bạn'; }
                } catch { alert('Lỗi kết nối mạng'); this.disabled = false; this.innerText = 'Hủy kết bạn'; }
            });
        });
    }


    // ═══════════════════════════════════════════════════════════════════════
    // SHARED HELPERS
    // ═══════════════════════════════════════════════════════════════════════
    async function handleRequestAction(reqId, action, itemId, container, btn) {
        const item = document.getElementById(itemId);
        const origHtml = btn.innerHTML;
        const allBtns = item ? item.querySelectorAll('button') : [btn];
        allBtns.forEach(b => b.disabled = true);
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

        try {
            const res = await fetch(`/api/v1/social/follow-requests/${reqId}/${action}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' }
            });
            const result = await res.json();
            if (result.success && item) {
                item.style.opacity = '0';
                setTimeout(() => { item.remove(); checkEmpty(container); }, 300);
            } else {
                alert(result.error?.message || 'Có lỗi xảy ra');
                allBtns.forEach(b => b.disabled = false);
                btn.innerHTML = origHtml;
            }
        } catch {
            alert('Lỗi kết nối mạng');
            allBtns.forEach(b => b.disabled = false);
            btn.innerHTML = origHtml;
        }
    }

    function checkEmpty(container, msg = 'Danh sách trống.') {
        if (container && !container.querySelector('[id]')) {
            container.innerHTML = emptyHtml(msg);
        }
    }



    function defaultAvatar() {
        return 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80';
    }

    function loadingHtml() {
        return '<div class="text-center text-muted-custom py-4 small"><div class="spinner-border spinner-border-sm" role="status"></div><span class="ms-2">Đang tải...</span></div>';
    }

    function emptyHtml(msg) {
        return `<div class="text-center text-muted-custom py-4 small">${msg}</div>`;
    }

    function errorHtml() {
        return '<div class="text-center text-danger py-4 small">Lỗi kết nối. Vui lòng thử lại.</div>';
    }
});
