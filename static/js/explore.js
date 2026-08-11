document.addEventListener('DOMContentLoaded', function() {
    var DEFAULT_COVER = 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
    var DEFAULT_AVATAR = 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80';
    var DEFAULT_PL_COVER = 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';

    function esc(str) {
        return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function renderSongCard(song) {
        var cover = song.cover_image || DEFAULT_COVER;
        var artist = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
        return '<div class="music-card" onclick="window.location.href=\'/song/?id=' + song.id + '\'" style="cursor:pointer;">' +
            '<div class="music-card-img-wrap">' +
            '<img src="' + esc(cover) + '" alt="' + esc(song.title) + '" class="music-card-img" loading="lazy">' +
            '<button class="btn-card-play" onclick="event.stopPropagation();if(window.playSong)window.playSong(\'' + song.id + '\',event)"><i class="bi bi-play-fill"></i></button>' +
            '</div>' +
            '<div class="music-card-title">' + esc(song.title) + '</div>' +
            '<div class="music-card-artist">' + esc(artist) + '</div>' +
            '</div>';
    }

    function renderPlaylistCard(pl) {
        var cover = pl.cover_image || DEFAULT_PL_COVER;
        var owner = pl.owner ? pl.owner.display_name : 'Không rõ';
        var songCount = pl.song_count != null ? pl.song_count + ' bài' : '';
        return '<a href="/playlist/detail/?id=' + pl.id + '" class="playlist-card">' +
            '<div class="playlist-card-img-wrap">' +
            '<img src="' + esc(cover) + '" alt="' + esc(pl.name) + '" loading="lazy">' +
            '<button class="btn-card-play-pl" onclick="event.preventDefault();event.stopPropagation();if(window.playPlaylist)window.playPlaylist(\'' + pl.id + '\',event)"><i class="bi bi-play-fill"></i></button>' +
            '</div>' +
            '<div class="playlist-card-title">' + esc(pl.name) + '</div>' +
            '<div class="playlist-card-sub">bởi ' + esc(owner) + (songCount ? ' - ' + songCount : '') + '</div>' +
            '</a>';
    }

    function renderArtistCard(artist) {
        var avatar = artist.avatar || DEFAULT_AVATAR;
        return '<a href="/profile/' + artist.id + '/" class="artist-card">' +
            '<img src="' + esc(avatar) + '" alt="' + esc(artist.display_name) + '" class="artist-avatar" loading="lazy">' +
            '<div class="artist-name">' + esc(artist.display_name) + '</div>' +
            '<div class="artist-role">Nghe si</div>' +
            '</a>';
    }

    function renderError(msg) {
        return '<div class="section-error"><i class="bi bi-exclamation-circle me-2"></i>' + msg + '</div>';
    }

    var GENRE_COLORS = [
        {bg:'linear-gradient(135deg,#FF416C,#FF4B2B)'},
        {bg:'linear-gradient(135deg,#36D1DC,#5B86E5)'},
        {bg:'linear-gradient(135deg,#F09819,#EDDE5D)',color:'#000'},
        {bg:'linear-gradient(135deg,#8A2387,#E94057,#F27121)'},
        {bg:'linear-gradient(135deg,#11998e,#38ef7d)'},
        {bg:'linear-gradient(135deg,#FC5C7D,#6A82FB)'},
        {bg:'linear-gradient(135deg,#4776E6,#8E54E9)'},
        {bg:'linear-gradient(135deg,#1a1a2e,#16213e,#0f3460)'},
    ];

    // -- 1. GỢI Ý CHO BẠN
    (async function() {
        var container = document.getElementById('forYouContainer');
        var sourceEl = document.getElementById('forYouSource');
        try {
            var res = await fetch('/api/v1/recommendations/for-you/?page_size=10');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                var items = data.data.items;
                container.innerHTML = items.map(function(item) {
                    return renderSongCard(item.song || item);
                }).join('');
                sourceEl.textContent = data.data.source === 'trending' ? 'Thinh hanh' : 'Ca nhan hoa';
                updateHero(items[0].song || items[0]);
            } else {
                container.innerHTML = renderError('Chua co goi y nao. Hay nghe mot so bai hat de bat dau!');
                loadHeroFallback();
            }
        } catch(e) {
            console.error(e);
            container.innerHTML = renderError('Khong the tai goi y.');
            loadHeroFallback();
        }
    })();

    // -- 2. MỚI PHÁT HÀNH
    (async function() {
        var container = document.getElementById('newReleasesContainer');
        try {
            var res = await fetch('/api/v1/music/songs/?ordering=-created_at&page_size=10');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.map(renderSongCard).join('');
            } else {
                container.innerHTML = renderError('Chua co bai hat nao.');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai du lieu.');
        }
    })();

    // -- 3. THỂ LOẠI
    (async function() {
        var container = document.getElementById('genreGrid');
        try {
            var res = await fetch('/api/v1/music/genres/');
            var data = await res.json();
            var genres = data.success && data.data && data.data.items ? data.data.items : [];
            if (genres.length > 0) {
                container.innerHTML = genres.slice(0, 8).map(function(genre, i) {
                    var style = GENRE_COLORS[i % GENRE_COLORS.length];
                    var textColor = style.color ? 'color:' + style.color + ';' : '';
                    var img = genre.cover_image ? '<img src="' + esc(genre.cover_image) + '" class="genre-img" alt="' + esc(genre.name) + '">' : '';
                    return '<a href="#" class="genre-card" style="background:' + style.bg + ';' + textColor + '">' +
                        '<div class="genre-title" style="' + textColor + '">' + esc(genre.name) + '</div>' + img + '</a>';
                }).join('');
            } else {
                container.innerHTML = renderStaticGenres();
            }
        } catch(e) {
            container.innerHTML = renderStaticGenres();
        }
    })();

    function renderStaticGenres() {
        var genres = [
            {name:'Pop',bg:'linear-gradient(135deg,#FF416C,#FF4B2B)'},
            {name:'Chill / Lofi',bg:'linear-gradient(135deg,#36D1DC,#5B86E5)'},
            {name:'Hip Hop',bg:'linear-gradient(135deg,#F09819,#EDDE5D)',tc:'#000'},
            {name:'Electronic',bg:'linear-gradient(135deg,#8A2387,#E94057,#F27121)'},
            {name:'R&B',bg:'linear-gradient(135deg,#11998e,#38ef7d)'},
            {name:'Rock',bg:'linear-gradient(135deg,#FC5C7D,#6A82FB)'},
            {name:'Jazz',bg:'linear-gradient(135deg,#4776E6,#8E54E9)'},
            {name:'Classical',bg:'linear-gradient(135deg,#2c3e50,#3498db)'},
        ];
        return genres.map(function(g) {
            var tc = g.tc ? 'color:' + g.tc + ';' : '';
            return '<a href="#" class="genre-card" style="background:' + g.bg + ';' + tc + '">' +
                '<div class="genre-title" style="' + tc + '">' + g.name + '</div></a>';
        }).join('');
    }

    // -- 4. PLAYLIST GỢI Ý
    (async function() {
        var container = document.getElementById('playlistsContainer');
        try {
            var res = await fetch('/api/v1/recommendations/playlists/?limit=10');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.map(renderPlaylistCard).join('');
            } else {
                container.innerHTML = renderError('Chua co playlist nao. Hay tao playlist cua ban!');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai playlist.');
        }
    })();

    // -- 5. NGHỆ SĨ NỔI BẬT
    (async function() {
        var container = document.getElementById('featuredArtistsContainer');
        try {
            var res = await fetch('/api/v1/recommendations/artists/?limit=10');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.map(renderArtistCard).join('');
            } else {
                container.innerHTML = renderError('Chua co nghe si nao de goi y.');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai danh sach nghe si.');
        }
    })();

    // -- 6. THỊNH HÀNH
    (async function() {
        var container = document.getElementById('trendingContainer');
        try {
            var res = await fetch('/api/v1/music/songs/trending/?page_size=10');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.map(renderSongCard).join('');
            } else {
                container.innerHTML = renderError('Chua co bai hat thinh hanh nao.');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai bai hat thinh hanh.');
        }
    })();

    // -- Hero Banner
    function updateHero(song) {
        if (!song) return;
        var banner = document.getElementById('heroBanner');
        var titleEl = document.getElementById('heroTitle');
        var tagEl = document.getElementById('heroTag');
        var btn = document.getElementById('heroBtnPlay');
        if (song.cover_image) {
            banner.style.backgroundImage = 'url(' + song.cover_image + ')';
            banner.style.backgroundSize = 'cover';
            banner.style.backgroundPosition = 'center';
        }
        titleEl.textContent = song.title || 'Kham Pha Am Nhac';
        var artistName = song.artist ? song.artist.display_name : '';
        tagEl.textContent = artistName ? artistName + ' - Goi y cho ban' : 'Goi y cho ban';
        btn.href = '/song/?id=' + song.id;
        btn.onclick = function(e) {
            e.preventDefault();
            if (window.playSong) window.playSong(song.id, e);
        };
    }

    async function loadHeroFallback() {
        try {
            var res = await fetch('/api/v1/music/songs/trending/?page_size=1');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                updateHero(data.data.items[0]);
                document.getElementById('heroTag').textContent = 'Noi bat tuan nay';
            } else {
                document.getElementById('heroTag').textContent = 'Kham pha am nhac';
            }
        } catch(e) {
            document.getElementById('heroTag').textContent = 'Kham pha am nhac';
        }
    }
});
