/**
 * static/js/all_playlists.js
 *
 * Logic quản lý cho trang Tất cả Playlist.
 * Tương tự như albums.js, gọi API lấy danh sách playlist và hiển thị ra màn hình với infinite scroll.
 */

var CURRENT_USER_ID = window.PLAYLIST_CONFIG?.userId || '';

var currentPlaylistPage = 1;
var isFetchingPlaylists = false;
var hasMorePlaylists = true;

/** Map<string, playlistObject> */
var playlistCache = new Map();

function closeAllMenus() {
    document.querySelectorAll('.card-menu-dropdown.open')
        .forEach(d => d.classList.remove('open'));
}

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g,  '&amp;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;')
        .replace(/"/g,  '&quot;')
        .replace(/'/g, '&#39;');
}

function toast(msg, ok = true) {
    if (window.showToast) showToast(msg, ok);
}

/* ══════════════════════════════════════════════
   LOAD PLAYLISTS
══════════════════════════════════════════════ */
async function loadPlaylists(reset = true) {
    if (isFetchingPlaylists || (!hasMorePlaylists && !reset)) return;
    
    if (reset) {
        currentPlaylistPage = 1;
        hasMorePlaylists = true;
        playlistCache.clear();
    }

    isFetchingPlaylists = true;
    try {
        const res  = await fetch(`/api/v1/playlists/?page=${currentPlaylistPage}&page_size=10`);
        const data = await res.json();
        if (!data.success) return;

        let playlists = [];
        let pagination = null;
        
        if (Array.isArray(data.data)) {
            playlists = data.data;
            hasMorePlaylists = false;
        } else if (data.data.items) {
            playlists = data.data.items;
            pagination = data.data.pagination;
            if (pagination) {
                hasMorePlaylists = currentPlaylistPage < pagination.total_pages;
                const badge = document.getElementById('playlistCountBadge');
                if (badge) badge.textContent = `${pagination.total} playlist`;
            } else {
                hasMorePlaylists = false;
            }
        }

        playlists.forEach(p => playlistCache.set(String(p.id), p));

        renderGrid(playlists, !reset);
        
        currentPlaylistPage++;
    } catch (err) {
        console.error('loadPlaylists:', err);
    } finally {
        isFetchingPlaylists = false;
    }
}

function renderGrid(playlists, append = false) {
    const grid  = document.getElementById('playlistGrid');
    const noMsg = document.getElementById('noPlaylistsMsg');
    if (!grid) return;

    if (!append) grid.innerHTML = '';

    if (!append && playlists.length === 0) {
        if (noMsg) noMsg.classList.remove('d-none');
        return;
    }
    if (noMsg) noMsg.classList.add('d-none');

    const startIndex = append ? grid.children.length : 0;
    playlists.forEach((playlist, index) => grid.appendChild(buildPlaylistCard(playlist, startIndex + index + 1)));
}

function buildPlaylistCard(playlist, index) {
    const playlistId = String(playlist.id);
    const card    = document.createElement('div');
    card.className       = 'playlist-grid album-list-grid playlist-grid-row py-2 px-3 rounded position-relative';
    card.dataset.playlistId = playlistId;

    const coverHtml = playlist.cover_image
        ? `<img src="${escHtml(playlist.cover_image)}" alt="${escHtml(playlist.title)}" class="rounded flex-shrink-0" style="width: 40px; height: 40px; object-fit: cover;">`
        : `<div class="rounded flex-shrink-0 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; background: #2a2a2a; color: rgba(255,255,255,0.2);"><i class="bi bi-music-note-list"></i></div>`;

    const isPublic = playlist.is_public;
    
    // Format created_at to DD/MM/YYYY
    let createdStr = '';
    if (playlist.created_at) {
        const d = new Date(playlist.created_at);
        createdStr = d.toLocaleDateString('vi-VN');
    }

    card.innerHTML = `
        <div class="text-secondary text-center">${index}</div>
        <div class="d-flex align-items-center gap-3 text-truncate">
            ${coverHtml}
            <div class="text-truncate">
                <div class="fw-semibold text-white text-truncate">${escHtml(playlist.title)}</div>
                <div class="small text-secondary text-truncate">${isPublic ? 'Công khai' : 'Riêng tư'}</div>
            </div>
        </div>
        <div class="text-secondary hide-md text-truncate">
            ${isPublic ? 'Công khai' : 'Riêng tư'}
        </div>
        <div class="text-secondary hide-lg text-truncate">
            ${playlist.song_count || 0} bài hát
        </div>
        <div class="text-secondary hide-lg">
            ${createdStr}
        </div>
        <div class="text-secondary text-center">
            <div style="position:relative; display:inline-block;">
                <i class="bi bi-three-dots-vertical hover-text-white card-menu-btn js-menu-btn" title="Tùy chọn" style="cursor: pointer; font-size: 1.1rem; z-index: 3; transition: color 0.2s; position:relative; background:transparent; border:none; color:var(--pm-muted); padding:0;"></i>
                <div class="card-menu-dropdown js-menu-dropdown">
                    <button class="card-menu-item js-manage">
                        <i class="bi bi-music-note-list"></i> Quản lý bài hát
                    </button>
                    <button class="card-menu-item js-edit">
                        <i class="bi bi-pencil"></i> Chỉnh sửa
                    </button>
                    <div class="card-menu-divider"></div>
                    <button class="card-menu-item danger js-delete">
                        <i class="bi bi-trash3"></i> Xóa playlist
                    </button>
                </div>
            </div>
        </div>
    `;

    const menuBtn      = card.querySelector('.js-menu-btn');
    const menuDropdown = card.querySelector('.js-menu-dropdown');

    menuBtn.onclick = e => {
        e.stopPropagation();
        const isOpen = menuDropdown.classList.contains('open');
        closeAllMenus();
        if (!isOpen) menuDropdown.classList.add('open');
    };

    card.querySelector('.js-manage').onclick = e => {
        e.stopPropagation(); closeAllMenus(); 
        openPlaylistSongs(playlistId, playlist.title);
    };
    card.querySelector('.js-edit').onclick   = e => {
        e.stopPropagation(); closeAllMenus(); 
        if(window.openPlaylistFormModal) window.openPlaylistFormModal(playlist, e);
    };
    card.querySelector('.js-delete').onclick = e => {
        e.stopPropagation(); closeAllMenus(); 
        askDeletePlaylist(playlistId, playlist.title);
    };

    /* Click vào card → đi tới trang chi tiết playlist */
    card.onclick = () => window.location.href = `/playlist/detail/?id=${playlistId}`;
    return card;
}

function askDeletePlaylist(playlistId, name) {
    if (confirm(`Bạn có chắc muốn xoá playlist "${name}" không?`)) {
        deletePlaylist(playlistId);
    }
}

async function deletePlaylist(playlistId) {
    try {
        const csrfToken = typeof getCookie === 'function' ? getCookie('csrftoken') : '';
        const res = await fetch(`/api/v1/playlists/${playlistId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        if (res.ok) {
            toast('Đã xoá playlist', true);
            loadPlaylists(true);
        } else {
            toast('Không thể xoá playlist', false);
        }
    } catch (e) {
        console.error(e);
        toast('Lỗi khi xoá', false);
    }
}

/* ══════════════════════════════════════════════
   INIT
══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    /* Đóng tất cả dropdown khi click bên ngoài card */
    document.addEventListener('click', closeAllMenus);

    /* Scroll pagination */
    const handleScroll = function(e) {
        const target = e.target;
        if (target && target.classList && target.classList.contains('content-scroll')) {
            if (target.scrollHeight - target.scrollTop <= target.clientHeight + 150) {
                loadPlaylists(false);
            }
        }
    };
    
    document.addEventListener('scroll', handleScroll, true);

    const searchResultsContainerPlaylist = document.getElementById('songSearchResultsPlaylist');
    if (searchResultsContainerPlaylist) {
        searchResultsContainerPlaylist.addEventListener('scroll', function() {
            if (this.scrollHeight - this.scrollTop <= this.clientHeight + 20) {
                if (currentSearchPagePlaylist * PLAYLIST_SEARCH_PAGE_SIZE < currentSearchResultsPlaylist.length) {
                    renderSearchPagePlaylist();
                }
            }
        });
    }

    loadPlaylists(true);
});

/* ─── QUẢN LÝ BÀI HÁT PLAYLIST (TỪ MODAL) ─── */
var currentManagePlaylistId = null;
var playlistSongSearchTimeout = null;
var currentSearchPagePlaylist = 0;
var currentSearchResultsPlaylist = [];
var PLAYLIST_SEARCH_PAGE_SIZE = 5;

function fmtDuration(secs) {
    if (!secs) return '';
    const m = Math.floor(secs / 60);
    const s = String(secs % 60).padStart(2, '0');
    return `${m}:${s}`;
}

async function openPlaylistSongs(playlistId, playlistName) {
    currentManagePlaylistId = playlistId;

    // Set title
    const pTitle = document.getElementById('playlistSongsTitle');
    if (pTitle) pTitle.textContent = playlistName || 'Quản lý bài hát';

    const sInput = document.getElementById('songSearchInputPlaylist');
    if (sInput) sInput.value = '';
    
    const sResults = document.getElementById('songSearchResultsPlaylist');
    if (sResults) sResults.innerHTML = '';

    bootstrap.Modal.getOrCreateInstance(document.getElementById('playlistSongsModal')).show();

    await loadPlaylistSongs(playlistId);
}

async function loadPlaylistSongs(playlistId) {
    const container = document.getElementById('playlistSongsListContainer');
    if (!container) return;
    
    container.innerHTML =
        `<div class="text-center py-3">
            <div class="spinner-border spinner-border-sm" style="color:var(--pm-theme);"></div>
         </div>`;

    try {
        const res  = await fetch(`/api/v1/playlists/${playlistId}/songs/`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error?.message);

        const songs = data.data.items || [];
        const countBadge = document.getElementById('playlistSongCount');
        if (countBadge) countBadge.textContent = `${songs.length} bài`;

        if (songs.length === 0) {
            container.innerHTML =
                `<div class="text-center py-4 text-secondary small">
                    <i class="bi bi-music-note"
                        style="font-size:2rem;opacity:.3;display:block;margin-bottom:.5rem;"></i>
                    Chưa có bài hát nào trong playlist.
                 </div>`;
            return;
        }

        container.innerHTML = '';
        songs.forEach((item, i) => {
            const s   = item.song;
            const row = document.createElement('div');
            row.className = 'song-row';

            const thumb = s.cover_image
                ? `<img src="${escHtml(s.cover_image)}" class="song-thumb" alt="">`
                : `<div class="song-thumb-ph"><i class="bi bi-music-note"></i></div>`;

            row.innerHTML = `
                <span class="song-num">${i + 1}</span>
                ${thumb}
                <div class="song-info">
                    <div class="song-title-sm">${escHtml(s.title)}</div>
                    <div class="song-dur">${fmtDuration(s.duration)}</div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn-rm-song" title="Xoá khỏi playlist">
                        <i class="bi bi-x-lg" style="font-size:.8rem;"></i>
                    </button>
                </div>`;

            row.querySelector('.btn-rm-song').onclick =
                () => removeSongFromPlaylist(playlistId, s.id);

            container.appendChild(row);
        });
    } catch (err) {
        container.innerHTML =
            `<div class="text-danger py-3 text-center small">Lỗi tải dữ liệu</div>`;
        console.error('loadPlaylistSongs:', err);
    }
}

window.debouncedSearchPlaylist = function(q) {
    clearTimeout(playlistSongSearchTimeout);
    playlistSongSearchTimeout = setTimeout(() => searchPlaylistSongs(q), 300);
}

async function searchPlaylistSongs(query) {
    const container = document.getElementById('songSearchResultsPlaylist');
    if (!container) return;
    
    const q = query.trim().toLowerCase();
    
    currentSearchPagePlaylist = 0;
    currentSearchResultsPlaylist = [];
    container.innerHTML = '';

    if (!q) return;

    container.innerHTML =
        `<div class="text-center py-2"><span class="spinner-border spinner-border-sm text-secondary"></span></div>`;

    try {
        const res = await fetch(`/api/v1/music/songs/?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        
        if (!data.success || !data.data.items || data.data.items.length === 0) {
            container.innerHTML =
                `<div class="song-row text-secondary" style="font-size:.78rem;">
                    Không tìm thấy bài hát</div>`;
            return;
        }
        
        currentSearchResultsPlaylist = data.data.items;
        container.innerHTML = '';
        renderSearchPagePlaylist();
        
    } catch(err) {
        container.innerHTML =
            `<div class="song-row text-danger" style="font-size:.78rem;">Lỗi tìm kiếm</div>`;
    }
}

function renderSearchPagePlaylist() {
    const container = document.getElementById('songSearchResultsPlaylist');
    const start = currentSearchPagePlaylist * PLAYLIST_SEARCH_PAGE_SIZE;
    const end = start + PLAYLIST_SEARCH_PAGE_SIZE;
    const results = currentSearchResultsPlaylist.slice(start, end);
    
    if (results.length === 0) return;

    results.forEach(s => {
        const row = document.createElement('div');
        row.className    = 'song-row';
        row.style.cursor = 'pointer';

        const thumb = s.cover_image
            ? `<img src="${escHtml(s.cover_image)}" class="song-thumb"
                style="width:32px;height:32px;" alt="">`
            : `<div class="song-thumb-ph" style="width:32px;height:32px;">
                <i class="bi bi-music-note"></i></div>`;

        row.innerHTML = `
            ${thumb}
            <div class="song-info">
                <div class="song-title-sm" style="font-size:.82rem;">${escHtml(s.title)}</div>
                <div class="text-secondary" style="font-size:.7rem;">${s.artist ? escHtml(s.artist.display_name) : 'Unknown'}</div>
            </div>
            <i class="bi bi-plus-circle text-white"
                style="font-size:1.1rem;flex-shrink:0;"></i>`;
        row.onclick = () => addSongToPlaylist(s.id, s.title);
        container.appendChild(row);
    });
    
    currentSearchPagePlaylist++;
}

async function addSongToPlaylist(songId, songTitle) {
    if (!currentManagePlaylistId) return;
    try {
        const res  = await fetch(`/api/v1/playlists/${currentManagePlaylistId}/songs/`, {
            method:  'POST',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '', 'Content-Type': 'application/json' },
            body:    JSON.stringify({ song_id: songId }),
        });
        const data = await res.json();
        if (data.success) {
            toast(`Đã thêm "${songTitle}" vào playlist!`, true);
            const sInput = document.getElementById('songSearchInputPlaylist');
            if (sInput) sInput.value = '';
            const sResults = document.getElementById('songSearchResultsPlaylist');
            if (sResults) sResults.innerHTML = '';
            
            await loadPlaylistSongs(currentManagePlaylistId);
        } else {
            toast(data.error?.message || 'Không thể thêm bài hát', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    }
}

async function removeSongFromPlaylist(playlistId, songId) {
    try {
        const res = await fetch(`/api/v1/playlists/${playlistId}/songs/${songId}/`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '' }
        });
        const data = await res.json();
        if (data.success) {
            toast('Đã xoá bài hát khỏi playlist', true);
            await loadPlaylistSongs(playlistId);
        } else {
            toast(data.error?.message || 'Không thể xoá bài hát', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    }
}
