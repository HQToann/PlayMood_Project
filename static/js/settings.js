// Helper: get CSRF cookie
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
    // Fallback: try hidden CSRF input in the page
    if (!cookieValue) {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfInput) cookieValue = csrfInput.value;
    }
    return cookieValue;
}

// Image preview logic
        const _idCardImage = document.getElementById('id_card_image');
        if (_idCardImage) {
            _idCardImage.addEventListener('change', function (event) {
                const file = event.target.files[0];
                const previewContainer = document.getElementById('id_card_preview_container');
                const previewImage = document.getElementById('id_card_preview');

                if (file) {
                    const reader = new FileReader();
                    reader.onload = function (e) {
                        previewImage.src = e.target.result;
                        previewContainer.classList.remove('d-none');
                    }
                    reader.readAsDataURL(file);
                } else {
                    previewImage.src = "";
                    previewContainer.classList.add('d-none');
                }
            });
        }

        

        // Tự động kiểm tra trạng thái đăng ký nghệ sĩ khi tải trang
        document.addEventListener('DOMContentLoaded', async () => {
            try {
                const response = await fetch('/api/v1/accounts/artist-verification/me/');
                if (response.ok) {
                    const result = await response.json();
                    if (result.success && result.data) {
                        const status = result.data.status;
                        const actionContainer = document.getElementById('artist-register-action');
                        if (actionContainer) {
                            if (status === 'pending') {
                                actionContainer.innerHTML = '<span class="text-warning fw-bold"><i class="bi bi-circle-fill me-1" style="font-size: 0.7rem;"></i> Chờ duyệt...</span>';
                            } else if (status === 'approved') {
                                actionContainer.innerHTML = '<span class="text-success fw-bold"><i class="bi bi-check-circle-fill me-1"></i> Đã được chấp thuận</span>';
                            } else if (status === 'rejected') {
                                const infoContainer = document.getElementById('artist-register-info');
                                const existingError = document.getElementById('artist-register-error');
                                if (existingError) existingError.remove();
                                infoContainer.insertAdjacentHTML('beforeend', '<div id="artist-register-error" class="text-danger small mt-1 fw-bold"><i class="bi bi-circle-fill me-1" style="font-size: 0.7rem;"></i> Bị từ chối. Vui lòng đăng ký lại</div>');
                            }
                        }
                    }
                }
            } catch (e) {
                console.error("Lỗi khi lấy trạng thái đăng ký nghệ sĩ:", e);
            }
        });

        window.handleArtistRegistration = async function() {
            const form = document.getElementById('artistRegisterForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const realName = document.getElementById('real_name').value;
            const note = document.getElementById('note').value;
            const fileInput = document.getElementById('id_card_image');

            const formData = new FormData();
            formData.append('real_name', realName);
            formData.append('note', note);
            if (fileInput.files.length > 0) {
                formData.append('id_card_image', fileInput.files[0]);
            }

            const actionContainer = document.getElementById('artist-register-action');
            const originalHTML = actionContainer.innerHTML;

            try {
                // Hiển thị trạng thái đang tải (tùy chọn)
                const btn = document.querySelector('#artistRegisterModal button[onclick="handleArtistRegistration()"]');
                const originalBtnText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang gửi...';
                btn.disabled = true;

                const csrfToken = getCookie('csrftoken') || '{{ csrf_token }}';
                const response = await fetch('/api/v1/accounts/artist-verification/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    },
                    body: formData
                });

                const result = await response.json();

                btn.innerHTML = originalBtnText;
                btn.disabled = false;

                if (response.ok && result.success) {
                    // Đóng modal
                    const modalEl = document.getElementById('artistRegisterModal');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    modal.hide();

                    // Cập nhật giao diện thành Chờ duyệt
                    actionContainer.innerHTML = '<span class="text-warning fw-bold"><i class="bi bi-circle-fill me-1" style="font-size: 0.7rem;"></i> Chờ duyệt...</span>';

                    // Reset form
                    form.reset();
                    document.getElementById('id_card_preview_container').classList.add('d-none');
                    
                    if (window.showToast) window.showToast('Đã gửi yêu cầu đăng ký nghệ sĩ thành công!', 'success');
                } else {
                    let errorMsg = 'Không thể gửi đăng ký.';
                    if (result.error && result.error.fields) {
                        const firstField = Object.keys(result.error.fields)[0];
                        errorMsg = result.error.fields[firstField][0];
                    } else if (result.error && result.error.message) {
                        errorMsg = result.error.message;
                    }
                    if (window.showToast) window.showToast('Lỗi: ' + errorMsg, 'error');
                    else alert('Lỗi: ' + errorMsg);
                }
            } catch (e) {
                console.error(e);
                if (window.showToast) window.showToast('Lỗi kết nối máy chủ. Vui lòng thử lại sau.', 'error');
                else alert('Lỗi kết nối máy chủ. Vui lòng thử lại sau.');
            }
        }

        // Change Password Form Handler
        const changePasswordForm = document.getElementById('changePasswordForm');
        if (changePasswordForm) {
            changePasswordForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('btnChangePassword');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
                btn.disabled = true;

                const payload = {
                    old_password: document.getElementById('old_password').value,
                    new_password: document.getElementById('new_password').value,
                    confirm_password: document.getElementById('confirm_password').value
                };

                try {
                    const response = await fetch('/api/v1/auth/password/change/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken') || ''
                        },
                        body: JSON.stringify(payload)
                    });
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        if(window.showToast) window.showToast('Đã cập nhật mật khẩu thành công!', true);
                        else alert('Đã cập nhật mật khẩu thành công!');
                        
                        const modalEl = document.getElementById('changePasswordModal');
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        modal.hide();
                        changePasswordForm.reset();
                    } else {
                        let errorMsg = 'Không thể đổi mật khẩu.';
                        if (result.error && result.error.fields) {
                            const firstField = Object.keys(result.error.fields)[0];
                            errorMsg = result.error.fields[firstField][0];
                        } else if (result.error && result.error.message) {
                            errorMsg = result.error.message;
                        }
                        if(window.showToast) window.showToast('Lỗi: ' + errorMsg, false);
                        else alert('Lỗi: ' + errorMsg);
                    }
                } catch (e) {
                    console.error(e);
                    if(window.showToast) window.showToast('Lỗi kết nối máy chủ.', false);
                    else alert('Lỗi kết nối máy chủ.');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            });
        }

        // Change Display Name Form Handler
        const changeDisplayNameForm = document.getElementById('changeDisplayNameForm');
        if (changeDisplayNameForm) {
            changeDisplayNameForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('btnChangeDisplayName');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
                btn.disabled = true;

                const usernameInput = document.getElementById('new_username');
                const payload = {
                    username: usernameInput ? usernameInput.value : ''
                };

                try {
                    const response = await fetch('/api/v1/accounts/me/', {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken') || ''
                        },
                        body: JSON.stringify(payload)
                    });
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        if(window.showToast) window.showToast('Đã cập nhật tên người dùng thành công!', true);
                        else alert('Đã cập nhật tên người dùng thành công!');
                        
                        const modalEl = document.getElementById('changeDisplayNameModal');
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        modal.hide();
                        // Reload page to reflect changes in UI
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        let errorMsg = 'Không thể đổi tên người dùng.';
                        if (result.error && result.error.fields) {
                            const firstField = Object.keys(result.error.fields)[0];
                            errorMsg = result.error.fields[firstField][0];
                        } else if (result.error && result.error.message) {
                            errorMsg = result.error.message;
                        }
                        if(window.showToast) window.showToast('Lỗi: ' + errorMsg, false);
                        else alert('Lỗi: ' + errorMsg);
                    }
                } catch (e) {
                    console.error(e);
                    if(window.showToast) window.showToast('Lỗi kết nối máy chủ.', false);
                    else alert('Lỗi kết nối máy chủ.');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            });
        }

        // Change Stage Name Form Handler
        const changeStageNameForm = document.getElementById('changeStageNameForm');
        if (changeStageNameForm) {
            changeStageNameForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('btnChangeStageName');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang lưu...';
                btn.disabled = true;

                const stageNameInput = document.getElementById('new_stage_name');
                const payload = {
                    stage_name: stageNameInput ? stageNameInput.value : ''
                };

                try {
                    const response = await fetch('/api/v1/accounts/me/', {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken') || ''
                        },
                        body: JSON.stringify(payload)
                    });
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        if(window.showToast) window.showToast('Đã cập nhật nghệ danh thành công!', true);
                        else alert('Đã cập nhật nghệ danh thành công!');
                        
                        const modalEl = document.getElementById('changeStageNameModal');
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        modal.hide();
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        let errorMsg = 'Không thể đổi nghệ danh.';
                        if (result.error && result.error.fields) {
                            const firstField = Object.keys(result.error.fields)[0];
                            errorMsg = result.error.fields[firstField][0];
                        } else if (result.error && result.error.message) {
                            errorMsg = result.error.message;
                        }
                        if(window.showToast) window.showToast('Lỗi: ' + errorMsg, false);
                        else alert('Lỗi: ' + errorMsg);
                    }
                } catch (e) {
                    console.error(e);
                    if(window.showToast) window.showToast('Lỗi kết nối máy chủ.', false);
                    else alert('Lỗi kết nối máy chủ.');
                } finally {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            });
        }

        window.saveSocials = async function() {
            const website = document.getElementById('websiteInput').value.trim();
            const facebook = document.getElementById('facebookInput').value.trim();
            const youtube = document.getElementById('youtubeInput').value.trim();

            try {
                const res = await fetch('/api/v1/artists/me/', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        website_url: website,
                        facebook_url: facebook,
                        youtube_url: youtube
                    })
                });
                const json = await res.json();
                if (json.success || res.ok) {
                    if (window.showToast) showToast('Đã cập nhật liên kết thành công!', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    if (window.showToast) showToast(json.error?.message || 'Lỗi cập nhật liên kết', 'error');
                }
            } catch (e) {
                if (window.showToast) showToast('Lỗi kết nối', 'error');
            }
        }

        // Blocked Users Modal Logic
        const blockedUsersModal = document.getElementById('blockedUsersModal');
        if (blockedUsersModal) {
            blockedUsersModal.addEventListener('show.bs.modal', async () => {
                const container = document.getElementById('blockedUsersListContainer');
                container.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-secondary" role="status"><span class="visually-hidden">Loading...</span></div></div>';

                try {
                    const res = await fetch('/api/v1/accounts/me/blocks/');
                    const data = await res.json();
                    
                    if (res.ok && data.success) {
                        const users = data.data;
                        if (users.length === 0) {
                            container.innerHTML = '<div class="text-center py-4 text-secondary">Bạn chưa chặn ai.</div>';
                            return;
                        }
                        
                        container.innerHTML = users.map(user => `
                            <div class="d-flex align-items-center justify-content-between mb-3 pb-3 border-bottom border-secondary border-opacity-25" id="blocked-user-${user.id}">
                                <div class="d-flex align-items-center gap-3">
                                    <img src="${user.avatar || 'https://images.unsplash.com/photo-1527980965255-d3b416303d12?ixlib=rb-4.0.3&auto=format&fit=crop&w=100&q=80'}"
                                        alt="User" class="rounded-circle" style="width: 45px; height: 45px; object-fit: cover;">
                                    <div>
                                        <h6 class="mb-0 fw-bold">${user.display_name}</h6>
                                        <small class="text-secondary">@${user.username}</small>
                                    </div>
                                </div>
                                <button class="btn btn-sm btn-outline-light rounded-pill px-3" onclick="unblockUserFromSettings(event, '${user.id}')">Bỏ chặn</button>
                            </div>
                        `).join('');
                    } else {
                        container.innerHTML = '<div class="text-center py-4 text-danger">Lỗi khi tải danh sách.</div>';
                    }
                } catch (e) {
                    console.error(e);
                    container.innerHTML = '<div class="text-center py-4 text-danger">Lỗi kết nối.</div>';
                }
            });
        }
        
        window.unblockUserFromSettings = async function(event, userId) {
            if (event) event.preventDefault();
            if (!confirm('Bạn có chắc chắn muốn bỏ chặn người dùng này?')) return;
            
            const btn = event ? event.currentTarget : null;
            const originalText = btn ? btn.innerHTML : 'Bỏ chặn';
            if (btn) {
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
                btn.disabled = true;
            }

            try {
                const csrf = getCookie('csrftoken');
                const res = await fetch(`/api/v1/accounts/users/${userId}/block/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrf,
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!res.ok) {
                    throw new Error('Lỗi từ máy chủ: ' + res.status);
                }
                
                const data = await res.json();
                if (data.success) {
                    if (window.showToast) window.showToast('Đã bỏ chặn người dùng.', 'success');
                    else alert('Đã bỏ chặn người dùng.');
                    
                    const item = document.getElementById(`blocked-user-${userId}`);
                    if (item) item.remove();
                    
                    const container = document.getElementById('blockedUsersListContainer');
                    if (container && container.children.length === 0) {
                        container.innerHTML = '<div class="text-center py-4 text-secondary">Bạn chưa chặn ai.</div>';
                    }
                } else {
                    if (window.showToast) window.showToast('Lỗi khi bỏ chặn.', 'error');
                    else alert('Lỗi khi bỏ chặn.');
                }
            } catch (e) {
                console.error(e);
                if (window.showToast) window.showToast('Lỗi kết nối: ' + e.message, 'error');
                else alert('Lỗi kết nối: ' + e.message);
            } finally {
                if (btn) {
                    btn.innerHTML = originalText;
                    btn.disabled = false;
                }
            }
        };

        // Notification Settings Handlers
        async function handleNotificationToggle(field, value, toggleElement) {
            // Hiển thị trạng thái disable tạm thời để tránh spam click
            toggleElement.disabled = true;
            try {
                const payload = {};
                payload[field] = value;

                const response = await fetch('/api/v1/accounts/me/notifications/', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();
                if (response.ok && result.success) {
                    if (window.showToast) {
                        window.showToast('Đã lưu cài đặt thông báo!', 'success');
                    }
                } else {
                    let errorMsg = 'Không thể lưu cài đặt.';
                    if (result.error && result.error.message) {
                        errorMsg = result.error.message;
                    }
                    if (window.showToast) window.showToast('Lỗi: ' + errorMsg, 'error');
                    else alert('Lỗi: ' + errorMsg);
                    // Revert UI if failed
                    toggleElement.checked = !value;
                }
            } catch (e) {
                console.error(e);
                if (window.showToast) window.showToast('Lỗi kết nối máy chủ.', 'error');
                else alert('Lỗi kết nối máy chủ.');
                toggleElement.checked = !value;
            } finally {
                toggleElement.disabled = false;
            }
        }

        const newSongNotifToggle = document.getElementById('newSongNotifToggle');
        if (newSongNotifToggle) {
            newSongNotifToggle.addEventListener('change', (e) => {
                handleNotificationToggle('new_song_notification', e.target.checked, e.target);
            });
        }

        const moodEmailNotifToggle = document.getElementById('moodEmailNotifToggle');
        if (moodEmailNotifToggle) {
            moodEmailNotifToggle.addEventListener('change', (e) => {
                handleNotificationToggle('mood_email_notification', e.target.checked, e.target);
            });
        }

        // Privacy Settings Handlers
        async function handlePrivacyToggle(field, value, toggleElement) {
            toggleElement.disabled = true;
            try {
                const payload = {};
                payload[field] = value;

                const response = await fetch('/api/v1/accounts/me/privacy/', {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();
                if (response.ok && result.success) {
                    if (window.showToast) {
                        window.showToast('Đã lưu cài đặt quyền riêng tư!', 'success');
                    }
                } else {
                    let errorMsg = 'Không thể lưu cài đặt.';
                    if (result.error && result.error.message) {
                        errorMsg = result.error.message;
                    }
                    if (window.showToast) window.showToast('Lỗi: ' + errorMsg, 'error');
                    else alert('Lỗi: ' + errorMsg);
                    toggleElement.checked = !value;
                }
            } catch (e) {
                console.error(e);
                if (window.showToast) window.showToast('Lỗi kết nối máy chủ.', 'error');
                else alert('Lỗi kết nối máy chủ.');
                toggleElement.checked = !value;
            } finally {
                toggleElement.disabled = false;
            }
        }

        const showPlaylistsToggle = document.getElementById('showPlaylistsToggle');
        if (showPlaylistsToggle) {
            showPlaylistsToggle.addEventListener('change', (e) => {
                handlePrivacyToggle('show_playlists', e.target.checked, e.target);
            });
        }

        const showMoodToggle = document.getElementById('showMoodToggle');
        if (showMoodToggle) {
            showMoodToggle.addEventListener('change', (e) => {
                handlePrivacyToggle('show_mood', e.target.checked, e.target);
            });
        }