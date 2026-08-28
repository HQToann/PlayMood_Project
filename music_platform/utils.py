def optimize_cloudinary_url(url, resource_type='image'):
    """
    Hàm đã được refactor để giữ tính tương thích ngược, 
    trả về nguyên gốc url vì hiện tại sử dụng storage nội bộ VPS (không dùng Cloudinary).
    """
    if not url:
        return url
    
    return url
