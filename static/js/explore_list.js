document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const section = params.get('section');
    
    const exploreTitle = document.getElementById('exploreTitle');
    const exploreGrid = document.getElementById('exploreGrid');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const endMessage = document.getElementById('endMessage');

    const config = {
        'for_you': { title: 'Gợi Ý Cho Bạn', type: 'songs', api: '/api/v1/recommendations/for-you/' },
        'new_releases': { title: 'Mới Phát Hành', type: 'songs', api: '/api/v1/music/songs/?ordering=-created_at' },
        'trending': { title: 'Đang Thịnh Hành', type: 'songs', api: '/api/v1/music/songs/trending/' },
        'top_playlists': { title: 'Top Playlist Nổi Bật', type: 'playlists', api: '/api/v1/playlists/?scope=public' },
        'for_you_playlists': { title: 'Playlist Phù Hợp Dành Cho Bạn', type: 'playlists', api: '/api/v1/recommendations/playlists/' },
        'featured_artists': { title: 'Nghệ Sĩ Nổi Bật', type: 'artists', api: '/api/v1/recommendations/artists/' },
        'genre': { title: params.get('name') ? `Nhạc Thể Loại "${params.get('name')}"` : 'Nhạc Theo Thể Loại', type: 'songs', api: `/api/v1/music/songs/?genre=${params.get('slug')}` }
    };

    if (!section || !config[section]) {
        exploreTitle.textContent = "Không tìm thấy dữ liệu";
        loadingSpinner.style.display = 'none';
        return;
    }

    const currentConfig = config[section];
    exploreTitle.textContent = currentConfig.title;

    let currentPage = 1;
    let limit = 20;
    let isFetching = false;
    let hasMore = true;

    async function fetchItems() {
        if (isFetching || !hasMore) return;
        
        isFetching = true;
        loadingSpinner.style.display = 'block';

        try {
            const separator = currentConfig.api.includes('?') ? '&' : '?';
            const response = await fetch(`${currentConfig.api}${separator}page=${currentPage}&page_size=${limit}&limit=${limit}`);
            const data = await response.json();

            if (data.success && data.data && data.data.items) {
                const items = data.data.items;
                
                if (items.length > 0) {
                    renderItems(items, currentConfig.type);
                    currentPage++;
                    
                    if (items.length < limit) {
                        hasMore = false;
                        loadingSpinner.style.display = 'none';
                        endMessage.classList.remove('d-none');
                    }
                } else {
                    hasMore = false;
                    loadingSpinner.style.display = 'none';
                    if (currentPage === 1) {
                        exploreGrid.innerHTML = '<div class="text-secondary w-100 text-center py-5">Không có dữ liệu.</div>';
                    } else {
                        endMessage.classList.remove('d-none');
                    }
                }
            } else {
                throw new Error("Invalid data format");
            }
        } catch (error) {
            console.error("Lỗi khi tải dữ liệu:", error);
            if (currentPage === 1) {
                exploreGrid.innerHTML = '<div class="text-danger w-100 text-center py-5">Đã xảy ra lỗi khi tải dữ liệu.</div>';
            }
            hasMore = false;
            loadingSpinner.style.display = 'none';
        } finally {
            isFetching = false;
            if (hasMore) {
                loadingSpinner.style.display = 'block';
            }
        }
    }

    function renderItems(items, type) {
        let cardHtml = '';
        items.forEach(rawItem => {
            let item = rawItem;
            // Handle cases where item is wrapped in an object like {song: {...}}
            if (type === 'songs' && rawItem.song) {
                item = rawItem.song;
            }

            if (type === 'songs') {
                const coverUrl = item.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';
                const artist = item.artist ? item.artist.display_name : 'Nghệ sĩ';

                cardHtml += `
                    <div class="music-card" onclick="window.goToPage('/song/?id=${item.id}')" style="cursor:pointer; width: 100%; min-width: 0;">
                        <div class="music-card-img-wrap">
                            <img src="${coverUrl}" alt="${item.title}" class="music-card-img" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';">
                        </div>
                        <div class="music-card-title">${item.title}</div>
                        <div class="music-card-artist">${artist}</div>
                    </div>
                `;
            } else if (type === 'playlists') {
                const coverUrl = item.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';
                const owner = item.owner ? item.owner.display_name : '';
                const songCount = item.song_count ? ` • ${item.song_count} bài` : '';

                cardHtml += `
                    <a href="/playlist/detail/?id=${item.id}" class="playlist-mood-card" style="width: 100%;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;display:block;text-decoration:none;color:#fff;transition:all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.08)';this.style.transform='translateY(-4px)'" onmouseout="this.style.background='rgba(255,255,255,0.04)';this.style.transform='translateY(0)'">
                        <div style="position:relative;width:100%;aspect-ratio:1;border-radius:8px;overflow:hidden;margin-bottom:0.75rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                            <img src="${coverUrl}" alt="${item.title}" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';">
                        </div>
                        <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;">${item.title || item.name}</div>
                        <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">bởi ${owner}${songCount}</div>
                    </a>
                `;
            } else if (type === 'artists') {
                const coverUrl = item.avatar || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.display_name) + '&background=random';
                
                cardHtml += `
                    <a href="/profile/${item.id}/" class="artist-mood-card" style="width: 100%;display:flex;flex-direction:column;align-items:center;text-decoration:none;color:#fff;transition:all 0.3s;" onmouseover="this.style.transform='translateY(-4px)'" onmouseout="this.style.transform='translateY(0)'">
                        <img src="${coverUrl}" alt="${item.display_name}" style="width:100%;aspect-ratio:1;border-radius:50%;object-fit:cover;margin-bottom:1rem;box-shadow:0 8px 24px rgba(0,0,0,0.4);border:3px solid transparent;" loading="lazy">
                        <div style="font-weight:600;font-size:1rem;text-align:center;">${item.display_name}</div>
                        <div style="color:rgba(255,255,255,0.5);font-size:0.8rem;">Nghệ sĩ</div>
                    </a>
                `;
            }
        });
        
        exploreGrid.insertAdjacentHTML('beforeend', cardHtml);
    }

    const observer = new IntersectionObserver((entries) => {
        const target = entries[0];
        if (target.isIntersecting && hasMore && !isFetching) {
            fetchItems();
        }
    }, {
        root: document.getElementById('mainContent'),
        rootMargin: '100px',
        threshold: 0.1
    });

    observer.observe(loadingSpinner);
    fetchItems();
});
