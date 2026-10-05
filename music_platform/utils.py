def optimize_cloudinary_url(url, resource_type='image'):
    """
    Tối ưu hoá URL Cloudinary bằng cách chèn tham số format/quality (chỉ áp dụng cho ảnh).
    - Ảnh: f_auto,q_auto (Tự định dạng WebP/AVIF và nén tự động)
    - Audio/Video: Giữ nguyên để tránh lỗi 404 Not Supported.
    """
    if not url:
        return url
    
    if isinstance(url, str) and 'res.cloudinary.com' in url and '/upload/' in url:
        # Bắt buộc chuyển HTTP sang HTTPS để tránh lỗi Mixed Content khi deploy
        url = url.replace('http://', 'https://')
        
        # Chỉ chèn transformation cho hình ảnh
        if resource_type == 'image' and '/upload/f_auto' not in url and '/upload/q_auto' not in url:
            return url.replace('/upload/', '/upload/f_auto,q_auto/', 1)
            
        # Nếu là audio/video, chủ động xoá các tham số f_auto, q_auto nếu vô tình bị dính vào từ DB
        if resource_type == 'audio' or resource_type == 'video':
            url = url.replace('/f_auto,q_auto/', '/')
            url = url.replace('/q_auto,f_auto/', '/')
            url = url.replace('/f_auto/', '/')
            url = url.replace('/q_auto/', '/')
            
    return url
