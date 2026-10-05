// === TAG BẠN BÈ FEATURE ===
// BUG FIX: Khi SPA router chạy lại script này qua fetchAndRun, nó wrap code vào
// (function(){...})() nên 'var taggedFriends' trở thành biến CỤC BỘ, không accessible
// từ posts.js. Fix: dùng window.taggedFriends để đảm bảo luôn là biến TOÀN CỤC.

window.taggedFriends = []; // [{ id, display_name, avatar }] - PHẢI là window để posts.js đọc được
var tagFriendSearchDebounce = null;

// Mở modal tag bạn bè
window.openTagFriendsModal = function() {
    const modalEl = document.getElementById('postTagFriendsModal');
    if (!modalEl) return;
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
};

// Render danh sách bạn bè trong modal
async function loadTagFriendList(query = '') {
    const listEl = document.getElementById('tagFriendList');
    if (!listEl) return;

    listEl.innerHTML = '<div class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm"></div></div>';

    try {
        const url = query
            ? `/api/v1/social/friends/?q=${encodeURIComponent(query)}`
            : '/api/v1/social/friends/';
        const res = await fetch(url);
        const data = await res.json();
        // API trả về: { success: true, data: { items: [...], pagination: {...} } }
        const friends = data.data?.items || [];

        if (!friends.length) {
            listEl.innerHTML = '<div class="text-center text-muted py-4"><i class="bi bi-people fs-3 d-block mb-2"></i>Không tìm thấy bạn bè</div>';
            return;
        }

        listEl.innerHTML = '';
        friends.forEach(friend => {
            const isSelected = window.taggedFriends.some(f => f.id === friend.id);
            const avatar = friend.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(friend.display_name)}&background=random`;

            const item = document.createElement('div');
            item.className = 'tag-friend-item d-flex align-items-center gap-3 px-3 py-2 rounded-3';
            item.style.cssText = 'cursor:pointer; transition: background 0.15s;';
            item.dataset.friendId = friend.id;
            item.innerHTML = `
                <img src="${avatar}" class="rounded-circle flex-shrink-0" width="42" height="42" style="object-fit:cover;">
                <div class="flex-grow-1 overflow-hidden">
                    <div class="text-white fw-semibold text-truncate" style="font-size:0.9rem;">${friend.display_name}</div>
                    ${friend.username ? `<div class="text-muted text-truncate" style="font-size:0.78rem;">@${friend.username}</div>` : ''}
                </div>
                <div class="tag-check-icon ${isSelected ? '' : 'd-none'}" style="width:24px;height:24px;border-radius:50%;background:#0d6efd;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <i class="bi bi-check2 text-white" style="font-size:0.85rem;"></i>
                </div>
                <div class="tag-uncheck-icon ${isSelected ? 'd-none' : ''}" style="width:24px;height:24px;border-radius:50%;border:2px solid rgba(255,255,255,0.2);flex-shrink:0;"></div>
            `;

            if (isSelected) item.style.backgroundColor = 'rgba(13,110,253,0.12)';

            item.addEventListener('mouseenter', () => {
                if (!window.taggedFriends.some(f => f.id === friend.id)) {
                    item.style.backgroundColor = 'rgba(255,255,255,0.07)';
                }
            });
            item.addEventListener('mouseleave', () => {
                if (!window.taggedFriends.some(f => f.id === friend.id)) {
                    item.style.backgroundColor = 'transparent';
                }
            });

            item.addEventListener('click', () => toggleTagFriend(friend, item));
            listEl.appendChild(item);
        });
    } catch (e) {
        listEl.innerHTML = '<div class="text-center text-danger py-4">Lỗi tải danh sách bạn bè</div>';
    }
}

// Toggle chọn/bỏ chọn bạn bè
function toggleTagFriend(friend, itemEl) {
    const idx = window.taggedFriends.findIndex(f => f.id === friend.id);
    const checkIcon = itemEl.querySelector('.tag-check-icon');
    const uncheckIcon = itemEl.querySelector('.tag-uncheck-icon');

    if (idx === -1) {
        // Thêm vào
        window.taggedFriends.push(friend);
        itemEl.style.backgroundColor = 'rgba(13,110,253,0.12)';
        checkIcon.classList.remove('d-none');
        checkIcon.style.display = 'flex';
        uncheckIcon.classList.add('d-none');
    } else {
        // Bỏ chọn
        window.taggedFriends.splice(idx, 1);
        itemEl.style.backgroundColor = 'transparent';
        checkIcon.classList.add('d-none');
        uncheckIcon.classList.remove('d-none');
    }

    updateTagSelectedChips();
}

// Cập nhật chips (tag đã chọn phía trên danh sách)
function updateTagSelectedChips() {
    const chipsEl = document.getElementById('tagSelectedChips');
    if (!chipsEl) return;

    if (!window.taggedFriends.length) {
        chipsEl.classList.add('d-none');
        return;
    }

    chipsEl.innerHTML = window.taggedFriends.map(f => {
        const avatar = f.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(f.display_name)}&background=random`;
        return `
            <div class="d-flex align-items-center gap-1 px-2 py-1 rounded-pill" style="background:rgba(13,110,253,0.18);font-size:0.78rem;">
                <img src="${avatar}" class="rounded-circle" width="20" height="20" style="object-fit:cover;">
                <span class="text-white">${f.display_name}</span>
                <button type="button" onclick="window.removeTagFromChips('${f.id}')" class="btn btn-link p-0 text-danger ms-1" style="font-size:0.7rem;line-height:1;"><i class="bi bi-x"></i></button>
            </div>
        `;
    }).join('');
    chipsEl.classList.remove('d-none');
}

// Xóa một tag từ chips
window.removeTagFromChips = function(friendId) {
    window.taggedFriends = window.taggedFriends.filter(f => f.id !== friendId);
    updateTagSelectedChips();
    applyTaggedFriendsToPost();
    // Cập nhật lại check icon trong danh sách
    const item = document.querySelector(`.tag-friend-item[data-friend-id="${friendId}"]`);
    if (item) {
        item.style.backgroundColor = 'transparent';
        item.querySelector('.tag-check-icon')?.classList.add('d-none');
        const uncheck = item.querySelector('.tag-uncheck-icon');
        if (uncheck) { uncheck.classList.remove('d-none'); uncheck.style.display = ''; }
    }
};

// Áp dụng tag vào badge trong createPostModal
function applyTaggedFriendsToPost() {
    const badge = document.getElementById('postTaggedFriendsBadge');
    const textEl = document.getElementById('postTaggedFriendsText');
    if (!badge || !textEl) return;

    if (!window.taggedFriends.length) {
        badge.classList.add('d-none');
        badge.classList.remove('d-inline-flex');
        return;
    }

    // Hiện tên: "An" hoặc "An và 2 người khác"
    let displayText = '';
    if (window.taggedFriends.length === 1) {
        displayText = window.taggedFriends[0].display_name;
    } else if (window.taggedFriends.length === 2) {
        displayText = `${window.taggedFriends[0].display_name} và ${window.taggedFriends[1].display_name}`;
    } else {
        displayText = `${window.taggedFriends[0].display_name} và ${window.taggedFriends.length - 1} người khác`;
    }

    textEl.textContent = displayText;
    badge.classList.remove('d-none');
    badge.classList.add('d-inline-flex');
}

// Khởi tạo sự kiện khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    const tagModalEl = document.getElementById('postTagFriendsModal');
    if (tagModalEl) {
        // Khi modal mở: load danh sách bạn bè + reset search input
        tagModalEl.addEventListener('shown.bs.modal', () => {
            const searchInput = document.getElementById('tagFriendSearchInput');
            if (searchInput) {
                searchInput.value = '';
                searchInput.focus();
            }
            loadTagFriendList();
            updateTagSelectedChips();
        });

        // BUG FIX: Bind input listener MỘT LẦN duy nhất trong DOMContentLoaded,
        // KHÔNG bind bên trong shown.bs.modal (sẽ gây duplicate listener mỗi lần mở modal)
        const searchInput = document.getElementById('tagFriendSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', function() {
                clearTimeout(tagFriendSearchDebounce);
                tagFriendSearchDebounce = setTimeout(() => loadTagFriendList(this.value.trim()), 350);
            });
        }
    }

    // Nút xác nhận trong tag modal
    const confirmBtn = document.getElementById('confirmTagFriendsBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            applyTaggedFriendsToPost();
            const bsModal = bootstrap.Modal.getInstance(tagModalEl);
            if (bsModal) bsModal.hide();

            // Sau khi modal đóng, mở lại createPostModal nếu chưa mở
            const createModalEl = document.getElementById('createPostModal');
            if (createModalEl && !createModalEl.classList.contains('show')) {
                tagModalEl.addEventListener('hidden.bs.modal', function openCreate() {
                    tagModalEl.removeEventListener('hidden.bs.modal', openCreate);
                    bootstrap.Modal.getOrCreateInstance(createModalEl).show();
                });
            }
        });
    }

    // Nút xóa tag khỏi badge
    const removeTagBtn = document.getElementById('removeTaggedFriendsBtn');
    if (removeTagBtn) {
        removeTagBtn.addEventListener('click', () => {
            window.taggedFriends = [];
            applyTaggedFriendsToPost();
        });
    }

    // Reset khi createPostModal đóng thực sự (không phải do mở tag modal đè lên)
    const createModalEl = document.getElementById('createPostModal');
    if (createModalEl) {
        createModalEl.addEventListener('hidden.bs.modal', () => {
            // Không clear nếu tag modal đang mở (bootstrap chưa đóng createPostModal xong)
            const tagModal = document.getElementById('postTagFriendsModal');
            if (tagModal && tagModal.classList.contains('show')) return;
            // Không clear nếu feeling modal đang mở
            const feelingModal = document.getElementById('postFeelingModal');
            if (feelingModal && feelingModal.classList.contains('show')) return;

            window.taggedFriends = [];
            applyTaggedFriendsToPost();
        });
    }
});
