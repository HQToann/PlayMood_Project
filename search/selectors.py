import math
from django.db.models import Q
from music.models import Song, Album
from artists.models import ArtistProfile
from playlists.models import Playlist
from accounts.models import User, BlockList


def _pagination(page: int, page_size: int, total: int) -> dict:
    return {
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': math.ceil(total/page_size) if total > 0 else 1,
    }


#tìm bài hát đã published ẩn bài hát  của nghệ sĩ đã block viewer
def search_songs(q='', genre='', artist_id='', ordering='-play_count',
                viewer=None, page=1, page_size=20):
    qs = Song.objects.filter(status=Song.STATUS_PUBLISHED).select_related('artist', 'genre')

    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(artist__username__icontains=q)
            | Q(artist__display_name__icontains=q)
        )

    if genre:
        qs = qs.filter(genre__slug=genre)
    if artist_id:
        qs = qs.filter(artist_id=artist_id)
    
    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        blocked_artist_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(artist_id__in=blocked_artist_ids)

    qs = qs.order_by(ordering)
    total = qs.count()
    start = (page - 1) * page_size

    #include_stats=False
    items = [s.to_dict(viewer=viewer, include_stats=False, include_viewer_state=False) for s in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': _pagination(page, page_size, total),
    }



#tìm nghệ sĩ theo tên nghệ danh / username ẩn nghệ sĩ đã block viewer
def search_artists(q='', viewer=None, page=1, page_size=20) -> dict:
    qs = ArtistProfile.objects.select_related('user').filter(user__is_active=True)

    if q:
        qs = qs.filter(Q(stage_name__icontains=q) | Q(user__username__icontains=q) | Q(user__display_name__icontains=q))

    viewer_id = getattr(viewer, 'id', None)
    if viewer_id and getattr(viewer, 'is_authenticated', False):
        blocked_ids = BlockList.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(user_id__in=blocked_ids).exclude(user_id=viewer_id)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    
    following_ids = set()
    requested_ids = set()
    viewer_is_auth = bool(viewer_id and getattr(viewer, 'is_authenticated', False))
    if viewer_is_auth:
        from social.models import Follow, FollowRequest
        following_ids = set(Follow.objects.filter(follower_id=viewer_id).values_list('following_id', flat=True))
        requested_ids = set(FollowRequest.objects.filter(sender_id=viewer_id).values_list('receiver_id', flat=True))
        
    items = []
    for a in qs[start:start + page_size]:
        a_dict = a.to_dict(viewer=viewer)
        if viewer_is_auth:
            if a.user_id in following_ids:
                a_dict['follow_status'] = 'following'
            elif a.user_id in requested_ids:
                a_dict['follow_status'] = 'requested'
            else:
                a_dict['follow_status'] = 'none'
        else:
            a_dict['follow_status'] = 'none'
        items.append(a_dict)

    return {
        'items': items,
        'pagination': _pagination(page, page_size, total),
    }


#tìm playlist công khai theo tên chỉ playlist is_public=True
def search_playlists(q='', viewer=None, page=1, page_size=20) -> dict:
    qs = Playlist.objects.filter(is_public=True, owner__is_active=True).select_related('owner')

    if q:
        qs = qs.filter(title__icontains=q)

    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size

    #include_song_count=False
    items = [p.to_dict(viewer=viewer, include_song_count=False) for p in qs[start:start + page_size]]

    return {
        'items': items,
        'pagination': _pagination(page, page_size, total),
    }


"""
Tìm người dùng theo username/display_name
mặc định CHỈ trả user is_private=False. User is_private=True chỉ
xuất hiện nếu requester đang follow họ (đã là "người quen"), tương tự cách
Instagram/X ẩn tài khoản riêng tư khỏi kết quả tìm kiếm của người lạ.
"""
def search_users(q='', requester=None, page=1, page_size=20) -> dict:
    qs = User.objects.filter(is_active=True)

    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(display_name__icontains=q))

    requester_id = getattr(requester, 'id', None)
    requester_is_auth = bool(requester_id and getattr(requester, 'is_authenticated', False))

    following_ids = set()
    requested_ids = set()

    if requester_is_auth:
        from social.models import Follow, FollowRequest
        following_ids = set(Follow.objects.filter(follower_id=requester_id).values_list('following_id', flat=True))
        requested_ids = set(FollowRequest.objects.filter(sender_id=requester_id).values_list('receiver_id', flat=True))
        qs = qs.filter(Q(is_private=False) | Q(id__in=following_ids))

        blocked_ids = BlockList.objects.filter(blocked_id=requester_id).values_list('blocker_id', flat=True)
        qs = qs.exclude(id__in=blocked_ids)
    else:
        qs = qs.filter(is_private=False)

    qs = qs.exclude(id=requester_id) if requester_is_auth else qs
    qs = qs.order_by('username')
    total = qs.count()
    start = (page - 1) * page_size

    items = []
    for u in qs[start:start + page_size]:
        u_dict = u.to_dict(include_private=False)
        # Gắn follow_status: none / requested / following
        if requester_is_auth:
            if u.id in following_ids:
                u_dict['follow_status'] = 'following'
            elif u.id in requested_ids:
                u_dict['follow_status'] = 'requested'
            else:
                u_dict['follow_status'] = 'none'
        else:
            u_dict['follow_status'] = 'none'
        items.append(u_dict)

    return {
        'items': items,
        'pagination': _pagination(page, page_size, total)
    }


def search_albums(q='', viewer=None, page=1, page_size=20) -> dict:
    from music.models import Album
    qs = Album.objects.filter(status='published', artist__is_active=True).select_related('artist')
    if q:
        qs = qs.filter(title__icontains=q)
    qs = qs.order_by('-created_at')
    total = qs.count()
    start = (page - 1) * page_size
    items = [a.to_dict(viewer=viewer) for a in qs[start:start + page_size]]
    return {'items': items, 'pagination': _pagination(page, page_size, total)}

def search_all(q, viewer=None, limit=5) -> dict:
    """Tìm kiếm tổng hợp - mỗi loại giới hạn `limit` kết quả, không phân trang đầy đủ."""
    songs = search_songs(q=q, viewer=viewer, page=1, page_size=limit)['items']
    artists = search_artists(q=q, viewer=viewer, page=1, page_size=limit)['items']
    playlists = search_playlists(q=q, viewer=viewer, page=1, page_size=limit)['items']
    albums = search_albums(q=q, viewer=viewer, page=1, page_size=limit)['items']
    users = search_users(q=q, requester=viewer, page=1, page_size=limit)['items']

    return {
        'songs': songs, 
        'artists': artists, 
        'playlists': playlists, 
        'albums': search_albums(q=q, viewer=viewer, page=1, page_size=limit)['items'],
        'albums': albums,
        'users': users
    }