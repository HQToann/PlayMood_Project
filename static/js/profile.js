function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

async function loadStats() {
    try {
        const targetUserId = window.TARGET_USER_ID;
        const res = await fetch(`/api/v1/social/users/${targetUserId}/follow-status/`);
        const data = await res.json();
        if (data.success) {
            const followersEl = document.getElementById('followersCount');
            const followingEl = document.getElementById('followingCount');
            if (followersEl) followersEl.innerText = formatNumber(data.data.followers_count || 0);
            if (followingEl) followingEl.innerText = formatNumber(data.data.following_count || 0);
        }
        
        const likesEl = document.getElementById('totalLikesCount');
        if (likesEl) {
            const statsRes = await fetch('/api/v1/artists/me/stats/');
            if (statsRes.ok) {
                const statsData = await statsRes.json();
                if (statsData.success) {
                    likesEl.innerText = formatNumber(statsData.data.total_likes || 0);
                }
            }
        }
    } catch (e) {
        console.error("Lỗi khi tải thống kê", e);
    }
}

class ProfilePaginator {
    constructor(config) {
        this.url = config.url;
        this.allContainerId = config.allContainerId;
        this.overviewContainerId = config.overviewContainerId;
        this.renderItem = config.renderItem;
        this.emptyMsg = config.emptyMsg;
        this.onItemsLoaded = config.onItemsLoaded;
        
        this.page = 1;
        this.limit = 20;
        this.hasMore = true;
        this.isLoading = false;
        this.items = [];
        
        this.init();
    }
    
    async init() {
        await this.loadMore();
        this.setupObserver();
    }
    
    async loadMore() {
        if (this.isLoading || !this.hasMore) return;
        this.isLoading = true;
        
        try {
            const sep = this.url.includes('?') ? '&' : '?';
            const res = await fetch(`${this.url}${sep}limit=${this.limit}&page=${this.page}`);
            const json = await res.json();
            let newItems = [];
            if (json.success && json.data) {
                newItems = Array.isArray(json.data) ? json.data : (json.data.items || []);
            }
            
            if (newItems.length < this.limit) {
                this.hasMore = false;
            }
            
            this.items = [...this.items, ...newItems];
            if (this.onItemsLoaded) this.onItemsLoaded(this.items);
            this.render();
            this.page++;
        } catch (e) {
            console.error('Error loading', this.url, e);
        } finally {
            this.isLoading = false;
        }
    }
    
    render() {
        const allContainer = document.getElementById(this.allContainerId);
        const overviewContainer = document.getElementById(this.overviewContainerId);
        
        if (this.items.length === 0) {
            const emptyHtml = `<div class="text-secondary py-3 text-center small w-100" style="grid-column: 1/-1;">${this.emptyMsg}</div>`;
            if (allContainer) allContainer.innerHTML = emptyHtml;
            if (overviewContainer) overviewContainer.innerHTML = emptyHtml;
            return;
        }
        
        const htmlAll = this.items.map(this.renderItem).join('');
        const htmlOverview = this.items.slice(0, 5).map(this.renderItem).join('');
        
        if (allContainer) {
            allContainer.innerHTML = htmlAll;
            if (this.hasMore) {
                allContainer.innerHTML += `<div id="sentinel-${this.allContainerId}" class="w-100 py-3 text-center" style="grid-column: 1/-1;"><div class="spinner-border spinner-border-sm text-secondary"></div></div>`;
            }
        }
        if (overviewContainer) overviewContainer.innerHTML = htmlOverview;
    }
    
    setupObserver() {
        const allContainer = document.getElementById(this.allContainerId);
        if (!allContainer) return;
        
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                this.loadMore();
            }
        }, { rootMargin: '100px' });
        
        const mo = new MutationObserver(() => {
            const sentinel = document.getElementById(`sentinel-${this.allContainerId}`);
            if (sentinel) observer.observe(sentinel);
        });
        mo.observe(allContainer, { childList: true });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadStats();
    
    const targetUserId = window.TARGET_USER_ID;
    
    new ProfilePaginator({
        url: `/api/v1/music/users/${targetUserId}/likes/`,
        allContainerId: 'allLikedSongsContainer',
        overviewContainerId: 'likedSongsContainer',
        emptyMsg: 'Chưa có bài hát yêu thích nào',
        renderItem: song => `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                </div>
                <div class="card-title">${song.title}</div>
                <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                <a href="/song/?id=${song.id}" class="stretched-link"></a>
            </div>`
    });
    
    new ProfilePaginator({
        url: `/api/v1/music/users/${targetUserId}/albums/`,
        allContainerId: 'allAlbumsContainer',
        overviewContainerId: 'albumsContainer',
        emptyMsg: 'Chưa có album nào',
        renderItem: album => `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0; cursor: pointer;" onclick="window.location.href='/album/detail/?id=${album.id}'">
                <div class="card-image-wrapper">
                    <img src="${album.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${album.title}">
                </div>
                <div class="card-title">${album.title}</div>
                <div class="card-subtitle">${album.song_count} bài hát</div>
            </div>`
    });
    
    new ProfilePaginator({
        url: `/api/v1/playlists/?user_id=${targetUserId}`,
        allContainerId: 'allPlaylistContainer',
        overviewContainerId: 'overviewPlaylistContainer',
        emptyMsg: 'Chưa có playlist nào',
        onItemsLoaded: (items) => {
            const el = document.getElementById('overviewPlaylistCount');
            if (el) el.textContent = items.length > 0 ? `(${items.length})` : '';
        },
        renderItem: pl => `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${pl.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${pl.title}">
                </div>
                <div class="card-title">${pl.title}</div>
                <div class="card-subtitle">${pl.song_count !== undefined ? pl.song_count + ' bài' : ''}</div>
                <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
            </div>`
    });
    
    new ProfilePaginator({
        url: `/api/v1/music/me/history/`,
        allContainerId: 'allRecentContainer',
        overviewContainerId: 'recentSongsContainerOverview',
        emptyMsg: 'Chưa có lịch sử nghe',
        renderItem: item => {
            const song = item.song || item;
            return `
            <div class="playlist-card position-relative" style="width: 100%; min-width: 0;">
                <div class="card-image-wrapper">
                    <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                </div>
                <div class="card-title">${song.title}</div>
                <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                <a href="/song/?id=${song.id}" class="stretched-link"></a>
            </div>`;
        }
    });
});

window.switchToTab = function(tabName) {
    const tab = document.querySelector(`.profile-tab[data-tab="${tabName}"]`);
    if (tab) {
        tab.click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};

document.querySelectorAll('.profile-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-section').forEach(s => s.style.display = 'none');
        tab.classList.add('active');
        const targetId = 'tab-' + tab.dataset.tab;
        const section = document.getElementById(targetId);
        if (section) section.style.display = 'block';
    });
});
