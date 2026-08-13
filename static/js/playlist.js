document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('myPlaylistsContainer');
    if (!container) return;

    if (typeof window.CURRENT_USER_AUTHENTICATED !== 'undefined' && !window.CURRENT_USER_AUTHENTICATED) {
        container.innerHTML = '<div class="text-secondary w-100 text-center py-4">Vui lòng đăng nhập để xem playlist của bạn.</div>';
        return;
    }

    try {
        const res = await fetch('/api/v1/playlists/');
        if (!res.ok) throw new Error('Network error');
        
        const data = await res.json();
        if (!data.success) throw new Error(data.error?.message || 'Có lỗi xảy ra');
        
        const playlists = data.data.items || [];
        
        if (playlists.length === 0) {
            container.innerHTML = `
                <div class="text-secondary w-100 text-center py-4 d-flex flex-column align-items-center">
                    <i class="bi bi-music-note-list mb-2" style="font-size: 2rem;"></i>
                    <p>Bạn chưa có playlist nào.</p>
                    <button type="button" class="btn btn-outline-light rounded-pill px-4 mt-2" onclick="openCreatePlaylistModal(event)">
                        Tạo Playlist Ngay
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        playlists.forEach(pl => {
            const imgUrl = pl.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
            html += `
                <div class="playlist-card position-relative">
                    <div class="card-image-wrapper">
                        <img src="${imgUrl}" alt="${pl.title}">
                        <div class="card-play-btn" onclick="event.preventDefault(); event.stopPropagation(); if(window.playPlaylist) window.playPlaylist('${pl.id}', event, '${pl.title.replace(/'/g, "\\'")}')"><i class="bi bi-play-fill"></i></div>
                    </div>
                    <div class="card-title text-truncate" title="${pl.title}">${pl.title}</div>
                    <div class="card-subtitle text-truncate">Bởi ${pl.owner.display_name}</div>
                    <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error(error);
        container.innerHTML = '<div class="text-danger w-100 text-center py-4">Không thể tải danh sách playlist.</div>';
    }

    // --- LOAD TOP PLAYLISTS ---
    const topContainer = document.getElementById('topPlaylistsContainer');
    if (topContainer) {
        try {
            const topRes = await fetch('/api/v1/playlists/?scope=public&limit=10');
            if (topRes.ok) {
                const topData = await topRes.json();
                if (topData.success && topData.data.items && topData.data.items.length > 0) {
                    topContainer.innerHTML = topData.data.items.map(pl => {
                        const imgUrl = pl.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                        return `
                            <div class="playlist-card position-relative">
                                <div class="card-image-wrapper">
                                    <img src="${imgUrl}" alt="${pl.title}" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';">
                                    <div class="card-play-btn" onclick="event.preventDefault(); event.stopPropagation(); if(window.playPlaylist) window.playPlaylist('${pl.id}', event, '${pl.title.replace(/'/g, "\\'")}')"><i class="bi bi-play-fill"></i></div>
                                </div>
                                <div class="card-title text-truncate" title="${pl.title}">${pl.title}</div>
                                <div class="card-subtitle text-truncate">Bởi ${pl.owner ? pl.owner.display_name : 'Nghệ sĩ'}</div>
                                <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
                            </div>
                        `;
                    }).join('');
                } else {
                    topContainer.innerHTML = '<div class="text-secondary w-100 py-4">Chưa có playlist nổi bật nào.</div>';
                }
            } else {
                topContainer.innerHTML = '<div class="text-danger w-100 py-4">Không thể tải danh sách playlist nổi bật.</div>';
            }
        } catch (e) {
            topContainer.innerHTML = '<div class="text-danger w-100 py-4">Không thể tải danh sách playlist nổi bật.</div>';
        }
    }

    // --- LOAD RECOMMENDED PLAYLISTS ---
    const recoContainer = document.getElementById('recommendedPlaylistsContainer');
    if (recoContainer) {
        try {
            const recoRes = await fetch('/api/v1/recommendations/playlists/?limit=10');
            if (recoRes.ok) {
                const recoData = await recoRes.json();
                if (recoData.success && recoData.data.items && recoData.data.items.length > 0) {
                    recoContainer.innerHTML = recoData.data.items.map(pl => {
                        const imgUrl = pl.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                        return `
                            <div class="playlist-card position-relative">
                                <div class="card-image-wrapper">
                                    <img src="${imgUrl}" alt="${pl.title}" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';">
                                    <div class="card-play-btn" onclick="event.preventDefault(); event.stopPropagation(); if(window.playPlaylist) window.playPlaylist('${pl.id}', event, '${pl.title.replace(/'/g, "\\'")}')"><i class="bi bi-play-fill"></i></div>
                                </div>
                                <div class="card-title text-truncate" title="${pl.title}">${pl.title}</div>
                                <div class="card-subtitle text-truncate">Bởi ${pl.owner ? pl.owner.display_name : 'Nghệ sĩ'}</div>
                                <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
                            </div>
                        `;
                    }).join('');
                } else {
                    recoContainer.innerHTML = '<div class="text-secondary w-100 py-4">Chưa có gợi ý playlist nào cho bạn.</div>';
                }
            } else {
                recoContainer.innerHTML = '<div class="text-danger w-100 py-4">Không thể tải danh sách gợi ý.</div>';
            }
        } catch (e) {
            recoContainer.innerHTML = '<div class="text-danger w-100 py-4">Không thể tải danh sách gợi ý.</div>';
        }
    }
});
