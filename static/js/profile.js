function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

async function loadStats() {
    try {
        const targetUserId = window.TARGET_USER_ID;
        const res = await fetch(`/api/v1/social/users/${targetUserId}/follow-status/`);
        const data = await res.json();
        if (data.success) {
            const followersEl = document.getElementById('followersCount');
            const followingEl = document.getElementById('followingCount');
            if (followersEl) followersEl.innerText = formatNumber(data.data.followers_count || 0);
            if (followingEl) followingEl.innerText = formatNumber(data.data.following_count || 0);
        }

        const likesEl = document.getElementById('totalLikesCount');
        if (likesEl) {
            const statsRes = await fetch('/api/v1/artists/me/stats/');
            if (statsRes.ok) {
                const statsData = await statsRes.json();
                if (statsData.success) {
                    likesEl.innerText = formatNumber(statsData.data.total_likes || 0);
                }
            }
        }
    } catch (e) {
        console.error("Lỗi khi tải thống kê", e);
    }
}

class ProfilePaginator {
    constructor(config) {
        this.url = config.url;
        this.allContainerId = config.allContainerId;
        this.overviewContainerId = config.overviewContainerId;
        this.renderItem = config.renderItem;
        this.emptyMsg = config.emptyMsg;
        this.onItemsLoaded = config.onItemsLoaded;

        this.page = 1;
        this.limit = 20;
        this.hasMore = true;
        this.isLoading = false;
        this.items = [];

        this.init();
    }

    async init() {
        await this.loadMore();
        this.setupObserver();
    }

    async loadMore() {
        if (this.isLoading || !this.hasMore) return;
        this.isLoading = true;

        try {
            const sep = this.url.includes('?') ? '&' : '?';
            const res = await fetch(`${this.url}${sep}limit=${this.limit}&page=${this.page}`);
            const json = await res.json();
            let newItems = [];
            if (json.success && json.data) {
                newItems = Array.isArray(json.data) ? json.data : (json.data.items || []);
            }

            if (newItems.length < this.limit) {
                this.hasMore = false;
            }

            this.items = [...this.items, ...newItems];
            if (this.onItemsLoaded) this.onItemsLoaded(this.items);
            this.render();
            this.page++;
        } catch (e) {
            console.error('Error loading', this.url, e);
        } finally {
            this.isLoading = false;
        }
    }

    render() {
        const allContainer = document.getElementById(this.allContainerId);
        const overviewContainer = document.getElementById(this.overviewContainerId);

        if (this.items.length === 0) {
            const emptyHtml = `<div class="text-secondary py-3 text-center small w-100" style="grid-column: 1/-1;">${this.emptyMsg}</div>`;
            if (allContainer) allContainer.innerHTML = emptyHtml;
            if (overviewContainer) overviewContainer.innerHTML = emptyHtml;
            return;
        }

        const htmlAll = this.items.map(this.renderItem).join('');
        // Hiển thị 6 thẻ trên mobile (vừa đủ 3 hàng x 2 cột), 5 thẻ trên máy tính (1 hàng x 5 cột)
        const maxOverview = window.innerWidth <= 768 ? 6 : 5;
        const htmlOverview = this.items.slice(0, maxOverview).map(this.renderItem).join('');

        if (allContainer) {
            allContainer.innerHTML = htmlAll;
            if (this.hasMore) {
                allContainer.innerHTML += `<div id="sentinel-${this.allContainerId}" class="w-100 py-3 text-center" style="grid-column: 1/-1;"><div class="spinner-border spinner-border-sm text-secondary"></div></div>`;
            }
        }
        if (overviewContainer) overviewContainer.innerHTML = htmlOverview;
    }

    setupObserver() {
        const allContainer = document.getElementById(this.allContainerId);
        if (!allContainer) return;

        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                this.loadMore();
            }
        }, { rootMargin: '100px' });

        const mo = new MutationObserver(() => {
            const sentinel = document.getElementById(`sentinel-${this.allContainerId}`);
            if (sentinel) observer.observe(sentinel);
        });
        mo.observe(allContainer, { childList: true });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadStats();

    const targetUserId = window.TARGET_USER_ID;

    // Block User Logic
    const blockUserBtn = document.getElementById('btn-block-user');
    if (blockUserBtn) {
        blockUserBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Close dropdown if open
            const menu = blockUserBtn.closest('.custom-dropdown-menu');
            if (menu) menu.style.display = 'none';

            const textSpan = document.getElementById('block-user-text');
            const isUnblocking = textSpan.innerText.includes('Bỏ chặn');
            
            const modalTitle = document.getElementById('blockConfirmModalTitle');
            const modalBody = document.getElementById('blockConfirmModalBody');
            const confirmBtn = document.getElementById('btn-confirm-block-action');
            
            if (isUnblocking) {
                modalTitle.innerText = 'Xác nhận bỏ chặn';
                modalBody.innerText = 'Bạn có chắc chắn muốn bỏ chặn người dùng này? Họ sẽ có thể tương tác lại với bạn.';
                confirmBtn.innerText = 'Bỏ chặn';
            } else {
                modalTitle.innerText = 'Xác nhận chặn';
                modalBody.innerText = 'Bạn có chắc chắn muốn chặn người dùng này không? Họ sẽ không thể tương tác với bạn nữa.';
                confirmBtn.innerText = 'Chặn';
            }
            
            const blockModalEl = document.getElementById('blockConfirmModal');
            let blockModal = bootstrap.Modal.getInstance(blockModalEl);
            if (!blockModal) blockModal = new bootstrap.Modal(blockModalEl);
            blockModal.show();
            
            const newConfirmBtn = confirmBtn.cloneNode(true);
            confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
            
            newConfirmBtn.addEventListener('click', async () => {
                const originalText = newConfirmBtn.innerText;
                newConfirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...';
                newConfirmBtn.disabled = true;

                try {
                    const res = await fetch(`/api/v1/accounts/users/${targetUserId}/block/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'Content-Type': 'application/json'
                        }
                    });
                    const data = await res.json();
                    if (data.success) {
                        const isBlocked = data.data.action === 'blocked';
                        textSpan.innerText = isBlocked ? 'Bỏ chặn người dùng' : 'Chặn người dùng';
                        if (window.showToast) window.showToast(isBlocked ? 'Đã chặn người dùng thành công' : 'Đã bỏ chặn người dùng', 'success');
                        
                        blockModal.hide();
                        setTimeout(() => window.goToPage(window.location.pathname + window.location.search), 1500);
                    } else {
                        throw new Error(data.error?.message || 'Lỗi khi thực hiện thao tác');
                    }
                } catch (err) {
                    console.error(err);
                    if (window.showToast) window.showToast(err.message, 'error');
                    newConfirmBtn.innerText = originalText;
                    newConfirmBtn.disabled = false;
                }
            });
        });
    }

    new ProfilePaginator({
        url: `/api/v1/music/users/${targetUserId}/likes/`,
        allContainerId: 'allLikedSongsContainer',
        overviewContainerId: 'likedSongsContainer',
        emptyMsg: 'Chưa có bài hát yêu thích nào',
        renderItem: song => `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                </div>
                <div class="card-title">${song.title}</div>
                <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                <a href="/song/?id=${song.id}" class="stretched-link"></a>
            </div>`
    });

    new ProfilePaginator({
        url: `/api/v1/music/users/${targetUserId}/albums/`,
        allContainerId: 'allAlbumsContainer',
        overviewContainerId: 'albumsContainer',
        emptyMsg: 'Chưa có album nào',
        renderItem: album => `
            <a href="/album/detail/?id=${album.id}" class="playlist-card position-relative text-decoration-none text-reset" style="width: 100%; min-width: 0; cursor: pointer; display:block;">
                <div class="card-image-wrapper">
                    <img src="${album.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${album.title}">
                </div>
                <div class="card-title">${album.title}</div>
                <div class="card-subtitle">${album.song_count} bài hát</div>
            </a>`
    });

    new ProfilePaginator({
        url: `/api/v1/playlists/?user_id=${targetUserId}`,
        allContainerId: 'allPlaylistContainer',
        overviewContainerId: 'overviewPlaylistContainer',
        emptyMsg: 'Chưa có playlist nào',
        onItemsLoaded: (items) => {
            const el = document.getElementById('overviewPlaylistCount');
            if (el) el.textContent = items.length > 0 ? `(${items.length})` : '';
        },
        renderItem: pl => `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${pl.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${pl.title}">
                </div>
                <div class="card-title">${pl.title}</div>
                <div class="card-subtitle">${pl.song_count !== undefined ? pl.song_count + ' bài' : ''}</div>
                <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
            </div>`
    });

    new ProfilePaginator({
        url: `/api/v1/music/me/history/`,
        allContainerId: 'allRecentContainer',
        overviewContainerId: 'recentSongsContainerOverview',
        emptyMsg: 'Chưa có lịch sử nghe',
        renderItem: item => {
            const song = item.song || item;
            return `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                </div>
                <div class="card-title">${song.title}</div>
                <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                <a href="/song/?id=${song.id}" class="stretched-link"></a>
            </div>`;
        }
    });
});

window.switchToTab = function (tabName) {
    const tab = document.querySelector(`.profile-tab[data-tab="${tabName}"]`);
    if (tab) {
        tab.click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};

document.querySelectorAll('.profile-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-section').forEach(s => s.style.display = 'none');
        tab.classList.add('active');
        const targetId = 'tab-' + tab.dataset.tab;
        const section = document.getElementById(targetId);
        if (section) section.style.display = 'block';
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const avatarInput = document.getElementById('avatarInput');
    const avatarPreview = document.getElementById('avatarPreview');
    if (avatarInput && avatarPreview) {
        avatarInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    avatarPreview.src = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        });
    }

    const coverInput = document.getElementById('coverInput');
    const coverPreview = document.getElementById('coverPreview');
    if (coverInput && coverPreview) {
        coverInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    coverPreview.src = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        });
    }
});

async function saveImages() {
    const avatarInput = document.getElementById('avatarInput');
    const coverInput = document.getElementById('coverInput');

    const formData = new FormData();
    let hasFile = false;

    if (avatarInput && avatarInput.files.length > 0) {
        formData.append('avatar', avatarInput.files[0]);
        hasFile = true;
    }

    if (coverInput && coverInput.files.length > 0) {
        formData.append('cover', coverInput.files[0]);
        hasFile = true;
    }

    if (!hasFile) {
        return;
    }

    try {
        if (window.showToast) {
            window.showToast('Đang tải ảnh lên hệ thống, vui lòng đợi...', 'info');
        }

        const csrfToken = getCookie('csrftoken');
        const response = await fetch('/api/v1/accounts/me/images/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });

        const result = await response.json();
        if (response.ok && result.success) {
            if (window.showToast) {
                window.showToast('Cập nhật ảnh thành công!', 'success');
                setTimeout(() => {
                    window.goToPage(window.location.pathname + window.location.search);
                }, 1500);
            } else {
                window.goToPage(window.location.pathname + window.location.search);
            }
        } else {
            console.error('Lỗi khi lưu hình ảnh:', result);
            if (window.showToast) {
                window.showToast(result.error?.message || 'Có lỗi xảy ra khi lưu hình ảnh', 'error');
            } else {
                alert(result.error?.message || 'Có lỗi xảy ra khi lưu hình ảnh');
            }
        }
    } catch (e) {
        console.error('Lỗi khi lưu hình ảnh:', e);
        if (window.showToast) {
            window.showToast('Có lỗi xảy ra khi lưu hình ảnh', 'error');
        } else {
            alert('Có lỗi xảy ra khi lưu hình ảnh');
        }
    }
}

window.saveSocials = async function () {
    const websiteInput = document.getElementById('websiteInput');
    const facebookInput = document.getElementById('facebookInput');
    const youtubeInput = document.getElementById('youtubeInput');

    if (!websiteInput && !facebookInput && !youtubeInput) return;

    const website = websiteInput ? websiteInput.value.trim() : '';
    const facebook = facebookInput ? facebookInput.value.trim() : '';
    const youtube = youtubeInput ? youtubeInput.value.trim() : '';

    try {
        const res = await fetch('/api/v1/artists/me/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                website_url: website,
                facebook_url: facebook,
                youtube_url: youtube
            })
        });
        const json = await res.json();
        if (json.success || res.ok) {
            if (window.showToast) window.showToast('Đã cập nhật liên kết thành công!', true);
            setTimeout(() => window.goToPage(window.location.pathname + window.location.search), 1000);
        } else {
            if (window.showToast) window.showToast(json.error?.message || 'Lỗi cập nhật liên kết', false);
            else alert(json.error?.message || 'Lỗi cập nhật liên kết');
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) window.showToast('Lỗi kết nối', false);
        else alert('Lỗi kết nối');
    }
}

// Bio Logic
window.saveBio = async function() {
    const bioInput = document.getElementById('bioInput');
    if (!bioInput) return;
    
    const bioText = bioInput.value;
    try {
        const res = await fetch('/api/v1/accounts/me/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ bio: bioText })
        });
        const json = await res.json();
        
        if (res.ok && json.success) {
            if (window.showToast) window.showToast('Đã cập nhật tiểu sử thành công!', 'success');
            setTimeout(() => window.goToPage(window.location.pathname + window.location.search), 1000);
        } else {
            const errorMsg = json.error?.message || 'Lỗi khi cập nhật tiểu sử';
            if (window.showToast) window.showToast(errorMsg, 'error');
            else alert(errorMsg);
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) window.showToast('Lỗi kết nối máy chủ', 'error');
        else alert('Lỗi kết nối máy chủ');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const bioInput = document.getElementById('bioInput');
    const bioCharCount = document.getElementById('bioCharCount');
    
    if (bioInput && bioCharCount) {
        const updateCount = () => {
            bioCharCount.textContent = bioInput.value.length;
        };
        bioInput.addEventListener('input', updateCount);
        updateCount(); // Initial count
    }
});

// Xử lý báo cáo người dùng
async function submitUserReport(event) {
    event.preventDefault();
    const btn = event.target;
    const reasonEl = document.getElementById('reportUserReason');
    const descriptionEl = document.getElementById('reportUserDescription');
    
    if (!reasonEl.value) {
        if (window.showToast) window.showToast('Vui lòng chọn lý do báo cáo.', 'warning');
        return;
    }

    if (!window.TARGET_USER_ID) {
        if (window.showToast) window.showToast('Không tìm thấy thông tin người dùng.', 'error');
        return;
    }

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/v1/music/reports/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                target_type: 'user',
                target_id: window.TARGET_USER_ID,
                reason: reasonEl.value,
                description: descriptionEl ? descriptionEl.value : ''
            })
        });
        const data = await res.json();
        
        if (res.ok && data.success) {
            if (window.showToast) window.showToast("Cảm ơn bạn. Báo cáo của bạn đã được ghi nhận.", 'success');
            const modalEl = document.getElementById('reportUserModal');
            const modalInstance = bootstrap.Modal.getInstance(modalEl);
            if (modalInstance) {
                modalInstance.hide();
            } else {
                const closeBtn = modalEl.querySelector('.btn-close');
                if (closeBtn) closeBtn.click();
            }
            reasonEl.value = ''; // Reset form
            const reasonTextEl = document.getElementById('reportUserReasonText');
            if (reasonTextEl) reasonTextEl.innerText = 'Chọn lý do...';
            if (descriptionEl) descriptionEl.value = '';
        } else {
            if (window.showToast) window.showToast("Lỗi khi gửi báo cáo: " + (data.error?.message || "Vui lòng thử lại sau."), 'error');
        }
    } catch (err) {
        console.error('Lỗi báo cáo người dùng:', err);
        if (window.showToast) window.showToast("Đã xảy ra lỗi khi gửi báo cáo.", 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}
