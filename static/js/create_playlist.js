// Helper for getting CSRF Token
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

window.openPlaylistFormModal = function(playlist, event) {
    playlist = playlist || null;
    event = event || null;
    if (event) event.preventDefault();
    if (typeof window.CURRENT_USER_AUTHENTICATED !== 'undefined' && !window.CURRENT_USER_AUTHENTICATED) {
        window.location.href = window.LOGIN_URL || '/auth/login/';
        return;
    }
    
    var isEdit = !!playlist;
    
    var labelEl = document.getElementById('playlistFormModalLabel');
    var saveBtnEl = document.getElementById('btnSavePlaylist');
    var editIdEl = document.getElementById('editPlaylistId');
    var nameEl = document.getElementById('playlistName');
    var descEl = document.getElementById('playlistDesc');
    var coverEl = document.getElementById('playlistCover');
    var coverPreview = document.getElementById('playlistCoverPreview');
    var coverPlaceholder = document.getElementById('playlistCoverPlaceholder');

    if (labelEl) labelEl.textContent = isEdit ? 'Chỉnh sửa Playlist' : 'Tạo Playlist mới';
    if (saveBtnEl) saveBtnEl.textContent = isEdit ? 'Lưu' : 'Tạo mới';
    if (editIdEl) editIdEl.value = isEdit ? playlist.id : '';
    if (nameEl) nameEl.value = isEdit ? (playlist.title || '') : '';
    if (descEl) descEl.value = isEdit ? (playlist.description || '') : '';
    if (coverEl) coverEl.value = '';
    
    if (coverPreview && coverPlaceholder) {
        if (isEdit && playlist.cover_image) {
            coverPreview.src = playlist.cover_image;
            coverPreview.style.display = 'block';
            coverPlaceholder.style.display = 'none';
        } else {
            coverPreview.src = '';
            coverPreview.style.display = 'none';
            coverPlaceholder.style.display = 'block';
        }
    }

    // Dùng hidden trigger button (data-bs-toggle) — tin cậy 100%
    var triggerBtn = document.getElementById('triggerPlaylistModal');
    if (triggerBtn) {
        triggerBtn.click();
        return;
    }

    // Fallback: gọi Bootstrap API
    var modalEl = document.getElementById('playlistFormModal');
    if (modalEl) {
        var showModal = function() {
            if (typeof bootstrap !== 'undefined') {
                bootstrap.Modal.getOrCreateInstance(modalEl).show();
            }
        };
        if (typeof bootstrap !== 'undefined') {
            showModal();
        } else {
            // Chờ Bootstrap load xong
            window.addEventListener('load', showModal, { once: true });
        }
    }
};

// Khả năng tương thích ngược
window.openCreatePlaylistModal = function(event) {
    window.openPlaylistFormModal(null, event);
};

document.addEventListener('click', async function(e) {
    if (e.target && e.target.id === 'btnSavePlaylist') {
        e.preventDefault();
        const btnSubmit = e.target;
        if (btnSubmit.disabled) return;
        
        const editId = document.getElementById('editPlaylistId').value;
        const isEdit = !!editId;
        const title = document.getElementById('playlistName').value.trim();
        const desc = document.getElementById('playlistDesc').value.trim();
        const status = document.getElementById('playlistStatus').value;
        const coverInput = document.getElementById('playlistCover');
        
        if (!title) {
            alert('Vui lòng nhập tên Playlist');
            return;
        }

        // Disable button while processing
        const originalText = btnSubmit.innerHTML;
        btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
        btnSubmit.disabled = true;

        try {
            const csrfToken = typeof getCookie === 'function' ? getCookie('csrftoken') : '';
            
            let targetUrl = '/api/v1/playlists/';
            let targetMethod = 'POST';
            if (isEdit) {
                targetUrl = `/api/v1/playlists/${editId}/`;
                targetMethod = 'PATCH';
            }
            
            // 1. Create/Update Playlist via JSON
            const res = await fetch(targetUrl, {
                method: targetMethod,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    title: title,
                    description: desc,
                    is_public: (status === 'public')
                })
            });

            const resData = await res.json();
            if (!resData.success && !res.ok) {
                throw new Error(resData.error?.message || 'Có lỗi xảy ra khi lưu playlist');
            }

            const playlistId = isEdit ? editId : resData.data.id;

            // 2. Upload Cover Image if selected
            if (coverInput.files && coverInput.files.length > 0) {
                const formData = new FormData();
                formData.append('cover_image', coverInput.files[0]);
                
                const uploadRes = await fetch(`/api/v1/playlists/${playlistId}/cover/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });
                
                const uploadData = await uploadRes.json();
                if (!uploadData.success) {
                    console.error('Lỗi khi upload ảnh bìa:', uploadData.error);
                }
            }

            // Success!
            const modalEl = document.getElementById('playlistFormModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) {
                modal.hide();
            }
            
            // Reset form
            document.getElementById('playlistForm').reset();
            
            // Nếu đang có yêu cầu "Tạo xong rồi thêm luôn bài hát"
            if (!isEdit && window.pendingSongToAddToNewPlaylist) {
                try {
                    const addRes = await fetch(`/api/v1/playlists/${playlistId}/songs/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ song_id: window.pendingSongToAddToNewPlaylist })
                    });
                    const addData = await addRes.json();
                    if (addRes.ok && addData.success) {
                        if (typeof showToast === 'function') {
                            showToast('Đã tạo playlist và thêm bài hát thành công!', 'success');
                        } else {
                            alert('Đã tạo playlist và thêm bài hát thành công!');
                        }
                    } else {
                        console.error('Lỗi khi thêm bài hát vào playlist mới:', addData.error);
                    }
                } catch(err) {
                    console.error('Lỗi gọi API thêm bài hát:', err);
                }
                window.pendingSongToAddToNewPlaylist = null;
                
                // Đợi chút xíu cho toast hiện rồi tải lại trang
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // Bình thường lưu xong thì load lại
                window.location.reload(); 
            }

        } catch (error) {
            alert(error.message);
        } finally {
            btnSubmit.innerHTML = originalText;
            btnSubmit.disabled = false;
        }
    }
});
