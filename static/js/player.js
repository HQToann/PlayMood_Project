// static/js/player.js
// Global audio player logic for PlayMood — Full Featured

const globalAudio = new Audio();
let currentSongId = null;
let isPlaying = false;
let isShuffle = false;
let repeatMode = 0; // 0=off, 1=repeat-one, 2=repeat-all
let playHistory = []; // Lịch sử bài đã phát

// DOM Elements
let pbCover, pbTitle, pbArtist, pbPlayBtn, pbPlayIcon;
let pbCurrentTime, pbDuration, pbProgressBg, pbProgressFill;
let pbMuteBtn, pbMuteIcon, pbVolumeBg, pbVolumeFill;
let pbHeartBtn, pbHeartIcon;
let pbShuffleBtn, pbPrevBtn, pbNextBtn, pbRepeatBtn, pbRepeatIcon;
let pbLyricsBtn;

document.addEventListener('DOMContentLoaded', () => {
    pbCover       = document.getElementById('pbCover');
    pbTitle       = document.getElementById('pbTitle');
    pbArtist      = document.getElementById('pbArtist');
    pbPlayBtn     = document.getElementById('pbPlayBtn');
    pbPlayIcon    = document.getElementById('pbPlayIcon');
    pbCurrentTime = document.getElementById('pbCurrentTime');
    pbDuration    = document.getElementById('pbDuration');
    pbProgressBg  = document.getElementById('pbProgressBg');
    pbProgressFill= document.getElementById('pbProgressFill');
    pbMuteBtn     = document.getElementById('pbMuteBtn');
    pbMuteIcon    = document.getElementById('pbMuteIcon');
    pbVolumeBg    = document.getElementById('pbVolumeBg');
    pbVolumeFill  = document.getElementById('pbVolumeFill');
    pbHeartBtn    = document.getElementById('pbHeartBtn');
    pbHeartIcon   = document.getElementById('pbHeartIcon');
    pbShuffleBtn  = document.getElementById('pbShuffleBtn');
    pbPrevBtn     = document.getElementById('pbPrevBtn');
    pbNextBtn     = document.getElementById('pbNextBtn');
    pbRepeatBtn   = document.getElementById('pbRepeatBtn');
    pbRepeatIcon  = document.getElementById('pbRepeatIcon');
    pbLyricsBtn   = document.getElementById('pbLyricsBtn');

    if (!pbPlayBtn) return; // Player bar not on this page

    // ── Play/Pause ──
    pbPlayBtn.addEventListener('click', () => {
        if (!currentSongId && globalAudio.src === '') return;
        togglePlay();
    });

    let isDraggingProgress = false;
    let isDraggingVolume = false;
    let dragProgressPercent = 0;

    // ── Progress: time update ──
    globalAudio.addEventListener('timeupdate', () => {
        if (isNaN(globalAudio.duration) || isDraggingProgress) return;
        const pct = (globalAudio.currentTime / globalAudio.duration) * 100;
        pbProgressFill.style.width = `${pct}%`;
        pbCurrentTime.textContent  = formatTime(globalAudio.currentTime);
    });

    // ── Duration loaded ──
    globalAudio.addEventListener('loadedmetadata', () => {
        pbDuration.textContent = formatTime(globalAudio.duration);
    });

    // ── Song ended → play next or repeat ──
    globalAudio.addEventListener('ended', () => {
        pbProgressFill.style.width = '0%';
        pbCurrentTime.textContent  = '0:00';

        if (repeatMode === 1) {
            // Repeat-one: phát lại bài hiện tại
            globalAudio.currentTime = 0;
            globalAudio.play();
            isPlaying = true;
            updatePlayIcon();
        } else {
            isPlaying = false;
            updatePlayIcon();
            playNext();
        }
    });

    // ── Seek (Drag) ──
    pbProgressBg.addEventListener('mousedown', (e) => {
        isDraggingProgress = true;
        updateProgressDrag(e);
    });

    function updateProgressDrag(e) {
        const rect = pbProgressBg.getBoundingClientRect();
        dragProgressPercent = (e.clientX - rect.left) / rect.width;
        dragProgressPercent = Math.max(0, Math.min(1, dragProgressPercent));
        
        pbProgressFill.style.width = (dragProgressPercent * 100) + '%';
        if (globalAudio.duration) {
            pbCurrentTime.textContent = formatTime(dragProgressPercent * globalAudio.duration);
        }
    }

    // ── Volume (Drag) ──
    pbVolumeBg.addEventListener('mousedown', (e) => {
        isDraggingVolume = true;
        updateVolumeDrag(e);
    });

    function updateVolumeDrag(e) {
        const rect = pbVolumeBg.getBoundingClientRect();
        let percent = (e.clientX - rect.left) / rect.width;
        percent = Math.max(0, Math.min(1, percent));
        globalAudio.volume = percent;
        updateVolumeUI();
    }

    // Lắng nghe chuột toàn màn hình để kéo mượt
    document.addEventListener('mousemove', (e) => {
        if (isDraggingProgress) updateProgressDrag(e);
        if (isDraggingVolume) updateVolumeDrag(e);
    });

    document.addEventListener('mouseup', () => {
        if (isDraggingProgress) {
            isDraggingProgress = false;
            if (globalAudio.duration) {
                globalAudio.currentTime = dragProgressPercent * globalAudio.duration;
            }
        }
        isDraggingVolume = false;
    });

    // ── Mute ──
    pbMuteBtn.addEventListener('click', () => {
        globalAudio.muted = !globalAudio.muted;
        updateVolumeUI();
    });

    // ── Like/Heart ──
    if (pbHeartBtn) {
        pbHeartBtn.addEventListener('click', toggleLike);
    }

    // ── Shuffle ──
    if (pbShuffleBtn) {
        pbShuffleBtn.addEventListener('click', () => {
            isShuffle = !isShuffle;
            pbShuffleBtn.style.color = isShuffle ? 'var(--accent-color)' : '';
            pbShuffleBtn.title = isShuffle ? 'Tắt phát ngẫu nhiên' : 'Phát ngẫu nhiên';
        });
    }

    // ── Repeat ──
    if (pbRepeatBtn) {
        pbRepeatBtn.addEventListener('click', () => {
            repeatMode = (repeatMode + 1) % 3;
            updateRepeatUI();
        });
    }

    // ── Previous ──
    if (pbPrevBtn) {
        pbPrevBtn.addEventListener('click', playPrev);
    }

    // ── Lyrics ──
    let isLyricsOpen = false;
    window.toggleLyricsPanel = function() {
        const panel = document.getElementById('lyricsPanel');
        if (!panel) return;
        isLyricsOpen = !isLyricsOpen;
        if (isLyricsOpen) {
            panel.style.top = '0'; // Slide up
            if (pbLyricsBtn) {
                pbLyricsBtn.style.color = 'var(--accent-color)';
            }
        } else {
            panel.style.top = '100vh'; // Slide down
            if (pbLyricsBtn) {
                pbLyricsBtn.style.color = '';
            }
        }
    };
    if (pbLyricsBtn) {
        pbLyricsBtn.addEventListener('click', toggleLyricsPanel);
    }

    // ── Devices ──
    let isDevicePanelOpen = false;
    window.toggleDevicePanel = function() {
        const panel = document.getElementById('devicePanel');
        const wrapper = document.getElementById('devicePanelWrapper');
        const btn = document.getElementById('pbDeviceBtn');
        if (!panel || !wrapper) return;
        
        isDevicePanelOpen = !isDevicePanelOpen;
        if (isDevicePanelOpen) {
            panel.style.transform = 'translateY(0)';
            wrapper.style.pointerEvents = 'all';
            if (btn) btn.style.color = 'var(--accent-color)';
            
            // Close queue panel if open
            if (typeof hideQueuePanel === 'function') {
                hideQueuePanel();
            }
            
            fetchDevices();
        } else {
            panel.style.transform = 'translateY(calc(100% + 50px))';
            wrapper.style.pointerEvents = 'none';
            if (btn) btn.style.color = '';
        }
    };
    
    // Define hideDevicePanel globally so other panels can close it
    window.hideDevicePanel = function() {
        const panel = document.getElementById('devicePanel');
        const wrapper = document.getElementById('devicePanelWrapper');
        const btn = document.getElementById('pbDeviceBtn');
        if (!panel || !wrapper) return;
        panel.style.transform = 'translateY(calc(100% + 50px))';
        wrapper.style.pointerEvents = 'none';
        if (btn) btn.style.color = '';
        isDevicePanelOpen = false;
    };

    async function fetchDevices() {
        const listEl = document.getElementById('deviceList');
        if (!listEl) return;
        
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
            listEl.innerHTML = '<div style="color: #ff6b6b; font-size: 0.85rem; padding: 8px;">Trình duyệt không hỗ trợ chọn thiết bị.</div>';
            return;
        }

        try {
            // Request permission first (required in some browsers to get device names)
            await navigator.mediaDevices.getUserMedia({ audio: true });
            
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioOutputs = devices.filter(d => d.kind === 'audiooutput');
            
            if (audioOutputs.length === 0) {
                listEl.innerHTML = '<div style="color: rgba(255,255,255,0.7); font-size: 0.85rem; padding: 8px;">Không tìm thấy thiết bị nào.</div>';
                return;
            }

            let html = '';
            audioOutputs.forEach(device => {
                // If it doesn't have a label, it usually means permissions were denied, but we tried.
                const label = device.label || `Thiết bị đầu ra (id: ${device.deviceId.slice(0, 5)}...)`;
                // globalAudio.sinkId holds the current device ID (if supported)
                const isActive = (globalAudio.sinkId === device.deviceId) || (!globalAudio.sinkId && device.deviceId === 'default');
                
                html += `
                    <div onclick="window.setAudioDevice('${device.deviceId}')" style="
                        display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 6px; cursor: pointer;
                        background: ${isActive ? 'rgba(255,255,255,0.1)' : 'transparent'};
                        transition: background 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.15)'" onmouseout="this.style.background='${isActive ? 'rgba(255,255,255,0.1)' : 'transparent'}'">
                        <i class="bi bi-${device.deviceId === 'default' ? 'laptop' : (label.toLowerCase().includes('head') ? 'headphones' : 'speaker')}" style="color: ${isActive ? 'var(--accent-color)' : 'white'}; font-size: 1.2rem;"></i>
                        <div style="flex: 1; min-width: 0;">
                            <div style="color: ${isActive ? 'var(--accent-color)' : 'white'}; font-size: 0.9rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${label}</div>
                        </div>
                        ${isActive ? '<i class="bi bi-check" style="color: var(--accent-color); font-size: 1.2rem;"></i>' : ''}
                    </div>
                `;
            });
            listEl.innerHTML = html;
        } catch (err) {
            console.error('Error fetching devices:', err);
            listEl.innerHTML = '<div style="color: rgba(255,255,255,0.7); font-size: 0.85rem; padding: 8px;">Vui lòng cấp quyền Micro để xem tên thiết bị.</div>';
        }
    }

    window.setAudioDevice = async function(deviceId) {
        if (typeof globalAudio.setSinkId !== 'undefined') {
            try {
                await globalAudio.setSinkId(deviceId);
                fetchDevices(); // Re-render to show active checkmark
                if (window.showToast) window.showToast('Đã chuyển đổi thiết bị âm thanh', 'success');
            } catch (error) {
                console.error('Lỗi khi đổi thiết bị:', error);
                if (window.showToast) window.showToast('Không thể kết nối với thiết bị này', 'error');
            }
        } else {
            console.warn('Browser does not support setSinkId');
            if (window.showToast) window.showToast('Trình duyệt của bạn không hỗ trợ tính năng này', 'info');
        }
    };

    // ── Init ──
    globalAudio.volume = 1.0;
    updateVolumeUI();
});

// ─────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────
function formatTime(s) {
    if (isNaN(s)) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec < 10 ? '0' : ''}${sec}`;
}

function getCsrf() {
    return typeof getCookie === 'function' ? getCookie('csrftoken') : '';
}

// ─────────────────────────────────────────────
// UI Updates
// ─────────────────────────────────────────────
function updatePlayIcon() {
    if (pbPlayIcon) {
        if (isPlaying) {
            pbPlayIcon.classList.remove('bi-play-fill', 'ms-1');
            pbPlayIcon.classList.add('bi-pause-fill');
        } else {
            pbPlayIcon.classList.remove('bi-pause-fill');
            pbPlayIcon.classList.add('bi-play-fill', 'ms-1');
        }
    }
    const detailPlayIcon = document.getElementById('detail-play-icon');
    if (detailPlayIcon) {
        const pid = new URLSearchParams(window.location.search).get('id');
        if (pid === currentSongId && isPlaying) {
            detailPlayIcon.classList.replace('bi-play-fill', 'bi-pause-fill');
            detailPlayIcon.style.marginLeft = '0';
        } else {
            detailPlayIcon.classList.replace('bi-pause-fill', 'bi-play-fill');
            detailPlayIcon.style.marginLeft = '2px';
        }
    }
}

function updateVolumeUI() {
    if (!pbMuteIcon || !pbVolumeFill) return;
    if (globalAudio.muted || globalAudio.volume === 0) {
        pbMuteIcon.className = 'bi bi-volume-mute';
        pbVolumeFill.style.width = '0%';
    } else {
        pbMuteIcon.className = globalAudio.volume < 0.5 ? 'bi bi-volume-down' : 'bi bi-volume-up';
        pbVolumeFill.style.width = `${globalAudio.volume * 100}%`;
    }
}

function updateRepeatUI() {
    if (!pbRepeatIcon) return;
    if (repeatMode === 0) {
        pbRepeatIcon.className = 'bi bi-repeat fs-6';
        pbRepeatBtn.style.color = '';
        pbRepeatBtn.title = 'Lặp lại';
    } else if (repeatMode === 1) {
        pbRepeatIcon.className = 'bi bi-repeat-1 fs-6';
        pbRepeatBtn.style.color = 'var(--accent-color)';
        pbRepeatBtn.title = 'Lặp lại bài hiện tại';
    } else {
        pbRepeatIcon.className = 'bi bi-repeat fs-6';
        pbRepeatBtn.style.color = 'var(--accent-color)';
        pbRepeatBtn.title = 'Lặp lại danh sách';
    }
}

function updateHeartUI(liked) {
    if (!pbHeartIcon) return;
    if (liked) {
        pbHeartIcon.className = 'bi bi-heart-fill';
        pbHeartIcon.style.color = 'var(--accent-color)';
    } else {
        pbHeartIcon.className = 'bi bi-heart';
        pbHeartIcon.style.color = '';
    }
}

// ─────────────────────────────────────────────
// Play Controls
// ─────────────────────────────────────────────
function togglePlay() {
    if (isPlaying) {
        globalAudio.pause();
    } else {
        globalAudio.play();
    }
    isPlaying = !isPlaying;
    updatePlayIcon();
}

function playNext() {
    // Lấy queue từ biến global _songQueue (định nghĩa trong player_bar.html)
    const queue = window._songQueue || [];
    if (queue.length === 0) {
        if (repeatMode === 2 && playHistory.length > 0) {
            // Repeat-all: quay lại từ đầu history
            window.playSong(playHistory[0]);
        }
        return;
    }

    let nextSong;
    if (isShuffle) {
        const idx = Math.floor(Math.random() * queue.length);
        nextSong = queue[idx];
    } else {
        nextSong = queue[0];
    }

    // Xoá bài khỏi queue sau khi phát
    if (window.removeFromQueue) window.removeFromQueue(nextSong.id);
    window.playSong(nextSong.id);
}

function playPrev() {
    // Phát bài trước trong history
    if (globalAudio.currentTime > 3) {
        // Nếu đã qua 3s, restart bài hiện tại
        globalAudio.currentTime = 0;
        return;
    }
    if (playHistory.length >= 2) {
        const prevId = playHistory[playHistory.length - 2];
        playHistory.pop(); // xoá bài hiện tại
        window.playSong(prevId, null, true); // true = from history, không thêm vào history lại
    }
}

// ─────────────────────────────────────────────
// Like
// ─────────────────────────────────────────────
let _isLiked = false; // Trạng thái like hiện tại

async function toggleLike() {
    if (!currentSongId) return;

    // Optimistic UI: đổi ngay trước khi gọi API
    _isLiked = !_isLiked;
    updateHeartUI(_isLiked);

    try {
        const res  = await fetch(`/api/v1/music/songs/${currentSongId}/like/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // Đồng bộ với giá trị thực từ server
            const serverLiked = data.data.is_liked ?? data.data.liked ?? _isLiked;
            _isLiked = serverLiked;
            updateHeartUI(_isLiked);
            if (window.showToast) window.showToast(
                _isLiked ? 'Đã thêm vào yêu thích ❤️' : 'Đã bỏ yêu thích',
                _isLiked ? 'success' : 'info'
            );
        } else {
            // Revert nếu API lỗi
            _isLiked = !_isLiked;
            updateHeartUI(_isLiked);
        }
    } catch (e) {
        console.error('Like error:', e);
        _isLiked = !_isLiked;
        updateHeartUI(_isLiked);
    }
}

// ─────────────────────────────────────────────
// Main playSong function
// ─────────────────────────────────────────────
window.playSong = async function(songId, event, fromHistory = false) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    // Same song → toggle
    if (currentSongId === String(songId)) {
        togglePlay();
        return;
    }

    try {
        const res  = await fetch(`/api/v1/music/songs/${songId}/`);
        const data = await res.json();

        if (!data.success) {
            if (window.showToast) window.showToast(data.error || 'Lỗi lấy bài hát', 'error');
            return;
        }

        const song = data.data;

        if (!song.audio_file) {
            if (!window.CURRENT_USER_AUTHENTICATED) {
                window.location.href = window.LOGIN_URL || '/auth/login/';
                return;
            }
            if (window.showToast) window.showToast('Bài hát chưa có file audio', 'error');
            return;
        }

        // Update player bar UI
        if (pbTitle)  pbTitle.textContent  = song.title;
        if (pbArtist) pbArtist.textContent = song.artist ? song.artist.display_name : 'Unknown';
        if (pbCover && song.cover_image) pbCover.src = song.cover_image;
        
        // Remove idle state
        const playerBar = document.getElementById('globalPlayerBar');
        if (playerBar) playerBar.classList.remove('pb-idle');

        // Reset heart
        _isLiked = song.is_liked || false;
        updateHeartUI(_isLiked);

        // Update Lyrics
        const lyricsContent = document.getElementById('lyricsContentText');
        if (lyricsContent) {
            if (song.lyrics && song.lyrics.trim() !== '') {
                lyricsContent.textContent = song.lyrics;
                lyricsContent.style.textAlign = 'left';
            } else {
                lyricsContent.textContent = 'Trông có vẻ như bài hát này chưa có lời...';
                lyricsContent.style.textAlign = 'center';
            }
        }

        // Play
        globalAudio.src = song.audio_file;
        await globalAudio.play();
        currentSongId = String(songId);
        isPlaying = true;
        updatePlayIcon();

        // History
        if (!fromHistory) {
            if (playHistory[playHistory.length - 1] !== String(songId)) {
                playHistory.push(String(songId));
                if (playHistory.length > 50) playHistory.shift(); // Giới hạn 50 bài
            }
        }

        // Record play
        fetch(`/api/v1/music/songs/${songId}/play/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' }
        })
        .then(r => r.json())
        .then(pd => {
            if (pd.success) {
                const pid = new URLSearchParams(window.location.search).get('id');
                if (pid === String(songId)) {
                    const el = document.getElementById('detail-plays');
                    if (el && pd.data.play_count !== undefined) {
                        el.textContent = `${Number(pd.data.play_count).toLocaleString('vi-VN')} lượt nghe`;
                    }
                }
            }
        })
        .catch(e => console.error('Play record error:', e));

    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast('Lỗi mạng', 'error');
    }
};

window.playPlaylist = async function(playlistId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    try {
        const res = await fetch(`/api/v1/playlists/${playlistId}/songs/?page_size=100`);
        const data = await res.json();
        if (data.success && data.data && data.data.items && data.data.items.length > 0) {
            const songs = data.data.items.map(item => item.song);
            window._songQueue = songs;
            window.playSong(songs[0].id, null, false);
        } else {
            if (window.showToast) window.showToast('Playlist này chưa có bài hát nào', 'info');
        }
    } catch (e) {
        console.error('Lỗi phát playlist:', e);
        if (window.showToast) window.showToast('Lỗi khi phát playlist', 'error');
    }
};

// ─────────────────────────────────────────────
// Queue Panel Logic
// ─────────────────────────────────────────────
window._queueVisible = false;
window._songQueue = []; // Mảng lưu danh sách chờ

window.toggleQueuePanel = function() {
    var panel = document.getElementById('queuePanel');
    var wrapper = document.getElementById('queuePanelWrapper');
    var btn = document.querySelector('button[onclick="toggleQueuePanel()"]');
    if (!panel) return;
    
    window._queueVisible = !window._queueVisible;
    if (window._queueVisible) {
        panel.style.transform = 'translateY(0)';
        wrapper.style.pointerEvents = 'all';
        if (btn) btn.style.color = 'var(--accent-color)';
        
        // Close device panel if open
        if (typeof window.hideDevicePanel === 'function') {
            window.hideDevicePanel();
        }
        
        renderQueue();
    } else {
        hideQueuePanel();
    }
}

window.showQueuePanel = function() {
    var panel = document.getElementById('queuePanel');
    var wrapper = document.getElementById('queuePanelWrapper');
    var btn = document.querySelector('button[onclick="toggleQueuePanel()"]');
    if (!panel) return;
    panel.style.transform = 'translateY(0)';
    wrapper.style.pointerEvents = 'all';
    window._queueVisible = true;
    if (btn) btn.style.color = 'var(--accent-color)';
    
    // Close device panel if open
    if (typeof window.hideDevicePanel === 'function') {
        window.hideDevicePanel();
    }
}

window.hideQueuePanel = function() {
    var panel = document.getElementById('queuePanel');
    var wrapper = document.getElementById('queuePanelWrapper');
    var btn = document.querySelector('button[onclick="toggleQueuePanel()"]');
    if (!panel) return;
    panel.style.transform = 'translateY(calc(100% + 50px))';
    wrapper.style.pointerEvents = 'none';
    window._queueVisible = false;
    if (btn) btn.style.color = '';
}

// Thêm bài hát vào danh sách chờ
window.addToQueue = function(songId, title, artist, cover) {
    // Tránh trùng lặp
    if (window._songQueue.find(s => s.id === songId)) {
        if (typeof showToast === 'function') showToast('Bài hát đã có trong danh sách chờ', 'info');
        return;
    }
    window._songQueue.push({ id: songId, title: title, artist: artist, cover: cover });
    renderQueue();
    window.showQueuePanel(); // Tự động mở panel
    if (typeof showToast === 'function') showToast(`Đã thêm "${title}" vào danh sách chờ`, 'success');
};

// Xoá bài khỏi queue
window.removeFromQueue = function(songId) {
    window._songQueue = window._songQueue.filter(s => s.id !== songId);
    renderQueue();
};

// Render danh sách chờ vào panel
function renderQueue() {
    var body = document.getElementById('queuePanelBody');
    if (!body) return;

    if (window._songQueue.length === 0) {
        body.innerHTML = `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:rgba(255,255,255,0.35); text-align:center;">
                <i class="bi bi-music-note-list" style="font-size:2.5rem; margin-bottom:12px;"></i>
                <p style="font-size:0.9rem; margin-bottom:6px; color:rgba(255,255,255,0.5);">Danh sách chờ đang trống</p>
                <p style="font-size:0.8rem; margin:0;">Chọn một bài hát để bắt đầu</p>
            </div>`;
        return;
    }

    var html = `<p style="font-size:0.75rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-bottom:12px;">Tiếp theo (${window._songQueue.length})</p>`;
    window._songQueue.forEach((song, index) => {
        html += `
            <div style="display:flex; align-items:center; gap:10px; padding:8px 6px; border-radius:8px; cursor:pointer; transition:background 0.15s;" 
                 onmouseover="this.style.background='rgba(255,255,255,0.06)'" 
                 onmouseout="this.style.background='transparent'"
                 onclick="window.playSong && window.playSong('${song.id}')">
                <img src="${song.cover}" alt="" style="width:40px; height:40px; border-radius:6px; object-fit:cover; flex-shrink:0;">
                <div style="flex:1; min-width:0;">
                    <div style="font-size:0.875rem; font-weight:600; color:white; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${song.title}</div>
                    <div style="font-size:0.75rem; color:rgba(255,255,255,0.45); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${song.artist}</div>
                </div>
                <button onclick="event.stopPropagation(); window.removeFromQueue('${song.id}')" 
                        style="background:none; border:none; color:rgba(255,255,255,0.3); cursor:pointer; padding:4px; border-radius:4px; transition:color 0.15s; flex-shrink:0;"
                        onmouseover="this.style.color='rgba(255,80,80,0.8)'" onmouseout="this.style.color='rgba(255,255,255,0.3)'"
                        title="Xoá khỏi danh sách chờ">
                    <i class="bi bi-x-lg" style="font-size:0.8rem;"></i>
                </button>
            </div>`;
    });
    body.innerHTML = html;
}
