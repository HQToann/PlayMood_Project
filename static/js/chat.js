// static/js/chat.js

let chatSocket = null;
let currentConversationId = null;
let currentTargetUserId = null;
let typingTimeout = null;
let isTyping = false;

// Variables for grouping messages
let lastMessageSenderId = null;
let lastMessageTimestamp = null;

// DOM Elements
const chatWidget = document.getElementById('chatWidget');
const closeChatBtn = document.getElementById('closeChatBtn');
const chatHeaderName = document.getElementById('chatHeaderName');
const chatHeaderAvatar = document.getElementById('chatHeaderAvatar');
const chatHeaderStatus = document.getElementById('chatHeaderStatus');
const chatHeaderOnlineDot = document.getElementById('chatHeaderOnlineDot');
const chatHeaderProfileLink = document.getElementById('chatHeaderProfileLink');

const chatMessages = document.getElementById('chatMessages');
const chatBody = document.getElementById('chatBody');
const chatLoading = document.getElementById('chatLoading');
const chatTypingIndicator = document.getElementById('chatTypingIndicator');

const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');

// Đóng chat
if (closeChatBtn) {
    closeChatBtn.addEventListener('click', () => {
        closeChat();
    });
}

function closeChat() {
    chatWidget.classList.add('d-none');
    if (chatSocket) {
        chatSocket.close();
        chatSocket = null;
    }
    currentConversationId = null;
    currentTargetUserId = null;
    lastMessageSenderId = null;
    lastMessageTimestamp = null;
}

// Mở chat từ màn hình bạn bè
window.openChat = async function(friendId, friendName, friendAvatar, isOnline = false) {
    if (!window.CURRENT_USER_AUTHENTICATED) {
        alert("Vui lòng đăng nhập để nhắn tin!");
        return;
    }

    // Nếu đang mở khung chat của người này thì thôi
    if (currentTargetUserId === friendId && !chatWidget.classList.contains('d-none')) {
        return;
    }

    // Đóng socket cũ nếu có
    if (chatSocket) {
        chatSocket.close();
    }

    currentTargetUserId = friendId;
    
    // Cập nhật giao diện ban đầu
    chatHeaderName.innerText = friendName;
    chatHeaderAvatar.src = friendAvatar;
    chatHeaderProfileLink.href = `/profile/${friendId}/`;
    
    if (isOnline) {
        chatHeaderStatus.innerText = "Đang hoạt động";
        chatHeaderOnlineDot.classList.remove('offline');
    } else {
        chatHeaderStatus.innerText = "Không hoạt động";
        chatHeaderOnlineDot.classList.add('offline');
    }

    // Hiển thị khung chat (Loading)
    chatWidget.classList.remove('d-none');
    chatMessages.innerHTML = '';
    chatLoading.classList.remove('d-none');
    chatInput.value = '';
    updateSendButtonState();

    try {
        // Lấy hoặc tạo mới Conversation (API POST)
        const csrfToken = getCookie('csrftoken'); // Dùng hàm getCookie từ main.js
        const response = await fetch('/api/v1/chat/conversations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ target_user_id: friendId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentConversationId = data.data.id;
            // Tải tin nhắn cũ
            await loadMessageHistory(currentConversationId);
            // Kết nối WebSocket
            connectWebSocket(currentConversationId);
        } else {
            alert(data.error?.message || "Không thể mở cuộc trò chuyện.");
            closeChat();
        }
    } catch (error) {
        console.error("Chat API Error:", error);
        alert("Lỗi kết nối tới máy chủ Chat.");
        closeChat();
    } finally {
        chatLoading.classList.add('d-none');
    }
};

// Tải lịch sử tin nhắn
async function loadMessageHistory(conversationId) {
    try {
        const response = await fetch(`/api/v1/chat/conversations/${conversationId}/messages/?page=1&page_size=50`);
        const data = await response.json();
        
        if (data.success && data.data.items) {
            chatMessages.innerHTML = '';
            lastMessageSenderId = null;
            lastMessageTimestamp = null;
            
            // Xóa .reverse() vì BE đã trả về tin nhắn cũ ở đầu, tin mới ở cuối (tăng dần theo thời gian)
            const items = data.data.items; 
            items.forEach(msg => {
                appendMessageToUI(msg);
            });
            scrollToBottom();
        }
    } catch (error) {
        console.error("Lỗi tải lịch sử tin nhắn", error);
    }
}

// Kết nối WebSocket
function connectWebSocket(conversationId) {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${protocol}${window.location.host}/ws/chat/conversation/${conversationId}/`;
    
    chatSocket = new WebSocket(wsUrl);
    
    chatSocket.onopen = function(e) {
        console.log("Đã kết nối WebSocket Chat");
        // Gửi event đã xem khi vừa kết nối vào room
        chatSocket.send(JSON.stringify({
            'type': 'mark_read'
        }));
    };
    
    chatSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const eventType = data.type;
        
        if (eventType === 'new_message') {
            const msg = data.data;
            appendMessageToUI(msg);
            scrollToBottom();
            
            // Ẩn chữ đang gõ nếu có tin nhắn gửi tới
            if (msg.sender && msg.sender.id !== window.CURRENT_USER_ID) {
                hideTypingIndicator();
                // Đánh dấu đã đọc nếu đang mở chat
                if (document.visibilityState === 'visible') {
                    chatSocket.send(JSON.stringify({ 'type': 'mark_read' }));
                }
            }
        } else if (eventType === 'typing_status') {
            if (data.user_id !== window.CURRENT_USER_ID) {
                if (data.is_typing) {
                    showTypingIndicator();
                } else {
                    hideTypingIndicator();
                }
            }
        } else if (eventType === 'read_receipt') {
            // Có thể xử lý hiện chữ "Đã xem" dưới tin nhắn cuối cùng
        }
    };
    
    chatSocket.onclose = function(e) {
        console.log("WebSocket Chat bị đóng");
    };
}

// Render bong bóng tin nhắn
function appendMessageToUI(msg) {
    const isMe = msg.sender && msg.sender.id === window.CURRENT_USER_ID;
    const msgTime = new Date(msg.created_at);
    
    // 1. Phân tích khoảng cách thời gian (Time Divider)
    let showTimeDivider = false;
    if (!lastMessageTimestamp) {
        showTimeDivider = true;
    } else {
        const diffMinutes = (msgTime - lastMessageTimestamp) / (1000 * 60);
        if (diffMinutes > 30) { // Nếu cách nhau hơn 30 phút thì hiện mốc thời gian
            showTimeDivider = true;
        }
    }
    
    if (showTimeDivider) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'text-center text-muted-custom my-3';
        timeDiv.style.fontSize = '0.75rem';
        const formattedTime = msgTime.toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'}) + ' ' + msgTime.toLocaleDateString('vi-VN', {day: 'numeric', month: 'long', year: 'numeric'});
        timeDiv.innerText = formattedTime;
        chatMessages.appendChild(timeDiv);
    }
    
    // 2. Ẩn avatar của tin nhắn cũ cùng cụm (để avatar luôn ở tin cuối cùng như Messenger)
    if (!isMe && lastMessageSenderId === msg.sender?.id && !showTimeDivider) {
        const previousThem = chatMessages.querySelectorAll('.msg-wrapper.them');
        if (previousThem.length > 0) {
            const lastThem = previousThem[previousThem.length - 1];
            const oldAvatar = lastThem.querySelector('.msg-avatar-img');
            if (oldAvatar) {
                oldAvatar.style.visibility = 'hidden'; // Giấu đi nhưng vẫn chiếm diện tích
            }
        }
    }

    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${isMe ? 'me' : 'them'}`;
    
    // Cấu trúc flex ngang cho wrapper để đặt avatar
    wrapper.style.display = 'flex';
    wrapper.style.flexDirection = 'row';
    wrapper.style.alignItems = 'flex-end'; // Avatar sẽ nằm ở đáy bong bóng
    wrapper.style.gap = '8px';
    wrapper.style.marginBottom = '2px';
    
    // Nếu là tin nhắn mới khác người gửi, cách ra 1 tí
    if (lastMessageSenderId !== msg.sender?.id || showTimeDivider) {
        wrapper.style.marginTop = '10px';
    }
    
    let contentHtml = '';
    
    if (msg.image_url) {
        contentHtml += `<img src="${msg.image_url}" class="msg-image" onclick="window.open(this.src, '_blank')">`;
    }
    if (msg.content) {
        const text = msg.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        contentHtml += `<div>${text}</div>`;
    }
    if (msg.shared_song) {
        const song = msg.shared_song;
        const fallbackCover = "https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80";
        contentHtml += `
            <a href="javascript:void(0)" onclick="if(typeof playSong === 'function') playSong('${song.id}')" class="msg-song-card text-decoration-none">
                <img src="${song.cover_image || fallbackCover}" class="msg-song-cover shadow-sm">
                <div class="overflow-hidden">
                    <div class="text-truncate fw-bold text-white" style="font-size:0.85rem;">${song.title}</div>
                    <div class="text-truncate text-white-50" style="font-size:0.75rem;"><i class="bi bi-music-note-beamed text-accent"></i> Bài hát</div>
                </div>
            </a>
        `;
    }
    if (msg.shared_album) {
        const album = msg.shared_album;
        const fallbackCover = "https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80";
        contentHtml += `
            <a href="/album/${album.id}/" target="_blank" class="msg-song-card text-decoration-none">
                <img src="${album.cover_image || fallbackCover}" class="msg-song-cover shadow-sm">
                <div class="overflow-hidden">
                    <div class="text-truncate fw-bold text-white" style="font-size:0.85rem;">${album.title}</div>
                    <div class="text-truncate text-white-50" style="font-size:0.75rem;"><i class="bi bi-disc text-accent"></i> Album</div>
                </div>
            </a>
        `;
    }
    if (msg.shared_playlist) {
        const playlist = msg.shared_playlist;
        const fallbackCover = "https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80";
        contentHtml += `
            <a href="/playlist/${playlist.id}/" target="_blank" class="msg-song-card text-decoration-none">
                <img src="${playlist.cover_image || fallbackCover}" class="msg-song-cover shadow-sm">
                <div class="overflow-hidden">
                    <div class="text-truncate fw-bold text-white" style="font-size:0.85rem;">${playlist.title}</div>
                    <div class="text-truncate text-white-50" style="font-size:0.75rem;"><i class="bi bi-collection-play text-accent"></i> Playlist</div>
                </div>
            </a>
        `;
    }
    if (!contentHtml) return;

    let avatarHtml = '';
    if (!isMe) {
        const avatarUrl = msg.sender?.avatar || 'https://ui-avatars.com/api/?name=User';
        avatarHtml = `<img src="${avatarUrl}" class="rounded-circle msg-avatar-img" style="width: 28px; height: 28px; object-fit: cover; flex-shrink: 0; transition: visibility 0s;">`;
    }
    
    // Gói bong bóng vào một div con để căn lề phải cho tin nhắn của mình
    wrapper.innerHTML = `
        ${avatarHtml}
        <div style="display: flex; flex-direction: column; max-width: ${isMe ? '100%' : 'calc(100% - 36px)'}; ${isMe ? 'align-items: flex-end;' : 'align-items: flex-start;'}">
            <div class="msg-bubble">${contentHtml}</div>
        </div>
    `;
    
    chatMessages.appendChild(wrapper);
    
    lastMessageSenderId = msg.sender?.id;
    lastMessageTimestamp = msgTime;
}

// Khởi tạo các biến UI mới
const chatAttachmentPreview = document.getElementById('chatAttachmentPreview');
const chatAttachmentPreviewContent = document.getElementById('chatAttachmentPreviewContent');
const chatRemoveAttachmentBtn = document.getElementById('chatRemoveAttachmentBtn');
let pendingAttachment = null; // Có thể là {type: 'image', file: File, preview: string} hoặc {type: 'song', id: string, title: string, cover: string}

// Xử lý hiển thị Preview
function updateAttachmentPreview() {
    if (!pendingAttachment) {
        chatAttachmentPreview.classList.add('d-none');
        chatAttachmentPreview.classList.remove('d-flex');
        chatAttachmentPreviewContent.innerHTML = '';
        updateSendButtonState();
        return;
    }

    chatAttachmentPreview.classList.remove('d-none');
    chatAttachmentPreview.classList.add('d-flex');
    
    if (pendingAttachment.type === 'image') {
        chatAttachmentPreviewContent.innerHTML = `
            <img src="${pendingAttachment.preview}" class="rounded" style="width: 40px; height: 40px; object-fit: cover;">
            <span class="text-truncate text-white" style="font-size: 0.85rem;">Hình ảnh đính kèm</span>
        `;
    } else if (pendingAttachment.type === 'song') {
        chatAttachmentPreviewContent.innerHTML = `
            <img src="${pendingAttachment.cover}" class="rounded" style="width: 40px; height: 40px; object-fit: cover;">
            <span class="text-truncate text-white" style="font-size: 0.85rem;">${pendingAttachment.title}</span>
        `;
    }
    
    updateSendButtonState();
}

if (chatRemoveAttachmentBtn) {
    chatRemoveAttachmentBtn.addEventListener('click', function() {
        pendingAttachment = null;
        if(chatImageInput) chatImageInput.value = '';
        updateAttachmentPreview();
    });
}

// Xử lý Gửi tin nhắn (Cả text và attachment)
chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    
    if (!text && !pendingAttachment) return; // Không có gì để gửi
    if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) return;
    
    // Nếu có ảnh đính kèm, tải ảnh lên trước
    if (pendingAttachment && pendingAttachment.type === 'image') {
        const file = pendingAttachment.file;
        
        // Disable UI tạm thời
        const originalValue = chatInput.value;
        chatInput.value = 'Đang tải ảnh lên...';
        chatInput.disabled = true;
        chatSendBtn.disabled = true;
        
        try {
            const formData = new FormData();
            formData.append('image', file);
            
            const csrfToken = getCookie('csrftoken');
            const response = await fetch('/api/v1/chat/upload-image/', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success && data.data.image_url) {
                // Gửi tin nhắn có chứa ảnh
                chatSocket.send(JSON.stringify({
                    'type': 'send_message',
                    'content': text,
                    'image_url': data.data.image_url
                }));
            } else {
                alert(data.error?.message || 'Lỗi tải ảnh');
                return; // Dừng lại nếu lỗi
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối khi tải ảnh');
            return;
        } finally {
            chatInput.value = originalValue;
            chatInput.disabled = false;
        }
    } 
    // Nếu đính kèm là nhạc
    else if (pendingAttachment && pendingAttachment.type === 'song') {
        chatSocket.send(JSON.stringify({
            'type': 'send_message',
            'content': text,
            'shared_song_id': pendingAttachment.id
        }));
    }
    // Gửi tin nhắn text thuần tuý
    else {
        chatSocket.send(JSON.stringify({
            'type': 'send_message',
            'content': text
        }));
    }
    
    // Reset UI sau khi gửi
    chatInput.value = '';
    pendingAttachment = null;
    if(chatImageInput) chatImageInput.value = '';
    updateAttachmentPreview();
    
    // Reset typing status
    isTyping = false;
    chatSocket.send(JSON.stringify({ 'type': 'typing_status', 'is_typing': false }));
});

// Xử lý Chọn ảnh (Chỉ lưu vào Preview, không gửi ngay)
const chatImageInput = document.getElementById('chatImageInput');
if (chatImageInput) {
    chatImageInput.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            alert('Vui lòng chọn file ảnh hợp lệ');
            this.value = '';
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            alert('Kích thước ảnh không được vượt quá 5MB');
            this.value = '';
            return;
        }
        
        // Đọc file để hiển thị preview
        const reader = new FileReader();
        reader.onload = function(e) {
            pendingAttachment = {
                type: 'image',
                file: file,
                preview: e.target.result
            };
            updateAttachmentPreview();
        };
        reader.readAsDataURL(file);
    });
}

// Auto Resize Input & Bắt sự kiện gõ phím
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight < 120 ? this.scrollHeight : 120) + 'px';
    updateSendButtonState();
    
    // Báo trạng thái đang gõ
    if (!isTyping && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        isTyping = true;
        chatSocket.send(JSON.stringify({ 'type': 'typing_status', 'is_typing': true }));
    }
    
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
        isTyping = false;
        if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
            chatSocket.send(JSON.stringify({ 'type': 'typing_status', 'is_typing': false }));
        }
    }, 2000);
});

// Nhấn Enter để gửi (Shift+Enter để xuống dòng)
chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

function updateSendButtonState() {
    if (chatInput.value.trim().length > 0 || pendingAttachment !== null) {
        chatSendBtn.removeAttribute('disabled');
        chatSendBtn.classList.add('text-accent');
        chatSendBtn.classList.remove('text-muted-custom');
    } else {
        chatSendBtn.setAttribute('disabled', 'true');
        chatSendBtn.classList.remove('text-accent');
        chatSendBtn.classList.add('text-muted-custom');
        chatInput.style.height = 'auto'; // Reset height
    }
}

// === CHAT SHARE MUSIC MODAL LOGIC ===
const chatShareMusicModalEl = document.getElementById('chatShareMusicModal');
const chatMusicSearchInput = document.getElementById('chatMusicSearchInput');
const chatShareMusicResults = document.getElementById('chatShareMusicResults');
const chatShareMusicTitle = document.getElementById('chatShareMusicTitle');

let musicSearchDebounce = null;

if (chatShareMusicModalEl) {
    
    // Khi mở modal, lấy danh sách gợi ý
    chatShareMusicModalEl.addEventListener('show.bs.modal', async function () {
        chatMusicSearchInput.value = '';
        chatShareMusicTitle.innerText = 'GỢI Ý CHO BẠN';
        chatShareMusicResults.innerHTML = '<div class="text-center text-muted-custom py-4"><div class="spinner-border spinner-border-sm"></div></div>';
        
        try {
            const res = await fetch('/api/v1/recommendations/for-you/');
            const data = await res.json();
            
            // Xử lý cả trường hợp data.data là mảng (nếu API cũ) hoặc object có .items (nếu API mới)
            const results = Array.isArray(data.data) ? data.data : (data.data?.items || []);
            
            if (data.success && results.length > 0) {
                renderMusicResults(results);
            } else {
                chatShareMusicResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Không có gợi ý nào. Hãy tìm kiếm...</div>';
            }
        } catch (e) {
            chatShareMusicResults.innerHTML = '<div class="text-danger text-center py-3 small">Lỗi kết nối.</div>';
            console.error('Fetch recommendations error:', e);
        }
    });
    
    // Tìm kiếm nhạc
    chatMusicSearchInput.addEventListener('input', function(e) {
        clearTimeout(musicSearchDebounce);
        const query = e.target.value.trim();
        
        if (!query) {
            // Có thể load lại gợi ý hoặc hiện rỗng
            chatShareMusicTitle.innerText = 'GỢI Ý CHO BẠN';
            chatShareMusicResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Gõ để tìm kiếm...</div>';
            return;
        }
        
        chatShareMusicTitle.innerText = 'KẾT QUẢ TÌM KIẾM';
        chatShareMusicResults.innerHTML = '<div class="text-center text-muted-custom py-4"><div class="spinner-border spinner-border-sm"></div></div>';
        
        musicSearchDebounce = setTimeout(async () => {
            try {
                const res = await fetch(`/api/v1/music/songs/?q=${encodeURIComponent(query)}`);
                const data = await res.json();
                
                const results = Array.isArray(data.data) ? data.data : (data.data?.items || []);
                
                if (data.success && results.length > 0) {
                    renderMusicResults(results);
                } else {
                    chatShareMusicResults.innerHTML = '<div class="text-center text-muted-custom py-3 small">Không tìm thấy kết quả phù hợp.</div>';
                }
            } catch (err) {
                chatShareMusicResults.innerHTML = '<div class="text-danger text-center py-3 small">Lỗi kết nối.</div>';
                console.error('Search songs error:', err);
            }
        }, 500);
    });
}

function renderMusicResults(songs) {
    chatShareMusicResults.innerHTML = '';
    
    songs.forEach(song => {
        const item = document.createElement('div');
        item.className = 'd-flex align-items-center justify-content-between p-2 rounded';
        item.style.cursor = 'pointer';
        item.style.transition = 'background 0.2s';
        
        // Hover effect
        item.onmouseover = () => item.style.background = 'rgba(255,255,255,0.05)';
        item.onmouseout = () => item.style.background = 'transparent';
        
        item.onclick = () => {
            // Chọn bài này làm pendingAttachment
            pendingAttachment = {
                type: 'song',
                id: song.id,
                title: song.title,
                cover: song.cover_image || 'https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80'
            };
            
            bootstrap.Modal.getInstance(chatShareMusicModalEl).hide();
            updateAttachmentPreview();
        };
        
        const fallback = 'https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
        const cover = song.cover_image || fallback;
        const artist = song.artist?.display_name || 'Nghệ sĩ';
        
        item.innerHTML = `
            <div class="d-flex align-items-center gap-3 overflow-hidden">
                <img src="${cover}" class="rounded" style="width: 48px; height: 48px; object-fit: cover;">
                <div class="overflow-hidden">
                    <div class="text-truncate fw-bold text-white mb-1" style="font-size:0.9rem;">${song.title}</div>
                    <div class="text-truncate text-white-50" style="font-size:0.8rem;">${artist}</div>
                </div>
            </div>
            <i class="bi bi-send text-accent fs-5"></i>
        `;
        
        chatShareMusicResults.appendChild(item);
    });
}

function showTypingIndicator() {
    chatTypingIndicator.classList.remove('d-none');
    scrollToBottom();
}

function hideTypingIndicator() {
    chatTypingIndicator.classList.add('d-none');
}

function scrollToBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
}
