/**
 * static/js/albums.js
 *
 * Logic quản lý album cho trang Library > Albums.
 *
 * Biến cấu hình được inject từ template albums.html:
 *   window.ALBUM_CONFIG = { userId: '...', isArtist: true/false }
 *
 * Yêu cầu: Bootstrap 5 + Bootstrap Icons đã được load trước file này.
 */

/* ══════════════════════════════════════════════
   STATE (lấy config từ template qua window.ALBUM_CONFIG)
══════════════════════════════════════════════ */
var CURRENT_USER_ID = window.ALBUM_CONFIG?.userId   || '';
var IS_ARTIST       = window.ALBUM_CONFIG?.isArtist || false;

var currentAlbumId   = null;
var deleteTargetId   = null;

/** Map<string, albumObject> – tránh JSON.stringify inline trong onclick */
var albumCache = new Map();

var myPublishedSongs  = null;   // null = chưa load
var songSearchTimeout = null;
var currentSearchQuery = '';
var currentSearchResults = [];
var currentSearchPage = 0;
var SEARCH_PAGE_SIZE = 5;

/* ══════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════ */

function fmtDuration(secs) {
    if (!secs) return '';
    const m = Math.floor(secs / 60);
    const s = String(secs % 60).padStart(2, '0');
    return `${m}:${s}`;
}

function toast(msg, ok = true) {
    if (window.showToast) showToast(msg, ok);
}

function escHtml(str) {
    return String(str)
        .replace(/&/g,  '&amp;')
        .replace(/</g,  '&lt;')
        .replace(/>/g,  '&gt;')
        .replace(/"/g,  '&quot;')
        .replace(/'/g, '&#39;');
}

function getModal(id) {
    return bootstrap.Modal.getOrCreateInstance(document.getElementById(id));
}

/** Đóng tất cả card menu dropdown đang mở */
function closeAllMenus() {
    document.querySelectorAll('.card-menu-dropdown.open')
        .forEach(d => d.classList.remove('open'));
}

/* ══════════════════════════════════════════════
   LOAD ALBUMS
══════════════════════════════════════════════ */
var currentAlbumPage = 1;
var isFetchingAlbums = false;
var hasMoreAlbums = true;

async function loadAlbums(reset = true) {
    if (isFetchingAlbums || (!hasMoreAlbums && !reset)) return;
    
    if (reset) {
        currentAlbumPage = 1;
        hasMoreAlbums = true;
        albumCache.clear();
    }

    isFetchingAlbums = true;
    try {
        const res  = await fetch(`/api/v1/music/users/${CURRENT_USER_ID}/albums/?page=${currentAlbumPage}&page_size=10`);
        const data = await res.json();
        if (!data.success) return;

        let albums = [];
        let pagination = null;
        
        if (Array.isArray(data.data)) {
            // Trường hợp backend chưa update phân trang (hoặc lỗi fallback)
            albums = data.data;
            hasMoreAlbums = false;
        } else if (data.data.items) {
            albums = data.data.items;
            pagination = data.data.pagination;
            if (pagination) {
                hasMoreAlbums = currentAlbumPage < pagination.total_pages;
                const badge = document.getElementById('albumCountBadge');
                if (badge) badge.textContent = `${pagination.total} album`;
            } else {
                hasMoreAlbums = false;
            }
        }

        albums.forEach(a => albumCache.set(String(a.id), a));

        renderGrid(albums, !reset);
        
        currentAlbumPage++;
    } catch (err) {
        console.error('loadAlbums:', err);
    } finally {
        isFetchingAlbums = false;
    }
}

function renderGrid(albums, append = false) {
    const grid  = document.getElementById('albumGrid');
    const noMsg = document.getElementById('noAlbumsMsg');
    if (!grid) return;

    if (!append) grid.innerHTML = '';

    if (!append && albums.length === 0) {
        if (noMsg) noMsg.classList.remove('d-none');
        return;
    }
    if (noMsg) noMsg.classList.add('d-none');

    const startIndex = append ? grid.children.length : 0;
    albums.forEach((album, index) => grid.appendChild(buildAlbumCard(album, startIndex + index + 1)));
}

/* ── Build card – nút ⋮ cố định + dropdown menu (thân thiện mobile) ── */
function buildAlbumCard(album, index) {
    const albumId = String(album.id);
    const card    = document.createElement('div');
    card.className       = 'playlist-grid album-list-grid playlist-grid-row py-2 px-3 rounded position-relative';
    card.dataset.albumId = albumId;

    const coverHtml = album.cover_image
        ? `<img src="${escHtml(album.cover_image)}" alt="${escHtml(album.title)}" class="rounded flex-shrink-0" style="width: 40px; height: 40px; object-fit: cover;">`
        : `<div class="rounded flex-shrink-0 d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; background: #2a2a2a; color: rgba(255,255,255,0.2);"><i class="bi bi-vinyl-fill"></i></div>`;

    const isPub = album.status === 'published';
    
    // Format created_at to DD/MM/YYYY
    let createdStr = '';
    if (album.created_at) {
        const d = new Date(album.created_at);
        createdStr = d.toLocaleDateString('vi-VN');
    }

    card.innerHTML = `
        <div class="text-secondary text-center">${index}</div>
        <div class="d-flex align-items-center gap-3 text-truncate">
            ${coverHtml}
            <div class="text-truncate">
                <div class="fw-semibold text-white text-truncate">${escHtml(album.title)}</div>
                <div class="small text-secondary text-truncate">${isPub ? 'Phát hành' : 'Nháp'}</div>
            </div>
        </div>
        <div class="text-secondary hide-md text-truncate">
            ${isPub ? 'Phát hành' : 'Nháp'}
        </div>
        <div class="text-secondary hide-lg text-truncate">
            ${album.song_count} bài hát
        </div>
        <div class="text-secondary hide-lg">
            ${createdStr}
        </div>
        <div class="text-secondary text-center">
            <div style="position:relative; display:inline-block;">
                <i class="bi bi-three-dots-vertical hover-text-white card-menu-btn js-menu-btn" title="Tùy chọn" style="cursor: pointer; font-size: 1.1rem; z-index: 3; transition: color 0.2s; position:relative; background:transparent; border:none; color:var(--pm-muted); padding:0;"></i>
                <div class="card-menu-dropdown js-menu-dropdown">
                    <button class="card-menu-item js-songs">
                        <i class="bi bi-music-note-list"></i> Quản lý bài hát
                    </button>
                    <button class="card-menu-item js-edit">
                        <i class="bi bi-pencil"></i> Chỉnh sửa album
                    </button>
                    <div class="card-menu-divider"></div>
                    <button class="card-menu-item danger js-delete">
                        <i class="bi bi-trash3"></i> Xóa album
                    </button>
                </div>
            </div>
        </div>
    `;

    const menuBtn      = card.querySelector('.js-menu-btn');
    const menuDropdown = card.querySelector('.js-menu-dropdown');

    /* Toggle dropdown khi bấm nút ⋮ */
    menuBtn.onclick = e => {
        e.stopPropagation();
        const isOpen = menuDropdown.classList.contains('open');
        closeAllMenus();
        if (!isOpen) menuDropdown.classList.add('open');
    };

    /* Các action trong dropdown */
    card.querySelector('.js-songs').onclick  = e => {
        e.stopPropagation(); closeAllMenus(); openAlbumSongs(albumId);
    };
    card.querySelector('.js-edit').onclick   = e => {
        e.stopPropagation(); closeAllMenus(); openEditAlbum(albumId);
    };
    card.querySelector('.js-delete').onclick = e => {
        e.stopPropagation(); closeAllMenus(); askDeleteAlbum(albumId);
    };

    /* Click vào card → đi tới trang chi tiết album */
    card.onclick = () => window.location.href = `/album/detail/?id=${albumId}`;
    return card;
}

/* ══════════════════════════════════════════════
   PLAY ALBUM
══════════════════════════════════════════════ */
/**
 * Fetch bài hát trong album rồi phát bài đầu tiên.
 * Nếu album rỗng → thông báo toast.
 */
async function playAlbum(albumId, albumTitle = 'Album') {
    try {
        let contextName = albumTitle;
        if (contextName === 'Album') {
            try {
                const alRes = await fetch(`/api/v1/music/albums/${albumId}/`);
                const alData = await alRes.json();
                if (alData.success && alData.data) {
                    contextName = alData.data.title || 'Album';
                }
            } catch(e) {}
        }

        const res  = await fetch(`/api/v1/music/albums/${albumId}/songs/`);
        const data = await res.json();
        if (!data.success) { toast('Không thể tải album', false); return; }

        const songs = data.data.items || [];
        if (songs.length === 0) {
            toast('Album chưa có bài hát nào', false);
            return;
        }

        /* Phát bài đầu tiên qua window.playSong */
        const firstSongId = songs[0].song.id;
        if (typeof window.playSong === 'function') {
            // Xoá sạch danh sách chờ hiện tại trước khi phát album
            if (typeof window._songQueue !== 'undefined') {
                window._songQueue = [];
                localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
            }

            window.playSong(firstSongId);
            
            // Append rest to queue
            let rest = songs.slice(1);
            
            // Xáo trộn nếu đang bật chế độ ngẫu nhiên
            const isShuffle = localStorage.getItem("pm_shuffle") === "true";
            if (isShuffle && rest.length > 0) {
                for (let i = rest.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [rest[i], rest[j]] = [rest[j], rest[i]];
                }
            }

            rest.forEach(item => {
                const s = item.song;
                const artistName = s.artist ? (s.artist.display_name || s.artist.username || 'Unknown') : 'Unknown';
                window.addToQueue(s.id, s.title, artistName, s.cover_image, `Nội dung tiếp theo từ ${contextName}`, true);
            });
        } else {
            toast('Player chưa sẵn sàng', false);
        }
    } catch (err) {
        console.error('playAlbum:', err);
        toast('Lỗi kết nối', false);
    }
}

/* ══════════════════════════════════════════════
   MODAL: TẠO / SỬA ALBUM
══════════════════════════════════════════════ */
function openCreateAlbumModal() {
    document.getElementById('albumFormTitle').textContent = 'Tạo Album mới';
    document.getElementById('editAlbumId').value          = '';
    document.getElementById('albumTitleInput').value      = '';
    document.getElementById('albumDescInput').value       = '';
    document.getElementById('albumCoverInput').value      = '';
    const statusDiv = document.getElementById('editAlbumStatusActions');
    if (statusDiv) statusDiv.innerHTML = '';
    resetCover();
    getModal('albumFormModal').show();
}

function openEditAlbum(albumId) {
    const album = albumCache.get(String(albumId));
    if (!album) return;
    document.getElementById('albumFormTitle').textContent = 'Chỉnh sửa Album';
    document.getElementById('editAlbumId').value          = albumId;
    document.getElementById('albumTitleInput').value      = album.title || '';
    document.getElementById('albumDescInput').value       = album.description || '';
    document.getElementById('albumCoverInput').value      = '';
    album.cover_image ? setCover(album.cover_image) : resetCover();
    
    const statusDiv = document.getElementById('editAlbumStatusActions');
    if (statusDiv) {
        if (album.status === 'draft') {
            statusDiv.innerHTML = `<button type="button" class="btn-save-album" onclick="publishAlbum('${album.id}', 'edit')">Phát hành</button>`;
        } else {
            statusDiv.innerHTML = `<button type="button" class="btn-pm-outline" onclick="unpublishAlbum('${album.id}', 'edit')">Ẩn album</button>`;
        }
    }
    
    getModal('albumFormModal').show();
}

function resetCover() {
    document.getElementById('coverPreviewBox').innerHTML =
        '<i class="bi bi-image"></i>';
}

function setCover(src) {
    document.getElementById('coverPreviewBox').innerHTML =
        `<img src="${src}" alt="cover">`;
}

async function saveAlbum() {
    const albumId   = document.getElementById('editAlbumId').value.trim();
    const title     = document.getElementById('albumTitleInput').value.trim();
    const desc      = document.getElementById('albumDescInput').value.trim();
    const coverFile = document.getElementById('albumCoverInput').files?.[0];

    if (!title) {
        toast('Vui lòng nhập tên album', false);
        document.getElementById('albumTitleInput').focus();
        return;
    }

    const btn = document.getElementById('saveAlbumBtn');
    btn.disabled  = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang lưu…';

    try {
        let res, data;

        if (albumId) {
            /* ── UPDATE ── */
            if (coverFile) {
                const fd = new FormData();
                fd.append('title', title);
                fd.append('description', desc);
                fd.append('cover_image', coverFile);
                res = await fetch(`/api/v1/music/albums/${albumId}/`, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '' },
                    body: fd,
                });
            } else {
                res = await fetch(`/api/v1/music/albums/${albumId}/`, {
                    method: 'PATCH',
                    headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '', 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description: desc }),
                });
            }
            data = await res.json();
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('albumFormModal'))?.hide();
                toast('Đã cập nhật album!', true);
                await loadAlbums();
            } else {
                toast(data.error?.message || 'Có lỗi xảy ra', false);
            }

        } else {
            /* ── CREATE ──
               POST JSON để tạo album, sau đó PATCH cover nếu có.
               Chỉ gọi loadAlbums() 1 lần duy nhất ở cuối.
            */
            res  = await fetch('/api/v1/music/albums/', {
                method: 'POST',
                headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '', 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description: desc }),
            });
            data = await res.json();

            if (data.success) {
                if (coverFile && data.data?.id) {
                    const fd = new FormData();
                    fd.append('cover_image', coverFile);
                    await fetch(`/api/v1/music/albums/${data.data.id}/`, {
                        method: 'POST',
                        headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '' },
                        body: fd,
                    });
                }
                bootstrap.Modal.getInstance(document.getElementById('albumFormModal'))?.hide();
                toast('Đã tạo album mới!', true);
                await loadAlbums();   // gọi 1 lần duy nhất
            } else {
                toast(data.error?.message || 'Có lỗi xảy ra', false);
            }
        }
    } catch (err) {
        console.error(err);
        toast('Lỗi kết nối', false);
    } finally {
        btn.disabled  = false;
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Lưu';
    }
}

/* ══════════════════════════════════════════════
   MODAL: QUẢN LÝ BÀI HÁT
══════════════════════════════════════════════ */
async function openAlbumSongs(albumId) {
    const album = albumCache.get(String(albumId));
    if (!album) return;

    currentAlbumId = albumId;

    document.getElementById('albumSongsTitle').textContent = album.title;
    document.getElementById('albumSongsMeta').innerHTML = '';

    document.getElementById('songSearchInput').value       = '';
    document.getElementById('songSearchResults').innerHTML = '';
    renderStatusActions(album);

    getModal('albumSongsModal').show();

    /* Tải song song */
    await Promise.all([
        loadAlbumSongs(albumId),
        ensureMyPublishedSongs(),
    ]);
}

function renderStatusActions(album) {
    const div = document.getElementById('albumStatusActions');
    if (div) div.innerHTML = ''; // Đã xoá nút Phát hành / Ẩn album theo yêu cầu
}

async function loadAlbumSongs(albumId) {
    const container = document.getElementById('albumSongsListContainer');
    container.innerHTML =
        `<div class="text-center py-3">
            <div class="spinner-border spinner-border-sm" style="color:var(--pm-theme);"></div>
         </div>`;

    try {
        const res  = await fetch(`/api/v1/music/albums/${albumId}/songs/`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error?.message);

        const songs = data.data.items || [];
        document.getElementById('albumSongCount').textContent = `${songs.length} bài`;

        if (songs.length === 0) {
            container.innerHTML =
                `<div class="text-center py-4 text-secondary small">
                    <i class="bi bi-music-note"
                        style="font-size:2rem;opacity:.3;display:block;margin-bottom:.5rem;"></i>
                    Chưa có bài hát nào trong album.
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
                    <button class="btn-rm-song" title="Xoá khỏi album">
                        <i class="bi bi-x-lg" style="font-size:.8rem;"></i>
                    </button>
                </div>`;

            row.querySelector('.btn-rm-song').onclick =
                () => removeSongFromAlbum(albumId, s.id);

            container.appendChild(row);
        });
    } catch (err) {
        container.innerHTML =
            `<div class="text-danger py-3 text-center small">Lỗi tải dữ liệu</div>`;
        console.error('loadAlbumSongs:', err);
    }
}

/* ── Load bài hát published của artist – chỉ gọi 1 lần ── */
async function ensureMyPublishedSongs() {
    if (myPublishedSongs !== null) return;
    try {
        const res  = await fetch(
            `/api/v1/music/songs/?status=published&artist_id=${CURRENT_USER_ID}&limit=200`
        );
        const data = await res.json();
        if (data.success) {
            /* artist.id trong to_dict() là str(self.artist_id) → so sánh string an toàn */
            myPublishedSongs = (data.data.items || []).filter(
                s => s.artist && String(s.artist.id) === String(CURRENT_USER_ID)
            );
        } else {
            myPublishedSongs = [];
        }
    } catch (err) {
        myPublishedSongs = [];
        console.error('ensureMyPublishedSongs:', err);
    }
}

/* ── Debounced search ── */
function debouncedSearch(q) {
    clearTimeout(songSearchTimeout);
    songSearchTimeout = setTimeout(() => searchMySongs(q), 200);
}

function searchMySongs(query) {
    const container = document.getElementById('songSearchResults');
    const q = query.trim().toLowerCase();
    
    currentSearchQuery = q;
    currentSearchPage = 0;
    currentSearchResults = [];
    container.innerHTML = '';

    if (!q) return;

    if (!myPublishedSongs || myPublishedSongs.length === 0) {
        container.innerHTML =
            `<div class="song-row text-secondary" style="font-size:.78rem;">
                Chưa có bài hát nào được phát hành</div>`;
        return;
    }

    currentSearchResults = myPublishedSongs.filter(s => s.title.toLowerCase().includes(q));

    if (currentSearchResults.length === 0) {
        container.innerHTML =
            `<div class="song-row text-secondary" style="font-size:.78rem;">
                Không tìm thấy bài hát</div>`;
        return;
    }

    renderSearchPage();
}

function renderSearchPage() {
    const container = document.getElementById('songSearchResults');
    const start = currentSearchPage * SEARCH_PAGE_SIZE;
    const end = start + SEARCH_PAGE_SIZE;
    const results = currentSearchResults.slice(start, end);
    
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
            </div>
            <i class="bi bi-plus-circle text-white"
                style="font-size:1.1rem;flex-shrink:0;"></i>`;
        row.onclick = () => addSongToAlbum(s.id, s.title);
        container.appendChild(row);
    });
    
    currentSearchPage++;
}

async function addSongToAlbum(songId, songTitle) {
    try {
        const res  = await fetch(`/api/v1/music/albums/${currentAlbumId}/songs/`, {
            method:  'POST',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '', 'Content-Type': 'application/json' },
            body:    JSON.stringify({ song_id: songId }),
        });
        const data = await res.json();
        if (data.success) {
            toast(`Đã thêm "${songTitle}" vào album!`, true);
            document.getElementById('songSearchInput').value       = '';
            document.getElementById('songSearchResults').innerHTML = '';
            await loadAlbumSongs(currentAlbumId);
            await loadAlbums();
            // Đồng bộ status actions sau khi cache được reload
            const updated = albumCache.get(String(currentAlbumId));
            if (updated) renderStatusActions(updated);
        } else {
            toast(data.error?.message || 'Không thể thêm bài hát', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    }
}

async function removeSongFromAlbum(albumId, songId) {
    try {
        const res  = await fetch(`/api/v1/music/albums/${albumId}/songs/${songId}/`, {
            method:  'DELETE',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '' },
        });
        const data = await res.json();
        if (data.success) {
            toast('Đã xoá bài hát khỏi album', true);
            await loadAlbumSongs(albumId);
            await loadAlbums();
        } else {
            toast(data.error?.message || 'Không thể xoá', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    }
}

/* ══════════════════════════════════════════════
   PUBLISH / UNPUBLISH
══════════════════════════════════════════════ */
async function publishAlbum(albumId, source = null)   { await changeAlbumStatus(albumId, 'publish', source); }
async function unpublishAlbum(albumId, source = null) { await changeAlbumStatus(albumId, 'unpublish', source); }

async function changeAlbumStatus(albumId, action, source) {
    try {
        const res  = await fetch(`/api/v1/music/albums/${albumId}/${action}/`, {
            method:  'POST',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '', 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        if (data.success) {
            toast(action === 'publish' ? 'Album đã được phát hành! 🚀' : 'Đã ẩn album', true);
            if (source === 'edit') {
                bootstrap.Modal.getInstance(document.getElementById('albumFormModal'))?.hide();
            } else {
                bootstrap.Modal.getInstance(document.getElementById('albumSongsModal'))?.hide();
            }
            await loadAlbums();
        } else {
            toast(data.error?.message || 'Có lỗi xảy ra', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    }
}

/* ══════════════════════════════════════════════
   EDIT (từ songs modal)
══════════════════════════════════════════════ */
function openEditModal() {
    if (!currentAlbumId) return;
    bootstrap.Modal.getInstance(document.getElementById('albumSongsModal'))?.hide();
    setTimeout(() => openEditAlbum(currentAlbumId), 280);
}

/* ══════════════════════════════════════════════
   DELETE ALBUM
══════════════════════════════════════════════ */
function askDeleteAlbum(albumId) {
    const album = albumCache.get(String(albumId));
    if (!album) return;
    deleteTargetId = albumId;
    document.getElementById('deleteAlbumName').textContent = album.title;
    getModal('deleteAlbumModal').show();
}

async function confirmDeleteAlbum() {
    if (!deleteTargetId) return;
    const btn = document.getElementById('confirmDeleteBtn');
    btn.disabled    = true;
    btn.textContent = 'Đang xoá…';
    try {
        const res  = await fetch(`/api/v1/music/albums/${deleteTargetId}/`, {
            method:  'DELETE',
            headers: { 'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '' },
        });
        const data = await res.json();
        if (data.success) {
            toast('Đã xoá album', true);
            bootstrap.Modal.getInstance(document.getElementById('deleteAlbumModal'))?.hide();
            await loadAlbums();
        } else {
            toast(data.error?.message || 'Không thể xoá album', false);
        }
    } catch (err) {
        toast('Lỗi kết nối', false);
    } finally {
        btn.disabled    = false;
        btn.textContent = 'Xoá';
        deleteTargetId  = null;
    }
}

/* ══════════════════════════════════════════════
   INIT
══════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    /* Preview cover khi chọn file */
    document.getElementById('albumCoverInput')?.addEventListener('change', e => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = ev => setCover(ev.target.result);
        reader.readAsDataURL(file);
    });

    /* Đóng tất cả dropdown khi click bên ngoài card */
    document.addEventListener('click', closeAllMenus);

    /* Scroll pagination */
    const handleScroll = function(e) {
        const target = e.target;
        if (target && target.classList && target.classList.contains('content-scroll')) {
            if (target.scrollHeight - target.scrollTop <= target.clientHeight + 150) {
                loadAlbums(false);
            }
        }
    };
    
    document.addEventListener('scroll', handleScroll, true);

    const searchResultsContainer = document.getElementById('songSearchResults');
    if (searchResultsContainer) {
        searchResultsContainer.addEventListener('scroll', function() {
            if (this.scrollHeight - this.scrollTop <= this.clientHeight + 20) {
                if (currentSearchPage * SEARCH_PAGE_SIZE < currentSearchResults.length) {
                    renderSearchPage();
                }
            }
        });
    }

    if (IS_ARTIST) loadAlbums(true);
});
