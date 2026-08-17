document.addEventListener('DOMContentLoaded', function () {
    // Lấy ID bài hát từ URL (?id=...)
    const urlParams = new URLSearchParams(window.location.search);
    const songId = urlParams.get('id');

    if (songId) {
        // Hàm format duration từ giây sang mm:ss
        const formatDuration = (seconds) => {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}:${s < 10 ? '0' : ''}${s}`;
        };

        // Gọi API backend
        fetch(`/api/v1/music/songs/${songId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data) {
                    const song = data.data;

                    // Cập nhật giao diện Header
                    const coverUrl = song.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80';

                    const imgEl = document.getElementById('detail-cover');
                    imgEl.crossOrigin = "Anonymous";

                    // Lấy màu nền khi ảnh đã tải xong
                    imgEl.addEventListener('load', function () {
                        try {
                            const colorThief = new ColorThief();
                            const color = colorThief.getColor(imgEl);
                            if (color) {
                                const songHeader = document.querySelector('.song-header');
                                // Đổi nền gradient với màu của ảnh (có độ trong suốt 0.4 để màu tối hơn)
                                songHeader.style.background = `linear-gradient(to bottom, rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.4), var(--bg-app))`;
                            }
                        } catch (e) {
                            console.warn('Không thể lấy màu nền từ ảnh do lỗi CORS hoặc thư viện.', e);
                        }
                    });

                    imgEl.src = coverUrl;

                    document.getElementById('detail-title').textContent = song.title;

                    const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
                    const artistAvatar = (song.artist && song.artist.avatar) ? song.artist.avatar : `https://ui-avatars.com/api/?name=${encodeURIComponent(artistName)}&background=random`;

                    const artistNameEl = document.getElementById('detail-artist-name');
                    artistNameEl.textContent = artistName;
                    if (song.artist) {
                        artistNameEl.href = `/profile/${song.artist.id}/`;
                    }
                    
                    document.getElementById('detail-artist-img').src = artistAvatar;
                    
                    const releaseYear = song.released_at ? new Date(song.released_at).getFullYear() : (song.created_at ? new Date(song.created_at).getFullYear() : '2023');
                    document.getElementById('detail-year').textContent = releaseYear;
                    document.getElementById('detail-duration').textContent = formatDuration(song.duration);
                    document.getElementById('detail-plays').textContent = `${(song.play_count || 0).toLocaleString('vi-VN')} lượt nghe`;
                    document.getElementById('detail-likes').innerHTML = `<i class="bi bi-heart-fill" style="font-size:0.75rem;"></i> ${(song.like_count || 0).toLocaleString('vi-VN')}`;

                    // Cập nhật Lyrics
                    if (song.lyrics) {
                        document.getElementById('detail-lyrics').textContent = song.lyrics;
                    } else {
                        document.getElementById('detail-lyrics').textContent = "Bài hát này chưa có lời.";
                    }

                        // Cập nhật Artist Section
                    document.getElementById('detail-artist-avatar').src = artistAvatar;
                    document.getElementById('detail-artist-name-2').textContent = artistName;
                    
                    const monthlyListeners = (song.artist && song.artist.monthly_listeners !== undefined) 
                        ? song.artist.monthly_listeners 
                        : 0;
                    document.getElementById('detail-artist-followers').textContent = `${monthlyListeners.toLocaleString('vi-VN')} người nghe hàng tháng`;
                    
                    const artistLink = document.getElementById('detail-artist-link');
                    if (artistLink && song.artist) {
                        artistLink.href = `/profile/${song.artist.id}/`;
                    }

                    // Xử lý Tải xuống
                    const downloadBtn = document.getElementById('detail-download-btn');
                    if (downloadBtn && song.audio_file) {
                        downloadBtn.onclick = async function(e) {
                            e.preventDefault();
                            try {
                                // Hiển thị trạng thái đang tải (tùy chọn)
                                downloadBtn.classList.replace('bi-arrow-down-circle', 'bi-hourglass-split');
                                
                                const response = await fetch(song.audio_file);
                                const blob = await response.blob();
                                const blobUrl = window.URL.createObjectURL(blob);
                                
                                const a = document.createElement('a');
                                a.href = blobUrl;
                                a.download = `${song.title} - ${artistName}.mp3`.replace(/[\\/:*?"<>|]/g, ''); // Clean filename
                                document.body.appendChild(a);
                                a.click();
                                
                                window.URL.revokeObjectURL(blobUrl);
                                document.body.removeChild(a);
                            } catch (err) {
                                console.error('Lỗi tải xuống:', err);
                                // Fallback mở file trong tab mới
                                window.open(song.audio_file, '_blank');
                            } finally {
                                // Khôi phục icon
                                downloadBtn.classList.replace('bi-hourglass-split', 'bi-arrow-down-circle');
                            }
                        };
                    } else if (downloadBtn) {
                        downloadBtn.style.display = 'none'; // Ẩn nếu không có file
                    }

                    // Xử lý Báo cáo
                    const submitReportBtn = document.getElementById('submitReportBtn');
                    if (submitReportBtn) {
                        submitReportBtn.onclick = async function(e) {
                            e.preventDefault();
                            if (!window.CURRENT_USER_ID) {
                                if (window.showToast) window.showToast("Bạn cần đăng nhập để báo cáo bài hát.", 'warning');
                                return;
                            }
                            
                            const reasonEl = document.getElementById('reportReason');
                            const descriptionEl = document.getElementById('reportDescription');
                            if (!reasonEl.value) {
                                if (window.showToast) window.showToast("Vui lòng chọn lý do báo cáo.", 'warning');
                                return;
                            }

                            const originalText = submitReportBtn.innerHTML;
                            submitReportBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
                            submitReportBtn.disabled = true;

                            try {
                                const res = await fetch('/api/v1/music/reports/', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        'X-CSRFToken': getCookie('csrftoken')
                                    },
                                    body: JSON.stringify({
                                        target_type: 'song',
                                        target_id: song.id,
                                        reason: reasonEl.value,
                                        description: descriptionEl ? descriptionEl.value : ''
                                    })
                                });
                                const data = await res.json();
                                if (res.ok && data.success) {
                                    if (window.showToast) window.showToast("Cảm ơn bạn. Báo cáo của bạn đã được ghi nhận.", 'success');
                                    const modalEl = document.getElementById('reportSongModal');
                                    const modalInstance = bootstrap.Modal.getInstance(modalEl);
                                    if (modalInstance) {
                                        modalInstance.hide();
                                    } else {
                                        // Fallback
                                        const closeBtn = modalEl.querySelector('.btn-close');
                                        if (closeBtn) closeBtn.click();
                                    }
                                    reasonEl.value = ''; // Reset form
                                    const reasonTextEl = document.getElementById('reportReasonText');
                                    if (reasonTextEl) reasonTextEl.innerText = 'Chọn lý do...';
                                    if (descriptionEl) descriptionEl.value = '';
                                } else {
                                    if (window.showToast) window.showToast("Lỗi khi gửi báo cáo: " + (data.error?.message || "Vui lòng thử lại sau."), 'error');
                                }
                            } catch (err) {
                                console.error('Lỗi báo cáo:', err);
                                if (window.showToast) window.showToast("Đã xảy ra lỗi khi gửi báo cáo.", 'error');
                            } finally {
                                submitReportBtn.innerHTML = originalText;
                                submitReportBtn.disabled = false;
                            }
                        };
                    }

                    // Cập nhật nút Like
                    const likeBtn = document.getElementById('detail-like-btn');
                    if (likeBtn) {
                        if (song.is_liked) {
                            likeBtn.classList.remove('bi-heart');
                            likeBtn.classList.add('bi-heart-fill', 'text-accent');
                        }
                        
                        likeBtn.addEventListener('click', async function () {
                            const isLiked = this.classList.contains('bi-heart-fill');
                            if (isLiked) {
                                this.classList.remove('bi-heart-fill', 'text-accent');
                                this.classList.add('bi-heart');
                            } else {
                                this.classList.remove('bi-heart');
                                this.classList.add('bi-heart-fill', 'text-accent');
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
                                    // Revert
                                    if (isLiked) {
                                        this.classList.remove('bi-heart');
                                        this.classList.add('bi-heart-fill', 'text-accent');
                                    } else {
                                        this.classList.remove('bi-heart-fill', 'text-accent');
                                        this.classList.add('bi-heart');
                                    }
                                } else {
                                    // Cập nhật số lượt thích UI
                                    const currentLikes = parseInt(document.getElementById('detail-likes').innerText.replace(/\D/g, '')) || 0;
                                    const newLikes = isLiked ? currentLikes - 1 : currentLikes + 1;
                                    document.getElementById('detail-likes').innerHTML = `<i class="bi bi-heart-fill" style="font-size:0.75rem;"></i> ${newLikes.toLocaleString('vi-VN')}`;
                                    
                                    // Dispatch event to sync with player bar
                                    document.dispatchEvent(new CustomEvent('songLikeToggled', { 
                                        detail: { songId: songId, isLiked: !isLiked, likeCount: newLikes } 
                                    }));
                                }
                            } catch (err) {
                                console.error(err);
                                // Revert
                                if (isLiked) {
                                    this.classList.remove('bi-heart');
                                    this.classList.add('bi-heart-fill', 'text-accent');
                                } else {
                                    this.classList.remove('bi-heart-fill', 'text-accent');
                                    this.classList.add('bi-heart');
                                }
                            }
                        });
                    }
                    
                    // Xử lý nút Thêm vào Playlist (Dropdown)
                    const btnAddToPlaylist = document.getElementById('btn-add-to-playlist');
                    const playlistDropdown = document.getElementById('playlist-dropdown-menu');
                    
                    if (btnAddToPlaylist && playlistDropdown) {
                        btnAddToPlaylist.addEventListener('click', async function(e) {
                            e.stopPropagation();
                            
                            const isShowing = playlistDropdown.style.display === 'block';
                            if (isShowing) {
                                playlistDropdown.style.display = 'none';
                                return;
                            }
                            
                            playlistDropdown.style.display = 'block';
                            playlistDropdown.innerHTML = '<li class="text-center py-3 text-secondary small"><div class="spinner-border spinner-border-sm" role="status"></div></li>';
                            
                            try {
                                const res = await fetch('/api/v1/playlists/');
                                const data = await res.json();
                                
                                let html = '';
                                // Nút Thêm vào danh sách phát
                                html += `
                                    <li>
                                        <a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white fw-bold hover-bg-secondary" href="#" id="btn-add-to-queue-dropdown">
                                            <i class="bi bi-music-note-list text-accent"></i> Thêm vào danh sách phát
                                        </a>
                                    </li>
                                `;
                                // Nút Tạo playlist mới và ô tìm kiếm
                                html += `
                                    <li>
                                        <a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white fw-bold hover-bg-secondary" href="#" id="btn-create-and-add">
                                            <i class="bi bi-plus-lg text-accent"></i> Tạo playlist mới
                                        </a>
                                    </li>
                                    <li><hr class="dropdown-divider border-secondary opacity-25 my-1"></li>
                                    <li class="px-2 pb-2" onclick="event.stopPropagation()">
                                        <div class="playlist-search-container position-relative" style="background: rgba(255,255,255,0.1); border-radius: 4px; padding: 6px 10px; display: flex; align-items: center;">
                                            <i class="bi bi-search text-secondary" style="font-size: 0.85rem;"></i>
                                            <input type="text" id="playlist-search-input" placeholder="Tìm kiếm playlist..." class="text-white" style="background: none; border: none; outline: none; width: 100%; margin-left: 8px; font-size: 0.9rem;" onclick="event.stopPropagation()">
                                        </div>
                                    </li>
                                `;
                                
                                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                                    data.data.items.forEach(pl => {
                                        html += `
                                            <li class="playlist-dropdown-item">
                                                <a class="dropdown-item d-flex align-items-center gap-2 py-2 px-3 text-decoration-none text-white hover-bg-secondary add-to-existing-pl" href="#" data-playlist-id="${pl.id}">
                                                    <i class="bi bi-music-note-list text-secondary"></i>
                                                    <span class="text-truncate playlist-name-text">${pl.title}</span>
                                                </a>
                                            </li>
                                        `;
                                    });
                                } else {
                                    html += `
                                        <li class="text-center py-3 text-secondary small px-3">
                                            Bạn chưa có playlist nào.
                                        </li>
                                    `;
                                }
                                
                                playlistDropdown.innerHTML = html;
                                
                                // Xử lý tìm kiếm playlist
                                const searchInput = document.getElementById('playlist-search-input');
                                if (searchInput) {
                                    searchInput.addEventListener('input', function(e) {
                                        const searchTerm = e.target.value.toLowerCase().trim();
                                        const items = playlistDropdown.querySelectorAll('.playlist-dropdown-item');
                                        items.forEach(item => {
                                            const text = item.querySelector('.playlist-name-text').textContent.toLowerCase();
                                            if (text.includes(searchTerm)) {
                                                item.style.display = 'block';
                                            } else {
                                                item.style.display = 'none';
                                            }
                                        });
                                    });
                                }
                                
                                // Event: Thêm vào danh sách phát (Queue)
                                const btnAddToQueueDropdown = document.getElementById('btn-add-to-queue-dropdown');
                                if (btnAddToQueueDropdown) {
                                    btnAddToQueueDropdown.addEventListener('click', function(e) {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        playlistDropdown.style.display = 'none';
                                        
                                        const cover = song.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                                        if (window.addToQueue) {
                                            window.addToQueue(song.id, song.title, artistName, cover);
                                        } else {
                                            if (window.showToast) window.showToast('Không thể thêm vào danh sách phát', 'error');
                                        }
                                    });
                                }

                                // Event: Tạo mới và thêm
                                const btnCreateAndAdd = document.getElementById('btn-create-and-add');
                                if (btnCreateAndAdd) {
                                    btnCreateAndAdd.addEventListener('click', function(e) {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        playlistDropdown.style.display = 'none';
                                        window.pendingSongToAddToNewPlaylist = songId; // Lưu id bài hát
                                        if (window.openCreatePlaylistModal) {
                                            window.openCreatePlaylistModal();
                                        }
                                    });
                                }
                                
                                // Event: Thêm vào playlist có sẵn
                                document.querySelectorAll('.add-to-existing-pl').forEach(item => {
                                    item.addEventListener('click', async function(e) {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        const plId = this.getAttribute('data-playlist-id');
                                        playlistDropdown.style.display = 'none';
                                        
                                        try {
                                            const addRes = await fetch(`/api/v1/playlists/${plId}/songs/`, {
                                                method: 'POST',
                                                headers: {
                                                    'Content-Type': 'application/json',
                                                    'X-CSRFToken': getCookie('csrftoken')
                                                },
                                                body: JSON.stringify({ song_id: songId })
                                            });
                                            const addData = await addRes.json();
                                            
                                            if (addRes.ok && addData.success) {
                                                if (window.showToast) showToast('Đã thêm bài hát vào playlist', 'success');
                                            } else {
                                                if (window.showToast) showToast(addData.error?.message || 'Có lỗi xảy ra', 'error');
                                            }
                                        } catch (err) {
                                            console.error(err);
                                            if (window.showToast) showToast('Lỗi kết nối', 'error');
                                        }
                                    });
                                });
                                
                            } catch(err) {
                                console.error('Error fetching playlists', err);
                                playlistDropdown.innerHTML = '<li class="text-center py-2 text-danger small">Lỗi tải dữ liệu</li>';
                            }
                        });
                        
                        // Đóng dropdown khi click ra ngoài
                        document.addEventListener('click', function(e) {
                            if (playlistDropdown && !playlistDropdown.contains(e.target) && e.target !== btnAddToPlaylist) {
                                playlistDropdown.style.display = 'none';
                            }
                        });
                    }

                    // Bind play button
                    const playBtn = document.querySelector('.btn-play-large');
                    if (playBtn) {
                        playBtn.onclick = function (e) {
                            if (window.playSong) {
                                window.playSong(song.id, e);
                            }
                        };
                    }
                    if (window.syncPlayerUI) {
                        window.syncPlayerUI();
                    }

                } else {
                    document.getElementById('detail-title').textContent = "Không tìm thấy bài hát";
                }
            })
            .catch(error => {
                console.error('Lỗi khi lấy thông tin bài hát:', error);
                document.getElementById('detail-title').textContent = "Lỗi tải dữ liệu";
            });
        
        // Fetch Similar Songs Overview
        fetch(`/api/v1/recommendations/similar/${songId}/?limit=5`)
            .then(response => response.json())
            .then(data => {
                const overviewContainer = document.getElementById('overviewRecommendations');
                if (!overviewContainer) return;
                
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    overviewContainer.innerHTML = '';
                    
                    data.data.items.forEach((item, index) => {
                        const song = item.song || item;
                        const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
                        const coverImg = song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&w=300&h=300&fit=crop';
                        
                        const html = `
                        <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                            <div class="card-image-wrapper">
                                <img src="${coverImg}" alt="${song.title}">
                            </div>
                            <div class="card-title">${song.title}</div>
                            <div class="card-subtitle">${artistName}</div>
                            <a href="/song/?id=${song.id}" class="stretched-link"></a>
                        </div>
                        `;
                        overviewContainer.insertAdjacentHTML('beforeend', html);
                    });
                } else {
                    overviewContainer.innerHTML = '<div class="text-secondary small w-100 text-center py-3" style="grid-column: 1/-1;">Chưa có bài hát tương tự.</div>';
                    const btnViewAll = document.getElementById('btnViewAllRecommendations');
                    if (btnViewAll) btnViewAll.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Lỗi lấy bài hát tương tự:', error);
                const overviewContainer = document.getElementById('overviewRecommendations');
                if (overviewContainer) overviewContainer.innerHTML = '<div class="text-secondary small w-100 text-center py-3" style="grid-column: 1/-1;">Lỗi tải bài hát tương tự.</div>';
            });
    } else {
        document.getElementById('detail-title').textContent = "Không tìm thấy bài hát (Thiếu ID)";
    }
});

window.showAllRecommendations = function() {
    const btn = document.getElementById('btnViewAllRecommendations');
    const overviewContainer = document.getElementById('overviewRecommendations');
    const allContainer = document.getElementById('allRecommendations');
    
    if (btn) btn.style.display = 'none';
    if (overviewContainer) overviewContainer.style.display = 'none';
    if (allContainer) {
        allContainer.style.display = 'grid';
        allContainer.innerHTML = `
            <div class="d-flex justify-content-center align-items-center w-100 py-4" style="grid-column: 1/-1;">
                <div class="spinner-border spinner-border-sm text-secondary" role="status"></div>
            </div>`;
            
        const urlParams = new URLSearchParams(window.location.search);
        const songId = urlParams.get('id');
        if (!songId) return;
        
        fetch(`/api/v1/recommendations/similar/${songId}/?limit=100`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    allContainer.innerHTML = '';
                    data.data.items.forEach((item, index) => {
                        const song = item.song || item;
                        const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
                        const coverImg = song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&w=300&h=300&fit=crop';
                        
                        const html = `
                        <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                            <div class="card-image-wrapper">
                                <img src="${coverImg}" alt="${song.title}">
                            </div>
                            <div class="card-title">${song.title}</div>
                            <div class="card-subtitle">${artistName}</div>
                            <a href="/song/?id=${song.id}" class="stretched-link"></a>
                        </div>
                        `;
                        allContainer.insertAdjacentHTML('beforeend', html);
                    });
                } else {
                    allContainer.innerHTML = '<div class="text-secondary small w-100 text-center py-3" style="grid-column: 1/-1;">Không có thêm bài hát tương tự.</div>';
                }
            })
            .catch(error => {
                console.error('Lỗi lấy bài hát tương tự:', error);
                allContainer.innerHTML = '<div class="text-secondary small w-100 text-center py-3" style="grid-column: 1/-1;">Lỗi tải bài hát tương tự.</div>';
            });
    }
};
// ──────────────────────────────────────────────────────────────
// BÌNH LUẬN (COMMENTS)
// ──────────────────────────────────────────────────────────────
var commentUrlParams = new URLSearchParams(window.location.search);
var commentSongId = commentUrlParams.get('id');

// Global user id already provided in window object usually, if not fallback to template variable if needed.
// Wait, we can't use Django template variables directly in external JS.
// I will access it via window.CURRENT_USER_ID if it exists, otherwise get it from DOM or assume no user.
var currentUserId = window.CURRENT_USER_ID || '';

var commentsListContainer = document.getElementById('commentsListContainer');
var commentCountDisplay = document.getElementById('commentCountDisplay');
var commentInput = document.getElementById('commentInput');
var commentSubmitBtn = document.getElementById('commentSubmitBtn');
var currentReplyParentId = null; // Nếu đang trả lời bình luận nào đó

// Hàm render 1 comment HTML (đệ quy nếu có replies)
function renderCommentHTML(comment, isReply = false) {
    const userAvatar = comment.user.avatar || `https://ui-avatars.com/api/?name=${comment.user.username}&background=random`;
    const userName = comment.user.display_name || comment.user.username;
    const timeAgo = new Date(comment.created_at).toLocaleString('vi-VN');
    const likeColor = comment.is_liked_by_viewer ? 'var(--accent-color)' : '';
    const heartIcon = comment.is_liked_by_viewer ? 'bi-heart-fill' : 'bi-heart';

    let dropdownMenuHtml = `<li><a class="dropdown-item py-2 text-danger" href="#"><i class="bi bi-flag me-2"></i> Báo cáo</a></li>`;
    if (currentUserId && comment.user.id.toString() === currentUserId.toString()) {
        dropdownMenuHtml = `<li><a class="dropdown-item py-2 text-danger" href="javascript:void(0)" onclick="deleteComment('${comment.id}')"><i class="bi bi-trash me-2"></i> Xóa</a></li>` + dropdownMenuHtml;
    }

    let html = `
        <div class="d-flex gap-3 ${isReply ? 'mt-3' : ''}" id="comment-${comment.id}">
            <img src="${userAvatar}" class="rounded-circle object-fit-cover" style="width: ${isReply ? '30' : '40'}px; height: ${isReply ? '30' : '40'}px;">
            <div class="flex-grow-1">
                <div class="d-flex align-items-baseline justify-content-between mb-1">
                    <div class="d-flex align-items-baseline gap-2">
                        <span class="fw-bold" style="font-size: ${isReply ? '0.9' : '1'}rem;">${userName}</span>
                        <span class="text-secondary" style="font-size: 0.75rem;">${timeAgo}</span>
                    </div>
                    <div class="dropdown">
                        <i class="bi bi-three-dots text-secondary" style="cursor: pointer; padding: 0 8px;" data-bs-toggle="dropdown" aria-expanded="false" onmouseover="this.classList.replace('text-secondary', 'text-white')" onmouseout="this.classList.replace('text-white', 'text-secondary')"></i>
                        <ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow" style="background-color: var(--bg-card); min-width: 120px; font-size: 0.85rem;">
                            ${dropdownMenuHtml}
                        </ul>
                    </div>
                </div>
                <div class="text-light" style="font-size: ${isReply ? '0.85' : '0.9'}rem;">
                    ${comment.content}
                </div>
                <div class="d-flex align-items-center gap-3 mt-2 text-secondary" style="font-size: 0.85rem;">
                    <div class="d-flex align-items-center gap-1" style="cursor: pointer;" onclick="toggleCommentLike('${comment.id}')" onmouseover="this.classList.replace('text-secondary', 'text-white')" onmouseout="this.classList.replace('text-white', 'text-secondary')">
                        <i class="bi ${heartIcon}" id="like-icon-${comment.id}" style="color: ${likeColor};"></i> 
                        <span id="like-count-${comment.id}" style="color: ${likeColor};">${comment.like_count}</span>
                    </div>
                    <div style="cursor: pointer;" onclick="prepareReply('${comment.parent_id || comment.id}', '${userName}')" onmouseover="this.classList.replace('text-secondary', 'text-white')" onmouseout="this.classList.replace('text-white', 'text-secondary')">
                        Phản hồi
                    </div>
                </div>
                <!-- Replies Container -->
                <div id="replies-container-${comment.id}">
    `;
    
    if (comment.replies && comment.replies.length > 0) {
        comment.replies.forEach(reply => {
            html += renderCommentHTML(reply, true);
        });
    }

    html += `
                </div>
            </div>
        </div>
    `;
    return html;
}

// Tải danh sách bình luận
async function fetchComments() {
    if (!commentsListContainer || !commentSongId) return;
    try {
        const res = await fetch(`/api/v1/music/songs/${commentSongId}/comments/`);
        const data = await res.json();
        if (data.success) {
            if (commentCountDisplay) {
                const total = data.data.total !== undefined ? data.data.total : (data.data.items ? data.data.items.length : 0);
                commentCountDisplay.textContent = `(${total})`;
            }
            const comments = data.data.items;
            if (comments.length === 0) {
                commentsListContainer.innerHTML = '<div class="text-center text-secondary py-3">Chưa có bình luận nào. Hãy là người đầu tiên!</div>';
            } else {
                let html = '';
                comments.forEach(c => {
                    html += renderCommentHTML(c);
                });
                commentsListContainer.innerHTML = html;
            }
        }
    } catch (err) {
        console.error("Error fetching comments", err);
        commentsListContainer.innerHTML = '<div class="text-center text-danger py-3">Lỗi tải bình luận</div>';
    }
}

// Gửi bình luận
if (commentSubmitBtn && commentInput) {
    commentSubmitBtn.addEventListener('click', async () => {
        const content = commentInput.value.trim();
        if (!content || !commentSongId) return;
        
        // Disable input during request
        commentInput.disabled = true;
        commentSubmitBtn.disabled = true;
        
        try {
            const bodyData = { content: content };
            if (currentReplyParentId) {
                bodyData.parent_id = currentReplyParentId;
            }

            const res = await fetch(`/api/v1/music/songs/${commentSongId}/comments/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // make sure getCookie is globally available from main.js
                },
                body: JSON.stringify(bodyData)
            });
            
            const data = await res.json();
            if (res.ok && data.success) {
                commentInput.value = '';
                currentReplyParentId = null;
                commentInput.placeholder = 'Viết bình luận của bạn...';
                fetchComments(); // Tải lại bình luận
                if (window.showToast) showToast('Đã gửi bình luận', 'success');
            } else {
                if (res.status === 401 || res.status === 403) {
                    if (window.showToast) showToast('Bạn cần đăng nhập để bình luận', 'warning');
                } else {
                    if (window.showToast) showToast(data.error?.message || 'Lỗi gửi bình luận', 'error');
                }
            }
        } catch(err) {
            console.error(err);
            if (window.showToast) showToast('Lỗi mạng', 'error');
        } finally {
            commentInput.disabled = false;
            commentSubmitBtn.disabled = false;
            commentInput.focus();
        }
    });

    // Enter để gửi
    commentInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            commentSubmitBtn.click();
        }
    });
}

// Like bình luận
window.toggleCommentLike = async function(commentId) {
    try {
        const res = await fetch(`/api/v1/music/comments/${commentId}/like/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        const data = await res.json();
        if (res.ok && data.success) {
            const iconEl = document.getElementById(`like-icon-${commentId}`);
            const countEl = document.getElementById(`like-count-${commentId}`);
            
            if (data.data.is_liked) {
                iconEl.classList.replace('bi-heart', 'bi-heart-fill');
                iconEl.style.color = 'var(--accent-color)';
                countEl.style.color = 'var(--accent-color)';
            } else {
                iconEl.classList.replace('bi-heart-fill', 'bi-heart');
                iconEl.style.color = '';
                countEl.style.color = '';
            }
            countEl.textContent = data.data.like_count;
        } else {
            if (res.status === 401 || res.status === 403) {
                if (window.showToast) showToast('Bạn cần đăng nhập để thích', 'warning');
            }
        }
    } catch(err) {
        console.error('Error liking comment', err);
    }
};

// Chuẩn bị phản hồi
window.prepareReply = function(parentId, userName) {
    currentReplyParentId = parentId;
    if (commentInput) {
        commentInput.placeholder = `Trả lời ${userName}...`;
        commentInput.focus();
    }
};

// Xóa bình luận
window.deleteComment = async function(commentId) {
    if (!confirm('Bạn có chắc chắn muốn xóa bình luận này không?')) return;
    
    try {
        const res = await fetch(`/api/v1/music/comments/${commentId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (res.ok) {
            if (window.showToast) showToast('Đã xóa bình luận', 'success');
            fetchComments(); // Reload bình luận
        } else {
            const data = await res.json();
            if (window.showToast) showToast(data.error?.message || 'Lỗi khi xóa bình luận', 'error');
        }
    } catch(err) {
        console.error('Error deleting comment:', err);
        if (window.showToast) showToast('Lỗi kết nối khi xóa bình luận', 'error');
    }
};

// Lắng nghe sự kiện like từ player.js để đồng bộ giao diện
document.addEventListener('songLikeToggled', function(e) {
    const params = new URLSearchParams(window.location.search);
    const currentPageSongId = params.get('id');
    if (currentPageSongId && currentPageSongId == e.detail.songId) {
        const likeBtn = document.getElementById('detail-like-btn');
        if (likeBtn) {
            const isCurrentlyLiked = likeBtn.classList.contains('bi-heart-fill');
            if (isCurrentlyLiked !== e.detail.isLiked) {
                if (e.detail.isLiked) {
                    likeBtn.classList.remove('bi-heart');
                    likeBtn.classList.add('bi-heart-fill', 'text-accent');
                } else {
                    likeBtn.classList.remove('bi-heart-fill', 'text-accent');
                    likeBtn.classList.add('bi-heart');
                }
                
                if (e.detail.likeCount !== undefined) {
                    document.getElementById('detail-likes').innerHTML = `<i class="bi bi-heart-fill" style="font-size:0.75rem;"></i> ${e.detail.likeCount.toLocaleString('vi-VN')}`;
                }
            }
        }
    }
});

// Fetch comments khi vào trang
if (commentSongId) {
    fetchComments();
}
