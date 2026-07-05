function toggleAuth(isRegister) {
            const container = document.getElementById('authContainer');
            const subtitle = document.getElementById('authSubtitle');
            document.getElementById('loginError').style.display = 'none';
            document.getElementById('registerError').style.display = 'none';
            
            if (isRegister) {
                container.classList.add('is-register');
                subtitle.innerText = "Tạo tài khoản mới để trải nghiệm đầy đủ tính năng.";
            } else {
                container.classList.remove('is-register');
                subtitle.innerText = "Đăng nhập để khám phá thế giới âm nhạc của riêng bạn.";
            }
        }

        // Toggle Password Visibility
        function togglePasswordVisibility(inputId, icon) {
            const input = document.getElementById(inputId);
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            } else {
                input.type = 'password';
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            }
        }


        // Gọi API CSRF trước khi POST
        async function fetchCsrf() {
            await fetch('/api/v1/auth/csrf/');
        }

        // Xử lý Form Đăng Nhập
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            const errorDiv = document.getElementById('loginError');
            errorDiv.style.display = 'none';

            try {
                await fetchCsrf();
                const csrfToken = getCookie('csrftoken');

                const response = await fetch('/api/v1/auth/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ email, password })
                });

                const result = await response.json();
                if (response.ok && result.success) {
                    window.location.href = window.HOME_URL;
                } else {
                    errorDiv.innerText = result.error?.message || 'Đăng nhập thất bại. Vui lòng kiểm tra lại.';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.innerText = 'Lỗi kết nối máy chủ. Vui lòng thử lại sau.';
                errorDiv.style.display = 'block';
            }
        });

        // Xử lý Form Đăng Ký
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            const username = document.getElementById('registerUsername').value;
            const email = document.getElementById('registerEmail').value;
            const password = document.getElementById('registerPassword').value;
            const confirmPassword = document.getElementById('registerConfirmPassword').value;
            const errorDiv = document.getElementById('registerError');
            errorDiv.style.display = 'none';

            if (password !== confirmPassword) {
                errorDiv.innerText = 'Mật khẩu xác nhận không khớp.';
                errorDiv.style.display = 'block';
                return;
            }

            try {
                await fetchCsrf();
                const csrfToken = getCookie('csrftoken');

                const response = await fetch('/api/v1/auth/register/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ username, email, password })
                });

                const result = await response.json();
                if (response.ok && result.success) {
                    // Đăng ký thành công, tự động đăng nhập hoặc chuyển về màn hình đăng nhập
                    alert('Đăng ký thành công! Vui lòng đăng nhập.');
                    toggleAuth(false);
                    document.getElementById('loginEmail').value = email;
                    document.getElementById('loginPassword').value = '';
                } else {
                    // Hiển thị lỗi từ backend
                    let errorMsg = result.error?.message || 'Đăng ký thất bại.';
                    if (result.error?.fields) {
                        const firstError = Object.values(result.error.fields)[0];
                        if (firstError && firstError.length > 0) {
                            errorMsg = firstError[0];
                        }
                    }
                    errorDiv.innerText = errorMsg;
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.innerText = 'Lỗi kết nối máy chủ. Vui lòng thử lại sau.';
                errorDiv.style.display = 'block';
            }
        });