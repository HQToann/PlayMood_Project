document.addEventListener('DOMContentLoaded', function() {
    // Lấy token từ query string
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('token');

    // Nếu không có token → hiển thị invalid
    if (!resetToken) {
        document.getElementById('resetSection').style.display = 'none';
        document.getElementById('invalidTokenSection').style.display = 'block';
    }

    const resetForm = document.getElementById('resetForm');
    if (resetForm) {
        resetForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmNewPassword').value;
            const errorDiv = document.getElementById('resetError');
            const btn = document.getElementById('resetSubmitBtn');

            errorDiv.style.display = 'none';

            if (newPassword !== confirmPassword) {
                errorDiv.innerText = 'Xác nhận mật khẩu không khớp.';
                errorDiv.style.display = 'block';
                return;
            }

            btn.disabled = true;
            btn.innerText = 'Đang xử lý...';

            try {
                await fetch('/api/v1/auth/csrf/');
                const csrfToken = getCookie('csrftoken');

                const response = await fetch('/api/v1/auth/password/reset/confirm/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ token: resetToken, new_password: newPassword })
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    // Hiển thị thông báo thành công
                    document.getElementById('resetForm').style.display = 'none';
                    const subtitle = document.querySelector('.auth-subtitle');
                    if(subtitle) subtitle.style.display = 'none';
                    const switchDiv = document.querySelector('.auth-switch');
                    if(switchDiv) switchDiv.style.display = 'none';
                    document.getElementById('resetError').style.display = 'none';
                    document.getElementById('resetSuccess').style.display = 'block';
                } else {
                    // Token hết hạn hoặc không hợp lệ
                    const msg = result.error?.message || 'Có lỗi xảy ra. Vui lòng thử lại.';
                    if (msg.includes('hết hạn') || msg.includes('không hợp lệ')) {
                        document.getElementById('resetSection').style.display = 'none';
                        document.getElementById('invalidTokenSection').style.display = 'block';
                    } else {
                        errorDiv.innerText = msg;
                        errorDiv.style.display = 'block';
                    }
                }
            } catch (err) {
                errorDiv.innerText = 'Lỗi kết nối. Vui lòng thử lại.';
                errorDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.innerText = 'Đặt lại mật khẩu';
            }
        });
    }
});
