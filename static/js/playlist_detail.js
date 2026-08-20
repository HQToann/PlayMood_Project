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

    // Lấy ID playlist từ URL (?id=...)
    const urlParams = new URLSearchParams(window.location.search);
    const playlistId = urlParams.get('id');

    if (playlistId) {
        // Tải thông tin playlist
        fetch(`/api/v1/playlists/${playlistId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data) {
                    const playlist = data.data;
                    window._currentPlaylist = playlist;
                    
                    const coverUrl = playlist.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80';
                    const imgEl = document.getElementById('detail-playlist-cover');
                    imgEl.crossOrigin = "Anonymous";
                    
                    // Lấy màu nền khi ảnh đã tải xong
                    imgEl.addEventListener('load', function () {
                        try {
                            const colorThief = new ColorThief();
                            const color = colorThief.getColor(imgEl);
                            if (color) {
                                const playlistHeader = document.querySelector('.playlist-header');
                                // Đổi nền gradient với màu của ảnh (có độ trong suốt 0.4 để màu tối hơn)
                                playlistHeader.style.background = `linear-gradient(to bottom, rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.4), var(--bg-app))`;
                            }
                        } catch (e) {
                            console.warn('Không thể lấy màu nền từ ảnh do lỗi CORS hoặc thư viện.', e);
                        }
                    });
                    
                    imgEl.src = coverUrl;
                    imgEl.alt = playlist.title || 'Playlist';
                    
                    document.getElementById('detail-playlist-title').textContent = playlist.title || 'Playlist không tên';
                    
                    const creatorName = playlist.owner ? (playlist.owner.display_name || playlist.owner.username) : 'Người dùng ẩn danh';
                    const creatorEl = document.getElementById('detail-playlist-creator');
                    creatorEl.textContent = creatorName;
                    if (playlist.owner) {
                        creatorEl.href = `/profile/${playlist.owner.id}/`;
                    }
                    
                    document.getElementById('detail-playlist-song-count').textContent = `${playlist.song_count || 0} bài hát,`;
                    
                    if (playlist.total_duration) {
                        const hours = Math.floor(playlist.total_duration / 3600);
                        const minutes = Math.floor((playlist.total_duration % 3600) / 60);
                        let durationText = 'khoảng ';
                        if (hours > 0) durationText += `${hours} giờ `;
                        durationText += `${minutes} phút`;
                        document.getElementById('detail-playlist-duration').textContent = durationText;
                    } else {
                        document.getElementById('detail-playlist-duration').textContent = '';
                        document.getElementById('detail-playlist-song-count').textContent = `${playlist.song_count || 0} bài hát`;
                    }
                    
                    // Hiển thị menu xóa hoặc báo cáo dựa vào quyền owner
                    const liEdit = document.getElementById('li-edit-playlist');
                    const liDelete = document.getElementById('li-delete-playlist');
                    const liReport = document.getElementById('li-report-playlist');
                    
                    // Dùng === true để tránh null/undefined bị coi là truthy
                    if (playlist.is_owner === true) {
                        if (liEdit) liEdit.style.display = 'block';
                        if (liDelete) liDelete.style.display = 'block';
                        if (liReport) liReport.style.display = 'none';
                        
                        const addSongsSection = document.querySelector('.playlist-add-songs-section');
                        if (addSongsSection) addSongsSection.style.display = 'block';

                        // Populate Edit Modal
                        const editModalBtn = document.getElementById('btn-edit-playlist');
                        if (editModalBtn) {
                            editModalBtn.addEventListener('click', (e) => {
                                e.preventDefault();
                                const menu = editModalBtn.closest('.custom-dropdown-menu');
                                if (menu) menu.style.display = 'none';
                                
                                if (typeof window.openPlaylistFormModal === 'function') {
                                    window.openPlaylistFormModal(window._currentPlaylist);
                                }
                            });
                        }
                        
                        // Handle Playlist Delete
                        const deleteBtn = document.getElementById('btn-delete-playlist');
                        if (deleteBtn) {
                            deleteBtn.addEventListener('click', (e) => {
                                e.preventDefault();
                                const menu = deleteBtn.closest('.custom-dropdown-menu');
                                if (menu) menu.style.display = 'none';
                                
                                // Mở modal xóa playlist
                                const deletePlaylistModal = new bootstrap.Modal(document.getElementById('deletePlaylistConfirmModal'));
                                deletePlaylistModal.show();
                                
                                const confirmDeleteBtn = document.getElementById('btn-confirm-delete-playlist-modal');
                                
                                // Gỡ bỏ sự kiện cũ để tránh bị gọi nhiều lần nếu người dùng bấm hủy rồi mở lại
                                const newConfirmDeleteBtn = confirmDeleteBtn.cloneNode(true);
                                confirmDeleteBtn.parentNode.replaceChild(newConfirmDeleteBtn, confirmDeleteBtn);
                                
                                newConfirmDeleteBtn.addEventListener('click', () => {
                                    // Đổi nút thành trạng thái loading
                                    const originalText = newConfirmDeleteBtn.innerHTML;
                                    newConfirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xóa...';
                                    newConfirmDeleteBtn.disabled = true;

                                    fetch(`/api/v1/playlists/${playlistId}/`, {
                                        method: 'DELETE',
                                        headers: {
                                            'X-CSRFToken': getCookie('csrftoken')
                                        }
                                    })
                                    .then(res => {
                                        if (res.ok) {
                                            deletePlaylistModal.hide();
                                            if (window.showToast) window.showToast('Đã xóa playlist', 'success');
                                            setTimeout(() => {
                                                window.goToPage ? window.goToPage('/explore/') : window.location.href = '/explore/';
                                            }, 500);
                                        } else {
                                            throw new Error('Lỗi khi xóa playlist');
                                        }
                                    })
                                    .catch(err => {
                                        console.error(err);
                                        deletePlaylistModal.hide();
                                        if (window.showToast) window.showToast('Lỗi khi xóa playlist', 'error');
                                        newConfirmDeleteBtn.innerHTML = originalText;
                                        newConfirmDeleteBtn.disabled = false;
                                    });
                                });
                            });
                        }
                    } else {
                        if (liEdit) liEdit.style.display = 'none';
                        if (liDelete) liDelete.style.display = 'none';
                        if (liReport) liReport.style.display = 'block';
                        
                        const addSongsSection = document.querySelector('.playlist-add-songs-section');
                        if (addSongsSection) addSongsSection.style.display = 'none';
                        
                        // Handle Playlist Report
                        const reportBtn = document.getElementById('btn-report-playlist');
                        if (reportBtn) {
                            reportBtn.addEventListener('click', (e) => {
                                e.preventDefault();
                                const menu = reportBtn.closest('.custom-dropdown-menu');
                                if (menu) menu.style.display = 'none';
                                
                                const reportModal = new bootstrap.Modal(document.getElementById('reportPlaylistModal'));
                                reportModal.show();
                                
                                // Setup submit
                                const submitReportBtn = document.getElementById('btn-submit-report-playlist');
                                const newSubmitReportBtn = submitReportBtn.cloneNode(true);
                                submitReportBtn.parentNode.replaceChild(newSubmitReportBtn, submitReportBtn);
                                
                                newSubmitReportBtn.addEventListener('click', async () => {
                                    const reasonEl = document.getElementById('reportPlaylistReason');
                                    const descriptionEl = document.getElementById('reportPlaylistDescription');
                                    
                                    if (!reasonEl.value) {
                                        if (window.showToast) window.showToast('Vui lòng chọn lý do báo cáo.', 'warning');
                                        return;
                                    }
                                    
                                    const originalText = newSubmitReportBtn.innerHTML;
                                    newSubmitReportBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
                                    newSubmitReportBtn.disabled = true;

                                    try {
                                        const res = await fetch('/api/v1/music/reports/', {
                                            method: 'POST',
                                            headers: {
                                                'Content-Type': 'application/json',
                                                'X-CSRFToken': getCookie('csrftoken')
                                            },
                                            body: JSON.stringify({
                                                target_type: 'playlist',
                                                target_id: playlistId,
                                                reason: reasonEl.value,
                                                description: descriptionEl ? descriptionEl.value : ''
                                            })
                                        });
                                        const data = await res.json();
                                        
                                        if (res.ok && data.success) {
                                            if (window.showToast) window.showToast("Cảm ơn bạn. Báo cáo của bạn đã được ghi nhận.", 'success');
                                            reportModal.hide();
                                            reasonEl.value = '';
                                            document.getElementById('reportPlaylistReasonText').innerText = 'Chọn lý do...';
                                            if (descriptionEl) descriptionEl.value = '';
                                        } else {
                                            throw new Error(data.error?.message || 'Lỗi khi gửi báo cáo');
                                        }
                                    } catch (err) {
                                        console.error(err);
                                        if (window.showToast) window.showToast(err.message, 'error');
                                    } finally {
                                        newSubmitReportBtn.innerHTML = originalText;
                                        newSubmitReportBtn.disabled = false;
                                    }
                                });
                            });
                        }
                    }
                    
                    
                } else {
                    document.getElementById('detail-playlist-title').textContent = "Không tìm thấy playlist";
                }
            })
            .catch(err => {
                console.error('Lỗi khi tải playlist:', err);
                document.getElementById('detail-playlist-title').textContent = "Lỗi tải dữ liệu";
            });

        // Hàm tải lại danh sách bài hát
        window.loadPlaylistSongs = function() {
            fetch(`/api/v1/playlists/${playlistId}/songs/`)
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.data && data.data.items) {
                        window._currentPlaylistSongs = data.data.items;
                        renderPlaylistSongs(data.data.items);
                    } else {
                        document.getElementById('playlist-songs-container').innerHTML = '<div class="text-center py-4 text-secondary">Lỗi tải danh sách bài hát</div>';
                    }
                })
                .catch(err => {
                    console.error('Lỗi khi tải danh sách bài hát:', err);
                    document.getElementById('playlist-songs-container').innerHTML = '<div class="text-center py-4 text-secondary">Lỗi kết nối</div>';
                });
        };
        
        // Khởi chạy lần đầu
        loadPlaylistSongs();
    } else {
        document.getElementById('detail-playlist-title').textContent = "Không tìm thấy Playlist";
        document.getElementById('detail-playlist-creator').textContent = "";
        document.getElementById('detail-playlist-song-count').textContent = "";
        document.getElementById('detail-playlist-duration').textContent = "";
        document.getElementById('playlist-songs-container').innerHTML = '<div class="text-center py-5 text-secondary"><i class="bi bi-exclamation-triangle fs-1 d-block mb-3"></i><h4>Đường dẫn không hợp lệ</h4><p>Không tìm thấy ID của Playlist. Vui lòng quay lại và chọn một Playlist hợp lệ.</p><a href="/playlist/" class="btn btn-outline-light rounded-pill mt-3 px-4">Quay lại Playlist</a></div>';
        
        // Ẩn các control không cần thiết
        const controls = document.querySelector('.playlist-controls');
        if (controls) controls.style.display = 'none';
        
        const addSongsSection = document.querySelector('.playlist-add-songs-section');
        if (addSongsSection) addSongsSection.style.display = 'none';
    }

    function renderPlaylistSongs(songs) {
        const container = document.getElementById('playlist-songs-container');
        if (!songs || songs.length === 0) {
            container.innerHTML = '<div class="text-center py-4 text-secondary">Playlist này chưa có bài hát nào.</div>';
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
                <div class="playlist-grid playlist-grid-row py-2 px-3 rounded position-relative">
                    <div class="text-secondary text-center">${index + 1}</div>
                    <div class="d-flex align-items-center gap-3 text-truncate">
                        <a href="/song/?id=${song.id}" class="text-decoration-none text-reset flex-shrink-0 d-block" style="cursor: pointer;">
                            <img src="${coverImg}" class="rounded" alt="cover" style="width: 40px; height: 40px; object-fit: cover;">
                        </a>
                        <div class="text-truncate">
                            <a href="/song/?id=${song.id}" class="fw-semibold text-truncate text-white text-decoration-none d-block" style="cursor: pointer;">${song.title}</a>
                            <div class="small text-secondary text-truncate">${artistName}</div>
                        </div>
                    </div>
                    <div class="text-secondary hide-md text-truncate">Bài hát đơn</div>
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
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white btn-report-song" href="#" data-song-id="${song.id}"><i class="bi bi-flag"></i> Báo cáo bài hát</a></li>
                            ${window._currentPlaylist && window._currentPlaylist.is_owner ? `
                            <li><hr class="dropdown-divider border-secondary opacity-25 my-1"></li>
                            <li><a class="dropdown-item text-danger d-flex align-items-center gap-2 py-2 px-3 text-decoration-none btn-remove-from-playlist" href="#" data-song-id="${song.id}"><i class="bi bi-trash"></i> Xóa khỏi playlist</a></li>
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
        
        // Xoá bài hát khỏi playlist
        document.querySelectorAll('.btn-remove-from-playlist').forEach(btn => {
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
                const res = await fetch(`/api/v1/playlists/${playlistId}/songs/${songId}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                
                if (res.ok) {
                    if (window.showToast) showToast('Đã xóa bài hát khỏi playlist', 'success');
                    if (window.loadPlaylistSongs) window.loadPlaylistSongs(); // Tải lại danh sách
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
    

    // Thêm toàn bộ bài hát vào danh sách phát (hàng đợi)
    const btnAddToLibrary = document.getElementById('btn-add-to-library');
    if (btnAddToLibrary) {
        btnAddToLibrary.addEventListener('click', function() {
            if (window._currentPlaylistSongs && window._currentPlaylistSongs.length > 0) {
                const playlistName = document.getElementById('detail-playlist-title').textContent || 'Playlist';
                let addedCount = 0;
                
                window._currentPlaylistSongs.forEach(item => {
                    const s = item.song;
                    const artistName = s.artist ? (s.artist.display_name || s.artist.username || 'Unknown') : 'Unknown';
                    if (window.addToQueue) {
                        window.addToQueue(s.id, s.title, artistName, s.cover_image, `Từ ${playlistName}`, true);
                        addedCount++;
                    }
                });
                
                if (addedCount > 0 && window.showToast) {
                    window.showToast(`Đã thêm ${addedCount} bài hát vào danh sách chờ`, 'success');
                }
            } else {
                if (window.showToast) showToast('Playlist trống', 'warning');
            }
        });
    }

    // Gắn API backend cho nút phát nhạc Playlist
    const btnPlayPlaylist = document.getElementById('btn-play-playlist');
    if (btnPlayPlaylist) {
        btnPlayPlaylist.addEventListener('click', function(e) {
            if (!playlistId) {
                if (window.showToast) showToast('Chưa có ID Playlist hợp lệ!', 'error');
                return;
            } 
            if (window.playPlaylist) {
                window.playPlaylist(playlistId, e);
            } else {
                if (window.showToast) showToast('Hệ thống phát nhạc chưa sẵn sàng.', 'error');
            }
        });
    }

    // --- Logic "Tìm thêm" bài hát vào playlist ---
    const btnToggleSearch = document.getElementById('btn-toggle-search');
    const searchArea = document.getElementById('playlistSearchArea');
    const searchInput = document.getElementById('playlistSearchInput');
    const searchResults = document.getElementById('playlistSearchResults');
    const searchLoading = document.getElementById('playlistSearchLoading');
    const btnCloseSearch = document.getElementById('btn-close-search');
    const btnSearchContainer = document.getElementById('btn-search-container');
    const playlistSearchWrapper = document.getElementById('playlistSearchWrapper');
    
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
            playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
            
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
            playlistSearchWrapper.style.height = '38px';
            
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
                playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
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
        playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        
        try {
            const res = await fetch(`/api/v1/music/songs/?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            if (data.success && data.data && data.data.items) {
                renderSearchResults(data.data.items);
            } else {
                searchResults.innerHTML = '<div class="text-secondary p-3">Không tìm thấy bài hát nào.</div>';
                searchResults.style.display = 'block';
                playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
            }
        } catch (e) {
            console.error('Search error:', e);
            searchResults.innerHTML = '<div class="text-danger p-3">Lỗi tìm kiếm.</div>';
            searchResults.style.display = 'block';
            playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        } finally {
            searchLoading.style.display = 'none';
            playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
        }
    }

    function renderSearchResults(songs) {
        if (songs.length === 0) {
            searchResults.innerHTML = '<div class="text-secondary p-3">Không tìm thấy bài hát nào.</div>';
            searchResults.style.display = 'block';
            playlistSearchWrapper.style.height = searchArea.offsetHeight + 'px';
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
                    <button class="btn btn-link text-secondary hover-text-white p-2 text-decoration-none add-to-playlist-btn flex-shrink-0" data-song-id="${song.id}">
                        <i class="bi bi-plus-circle fs-5" style="transition: color 0.2s;"></i>
                    </button>
                </div>
            `;
        });
        html += '</div>';
        
        searchResults.innerHTML = html;
        searchResults.style.display = 'block';

        // Add event listeners to "Thêm" buttons
        document.querySelectorAll('.add-to-playlist-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.stopPropagation(); // Prevent row click if any
                const songId = this.getAttribute('data-song-id');
                
                try {
                    const res = await fetch(`/api/v1/playlists/${playlistId}/songs/`, {
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
                            showToast('Đã thêm bài hát vào playlist thành công', 'success');
                        }
                        this.innerHTML = '<i class="bi bi-check-circle-fill fs-5 text-success"></i>';
                        this.classList.remove('hover-text-white');
                        this.disabled = true;
                        
                        // Tải lại danh sách bên dưới
                        if(window.loadPlaylistSongs) {
                            window.loadPlaylistSongs();
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

    function renderSimilarPlaylists(items) {
        const container = document.getElementById('similar-playlists-container');
        if (!container) return;
        if (!items || items.length === 0) {
            document.getElementById('similar-playlists-wrapper').style.display = 'none';
            return;
        }
        const displayItems = items.slice(0, 6);
        container.innerHTML = displayItems.map(pl => {
            const cover = pl.cover_image || DEFAULT_COVER_PL;
            const owner = pl.owner ? pl.owner.display_name : 'Hệ thống';
            return `
            <a href="/playlist/detail/?id=${pl.id}" class="playlist-card">
                <div class="playlist-card-img-wrap">
                    <img src="${cover}" alt="${pl.title}" loading="lazy">
                </div>
                <div class="playlist-card-title">${pl.title}</div>
                <div class="playlist-card-sub">bởi ${owner}</div>
            </a>`;
        }).join('');
    }

    function renderRecommendedSongs(items) {
        const container = document.getElementById('recommended-songs-container');
        if (!container) return;
        if (!items || items.length === 0) {
            document.getElementById('recommended-songs-wrapper').style.display = 'none';
            return;
        }
        const displayItems = items.slice(0, 5);
        container.innerHTML = displayItems.map(songData => {
            const song   = songData.song || songData;
            const cover  = song.cover_image || DEFAULT_COVER_SONG;
            const artist = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
            return `
            <div class="music-card" onclick="window.goToPage('/song/?id=${song.id}')">
                <div class="music-card-img-wrap">
                    <img src="${cover}" alt="${song.title}" class="music-card-img" loading="lazy">
                </div>
                <div class="music-card-title">${song.title}</div>
                <div class="music-card-artist">${artist}</div>
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

        // Load similar playlists (recommended playlists)
        fetch('/api/v1/recommendations/playlists/?limit=8')
            .then(r => r.json())
            .then(data => {
                if (data.success && data.data && data.data.items) {
                    renderSimilarPlaylists(data.data.items);
                } else {
                    document.getElementById('similar-playlists-wrapper').style.display = 'none';
                }
            })
            .catch(() => {
                document.getElementById('similar-playlists-wrapper').style.display = 'none';
            });
    });
})();

// ════════════════════════════════════════════════════
// REPORT PLAYLIST - Setup độc lập, không phụ thuộc fetch
// ════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function() {
    function getCookieLocal(name) {
        const m = document.cookie.match(new RegExp('(?:^|;)\\s*' + name + '=([^;]*)'));
        return m ? decodeURIComponent(m[1]) : '';
    }

    const submitBtn = document.getElementById('btn-submit-report-playlist');
    if (!submitBtn) return;

    submitBtn.addEventListener('click', async function() {
        const urlParams = new URLSearchParams(window.location.search);
        const playlistId = urlParams.get('id');
        if (!playlistId) {
            alert('Không tìm thấy ID playlist.');
            return;
        }

        const reasonEl = document.getElementById('reportPlaylistReason');
        const descriptionEl = document.getElementById('reportPlaylistDescription');

        if (!reasonEl || !reasonEl.value) {
            if (window.showToast) window.showToast('Vui lòng chọn lý do báo cáo.', false);
            else alert('Vui lòng chọn lý do báo cáo.');
            return;
        }

        const originalText = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
        this.disabled = true;

        try {
            const res = await fetch('/api/v1/music/reports/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookieLocal('csrftoken')
                },
                body: JSON.stringify({
                    target_type: 'playlist',
                    target_id: playlistId,
                    reason: reasonEl.value,
                    description: descriptionEl ? descriptionEl.value : ''
                })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                if (window.showToast) window.showToast('Cảm ơn bạn. Báo cáo đã được ghi nhận.', true);
                // Đóng modal
                const modalEl = document.getElementById('reportPlaylistModal');
                const bsModal = bootstrap.Modal.getInstance(modalEl);
                if (bsModal) bsModal.hide();
                // Reset form
                reasonEl.value = '';
                const reasonText = document.getElementById('reportPlaylistReasonText');
                if (reasonText) reasonText.innerText = 'Chọn lý do...';
                if (descriptionEl) descriptionEl.value = '';
            } else {
                const msg = data.error?.message || 'Lỗi khi gửi báo cáo.';
                if (window.showToast) window.showToast(msg, false);
                else alert(msg);
            }
        } catch(e) {
            console.error('Report error:', e);
            if (window.showToast) window.showToast('Lỗi kết nối: ' + e.message, false);
            else alert('Lỗi kết nối.');
        } finally {
            this.innerHTML = originalText;
            this.disabled = false;
        }
    });
});
