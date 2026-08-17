
// ═══════════════════════════════════════════════════════
// GLOBAL ERROR GUARD - Ngăn lỗi JS lan rộng trên toàn site
// ═══════════════════════════════════════════════════════
window.addEventListener('error', function(e) {
    if (e.message && (
        e.message.includes('null') ||
        e.message.includes('Cannot read') ||
        e.message.includes('is not defined')
    )) {
        console.warn('[PlayMood Guard] JS error caught (không crash):', e.message, '@', e.filename + ':' + e.lineno);
        e.preventDefault();
        return true;
    }
});

// Global navigation wrapper to use AJAX router if available
window.goToPage = function(url) {
    if (window.pmNavigate) {
        window.pmNavigate(url, true);
    } else {
        window.location.href = url;
    }
};
// main.js
// Common JS code for PlayMood

document.addEventListener('DOMContentLoaded', () => {
    // 1. Fetch unread notifications count globally
    fetch('/api/v1/notifications/unread-count/', {
        headers: { 'Accept': 'application/json' }
    })
    .then(res => {
        if (res.ok) return res.json();
        throw new Error('Not authenticated');
    })
    .then(data => {
        const count = data.data?.unread_count || 0;
        document.querySelectorAll('.bell-badge').forEach(b => {
            b.textContent = count > 99 ? '99+' : count;
            b.style.display = count > 0 ? 'inline-block' : 'none';
            
            // Revert any previously set inline styles just in case
            b.style.top = '';
            b.style.right = '';
            b.style.left = '';
            b.style.transform = '';
            
            // Change bell icon to solid white if there are notifications
            // The icon is now wrapped in a div, so we need to find it correctly
            const icon = b.parentElement.querySelector('i');
            if (icon) {
                if (count > 0) {
                    icon.classList.remove('bi-bell');
                    icon.classList.add('bi-bell-fill', 'text-white');
                } else {
                    icon.classList.remove('bi-bell-fill', 'text-white');
                    icon.classList.add('bi-bell');
                }
            }
        });
    })
    .catch(() => {
        // Do nothing if not authenticated
    });
});



// Global logout handler
async function handleLogout(event) {
    if (event) {
        event.preventDefault();
        const btn = event.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...';
        btn.disabled = true;
    }
    
    try {
        const response = await fetch('/api/v1/auth/logout/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            window.location.href = '/auth/login/';
        } else {
            console.error('Logout failed');
            if (window.showToast) {
                window.showToast('Đăng xuất thất bại, vui lòng thử lại.', false);
            } else {
                alert('Đăng xuất thất bại, vui lòng thử lại.');
            }
            if (event) {
                const btn = event.currentTarget;
                btn.innerHTML = 'Đăng xuất';
                btn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Error during logout:', error);
        if (window.showToast) {
            window.showToast('Có lỗi xảy ra, vui lòng thử lại.', false);
        } else {
            alert('Có lỗi xảy ra, vui lòng thử lại.');
        }
        if (event) {
            const btn = event.currentTarget;
            btn.innerHTML = 'Đăng xuất';
            btn.disabled = false;
        }
    }
}

// Helper to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {


            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Global Toggle Password Visibility
window.togglePasswordVisibility = function(inputId, icon) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('bi-eye-slash');
        icon.classList.add('bi-eye');
    } else {
        input.type = 'password';
        icon.classList.remove('bi-eye');
        icon.classList.add('bi-eye-slash');
    }
};

// Global Toast Notification
window.showToast = function(msg, isSuccess = true) {
    let toastContainer = document.getElementById('global-toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'global-toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    const toastElem = document.createElement('div');
    toastElem.className = `toast align-items-center border-0 text-white bg-${isSuccess ? 'success' : 'danger'}`;
    toastElem.setAttribute('role', 'alert');
    toastElem.setAttribute('aria-live', 'assertive');
    toastElem.setAttribute('aria-atomic', 'true');
    
    toastElem.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fw-bold">
                ${msg}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastElem);
    const toast = new bootstrap.Toast(toastElem, { delay: 3000 });
    
    toastElem.addEventListener('hidden.bs.toast', () => {
        toastElem.remove();
    });
    
    toast.show();
};

// Global Time Ago Formatter
window.timeAgo = function(isoString) {
    if (!isoString) return '';
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
};

// Global Format Time (seconds -> mm:ss)
window.formatTime = function(s) {
    if (isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
};

// Global toggle follow user
window.toggleFollowUser = async function(userId, btnElement) {
    // Fallback to checking undefined just in case
    if (window.USER_IS_AUTHENTICATED === false || window.CURRENT_USER_AUTHENTICATED === false) {
        window.location.href = window.LOGIN_URL || '/auth/login/';
        return;
    }
    
    const originalText = btnElement.innerText;
    btnElement.disabled = true;
    btnElement.innerText = '...';
    
    function getCsrf() {
        if (typeof getCookie === 'function') return getCookie('csrftoken');
        const match = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
        return match ? match[2] : '';
    }
    
    try {
        const res = await fetch(`/api/v1/social/users/${userId}/follow/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrf(),
                'Content-Type': 'application/json'
            }
        });
        
        const data = await res.json();
        if (data.success) {
            if (data.data.status === 'following') {
                btnElement.innerText = 'Đang theo dõi';
                btnElement.classList.remove('btn-outline-light', 'text-white', 'btn-light', 'text-dark');
                btnElement.style.background = '#8CE1B2';
                btnElement.style.color = '#121929';
                btnElement.style.border = 'none';
            } else if (data.data.status === 'requested') {
                btnElement.innerText = 'Đã yêu cầu';
                btnElement.classList.remove('btn-outline-light', 'text-white', 'btn-light', 'text-dark');
                btnElement.style.background = '#8CE1B2';
                btnElement.style.color = '#121929';
                btnElement.style.border = 'none';
            } else {
                btnElement.innerText = 'Theo dõi';
                btnElement.classList.remove('btn-light', 'text-dark');
                btnElement.classList.add('btn-outline-light', 'text-white');
                btnElement.style.background = '';
                btnElement.style.color = '';
                btnElement.style.border = '';
            }
        } else {
            if (window.showToast) {
                window.showToast(data.error?.message || 'Lỗi xử lý yêu cầu', false);
            } else {
                alert(data.error?.message || 'Lỗi xử lý yêu cầu');
            }
            btnElement.innerText = originalText;
        }
    } catch (err) {
        console.error(err);
        if (window.showToast) {
            window.showToast('Lỗi kết nối', false);
        } else {
            alert('Lỗi kết nối');
        }
        btnElement.innerText = originalText;
    } finally {
        btnElement.disabled = false;
    }
};

// Global open add to playlist (fallback to redirecting to song details since there's no global modal)
window.openAddToPlaylistModal = function(songId) {
    window.goToPage(`/song/?id=${songId}`);
};

// Global play album logic
window.playAlbum = async function(albumId, albumTitle = 'Album') {
    try {
        let contextName = albumTitle;
        if (contextName === 'Album') {
            try {
                const alRes = await fetch(`/api/v1/music/albums/${albumId}/`);
                const alData = await alRes.json();
                if (alData.success && alData.data) {
                    contextName = alData.data.title || 'Album';
                }
            } catch(e) {}
        }

        const res  = await fetch(`/api/v1/music/albums/${albumId}/songs/`);
        const data = await res.json();
        if (!data.success) { 
            if (window.showToast) window.showToast('Không thể tải album', 'error');
            return; 
        }

        const songs = data.data.items || [];
        if (songs.length === 0) {
            if (window.showToast) window.showToast('Album chưa có bài hát nào', 'error');
            return;
        }

        /* Phát bài đầu tiên qua window.playSong */
        const firstSongId = songs[0].song.id;
        if (typeof window.playSong === 'function') {
            // Xoá sạch danh sách chờ hiện tại trước khi phát album
            if (typeof window._songQueue !== 'undefined') {
                window._songQueue = [];
                localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
            }

            window.playSong(firstSongId);
            
            // Append rest to queue
            let rest = songs.slice(1);
            
            // Xáo trộn nếu đang bật chế độ ngẫu nhiên
            const isShuffle = localStorage.getItem("pm_shuffle") === "true";
            if (isShuffle && rest.length > 0) {
                for (let i = rest.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [rest[i], rest[j]] = [rest[j], rest[i]];
                }
            }

            rest.forEach(item => {
                const s = item.song;
                const artistName = s.artist ? (s.artist.display_name || s.artist.username || 'Unknown') : 'Unknown';
                if (window.addToQueue) {
                    window.addToQueue(s.id, s.title, artistName, s.cover_image, `Nội dung tiếp theo từ ${contextName}`, true);
                }
            });
        } else {
            if (window.showToast) window.showToast('Player chưa sẵn sàng', 'error');
        }
    } catch (err) {
        console.error('playAlbum:', err);
        if (window.showToast) window.showToast('Lỗi kết nối', 'error');
    }
};
