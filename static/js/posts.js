// File: static/js/posts.js

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// -- TẢI BẢNG TIN (FEED) --
async function loadFeed() {
    const feedContainer = document.getElementById('postsFeedContainer');
    if(!feedContainer) return;

    try {
        const res = await fetch('/api/v1/posts/?page=1&page_size=10');
        const data = await res.json();
        if(data.success) {
            renderFeed(data.data.items);
        }
    } catch(e) {
        console.error(e);
    }
}

function timeSince(dateString) {
    const date = new Date(dateString);
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " năm";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " tháng";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " ngày";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " giờ";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " phút";
    return Math.floor(seconds) + " giây";
}

function renderFeed(posts) {
    const feedContainer = document.getElementById('postsFeedContainer');
    feedContainer.innerHTML = ''; // Clear loading
    
    if(posts.length === 0) {
        feedContainer.innerHTML = '<div class="text-center text-muted-custom py-5">Chưa có bài viết nào. Hãy là người đầu tiên đăng bài!</div>';
        return;
    }

    posts.forEach(post => {
        const avatar = post.author.avatar || 'https://ui-avatars.com/api/?name=User';
        
        let gridHtml = '';
        if(post.media && post.media.length > 0) {
            const count = post.media.length;
            const gridClass = count === 1 ? '' : count === 2 ? 'grid-2' : count === 3 ? 'grid-3' : 'grid-4';
            gridHtml = `<div class="post-image-grid ${gridClass} mt-2">`;
            post.media.slice(0, 4).forEach((media, idx) => {
                if(idx === 3 && count > 4) {
                    gridHtml += `<div class="grid-img more-overlay" style="background-image: url('${media.url}');"><span>+${count - 3}</span></div>`;
                } else {
                    gridHtml += `<div class="grid-img" style="background-image: url('${media.url}');"></div>`;
                }
            });
            gridHtml += `</div>`;
        }

        let sharedSongHtml = '';
        if (post.shared_song) {
            sharedSongHtml = `
            <div class="mt-2 p-3 bg-dark rounded d-flex align-items-center gap-3 cursor-pointer" onclick="playSong('${post.shared_song.id}')" style="border: 1px solid rgba(255,255,255,0.1);">
                <div class="position-relative">
                    <img src="${post.shared_song.cover_image}" class="rounded" width="60" height="60" style="object-fit: cover;">
                    <div class="position-absolute top-50 start-50 translate-middle text-white bg-dark bg-opacity-50 rounded-circle d-flex align-items-center justify-content-center" style="width: 30px; height: 30px;">
                        <i class="bi bi-play-fill"></i>
                    </div>
                </div>
                <div class="flex-grow-1 overflow-hidden">
                    <div class="fw-bold text-white text-truncate">${post.shared_song.title}</div>
                    <div class="text-muted-custom small text-truncate">${post.shared_song.artist}</div>
                </div>
            </div>`;
        }

        const REACTION_EMOJIS = {
            'LIKE': '👍',
            'LOVE': '❤️',
            'HAHA': '😂',
            'WOW': '😮',
            'SAD': '😢',
            'ANGRY': '😡'
        };

        let reactionStackHtml = '';
        if (post.top_reactions && post.top_reactions.length > 0) {
            post.top_reactions.forEach((r, idx) => {
                const margin = idx > 0 ? 'margin-left: -8px;' : '';
                reactionStackHtml += `<span style="${margin}">${REACTION_EMOJIS[r] || '👍'}</span>`;
            });
        }

        let mainActionBtnClass = 'btn-link text-muted-custom text-decoration-none fw-bold btn-action react-trigger';
        let mainActionBtnContent = '<i class="bi bi-hand-thumbs-up"></i> Thích';
        
        if (post.current_user_reaction) {
            const type = post.current_user_reaction;
            mainActionBtnClass += ` reacted-${type.toLowerCase()}`;
            
            let iconHtml = '';
            let text = '';
            switch(type) {
                case 'LIKE': iconHtml = '<i class="bi bi-hand-thumbs-up-fill fs-5"></i>'; text = 'Thích'; break;
                case 'LOVE': iconHtml = '<i class="bi bi-heart-fill fs-5"></i>'; text = 'Yêu thích'; break;
                case 'HAHA': iconHtml = '<i class="bi bi-emoji-laughing-fill fs-5"></i>'; text = 'Haha'; break;
                case 'WOW': iconHtml = '<i class="bi bi-emoji-surprise-fill fs-5"></i>'; text = 'Wow'; break;
                case 'SAD': iconHtml = '<i class="bi bi-emoji-frown-fill fs-5"></i>'; text = 'Buồn'; break;
                case 'ANGRY': iconHtml = '<i class="bi bi-emoji-angry-fill fs-5"></i>'; text = 'Phẫn nộ'; break;
            }
            mainActionBtnContent = `${iconHtml} ${text}`;
        }

        const html = `
        <div class="post-card bg-card rounded-4 p-3 mb-4 shadow-sm" data-post-id="${post.id}">
            <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="d-flex align-items-center gap-2">
                    <img src="${avatar}" class="rounded-circle" width="40" height="40" style="object-fit: cover;">
                    <div>
                        <h6 class="mb-0 fw-bold text-white">${post.author.display_name}</h6>
                        <small class="text-muted-custom">${timeSince(post.created_at)} trước</small>
                    </div>
                </div>
                <button class="btn btn-link text-muted-custom p-0"><i class="bi bi-three-dots"></i></button>
            </div>
            
            <div class="post-body text-white mb-2">
                <p class="mb-2" style="font-size: 0.95rem;">${post.content}</p>
                ${gridHtml}
                ${sharedSongHtml}
            </div>
            
            <div class="d-flex align-items-center justify-content-between pb-2 border-bottom border-secondary mb-2">
                <div class="d-flex align-items-center gap-1">
                    <div class="reaction-stack d-flex align-items-center fs-5" style="margin-right: 4px;">
                        ${reactionStackHtml}
                    </div>
                    <span class="text-muted-custom small" id="reaction-count-${post.id}">${post.reactions_count > 0 ? post.reactions_count : ''}</span>
                </div>
                <div class="text-muted-custom small">
                    <span class="me-3">${post.comments_count > 0 ? post.comments_count + ' bình luận' : ''}</span>
                    <span>12 chia sẻ</span>
                </div>
            </div>
            
            <div class="d-flex align-items-center justify-content-between">
                <div class="position-relative reaction-container">
                    <button class="btn ${mainActionBtnClass}">
                        ${mainActionBtnContent}
                    </button>
                    <div class="reaction-popover shadow-lg rounded-pill px-3 py-2 d-flex gap-2">
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="LIKE" title="Thích">👍</button>
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="LOVE" title="Yêu thích">❤️</button>
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="HAHA" title="Haha">😂</button>
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="WOW" title="Wow">😮</button>
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="SAD" title="Buồn">😢</button>
                        <button class="btn btn-sm btn-link p-0 react-icon text-decoration-none fs-3" data-type="ANGRY" title="Phẫn nộ">😡</button>
                    </div>
                </div>
                <button class="btn btn-link text-muted-custom text-decoration-none fw-bold action-btn btn-comment">
                    <i class="bi bi-chat fs-5"></i> Bình luận
                </button>
                <button class="btn btn-link text-muted-custom text-decoration-none fw-bold action-btn btn-share" data-bs-toggle="modal" data-bs-target="#sharePostModal">
                    <i class="bi bi-share fs-5"></i> Chia sẻ
                </button>
            </div>
        </div>
        `;
        feedContainer.insertAdjacentHTML('beforeend', html);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadFeed();

    // -- XỬ LÝ PREVIEW ẢNH & NHẠC --
    const postImageInput = document.getElementById('postImageInput');
    const postPreviewContainer = document.getElementById('postPreviewContainer');
    const postImagePreview = document.getElementById('postImagePreview');
    const postSongPreview = document.getElementById('postSongPreview');
    const postSharedSongId = document.getElementById('postSharedSongId');
    const removePostPreviewBtn = document.getElementById('removePostPreviewBtn');

    function resetPreview() {
        postPreviewContainer.classList.add('d-none');
        postImagePreview.classList.add('d-none');
        postSongPreview.classList.add('d-none');
        postImagePreview.src = '';
        if(postImageInput) postImageInput.value = '';
        if(postSharedSongId) postSharedSongId.value = '';
    }

    if(removePostPreviewBtn) {
        removePostPreviewBtn.addEventListener('click', resetPreview);
    }

    if(postImageInput) {
        postImageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Hide song preview if any, but DO NOT call resetPreview() which clears the file input
                    postSongPreview.classList.add('d-none');
                    if(postSharedSongId) postSharedSongId.value = '';
                    
                    postPreviewContainer.classList.remove('d-none');
                    postImagePreview.classList.remove('d-none');
                    postImagePreview.src = e.target.result;
                }
                reader.readAsDataURL(this.files[0]);
            }
        });
    }

    // -- CHIA SẺ NHẠC TRONG BÀI VIẾT --
    const postMusicSearchInput = document.getElementById('postMusicSearchInput');
    const postMusicSearchResults = document.getElementById('postMusicSearchResults');
    const postShareMusicModal = document.getElementById('postShareMusicModal');
    let postMusicSearchDebounce = null;

    if (postShareMusicModal) {
        postShareMusicModal.addEventListener('show.bs.modal', async function () {
            postMusicSearchInput.value = '';
            postMusicSearchResults.innerHTML = '<div class="text-center text-muted-custom py-4"><div class="spinner-border spinner-border-sm"></div></div>';
            
            try {
                const res = await fetch('/api/v1/recommendations/for-you/');
                const data = await res.json();
                const results = Array.isArray(data.data) ? data.data : (data.data?.items || []);
                renderPostMusicResults(results);
            } catch (e) {
                postMusicSearchResults.innerHTML = '<div class="text-center text-danger">Lỗi tải dữ liệu</div>';
            }
        });

        postMusicSearchInput.addEventListener('input', function () {
            clearTimeout(postMusicSearchDebounce);
            const query = this.value.trim();
            if (!query) return;

            postMusicSearchDebounce = setTimeout(async () => {
                postMusicSearchResults.innerHTML = '<div class="text-center text-muted-custom py-4"><div class="spinner-border spinner-border-sm"></div></div>';
                try {
                    const res = await fetch(`/api/v1/search/?q=${encodeURIComponent(query)}`);
                    const data = await res.json();
                    renderPostMusicResults(data.data.songs || []);
                } catch (e) {
                    postMusicSearchResults.innerHTML = '<div class="text-center text-danger">Lỗi tải dữ liệu</div>';
                }
            }, 500);
        });
    }

    function renderPostMusicResults(songs) {
        if (!songs.length) {
            postMusicSearchResults.innerHTML = '<div class="text-center text-muted-custom py-4">Không tìm thấy bài hát nào</div>';
            return;
        }

        postMusicSearchResults.innerHTML = '';
        songs.forEach(song => {
            const item = document.createElement('div');
            item.className = 'd-flex align-items-center gap-3 p-2 rounded cursor-pointer song-row';
            item.style.transition = 'background 0.2s';
            
            const cover = song.cover_image || 'https://images.unsplash.com/photo-1614680376593-902f74a7460c?ixlib=rb-4.0.3&auto=format&fit=crop&w=300&q=80';
            const artist = song.artist?.display_name || 'Nghệ sĩ';
            
            item.innerHTML = `
                <img src="${cover}" class="rounded" style="width: 48px; height: 48px; object-fit: cover;">
                <div class="flex-grow-1 overflow-hidden">
                    <div class="text-white text-truncate fw-bold">${song.title}</div>
                    <div class="text-muted-custom small text-truncate">${artist}</div>
                </div>
            `;
            
            // Hover effect
            item.addEventListener('mouseenter', () => item.style.backgroundColor = 'rgba(255,255,255,0.1)');
            item.addEventListener('mouseleave', () => item.style.backgroundColor = 'transparent');
            
            item.addEventListener('click', () => {
                resetPreview(); // Clear old preview
                postSharedSongId.value = song.id;
                
                document.getElementById('postSongCover').src = cover;
                document.getElementById('postSongTitle').innerText = song.title;
                
                postPreviewContainer.classList.remove('d-none');
                postSongPreview.classList.remove('d-none');
                postSongPreview.classList.add('d-flex');
                
                bootstrap.Modal.getInstance(postShareMusicModal).hide();
            });
            postMusicSearchResults.appendChild(item);
        });
    }

    // -- POST BÀI MỚI --
    const btnSubmitPost = document.getElementById('btnSubmitPost');
    if(btnSubmitPost) {
        btnSubmitPost.addEventListener('click', async () => {
            const content = document.getElementById('postContentInput').value;
            const visibility = document.getElementById('postVisibility').value;
            
            const formData = new FormData();
            formData.append('content', content);
            formData.append('visibility', visibility);
            
            if(postImageInput && postImageInput.files.length > 0) {
                for(let i = 0; i < postImageInput.files.length; i++) {
                    formData.append('images', postImageInput.files[i]);
                }
            }
            if(postSharedSongId && postSharedSongId.value) {
                formData.append('shared_song_id', postSharedSongId.value);
            }
            
            btnSubmitPost.disabled = true;
            btnSubmitPost.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang đăng...';
            
            try {
                const res = await fetch('/api/v1/posts/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrftoken },
                    body: formData
                });
                const data = await res.json();
                if(data.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('createPostModal'));
                    modal.hide();
                    document.getElementById('postContentInput').value = '';
                    resetPreview();
                    loadFeed(); // Reload feed
                } else {
                    alert(data.error.message || 'Lỗi khi đăng bài');
                }
            } catch(e) {
                console.error(e);
            } finally {
                btnSubmitPost.disabled = false;
                btnSubmitPost.innerHTML = 'Đăng';
            }
        });
    }

    // -- EVENT DELEGATION: Tương tác ngầm --
    document.body.addEventListener('click', async (e) => {
        
        // --- 1. THẢ CẢM XÚC ---
        const reactBtn = e.target.closest('.react-icon');
        if (reactBtn) {
            e.preventDefault();
            const postCard = reactBtn.closest('.post-card');
            const postId = postCard.dataset.postId;
            const reactionType = reactBtn.dataset.type;
            
            try {
                const response = await fetch(`/api/v1/posts/${postId}/react/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({ reaction_type: reactionType })
                });
                
                const data = await response.json();
                if (data.success) {
                    updateReactionUI(postCard, data.data);
                }
            } catch (error) {
                console.error(error);
            }
        }
        
        // --- 2. MỞ CHIA SẺ BÀI VIẾT LỚP 1 ---
        const shareBtn = e.target.closest('.btn-share');
        if (shareBtn) {
            const postCard = shareBtn.closest('.post-card');
            window.currentSharePostId = postCard.dataset.postId;
            document.getElementById('shareModalLayer1').style.display = 'block';
            document.getElementById('shareModalLayer2').style.display = 'none';
        }
        
        // --- 3. CHỌN BẠN BÈ ĐỂ CHIA SẺ (LỚP 2) ---
        const friendItem = e.target.closest('.share-friend-item');
        if (friendItem) {
            const conversationId = friendItem.dataset.conversationId;
            document.getElementById('btnConfirmShare').dataset.conversationId = conversationId;
            
            document.getElementById('shareModalLayer1').style.display = 'none';
            document.getElementById('shareModalLayer2').style.display = 'block';
        }
        
        // NÚT BACK (TỪ 2 QUAY VỀ 1)
        if(e.target.closest('#btnBackToLayer1')) {
            document.getElementById('shareModalLayer1').style.display = 'block';
            document.getElementById('shareModalLayer2').style.display = 'none';
        }

        // --- 4. MỞ BÌNH LUẬN ---
        const commentBtn = e.target.closest('.btn-comment');
        if (commentBtn) {
            e.preventDefault();
            const postCard = commentBtn.closest('.post-card');
            window.currentCommentPostId = postCard.dataset.postId;
            
            const commentModal = new bootstrap.Modal(document.getElementById('commentPostModal'));
            commentModal.show();
            
            loadComments(window.currentCommentPostId);
        }
    });
    
    // --- NÚT GỬI CHIA SẺ TRONG CHAT ---
    const btnConfirmShare = document.getElementById('btnConfirmShare');
    if(btnConfirmShare) {
        btnConfirmShare.addEventListener('click', function() {
            const conversationId = this.dataset.conversationId;
            const optionalMessage = document.getElementById('shareOptionalMessage').value;
            
            if (window.chatSocket && window.chatSocket.readyState === window.WebSocket.OPEN) {
                window.chatSocket.send(JSON.stringify({
                    'action': 'send_message',
                    'conversation_id': conversationId,
                    'message': optionalMessage,
                    'shared_post_id': window.currentSharePostId
                }));
                
                const modal = bootstrap.Modal.getInstance(document.getElementById('sharePostModal'));
                modal.hide();
                alert('Đã gửi bài viết qua tin nhắn!');
                document.getElementById('shareOptionalMessage').value = '';
            } else {
                alert('Chat chưa kết nối, vui lòng tải lại trang!');
            }
        });
    }

    // --- XỬ LÝ GỬI BÌNH LUẬN ---
    const submitCommentBtn = document.getElementById('submitCommentBtn');
    if (submitCommentBtn) {
        submitCommentBtn.addEventListener('click', async () => {
            if (!window.currentCommentPostId) return;
            const input = document.getElementById('commentInput');
            const content = input.value.trim();
            if (!content) return;
            
            // Ẩn nút gửi để tránh click nhiều lần
            submitCommentBtn.disabled = true;
            try {
                const response = await fetch(`/api/v1/posts/${window.currentCommentPostId}/comments/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({ content: content })
                });
                
                const data = await response.json();
                if (data.success) {
                    input.value = '';
                    loadComments(window.currentCommentPostId);
                    
                    // Cập nhật số đếm trên giao diện
                    const postCard = document.querySelector(`.post-card[data-post-id="${window.currentCommentPostId}"]`);
                    if (postCard) {
                        const commentsTextSpan = postCard.querySelector('.text-muted-custom.small span.me-3');
                        if (commentsTextSpan) {
                            const currentText = commentsTextSpan.innerText;
                            const match = currentText.match(/(\d+)/);
                            const count = match ? parseInt(match[1]) + 1 : 1;
                            commentsTextSpan.innerText = `${count} bình luận`;
                        }
                    }
                }
            } catch (error) {
                console.error('Error posting comment:', error);
            } finally {
                submitCommentBtn.disabled = false;
            }
        });
        
        // Nhấn Enter để gửi
        document.getElementById('commentInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitCommentBtn.click();
            }
        });
    }

});

// -- HÀM TẢI BÌNH LUẬN --
async function loadComments(postId) {
    const spinner = document.getElementById('commentLoadingSpinner');
    const listContainer = document.getElementById('commentList');
    spinner.classList.remove('d-none');
    listContainer.classList.add('d-none');
    listContainer.innerHTML = '';
    
    try {
        const response = await fetch(`/api/v1/posts/${postId}/comments/`);
        const data = await response.json();
        
        if (data.success) {
            if (data.data.length === 0) {
                listContainer.innerHTML = '<div class="text-center text-muted-custom py-3">Chưa có bình luận nào. Hãy là người đầu tiên!</div>';
            } else {
                data.data.forEach(comment => {
                    const avatar = comment.author.avatar || 'https://ui-avatars.com/api/?name=User';
                    const html = `
                    <div class="d-flex gap-2 mb-3">
                        <img src="${avatar}" class="rounded-circle mt-1" width="36" height="36" style="object-fit: cover;">
                        <div class="flex-grow-1">
                            <div class="bg-dark rounded-4 p-2 px-3 d-inline-block" style="border: 1px solid rgba(255,255,255,0.1);">
                                <h6 class="mb-0 fw-bold text-white small">${comment.author.display_name}</h6>
                                <span class="text-white small">${comment.content}</span>
                            </div>
                            <div class="text-muted-custom small ms-3 mt-1 d-flex gap-3">
                                <span class="cursor-pointer fw-bold">Thích</span>
                                <span class="cursor-pointer fw-bold">Phản hồi</span>
                                <span>${timeSince(comment.created_at)}</span>
                            </div>
                        </div>
                    </div>
                    `;
                    listContainer.insertAdjacentHTML('beforeend', html);
                });
            }
            spinner.classList.add('d-none');
            listContainer.classList.remove('d-none');
        }
    } catch (error) {
        console.error('Error loading comments:', error);
        spinner.classList.add('d-none');
        listContainer.classList.remove('d-none');
        listContainer.innerHTML = '<div class="text-center text-danger py-3">Lỗi tải bình luận.</div>';
    }
}

function updateReactionUI(postCard, resultData) {
    // 1. Cập nhật nút chính (Thích / Yêu thích...)
    const mainActionBtn = postCard.querySelector('.react-trigger');
    if (mainActionBtn) {
        mainActionBtn.classList.remove('reacted-like', 'reacted-love', 'reacted-haha', 'reacted-wow', 'reacted-sad', 'reacted-angry');
        
        if (resultData.action === 'removed') {
            mainActionBtn.innerHTML = '<i class="bi bi-hand-thumbs-up"></i> Thích';
        } else {
            const type = resultData.reaction;
            mainActionBtn.classList.add(`reacted-${type.toLowerCase()}`);
            
            let iconHtml = '';
            let text = '';
            switch(type) {
                case 'LIKE': iconHtml = '<i class="bi bi-hand-thumbs-up-fill fs-5"></i>'; text = 'Thích'; break;
                case 'LOVE': iconHtml = '<i class="bi bi-heart-fill fs-5"></i>'; text = 'Yêu thích'; break;
                case 'HAHA': iconHtml = '<i class="bi bi-emoji-laughing-fill fs-5"></i>'; text = 'Haha'; break;
                case 'WOW': iconHtml = '<i class="bi bi-emoji-surprise-fill fs-5"></i>'; text = 'Wow'; break;
                case 'SAD': iconHtml = '<i class="bi bi-emoji-frown-fill fs-5"></i>'; text = 'Buồn'; break;
                case 'ANGRY': iconHtml = '<i class="bi bi-emoji-angry-fill fs-5"></i>'; text = 'Phẫn nộ'; break;
            }
            mainActionBtn.innerHTML = `${iconHtml} ${text}`;
        }
    }

    // 2. Cập nhật dải biểu tượng (Reaction Stack)
    const stackContainer = postCard.querySelector('.reaction-stack');
    if (stackContainer && resultData.top_reactions) {
        const REACTION_EMOJIS = {
            'LIKE': '👍',
            'LOVE': '❤️',
            'HAHA': '😂',
            'WOW': '😮',
            'SAD': '😢',
            'ANGRY': '😡'
        };
        let stackHtml = '';
        resultData.top_reactions.forEach((r, idx) => {
            const margin = idx > 0 ? 'margin-left: -8px;' : '';
            stackHtml += `<span style="${margin}">${REACTION_EMOJIS[r] || '👍'}</span>`;
        });
        stackContainer.innerHTML = stackHtml;
    }

    // 3. Cập nhật số đếm
    const countSpan = postCard.querySelector('[id^="reaction-count-"]');
    if (countSpan && resultData.reactions_count !== undefined) {
        countSpan.innerText = resultData.reactions_count > 0 ? resultData.reactions_count : '';
    }
}
