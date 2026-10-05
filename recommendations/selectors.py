"""
recommendations/selectors.py

Tầng truy vấn (chỉ đọc) cho app recommendations.

Chiến lược Hybrid:
    1. Content-based:   dựa trên "gu nghe" của user (genre + artist đã
                         like/rate/nghe nhiều) để chấm điểm bài hát mới.
    2. Collaborative:   tìm những user có gu nghe giống mình (cosine
                         similarity trên vector tương tác), rồi gợi ý những
                         bài họ thích mà mình chưa nghe.
    3. Popularity:      play_count / trending, dùng làm tín hiệu phụ và để
                         lấp đầy khi 2 nguồn trên chưa đủ dữ liệu.

Cold-start (user mới, chưa có tương tác nào) -> fallback về trending.

Toàn bộ hàm ở đây chỉ ĐỌC dữ liệu, không ghi. Không import trực tiếp trong
views.py — views chỉ gọi qua các hàm public bên dưới.
"""

import math

from django.db.models import Count, Max, Sum

from music.models import Song, Genre, Like, Rating, ListenHistory
from music.exceptions import SongNotFound
from accounts.models import BlockList, User
from playlists.models import Playlist
from recommendations.models import RecommendationDismissal

# Trọng số các loại tương tác khi tính vector "mức độ quan tâm" của user
LIKE_WEIGHT = 3.0
LISTEN_WEIGHT = 1.0
LISTEN_CAP = 5  # tối đa 5 lượt nghe được tính cho 1 bài, tránh 1 bài lấn át cả vector

# Trọng số kết hợp 3 nguồn tín hiệu trong hybrid score, tổng = 1.0
ALPHA_CONTENT = 0.4
BETA_COLLAB = 0.4
GAMMA_POPULARITY = 0.2

# Số user tương tự tối đa được xét khi tính collaborative filtering
SIMILAR_USER_CANDIDATE_LIMIT = 200
SIMILAR_USER_TOP_K = 25


# Vector tương tác & gu nghe

def _get_interaction_vector(user_id) -> dict:
    """
    Trả về {song_id: weight} thể hiện mức độ quan tâm của 1 user với từng
    bài hát, gộp từ Like (3đ), Rating (1-5đ theo số sao) và ListenHistory
    (1đ/lượt nghe, tối đa 5 lượt/bài).
    """
    weights = {}

    liked_ids = Like.objects.filter(user_id=user_id).values_list('song_id', flat=True)
    for song_id in liked_ids:
        weights[song_id] = weights.get(song_id, 0) + LIKE_WEIGHT

    rated = Rating.objects.filter(user_id=user_id).values_list('song_id', 'score')
    for song_id, score in rated:
        weights[song_id] = weights.get(song_id, 0) + score

    listen_counts = (
        ListenHistory.objects.filter(user_id=user_id)
        .values('song_id')
        .annotate(cnt=Count('id'))
    )
    for row in listen_counts:
        capped = min(row['cnt'], LISTEN_CAP)
        weights[row['song_id']] = weights.get(row['song_id'], 0) + capped * LISTEN_WEIGHT

    return weights


def _taste_profile(interaction_vector: dict) -> dict:
    """
    Quy đổi vector tương tác theo bài hát -> "gu nghe" theo genre/artist.

    Returns:
        {'genre': {genre_id: weight}, 'artist': {artist_id: weight}}
    """
    if not interaction_vector:
        return {'genre': {}, 'artist': {}}

    songs = Song.objects.filter(id__in=interaction_vector.keys()).values(
        'id', 'genre_id', 'artist_id'
    )

    genre_weights, artist_weights = {}, {}
    for s in songs:
        w = interaction_vector.get(s['id'], 0)
        if s['genre_id']:
            genre_weights[s['genre_id']] = genre_weights.get(s['genre_id'], 0) + w
        artist_weights[s['artist_id']] = artist_weights.get(s['artist_id'], 0) + w

    return {'genre': genre_weights, 'artist': artist_weights}


def _excluded_song_ids(user_id) -> set:
    """Bài hát cần loại khỏi gợi ý: đã nghe, đã like, đã gạt bỏ (dismiss)."""
    listened = set(ListenHistory.objects.filter(user_id=user_id).values_list('song_id', flat=True))
    liked = set(Like.objects.filter(user_id=user_id).values_list('song_id', flat=True))
    dismissed = set(
        RecommendationDismissal.objects.filter(user_id=user_id).values_list('song_id', flat=True)
    )
    return listened | liked | dismissed


def _normalize(scores: dict) -> dict:
    """Đưa score về [0, 1] theo giá trị lớn nhất, để 3 nguồn cộng được với nhau."""
    if not scores:
        return {}
    max_val = max(scores.values())
    if max_val <= 0:
        return {k: 0.0 for k in scores}
    return {k: v / max_val for k, v in scores.items()}


# Content-based

def _content_scores(taste: dict, candidate_qs) -> dict:
    """Chấm điểm bài hát dựa trên mức trùng khớp genre/artist với gu nghe của user."""
    genre_w = taste['genre']
    artist_w = taste['artist']
    if not genre_w and not artist_w:
        return {}

    scores = {}
    for song in candidate_qs.only('id', 'genre_id', 'artist_id'):
        score = 0.0
        if song.genre_id and song.genre_id in genre_w:
            score += genre_w[song.genre_id]
        if song.artist_id in artist_w:
            # nghệ sĩ trọng số thấp hơn thể loại: thích thể loại thì đổi gu dễ hơn thích 1 nghệ sĩ cụ thể
            score += artist_w[song.artist_id] * 0.5
        if score > 0:
            scores[song.id] = score
    return scores


# Collaborative filtering (user-based)

def _cosine_similarity(vec_a: dict, vec_b: dict) -> float:
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _find_similar_users(user_id, my_vector: dict) -> list:
    """
    Tìm user khác từng tương tác (like/rate/nghe) chung ít nhất 1 bài hát
    với target user, xếp hạng theo cosine similarity trên vector tương tác.

    Returns: list [(other_user_id, similarity, other_vector), ...] giảm dần theo similarity.
    """
    if not my_vector:
        return []

    song_ids = list(my_vector.keys())

    other_user_ids = set(
        Like.objects.filter(song_id__in=song_ids)
        .exclude(user_id=user_id)
        .values_list('user_id', flat=True)[:SIMILAR_USER_CANDIDATE_LIMIT]
    ) | set(
        Rating.objects.filter(song_id__in=song_ids)
        .exclude(user_id=user_id)
        .values_list('user_id', flat=True)[:SIMILAR_USER_CANDIDATE_LIMIT]
    ) | set(
        ListenHistory.objects.filter(song_id__in=song_ids)
        .exclude(user_id=user_id)
        .values_list('user_id', flat=True)[:SIMILAR_USER_CANDIDATE_LIMIT]
    )

    similarities = []
    for other_id in other_user_ids:
        other_vector = _get_interaction_vector(other_id)
        sim = _cosine_similarity(my_vector, other_vector)
        if sim > 0:
            similarities.append((other_id, sim, other_vector))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:SIMILAR_USER_TOP_K]


def _collaborative_scores(user_id, my_vector: dict, exclude_ids: set) -> dict:
    """Chấm điểm bài hát dựa trên việc những user có gu giống mình đã thích gì."""
    similar_users = _find_similar_users(user_id, my_vector)
    scores = {}
    for other_id, sim, other_vector in similar_users:
        for song_id, weight in other_vector.items():
            if song_id in exclude_ids:
                continue
            scores[song_id] = scores.get(song_id, 0) + sim * weight
    return scores


# Lý do gợi ý (hiển thị cho user, kiểu "Vì bạn thích...")

def _reco_reason(song, taste: dict, content_score: float, collab_score: float) -> str:
    if collab_score and collab_score >= content_score:
        return 'Người nghe có gu giống bạn cũng thích bài này'
    if song.genre_id and taste['genre'].get(song.genre_id):
        return f'Vì bạn hay nghe thể loại {song.genre.name}'
    if taste['artist'].get(song.artist_id):
        return f'Vì bạn hay nghe nghệ sĩ {song.artist.get_display_name()}'
    return 'Đang thịnh hành trên PlayMood'


# Public API

def get_recommendations_for_user(user, page: int = 1, page_size: int = 20) -> dict:
    """
    Gợi ý bài hát hybrid cho 1 user đã đăng nhập.

    Cold-start (chưa Like/Rate/nghe bài nào): fallback toàn bộ về trending.
    Nếu hybrid không đủ số lượng cho trang yêu cầu: lấp đầy bằng trending.
    """
    user_id = user.id
    exclude_ids = _excluded_song_ids(user_id)

    blocked_artist_ids = set(
        BlockList.objects.filter(blocked_id=user_id).values_list('blocker_id', flat=True)
    )

    base_qs = (
        Song.objects.filter(status=Song.STATUS_PUBLISHED)
        .exclude(id__in=exclude_ids)
        .exclude(artist_id__in=blocked_artist_ids)
    )

    my_vector = _get_interaction_vector(user_id)

    if not my_vector:
        # Cold-start: chưa có dữ liệu hành vi -> trending
        start = (page - 1) * page_size
        trending_qs = base_qs.select_related('artist', 'genre').order_by('-is_trending', '-play_count')
        total = trending_qs.count()
        page_songs = trending_qs[start:start + page_size]
        items = [
            _to_reco_item(s, {'genre': {}, 'artist': {}}, 0, 0, user)
            for s in page_songs
        ]
        return {
            'items': items,
            'pagination': {'page': page, 'page_size': page_size, 'total': total},
            'source': 'trending',
        }

    taste = _taste_profile(my_vector)

    content_raw = _content_scores(taste, base_qs)
    collab_raw = _collaborative_scores(user_id, my_vector, exclude_ids)
    content = _normalize(content_raw)
    collab = _normalize(collab_raw)

    max_play = base_qs.aggregate(m=Max('play_count'))['m'] or 0
    popularity = {}
    if max_play:
        for song_id, play_count in base_qs.values_list('id', 'play_count'):
            popularity[song_id] = play_count / max_play

    all_ids = set(content) | set(collab) | set(popularity)
    hybrid = {
        song_id: (
            ALPHA_CONTENT * content.get(song_id, 0)
            + BETA_COLLAB * collab.get(song_id, 0)
            + GAMMA_POPULARITY * popularity.get(song_id, 0)
        )
        for song_id in all_ids
    }
    ranked_ids = sorted(hybrid, key=lambda k: hybrid[k], reverse=True)

    # Nếu hybrid chưa đủ dữ liệu cho tới trang được yêu cầu, lấp đầy bằng trending
    if len(ranked_ids) < page * page_size:
        fallback_ids = list(
            base_qs.exclude(id__in=ranked_ids)
            .order_by('-is_trending', '-play_count')
            .values_list('id', flat=True)[: page_size * 2]
        )
        ranked_ids += fallback_ids

    total = len(ranked_ids)
    start = (page - 1) * page_size
    page_ids = ranked_ids[start:start + page_size]

    songs_by_id = {
        s.id: s
        for s in Song.objects.filter(id__in=page_ids).select_related('artist', 'genre')
    }
    items = [
        _to_reco_item(
            songs_by_id[i], taste, content_raw.get(i, 0), collab_raw.get(i, 0), user
        )
        for i in page_ids
        if i in songs_by_id
    ]

    return {
        'items': items,
        'pagination': {'page': page, 'page_size': page_size, 'total': total},
        'source': 'hybrid',
    }


def get_similar_songs(song_id, viewer=None, limit: int = 10) -> list:
    """
    "Nghe tiếp bài tương tự" - content-based từ 1 bài hát cụ thể, không cần
    lịch sử của user. Không yêu cầu đăng nhập.

    Ưu tiên: cùng nghệ sĩ (2đ) > cùng thể loại (1đ) > được like bởi cùng
    nhóm user từng like bài gốc (item-based CF đơn giản, 0.5đ/lượt like chung).
    """
    try:
        anchor = Song.objects.select_related('artist', 'genre').get(
            id=song_id, status=Song.STATUS_PUBLISHED
        )
    except Song.DoesNotExist:
        raise SongNotFound()

    scores = {}

    same_artist_ids = Song.objects.filter(
        artist_id=anchor.artist_id, status=Song.STATUS_PUBLISHED
    ).exclude(id=anchor.id).values_list('id', flat=True)
    for song_id_ in same_artist_ids:
        scores[song_id_] = scores.get(song_id_, 0) + 2.0

    if anchor.genre_id:
        same_genre_ids = Song.objects.filter(
            genre_id=anchor.genre_id, status=Song.STATUS_PUBLISHED
        ).exclude(id=anchor.id).values_list('id', flat=True)
        for song_id_ in same_genre_ids:
            scores[song_id_] = scores.get(song_id_, 0) + 1.0

    co_liking_user_ids = Like.objects.filter(song_id=anchor.id).values_list(
        'user_id', flat=True
    )[:200]
    co_liked = (
        Like.objects.filter(user_id__in=co_liking_user_ids)
        .exclude(song_id=anchor.id)
        .values('song_id')
        .annotate(cnt=Count('id'))
    )
    for row in co_liked:
        scores[row['song_id']] = scores.get(row['song_id'], 0) + row['cnt'] * 0.5

    ranked_ids = sorted(scores, key=lambda k: scores[k], reverse=True)[:limit]

    songs_by_id = {
        s.id: s
        for s in Song.objects.filter(id__in=ranked_ids, status=Song.STATUS_PUBLISHED)
        .select_related('artist', 'genre')
    }
    return [
        songs_by_id[i].to_dict(viewer=viewer, include_stats=False)
        for i in ranked_ids
        if i in songs_by_id
    ]


def _to_reco_item(song, taste: dict, content_score: float, collab_score: float, viewer) -> dict:
    data = song.to_dict(viewer=viewer, include_stats=False, include_viewer_state=True)
    data['recommendation_reason'] = _reco_reason(song, taste, content_score, collab_score)
    return data


def get_recommended_artists(user, limit: int = 10) -> list:
    """
    Gợi ý nghệ sĩ dựa trên gu nghe của user.

    Thuật toán:
        1. Lấy danh sách artist_id mà user đã tương tác (Like / Rate / Listen),
           cho điểm theo mức độ tương tác (như LIKE_WEIGHT, LISTEN_WEIGHT).
        2. Loại bỏ các nghệ sĩ mà user đã bị block.
        3. Fallback nếu chưa có dữ liệu: nghệ sĩ có tổng play_count cao nhất.
    """
    user_id = user.id

    blocked_artist_ids = set(
        BlockList.objects.filter(blocked_id=user_id).values_list('blocker_id', flat=True)
    ) | set(
        BlockList.objects.filter(blocker_id=user_id).values_list('blocked_id', flat=True)
    )

    # Tính điểm cho từng artist dựa trên tương tác
    artist_scores: dict = {}

    # Lượt Like
    liked_artist_ids = (
        Like.objects.filter(user_id=user_id)
        .values_list('song__artist_id', flat=True)
    )
    for aid in liked_artist_ids:
        if aid:
            artist_scores[aid] = artist_scores.get(aid, 0) + LIKE_WEIGHT

    # Lịch sử nghe
    listened_artist_ids = (
        ListenHistory.objects.filter(user_id=user_id)
        .values_list('song__artist_id', flat=True)
    )
    for aid in listened_artist_ids:
        if aid:
            artist_scores[aid] = artist_scores.get(aid, 0) + LISTEN_WEIGHT

    # Lọc bỏ blocked và chỉ giữ artist (role='artist')
    candidate_ids = [
        aid for aid in artist_scores
        if aid and aid not in blocked_artist_ids
    ]

    if candidate_ids:
        ranked_ids = sorted(candidate_ids, key=lambda k: artist_scores[k], reverse=True)[:limit]
        artists = {
            u.id: u
            for u in User.objects.filter(id__in=ranked_ids, role=User.ROLE_ARTIST)
        }
        result = [artists[i].to_dict() for i in ranked_ids if i in artists]
    else:
        # Cold-start: top artist theo tổng play_count
        top_qs = (
            Song.objects.filter(status=Song.STATUS_PUBLISHED)
            .exclude(artist_id__in=blocked_artist_ids)
            .values('artist_id')
            .annotate(total_plays=Sum('play_count'))
            .order_by('-total_plays')[:limit]
        )
        artist_ids = [row['artist_id'] for row in top_qs]
        artists = {
            u.id: u
            for u in User.objects.filter(id__in=artist_ids, role=User.ROLE_ARTIST)
        }
        result = [artists[i].to_dict() for i in artist_ids if i in artists]

    return result


def get_recommended_playlists(user, limit: int = 10) -> list:
    """
    Gợi ý playlist công khai phù hợp với gu nghe của user.

    Thuật toán:
        1. Lấy set genre_id mà user hay nghe nhất từ taste profile.
        2. Ưu tiên playlist có nhiều bài hát thuộc các genre đó.
        3. Fallback nếu chưa có dữ liệu / chưa đủ: playlist mới nhất hoặc được like nhiều.
    """
    user_id = user.id
    my_vector = _get_interaction_vector(user_id)

    blocked_user_ids = set(
        BlockList.objects.filter(blocked_id=user_id).values_list('blocker_id', flat=True)
    ) | set(
        BlockList.objects.filter(blocker_id=user_id).values_list('blocked_id', flat=True)
    )

    # related_name trên PlaylistSong.playlist FK là 'playlist_songs'
    base_qs = (
        Playlist.objects.filter(is_public=True)
        .exclude(owner_id__in=blocked_user_ids)
        .select_related('owner')
    )

    playlists = []

    if my_vector:
        taste = _taste_profile(my_vector)
        top_genre_ids = sorted(
            taste['genre'], key=lambda g: taste['genre'][g], reverse=True
        )[:5]

        if top_genre_ids:
            # Ưu tiên playlist có nhiều bài hát thuộc genre yêu thích
            # Sử dụng đúng related_name: playlist_songs
            scored = (
                base_qs
                .filter(playlist_songs__song__genre_id__in=top_genre_ids)
                .annotate(match_count=Count('playlist_songs', distinct=True))
                .order_by('-match_count', '-created_at')
                .distinct()
            )
            playlists = list(scored[:limit])

    # Lấp đầy bằng playlist mới nhất nếu chưa đủ
    if len(playlists) < limit:
        seen_ids = [p.id for p in playlists]
        extras = list(
            base_qs
            .exclude(id__in=seen_ids)
            .order_by('-created_at')[:limit - len(playlists)]
        )
        playlists += extras

    viewer = user if getattr(user, 'is_authenticated', False) else None
    return [p.to_dict(viewer=viewer) for p in playlists]


# ──────────────────────────────────────────────────────────────────────────────
# Mood-based Recommendation
# ──────────────────────────────────────────────────────────────────────────────

from social.models import Mood, MoodType  # noqa: E402

# Mapping từ keyword trong tên cảm xúc → keyword tên genre (tiếng Việt + EN)
# Thuật toán sẽ dùng CONTAINS để match, không phân biệt hoa/thường
MOOD_GENRE_MAP: dict[str, list[str]] = {
    'vui':        ['pop', 'dance', 'kpop', 'edm'],
    'hạnh phúc':  ['pop', 'dance', 'kpop'],
    'phấn khích': ['edm', 'dance', 'hip hop', 'hip-hop', 'pop'],
    'buồn':       ['ballad', 'acoustic', 'indie', 'slow'],
    'cô đơn':     ['ballad', 'acoustic', 'indie'],
    'nhớ nhà':    ['ballad', 'acoustic', 'indie'],
    'thư giãn':   ['lofi', 'chill', 'jazz', 'acoustic', 'classical'],
    'bình yên':   ['lofi', 'chill', 'acoustic', 'classical'],
    'học':        ['lofi', 'chill', 'classical', 'instrumental'],
    'làm việc':   ['lofi', 'chill', 'edm'],
    'năng lượng': ['rock', 'edm', 'hip hop', 'hip-hop', 'pop'],
    'tập luyện':  ['edm', 'hip hop', 'rock'],
    'lãng mạn':   ['ballad', 'r&b', 'acoustic'],
    'yêu':        ['ballad', 'r&b', 'pop'],
    'tức':        ['rock', 'metal', 'hip hop', 'hip-hop'],
    'lo lắng':    ['chill', 'lofi', 'acoustic'],
    'căng thẳng': ['chill', 'lofi', 'classical'],
    'hoài niệm':  ['ballad', 'acoustic', 'indie', 'oldies'],
    'tự tin':     ['hip hop', 'hip-hop', 'pop', 'r&b'],
    'buồn ngủ':   ['lofi', 'chill', 'classical', 'acoustic'],
}

# Trọng số kết hợp 2 tín hiệu mood
MOOD_ALPHA_GENRE = 0.55      # genre mapping (rule-based)
MOOD_BETA_CO_MOOD = 0.45     # co-mood collaborative


def _match_genre_ids_for_mood(mood_name: str) -> list:
    """
    Từ tên cảm xúc (vd: 'Vui Vẻ'), tra MOOD_GENRE_MAP bằng substring matching
    để tìm tập genre_id phù hợp trong DB.
    """
    mood_name_lower = mood_name.lower()
    matched_keywords: set[str] = set()

    for keyword, genre_keywords in MOOD_GENRE_MAP.items():
        if keyword in mood_name_lower:
            matched_keywords.update(genre_keywords)

    if not matched_keywords:
        return []

    # Build OR query: genre.name ICONTAINS bất kỳ keyword nào
    from django.db.models import Q
    q = Q()
    for kw in matched_keywords:
        q |= Q(name__icontains=kw)

    return list(Genre.objects.filter(q).values_list('id', flat=True))


def _co_mood_listen_scores(mood_type_id, exclude_ids: set, limit_users: int = 100) -> dict:
    """
    Collaborative filtering theo tâm trạng:
    Tìm các user hiện đang (hoặc gần đây nhất) có cùng mood_type_id,
    lấy lịch sử nghe của họ → score bài theo số lượt nghe chung.
    """
    # Lấy user_id của những người có cùng mood_type (kể cả đã hết hạn —
    # dùng mood gần nhất để tăng coverage)
    co_mood_user_ids = list(
        Mood.objects.filter(mood_type_id=mood_type_id)
        .values_list('user_id', flat=True)
        .distinct()[:limit_users]
    )
    if not co_mood_user_ids:
        return {}

    listen_counts = (
        ListenHistory.objects.filter(user_id__in=co_mood_user_ids)
        .exclude(song_id__in=exclude_ids)
        .values('song_id')
        .annotate(cnt=Count('id'))
    )
    return {row['song_id']: row['cnt'] for row in listen_counts}


def get_songs_for_mood(mood_type_id, user=None, page: int = 1, limit: int = 20) -> dict:
    """
    Gợi ý bài hát phù hợp với 1 loại cảm xúc cụ thể.

    Thuật toán Hybrid (không cần migration):
        1. Genre Mapping  (55%): mood name → keyword → genre_ids → score theo genre match
        2. Co-Mood CF     (45%): user khác có cùng MoodType → lịch sử nghe của họ
        Fallback: nếu không đủ data → trending

    Args:
        mood_type_id: UUID của MoodType
        user:         User đang request (dùng để loại bài đã nghe)
        page:         Trang hiện tại (1-indexed)
        limit:        số bài trả về mỗi trang

    Returns:
        dict {items, total, mood_name, source}
    """
    try:
        mood_type = MoodType.objects.get(id=mood_type_id, is_active=True)
    except MoodType.DoesNotExist:
        return {'items': [], 'total': 0, 'mood_name': '', 'source': 'not_found'}

    viewer = user if getattr(user, 'is_authenticated', False) else None
    user_id = viewer.id if viewer else None

    # Bài hát cần loại trừ (đã nghe / đã like / đã dismiss)
    exclude_ids: set = set()
    if user_id:
        exclude_ids = _excluded_song_ids(user_id)

    blocked_artist_ids: set = set()
    if user_id:
        blocked_artist_ids = set(
            BlockList.objects.filter(blocked_id=user_id).values_list('blocker_id', flat=True)
        )

    base_qs = (
        Song.objects.filter(status=Song.STATUS_PUBLISHED)
        .exclude(id__in=exclude_ids)
        .exclude(artist_id__in=blocked_artist_ids)
        .select_related('artist', 'genre')
    )

    # ── Tín hiệu 1: Genre Mapping ──────────────────────────────────────────
    genre_ids = _match_genre_ids_for_mood(mood_type.name)
    genre_raw: dict = {}
    if genre_ids:
        for sid, play_count in base_qs.filter(genre_id__in=genre_ids).values_list('id', 'play_count'):
            # Bonus thêm cho bài thịnh hành trong genre đó
            genre_raw[sid] = 1.0 + (play_count / max(play_count, 1)) * 0.2

    # ── Tín hiệu 2: Co-Mood Collaborative Filtering ────────────────────────
    co_mood_raw = _co_mood_listen_scores(mood_type_id, exclude_ids)

    genre_norm = _normalize(genre_raw)
    co_mood_norm = _normalize(co_mood_raw)

    all_ids = set(genre_norm) | set(co_mood_norm)

    start = (page - 1) * limit
    end = start + limit

    if not all_ids:
        # Cold-start hoàn toàn: dùng trending
        trending = list(
            base_qs.order_by('-is_trending', '-play_count')[start:end]
        )
        return {
            'items': [s.to_dict(viewer=viewer, include_stats=False) for s in trending],
            'total': len(trending), # This isn't true total but helps frontend know if it's empty
            'mood_name': mood_type.name,
            'source': 'trending',
        }

    hybrid: dict = {
        sid: (
            MOOD_ALPHA_GENRE * genre_norm.get(sid, 0)
            + MOOD_BETA_CO_MOOD * co_mood_norm.get(sid, 0)
        )
        for sid in all_ids
    }
    # Sort all items
    all_ranked_ids = sorted(hybrid, key=lambda k: hybrid[k], reverse=True)
    
    # Get current page
    ranked_ids = all_ranked_ids[start:end]

    # Lấp đầy nếu chưa đủ limit
    if len(ranked_ids) < limit:
        # Nếu đã hết hybrid items, tính toán xem cần bỏ qua bao nhiêu fallback items
        fallback_offset = max(0, start - len(all_ranked_ids))
        fallback_limit = limit - len(ranked_ids)
        
        fallback = list(
            base_qs.exclude(id__in=all_ranked_ids)
            .order_by('-is_trending', '-play_count')
            .values_list('id', flat=True)[fallback_offset : fallback_offset + fallback_limit]
        )
        ranked_ids += fallback

    songs_by_id = {
        s.id: s
        for s in Song.objects.filter(id__in=ranked_ids).select_related('artist', 'genre')
    }
    items = [
        songs_by_id[i].to_dict(viewer=viewer, include_stats=False)
        for i in ranked_ids
        if i in songs_by_id
    ]

    source = 'hybrid' if (genre_raw or co_mood_raw) else 'trending'
    return {
        'items': items,
        'total': len(items),
        'mood_name': mood_type.name,
        'mood_emoji': mood_type.emoji,
        'source': source,
    }


def get_playlists_for_mood(mood_type_id, user=None, page: int = 1, limit: int = 10) -> dict:
    """
    Gợi ý playlist phù hợp với tâm trạng.

    Thuật toán:
        1. Lấy genre_ids của mood → playlist có nhiều bài genre đó
        2. User khác cùng mood → playlist họ thêm vào (nếu có)
        3. Fallback: playlist mới nhất công khai
    """
    try:
        mood_type = MoodType.objects.get(id=mood_type_id, is_active=True)
    except MoodType.DoesNotExist:
        return {'items': [], 'total': 0, 'mood_name': '', 'source': 'not_found'}

    viewer = user if getattr(user, 'is_authenticated', False) else None
    user_id = viewer.id if viewer else None

    blocked_user_ids: set = set()
    if user_id:
        blocked_user_ids = set(
            BlockList.objects.filter(blocked_id=user_id).values_list('blocker_id', flat=True)
        ) | set(
            BlockList.objects.filter(blocker_id=user_id).values_list('blocked_id', flat=True)
        )

    base_qs = (
        Playlist.objects.filter(is_public=True)
        .exclude(owner_id__in=blocked_user_ids)
        .select_related('owner')
    )

    playlists = []

    start = (page - 1) * limit
    end = start + limit

    # ── Tín hiệu 1: Genre match ─────────────────────────────────────────────
    genre_ids = _match_genre_ids_for_mood(mood_type.name)
    
    # We query all matched playlists
    all_matched = []
    if genre_ids:
        from django.db.models import Count as _Count
        all_matched = list(
            base_qs
            .filter(playlist_songs__song__genre_id__in=genre_ids)
            .annotate(match_count=_Count('playlist_songs', distinct=True))
            .order_by('-match_count', '-created_at')
            .distinct()
        )
        
    playlists = all_matched[start:end]

    # ── Lấp đầy bằng playlist mới nhất nếu chưa đủ ─────────────────────────
    if len(playlists) < limit:
        # Calculate offsets for fallback
        fallback_offset = max(0, start - len(all_matched))
        fallback_limit = limit - len(playlists)
        
        seen_ids = [p.id for p in all_matched] # Exclude all matched, not just current page
        from django.db.models import Count as _Count2
        extras = list(
            base_qs.exclude(id__in=seen_ids)
            .order_by('-created_at')[fallback_offset : fallback_offset + fallback_limit]
        )
        playlists += extras

    items = [p.to_dict(viewer=viewer) for p in playlists]
    return {
        'items': items,
        'total': len(items), # Simplified total
        'mood_name': mood_type.name,
        'mood_emoji': mood_type.emoji,
        'source': 'genre_match' if genre_ids else 'latest',
    }
