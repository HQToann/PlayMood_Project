
window.toggleSelectAll = function(checkbox) {
    document.querySelectorAll('.song-checkbox').forEach(cb => cb.checked = checkbox.checked);
    updateBulkDeleteBtn();
};

window.updateBulkDeleteBtn = function() {
    const checkboxes = document.querySelectorAll('.song-checkbox:checked');
    const btn = document.getElementById('bulkDeleteBtn');
    const countSpan = document.getElementById('selectedCount');
    if (btn && countSpan) {
        if (checkboxes.length > 0) { btn.classList.remove('d-none'); countSpan.innerText = checkboxes.length; }
        else { btn.classList.add('d-none'); }
    }
    const selectAll = document.getElementById('selectAllCheckbox');
    if (selectAll) {
        const total = document.querySelectorAll('.song-checkbox').length;
        selectAll.checked = total > 0 && checkboxes.length === total;
    }
};

window.bulkDeleteRecent = async function() {
    const checkboxes = document.querySelectorAll('.song-checkbox:checked');
    if (checkboxes.length === 0) return;
    if (!confirm(`Bạn có chắc muốn xoá ${checkboxes.length} bài hát khỏi lịch sử nghe?`)) return;
    const btn = document.getElementById('bulkDeleteBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Đang xoá...';
    btn.disabled = true;
    let successCount = 0;
    const promises = Array.from(checkboxes).map(async (cb) => {
        const songId = cb.value;
        try {
            const res = await fetch('/api/v1/music/me/history/', {
                method: 'DELETE',
                headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' },
                body: JSON.stringify({ song_id: songId })
            });
            if (res.ok || res.status === 204) {
                successCount++;
                const row = document.getElementById('recent-song-row-' + songId);
                if (row) row.remove();
            }
        } catch (e) { console.error('Lỗi khi xoá bài', songId, e); }
    });
    await Promise.all(promises);
    if (window.showToast) showToast(`Đã xoá ${successCount} bài hát khỏi lịch sử nghe`, true);
    updateBulkDeleteBtn();
    btn.innerHTML = originalText;
    btn.disabled = false;
};

window.toggleLikeRecent = async function(event, songId) {
    if (event) event.preventDefault();
    try {
        const res = await fetch(`/api/v1/music/songs/${songId}/like/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            if (data.data.action === 'unliked' && event && event.target && event.target.tagName === 'I')
                event.target.className = 'bi bi-heart hover-text-white position-relative';
            else if (data.data.action === 'liked' && event && event.target && event.target.tagName === 'I')
                event.target.className = 'bi bi-heart-fill text-accent position-relative';
        } else { if (window.showToast) showToast(data.error?.message || 'Có lỗi xảy ra', false); }
    } catch (e) { if (window.showToast) showToast('Lỗi kết nối', false); }
};
document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('recentSongsContainer');
    if (!container) return;
    try {
        const res = await fetch('/api/v1/music/me/history/?limit=50');
        const data = await res.json();
        if (data.success) {
            const items = data.data.items || [];
            if (items.length > 0) {
                container.innerHTML = '';
                items.forEach((item, index) => {
                    const song = item.song;
                    const durationStr = song.duration ? `${Math.floor(song.duration / 60)}:${(song.duration % 60).toString().padStart(2, '0')}` : '';
                    const albumName = song.genre ? song.genre.name : '';
                    const imageUrl = song.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=40&q=80';
                    const dateListenedStr = item.listened_at ? timeAgo(item.listened_at) : '';
                    const artistName = song.artist ? song.artist.display_name : '';
                    container.innerHTML += `
                        <div id="recent-song-row-${song.id}" class="playlist-grid playlist-grid-row py-2 px-3 rounded position-relative">
                            <div class="text-secondary text-center">${index + 1}</div>
                            <div class="d-flex align-items-center gap-3 text-truncate">
                                <img src="${imageUrl}" class="rounded flex-shrink-0" alt="cover" style="width: 40px; height: 40px; object-fit: cover;">
                                <div class="text-truncate">
                                    <div class="fw-semibold text-truncate text-white">${song.title}</div>
                                    <div class="small text-secondary text-truncate">${artistName}</div>
                                </div>
                            </div>
                            <div class="text-secondary hide-md text-truncate">${albumName}</div>
                            <div class="text-secondary hide-lg text-truncate">${dateListenedStr}</div>
                            <div class="text-secondary">${durationStr}</div>
                            <div class="text-secondary text-center">
                                <i class="bi ${song.is_liked ? 'bi-heart-fill text-accent' : 'bi-heart hover-text-white'} position-relative"
                                   style="z-index: 2; cursor: pointer; transition: color 0.2s;"
                                   onclick="toggleLikeRecent(event, '${song.id}')"></i>
                            </div>
                            <div class="text-secondary text-center d-flex align-items-center justify-content-center">
                                <input class="form-check-input song-checkbox m-0" type="checkbox" value="${song.id}"
                                       onchange="updateBulkDeleteBtn()"
                                       style="cursor: pointer; z-index: 2; position: relative; width: 18px; height: 18px;">
                            </div>
                            <a href="/song/?id=${song.id}" class="stretched-link"></a>
                        </div>
                    `;
                });
            } else {
                container.innerHTML = '<div class="text-secondary py-4 text-center">Bạn chưa có lịch sử nghe nào.</div>';
            }
        }
    } catch (e) {
        console.error('Lỗi khi tải lịch sử nghe', e);
        container.innerHTML = '<div class="text-danger py-4 text-center">Đã xảy ra lỗi khi tải lịch sử.</div>';
    }
});
