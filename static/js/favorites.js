
window.toggleSelectAll = function(checkbox) {
    const checkboxes = document.querySelectorAll('.song-checkbox');
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
    updateBulkDeleteBtn();
};

window.updateBulkDeleteBtn = function() {
    const checkboxes = document.querySelectorAll('.song-checkbox:checked');
    const btn = document.getElementById('bulkDeleteBtn');
    const countSpan = document.getElementById('selectedCount');
    if (btn && countSpan) {
        if (checkboxes.length > 0) {
            btn.classList.remove('d-none');
            countSpan.innerText = checkboxes.length;
        } else {
            btn.classList.add('d-none');
        }
    }
    
    // Cập nhật trạng thái select all
    const selectAll = document.getElementById('selectAllCheckbox');
    if (selectAll) {
        const total = document.querySelectorAll('.song-checkbox').length;
        selectAll.checked = total > 0 && checkboxes.length === total;
    }
};

window.bulkDeleteLiked = async function() {
    const checkboxes = document.querySelectorAll('.song-checkbox:checked');
    if (checkboxes.length === 0) return;
    
    if (!confirm(`Bạn có chắc chắn muốn bỏ yêu thích ${checkboxes.length} bài hát đã chọn?`)) {
        return;
    }
    
    const btn = document.getElementById('bulkDeleteBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Đang xoá...';
    btn.disabled = true;
    
    let successCount = 0;
    const promises = Array.from(checkboxes).map(async (cb) => {
        const songId = cb.value;
        try {
            const res = await fetch(`/api/v1/music/songs/${songId}/like/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            });
            const data = await res.json();
            if (data.success && data.data.action === 'unliked') {
                successCount++;
                const row = document.getElementById(`liked-song-row-${songId}`);
                if (row) row.remove();
            }
        } catch (e) {
            console.error('Lỗi khi xoá bài', songId, e);
        }
    });
    
    await Promise.all(promises);
    
    // Cập nhật lại số lượng trên header
    const countText = document.getElementById('songCountText');
    if (countText) {
        const match = countText.innerText.match(/\d+/);
        if (match) {
            const current = parseInt(match[0]);
            countText.innerText = `${Math.max(0, current - successCount)} bài hát`;
        }
    }
    
    if (window.showToast) {
        showToast(`Đã xoá ${successCount} bài hát khỏi danh sách yêu thích`, true);
    }
    
    updateBulkDeleteBtn();
    btn.innerHTML = originalText;
    btn.disabled = false;
};

window.toggleLikeFav = async function(event, songId, removeOnUnlike = false) {
    if (event) event.preventDefault();
    try {
        const res = await fetch(`/api/v1/music/songs/${songId}/like/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });
        const data = await res.json();
        if (data.success) {
            if (removeOnUnlike || data.data.action === 'unliked') {
                if (event && event.target && event.target.tagName === 'I') {
                    event.target.className = 'bi bi-heart hover-text-white position-relative';
                }
                
                // Update count
                const countText = document.getElementById('songCountText');
                if (countText) {
                    const match = countText.innerText.match(/\d+/);
                    if (match) {
                        const current = parseInt(match[0]);
                        countText.innerText = `${Math.max(0, current - 1)} bài hát`;
                    }
                }
            } else if (!removeOnUnlike && data.data.action === 'liked') {
                if (event && event.target && event.target.tagName === 'I') {
                    event.target.className = 'bi bi-heart-fill text-accent position-relative';
                }
                
                // Update count
                const countText = document.getElementById('songCountText');
                if (countText) {
                    const match = countText.innerText.match(/\d+/);
                    if (match) {
                        const current = parseInt(match[0]);
                        countText.innerText = `${current + 1} bài hát`;
                    }
                }
            }
        } else {
            if (window.showToast) showToast(data.error?.message || 'Có lỗi xảy ra', false);
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) showToast('Lỗi kết nối', false);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById('likedSongsContainer');
    const songCountText = document.getElementById('songCountText');
    if (!container) return;
    
    const targetUserId = window.CURRENT_USER_ID;
    try {
        const res = await fetch(`/api/v1/music/users/${targetUserId}/likes/?limit=100`);
        const data = await res.json();
        
        if (data.success) {
            const songs = data.data;
            songCountText.innerText = `${songs.length} bài hát`;
            
            if (songs.length > 0) {
                container.innerHTML = '';
                songs.forEach((song, index) => {
                    const durationStr = song.duration ? `${Math.floor(song.duration / 60)}:${(song.duration % 60).toString().padStart(2, '0')}` : '';
                    const albumName = song.genre ? song.genre.name : '';
                    const imageUrl = song.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=40&q=80';
                    
                    const dateAddedStr = song.liked_at ? timeAgo(song.liked_at) : '';
                    
                    const html = `
                        <div id="liked-song-row-${song.id}" class="playlist-grid playlist-grid-row py-2 px-3 rounded position-relative">
                            <div class="text-secondary text-center">
                                ${index + 1}
                            </div>
                            <div class="d-flex align-items-center gap-3 text-truncate">
                                <img src="${imageUrl}" class="rounded flex-shrink-0" alt="cover" style="width: 40px; height: 40px; object-fit: cover;">
                                <div class="text-truncate">
                                    <div class="fw-semibold text-truncate text-white">${song.title}</div>
                                    <div class="small text-secondary text-truncate">${song.artist.display_name}</div>
                                </div>
                            </div>
                            <div class="text-secondary hide-md text-truncate">${albumName}</div>
                            <div class="text-secondary hide-lg text-truncate">${dateAddedStr}</div>
                            <div class="text-secondary">${durationStr}</div>
                            <div class="text-secondary text-center">
                                <i class="bi ${song.is_liked !== false ? 'bi-heart-fill text-accent' : 'bi-heart hover-text-white'} position-relative" style="z-index: 2; cursor: pointer; transition: color 0.2s;" onclick="toggleLikeFav(event, '${song.id}')"></i>
                            </div>
                            <div class="text-secondary text-center d-flex align-items-center justify-content-center">
                                <input class="form-check-input song-checkbox m-0" type="checkbox" value="${song.id}" onchange="updateBulkDeleteBtn()" style="cursor: pointer; z-index: 2; position: relative; width: 18px; height: 18px;">
                            </div>
                            <a href="/song/?id=${song.id}" class="stretched-link"></a>
                        </div>
                    `;
                    container.innerHTML += html;
                });
            } else {
                container.innerHTML = '<div class="text-secondary py-4 text-center">Chưa có bài hát yêu thích nào</div>';
            }
        }
    } catch (e) {
        console.error("Lỗi khi tải bài hát yêu thích", e);
        container.innerHTML = '<div class="text-danger py-4 text-center">Đã xảy ra lỗi khi tải danh sách.</div>';
    }
});
