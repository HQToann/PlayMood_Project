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
        return '<a href="/song/?id=' + song.id + '" class="music-card text-decoration-none text-reset" style="cursor:pointer; display:block;">' +
            '<div class="music-card-img-wrap">' +
            '<img src="' + esc(cover) + '" alt="' + esc(song.title) + '" class="music-card-img" loading="lazy">' +
            '</div>' +
            '<div class="music-card-title">' + esc(song.title) + '</div>' +
            '<div class="music-card-artist">' + esc(artist) + '</div>' +
            '</a>';
    }

    function renderPlaylistCard(pl) {
        var cover = pl.cover_image || DEFAULT_PL_COVER;
        var owner = pl.owner ? pl.owner.display_name : 'Không rõ';
        var songCount = pl.song_count != null ? pl.song_count + ' bài' : '';
        return '<a href="/playlist/detail/?id=' + pl.id + '" class="playlist-card">' +
            '<div class="playlist-card-img-wrap">' +
            '<img src="' + esc(cover) + '" alt="' + esc(pl.name) + '" loading="lazy">' +
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
            var res = await fetch('/api/v1/recommendations/for-you/?page_size=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(function(item) {
                    return renderSongCard(item.song || item);
                }).join('');
                if (data.data.source === 'trending') {
                    sourceEl.textContent = 'Thinh hanh';
                } else {
                    sourceEl.textContent = '';
                }
            } else {
                container.innerHTML = renderError('Chua co goi y nao. Hay nghe mot so bai hat de bat dau!');
            }
        } catch(e) {
            console.error(e);
            container.innerHTML = renderError('Khong the tai goi y.');
        }
    })();

    // -- 2. MỚI PHÁT HÀNH
    (async function() {
        var container = document.getElementById('newReleasesContainer');
        try {
            var res = await fetch('/api/v1/music/songs/?ordering=-created_at&page_size=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(renderSongCard).join('');
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
        var prevBtn = document.getElementById('genrePrevBtn');
        var nextBtn = document.getElementById('genreNextBtn');
        var allGenres = [];
        var currentPage = 1;
        var pageSize = 4; // Hiển thị 4 mục mỗi trang (1 hàng) để test phân trang

        function renderGenres(page) {
            if (allGenres.length === 0) {
                container.innerHTML = '<div class="text-center text-muted py-4 w-100">Chưa có dữ liệu thể loại.</div>';
                if (prevBtn) prevBtn.disabled = true;
                if (nextBtn) nextBtn.disabled = true;
                return;
            }

            var start = (page - 1) * pageSize;
            var end = start + pageSize;
            var currentGenres = allGenres.slice(start, end);

            container.innerHTML = currentGenres.map(function(genre, i) {
                var style = GENRE_COLORS[(start + i) % GENRE_COLORS.length];
                var textColor = style.color ? 'color:' + style.color + ';' : '';
                var img = genre.cover_image ? '<img src="' + esc(genre.cover_image) + '" class="genre-img" alt="' + esc(genre.name) + '">' : '';
                return '<a href="/explore/list/?section=genre&slug=' + genre.slug + '&name=' + encodeURIComponent(genre.name) + '" class="genre-card" style="background:' + style.bg + ';' + textColor + '">' +
                    '<div class="genre-title" style="' + textColor + '">' + esc(genre.name) + '</div>' + img + '</a>';
            }).join('');

            if (prevBtn) prevBtn.disabled = page === 1;
            if (nextBtn) nextBtn.disabled = end >= allGenres.length;
        }

        try {
            var res = await fetch('/api/v1/music/genres/');
            var data = await res.json();
            allGenres = data.success && data.data && data.data.items ? data.data.items : [];
            renderGenres(currentPage);
        } catch(e) {
            renderGenres(currentPage);
        }

        if (prevBtn && nextBtn) {
            prevBtn.addEventListener('click', function() {
                if (currentPage > 1) {
                    currentPage--;
                    renderGenres(currentPage);
                }
            });
            nextBtn.addEventListener('click', function() {
                if (currentPage * pageSize < allGenres.length) {
                    currentPage++;
                    renderGenres(currentPage);
                }
            });
        }
    })();

    // Removed renderStaticGenres function

    // -- TOP PLAYLIST NỔI BẬT
    (async function() {
        var container = document.getElementById('topPlaylistsContainer');
        try {
            var res = await fetch('/api/v1/playlists/?scope=public&limit=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(renderPlaylistCard).join('');
            } else {
                container.innerHTML = renderError('Chua co playlist noi bat nao.');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai playlist noi bat.');
        }
    })();

    // -- 4. PLAYLIST GỢI Ý (PHÙ HỢP DÀNH CHO BẠN)
    (async function() {
        var container = document.getElementById('playlistsContainer');
        try {
            var res = await fetch('/api/v1/recommendations/playlists/?limit=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(renderPlaylistCard).join('');
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
            var res = await fetch('/api/v1/recommendations/artists/?limit=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(renderArtistCard).join('');
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
            var res = await fetch('/api/v1/music/songs/trending/?page_size=5');
            var data = await res.json();
            if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                container.innerHTML = data.data.items.slice(0, 6).map(renderSongCard).join('');
            } else {
                container.innerHTML = renderError('Chua co bai hat thinh hanh nao.');
            }
        } catch(e) {
            container.innerHTML = renderError('Khong the tai bai hat thinh hanh.');
        }
    })();


});
