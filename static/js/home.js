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
        return '<div class="music-card" onclick="window.goToPage(\'/song/?id=' + song.id + '\')" style="cursor:pointer;">' +
            '<div class="music-card-img-wrap">' +
            '<img src="' + esc(cover) + '" alt="' + esc(song.title) + '" class="music-card-img" loading="lazy">' +
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
            '<img src="' + esc(cover) + '" alt="' + esc(pl.title || pl.name) + '" loading="lazy">' +
            '</div>' +
            '<div class="playlist-card-title">' + esc(pl.title || pl.name) + '</div>' +
            '<div class="playlist-card-sub">bởi ' + esc(owner) + (songCount ? ' - ' + songCount : '') + '</div>' +
            '</a>';
    }

    function renderArtistCard(artist) {
        var avatar = artist.avatar || DEFAULT_AVATAR;
        return '<a href="/profile/' + (artist.username || artist.id) + '/" class="artist-card">' +
            '<img src="' + esc(avatar) + '" alt="' + esc(artist.display_name) + '" class="artist-avatar" loading="lazy">' +
            '<div class="artist-name">' + esc(artist.display_name) + '</div>' +
            '<div class="artist-role">Nghệ sĩ</div>' +
            '</a>';
    }

    // Fetch Trending Songs
    fetch('/api/v1/music/songs/trending/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data && data.data.items) {
                const container = document.getElementById('trending-songs-container');
                container.innerHTML = '';
                
                if(data.data.items.length === 0) {
                    container.innerHTML = '<div class="text-secondary p-3 w-100 text-center" style="grid-column: 1/-1;">Chưa có bài hát thịnh hành nào.</div>';
                } else {
                    container.innerHTML = data.data.items.slice(0, 5).map(renderSongCard).join('');
                }
            }
        })
        .catch(error => console.error('Lỗi khi tải bài hát thịnh hành:', error));

    if (window.USER_IS_AUTHENTICATED) {
        // Fetch For You Recommendations
        fetch('/api/v1/recommendations/for-you/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    const section = document.getElementById('recommendations-section');
                    const container = document.getElementById('foryou-songs-container');
                    section.style.display = 'block';
                    container.innerHTML = data.data.items.slice(0, 5).map(item => renderSongCard(item.song || item)).join('');
                }
            })
            .catch(error => console.error('Lỗi gợi ý bài hát:', error));

        // Fetch Recommended Artists
        fetch('/api/v1/recommendations/artists/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    const section = document.getElementById('artists-section');
                    const container = document.getElementById('recommended-artists-container');
                    section.style.display = 'block';
                    container.innerHTML = data.data.items.slice(0, 5).map(renderArtistCard).join('');
                }
            })
            .catch(error => console.error('Lỗi gợi ý nghệ sĩ:', error));

        // Fetch Recommended Playlists
        fetch('/api/v1/recommendations/playlists/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.data && data.data.items && data.data.items.length > 0) {
                    const section = document.getElementById('playlists-section');
                    const container = document.getElementById('recommended-playlists-container');
                    section.style.display = 'block';
                    container.innerHTML = data.data.items.slice(0, 5).map(renderPlaylistCard).join('');
                }
            })
            .catch(error => console.error('Lỗi gợi ý playlist:', error));
    }
});
