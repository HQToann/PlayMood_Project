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
            b.style.display = count > 0 ? 'flex' : 'none';
        });
    })
    .catch(() => {
        // Do nothing if not authenticated
    });
});
