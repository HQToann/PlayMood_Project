document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('topSearchInput');
    const searchResults = document.getElementById('searchResultsDropdown');
    const clearBtn = document.getElementById('clearSearchBtn');
    let searchTimeout;

    if (searchInput && searchResults) {
        // Hiển thị nút X nếu input đã có giá trị từ trước
        if (searchInput.value.trim().length > 0 && clearBtn) {
            clearBtn.style.display = 'block';
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                searchInput.value = '';
                clearBtn.style.display = 'none';
                searchResults.style.display = 'none';
                searchInput.focus();
            });
        }

        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const q = e.target.value.trim();
            
            if (clearBtn) {
                clearBtn.style.display = q.length > 0 ? 'block' : 'none';
            }
            
            if (q.length === 0) {
                searchResults.style.display = 'none';
                return;
            }

            searchTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/v1/search/?q=${encodeURIComponent(q)}&limit=5`);
                    const data = await res.json();
                    
                    if (data.success && data.data) {
                        const songs = data.data.songs || [];
                        const artists = data.data.artists || [];
                        const albums = data.data.albums || [];
                        const playlists = data.data.playlists || [];
                        const users = data.data.users || [];
                        
                        let combinedUsers = [...artists, ...users];
                        let uniqueUsers = [];
                        let seenUserIds = new Set();
                        combinedUsers.forEach(u => {
                            let uid = u.user ? u.user.id : u.id;
                            if (!seenUserIds.has(uid)) {
                                seenUserIds.add(uid);
                                uniqueUsers.push(u);
                            }
                        });
                        
                        // Gộp kết quả, ưu tiên 2 nghệ sĩ/người dùng đầu, 1 album, 1 playlist, sau đó đến bài hát
                        let items = [...uniqueUsers.slice(0,2), ...albums.slice(0,1), ...playlists.slice(0,1), ...songs].slice(0,5);
                        
                        let html = '';
                        
                        // Tạo danh sách gợi ý từ khoá
                        let suggestions = [];
                        songs.forEach(s => {
                            if (s.title && !suggestions.includes(s.title)) suggestions.push(s.title);
                        });
                        albums.forEach(a => {
                            if (a.title && !suggestions.includes(a.title)) suggestions.push(a.title);
                        });
                        playlists.forEach(p => {
                            if (p.title && !suggestions.includes(p.title)) suggestions.push(p.title);
                        });
                        uniqueUsers.forEach(a => {
                            let name = a.stage_name || a.display_name || a.username;
                            if (name && !suggestions.includes(name)) suggestions.push(name);
                        });
                        suggestions = suggestions.slice(0, 4);
                        
                        suggestions.forEach(text => {
                            // Highlight phần khớp với từ khoá
                            const escapedQ = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                            const regex = new RegExp(`(${escapedQ})`, 'gi');
                            const displayHTML = text.replace(regex, '<span class="fw-bold text-white">$1</span>');
                            
                            html += `
                                <div class="dropdown-item py-2 px-3 d-flex align-items-center gap-3" style="cursor: pointer; transition: background 0.2s;" onclick="window.goToPage('/search/?q=${encodeURIComponent(text)}')">
                                    <i class="bi bi-search fs-5 text-muted-custom"></i>
                                    <span style="font-size: 1rem; color: var(--text-secondary);">${displayHTML}</span>
                                </div>
                            `;
                        });
                        
                        if (items.length > 0) {
                            items.forEach(item => {
                                if (item.stage_name !== undefined || item.role !== undefined) {
                                    // Đây là nghệ sĩ hoặc người dùng
                                    const avatar = item.avatar || (item.user && item.user.avatar) || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80';
                                    const name = item.stage_name || item.display_name || item.username || 'Người dùng';
                                    const isArtist = (item.stage_name !== undefined) || (item.role === 'artist');
                                    const subtitle = isArtist ? 'Nghệ sĩ' : 'Người dùng';
                                    const profileLink = item.user ? `/profile/${item.user.id}` : `/profile/${item.id}`;
                                    const userId = item.user ? item.user.id : item.id;
                                    
                                    html += `
                                        <div class="dropdown-item py-2 px-3 d-flex align-items-center justify-content-between" style="cursor: pointer; transition: background 0.2s;" onclick="window.goToPage('${profileLink}')">
                                            <div class="d-flex align-items-center gap-3">
                                                <div style="position: relative; width: 48px; height: 48px;">
                                                    <img src="${avatar}" alt="Avatar" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">
                                                </div>
                                                <div>
                                                    <div style="font-size: 1rem; font-weight: 600; color: white;">${name}</div>
                                                    <div style="font-size: 0.85rem; color: var(--text-secondary);">${subtitle}</div>
                                                </div>
                                            </div>
                                            <button class="btn btn-outline-light rounded-pill btn-sm fw-bold px-3 py-1" onclick="event.stopPropagation(); window.toggleFollowUser('${userId}', this);" style="font-size: 0.8rem; border-color: rgba(255,255,255,0.3);">
                                                Theo dõi
                                            </button>
                                        </div>
                                    `;
                                } else if (item.song_count !== undefined) {
                                    // Đây là album
                                    const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                                    const artist = item.artist ? (item.artist.display_name || item.artist.username) : 'Nghệ sĩ';
                                    html += `
                                        <div class="dropdown-item py-2 px-3 d-flex align-items-center justify-content-between" style="cursor: pointer; transition: background 0.2s;" onclick="window.goToPage('/album/detail/?id=${item.id}')">
                                            <div class="d-flex align-items-center gap-3">
                                                <div style="position: relative; width: 48px; height: 48px;">
                                                    <img src="${img}" alt="cover" style="width: 100%; height: 100%; border-radius: 4px; object-fit: cover;">
                                                </div>
                                                <div>
                                                    <div style="font-size: 1rem; font-weight: 600; color: white;">${item.title}</div>
                                                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Album • ${artist}</div>
                                                </div>
                                            </div>
                                            <button class="btn btn-link text-white p-0 text-decoration-none" onclick="event.stopPropagation(); if(window.playAlbum) { window.playAlbum('${item.id}', '${item.title.replace(/'/g, "\\'")}'); }" style="font-size: 1.5rem;">
                                                <i class="bi bi-play-circle"></i>
                                            </button>
                                        </div>
                                    `;
                                } else if (item.is_public !== undefined) {
                                    // Đây là playlist
                                    const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                                    const owner = item.owner ? (item.owner.display_name || item.owner.username) : 'Người dùng';
                                    html += `
                                        <div class="dropdown-item py-2 px-3 d-flex align-items-center justify-content-between" style="cursor: pointer; transition: background 0.2s;" onclick="window.goToPage('/playlist/detail/?id=${item.id}')">
                                            <div class="d-flex align-items-center gap-3">
                                                <div style="position: relative; width: 48px; height: 48px;">
                                                    <img src="${img}" alt="cover" style="width: 100%; height: 100%; border-radius: 4px; object-fit: cover;">
                                                </div>
                                                <div>
                                                    <div style="font-size: 1rem; font-weight: 600; color: white;">${item.title}</div>
                                                    <div style="font-size: 0.85rem; color: var(--text-secondary);">Playlist • ${owner}</div>
                                                </div>
                                            </div>
                                        </div>
                                    `;
                                } else {
                                    // Đây là bài hát (Song)
                                    const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                                    const artist = item.artist ? item.artist.display_name : 'Nghệ sĩ';
                                    html += `
                                        <div class="dropdown-item py-2 px-3 d-flex align-items-center justify-content-between" style="cursor: pointer; transition: background 0.2s;" onclick="window.goToPage('/song/?id=${item.id}')">
                                            <div class="d-flex align-items-center gap-3">
                                                <div style="position: relative; width: 48px; height: 48px;">
                                                    <img src="${img}" alt="cover" style="width: 100%; height: 100%; border-radius: 4px; object-fit: cover;">
                                                </div>
                                                <div>
                                                    <div style="font-size: 1rem; font-weight: 600; color: white;">${item.title}</div>
                                                    <div style="font-size: 0.85rem; color: var(--text-secondary);">${artist}</div>
                                                </div>
                                            </div>
                                            <button class="btn btn-link text-muted-custom p-0 text-decoration-none" onclick="event.stopPropagation(); window.openAddToPlaylistModal('${item.id}');" style="font-size: 1.2rem;">
                                                <i class="bi bi-plus-circle"></i>
                                            </button>
                                        </div>
                                    `;
                                }
                            });
                            
                            // Nút Xem tất cả
                            html += `
                                <div class="p-3 pb-2">
                                    <a href="/search/?q=${encodeURIComponent(q)}" class="btn btn-outline-light rounded-pill px-3 py-1" style="font-size: 0.9rem; font-weight: 600; border-color: rgba(255,255,255,0.2);">
                                        Xem tất cả kết quả về "${q}"
                                    </a>
                                </div>
                            `;
                            searchResults.innerHTML = html;
                            searchResults.style.display = 'block';
                        } else {
                            searchResults.innerHTML = '<div class="p-3 text-center text-muted-custom" style="font-size: 0.85rem;">Không tìm thấy kết quả nào</div>';
                            searchResults.style.display = 'block';
                        }
                    } else {
                        searchResults.innerHTML = '<div class="p-3 text-center text-muted-custom" style="font-size: 0.85rem;">Không tìm thấy kết quả nào</div>';
                        searchResults.style.display = 'block';
                    }
                } catch (err) {
                    console.error('Lỗi tìm kiếm:', err);
                }
            }, 400); // 400ms debounce
        });

        // Lắng nghe sự kiện nhấn Enter
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const q = searchInput.value.trim();
                if (q.length > 0) {
                    window.goToPage(`/search/?q=${encodeURIComponent(q)}`);
                }
            }
        });

        // Ẩn khi click ra ngoài
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.style.display = 'none';
            }
        });
        
        // Hiện lại khi click vào ô search có nội dung
        searchInput.addEventListener('focus', () => {
            if (searchInput.value.trim().length > 0 && searchResults.innerHTML.trim() !== '') {
                searchResults.style.display = 'block';
            }
        });
    }
});
