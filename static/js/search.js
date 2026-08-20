async function initSearchPage() {
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q') || '';
    
    if (q) {
        // Update header search input to reflect current query
        const searchInput = document.getElementById('topSearchInput');
        if (searchInput) {
            searchInput.value = q;
            const clearBtn = document.getElementById('clearSearchBtn');
            if (clearBtn) clearBtn.style.display = 'block';
        }
        
        document.getElementById('keywordDisplayError').textContent = q;
        await performSearch(q);
    } else {
        const loadingIndicator = document.getElementById('loadingIndicator');
        const noResults = document.getElementById('noResults');
        const keywordDisplayError = document.getElementById('keywordDisplayError');
        
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        if (noResults) noResults.style.display = 'block';
        if (keywordDisplayError) keywordDisplayError.textContent = '...';
    }
}

document.addEventListener('DOMContentLoaded', initSearchPage);

window.addEventListener('routerPageChanged', () => {
    if (window.location.pathname.startsWith('/search')) {
        // Reset state
        const loadingIndicator = document.getElementById('loadingIndicator');
        const searchResultsArea = document.getElementById('searchResultsArea');
        const noResults = document.getElementById('noResults');
        
        if (loadingIndicator) loadingIndicator.style.display = 'flex';
        if (searchResultsArea) searchResultsArea.style.display = 'none';
        if (noResults) noResults.style.display = 'none';
        
        initSearchPage();
    }
});

var globalSearchData = { songs: [], artists: [], playlists: [], albums: [], users: [] };
var currentFilter = 'all';

async function performSearch(query) {
    try {
        const res = await fetch(`/api/v1/search/?q=${encodeURIComponent(query)}&limit=10`);
        const data = await res.json();
        
        document.getElementById('loadingIndicator').style.display = 'none';
        
        if (data.success && data.data) {
            const songs = data.data.songs || [];
            const artists = data.data.artists || [];
            const playlists = data.data.playlists || [];
            const users = data.data.users || [];
            const albums = data.data.albums || [];
            
            if (songs.length > 0 || artists.length > 0 || playlists.length > 0 || users.length > 0 || albums.length > 0) {
                globalSearchData = { songs, artists, playlists, albums, users };
                applyFilter('all');
                document.getElementById('searchResultsArea').style.display = 'block';
            } else {
                document.getElementById('noResults').style.display = 'block';
            }
        } else {
            document.getElementById('noResults').style.display = 'block';
        }
    } catch (err) {
        console.error('Search API error:', err);
        document.getElementById('loadingIndicator').style.display = 'none';
        document.getElementById('noResults').style.display = 'block';
    }
}

window.applyFilter = function(type) {
    currentFilter = type;
    
    document.querySelectorAll('.filter-chip').forEach(btn => {
        if (btn.dataset.type === type) btn.classList.add('active');
        else btn.classList.remove('active');
    });
    
    renderFilteredResults();
}

function renderFilteredResults() {
    const { songs, artists, playlists, albums, users } = globalSearchData;
    
    let combinedUsers = [...artists];
    let uniqueUsers = [];
    let seenUserIds = new Set();
    combinedUsers.forEach(u => {
        let uid = u.user ? u.user.id : u.id;
        if (!seenUserIds.has(uid)) {
            seenUserIds.add(uid);
            uniqueUsers.push(u);
        }
    });

    const topCol = document.getElementById('topResultCol');
    const listCol = document.getElementById('listCol');
    const listTitle = document.getElementById('listTitle');
    
    if (currentFilter === 'all') {
        topCol.style.display = 'block';
        listCol.className = 'col-lg-7';
        listTitle.textContent = 'Bài hát';
        
        renderTopResult(songs, uniqueUsers, playlists, albums);
        renderList(songs.slice(0, 4), 'song');
    } else {
        topCol.style.display = 'none';
        listCol.className = 'col-lg-12';
        
        if (currentFilter === 'songs') {
            listTitle.textContent = 'Tất cả Bài hát';
            renderList(songs, 'song');
        } else if (currentFilter === 'artists') {
            listTitle.textContent = 'Nghệ sĩ';
            renderList(uniqueUsers, 'artist');
        } else if (currentFilter === 'playlists') {
            listTitle.textContent = 'Playlists';
            renderList(playlists, 'playlist');
        } else if (currentFilter === 'albums') {
            listTitle.textContent = 'Albums';
            renderList(albums, 'album');
        }
    }
}

function renderTopResult(songs, uniqueUsers, playlists, albums = []) {
    let topItem = null;
    let topType = '';
    
    if (uniqueUsers.length > 0) {
        topItem = uniqueUsers[0];
        topType = 'artist';
    } else if (albums.length > 0) {
        topItem = albums[0];
        topType = 'album';
    } else if (songs.length > 0) {
        topItem = songs[0];
        topType = 'song';
    } else if (playlists.length > 0) {
        topItem = playlists[0];
        topType = 'playlist';
    }

    if (topItem) {
        let topHtml = '';
        if (topType === 'artist') {
            const avatar = topItem.avatar || (topItem.user && topItem.user.avatar) || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80';
            const name = topItem.display_name || topItem.username || 'Người dùng';
            const isArtist = (topItem.stage_name !== undefined) || (topItem.role === 'artist');
            const subtitle = isArtist ? 'Nghệ sĩ' : 'Người dùng';
            const profileLink = topItem.user ? `/profile/${topItem.user.id}` : `/profile/${topItem.id}`;
            const userId = topItem.user ? topItem.user.id : topItem.id;
            
            let followBtnClass = "btn-outline-light text-white";
            let followBtnText = "Theo dõi";
            let followBtnStyle = "";
            if (topItem.follow_status === 'following') {
                followBtnClass = "";
                followBtnStyle = "background:#8CE1B2; color:#121929; border:none;";
                followBtnText = "Đang theo dõi";
            } else if (topItem.follow_status === 'requested') {
                followBtnClass = "";
                followBtnStyle = "background:#8CE1B2; color:#121929; border:none;";
                followBtnText = "Đã yêu cầu";
            }
            
                <a href="${profileLink}" class="top-result-card p-4 rounded-4 position-relative text-decoration-none text-reset" style="background-color: var(--bg-card); cursor: pointer; transition: background 0.3s;">
                    <img src="${avatar}" alt="Avatar" class="rounded-circle mb-3 shadow" style="width: 100px; height: 100px; object-fit: cover;">
                    <div class="top-result-content">
                        <h2 class="fw-bold text-white mb-2 top-result-title" style="letter-spacing: -0.5px;">${name}</h2>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill text-black" style="background-color: rgba(255,255,255,0.8); font-weight: 600;">${subtitle}</span>
                        </div>
                    </div>
                    
                    <button class="btn ${followBtnClass} rounded-pill fw-bold position-absolute px-4 py-2 top-result-btn" style="${followBtnStyle}" onclick="event.stopPropagation(); window.toggleFollowUser('${userId}', this);">
                        ${followBtnText}
                    </button>
                </a>
            `;
        } else if (topType === 'song') {
            const img = topItem.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=300&q=80';
            const artistName = topItem.artist ? topItem.artist.display_name : 'Nghệ sĩ';
                <a href="/song/?id=${topItem.id}" class="top-result-card p-4 rounded-4 position-relative text-decoration-none text-reset" style="background-color: var(--bg-card); cursor: pointer; transition: background 0.3s;">
                    <img src="${img}" alt="Cover" class="rounded-2 mb-3 shadow" style="width: 100px; height: 100px; object-fit: cover;">
                    <div class="top-result-content">
                        <h2 class="fw-bold text-white mb-2 top-result-title" style="letter-spacing: -0.5px;">${topItem.title}</h2>
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-muted-custom fw-semibold">${artistName}</span>
                        </div>
                    </div>
                    
                    <button class="btn-play-circle position-absolute top-result-btn" onclick="event.stopPropagation(); window.goToPage('/song/?id=${topItem.id}')">
                        <i class="bi bi-play-fill fs-3" style="margin-left: 3px;"></i>
                    </button>
                </a>
            `;
        } else if (topType === 'album') {
            const img = topItem.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=300&q=80';
            const artistName = topItem.artist ? (topItem.artist.display_name || topItem.artist.username) : 'Nghệ sĩ';
                <a href="/album/detail/?id=${topItem.id}" class="top-result-card p-4 rounded-4 position-relative text-decoration-none text-reset" style="background-color: var(--bg-card); cursor: pointer; transition: background 0.3s;">
                    <img src="${img}" alt="Cover" class="rounded-2 mb-3 shadow" style="width: 100px; height: 100px; object-fit: cover;">
                    <div class="top-result-content">
                        <h2 class="fw-bold text-white mb-2 top-result-title" style="letter-spacing: -0.5px;">${topItem.title}</h2>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill text-black" style="background-color: rgba(255,255,255,0.8); font-weight: 600;">Album</span>
                            <span class="text-muted-custom fw-semibold">${artistName}</span>
                        </div>
                    </div>
                    
                    <button class="btn-play-circle position-absolute top-result-btn" onclick="event.stopPropagation(); if(window.playAlbum) { window.playAlbum('${topItem.id}', '${topItem.title.replace(/'/g, "\\'")}'); }">
                        <i class="bi bi-play-fill fs-3" style="margin-left: 3px;"></i>
                    </button>
                </a>
            `;
        } else if (topType === 'playlist') {
            const img = topItem.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=300&q=80';
            const ownerName = topItem.owner ? (topItem.owner.display_name || topItem.owner.username) : 'Người dùng';
                <a href="/playlist/detail/?id=${topItem.id}" class="top-result-card p-4 rounded-4 position-relative text-decoration-none text-reset" style="background-color: var(--bg-card); cursor: pointer; transition: background 0.3s;">
                    <img src="${img}" alt="Cover" class="rounded-2 mb-3 shadow" style="width: 100px; height: 100px; object-fit: cover;">
                    <div class="top-result-content">
                        <h2 class="fw-bold text-white mb-2 top-result-title" style="letter-spacing: -0.5px;">${topItem.title}</h2>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge rounded-pill text-black" style="background-color: rgba(255,255,255,0.8); font-weight: 600;">Playlist</span>
                            <span class="text-muted-custom fw-semibold">${ownerName}</span>
                        </div>
                    </div>
                    
                    <button class="btn-play-circle position-absolute top-result-btn" onclick="event.stopPropagation(); if(window.playPlaylist) { window.playPlaylist('${topItem.id}', event, '${topItem.title.replace(/'/g, "\\'")}'); }">
                        <i class="bi bi-play-fill fs-3" style="margin-left: 3px;"></i>
                    </button>
                </a>
            `;
        } else {
            topHtml = `<div class="top-result-card p-4 rounded-4" style="background-color: var(--bg-card);"><h2 class="text-white">${topItem.title}</h2></div>`;
        }
        document.getElementById('topResultContainer').innerHTML = topHtml;
    } else {
        document.getElementById('topResultContainer').innerHTML = '';
    }
}

function renderList(items, type) {
    let html = '';
    if (items.length > 0) {
        items.forEach(item => {
            if (type === 'song') {
                const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                const artist = item.artist ? item.artist.display_name : 'Nghệ sĩ';
                
                html += `
                    <a href="/song/?id=${item.id}" class="song-row d-flex align-items-center justify-content-between p-2 rounded-3 text-decoration-none text-reset" style="cursor: pointer;">
                        <div class="d-flex align-items-center gap-3 flex-grow-1" style="min-width: 0;">
                            <div class="song-cover-container">
                                <img src="${img}" alt="cover" class="w-100 h-100 rounded" style="object-fit: cover;">
                                <div class="play-icon-overlay">
                                    <i class="bi bi-play-fill"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1 text-truncate pe-3" style="min-width: 0;">
                                <div class="text-white fw-semibold text-truncate" style="font-size: 1rem;">${item.title}</div>
                                <div class="text-muted-custom text-truncate" style="font-size: 0.85rem;">${artist}</div>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-3 flex-shrink-0">
                            <button class="btn btn-link text-muted-custom p-0 text-decoration-none" style="font-size: 1.2rem;" onclick="event.stopPropagation(); window.addToQueue('${item.id}', '${item.title.replace(/'/g, `\\'`)}', '${artist.replace(/'/g, `\\'`)}', '${img}', null, true); window.showToast('Đã thêm &quot;' + '${item.title.replace(/'/g, `\\'`)}' + '&quot; vào danh sách chờ', 'success');" title="Thêm vào danh sách chờ">
                                <i class="bi bi-plus-circle"></i>
                            </button>
                        </div>
                    </a>
                `;
            } else if (type === 'artist') {
                const avatar = item.avatar || (item.user && item.user.avatar) || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80';
                const name = item.display_name || item.username || 'Người dùng';
                const isArtist = (item.stage_name !== undefined) || (item.role === 'artist');
                const subtitle = isArtist ? 'Nghệ sĩ' : 'Người dùng';
                const profileLink = item.user ? `/profile/${item.user.id}` : `/profile/${item.id}`;
                const userId = item.user ? item.user.id : item.id;
                let followBtnClass = "btn-outline-light";
                let followBtnText = "Theo dõi";
                let followBtnStyle = "";
                if (item.follow_status === 'following') {
                    followBtnClass = "";
                    followBtnStyle = "background:#8CE1B2; color:#121929; border:none;";
                    followBtnText = "Đang theo dõi";
                } else if (item.follow_status === 'requested') {
                    followBtnClass = "";
                    followBtnStyle = "background:#8CE1B2; color:#121929; border:none;";
                    followBtnText = "Đã yêu cầu";
                }
                
                html += `
                    <a href="${profileLink}" class="song-row d-flex align-items-center justify-content-between p-2 rounded-3 text-decoration-none text-reset" style="cursor: pointer;">
                        <div class="d-flex align-items-center gap-3 flex-grow-1" style="min-width: 0;">
                            <div style="width: 48px; height: 48px; flex-shrink: 0;">
                                <img src="${avatar}" alt="Avatar" class="w-100 h-100 rounded-circle" style="object-fit: cover;">
                            </div>
                            <div class="flex-grow-1 text-truncate pe-3" style="min-width: 0;">
                                <div class="text-white fw-semibold text-truncate" style="font-size: 1rem;">${name}</div>
                                <div class="text-muted-custom text-truncate" style="font-size: 0.85rem;">${subtitle}</div>
                            </div>
                        </div>
                        <button class="btn ${followBtnClass} rounded-pill btn-sm fw-bold px-3 py-1 flex-shrink-0" onclick="event.stopPropagation(); window.toggleFollowUser('${userId}', this);" style="font-size: 0.8rem; border-color: rgba(255,255,255,0.3); ${followBtnStyle}">
                            ${followBtnText}
                        </button>
                    </a>
                `;
            } else if (type === 'playlist') {
                const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                const ownerName = item.owner ? (item.owner.display_name || item.owner.username) : 'Người dùng';
                html += `
                    <a href="/playlist/detail/?id=${item.id}" class="song-row d-flex align-items-center justify-content-between p-2 rounded-3 text-decoration-none text-reset" style="cursor: pointer;">
                        <div class="d-flex align-items-center gap-3 flex-grow-1" style="min-width: 0;">
                            <div class="song-cover-container">
                                <img src="${img}" alt="Cover" class="rounded-2" style="width: 100%; height: 100%; object-fit: cover;">
                            </div>
                            <div class="flex-grow-1 text-truncate pe-3" style="min-width: 0;">
                                <div class="text-white fw-semibold text-truncate" style="font-size: 1rem;">${item.title}</div>
                                <div class="text-muted-custom text-truncate" style="font-size: 0.85rem;">${ownerName}</div>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-3 flex-shrink-0">
                            <div class="text-muted-custom hide-md" style="font-size: 0.9rem;">Playlist</div>
                            <button class="btn btn-link text-white p-0 text-decoration-none" style="font-size: 1.5rem;" onclick="event.stopPropagation(); if(window.playPlaylist) { window.playPlaylist('${item.id}', event, '${item.title.replace(/'/g, "\\'")}'); }">
                                <i class="bi bi-play-circle"></i>
                            </button>
                        </div>
                    </a>
                `;
            } else if (type === 'album') {
                const img = item.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?w=100&q=80';
                const artistName = item.artist ? (item.artist.display_name || item.artist.username) : 'Nghệ sĩ';
                html += `
                    <a href="/album/detail/?id=${item.id}" class="song-row d-flex align-items-center justify-content-between p-2 rounded-3 text-decoration-none text-reset" style="cursor: pointer;">
                        <div class="d-flex align-items-center gap-3 flex-grow-1" style="min-width: 0;">
                            <div style="width: 48px; height: 48px; flex-shrink: 0;">
                                <img src="${img}" alt="cover" class="w-100 h-100 rounded" style="object-fit: cover;">
                            </div>
                            <div class="flex-grow-1 text-truncate pe-3" style="min-width: 0;">
                                <div class="text-white fw-semibold text-truncate" style="font-size: 1rem;">${item.title}</div>
                                <div class="text-muted-custom text-truncate" style="font-size: 0.85rem;">Album • ${artistName}</div>
                            </div>
                        </div>
                        <div class="d-flex align-items-center gap-3 flex-shrink-0">
                            <button class="btn btn-link text-white p-0 text-decoration-none" style="font-size: 1.5rem;" onclick="event.stopPropagation(); if(window.playAlbum) { window.playAlbum('${item.id}', '${item.title.replace(/'/g, "\\'")}'); }">
                                <i class="bi bi-play-circle"></i>
                            </button>
                        </div>
                    </a>
                `;
            }
        });
    } else {
        html = '<div class="text-muted-custom">Không có kết quả nào khớp.</div>';
    }
    
    document.getElementById('songsListContainer').innerHTML = html;
}
