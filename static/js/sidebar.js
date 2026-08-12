document.addEventListener('DOMContentLoaded', async () => {
    const sidebarContainer = document.getElementById('sidebarPlaylistsContainer');
    if (!sidebarContainer) return;

    if (typeof window.CURRENT_USER_AUTHENTICATED !== 'undefined' && !window.CURRENT_USER_AUTHENTICATED) {
        sidebarContainer.innerHTML = '';
        return;
    }

    try {
        const res = await fetch('/api/v1/playlists/');
        if (!res.ok) throw new Error('Failed to load playlists');
        
        const data = await res.json();
        if (!data.success) throw new Error(data.error?.message || 'Lỗi tải playlist');
        
        const playlists = data.data.items || [];
        
        if (playlists.length === 0) {
            sidebarContainer.innerHTML = '';
            return;
        }

        let html = '';
        playlists.forEach((pl, index) => {
            const imgUrl = pl.cover_image || 'https://images.unsplash.com/photo-1518609878373-06d740f60d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80';
            // Only show a limited number of playlists on sidebar (e.g. 5)
            if (index < 5) {
                html += `
                    <a href="/playlist/detail/?id=${pl.id}" class="text-decoration-none text-white d-block">
                        <div class="playlist-item mt-2 hover-bg-light p-1 rounded" style="transition: background-color 0.2s;">
                            <img src="${imgUrl}" alt="cover" class="playlist-img">
                            <div>
                                <div style="font-size: 0.85rem; font-weight: 600;" class="text-truncate">${pl.title}</div>
                                <div style="font-size: 0.75rem; color: var(--text-secondary);" class="text-truncate">${pl.is_public ? 'Công khai' : 'Riêng tư'}</div>
                            </div>
                        </div>
                    </a>
                `;
            }
        });
        
        sidebarContainer.innerHTML = html;
        
    } catch (error) {
        console.error('Sidebar playlists load error:', error);
        sidebarContainer.innerHTML = '';
    }
});
