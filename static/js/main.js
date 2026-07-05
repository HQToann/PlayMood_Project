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
            alert('Đăng xuất thất bại, vui lòng thử lại.');
            if (event) {
                const btn = event.currentTarget;
                btn.innerHTML = 'Đăng xuất';
                btn.disabled = false;
            }
        }
    } catch (error) {
        console.error('Error during logout:', error);
        alert('Có lỗi xảy ra, vui lòng thử lại.');
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
