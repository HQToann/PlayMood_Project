window.openCreatePlaylistModal = function(event) {
    if (event) event.preventDefault();
    if (typeof window.CURRENT_USER_AUTHENTICATED !== 'undefined' && !window.CURRENT_USER_AUTHENTICATED) {
        window.location.href = window.LOGIN_URL || '/auth/login/';
        return;
    }
    const modalEl = document.getElementById('createPlaylistModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    } else {
        console.warn('Bootstrap is not loaded yet or modal element not found');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const btnSubmit = document.getElementById('btnCreatePlaylistSubmit');
    if (btnSubmit && !btnSubmit.dataset.hasListener) {
        btnSubmit.dataset.hasListener = 'true';
        btnSubmit.addEventListener('click', async function() {
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
            btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang tạo...';
            btnSubmit.disabled = true;

            try {
                const csrfToken = typeof getCookie === 'function' ? getCookie('csrftoken') : '';
                
                // 1. Create Playlist via JSON
                const createRes = await fetch('/api/v1/playlists/', {
                    method: 'POST',
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

                const createData = await createRes.json();
                if (!createData.success) {
                    throw new Error(createData.error?.message || 'Có lỗi xảy ra khi tạo playlist');
                }

                const playlistId = createData.data.id;

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
                const modalEl = document.getElementById('createPlaylistModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                }
                
                // Reset form
                document.getElementById('createPlaylistForm').reset();
                
                // Nếu đang có yêu cầu "Tạo xong rồi thêm luôn bài hát"
                if (window.pendingSongToAddToNewPlaylist) {
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
                    // Bình thường tạo xong thì load lại (hoặc tuỳ trang)
                    window.location.reload(); 
                }

            } catch (error) {
                alert(error.message);
            } finally {
                btnSubmit.innerHTML = originalText;
                btnSubmit.disabled = false;
            }
        });
    }
});
