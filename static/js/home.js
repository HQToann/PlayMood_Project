document.addEventListener('DOMContentLoaded', function() {
    // Fetch Trending Songs
    fetch('/api/v1/music/songs/trending/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data && data.data.items) {
                const container = document.getElementById('trending-songs-container');
                container.innerHTML = ''; // Xoá loading spinner
                
                data.data.items.forEach(song => {
                    const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
                    const coverImg = song.cover_image ? song.cover_image : 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                    
                    // HTML của Thẻ Bài hát (Card component style='song')
                    const cardHTML = `
                    <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                        <div class="card-image-wrapper">
                            <img src="${coverImg}" alt="${song.title}">

                        </div>
                        <div class="card-title" title="${song.title}">${song.title}</div>
                        <div class="card-subtitle" title="${artistName}">${artistName}</div>
                        <a href="/song/?id=${song.id}" class="stretched-link"></a>
                    </div>
                    `;
                    container.insertAdjacentHTML('beforeend', cardHTML);
                });
                
                // Nếu không có bài nào
                if(data.data.items.length === 0) {
                    container.innerHTML = '<div class="text-secondary p-3">Chưa có bài hát thịnh hành nào.</div>';
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
                    container.innerHTML = '';
                    section.style.display = 'block';
                    
                    data.data.items.forEach(songData => {
                        const song = songData.song || songData;
                        const artistName = song.artist ? song.artist.display_name : 'Nghệ sĩ ẩn danh';
                        const coverImg = song.cover_image ? song.cover_image : 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                        const cardHTML = `
                        <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                            <div class="card-image-wrapper">
                                <img src="${coverImg}" alt="${song.title}">

                            </div>
                            <div class="card-title" title="${song.title}">${song.title}</div>
                            <div class="card-subtitle" title="${artistName}">${artistName}</div>
                            <a href="/song/?id=${song.id}" class="stretched-link"></a>
                        </div>`;
                        container.insertAdjacentHTML('beforeend', cardHTML);
                    });
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
                    container.innerHTML = '';
                    section.style.display = 'block';

                    data.data.items.forEach(artist => {
                        const avatarImg = artist.avatar ? artist.avatar : 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                        const cardHTML = `
                        <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                            <div class="card-image-wrapper" style="border-radius: 50%; overflow: hidden;">
                                <img src="${avatarImg}" alt="${artist.display_name}" style="object-fit: cover;">
                            </div>
                            <div class="card-title" title="${artist.display_name}">${artist.display_name}</div>
                            <div class="card-subtitle">Nghệ sĩ</div>
                            <a href="/profile/${artist.username}/" class="stretched-link"></a>
                        </div>`;
                        container.insertAdjacentHTML('beforeend', cardHTML);
                    });
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
                    container.innerHTML = '';
                    section.style.display = 'block';

                    data.data.items.forEach(playlist => {
                        const coverImg = playlist.cover_image ? playlist.cover_image : 'https://images.unsplash.com/photo-1493225457124-a1a2a5f5f924?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
                        const ownerName = playlist.owner ? playlist.owner.display_name : '';
                        const songCount = playlist.song_count !== undefined ? `${playlist.song_count} bài` : '';
                        const cardHTML = `
                        <div class="playlist-card position-relative" style="min-width: 160px; max-width: 160px;">
                            <div class="card-image-wrapper">
                                <img src="${coverImg}" alt="${playlist.title}">

                            </div>
                            <div class="card-title" title="${playlist.title}">${playlist.title}</div>
                            <div class="card-subtitle">${ownerName} ${songCount ? '&bull; ' + songCount : ''}</div>
                            <a href="/playlist/detail/?id=${playlist.id}" class="stretched-link"></a>
                        </div>`;
                        container.insertAdjacentHTML('beforeend', cardHTML);
                    });
                }
            })
            .catch(error => console.error('Lỗi gợi ý playlist:', error));
    }
});
