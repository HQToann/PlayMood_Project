document.addEventListener('DOMContentLoaded', function() {
    // Helper để lấy CSRF token
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

    // Lấy ID album từ URL (?id=...)
    const urlParams = new URLSearchParams(window.location.search);
    const albumId = urlParams.get('id');

    if (albumId) {
        // Tải thông tin album
        fetch(`/api/v1/music/albums/${albumId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data) {
                    const album = data.data;
                    window._currentAlbum = album;
                    
                    const coverUrl = album.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80';
                    const imgEl = document.getElementById('detail-album-cover');
                    imgEl.crossOrigin = "Anonymous";
                    
                    // Lấy màu nền khi ảnh đã tải xong
                    imgEl.addEventListener('load', function () {
                        try {
                            const colorThief = new ColorThief();
                            const color = colorThief.getColor(imgEl);
                            if (color) {
                                const albumHeader = document.querySelector('.album-header');
                                // Đổi nền gradient với màu của ảnh (có độ trong suốt 0.4 để màu tối hơn)
                                albumHeader.style.background = `linear-gradient(to bottom, rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.4), var(--bg-app))`;
                            }
                        } catch (e) {
                            console.warn('Không thể lấy màu nền từ ảnh do lỗi CORS hoặc thư viện.', e);
                        }
                    });
                    
                    imgEl.src = coverUrl;
                    imgEl.alt = album.title || 'Album';
                    
                    document.getElementById('detail-album-title').textContent = album.title || 'Album không tên';
                    
                    const creatorName = album.artist ? (album.artist.display_name || album.artist.username) : 'Người dùng ẩn danh';
                    const creatorEl = document.getElementById('detail-album-artist');
                    creatorEl.textContent = creatorName;
                    if (album.artist) {
                        creatorEl.href = `/profile/${album.artist.id}/`;
                    }
                    
                    document.getElementById('detail-album-song-count').textContent = `${album.song_count || 0} bài hát,`;
                    
                    if (album.total_duration) {
                        const hours = Math.floor(album.total_duration / 3600);
                        const minutes = Math.floor((album.total_duration % 3600) / 60);
                        let durationText = 'khoảng ';
                        if (hours > 0) durationText += `${hours} giờ `;
                        durationText += `${minutes} phút`;
                        document.getElementById('detail-album-duration').textContent = durationText;
                    } else {
                        document.getElementById('detail-album-duration').textContent = '';
                        document.getElementById('detail-album-song-count').textContent = `${album.song_count || 0} bài hát`;
                    }
                    
                    // Hiển thị trạng thái Thả tim album
                    const btnLikeAlbum = document.getElementById('btn-like-album');
                    if (btnLikeAlbum) {
                        if (album.is_liked) {
                            btnLikeAlbum.className = 'bi bi-heart-fill action-icon position-relative text-accent';
                        } else {
                            btnLikeAlbum.className = 'bi bi-heart action-icon position-relative hover-text-white';
                        }
                    }
                    
                    // Hiển thị tính năng chỉnh sửa nếu là owner
                    const liEdit = document.getElementById('li-edit-album');
                    const liDelete = document.getElementById('li-delete-album');
                    const addSongsSection = document.querySelector('.album-add-songs-section');
                    if (album.is_owner) {
                        if (liEdit) liEdit.style.display = 'block';
                        if (liDelete) liDelete.style.display = 'block';
                        if (addSongsSection) addSongsSection.style.display = 'block';
                            
                            // Populate Edit Modal
                            const editModalBtn = document.getElementById('btn-edit-album');
                            const editTitleInput = document.getElementById('editAlbumTitle');
                            const editCoverPreview = document.getElementById('editAlbumCoverPreview');
                            const editCoverUpload = document.getElementById('editAlbumCoverUpload');
                            let selectedCoverFile = null;

                            if (editModalBtn) {
                                editModalBtn.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    // Đóng menu dropdown
                                    const menu = editModalBtn.closest('.custom-dropdown-menu');
                                    if (menu) menu.style.display = 'none';
                                    
                                    // Nạp dữ liệu vào form
                                    editTitleInput.value = album.title || '';
                                    editCoverPreview.src = album.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80';
                                    selectedCoverFile = null; // reset
                                    
                                    // Hiển thị modal
                                    const modalEl = document.getElementById('editAlbumModal');
                                    const modal = new bootstrap.Modal(modalEl);
                                    modal.show();
                                });
                            }

                            if (editCoverUpload) {
                                editCoverUpload.addEventListener('change', function() {
                                    if (this.files && this.files[0]) {
                                        selectedCoverFile = this.files[0];
                                        const reader = new FileReader();
                                        reader.onload = (e) => editCoverPreview.src = e.target.result;
                                        reader.readAsDataURL(selectedCoverFile);
                                    }
                                });
                            }

                            const saveBtn = document.getElementById('btn-save-edit-album');
                            if (saveBtn) {
                                saveBtn.addEventListener('click', async function() {
                                    const originalBtnText = this.innerHTML;
                                    this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
                                    this.disabled = true;

                                    let hasUpdates = false;

                                    // Update Title
                                    const newTitle = editTitleInput.value.trim();
                                    if (newTitle && newTitle !== album.title) {
                                        try {
                                            const res = await fetch(`/api/v1/music/albums/${albumId}/`, {
                                                method: 'PATCH',
                                                headers: {
                                                    'Content-Type': 'application/json',
                                                    'X-CSRFToken': getCookie('csrftoken')
                                                },
                                                body: JSON.stringify({ title: newTitle })
                                            });
                                            if (res.ok) {
                                                album.title = newTitle;
                                                document.getElementById('detail-album-title').textContent = newTitle;
                                                hasUpdates = true;
                                            }
                                        } catch (e) {
                                            console.error(e);
                                        }
                                    }

                                    // Update Cover
                                    if (selectedCoverFile) {
                                        try {
                                            const formData = new FormData();
                                            formData.append('cover_image', selectedCoverFile);
                                            const res = await fetch(`/api/v1/music/albums/${albumId}/cover/`, {
                                                method: 'POST',
                                                headers: {
                                                    'X-CSRFToken': getCookie('csrftoken')
                                                },
                                                body: formData
                                            });
                                            const data = await res.json();
                                            if (res.ok && data.success) {
                                                album.cover_image = data.data.cover_image;
                                                imgEl.src = album.cover_image;
                                                hasUpdates = true;
                                            }
                                        } catch (e) {
                                            console.error(e);
                                        }
                                    }

                                    this.innerHTML = originalBtnText;
                                    this.disabled = false;

                                    if (hasUpdates) {
                                        if (window.showToast) showToast('Đã lưu thay đổi', 'success');
                                        // Quick update sidebar
                                        const sbTitle = document.querySelector(`.album-item a[href*="${albumId}"] .text-truncate`);
                                        if(sbTitle && album.title) sbTitle.textContent = album.title;
                                        const sbImg = document.querySelector(`.album-item a[href*="${albumId}"] img`);
                                        if(sbImg && album.cover_image) sbImg.src = album.cover_image;
                                    }
                                    
                                    // Close modal
                                    const modalEl = document.getElementById('editAlbumModal');
                                    const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                                    modalInstance.hide();
                                });
                            }
                        } else {
                            if (addSongsSection) addSongsSection.style.display = 'none';
                        }
                    
                    // Render right away using album.songs
                    if (album && album.songs) {
                        renderAlbumSongs(album.songs);
                    } else {
                        document.getElementById('album-songs-container').innerHTML = '<div class="text-center py-4 text-secondary">Album này chưa có bài hát nào.</div>';
                    }
                    
                } else {
                    document.getElementById('detail-album-title').textContent = "Không tìm thấy album";
                }
            })
            .catch(err => {
                console.error('Lỗi khi tải album:', err);
                document.getElementById('detail-album-title').textContent = "Lỗi tải dữ liệu";
            });
    } else {
        document.getElementById('detail-album-title').textContent = "Không tìm thấy Album";
        document.getElementById('detail-album-artist').textContent = "";
        document.getElementById('detail-album-song-count').textContent = "";
        document.getElementById('detail-album-duration').textContent = "";
        document.getElementById('album-songs-container').innerHTML = '<div class="text-center py-5 text-secondary"><i class="bi bi-exclamation-triangle fs-1 d-block mb-3"></i><h4>Đường dẫn không hợp lệ</h4><p>Không tìm thấy ID của Album. Vui lòng quay lại và chọn một Album hợp lệ.</p><a href="/album/" class="btn btn-outline-light rounded-pill mt-3 px-4">Quay lại Album</a></div>';
        
        // Ẩn các control không cần thiết
        const controls = document.querySelector('.album-controls');
        if (controls) controls.style.display = 'none';
        
        const addSongsSection = document.querySelector('.album-add-songs-section');
        if (addSongsSection) addSongsSection.style.display = 'none';
    }

    function renderAlbumSongs(songs) {
        const container = document.getElementById('album-songs-container');
        if (!songs || songs.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">Album này chưa có bài hát nào.</div>';
            return;
        }
        
        // Hàm format duration
        const formatDuration = (seconds) => {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}:${s < 10 ? '0' : ''}${s}`;
        };
        
        // Hàm format thời gian (ngày thêm)
        const formatDate = (isoString) => {
            const date = new Date(isoString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            if (diffDays <= 1) return 'Hôm nay';
            if (diffDays <= 30) return `${diffDays} ngày trước`;
            if (diffDays <= 365) return `${Math.floor(diffDays/30)} tháng trước`;
            return `${Math.floor(diffDays/365)} năm trước`;
        };

        let html = '';
        songs.forEach((item, index) => {
            const song = item.song;
            const artistName = song.artist ? (song.artist.display_name || song.artist.username) : 'Nghệ sĩ ẩn danh';
            const coverImg = song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&w=40&h=40&fit=crop';
            
            html += `
                <div class="album-grid album-grid-row py-2 px-3 rounded position-relative">
                    <div class="text-secondary text-center">${index + 1}</div>
                    <div class="d-flex align-items-center gap-3 text-truncate">
                        <img src="${coverImg}" class="rounded flex-shrink-0" alt="cover" style="width: 40px; height: 40px; object-fit: cover; cursor: pointer;" onclick="window.goToPage('/song/?id=${song.id}')">
                        <div class="text-truncate">
                            <div class="fw-semibold text-truncate text-white" style="cursor: pointer;" onclick="window.goToPage('/song/?id=${song.id}')">${song.title}</div>
                            <div class="small text-secondary text-truncate">${artistName}</div>
                        </div>
                    </div>
                    <div class="text-secondary hide-md text-truncate">${(song.play_count || 0).toLocaleString('vi-VN')}</div>
                    <div class="text-secondary hide-lg text-truncate">${formatDate(item.added_at)}</div>
                    <div class="text-secondary">${formatDuration(song.duration || 0)}</div>
                    <div class="text-secondary text-center position-relative btn-like" data-song-id="${song.id}" style="z-index: 2;" onclick="event.stopPropagation()">
                        <i class="bi ${song.is_liked ? 'bi-heart-fill text-accent' : 'bi-heart hover-text-white'} position-relative" style="cursor: pointer; transition: color 0.2s; font-size: 1.2rem;"></i>
                    </div>
                    <div class="position-relative">
                        <div class="custom-dropdown-toggle" style="cursor: pointer; display: inline-flex; align-items: center; justify-content: center;">
                            <i class="bi bi-three-dots-vertical action-icon hover-text-white" style="font-size: 1.2rem;"></i>
                        </div>
                        <ul class="custom-dropdown-menu dropdown-menu-dark shadow" style="display: none; position: absolute; right: 0; top: 100%; list-style: none; padding: 0.5rem 0; margin: 0; min-width: 200px; background-color: var(--bg-card); border: 1px solid rgba(255,255,255,0.1); border-radius: 0.375rem; margin-top: 10px; z-index: 1050;">
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white btn-queue-next" href="#" data-song-id="${song.id}" onclick="window.queueNext('${song.id}', event)"><i class="bi bi-music-note-list"></i> Phát tiếp theo</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white btn-add-to-other" href="#" data-song-id="${song.id}"><i class="bi bi-plus-circle"></i> Thêm vào playlist khác</a></li>
                            ${window._currentAlbum && window._currentAlbum.is_owner ? `
                            <li><hr class="dropdown-divider border-secondary opacity-25 my-1"></li>
                            <li><a class="dropdown-item text-danger d-flex align-items-center gap-2 py-2 px-3 text-decoration-none btn-remove-from-album" href="#" data-song-id="${song.id}"><i class="bi bi-trash"></i> Xóa khỏi album</a></li>
                            ` : ''}
                        </ul>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

        // Gắn sự kiện nút thả tim
        document.querySelectorAll('.btn-like').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation();
                const songId = this.getAttribute('data-song-id');
                const icon = this.querySelector('i');
                
                // Optimistic UI update
                const isCurrentlyLiked = icon.classList.contains('bi-heart-fill');
                if (isCurrentlyLiked) {
                    icon.className = 'bi bi-heart position-relative hover-text-white';
                } else {
                    icon.className = 'bi bi-heart-fill position-relative text-accent';
                }
                
                try {
                    const res = await fetch(`/api/v1/music/songs/${songId}/like/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });
                    const data = await res.json();
                    if (!res.ok || !data.success) {
                        // Revert on API failure
                        if (isCurrentlyLiked) {
                            icon.className = 'bi bi-heart-fill position-relative text-accent';
                        } else {
                            icon.className = 'bi bi-heart position-relative hover-text-white';
                        }
                        console.error('Lỗi khi thả tim:', data.error?.message);
                    }
                } catch (err) {
                    // Revert on network failure
                    if (isCurrentlyLiked) {
                        icon.className = 'bi bi-heart-fill position-relative text-accent';
                    } else {
                        icon.className = 'bi bi-heart position-relative hover-text-white';
                    }
                    console.error('Lỗi mạng khi thả tim:', err);
                }
            });
        });
        
        // Xoá bài hát khỏi album
        document.querySelectorAll('.btn-remove-from-album').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                // Gán id bài hát vào data attribute của nút xác nhận xoá
                const confirmBtn = document.getElementById('btn-confirm-delete');
                if (confirmBtn) {
                    confirmBtn.setAttribute('data-song-id', this.getAttribute('data-song-id'));
                }
                // Hiển thị modal
                const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
                deleteModal.show();
            });
        });
    }

    // Xử lý các menu 3 chấm (tự tạo)
    document.addEventListener('click', function(e) {
        var toggle = e.target.closest('.custom-dropdown-toggle');
        
        document.querySelectorAll('.custom-dropdown-menu').forEach(function(menu) {
            // Nếu click ra ngoài, hoặc click vào toggle khác, thì ẩn menu đi
            if (!toggle || menu !== toggle.nextElementSibling) {
                menu.style.display = 'none';
            }
        });
        
        if (toggle) {
            e.preventDefault();
            e.stopPropagation();
            var menu = toggle.nextElementSibling;
            if (menu && menu.classList.contains('custom-dropdown-menu')) {
                if (menu.style.display === 'block') {
                    menu.style.display = 'none';
                } else {
                    menu.style.display = 'block';
                }
            }
        }
    });

    // Xử lý nút xác nhận xoá trong modal
    const btnConfirmDelete = document.getElementById('btn-confirm-delete');
    if (btnConfirmDelete) {
        btnConfirmDelete.addEventListener('click', async function() {
            const songId = this.getAttribute('data-song-id');
            if (!songId) return;
            
            try {
                const res = await fetch(`/api/v1/music/albums/${albumId}/songs/${songId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                
                if (res.ok) {
                    if (window.showToast) showToast('Đã xóa bài hát khỏi album', 'success');
                    if (window.loadAlbumSongs) window.loadAlbumSongs(); // Tải lại danh sách
                } else {
                    const data = await res.json().catch(() => ({}));
                    if (window.showToast) showToast(data.error?.message || 'Không thể xóa bài hát', 'error');
                }
            } catch (err) {
                console.error('Lỗi khi xóa bài hát:', err);
                if (window.showToast) showToast('Lỗi kết nối', 'error');
            } finally {
                const modalEl = document.getElementById('deleteConfirmModal');
                const modalInstance = bootstrap.Modal.getInstance(modalEl);
                if (modalInstance) {
                    modalInstance.hide();
                }
                this.removeAttribute('data-song-id');
            }
        });
    }
    
    // Xoá Album toàn bộ
    const btnDeleteAlbum = document.getElementById('btn-delete-album');
    if (btnDeleteAlbum) {
        btnDeleteAlbum.addEventListener('click', async function(e) {
            e.preventDefault();
            if (!confirm('Bạn có chắc chắn muốn xóa toàn bộ album này? Hành động này không thể hoàn tác!')) return;
            
            try {
                const res = await fetch(`/api/v1/music/albums/${albumId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                if (res.ok) {
                    if (window.showToast) showToast('Đã xóa album thành công', 'success');
                    setTimeout(() => {
                        window.goToPage('/'); // Quay về trang chủ
                    }, 1000);
                } else {
                    const data = await res.json().catch(() => ({}));
                    if (window.showToast) showToast(data.error?.message || 'Không thể xóa album', 'error');
                }
            } catch (err) {
                console.error('Lỗi xóa album:', err);
                if (window.showToast) showToast('Lỗi kết nối', 'error');
            }
        });
    }

    // Thêm toàn bộ bài hát vào danh sách phát (hàng đợi)
    const btnAddToLibrary = document.getElementById('btn-add-to-library');
    if (btnAddToLibrary) {
        btnAddToLibrary.addEventListener('click', function() {
            if (window._currentAlbum && window._currentAlbum.songs && window._currentAlbum.songs.length > 0) {
                const albumName = document.getElementById('detail-album-title').textContent || 'Album';
                let addedCount = 0;
                
                window._currentAlbum.songs.forEach(item => {
                    const s = item.song;
                    const artistName = s.artist ? (s.artist.display_name || s.artist.username || 'Unknown') : 'Unknown';
                    if (window.addToQueue) {
                        window.addToQueue(s.id, s.title, artistName, s.cover_image, `Từ ${albumName}`, true);
                        addedCount++;
                    }
                });
                
                if (addedCount > 0 && window.showToast) {
                    window.showToast(`Đã thêm ${addedCount} bài hát vào danh sách chờ`, 'success');
                }
            } else {
                if (window.showToast) showToast('Album trống', 'warning');
            }
        });
    }

    // Gắn API backend cho nút phát nhạc Album
    const btnPlayAlbum = document.getElementById('btn-play-album');
    if (btnPlayAlbum) {
        btnPlayAlbum.addEventListener('click', function(e) {
            if (!albumId) {
                if (window.showToast) showToast('Chưa có ID Album hợp lệ!', 'error');
                return;
            } 
            if (window.playAlbum) {
                window.playAlbum(albumId, e);
            } else {
                if (window.showToast) showToast('Hệ thống phát nhạc chưa sẵn sàng.', 'error');
            }
        });
    }

    // --- Logic "Tìm thêm" bài hát vào album ---
    const btnToggleSearch = document.getElementById('btn-toggle-search');
    const searchArea = document.getElementById('albumSearchArea');
    const searchInput = document.getElementById('albumSearchInput');
    const searchResults = document.getElementById('albumSearchResults');
    const searchLoading = document.getElementById('albumSearchLoading');
    const btnCloseSearch = document.getElementById('btn-close-search');
    const btnSearchContainer = document.getElementById('btn-search-container');
    const albumSearchWrapper = document.getElementById('albumSearchWrapper');
    
    let searchTimeout = null;

    if (btnToggleSearch) {
        btnToggleSearch.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Hide "Tìm thêm" button instantly to prevent blur/ghosting
            btnSearchContainer.style.opacity = '0';
            btnSearchContainer.style.pointerEvents = 'none';

            // Show search area with slide-in
            searchArea.style.pointerEvents = 'auto';
            searchArea.style.transform = 'translateX(0)';
            searchArea.style.opacity = '1';
            
            // Adjust wrapper height to match search area
            albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
            
            setTimeout(() => {
                searchInput.focus();
            }, 400); // Focus after slide finishes

            if(searchInput.value.trim() !== '') {
                performSearch(searchInput.value.trim());
            }
        });
    }
    
    if (btnCloseSearch) {
        btnCloseSearch.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Slide out search area
            searchArea.style.transform = 'translateX(100%)';
            searchArea.style.opacity = '0';
            searchArea.style.pointerEvents = 'none';
            
            // Shrink wrapper back to initial height
            albumSearchWrapper.style.height = '38px';
            
            // Show "Tìm thêm" button again smoothly
            setTimeout(() => {
                btnSearchContainer.style.opacity = '1';
                btnSearchContainer.style.pointerEvents = 'auto';
            }, 200);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            clearTimeout(searchTimeout);
            if (query === '') {
                searchResults.style.display = 'none';
                searchResults.innerHTML = '';
                albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
                return;
            }
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 500);
        });
    }

    async function performSearch(query) {
        searchLoading.style.display = 'block';
        searchResults.style.display = 'none';
        albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        
        try {
            const res = await fetch(`/api/v1/music/songs/?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            if (data.success && data.data && data.data.items) {
                renderSearchResults(data.data.items);
            } else {
                searchResults.innerHTML = '<div class="text-secondary p-3">Không tìm thấy bài hát nào.</div>';
                searchResults.style.display = 'block';
                albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
            }
        } catch (e) {
            console.error('Search error:', e);
            searchResults.innerHTML = '<div class="text-danger p-3">Lỗi tìm kiếm.</div>';
            searchResults.style.display = 'block';
            albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        } finally {
            searchLoading.style.display = 'none';
            albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        }
    }

    function renderSearchResults(songs) {
        if (songs.length === 0) {
            searchResults.innerHTML = '<div class="text-secondary p-3">Không tìm thấy bài hát nào.</div>';
            searchResults.style.display = 'block';
            albumSearchWrapper.style.height = searchArea.offsetHeight + 'px';
            return;
        }
        
        let html = '<div class="d-flex flex-column gap-2">';
        songs.forEach(song => {
            const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
            const coverImg = song.cover_image ? song.cover_image : 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
            html += `
                <div class="d-flex align-items-center justify-content-between p-2 rounded hover-bg-secondary transition-colors">
                    <div class="d-flex align-items-center gap-3 overflow-hidden">
                        <img src="${coverImg}" alt="${song.title}" class="rounded flex-shrink-0" style="width: 48px; height: 48px; object-fit: cover; cursor: pointer;" onclick="window.goToPage('/song/?id=${song.id}')">
                        <div class="overflow-hidden">
                            <div class="text-white fw-semibold text-truncate" style="font-size: 1rem; cursor: pointer;" onclick="window.goToPage('/song/?id=${song.id}')">${song.title}</div>
                            <div class="text-secondary text-truncate small" style="font-size: 0.85rem;">Bài hát • ${artistName}</div>
                        </div>
                    </div>
                    <button class="btn btn-link text-secondary hover-text-white p-2 text-decoration-none add-to-album-btn flex-shrink-0" data-song-id="${song.id}">
                        <i class="bi bi-plus-circle fs-5" style="transition: color 0.2s;"></i>
                    </button>
                </div>
            `;
        });
        html += '</div>';
        
        searchResults.innerHTML = html;
        searchResults.style.display = 'block';

        // Add event listeners to "Thêm" buttons
        document.querySelectorAll('.add-to-album-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation(); // Prevent row click if any
                const songId = this.getAttribute('data-song-id');
                
                try {
                    const res = await fetch(`/api/v1/music/albums/${albumId}/songs/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: JSON.stringify({ song_id: songId })
                    });
                    
                    const data = await res.json();
                    
                    if (res.ok && data.success) {
                        if (window.showToast) {
                            showToast('Đã thêm bài hát vào album thành công', 'success');
                        }
                        this.innerHTML = '<i class="bi bi-check-circle-fill fs-5 text-success"></i>';
                        this.classList.remove('hover-text-white');
                        this.disabled = true;
                        
                        // Tải lại danh sách bên dưới
                        if(window.loadAlbumSongs) {
                            window.loadAlbumSongs();
                        }
                    } else {
                        if (window.showToast) {
                            showToast(data.error?.message || 'Có lỗi xảy ra', 'error');
                        }
                    }
                } catch(err) {
                    console.error(err);
                    if (window.showToast) {
                        showToast('Lỗi kết nối', 'error');
                    }
                }
            });
        });
    }
});

(function () {
    const DEFAULT_COVER_PL   = 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=300&q=80';
    const DEFAULT_COVER_SONG = 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?w=300&q=80';

    function renderSimilarAlbums(items) {
        const container = document.getElementById('similar-albums-container');
        if (!container) return;
        if (!items || items.length === 0) {
            document.getElementById('similar-albums-wrapper').style.display = 'none';
            return;
        }
        container.innerHTML = items.map(pl => {
            const cover = pl.cover_image || DEFAULT_COVER_PL;
            const owner = pl.owner ? pl.owner.display_name : '';
            const count = pl.song_count != null ? ` &bull; ${pl.song_count} b&agrave;i` : '';
            return `
            <a href="/album/detail/?id=${pl.id}" class="pl-reco-card">
                <div class="card-img-wrap">
                    <img src="${cover}" alt="${pl.title}" loading="lazy">
                    <button onclick="event.preventDefault();event.stopPropagation();if(window.playAlbum)window.playAlbum('${pl.id}',event)"
                        style="position:absolute;bottom:8px;right:8px;width:34px;height:34px;border-radius:50%;
                               background:var(--accent-color,#2dd4bf);color:#000;border:none;
                               display:flex;align-items:center;justify-content:center;
                               opacity:0;transition:opacity .2s;font-size:.95rem;"
                        onmouseover="this.style.opacity='1'" class="pl-play-inner">
                        <i class="bi bi-play-fill"></i>
                    </button>
                </div>
                <div class="card-title-text">${pl.title}</div>
                <div class="card-sub-text">b&#7903;i ${owner}${count}</div>
            </a>`;
        }).join('');
        // hover effect on play button via CSS handled; show on card hover
        container.querySelectorAll('.pl-reco-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                const btn = card.querySelector('.pl-play-inner');
                if (btn) btn.style.opacity = '1';
            });
            card.addEventListener('mouseleave', () => {
                const btn = card.querySelector('.pl-play-inner');
                if (btn) btn.style.opacity = '0';
            });
        });
    }

    function renderRecommendedSongs(items) {
        const container = document.getElementById('recommended-songs-container');
        if (!container) return;
        if (!items || items.length === 0) {
            document.getElementById('recommended-songs-wrapper').style.display = 'none';
            return;
        }
        container.innerHTML = items.map(songData => {
            const song   = songData.song || songData;
            const cover  = song.cover_image || DEFAULT_COVER_SONG;
            const artist = song.artist ? song.artist.display_name : 'Ngh&#7879; s&#297;';
            return `
            <div class="song-reco-card" onclick="window.goToPage('/song/?id=${song.id}')">
                <div class="card-img-wrap">
                    <img src="${cover}" alt="${song.title}" loading="lazy">
                    <button class="play-overlay"
                            onclick="event.stopPropagation();if(window.playSong)window.playSong('${song.id}',event)">
                        <i class="bi bi-play-fill"></i>
                    </button>
                </div>
                <div class="card-title-text">${song.title}</div>
                <div class="card-sub-text">${artist}</div>
            </div>`;
        }).join('');
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Load song recommendations (for-you or trending nếu guest)
        fetch('/api/v1/recommendations/for-you/?page_size=10')
            .then(r => r.json())
            .then(data => {
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    renderRecommendedSongs(data.data.items);
                } else {
                    // fallback: trending
                    return fetch('/api/v1/music/songs/trending/?page_size=10')
                        .then(r => r.json())
                        .then(d => {
                            if (d.success && d.data && d.data.items) {
                                renderRecommendedSongs(d.data.items);
                            } else {
                                document.getElementById('recommended-songs-wrapper').style.display = 'none';
                            }
                        });
                }
            })
            .catch(() => {
                document.getElementById('recommended-songs-wrapper').style.display = 'none';
            });

        // Load similar albums (recommended albums)
        fetch('/api/v1/recommendations/albums/?limit=8')
            .then(r => r.json())
            .then(data => {
                if (data.success && data.data && data.data.items) {
                    renderSimilarAlbums(data.data.items);
                } else {
                    document.getElementById('similar-albums-wrapper').style.display = 'none';
                }
            })
            .catch(() => {
                document.getElementById('similar-albums-wrapper').style.display = 'none';
            });
    });
})();
