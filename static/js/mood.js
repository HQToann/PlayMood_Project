// ============================================
// Fetch data từ API
// ============================================
var MOOD_THEMES = [];
var MOOD_TYPES = [];

var selectedMoodId = null;
var selectedThemeId = null;

function renderThemes() {
    const picker = document.getElementById('themeColorPicker');
    picker.innerHTML = '';
    MOOD_THEMES.forEach(theme => {
        const div = document.createElement('div');
        div.className = 'color-swatch';
        if (theme.id === selectedThemeId) div.classList.add('selected');
        div.dataset.id = theme.id;
        div.style.width = '24px';
        div.style.height = '24px';
        div.style.borderRadius = '50%';
        div.style.background = `linear-gradient(135deg, ${theme.gradient_from}, ${theme.gradient_to})`;
        div.style.cursor = 'pointer';
        div.style.display = 'flex';
        div.style.alignItems = 'center';
        div.style.justifyContent = 'center';
        div.style.fontSize = '0.7rem';
        div.style.color = '#fff';
        if (theme.id === selectedThemeId) {
            div.innerHTML = '✓';
            document.getElementById('theme_id_input').value = theme.id;
        }

        div.addEventListener('click', () => {
            // Khi tự chọn theme, bỏ chọn tag cảm xúc
            deselectMood();
            selectTheme(theme.id);
        });
        picker.appendChild(div);
    });
}

function selectTheme(themeId) {
    selectedThemeId = themeId;
    document.getElementById('theme_id_input').value = themeId;
    document.querySelectorAll('.color-swatch').forEach(s => {
        if (s.dataset.id === themeId) {
            s.classList.add('selected');
            s.innerHTML = '✓';
            s.style.borderColor = 'rgba(255, 255, 255, 0.8)';
        } else {
            s.classList.remove('selected');
            s.innerHTML = '';
            s.style.borderColor = 'transparent';
        }
    });
}

function renderMoodTypes(moodTypes) {
    const grid = document.getElementById('moodTypeGrid');
    grid.innerHTML = '';
    moodTypes.forEach(mt => {
        const div = document.createElement('div');
        div.className = 'mood-card-item';
        div.dataset.id = mt.id;
        div.innerHTML = `
                                <div class="mood-name" style="color: ${mt.theme.color_hex}; transition: color 0.2s;">${mt.name}</div>`;
        div.addEventListener('click', () => selectMood(mt, div));
        grid.appendChild(div);
    });
}

function deselectMood() {
    selectedMoodId = null;
    document.getElementById('mood_type_id').value = '';
    document.querySelectorAll('.mood-card-item').forEach(c => {
        c.classList.remove('selected');
        c.style.background = 'rgba(255, 255, 255, 0.08)';
        const nameDiv = c.querySelector('.mood-name');
        if (nameDiv) {
            // Phục hồi lại màu chữ ban đầu từ data
            const mtId = c.dataset.id;
            const mt = MOOD_TYPES.find(m => m.id === mtId);
            if (mt) nameDiv.style.color = mt.theme.color_hex;
        }
    });
    const label = document.getElementById('selectedMoodLabel');
    if (label) label.textContent = 'Chưa chọn cảm xúc';
}

function selectMood(mt, el) {
    deselectMood(); // Bỏ chọn các tag khác và phục hồi màu chữ

    el.classList.add('selected');
    el.style.background = `linear-gradient(135deg, ${mt.theme.gradient_from}, ${mt.theme.gradient_to})`;
    const nameDiv = el.querySelector('.mood-name');
    if (nameDiv) {
        nameDiv.style.color = '#ffffff'; // Đổi màu chữ thành trắng khi được chọn để nổi bật trên nền gradient
    }

    selectedMoodId = mt.id;
    document.getElementById('mood_type_id').value = mt.id;
    const label = document.getElementById('selectedMoodLabel');
    if (label) label.textContent = mt.name;

    // Auto select the theme for this mood
    selectTheme(mt.theme.id);

    // Update section titles
    const songsTitleEl = document.getElementById('songsSectionTitle');
    if (songsTitleEl) songsTitleEl.textContent = `Nhạc Phù Hợp Với "${mt.name}"`;
    document.getElementById('playlistSectionTitle').textContent = `Playlist Cho "${mt.name}"`;

    // Gọi API gợi ý theo tâm trạng
    loadMoodRecommendations(mt.id, mt.name, mt.emoji);
}

// ============================================
// Load gợi ý theo tâm trạng
// ============================================
async function loadMoodRecommendations(moodTypeId, moodName, moodEmoji) {
    const songsContainer = document.getElementById('moodSongsContainer');
    const playlistContainer = document.getElementById('moodPlaylistsContainer');
    const recoSection = document.getElementById('moodRecoSection');
    const placeholder = document.getElementById('moodRecoPlaceholder');
    if (!recoSection) return;

    // Hiện section và skeleton, ẩn placeholder
    recoSection.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';

    // Skeleton bài hát
    if (songsContainer) {
        songsContainer.innerHTML = Array(5).fill(`
                                    <div style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;">
                                        <div style="width:100%;aspect-ratio:1;border-radius:8px;background:rgba(255,255,255,0.07);margin-bottom:0.75rem;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:13px;border-radius:4px;background:rgba(255,255,255,0.07);width:80%;margin-bottom:8px;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:11px;border-radius:4px;background:rgba(255,255,255,0.05);width:55%;animation:skeleton-pulse 1.5s infinite;"></div>
                                    </div>`).join('');
    }
    if (playlistContainer) {
        playlistContainer.innerHTML = Array(4).fill(`
                                    <div style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;">
                                        <div style="width:100%;aspect-ratio:1;border-radius:8px;background:rgba(255,255,255,0.07);margin-bottom:0.75rem;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:13px;border-radius:4px;background:rgba(255,255,255,0.07);width:75%;margin-bottom:8px;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:11px;border-radius:4px;background:rgba(255,255,255,0.05);width:50%;animation:skeleton-pulse 1.5s infinite;"></div>
                                    </div>`).join('');
    }

    // Gọi 2 API song song
    try {
        const [songsRes, playlistsRes] = await Promise.all([
            fetch(`/api/v1/recommendations/mood/${moodTypeId}/songs/?limit=5`).then(r => r.json()),
            fetch(`/api/v1/recommendations/mood/${moodTypeId}/playlists/?limit=5`).then(r => r.json()),
        ]);

        // Render bài hát
        if (songsContainer) {
            if (songsRes.success && songsRes.data && songsRes.data.items && songsRes.data.items.length > 0) {
                songsContainer.innerHTML = songsRes.data.items.map(song => {
                    const cover = song.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';
                    const artist = song.artist ? song.artist.display_name : 'Nghệ sĩ';
                    return `
                                                <div class="music-card" onclick="window.goToPage('/song/?id=${song.id}')" style="cursor:pointer;min-width:160px;width:160px;">
                                                    <div class="music-card-img-wrap">
                                                        <img src="${cover}" alt="${song.title}" class="music-card-img" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';">

                                                    </div>
                                                    <div class="music-card-title">${song.title}</div>
                                                    <div class="music-card-artist">${artist}</div>
                                                </div>`;
                }).join('');
            } else {
                songsContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Chưa có bài hát nào phù hợp với tâm trạng này.</div>';
            }
        }

        // Render playlist
        if (playlistContainer) {
            if (playlistsRes.success && playlistsRes.data && playlistsRes.data.items && playlistsRes.data.items.length > 0) {
                playlistContainer.innerHTML = playlistsRes.data.items.map(pl => {
                    const cover = pl.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';
                    const owner = pl.owner ? pl.owner.display_name : '';
                    const songCount = pl.song_count ? ` • ${pl.song_count} bài` : '';
                    return `
                                                <a href="/playlist/detail/?id=${pl.id}" class="playlist-mood-card" style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;display:block;text-decoration:none;color:#fff;transition:all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.08)';this.style.transform='translateY(-4px)'" onmouseout="this.style.background='rgba(255,255,255,0.04)';this.style.transform='translateY(0)'">
                                                    <div style="position:relative;width:100%;aspect-ratio:1;border-radius:8px;overflow:hidden;margin-bottom:0.75rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                                                        <img src="${cover}" alt="${pl.title}" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';">

                                                    </div>
                                                    <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;">${pl.title}</div>
                                                    <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">bởi ${owner}${songCount}</div>
                                                </a>`;
                }).join('');
            } else {
                playlistContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Chưa có playlist nào phù hợp.</div>';
            }
        }
    } catch (err) {
        console.error('Lỗi tải gợi ý theo tâm trạng:', err);
        if (songsContainer) songsContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Không thể tải dữ liệu.</div>';
        if (playlistContainer) playlistContainer.innerHTML = '';
    }
}

// ============================================
// Load gợi ý mặc định (khi chưa chọn mood)
// ============================================
async function loadDefaultRecommendations() {
    const songsContainer = document.getElementById('moodSongsContainer');
    const playlistContainer = document.getElementById('moodPlaylistsContainer');

    // Skeleton bài hát
    if (songsContainer) {
        songsContainer.innerHTML = Array(5).fill(`
                                    <div style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;">
                                        <div style="width:100%;aspect-ratio:1;border-radius:8px;background:rgba(255,255,255,0.07);margin-bottom:0.75rem;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:13px;border-radius:4px;background:rgba(255,255,255,0.07);width:80%;margin-bottom:8px;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:11px;border-radius:4px;background:rgba(255,255,255,0.05);width:55%;animation:skeleton-pulse 1.5s infinite;"></div>
                                    </div>`).join('');
    }
    if (playlistContainer) {
        playlistContainer.innerHTML = Array(4).fill(`
                                    <div style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;">
                                        <div style="width:100%;aspect-ratio:1;border-radius:8px;background:rgba(255,255,255,0.07);margin-bottom:0.75rem;animation:skeleton-pulse 1.5s infinite;"></div>
                                        <div style="height:13px;border-radius:4px;background:rgba(255,255,255,0.07);width:75%;margin-bottom:8px;animation:skeleton-pulse 1.5s infinite;"></div>
                                    </div>`).join('');
    }

    try {
        const [songsRes, playlistsRes] = await Promise.all([
            fetch(`/api/v1/recommendations/for-you/?limit=10`).then(r => r.json()),
            fetch(`/api/v1/recommendations/playlists/?limit=8`).then(r => r.json()),
        ]);

        // Render bài hát
        if (songsContainer) {
            if (songsRes.success && songsRes.data && songsRes.data.items && songsRes.data.items.length > 0) {
                songsContainer.innerHTML = songsRes.data.items.map(song => {
                    const cover = song.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';
                    const artist = song.artist ? song.artist.display_name : 'Nghệ sĩ';
                    return `
                                                <div class="music-card" onclick="window.goToPage('/song/?id=${song.id}')" style="cursor:pointer;min-width:160px;width:160px;">
                                                    <div class="music-card-img-wrap">
                                                        <img src="${cover}" alt="${song.title}" class="music-card-img" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%27100%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%99%AA%3C/text%3E%3C/svg%3E';">

                                                    </div>
                                                    <div class="music-card-title">${song.title}</div>
                                                    <div class="music-card-artist">${artist}</div>
                                                </div>`;
                }).join('');
            } else {
                songsContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Chưa có gợi ý bài hát.</div>';
            }
        }

        // Render playlist
        if (playlistContainer) {
            if (playlistsRes.success && playlistsRes.data && playlistsRes.data.items && playlistsRes.data.items.length > 0) {
                playlistContainer.innerHTML = playlistsRes.data.items.map(pl => {
                    const cover = pl.cover_image || 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';
                    const owner = pl.owner ? pl.owner.display_name : '';
                    const songCount = pl.song_count ? ` • ${pl.song_count} bài` : '';
                    return `
                                                <a href="/playlist/detail/?id=${pl.id}" class="playlist-mood-card" style="min-width:160px;width:160px;background:rgba(255,255,255,0.04);border-radius:12px;padding:1rem;display:block;text-decoration:none;color:#fff;transition:all 0.3s;" onmouseover="this.style.background='rgba(255,255,255,0.08)';this.style.transform='translateY(-4px)'" onmouseout="this.style.background='rgba(255,255,255,0.04)';this.style.transform='translateY(0)'">
                                                    <div style="position:relative;width:100%;aspect-ratio:1;border-radius:8px;overflow:hidden;margin-bottom:0.75rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);">
                                                        <img src="${cover}" alt="${pl.title}" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27300%27 height=%27300%27 viewBox=%270 0 300 300%27%3E%3Crect width=%27300%27 height=%27300%27 fill=%27%232a2a35%27/%3E%3Ctext x=%2750%25%27 y=%2754%25%27 font-size=%2780%27 text-anchor=%27middle%27 dominant-baseline=%27middle%27 fill=%27%23555%27%3E%E2%96%B6%3C/text%3E%3C/svg%3E';">

                                                    </div>
                                                    <div style="font-weight:600;font-size:0.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;">${pl.title}</div>
                                                    <div style="color:rgba(255,255,255,0.5);font-size:0.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">bởi ${owner}${songCount}</div>
                                                </a>`;
                }).join('');
            } else {
                playlistContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Chưa có playlist nào.</div>';
            }
        }
    } catch (err) {
        console.error('Lỗi tải gợi ý mặc định:', err);
        if (songsContainer) songsContainer.innerHTML = '<div style="color:rgba(255,255,255,0.4);font-size:0.88rem;padding:1rem 0;">Không thể tải dữ liệu.</div>';
        if (playlistContainer) playlistContainer.innerHTML = '';
    }
}

// Load data từ Backend
async function loadMoodData() {
    try {
        const [themesRes, typesRes, myMoodRes] = await Promise.all([
            fetch('/api/v1/social/mood-themes/').then(r => r.json()),
            fetch('/api/v1/social/mood-types/').then(r => r.json()),
            fetch('/api/v1/social/me/mood/').then(r => r.json()).catch(() => ({ success: false })) // Bỏ qua lỗi nếu chưa đăng nhập
        ]);

        if (themesRes.success) {
            MOOD_THEMES = themesRes.data;
            if (MOOD_THEMES.length > 0) {
                selectedThemeId = MOOD_THEMES[0].id; // Mặc định chọn theme đầu tiên
            }
            renderThemes();
        }

        if (typesRes.success) {
            MOOD_TYPES = typesRes.data;
            // Bản mood types API trả về cần có object theme lồng nhau để render
            renderMoodTypes(MOOD_TYPES);
        }

        // Hiển thị Tâm trạng hiện tại
        const myMoodTag = document.getElementById('myMoodBadge');
        if (myMoodRes.success && myMoodRes.data) {
            const mood = myMoodRes.data;
            if (myMoodTag) {
                myMoodTag.style.display = 'inline-block';
                myMoodTag.style.background = `linear-gradient(135deg, ${mood.theme.gradient_from}, ${mood.theme.gradient_to})`;
                myMoodTag.style.color = '#fff';

                let contentHtml = '';
                if (mood.mood_type) {
                    contentHtml = `<span class="me-1">${mood.mood_type.emoji || '<i class="bi bi-emoji-smile"></i>'}</span> ${mood.mood_type.name}`;
                } else {
                    contentHtml = `<i class="bi bi-chat-fill me-1"></i> ${mood.status_text || 'Đang cảm thấy...'}`;
                }
                myMoodTag.innerHTML = contentHtml;
                myMoodTag.title = mood.status_text || 'Tâm trạng hiện tại của bạn';
            }

            // Nếu user đang có mood, tự động hiện gợi ý luôn
            if (mood.mood_type) {
                const songsTitleEl = document.getElementById('songsSectionTitle');
                if (songsTitleEl) songsTitleEl.textContent = `Nhạc Phù Hợp Với "${mood.mood_type.name}"`;
                const plTitleEl = document.getElementById('playlistSectionTitle');
                if (plTitleEl) plTitleEl.textContent = `Playlist Cho "${mood.mood_type.name}"`;

                loadMoodRecommendations(mood.mood_type.id, mood.mood_type.name, mood.mood_type.emoji);
            } else {
                loadDefaultRecommendations();
            }
        } else {
            if (myMoodTag) myMoodTag.style.display = 'none';
            loadDefaultRecommendations();
        }
    } catch (e) {
        console.error('Lỗi khi tải dữ liệu mood:', e);
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadMoodData();
});

// Select expires hours
function selectExpires(event, val, text) {
    event.preventDefault();
    document.getElementById('expires_hours_input').value = val;
    document.getElementById('selectedExpiresText').textContent = text;

    // Update active state
    const items = event.currentTarget.closest('.custom-dropdown-menu').querySelectorAll('.custom-dropdown-item');
    items.forEach(item => item.classList.remove('active'));
    event.currentTarget.classList.add('active');
}



// Handle form submit
async function handlePostMood(event) {
    event.preventDefault();

    const btn = document.getElementById('submitBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang đăng...';
    btn.disabled = true;

    const moodTypeId = document.getElementById('mood_type_id').value;
    const themeId = document.getElementById('theme_id_input').value;
    const statusText = document.getElementById('status_text').value;
    const durationHours = parseInt(document.getElementById('expires_hours_input').value, 10);

    const songId = document.getElementById('attached_song_id').value;

    const payload = {
        status_text: statusText,
        duration_hours: durationHours,
        theme_id: themeId || null
    };
    if (moodTypeId) payload.mood_type_id = moodTypeId;
    if (songId) payload.song_id = songId;

    try {
        const csrfToken = getCookie('csrftoken') || '{{ csrf_token }}';
        const response = await fetch('/api/v1/social/me/mood/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (response.ok && data.success) {
            window.showToast('Đã đăng tâm trạng thành công!', true);
            // Reset form
            document.getElementById('status_text').value = '';
            document.getElementById('charCount').textContent = '0';
            document.getElementById('attached_song_id').value = '';
            resetSongAttachmentUI();

            // Lưu lại moodTypeId trước khi deselectMood
            const postedMoodId = selectedMoodId;
            const postedMoodType = MOOD_TYPES.find(m => m.id === postedMoodId);
            deselectMood();

            // Reload data to show new mood immediately
            loadMoodData();

            // Tải lại gợi ý cho mood vừa đăng
            if (postedMoodType) {
                loadMoodRecommendations(postedMoodType.id, postedMoodType.name, postedMoodType.emoji);
            }
        } else {
            window.showToast('Lỗi: ' + (data.error?.message || 'Không thể đăng tâm trạng.'), false);
        }
    } catch (e) {
        console.error('Lỗi khi đăng mood:', e);
        window.showToast('Lỗi kết nối, vui lòng thử lại.', false);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Handle Search Music
var searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('musicSearchInput');
    const searchResults = document.getElementById('searchResults');
    const modalBody = searchInput ? searchInput.closest('.modal-body') : null;

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            if (!query) {
                searchResults.innerHTML = '<div class="text-center text-secondary py-4" style="font-size: 0.9rem;">Nhập từ khóa để tìm kiếm bản nhạc bạn muốn đính kèm.</div>';
                return;
            }

            searchTimeout = setTimeout(() => {
                currentSearchQuery = query;
                currentSearchPage = 1;
                hasMoreSearchResults = true;
                fetchSongs(query, 1, false);
            }, 500);
        });
    }

    if (searchResults) {
        searchResults.addEventListener('scroll', () => {
            // Kiểm tra xem đã cuộn đến cuối chưa (với sai số 20px)
            if (searchResults.scrollTop + searchResults.clientHeight >= searchResults.scrollHeight - 20) {
                if (hasMoreSearchResults && !isSearchLoading && currentSearchQuery) {
                    fetchSongs(currentSearchQuery, currentSearchPage, true);
                }
            }
        });
    }
});

let currentSearchQuery = '';
let currentSearchPage = 1;
let isSearchLoading = false;
let hasMoreSearchResults = true;

async function fetchSongs(query, page = 1, append = false) {
    if (isSearchLoading || (!hasMoreSearchResults && page > 1)) return;
    
    const searchLoading = document.getElementById('searchLoading');
    const searchResults = document.getElementById('searchResults');

    isSearchLoading = true;
    if (!append) {
        searchLoading.style.display = 'block';
        searchResults.innerHTML = '';
    } else {
        // Add a small loading indicator at the bottom when appending
        const appendLoading = document.createElement('div');
        appendLoading.id = 'appendSearchLoading';
        appendLoading.className = 'text-center py-2';
        appendLoading.innerHTML = '<div class="spinner-border text-light spinner-border-sm" role="status"></div>';
        searchResults.appendChild(appendLoading);
    }

    try {
        const res = await fetch(`/api/v1/search/songs/?q=${encodeURIComponent(query)}&page=${page}&page_size=5`);
        const data = await res.json();
        
        searchLoading.style.display = 'none';
        const appendLoader = document.getElementById('appendSearchLoading');
        if (appendLoader) appendLoader.remove();

        if (data.success && data.data && data.data.items && data.data.items.length > 0) {
            renderSearchResults(data.data.items, searchResults, append);
            
            // Check if we reached the end
            if (data.data.items.length < 5 || (data.data.total && data.data.items.length + (page - 1) * 5 >= data.data.total)) {
                hasMoreSearchResults = false;
            } else {
                hasMoreSearchResults = true;
                currentSearchPage = page + 1;
            }
        } else {
            hasMoreSearchResults = false;
            if (!append) {
                searchResults.innerHTML = '<div class="text-center text-secondary py-4" style="font-size: 0.9rem;">Không tìm thấy kết quả nào.</div>';
            }
        }
    } catch (err) {
        searchLoading.style.display = 'none';
        const appendLoader = document.getElementById('appendSearchLoading');
        if (appendLoader) appendLoader.remove();
        
        if (!append) {
            searchResults.innerHTML = '<div class="text-center text-danger py-4" style="font-size: 0.9rem;">Đã xảy ra lỗi, vui lòng thử lại sau.</div>';
        }
    } finally {
        isSearchLoading = false;
    }
}

function renderSearchResults(songs, searchResultsEl, append = false) {
    let html = '';
    songs.forEach(song => {
        // Nếu cover_image null, dùng ảnh mặc định
        const cover = song.cover_image || 'https://via.placeholder.com/150?text=No+Cover';
        // Tên artist (dùng map lấy tên nếu trả về array)
        const artistNames = Array.isArray(song.artists) ? song.artists.map(a => a.name).join(', ') : 'Unknown Artist';

        html += `
                                    <div class="d-flex align-items-center gap-3 p-2 rounded" style="cursor: pointer; transition: background 0.2s;" 
                                         onmouseover="this.style.background='rgba(255,255,255,0.05)'" 
                                         onmouseout="this.style.background='transparent'"
                                         onclick="selectSong('${song.id}', '${song.title.replace(/'/g, "\\'")}', '${artistNames.replace(/'/g, "\\'")}', '${cover}')">
                                        <img src="${cover}" alt="${song.title}" style="width: 48px; height: 48px; border-radius: 8px; object-fit: cover;">
                                        <div style="flex: 1; min-width: 0;">
                                            <div style="font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${song.title}</div>
                                            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.5); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${artistNames}</div>
                                        </div>
                                    </div>
                                `;
    });

    const target = searchResultsEl || document.getElementById('searchResults');
    if (target) {
        if (append) {
            target.insertAdjacentHTML('beforeend', html);
        } else {
            target.innerHTML = html;
        }
    }
}

function selectSong(id, title, artist, cover) {
    // Update input
    document.getElementById('attached_song_id').value = id;

    // Update UI
    const area = document.getElementById('songAttachmentArea');
    area.innerHTML = `
                                <img src="${cover}" alt="cover" style="width: 46px; height: 46px; border-radius: 12px; object-fit: cover; flex-shrink: 0;">
                                <div style="flex:1; min-width:0;">
                                    <div style="color: #fff; font-size: 0.88rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${title}</div>
                                    <div style="color: rgba(255,255,255,0.5); font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${artist}</div>
                                </div>
                                <button type="button" class="btn btn-sm btn-link p-0 ms-2" 
                                    style="color: rgba(255,255,255,0.4); text-decoration: none; font-size: 1.2rem; transition: color 0.2s;" 
                                    onmouseover="this.style.color='#fff'" 
                                    onmouseout="this.style.color='rgba(255,255,255,0.4)'"
                                    onclick="resetSongAttachmentUI()" title="Xóa">
                                    <i class="bi bi-x"></i>
                                </button>
                            `;

    // Đóng modal an toàn
    const modalEl = document.getElementById('searchMusicModal');
    if (modalEl) {
        const closeBtn = modalEl.querySelector('.btn-close');
        if (closeBtn) closeBtn.click();
    }
}

function resetSongAttachmentUI() {
    document.getElementById('attached_song_id').value = '';
    const area = document.getElementById('songAttachmentArea');
    area.innerHTML = `
                                <div style="width: 46px; height: 46px; border-radius: 12px; background: rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.3); font-size: 1.1rem; flex-shrink: 0;">
                                    🎵</div>
                                <div style="flex:1; min-width:0;">
                                    <div style="color: rgba(255,255,255,0.5); font-size: 0.88rem;">Chưa đính kèm bài hát</div>
                                    <div style="color: rgba(255,255,255,0.25); font-size: 0.78rem;">Bài hát sẽ hiển thị cùng tâm trạng của bạn</div>
                                </div>
                                <button type="button"
                                    data-bs-toggle="modal" data-bs-target="#searchMusicModal"
                                    style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); border-radius: 50px; padding: 7px 18px; font-size: 0.82rem; cursor: pointer; transition: all .2s; white-space: nowrap;"
                                    onmouseover="this.style.background='linear-gradient(135deg, #667eea, #764ba2)'; this.style.borderColor='transparent'; this.style.color='#fff';"
                                    onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.borderColor='rgba(255,255,255,0.1)'; this.style.color='rgba(255,255,255,0.6)';">
                                    <i class="bi bi-search me-1"></i> Tìm nhạc
                                </button>
                            `;
}
