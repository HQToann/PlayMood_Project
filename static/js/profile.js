document.addEventListener('DOMContentLoaded', () => {
    const bioInput = document.getElementById('bioInput');
    const bioCharCount = document.getElementById('bioCharCount');
    if (bioInput && bioCharCount) {
        const updateCount = () => {
            bioCharCount.textContent = bioInput.value.length;
        };
        bioInput.addEventListener('input', updateCount);
        updateCount();
    }
});

async function saveBio() {
    const bio = document.getElementById('bioInput').value.trim();
    try {
        const res = await fetch('/api/v1/accounts/me/', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({ bio })
        });
        
        if (res.ok) {
            document.getElementById('bioText').textContent = bio || 'Thêm tiểu sử...';
            if (window.showToast) showToast('Đã cập nhật tiểu sử!', 'success');
        } else {
            const json = await res.json().catch(() => ({}));
            if (window.showToast) showToast(json.error?.message || 'Lỗi cập nhật', 'error');
        }
    } catch (e) {
        if (window.showToast) showToast('Lỗi kết nối', 'error');
    }
}

// Preview avatar
document.getElementById('avatarInput')?.addEventListener('change', function(e) {
    if (e.target.files && e.target.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('avatarPreview').src = e.target.result;
        }
        reader.readAsDataURL(e.target.files[0]);
    }
});

// Preview cover
document.getElementById('coverInput')?.addEventListener('change', function(e) {
    if (e.target.files && e.target.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('coverPreview').src = e.target.result;
        }
        reader.readAsDataURL(e.target.files[0]);
    }
});

async function saveImages() {
    const avatarFile = document.getElementById('avatarInput')?.files[0];
    const coverFile = document.getElementById('coverInput')?.files[0];
    
    if (!avatarFile && !coverFile) {
        if (window.showToast) showToast('Chưa chọn ảnh nào để cập nhật', 'info');
        return;
    }

    const formData = new FormData();
    if (avatarFile) formData.append('avatar', avatarFile);
    if (coverFile) formData.append('cover', coverFile);

    try {
        const res = await fetch('/api/v1/accounts/me/images/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: formData
        });
        const json = await res.json();
        if (json.success || res.ok) {
            if (window.showToast) showToast('Đã cập nhật ảnh thành công!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            if (window.showToast) showToast(json.error?.message || 'Lỗi cập nhật ảnh', 'error');
        }
    } catch (e) {
        if (window.showToast) showToast('Lỗi kết nối', 'error');
    }
}

async function saveSocials() {
    const website = document.getElementById('websiteInput')?.value.trim();
    const facebook = document.getElementById('facebookInput')?.value.trim();
    const youtube = document.getElementById('youtubeInput')?.value.trim();

    try {
        const res = await fetch('/api/v1/artists/me/', {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                website_url: website,
                facebook_url: facebook,
                youtube_url: youtube
            })
        });
        const json = await res.json();
        if (json.success || res.ok) {
            if (window.showToast) showToast('Đã cập nhật liên kết thành công!', 'success');
            setTimeout(() => window.location.reload(), 1000);
        } else {
            if (window.showToast) showToast(json.error?.message || 'Lỗi cập nhật liên kết', 'error');
        }
    } catch (e) {
        if (window.showToast) showToast('Lỗi kết nối', 'error');
    }
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1).replace('.0', '') + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1).replace('.0', '') + 'K';
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
        
        // Load artist stats if element exists
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

async function loadLikedSongs() {
    const containers = ['likedSongsContainer', 'allLikedSongsContainer'].map(id => document.getElementById(id)).filter(Boolean);
    if (!containers.length) return;
    const targetUserId = window.TARGET_USER_ID;
    try {
        const res = await fetch(`/api/v1/music/users/${targetUserId}/likes/?limit=20`);
        const data = await res.json();
        const songs = (data.success && data.data) ? data.data : [];
        const html = songs.length > 0
            ? songs.map(song => `
                <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                    <div class="card-image-wrapper">
                        <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                        <div class="card-play-btn" onclick="playSong('${song.id}', event)" style="position:relative;z-index:2;"><i class="bi bi-play-fill"></i></div>
                    </div>
                    <div class="card-title">${song.title}</div>
                    <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                    <a href="/song/?id=${song.id}" class="stretched-link"></a>
                </div>`).join('')
            : '<div class="text-secondary py-3 text-center small w-100">Chưa có bài hát yêu thích nào</div>';
        containers.forEach(c => c.innerHTML = html);
    } catch (e) {
        console.error('Lỗi khi tải bài hát yêu thích', e);
        containers.forEach(c => c.innerHTML = '<div class="text-danger py-3 text-center small">Lỗi khi tải bài hát</div>');
    }
}

async function loadAlbums() {
    const containers = ['albumsContainer', 'allAlbumsContainer'].map(id => document.getElementById(id)).filter(Boolean);
    if (!containers.length) return;
    const targetUserId = window.TARGET_USER_ID;
    try {
        const res = await fetch(`/api/v1/music/users/${targetUserId}/albums/`);
        const data = await res.json();
        const albums = (data.success && data.data && data.data.items) ? data.data.items : [];
        const html = albums.length > 0
            ? albums.map(album => `
                <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                    <div class="card-image-wrapper">
                        <img src="${album.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${album.title}">
                        <div class="card-play-btn"><i class="bi bi-play-fill"></i></div>
                    </div>
                    <div class="card-title">${album.title}</div>
                    <div class="card-subtitle">${album.song_count} bài hát</div>
                </div>`).join('')
            : '<div class="text-secondary py-3 text-center small w-100">Chưa có album nào</div>';
        containers.forEach(c => c.innerHTML = html);
    } catch (e) {
        console.error('Lỗi khi tải album', e);
        containers.forEach(c => c.innerHTML = '<div class="text-danger py-3 text-center small w-100">Lỗi khi tải album</div>');
    }
}

async function loadPlaylists() {
    const containers = ['overviewPlaylistContainer', 'allPlaylistContainer'].map(id => document.getElementById(id)).filter(Boolean);
    if (!containers.length) return;
    const targetUserId = window.TARGET_USER_ID;
    try {
        const res = await fetch(`/api/v1/playlists/?user_id=${targetUserId}`);
        const data = await res.json();
        const playlists = (data.success && data.data && data.data.items) ? data.data.items : [];

        const el = document.getElementById('overviewPlaylistCount');
        if (el) el.textContent = playlists.length > 0 ? `(${playlists.length})` : '';

        const html = playlists.length > 0
            ? playlists.map(pl => `
                <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                    <div class="card-image-wrapper">
                        <img src="${pl.cover_image || 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${pl.title}">
                        <div class="card-play-btn" onclick="playPlaylist('${pl.id}', event)" style="position:relative;z-index:2;"><i class="bi bi-play-fill"></i></div>
                    </div>
                    <div class="card-title">${pl.title}</div>
                    <div class="card-subtitle">${pl.song_count !== undefined ? pl.song_count + ' bài' : ''}</div>
                    <a href="/playlist/detail/?id=${pl.id}" class="stretched-link"></a>
                </div>`).join('')
            : '<div class="text-secondary py-3 text-center small w-100">Chưa có playlist nào</div>';
        containers.forEach(c => c.innerHTML = html);
    } catch (e) {
        console.error('Lỗi khi tải playlist', e);
    }
}

async function loadRecentSongs() {
    const containers = ['recentSongsContainerOverview', 'allRecentContainer'].map(id => document.getElementById(id)).filter(Boolean);
    if (!containers.length) return;
    try {
        const res = await fetch('/api/v1/music/me/history/?limit=20');
        const data = await res.json();
        const items = (data.success && data.data && data.data.items) ? data.data.items : [];

        const html = items.length > 0
            ? items.map(item => {
                const song = item.song || item;
                return `
                <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                    <div class="card-image-wrapper">
                        <img src="${song.cover_image || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'}" alt="${song.title}">
                        <div class="card-play-btn" onclick="playSong('${song.id}', event)" style="position:relative;z-index:2;"><i class="bi bi-play-fill"></i></div>
                    </div>
                    <div class="card-title">${song.title}</div>
                    <div class="card-subtitle">${song.artist?.display_name || ''}</div>
                    <a href="/song/?id=${song.id}" class="stretched-link"></a>
                </div>`;}).join('')
            : '<div class="text-secondary py-3 text-center small w-100">Chưa có lịch sử nghe</div>';
        containers.forEach(c => c.innerHTML = html);
    } catch (e) {
        console.error('Lỗi khi tải lịch sử nghe', e);
    }
}

// Tab switching
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

document.addEventListener("DOMContentLoaded", () => {
    loadStats();
    loadLikedSongs();
    loadAlbums();
    loadPlaylists();
    loadRecentSongs();
});
