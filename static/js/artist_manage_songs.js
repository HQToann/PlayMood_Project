        document.addEventListener('DOMContentLoaded', function() {
            const userId = window.CURRENT_USER_ID;
            const songsContainer = document.getElementById('songsListContainer');
            
            // Setup modals if they exist
            const editSongModalElem = document.getElementById('editSongModal');
            const editSongModal = editSongModalElem ? new bootstrap.Modal(editSongModalElem) : null;
            
            const appealModalElem = document.getElementById('appealSongModal');
            const appealModal = appealModalElem ? new bootstrap.Modal(appealModalElem) : null;

            

            function showToast(msg, isSuccess = true) {
                const toastElem = document.getElementById('systemToast');
                if(!toastElem) return;
                const msgElem = document.getElementById('toastMessage');
                msgElem.textContent = msg;
                toastElem.className = `toast align-items-center border-0 text-white bg-${isSuccess ? 'success' : 'danger'}`;
                const toast = new bootstrap.Toast(toastElem, { delay: 3000 });
                toast.show();
            }

            let currentActionSongId = null;
            let originalEditValues = {};

            let currentManagePage = 1;
            let isFetchingManage = false;
            let hasMoreManage = true;

            async function loadSongs(reset = false) {
                if (isFetchingManage || (!hasMoreManage && !reset)) return;

                if (reset) {
                    currentManagePage = 1;
                    hasMoreManage = true;
                    songsContainer.innerHTML = `
                        <div id="manageLoadingIndicator" class="d-flex flex-column gap-1 w-100">
                            <div class="skeleton" style="border-radius:10px;height:56px;width:100%;"></div>
                            <div class="skeleton" style="border-radius:10px;height:56px;width:100%;"></div>
                            <div class="skeleton" style="border-radius:10px;height:56px;width:100%;"></div>
                        </div>`;
                } else {
                    const loadingDiv = document.createElement('div');
                    loadingDiv.id = 'manageLoadingIndicator';
                    loadingDiv.className = 'w-100 mt-2';
                    loadingDiv.innerHTML = `<div class="skeleton" style="border-radius:10px;height:56px;width:100%;"></div>`;
                    songsContainer.appendChild(loadingDiv);
                }

                isFetchingManage = true;

                try {
                    const response = await fetch(`/api/v1/music/songs/?artist_id=${userId}&page=${currentManagePage}&limit=10`);
                    const data = await response.json();
                    
                    const loadingIndicator = document.getElementById('manageLoadingIndicator');
                    if (loadingIndicator) loadingIndicator.remove();
                    
                    if (data.success) {
                        let songs = [];
                        if (Array.isArray(data.data)) {
                            songs = data.data;
                            hasMoreManage = false;
                        } else if (data.data.items) {
                            songs = data.data.items;
                            const pagination = data.data.pagination;
                            if (pagination) {
                                hasMoreManage = currentManagePage < pagination.total_pages;
                            } else {
                                hasMoreManage = false;
                            }
                        }

                        if (reset && songs.length === 0) {
                            songsContainer.innerHTML = '<div class="text-center text-secondary py-5">Bạn chưa có bài hát nào. Hãy tải bài hát đầu tiên lên!</div>';
                            isFetchingManage = false;
                            return;
                        }

                        if (reset) {
                            songsContainer.innerHTML = '';
                        }

                        songs.forEach(song => {
                            const isDraft = song.status === 'draft';
                            const isHidden = song.status === 'hidden';
                            const hiddenByAdmin = song.hidden_by_admin;
                            
                            const dateStr = song.released_at 
                                ? new Date(song.released_at).toLocaleDateString('vi-VN') 
                                : new Date(song.created_at).toLocaleDateString('vi-VN');
                            
                            const coverUrl = song.cover_image ? song.cover_image : null;

                            let statusHtml = '';
                            let actionHtml = '';

                            if (hiddenByAdmin) {
                                statusHtml = '<span class="text-secondary">Bị khoá</span>';
                                if (song.is_appealed) {
                                    actionHtml = `<li><a class="dropdown-item py-2 disabled" href="#" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-hourglass-split me-3 text-muted-custom"></i> Đang chờ xử lý khiếu nại</a></li>`;
                                } else {
                                    actionHtml = `<li><a class="dropdown-item py-2 action-appeal-song" href="#" data-bs-toggle="modal" data-bs-target="#appealSongModal" data-song-id="${song.id}" data-hidden-reason="${song.hidden_reason || 'Vi phạm chính sách'}" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-exclamation-triangle me-3 text-muted-custom"></i> Lý do và kiến nghị</a></li>`;
                                }
                            } else if (isDraft) {
                                statusHtml = '<span class="text-secondary">Bản nháp</span>';
                                actionHtml = `<li><a class="dropdown-item py-2 action-publish-song" href="#" data-song-id="${song.id}" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-send-check me-3 text-muted-custom"></i> Phát hành ngay</a></li>`;
                            } else if (isHidden) {
                                statusHtml = '<span class="text-secondary">Đã ẩn</span>';
                                actionHtml = `<li><a class="dropdown-item py-2 action-publish-song" href="#" data-song-id="${song.id}" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-eye me-3 text-muted-custom"></i> Hiện lại bài hát</a></li>`;
                            } else {
                                statusHtml = '<span class="text-secondary">Phát hành</span>';
                                actionHtml = `<li><a class="dropdown-item py-2 action-hide-song" href="#" data-song-id="${song.id}" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-eye-slash me-3 text-muted-custom"></i> Ẩn bài hát</a></li>`;
                            }

                            const html = `
                                <div class="song-manage-item row align-items-center py-3 px-3 rounded-3 mb-2" style="background-color: rgba(255,255,255,0.02); transition: background-color 0.2s; ${hiddenByAdmin ? 'border: 1px solid rgba(220, 53, 69, 0.4);' : 'border: 1px solid transparent;'}">
                                    <div class="col-12 col-md-5 d-flex align-items-center gap-3 mb-3 mb-md-0">
                                        ${coverUrl 
                                            ? `<img src="${coverUrl}" alt="cover" class="rounded play-trigger" style="width: 50px; height: 50px; object-fit: cover; cursor:pointer;" onclick="if(window.playSong)window.playSong('${song.id}', event)">`
                                            : `<div class="d-flex align-items-center justify-content-center rounded bg-secondary bg-opacity-25 play-trigger" style="width: 50px; height: 50px; cursor:pointer;" onclick="if(window.playSong)window.playSong('${song.id}', event)"><i class="bi bi-music-note text-secondary fs-4"></i></div>`
                                        }
                                        <div>
                                            <div class="text-white fw-semibold play-trigger" style="cursor:pointer;" onclick="if(window.playSong)window.playSong('${song.id}', event)">${song.title}</div>
                                            <div class="text-secondary small">${song.genre ? song.genre.name : 'Chưa phân loại'} • ${dateStr}</div>
                                        </div>
                                    </div>
                                    <div class="col-6 col-md-2 text-md-center">
                                        ${statusHtml}
                                    </div>
                                    <div class="col-6 col-md-3 text-md-center d-flex justify-content-end justify-content-md-center gap-4">
                                        <div class="text-secondary ${isDraft ? 'opacity-50' : ''}" title="Lượt nghe"><i class="bi bi-headphones me-1"></i> ${song.play_count || 0}</div>
                                        <div class="text-secondary ${isDraft ? 'opacity-50' : ''}" title="Lượt thích"><i class="bi bi-heart me-1"></i> ${song.like_count || 0}</div>
                                    </div>
                                    <div class="col-12 col-md-2 text-end mt-3 mt-md-0">
                                        <div class="dropdown">
                                            <button class="btn btn-sm btn-link text-light p-0 shadow-none" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                                <i class="bi bi-three-dots-vertical fs-5"></i>
                                            </button>
                                            <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow-lg" style="background: rgba(30, 30, 30, 0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); padding: 6px;">
                                                <li><a class="dropdown-item py-2 action-edit-song" href="#" data-bs-toggle="modal" data-bs-target="#editSongModal" data-song-id="${song.id}" style="border-radius: 8px; margin-bottom: 2px;"><i class="bi bi-pencil me-3 text-muted-custom"></i> Chỉnh sửa</a></li>
                                                ${actionHtml}
                                                <li><hr class="dropdown-divider" style="border-color: rgba(255,255,255,0.08); margin: 6px 0;"></li>
                                                <li><a class="dropdown-item py-2 text-danger action-delete-song" href="#" data-bs-toggle="modal" data-bs-target="#deleteSongConfirmModal" data-song-id="${song.id}" style="border-radius: 8px;" onmouseover="this.style.backgroundColor='rgba(239,68,68,0.15)'" onmouseout="this.style.backgroundColor='transparent'"><i class="bi bi-trash me-3"></i> Xóa bài hát</a></li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            `;
                            songsContainer.insertAdjacentHTML('beforeend', html);
                        });
                        currentManagePage++;
                    } else {
                        if (reset) songsContainer.innerHTML = '<div class="text-danger py-3 text-center">Lỗi tải danh sách bài hát.</div>';
                    }
                } catch (err) {
                    console.error(err);
                    const loadingIndicator = document.getElementById('manageLoadingIndicator');
                    if (loadingIndicator) loadingIndicator.remove();
                    if (reset) songsContainer.innerHTML = '<div class="text-danger py-3 text-center">Lỗi kết nối máy chủ.</div>';
                } finally {
                    isFetchingManage = false;
                }
            }

            async function loadGenres() {
                try {
                    const res = await fetch('/api/v1/music/genres/');
                    const data = await res.json();
                    if (data.success && data.data && data.data.items) {
                        const genreSelect = document.getElementById('editSongGenre');
                        genreSelect.innerHTML = '<option value="">Chọn thể loại...</option>';
                        data.data.items.forEach(genre => {
                            const opt = document.createElement('option');
                            opt.value = genre.id;
                            opt.textContent = genre.name;
                            genreSelect.appendChild(opt);
                        });
                    }
                } catch(err) {
                    console.error('Failed to load genres', err);
                }
            }

            loadGenres();

            loadSongs(true);
            
            const handleManageScroll = function(e) {
                const target = e.target;
                if (target && target.classList && target.classList.contains('content-scroll')) {
                    if (target.scrollHeight - target.scrollTop <= target.clientHeight + 150) {
                        loadSongs(false);
                    }
                }
            };
            
            document.addEventListener('scroll', handleManageScroll, true);

            // Event Delegation for action clicks
            document.body.addEventListener('click', async function(e) {
                const target = e.target.closest('a.dropdown-item');
                if (!target) return;

                if (target.classList.contains('action-delete-song')) {
                    currentActionSongId = target.getAttribute('data-song-id');
                }

                if (target.classList.contains('action-publish-song') || target.classList.contains('action-hide-song')) {
                    e.preventDefault();
                    const songId = target.getAttribute('data-song-id');
                    const isPublish = target.classList.contains('action-publish-song');
                    const url = `/api/v1/music/songs/${songId}/${isPublish ? 'publish' : 'hide'}/`;

                    try {
                        const csrfToken = getCookie('csrftoken');
                        const response = await fetch(url, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': csrfToken,
                                'Content-Type': 'application/json'
                            }
                        });
                        const data = await response.json();
                        if (data.success) {
                            loadSongs(true);
                            showToast(isPublish ? 'Phát hành bài hát thành công!' : 'Đã ẩn bài hát thành công!');
                        } else {
                            showToast('Lỗi: ' + (data.error?.message || 'Có lỗi xảy ra'), false);
                        }
                    } catch (err) {
                        console.error(err);
                        showToast('Lỗi kết nối máy chủ', false);
                    }
                }

                if (target.classList.contains('action-appeal-song')) {
                    e.preventDefault();
                    currentActionSongId = target.getAttribute('data-song-id');
                    const reason = target.getAttribute('data-hidden-reason');
                    document.getElementById('appealSongId').value = currentActionSongId;
                    document.getElementById('appealHiddenReason').textContent = reason;
                    document.getElementById('appealMessage').value = '';
                }

                // Edit song
                if (target.classList.contains('action-edit-song')) {
                    e.preventDefault();
                    currentActionSongId = target.getAttribute('data-song-id');
                    
                    try {
                        const res = await fetch(`/api/v1/music/songs/${currentActionSongId}/`);
                        const data = await res.json();
                        if (data.success) {
                            const s = data.data;
                            document.getElementById('editSongTitle').value = s.title;
                            document.getElementById('editSongGenre').value = s.genre ? s.genre.id : '';
                            document.getElementById('editSongLyrics').value = s.lyrics || '';
                            document.getElementById('editSongAllowDownload').checked = s.allow_download;
                            document.getElementById('editSongCoverPreview').src = s.cover_image || 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                            document.getElementById('editSongCover').value = '';
                            
                            originalEditValues = {
                                title: s.title || '',
                                genre_id: s.genre ? String(s.genre.id) : '',
                                lyrics: s.lyrics || '',
                                allow_download: s.allow_download
                            };
                        } else {
                            showToast('Lỗi tải thông tin bài hát', false);
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }
            });

            // Preview cover image on select
            const editSongCoverInput = document.getElementById('editSongCover');
            if (editSongCoverInput) {
                editSongCoverInput.addEventListener('change', function(e) {
                    const file = e.target.files[0];
                    if (file) {
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            document.getElementById('editSongCoverPreview').src = e.target.result;
                        }
                        reader.readAsDataURL(file);
                    }
                });
            }

            // Handle Delete confirmation
            const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
            if (confirmDeleteBtn) {
                confirmDeleteBtn.addEventListener('click', async function () {
                    if (!currentActionSongId) return;
                    try {
                        const originalHtml = confirmDeleteBtn.innerHTML;
                        confirmDeleteBtn.disabled = true;
                        confirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Đang xóa...';
                        
                        const response = await fetch(`/api/v1/music/songs/${currentActionSongId}/`, {
                            method: 'DELETE',
                            headers: { 'X-CSRFToken': getCookie('csrftoken') }
                        });
                        
                        if (response.ok) {
                            const m = bootstrap.Modal.getInstance(document.getElementById('deleteSongConfirmModal'));
                            if (m) m.hide();
                            loadSongs(true);
                            showToast('Xóa bài hát thành công!');
                        } else {
                            showToast('Xóa thất bại', false);
                        }
                        
                        confirmDeleteBtn.disabled = false;
                        confirmDeleteBtn.innerHTML = originalHtml;
                    } catch (err) {
                        console.error(err);
                        confirmDeleteBtn.disabled = false;
                    }
                });
            }

            // Handle Appeal Submit
            const confirmAppealBtn = document.getElementById('confirmAppealBtn');
            if (confirmAppealBtn) {
                confirmAppealBtn.addEventListener('click', async function () {
                    const msg = document.getElementById('appealMessage').value.trim();
                    if (!msg) {
                        showToast('Vui lòng nhập nội dung khiếu nại', false);
                        return;
                    }
                    if (!currentActionSongId) return;

                    try {
                        const originalHtml = confirmAppealBtn.innerHTML;
                        confirmAppealBtn.disabled = true;
                        confirmAppealBtn.innerHTML = 'Đang gửi...';

                        const res = await fetch(`/api/v1/music/songs/${currentActionSongId}/appeal/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({ message: msg })
                        });
                        const data = await res.json();
                        if (data.success) {
                            if (appealModal) appealModal.hide();
                            loadSongs(true);
                            showToast('Gửi khiếu nại thành công! Vui lòng chờ admin xử lý.');
                        } else {
                            showToast('Lỗi: ' + (data.error?.message || 'Có lỗi xảy ra'), false);
                        }
                        confirmAppealBtn.disabled = false;
                        confirmAppealBtn.innerHTML = originalHtml;
                    } catch (err) {
                        console.error(err);
                        confirmAppealBtn.disabled = false;
                    }
                });
            }

            // Handle Edit Submit
            const editForm = document.getElementById('editSongForm');
            if (editForm) {
                editForm.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    if (!currentActionSongId) return;
                    
                    const btn = document.getElementById('confirmEditBtn');
                    const originalHtml = btn.innerHTML;
                    
                    try {
                        const title = document.getElementById('editSongTitle').value;
                        const genre_id = document.getElementById('editSongGenre').value;
                        const lyrics = document.getElementById('editSongLyrics').value;
                        const allow_download = document.getElementById('editSongAllowDownload').checked;
                        const coverFile = document.getElementById('editSongCover').files[0];
                        
                        if (!coverFile && 
                            title === originalEditValues.title && 
                            genre_id === originalEditValues.genre_id && 
                            lyrics === originalEditValues.lyrics && 
                            allow_download === originalEditValues.allow_download) {
                            showToast('Không có thay đổi nào để lưu', false);
                            if (editSongModal) editSongModal.hide();
                            return;
                        }

                        btn.disabled = true;
                        btn.innerHTML = 'Đang lưu...';
                        
                        const formData = new FormData();
                        formData.append('title', title);
                        formData.append('genre_id', genre_id);
                        formData.append('lyrics', lyrics);
                        formData.append('allow_download', allow_download);
                        
                        if (coverFile) formData.append('cover_image', coverFile);
                        
                        const res = await fetch(`/api/v1/music/songs/${currentActionSongId}/`, {
                            method: 'POST', // Use POST for multipart form data, SongDetailView.post calls self.patch
                            headers: {
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: formData
                        });
                        
                        const data = await res.json();
                        if (data.success) {
                            if (editSongModal) editSongModal.hide();
                            loadSongs(true);
                            showToast('Đã lưu thay đổi thành công!');
                        } else {
                            showToast('Lỗi: ' + (data.error?.message || 'Lưu thất bại'), false);
                        }
                    } catch (err) {
                        console.error(err);
                        showToast('Lỗi kết nối', false);
                    } finally {
                        btn.disabled = false;
                        btn.innerHTML = originalHtml;
                    }
                });
            }
            // Đã xoá logic trình phát Audio nội bộ gây lỗi nhạc đè lên nhau.

        });
