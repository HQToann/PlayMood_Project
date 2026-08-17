document.addEventListener('DOMContentLoaded', () => {
    // 1. Get parameters from URL
    const params = new URLSearchParams(window.location.search);
    const moodTypeId = params.get('mood_id');
    const type = params.get('type'); // 'songs' or 'playlists'
    const moodNameParam = params.get('mood_name');
    
    const exploreTitle = document.getElementById('exploreTitle');
    const exploreGrid = document.getElementById('exploreGrid');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const endMessage = document.getElementById('endMessage');

    if (!moodTypeId || !type) {
        exploreTitle.textContent = "Không tìm thấy dữ liệu";
        loadingSpinner.style.display = 'none';
        return;
    }

    // Set dynamic title
    if (moodNameParam) {
        if (type === 'songs') {
            exploreTitle.textContent = `Nhạc Phù Hợp Với "${moodNameParam}"`;
        } else if (type === 'playlists') {
            exploreTitle.textContent = `Playlist Cho "${moodNameParam}"`;
        }
    }

    // 2. Pagination state
    let currentPage = 1;
    let limit = 20; // Fetch 20 items per page
    let isFetching = false;
    let hasMore = true;

    function showSkeletons(count) {
        let html = '';
        for (let i = 0; i < count; i++) {
            if (type === 'artists') {
                html += `
                <div class="skeleton-artist temp-skeleton">
                    <div class="skeleton sk-avatar"></div>
                    <div class="skeleton sk-name"></div>
                    <div class="skeleton sk-role"></div>
                </div>`;
            } else {
                html += `
                <div class="skeleton-card temp-skeleton">
                    <div class="skeleton sk-img"></div>
                    <div class="skeleton sk-title"></div>
                    <div class="skeleton sk-sub"></div>
                </div>`;
            }
        }
        exploreGrid.insertAdjacentHTML('beforeend', html);
    }

    function removeSkeletons() {
        const skeletons = exploreGrid.querySelectorAll('.temp-skeleton');
        skeletons.forEach(el => el.remove());
    }

    // 3. Fetch data function
    async function fetchItems() {
        if (isFetching || !hasMore) return;
        
        isFetching = true;
        showSkeletons(currentPage === 1 ? limit : 5);

        try {
            const response = await fetch(`/api/v1/recommendations/mood/${moodTypeId}/${type}/?page=${currentPage}&limit=${limit}`);
            const data = await response.json();
            
            removeSkeletons();

            if (data.success && data.data && data.data.items) {
                const items = data.data.items;
                
                if (items.length > 0) {
                    renderItems(items, type);
                    currentPage++;
                    
                    if (items.length < limit) {
                        hasMore = false;
                        endMessage.classList.remove('d-none');
                    }
                } else {
                    hasMore = false;
                    if (currentPage === 1) {
                        exploreGrid.innerHTML = '<div class="text-secondary w-100 text-center py-5">Không có gợi ý nào.</div>';
                    } else {
                        endMessage.classList.remove('d-none');
                    }
                }
            } else {
                throw new Error("Invalid data format");
            }
        } catch (error) {
            removeSkeletons();
            console.error("Error fetching data:", error);
            if (currentPage === 1) {
                exploreGrid.innerHTML = '<div class="text-danger w-100 text-center py-5">Đã xảy ra lỗi khi tải dữ liệu.</div>';
            }
            hasMore = false;
        } finally {
            isFetching = false;
        }
    }

    // 4. Render HTML using existing card component (from components/card.js or similar logic)
    function renderItems(items, type) {
        items.forEach(item => {
            // Replicate the card logic from mood.js
            let cardHtml = '';
            if (type === 'songs') {
                const coverUrl = item.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';
                const artist = item.artist ? item.artist.display_name : 'Nghệ sĩ';

                cardHtml = `
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

                cardHtml = `
                    <a href="/playlist/detail/?id=${item.id}" class="playlist-mood-card" style="width: 100%;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;display:block;text-decoration:none;color:#fff;transition:all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.08)';this.style.transform='translateY(-4px)'" onmouseout="this.style.background='rgba(255,255,255,0.04)';this.style.transform='translateY(0)'">
                        <div style="position:relative;width:100%;aspect-ratio:1;border-radius:8px;overflow:hidden;margin-bottom:0.75rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                            <img src="${coverUrl}" alt="${item.title}" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';">
                        </div>
                        <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;">${item.title || item.name}</div>
                        <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">bởi ${owner}${songCount}</div>
                    </a>
                `;
            }
            
            // Append to grid
            exploreGrid.insertAdjacentHTML('beforeend', cardHtml);
        });
    }

    // 5. Infinite Scroll Observer
    const observer = new IntersectionObserver((entries) => {
        const target = entries[0];
        if (target.isIntersecting && hasMore && !isFetching) {
            fetchItems();
        }
    }, {
        root: document.getElementById('mainContent'), // Adjust based on scroll container
        rootMargin: '100px', // Load a bit earlier before actually reaching it
        threshold: 0.1
    });

    observer.observe(loadingSpinner);

    // Initial fetch (if observer doesn't trigger immediately)
    fetchItems();
});
