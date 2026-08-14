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

    // 3. Fetch data function
    async function fetchItems() {
        if (isFetching || !hasMore) return;
        
        isFetching = true;
        loadingSpinner.style.display = 'block';

        try {
            const response = await fetch(`/api/v1/recommendations/mood/${moodTypeId}/${type}/?page=${currentPage}&limit=${limit}`);
            const data = await response.json();

            if (data.success && data.data && data.data.items) {
                const items = data.data.items;
                
                if (items.length > 0) {
                    renderItems(items, type);
                    currentPage++;
                    
                    // If the number of items fetched is less than limit, it means we reached the end
                    if (items.length < limit) {
                        hasMore = false;
                        loadingSpinner.style.display = 'none';
                        endMessage.classList.remove('d-none');
                    }
                } else {
                    hasMore = false;
                    loadingSpinner.style.display = 'none';
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
            console.error("Lỗi khi tải dữ liệu:", error);
            if (currentPage === 1) {
                exploreGrid.innerHTML = '<div class="text-danger w-100 text-center py-5">Đã xảy ra lỗi khi tải dữ liệu.</div>';
            }
            hasMore = false;
            loadingSpinner.style.display = 'none';
        } finally {
            isFetching = false;
            if (hasMore) {
                loadingSpinner.style.display = 'block'; // Keep it visible for intersection observer
            }
        }
    }

    // 4. Render HTML using existing card component (from components/card.js or similar logic)
    function renderItems(items, type) {
        items.forEach(item => {
            // Replicate the card logic from mood.js
            let cardHtml = '';
            if (type === 'songs') {
                const coverUrl = item.cover_image_url || '/static/images/default_cover.jpg';
                const defaultAvatar = 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.artist?.display_name || 'A') + '&background=random';
                const artistAvatar = item.artist?.avatar_url || defaultAvatar;

                cardHtml = `
                    <div class="playlist-card" onclick="window.location.href='/song/${item.id}'">
                        <img src="${coverUrl}" alt="Song cover">
                        <h6 class="mt-3 mb-1 text-white text-truncate fw-bold">${item.title}</h6>
                        <p class="mb-0 text-truncate d-flex align-items-center gap-2" style="color: var(--text-secondary); font-size: 0.85rem;">
                            <img src="${artistAvatar}" alt="Artist" class="rounded-circle" style="width: 20px; height: 20px; object-fit: cover;">
                            ${item.artist?.display_name || 'Unknown Artist'}
                        </p>
                    </div>
                `;
            } else if (type === 'playlists') {
                const coverUrl = item.cover_image_url || '/static/images/default_playlist.png';
                const defaultAvatar = 'https://ui-avatars.com/api/?name=' + encodeURIComponent(item.owner?.display_name || 'U') + '&background=random';
                const ownerAvatar = item.owner?.avatar_url || defaultAvatar;

                cardHtml = `
                    <div class="playlist-card" onclick="window.location.href='/playlist/detail/?id=${item.id}'">
                        <img src="${coverUrl}" alt="Playlist cover" style="aspect-ratio: 1/1; object-fit: cover; border-radius: 12px; width: 100%;">
                        <h6 class="mt-3 mb-1 text-white text-truncate fw-bold">${item.name}</h6>
                        <p class="mb-0 text-truncate d-flex align-items-center gap-2" style="color: var(--text-secondary); font-size: 0.85rem;">
                            <img src="${ownerAvatar}" alt="Owner" class="rounded-circle" style="width: 20px; height: 20px; object-fit: cover;">
                            ${item.owner?.display_name || 'Unknown User'}
                        </p>
                    </div>
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
