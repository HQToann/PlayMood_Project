document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('uploadSongForm');
    const genreSelect = document.getElementById('genreSelect');
    const audioInput = document.querySelector('input[name="audio_file"]');
    const durationInput = document.getElementById('songDuration');
    const coverInput = document.getElementById('coverImageInput');
    const coverContainer = document.getElementById('coverPreviewContainer');
    const coverContent = document.getElementById('coverPlaceholderContent');
    const submitBtn = form.querySelector('button[type="submit"]');

    if (!form) return; // Prevent errors if loaded on other pages

    // CSRF Token Helper
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

    // Load Genres
    async function loadGenres() {
        try {
            const res = await fetch('/api/v1/music/genres/');
            const data = await res.json();
            if (data.success && data.data && data.data.items) {
                data.data.items.forEach(genre => {
                    const opt = document.createElement('option');
                    opt.value = genre.id;
                    opt.textContent = genre.name;
                    genreSelect.appendChild(opt);
                });
            }
        } catch(err) {
            console.error('Failed to load genres', err);
        }
    }
    loadGenres();

    // Cover Image Preview
    coverInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                coverContainer.style.backgroundImage = `url(${e.target.result})`;
                coverContent.style.display = 'none';
            }
            reader.readAsDataURL(file);
        } else {
            coverContainer.style.backgroundImage = 'none';
            coverContent.style.display = 'flex';
        }
    });

    // Get Audio Duration
    audioInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const objectUrl = URL.createObjectURL(file);
            const audio = new Audio(objectUrl);
            audio.addEventListener('loadedmetadata', function() {
                durationInput.value = Math.round(audio.duration);
                URL.revokeObjectURL(objectUrl);
            });
        } else {
            durationInput.value = 0;
        }
    });

    // Handle Submit
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!durationInput.value || durationInput.value === '0') {
            alert('Đang tính toán thời lượng audio, vui lòng thử lại sau giây lát.');
            return;
        }

        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Đang tải lên...';

        const formData = new FormData(form);
        formData.set('allow_download', document.getElementById('allowDownloadSwitch').checked);

        try {
            const res = await fetch('/api/v1/music/songs/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });
            
            const data = await res.json();
            if (data.success) {
                const songId = data.data.id;
                const status = form.querySelector('select[name="status"]').value;
                
                if (status === 'published') {
                    await fetch(`/api/v1/music/songs/${songId}/publish/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });
                }

                // Show toast
                const toastElement = document.getElementById('uploadSuccessToast');
                if (toastElement) {
                    const toast = new bootstrap.Toast(toastElement);
                    toast.show();
                }

                // Reset form
                form.reset();
                coverContainer.style.backgroundImage = 'none';
                coverContent.style.display = 'flex';
                durationInput.value = 0;
                
                // Redirect to manage songs
                setTimeout(() => {
                    if (window.ARTIST_MANAGE_URL) {
                        window.location.href = window.ARTIST_MANAGE_URL;
                    }
                }, 1500);

            } else {
                let errMsg = data.error?.message || 'Lỗi server';
                if (data.error?.fields) {
                    errMsg = Object.values(data.error.fields).join('\n');
                }
                alert('Lỗi: ' + errMsg);
            }
        } catch (err) {
            console.error(err);
            alert('Lỗi kết nối máy chủ');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    });
});
