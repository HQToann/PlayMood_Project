def optimize_cloudinary_url(url, resource_type='image'):
    """
    Tối ưu hoá URL Cloudinary bằng cách chèn tham số format/quality.
    - Ảnh: f_auto,q_auto (Tự định dạng WebP/AVIF và nén tự động)
    - Audio: q_auto (Tự động nén âm thanh ở chất lượng tốt nhất với dung lượng nhỏ nhất)
    """
    if not url:
        return url
    
    if isinstance(url, str) and 'res.cloudinary.com' in url and '/upload/' in url:
        # Tránh thêm nhiều lần nếu đã có
        if '/upload/f_auto' not in url and '/upload/q_auto' not in url:
            if resource_type == 'image':
                return url.replace('/upload/', '/upload/f_auto,q_auto/', 1)
            elif resource_type in ('audio', 'video'):
                return url.replace('/upload/', '/upload/q_auto/', 1)
    return url
