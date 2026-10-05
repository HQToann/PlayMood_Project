// static/js/player.js
// window.globalAudio được tạo một lần duy nhất để âm thanh không bị ngắt khi navigate
window.globalAudio = window.globalAudio || new Audio();
var globalAudio = window.globalAudio;

var currentSongId = null;
var isPlaying = false;
var isShuffle = localStorage.getItem("pm_shuffle") === "true";
// ─────────────────────────────────────────────
// Khởi tạo queueNext
// ─────────────────────────────────────────────
window.queueNext = async function(songId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Nếu dropdown menu đang mở thì đóng lại
    if (event && event.target) {
        const menu = event.target.closest('.custom-dropdown-menu');
        if (menu) menu.style.display = 'none';
    }

    try {
        const res = await fetch(`/api/v1/music/songs/${songId}/`);
        const data = await res.json();
        if (data.success && data.data) {
            const s = data.data;
            const artistName = s.artist ? (s.artist.display_name || s.artist.username || 'Unknown') : 'Unknown';
            
            // Nếu _songQueue chưa có, khởi tạo
            if (typeof window._songQueue === 'undefined') window._songQueue = [];
            
            // Xoá bài này nếu nó đã nằm sẵn trong danh sách chờ (để đưa lên đầu)
            window._songQueue = window._songQueue.filter(q => String(q.id) !== String(s.id));
            
            // Chèn vào đầu danh sách chờ
            window._songQueue.unshift({
                id: String(s.id),
                title: s.title || 'Unknown',
                artist: artistName,
                cover: s.cover_image || '',
                context: 'Phát tiếp theo'
            });
            
            localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
            localStorage.setItem('pm_saved_at', Date.now());
            
            // Nếu chưa có bài nào đang phát, phát luôn bài này
            if (!globalAudio.src && !currentSongId) {
                window.playSong(s.id);
            } else {
                if (typeof renderQueue === 'function') renderQueue();
                if (window.showToast) window.showToast('Đã thêm vào danh sách chờ', 'success');
            }
        }
    } catch(e) {
        console.error('queueNext error:', e);
        if (window.showToast) window.showToast('Lỗi kết nối', 'error');
    }
};

var repeatMode = parseInt(localStorage.getItem("pm_repeat")) || 0; // 0=off, 1=repeat-one, 2=repeat-all
var playHistory = []; // Lịch sử bài đã phát
try {
    var phStr = localStorage.getItem('pm_history');
    if (phStr) playHistory = JSON.parse(phStr);
} catch (e) { }

// DOM Elements
var pbCover, pbTitle, pbArtist, pbPlayBtn, pbPlayIcon;
var pbCurrentTime, pbDuration, pbProgressBg, pbProgressFill;
var pbMuteBtn, pbMuteIcon, pbVolumeBg, pbVolumeFill;
var pbHeartBtn, pbHeartIcon;
var pbShuffleBtn, pbPrevBtn, pbNextBtn, pbRepeatBtn, pbRepeatIcon;
var pbLyricsBtn;

document.addEventListener('DOMContentLoaded', () => {
    pbCover = document.getElementById('pbCover');
    pbTitle = document.getElementById('pbTitle');
    pbArtist = document.getElementById('pbArtist');
    pbPlayBtn = document.getElementById('pbPlayBtn');
    pbPlayIcon = document.getElementById('pbPlayIcon');
    pbCurrentTime = document.getElementById('pbCurrentTime');
    pbDuration = document.getElementById('pbDuration');
    pbProgressBg = document.getElementById('pbProgressBg');
    pbProgressFill = document.getElementById('pbProgressFill');
    pbMuteBtn = document.getElementById('pbMuteBtn');
    pbMuteIcon = document.getElementById('pbMuteIcon');
    pbVolumeBg = document.getElementById('pbVolumeBg');
    pbVolumeFill = document.getElementById('pbVolumeFill');
    pbHeartBtn = document.getElementById('pbHeartBtn');
    pbHeartIcon = document.getElementById('pbHeartIcon');
    pbShuffleBtn = document.getElementById('pbShuffleBtn');
    pbPrevBtn = document.getElementById('pbPrevBtn');
    pbNextBtn = document.getElementById('pbNextBtn');
    pbRepeatBtn = document.getElementById('pbRepeatBtn');
    pbRepeatIcon = document.getElementById('pbRepeatIcon');
    pbLyricsBtn = document.getElementById('pbLyricsBtn');

    if (!pbPlayBtn) return; // Player bar not on this page

    // Restore volume and mute from localStorage
    const savedVolume = localStorage.getItem("pm_volume");
    if (savedVolume !== null) {
        globalAudio.volume = parseFloat(savedVolume);
    }
    const savedMute = localStorage.getItem("pm_mute");
    if (savedMute === "true") {
        globalAudio.muted = true;
    }

    // Check expiry (e.g. 12 hours)
    const savedAt = parseInt(localStorage.getItem('pm_saved_at')) || 0;
    const isExpired = (Date.now() - savedAt) > 12 * 60 * 60 * 1000;

    if (isExpired) {
        localStorage.removeItem('pm_last_song');
        localStorage.removeItem('pm_history');
        localStorage.removeItem('pm_queue');
        localStorage.removeItem('pm_last_time');
        playHistory = [];
        window._songQueue = [];
    }

    // --- Restore last played song ---
    const lastSongStr = localStorage.getItem('pm_last_song');
    if (lastSongStr) {
        try {
            const song = JSON.parse(lastSongStr);
            currentSongId = String(song.id);
            if (pbTitle) pbTitle.textContent = song.title;
            if (pbArtist) pbArtist.textContent = song.artist ? (song.artist.display_name || song.artist.username || 'Unknown') : 'Unknown';
            if (pbCover && song.cover_image) pbCover.src = song.cover_image;

            const playerBar = document.getElementById('globalPlayerBar');
            if (playerBar) playerBar.classList.remove('pb-idle');

            if (song.audio_file) {
                globalAudio.src = song.audio_file;
            }

            // Restore current time if available
            const savedTime = localStorage.getItem('pm_last_time');
            if (savedTime) {
                globalAudio.currentTime = parseFloat(savedTime);
                // We use setTimeout so that formatTime is defined before we call it
                setTimeout(() => {
                    if (pbCurrentTime && typeof formatTime === 'function') pbCurrentTime.textContent = formatTime(parseFloat(savedTime));
                }, 100);
            }

            // Restore lyrics
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

            // Note: _isLiked is restored when clicking heart, but to restore UI correctly:
            setTimeout(() => {
                if (typeof updateHeartUI === 'function') updateHeartUI(song.is_liked || false);
                if (typeof updatePlayIcon === 'function') updatePlayIcon();
            }, 100);
        } catch (e) {
            console.error('Error restoring last song', e);
        }
    }

    // Restore shuffle UI
    if (isShuffle && pbShuffleBtn) {
        pbShuffleBtn.style.color = 'var(--accent-color)';
        pbShuffleBtn.title = 'Tắt phát ngẫu nhiên';
    }

    // ── Play/Pause ──
    pbPlayBtn.addEventListener('click', () => {
        if (!currentSongId && globalAudio.src === '') {
            // Lần đầu vào hoặc không có lịch sử -> phát bài hát gợi ý
            if (typeof playNext === 'function') playNext();
            return;
        }
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
        pbCurrentTime.textContent = formatTime(globalAudio.currentTime);
        localStorage.setItem('pm_last_time', globalAudio.currentTime);
    });

    // ── Duration loaded ──
    globalAudio.addEventListener('loadedmetadata', () => {
        pbDuration.textContent = formatTime(globalAudio.duration);
    });

    // ── Song ended → play next or repeat ──
    globalAudio.addEventListener('ended', () => {
        pbProgressFill.style.width = '0%';
        pbCurrentTime.textContent = '0:00';

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
        localStorage.setItem("pm_volume", percent);
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
        localStorage.setItem("pm_mute", globalAudio.muted);
        updateVolumeUI();
    });

    // ── Like/Heart ──
    if (pbHeartBtn) {
        pbHeartBtn.addEventListener('click', toggleLike);
    }

    if (pbShuffleBtn) {
        pbShuffleBtn.addEventListener('click', () => {
            isShuffle = !isShuffle;
            localStorage.setItem("pm_shuffle", isShuffle);
            pbShuffleBtn.style.color = isShuffle ? 'var(--accent-color)' : '';
            pbShuffleBtn.title = isShuffle ? 'Tắt phát ngẫu nhiên' : 'Phát ngẫu nhiên';
            
            // Xáo trộn queue hiện tại nếu bật shuffle
            if (isShuffle && window._songQueue && window._songQueue.length > 0) {
                // Tách riêng từng nhóm context để xáo trộn (tuỳ chọn), hoặc xáo trộn tất cả
                for (let i = window._songQueue.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [window._songQueue[i], window._songQueue[j]] = [window._songQueue[j], window._songQueue[i]];
                }
                localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
            localStorage.setItem('pm_saved_at', Date.now());
                if (typeof renderQueue === 'function') renderQueue();
            }
        });
    }

    // ── Repeat ──
    if (pbRepeatBtn) {
        pbRepeatBtn.addEventListener('click', () => {
            repeatMode = (repeatMode + 1) % 3;
            localStorage.setItem("pm_repeat", repeatMode);
            updateRepeatUI();
        });
    }

    // ── Previous & Next ──
    if (pbPrevBtn) {
        pbPrevBtn.addEventListener('click', playPrev);
    }
    if (pbNextBtn) {
        pbNextBtn.addEventListener('click', () => {
            if (typeof playNext === 'function') playNext();
        });
    }

    // ── Lyrics ──
    let isLyricsOpen = false;
    window.toggleLyricsPanel = function () {
        const panel = document.getElementById('lyricsPanel');
        if (!panel) return;
        isLyricsOpen = !isLyricsOpen;
        if (isLyricsOpen) {
            panel.style.top = '0'; // Slide up
            if (pbLyricsBtn) {
                pbLyricsBtn.style.color = 'var(--accent-color)';
            }
        } else {
            window.hideLyricsPanel();
        }
    };

    window.hideLyricsPanel = function () {
        const panel = document.getElementById('lyricsPanel');
        if (panel) panel.style.top = '100vh'; // Slide down
        isLyricsOpen = false;
        if (typeof pbLyricsBtn !== 'undefined' && pbLyricsBtn) {
            pbLyricsBtn.style.color = '';
        } else {
            const btn = document.getElementById('pbLyricsBtn');
            if (btn) btn.style.color = '';
        }
    };
    if (pbLyricsBtn) {
        pbLyricsBtn.addEventListener('click', toggleLyricsPanel);
    }

    // ── Devices ──
    let isDevicePanelOpen = false;
    window.toggleDevicePanel = function () {
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
    window.hideDevicePanel = function () {
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

    window.setAudioDevice = async function (deviceId) {
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
    // volume and mute might be restored from localStorage, so updateUI
    updateVolumeUI();
    // repeat UI needs init
    setTimeout(updateRepeatUI, 100);
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

window.syncPlayerUI = function() {
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
    
    // Đồng bộ nút play trên các danh sách playlist/album
    document.querySelectorAll('.card-play-btn').forEach(btn => {
        // Có thể mở rộng sau nếu cần đồng bộ nút play của từng item
    });
};

// ─────────────────────────────────────────────
// UI Updates
// ─────────────────────────────────────────────
function updatePlayIcon() {
    if (window.syncPlayerUI) window.syncPlayerUI();
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
        const playPromise = globalAudio.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                if (error.name !== 'AbortError') {
                    console.error("Playback error:", error);
                }
            });
        }
    }
    isPlaying = !isPlaying;
    updatePlayIcon();
}

function playSuggestedSong(toastMsg = 'Đang phát bài hát gợi ý') {
    fetch('/api/v1/music/songs/trending/')
        .then(res => res.json())
        .then(data => {
            let list = [];
            if (data.success && data.data) {
                list = Array.isArray(data.data) ? data.data : (data.data.items || []);
            }
            if (list.length > 0) {
                const randomIdx = Math.floor(Math.random() * list.length);
                const suggestedSong = list[randomIdx];
                window.playSong(suggestedSong.id);
                if (window.showToast) window.showToast(toastMsg, 'info');
            } else {
                // Fallback to latest songs if no trending
                fetch('/api/v1/music/songs/?page_size=50')
                    .then(r => r.json())
                    .then(d => {
                        let fbList = [];
                        if (d.success && d.data && d.data.items) fbList = d.data.items;
                        if (fbList.length > 0) {
                            const randomIdx = Math.floor(Math.random() * fbList.length);
                            const suggestedSong = fbList[randomIdx];
                            window.playSong(suggestedSong.id);
                            if (window.showToast) window.showToast(toastMsg, 'info');
                        } else {
                            if (window.showToast) window.showToast('Không có bài hát gợi ý nào', 'info');
                        }
                    });
            }
        })
        .catch(err => {
            console.error('Error fetching suggested song', err);
            if (window.showToast) window.showToast('Không thể tải bài hát gợi ý', 'error');
        });
}

function playNext() {
    // Lấy queue từ biến global _songQueue (định nghĩa trong player_bar.html)
    const queue = window._songQueue || [];
    if (queue.length === 0) {
        if (repeatMode === 2 && playHistory.length > 0) {
            // Repeat-all: quay lại từ đầu history
            window.playSong(playHistory[0]);
            return;
        }

        // Không có lịch sử hoặc queue rỗng -> Lấy bài hát gợi ý (trending)
        playSuggestedSong();
        return;
    }

    let nextSong = queue.shift();

    // Cập nhật lại queue sau khi pop
    localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
    if (typeof renderQueue === 'function') renderQueue();

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
        localStorage.setItem('pm_history', JSON.stringify(playHistory));
        window.playSong(prevId, null, true); // true = from history, không thêm vào history lại
    } else {
        playSuggestedSong('Đang phát bài hát gợi ý');
    }
}

// ─────────────────────────────────────────────
// Like
// ─────────────────────────────────────────────
var _isLiked = false; // Trạng thái like hiện tại

async function toggleLike() {
    if (!currentSongId) return;

    // Optimistic UI: đổi ngay trước khi gọi API
    _isLiked = !_isLiked;
    updateHeartUI(_isLiked);

    try {
        const res = await fetch(`/api/v1/music/songs/${currentSongId}/like/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // Đồng bộ với giá trị thực từ server
            const serverLiked = data.data.is_liked ?? data.data.liked ?? _isLiked;
            _isLiked = serverLiked;
            updateHeartUI(_isLiked);
            
            // Dispatch event to sync with song page
            document.dispatchEvent(new CustomEvent('songLikeToggled', { 
                detail: { songId: currentSongId, isLiked: _isLiked, likeCount: data.data.like_count } 
            }));
            
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
window.playSong = async function (songId, event, fromHistory = false) {
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
        const res = await fetch(`/api/v1/music/songs/${songId}/`);
        const data = await res.json();

        if (!data.success) {
            if (window.showToast) window.showToast(data.error || 'Lỗi lấy bài hát', 'error');
            return;
        }

        const song = data.data;
        localStorage.setItem('pm_last_song', JSON.stringify(song));
        localStorage.setItem('pm_saved_at', Date.now());

        if (!song.audio_file) {
            if (!window.CURRENT_USER_AUTHENTICATED) {
                window.location.href = window.LOGIN_URL || '/auth/login/';
                return;
            }
            if (window.showToast) window.showToast('Bài hát chưa có file audio', 'error');
            return;
        }

        // Update player bar UI
        if (pbTitle) pbTitle.textContent = song.title;
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
        try {
            await globalAudio.play();
        } catch (playErr) {
            if (playErr.name === 'AbortError') {
                console.log("Play interrupted by new load, ignoring...");
                return; // Ngừng chạy tiếp các lệnh lưu lịch sử nếu bài bị huỷ
            } else {
                throw playErr; // Các lỗi thật thì ném ra cho catch bên ngoài xử lý
            }
        }

        currentSongId = String(songId);
        isPlaying = true;
        updatePlayIcon();

        // History
        if (!fromHistory) {
            if (playHistory[playHistory.length - 1] !== String(songId)) {
                playHistory.push(String(songId));
                if (playHistory.length > 50) playHistory.shift(); // Giới hạn 50 bài
                localStorage.setItem('pm_history', JSON.stringify(playHistory));
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

        // Auto-fill queue if needed
        if (typeof window.ensureQueueFilled === 'function') {
            window.ensureQueueFilled();
        }

    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast('Lỗi mạng', 'error');
    }
};

// Hàm tự động nạp danh sách chờ (Auto-play)
window._isEnsuringQueue = false;
window.ensureQueueFilled = async function () {
    if (window._isEnsuringQueue) return;

    // Chỉ tự động nạp nếu queue đang trống hoặc tất cả bài trong queue đều là bài hát gợi ý.
    // Nếu người dùng đang nghe playlist/album thì KHÔNG can thiệp.
    const isAutoPlayQueue = window._songQueue.length === 0 || window._songQueue.every(s => s.context === 'Bài hát gợi ý');
    if (!isAutoPlayQueue) return;

    // Cần bổ sung để duy trì luôn có 20 bài gợi ý
    const needed = 20 - window._songQueue.length;
    if (needed <= 0) return;

    window._isEnsuringQueue = true;
    try {
        // Kiểm tra xem người dùng có đang nghe từ trang Profile của nghệ sĩ hay không
        let forceArtistContext = false;
        try {
            const currentPath = window.location.pathname;
            const referrer = document.referrer || '';
            if (currentPath.startsWith('/profile/')) {
                forceArtistContext = true;
            } else if (currentPath.startsWith('/song/')) {
                try {
                    const refUrl = new URL(referrer);
                    if (refUrl.pathname.startsWith('/profile/')) forceArtistContext = true;
                } catch(e) {
                    if (referrer.includes('/profile/')) forceArtistContext = true;
                }
            }
        } catch(e) {}
        
        // Lấy ID nghệ sĩ của bài đang phát (chỉ ưu tiên lấy nhạc cùng nghệ sĩ nếu click từ trang của nghệ sĩ đó)
        let artistId = null;
        if (forceArtistContext) {
            try {
                const lastSongStr = localStorage.getItem('pm_last_song');
                if (lastSongStr) {
                    const currentSong = JSON.parse(lastSongStr);
                    if (currentSong.artist && currentSong.artist.id) {
                        artistId = currentSong.artist.id;
                    }
                }
            } catch(e) {}
        }

        let fetchedSongs = [];

        // Nếu có nghệ sĩ, lấy danh sách bài hát của nghệ sĩ đó trước
        if (artistId) {
            try {
                const res = await fetch(`/api/v1/music/songs/?artist_id=${artistId}&page_size=30`);
                const data = await res.json();
                if (data.success && data.data && data.data.items) {
                    fetchedSongs = data.data.items.map(item => item.song || item);
                }
            } catch (e) { }
        }

        // Nếu vẫn chưa đủ, lấy thêm từ danh sách Trending
        if (fetchedSongs.length < needed) {
            try {
                const res = await fetch(`/api/v1/music/songs/trending/?page_size=30`);
                const data = await res.json();
                if (data.success && data.data) {
                    const trending = Array.isArray(data.data) ? data.data : (data.data.items || []);
                    fetchedSongs = [...fetchedSongs, ...trending.map(item => item.song || item)];
                }
            } catch (e) { }
        }
        
        // NẾU VẪN CHƯA ĐỦ, LẤY TẤT CẢ BÀI HÁT MỚI NHẤT LÀM GỢI Ý (Fallback)
        if (fetchedSongs.length < needed) {
            try {
                const res = await fetch(`/api/v1/music/songs/?page_size=50`);
                const data = await res.json();
                if (data.success && data.data && data.data.items) {
                    fetchedSongs = [...fetchedSongs, ...data.data.items.map(item => item.song || item)];
                }
            } catch(e) {}
        }

        // Xáo trộn nếu đang bật chế độ ngẫu nhiên
        if (isShuffle && fetchedSongs.length > 0) {
            for (let i = fetchedSongs.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [fetchedSongs[i], fetchedSongs[j]] = [fetchedSongs[j], fetchedSongs[i]];
            }
        }
        
        // Lọc các bài hợp lệ (bỏ qua bài đang phát và bài đã có trong queue)
        const currentId = currentSongId;
        let eligibleSongs = fetchedSongs.filter(s => 
            s && s.id && 
            String(s.id) !== String(currentId) && 
            !window._songQueue.find(q => String(q.id) === String(s.id))
        );
        
        // Cố gắng loại bỏ các bài đã nghe (trong history)
        let newSongs = eligibleSongs.filter(s => !playHistory.includes(String(s.id)));
        
        // Nếu database quá nhỏ, hết bài mới thì đành lấy lại các bài đã nghe (trừ bài đang phát)
        if (newSongs.length === 0 && eligibleSongs.length > 0) {
            newSongs = eligibleSongs; 
        }

        // Nạp vào danh sách chờ
        for (const songObj of newSongs) {
            const artistName = songObj.artist ? (songObj.artist.display_name || songObj.artist.username || 'Unknown') : 'Unknown';
            window.addToQueue(songObj.id, songObj.title, artistName, songObj.cover_image, 'Bài hát gợi ý', true);

            if (window._songQueue.length >= 20) break; // Đủ 20 bài thì dừng
        }

        // Update queue panel if open
        renderQueue();
    } finally {
        window._isEnsuringQueue = false;
    }
};

window.playPlaylist = async function (playlistId, event, contextTitle = 'Playlist') {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    try {
        let contextName = contextTitle;
        if (contextName === 'Playlist') {
            try {
                const plRes = await fetch(`/api/v1/playlists/${playlistId}/`);
                const plData = await plRes.json();
                if (plData.success && plData.data) {
                    contextName = plData.data.title || 'Playlist';
                }
            } catch (e) { }
        }

        const res = await fetch(`/api/v1/playlists/${playlistId}/songs/?page_size=100`);
        const data = await res.json();
        if (data.success && data.data && data.data.items && data.data.items.length > 0) {
            const songs = data.data.items.map(item => item.song);

            // Xoá sạch danh sách chờ hiện tại trước khi phát playlist
            window._songQueue = [];
            localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
            localStorage.setItem('pm_saved_at', Date.now());

            // Play the first song
            window.playSong(songs[0].id, null, false);

            // Append the rest to queue with context
            let rest = songs.slice(1);
            
            // Xáo trộn nếu đang bật chế độ ngẫu nhiên
            if (isShuffle && rest.length > 0) {
                for (let i = rest.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [rest[i], rest[j]] = [rest[j], rest[i]];
                }
            }

            rest.forEach(s => {
                window.addToQueue(s.id, s.title, s.artist ? s.artist.display_name : 'Unknown', s.cover_image, `Nội dung tiếp theo từ ${contextName}`, true);
            });
            // Tự động cuộn/mở panel tuỳ ý
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
var savedQueue = [];
try {
    const qStr = localStorage.getItem('pm_queue');
    if (qStr) savedQueue = JSON.parse(qStr);
} catch (e) { }
window._songQueue = Array.isArray(savedQueue) ? savedQueue : [];

window.toggleQueuePanel = function () {
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

window.showQueuePanel = function () {
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

window.hideQueuePanel = function () {
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
window.addToQueue = function (songId, title, artist, cover, context = null, silent = false) {
    // Tránh trùng lặp
    if (window._songQueue.find(s => s.id === songId)) {
        if (!silent && typeof showToast === 'function') showToast('Bài hát đã có trong danh sách chờ', 'info');
        return;
    }
    window._songQueue.push({ id: songId, title: title, artist: artist, cover: cover, context: context });
    localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
    renderQueue();
    if (!silent) window.showQueuePanel(); // Tự động mở panel nếu thêm thủ công
    if (!silent && typeof showToast === 'function') showToast(`Đã thêm "${title}" vào danh sách chờ`, 'success');
};

// Xoá bài khỏi queue
window.removeFromQueue = function (songId) {
    window._songQueue = window._songQueue.filter(s => s.id !== songId);
    localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
    renderQueue();
};

// Render danh sách chờ vào panel
// Hàm phát nhạc từ danh sách chờ (bỏ qua các bài trước đó)
window.playSongFromQueue = function (songId) {
    const idx = window._songQueue.findIndex(s => String(s.id) === String(songId));
    if (idx !== -1) {
        // Xoá toàn bộ bài hát từ đầu queue đến bài này (bao gồm cả bài này vì nó sẽ được phát)
        window._songQueue.splice(0, idx + 1);
        localStorage.setItem('pm_queue', JSON.stringify(window._songQueue));
    localStorage.setItem('pm_saved_at', Date.now());
        renderQueue();
    }
    window.playSong(songId);
};

function renderQueue() {
    var body = document.getElementById('queuePanelBody');
    if (!body) return;

    var html = ``;

    // 1. Render "Đang phát" (Currently playing song)
    try {
        const lastSongStr = localStorage.getItem('pm_last_song');
        if (lastSongStr) {
            const currentSong = JSON.parse(lastSongStr);
            const artistName = currentSong.artist ? (currentSong.artist.display_name || currentSong.artist.username || 'Unknown') : 'Unknown';
            html += `
                <p style="font-size:0.9rem; font-weight:700; color:white; margin-top: 0px; margin-bottom:12px;">Đang phát</p>
                <div style="display:flex; align-items:center; gap:10px; padding:8px 6px; border-radius:8px; margin-bottom: 24px;"
                     onmouseover="this.style.background='rgba(255,255,255,0.06)'" 
                     onmouseout="this.style.background='transparent'"
                     onclick="window.playSong && window.playSong('${currentSong.id}')"
                     style="cursor:pointer; transition:background 0.15s;">
                    <img src="${currentSong.cover_image || ''}" alt="" style="width:40px; height:40px; border-radius:6px; object-fit:cover; flex-shrink:0;">
                    <div style="flex:1; min-width:0;">
                        <div style="font-size:0.875rem; font-weight:600; color:var(--accent-color); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${currentSong.title}</div>
                        <div style="font-size:0.75rem; color:rgba(255,255,255,0.6); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${artistName}</div>
                    </div>
                </div>
            `;
        }
    } catch (e) { }

    // 2. Render the Queue items
    if (window._songQueue.length === 0) {
        html += `
            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding-top: 40px; color:rgba(255,255,255,0.35); text-align:center;">
                <i class="bi bi-music-note-list" style="font-size:2.5rem; margin-bottom:12px;"></i>
                <p style="font-size:0.9rem; margin-bottom:6px; color:rgba(255,255,255,0.5);">Danh sách chờ đang trống</p>
                <p style="font-size:0.8rem; margin:0;">Chọn một bài hát để bắt đầu</p>
            </div>`;
        body.innerHTML = html;
        return;
    }

    let currentContext = null;

    window._songQueue.forEach((song, index) => {
        const ctx = song.context || 'Tiếp theo';
        if (ctx !== currentContext) {
            html += `<p style="font-size:0.8rem; font-weight:700; color:white; margin-top: 16px; margin-bottom:12px;">${ctx}</p>`;
            currentContext = ctx;
        }
        html += `
            <div class="q-item" onclick="window.playSongFromQueue && window.playSongFromQueue('${song.id}')" style="display:flex; align-items:center; gap:10px; padding:8px 6px; border-radius:8px; cursor:pointer; transition:background 0.15s;" 
                 onmouseover="this.style.background='rgba(255,255,255,0.06)'" 
                 onmouseout="this.style.background='transparent'">
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

// Hàm đóng tất cả các panel (ngăn chặn lỗi block màn hình khi chuyển trang)
window.closeAllPlayerPanels = function () {
    if (typeof window.hideQueuePanel === 'function') window.hideQueuePanel();
    if (typeof window.hideDevicePanel === 'function') window.hideDevicePanel();
    if (typeof window.hideLyricsPanel === 'function') window.hideLyricsPanel();
};

// Reset panels khi chuyển trang (tương thích HTMX, Turbo, reload bình thường)
window.addEventListener('beforeunload', window.closeAllPlayerPanels);
document.addEventListener('htmx:beforeRequest', window.closeAllPlayerPanels);

// Đồng bộ trạng thái Like từ trang chi tiết bài hát sang Player Bar
document.addEventListener('songLikeToggled', function(e) {
    // currentSongId is global string in player.js
    if (e.detail.songId && String(e.detail.songId) === String(currentSongId)) {
        if (_isLiked !== e.detail.isLiked) {
            _isLiked = e.detail.isLiked;
            updateHeartUI(_isLiked);
        }
    }
});
document.addEventListener('turbo:before-visit', window.closeAllPlayerPanels);
document.addEventListener('turbolinks:before-visit', window.closeAllPlayerPanels);

// Gọi render 1 lần khi load trang để phục hồi queue UI và dọn dẹp các wrapper
document.addEventListener('DOMContentLoaded', () => {
    window.closeAllPlayerPanels();
    setTimeout(renderQueue, 150);
});
