// static/js/chat.js

let chatSocket = null;
let currentConversationId = null;
let currentTargetUserId = null;
let typingTimeout = null;
let isTyping = false;

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
            // API thường trả về tin nhắn mới nhất ở đầu mảng (descending), ta cần đảo ngược lại để vẽ từ trên xuống
            const items = data.data.items.reverse(); 
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
            if (msg.sender_id !== window.CURRENT_USER_ID) {
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
    const isMe = msg.sender_id === window.CURRENT_USER_ID;
    const wrapper = document.createElement('div');
    wrapper.className = `msg-wrapper ${isMe ? 'me' : 'them'}`;
    
    let contentHtml = '';
    
    // Nếu có ảnh
    if (msg.image_url) {
        contentHtml += `<img src="${msg.image_url}" class="msg-image" onclick="window.open(this.src, '_blank')">`;
    }
    
    // Nếu có text
    if (msg.content) {
        // Thoát thẻ HTML để tránh XSS
        const text = msg.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        contentHtml += `<div>${text}</div>`;
    }
    
    // Nếu có chia sẻ bài hát
    if (msg.shared_song) {
        const song = msg.shared_song;
        const fallbackCover = "https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80";
        contentHtml += `
            <a href="javascript:void(0)" onclick="if(typeof playSong === 'function') playSong('${song.id}')" class="msg-song-card text-decoration-none">
                <img src="${song.cover_image || fallbackCover}" class="msg-song-cover shadow-sm">
                <div class="overflow-hidden">
                    <div class="text-truncate fw-bold text-white" style="font-size:0.85rem;">${song.title}</div>
                    <div class="text-truncate text-white-50" style="font-size:0.75rem;"><i class="bi bi-play-circle-fill text-accent"></i> Phát ngay</div>
                </div>
            </a>
        `;
    }
    
    // Nếu hoàn toàn không có gì (lỗi data) thì bỏ qua
    if (!contentHtml) return;

    wrapper.innerHTML = `
        <div class="msg-bubble">${contentHtml}</div>
    `;
    
    chatMessages.appendChild(wrapper);
}

// Xử lý Gửi tin nhắn
chatForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    
    if (!text && !document.getElementById('chatImageInput').files.length) return; // Không có gì để gửi
    if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) return;
    
    // Gửi text (Image sẽ xử lý riêng qua API upload ảnh, ở đây giả lập text trước)
    chatSocket.send(JSON.stringify({
        'type': 'send_message',
        'content': text
    }));
    
    chatInput.value = '';
    updateSendButtonState();
    
    // Reset typing status
    isTyping = false;
    chatSocket.send(JSON.stringify({ 'type': 'typing_status', 'is_typing': false }));
});

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
    if (chatInput.value.trim().length > 0) {
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
