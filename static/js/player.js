// static/js/player.js
// Global audio player logic for PlayMood

const globalAudio = new Audio();
let currentSongId = null;
let isPlaying = false;

// DOM Elements
let pbCover, pbTitle, pbArtist, pbPlayBtn, pbPlayIcon, pbCurrentTime, pbDuration, pbProgressBg, pbProgressFill, pbMuteBtn, pbMuteIcon, pbVolumeBg, pbVolumeFill;

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

    if (!pbPlayBtn) return; // Player bar not on this page

    // Play/Pause toggle
    pbPlayBtn.addEventListener('click', () => {
        if (!currentSongId && globalAudio.src === '') return;
        togglePlay();
    });

    // Time update for progress bar
    globalAudio.addEventListener('timeupdate', () => {
        if (isNaN(globalAudio.duration)) return;
        const current = globalAudio.currentTime;
        const duration = globalAudio.duration;
        const percent = (current / duration) * 100;
        pbProgressFill.style.width = `${percent}%`;
        pbCurrentTime.textContent = formatTime(current);
    });

    // Duration change (metadata loaded)
    globalAudio.addEventListener('loadedmetadata', () => {
        pbDuration.textContent = formatTime(globalAudio.duration);
    });

    // Audio ended
    globalAudio.addEventListener('ended', () => {
        isPlaying = false;
        updatePlayIcon();
        pbProgressFill.style.width = '0%';
        pbCurrentTime.textContent = '0:00';
    });

    // Click on progress bar to seek
    pbProgressBg.addEventListener('click', (e) => {
        if (!globalAudio.duration) return;
        const rect = pbProgressBg.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const percent = x / rect.width;
        globalAudio.currentTime = percent * globalAudio.duration;
    });

    // Volume control
    pbVolumeBg.addEventListener('click', (e) => {
        const rect = pbVolumeBg.getBoundingClientRect();
        const x = e.clientX - rect.left;
        let percent = x / rect.width;
        percent = Math.max(0, Math.min(1, percent));
        globalAudio.volume = percent;
        updateVolumeUI();
    });

    // Mute toggle
    pbMuteBtn.addEventListener('click', () => {
        globalAudio.muted = !globalAudio.muted;
        updateVolumeUI();
    });
    
    // Init volume UI
    globalAudio.volume = 1.0;
    updateVolumeUI();
});

function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
}

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
        const urlParams = new URLSearchParams(window.location.search);
        const pageSongId = urlParams.get('id');
        if (pageSongId === currentSongId && isPlaying) {
            detailPlayIcon.classList.remove('bi-play-fill');
            detailPlayIcon.classList.add('bi-pause-fill');
            detailPlayIcon.style.marginLeft = '0';
        } else {
            detailPlayIcon.classList.remove('bi-pause-fill');
            detailPlayIcon.classList.add('bi-play-fill');
            detailPlayIcon.style.marginLeft = '2px';
        }
    }
}

function updateVolumeUI() {
    if (!pbMuteIcon || !pbVolumeFill) return;
    if (globalAudio.muted || globalAudio.volume === 0) {
        pbMuteIcon.classList.remove('bi-volume-up', 'bi-volume-down');
        pbMuteIcon.classList.add('bi-volume-mute');
        pbVolumeFill.style.width = '0%';
    } else {
        pbMuteIcon.classList.remove('bi-volume-mute');
        if (globalAudio.volume < 0.5) {
            pbMuteIcon.classList.remove('bi-volume-up');
            pbMuteIcon.classList.add('bi-volume-down');
        } else {
            pbMuteIcon.classList.remove('bi-volume-down');
            pbMuteIcon.classList.add('bi-volume-up');
        }
        pbVolumeFill.style.width = `${globalAudio.volume * 100}%`;
    }
}

window.playSong = async function(songId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // If it's the same song, just toggle play/pause
    if (currentSongId === songId) {
        togglePlay();
        return;
    }
    
    try {
        const res = await fetch(`/api/v1/music/songs/${songId}/`);
        const data = await res.json();
        
        if (data.success) {
            const song = data.data;
            if (!song.audio_file) {
                // Nếu chưa đăng nhập, backend sẽ không trả về audio_file, ta chuyển hướng sang login
                if (!window.CURRENT_USER_AUTHENTICATED) {
                    window.location.href = window.LOGIN_URL || '/auth/login/';
                    return;
                }
                if (window.showToast) window.showToast('Bài hát chưa có file audio', false);
                return;
            }
            
            // Update UI
            if (pbTitle) pbTitle.textContent = song.title;
            if (pbArtist) pbArtist.textContent = song.artist ? song.artist.display_name : 'Unknown';
            if (pbCover && song.cover_image) {
                pbCover.src = song.cover_image;
            }
            
            // Play audio
            globalAudio.src = song.audio_file;
            globalAudio.play();
            currentSongId = songId;
            isPlaying = true;
            updatePlayIcon();
            
            // Record play history & update play count on UI
            fetch(`/api/v1/music/songs/${songId}/play/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': typeof getCookie === 'function' ? getCookie('csrftoken') : '',
                    'Content-Type': 'application/json'
                }
            })
            .then(res => res.json())
            .then(playData => {
                if (playData.success) {
                    // Cập nhật play_count lên UI trang chi tiết bài hát (nếu đang xem đúng bài đó)
                    const urlParams = new URLSearchParams(window.location.search);
                    const pageSongId = urlParams.get('id');
                    if (pageSongId === String(songId)) {
                        const playsEl = document.getElementById('detail-plays');
                        if (playsEl && playData.data.play_count !== undefined) {
                            const formatted = Number(playData.data.play_count).toLocaleString('vi-VN');
                            playsEl.textContent = `${formatted} lượt nghe`;
                        }
                    }
                }
            })
            .catch(err => console.error('Failed to record play:', err));
            
        } else {
            if (window.showToast) window.showToast(data.error || 'Lỗi lấy bài hát', false);
        }
    } catch (err) {
        console.error(err);
        if (window.showToast) window.showToast('Lỗi mạng', false);
    }
};

function togglePlay() {
    if (isPlaying) {
        globalAudio.pause();
    } else {
        globalAudio.play();
    }
    isPlaying = !isPlaying;
    updatePlayIcon();
}
