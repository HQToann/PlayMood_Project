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
