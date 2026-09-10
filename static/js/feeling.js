// === FEELING / ACTIVITY FEATURE ===
// Data: danh sách cảm xúc giống Facebook
var FEELINGS_DATA = [
    { emoji: '😊', label: 'hạnh phúc' },
    { emoji: '😍', label: 'yêu đời' },
    { emoji: '😎', label: 'tuyệt vời' },
    { emoji: '🥰', label: 'đang yêu' },
    { emoji: '😂', label: 'vui nhộn' },
    { emoji: '🤩', label: 'phấn khích' },
    { emoji: '😤', label: 'quyết tâm' },
    { emoji: '😏', label: 'tự tin' },
    { emoji: '😌', label: 'thư giãn' },
    { emoji: '🥳', label: 'đang ăn mừng' },
    { emoji: '😴', label: 'buồn ngủ' },
    { emoji: '😑', label: 'chán nản' },
    { emoji: '😪', label: 'mệt mỏi' },
    { emoji: '😢', label: 'buồn bã' },
    { emoji: '😭', label: 'rất buồn' },
    { emoji: '😣', label: 'bực bội' },
    { emoji: '😤', label: 'tức giận' },
    { emoji: '🤔', label: 'đang suy nghĩ' },
    { emoji: '🤒', label: 'đang ốm' },
    { emoji: '😰', label: 'lo lắng' },
    { emoji: '😨', label: 'sợ hãi' },
    { emoji: '🤯', label: 'choáng ngợp' },
    { emoji: '🥺', label: 'xúc động' },
    { emoji: '🤗', label: 'được quan tâm' },
    { emoji: '😶', label: 'không muốn nói' },
    { emoji: '🙏', label: 'biết ơn' },
    { emoji: '💪', label: 'tràn đầy năng lượng' },
    { emoji: '🏠', label: 'ở nhà' },
    { emoji: '☕', label: 'đang uống cà phê' },
    { emoji: '🎵', label: 'đang nghe nhạc' },
    { emoji: '📚', label: 'đang học bài' },
    { emoji: '✈️', label: 'đang du lịch' },
    { emoji: '🍜', label: 'đang ăn uống' },
    { emoji: '🎮', label: 'đang chơi game' },
    { emoji: '🏋️', label: 'đang tập gym' },
];

window.currentFeeling = null; // { emoji, label }

function renderFeelingList(filter = '') {
    const list = document.getElementById('feelingList');
    if (!list) return;

    const filtered = filter
        ? FEELINGS_DATA.filter(f => f.label.toLowerCase().includes(filter.toLowerCase()) || f.emoji.includes(filter))
        : FEELINGS_DATA;

    if (!filtered.length) {
        list.innerHTML = '<div class="text-center text-muted py-4">Không tìm thấy cảm xúc nào</div>';
        return;
    }

    list.innerHTML = filtered.map(f => `
        <div class="feeling-item d-flex align-items-center gap-3 px-3 py-2 rounded-3"
             style="cursor:pointer; transition: background 0.15s;"
             onclick="selectFeeling('${f.emoji}', '${f.label}')">
            <span style="font-size: 1.8rem; line-height:1;">${f.emoji}</span>
            <span class="text-white" style="font-size:0.95rem;">đang <strong>${f.label}</strong></span>
        </div>
    `).join('');

    // Hover effects
    list.querySelectorAll('.feeling-item').forEach(el => {
        el.addEventListener('mouseenter', () => el.style.backgroundColor = 'rgba(255,255,255,0.08)');
        el.addEventListener('mouseleave', () => el.style.backgroundColor = 'transparent');
    });
}

window.selectFeeling = function(emoji, label) {
    window.currentFeeling = { emoji, label };

    // Đóng feeling modal
    const feelingModalEl = document.getElementById('postFeelingModal');
    const bsFeelingModal = bootstrap.Modal.getInstance(feelingModalEl);
    if (bsFeelingModal) bsFeelingModal.hide();

    // Khi modal đóng xong mới mở createPostModal
    const openCreate = function() {
        feelingModalEl.removeEventListener('hidden.bs.modal', openCreate);
        applyFeelingToPost();
        // Mở createPostModal nếu chưa mở
        const createModalEl = document.getElementById('createPostModal');
        if (createModalEl) bootstrap.Modal.getOrCreateInstance(createModalEl).show();
    };

    // Nếu createPostModal đã đang mở (gọi từ icon bên trong) thì chỉ apply không cần đợi
    const createModalEl = document.getElementById('createPostModal');
    const existingModal = bootstrap.Modal.getInstance(createModalEl);
    if (existingModal && createModalEl.classList.contains('show')) {
        applyFeelingToPost();
    } else {
        feelingModalEl.addEventListener('hidden.bs.modal', openCreate);
    }
}

window.applyFeelingToPost = function() {
    if (!window.currentFeeling) return;
    const badge = document.getElementById('postFeelingBadge');
    const textEl = document.getElementById('postFeelingText');
    if (badge && textEl) {
        textEl.textContent = `${window.currentFeeling.emoji} ${window.currentFeeling.label}`;
        badge.classList.remove('d-none');
        badge.classList.add('d-inline-flex');
    }
}

// Mở modal cảm xúc (từ nút ngoài feed - luồng độc lập)
window.openFeelingFlow = function() {
    openFeelingModal();
};

// Mở modal cảm xúc (dùng chung)
window.openFeelingModal = function() {
    const feelingModalEl = document.getElementById('postFeelingModal');
    if (!feelingModalEl) return;

    // Reset search
    const searchInput = document.getElementById('feelingSearchInput');
    if (searchInput) searchInput.value = '';
    renderFeelingList();

    bootstrap.Modal.getOrCreateInstance(feelingModalEl).show();
};

// Khởi tạo khi DOM sẵn sàng
document.addEventListener('DOMContentLoaded', () => {
    const feelingModalEl = document.getElementById('postFeelingModal');
    if (feelingModalEl) {
        feelingModalEl.addEventListener('shown.bs.modal', () => {
            renderFeelingList();
            const inp = document.getElementById('feelingSearchInput');
            if (inp) {
                inp.value = '';
                inp.focus();
            }
        });

        // BUG FIX: Bind input listener ONCE
        const inp = document.getElementById('feelingSearchInput');
        if (inp) {
            inp.addEventListener('input', function() {
                renderFeelingList(this.value.trim());
            });
        }
    }

    // Nút xóa cảm xúc trong createPostModal
    const removeFeelingBtn = document.getElementById('removeFeelingBtn');
    if (removeFeelingBtn) {
        removeFeelingBtn.addEventListener('click', () => {
            window.currentFeeling = null;
            const badge = document.getElementById('postFeelingBadge');
            if (badge) {
                badge.classList.add('d-none');
                badge.classList.remove('d-inline-flex');
            }
        });
    }

    // Reset feeling khi createPostModal đóng
    const createModalEl = document.getElementById('createPostModal');
    if (createModalEl) {
        createModalEl.addEventListener('hidden.bs.modal', () => {
            // Không clear nếu feeling modal đang mở (bootstrap chưa đóng createPostModal xong)
            const feelingModal = document.getElementById('postFeelingModal');
            if (feelingModal && feelingModal.classList.contains('show')) return;
            // Không clear nếu tag modal đang mở
            const tagModal = document.getElementById('postTagFriendsModal');
            if (tagModal && tagModal.classList.contains('show')) return;

            window.currentFeeling = null;
            const badge = document.getElementById('postFeelingBadge');
            if (badge) {
                badge.classList.add('d-none');
                badge.classList.remove('d-inline-flex');
            }
        });
    }
});
