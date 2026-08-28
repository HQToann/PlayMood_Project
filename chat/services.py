import logging
from social.models import Follow
from music.models import Song
from .models import Conversation, Message
from .exceptions import NotFriendsError
from .validators import validate_message_content
from .selectors import get_conversation_by_id

logger = logging.getLogger(__name__)

def check_is_friend(user, target_user) -> bool:
    """
    Kiểm tra xem 2 người có follow chéo nhau không (bạn bè).
    """
    user_follows_target = Follow.objects.filter(follower=user, following=target_user).exists()
    target_follows_user = Follow.objects.filter(follower=target_user, following=user).exists()
    return user_follows_target and target_follows_user

def get_or_create_direct_conversation(user, target_user) -> tuple[Conversation, bool]:
    """
    Tạo hoặc lấy ra cuộc trò chuyện 1-1. Trả về (Conversation, created_flag)
    """

    # Ràng buộc nghiệp vụ: Chỉ bạn bè mới được chat với nhau
    if not check_is_friend(user, target_user):
        raise NotFriendsError()

    # Lấy các đoạn chat có user tham gia
    conversations = Conversation.objects.filter(participants=user).filter(participants=target_user)

    # Tìm đoạn chat 1-1 (chỉ có 2 người)
    for conv in conversations:
        if conv.participants.count() == 2:
            return conv, False

    # Nếu chưa có, tạo mới
    new_conv = Conversation.objects.create()
    new_conv.participants.add(user, target_user)
    logger.info('Cuộc trò chuyện mới được tạo giữa %s và %s', user.username, target_user.username)
    return new_conv, True

def create_message(sender, conversation_id, data: dict) -> Message:
    """
    Tạo tin nhắn mới và lưu vào csdl
    """
    content = data.get('content', '')
    image_url = data.get('image_url', None)
    shared_song_id = data.get('shared_song_id', None)
    shared_album_id = data.get('shared_album_id', None)
    shared_playlist_id = data.get('shared_playlist_id', None)

    # 1. Validation
    validate_message_content(content, image_url, shared_song_id, shared_album_id, shared_playlist_id)

    # 2. Lấy conversation (đồng thời kiểm tra quyền)
    conversation = get_conversation_by_id(conversation_id, sender)

    # 3. Lấy Object đính kèm nếu có
    from music.models import Album
    from playlists.models import Playlist
    
    song_obj = None
    if shared_song_id:
        song_obj = Song.objects.get(id=shared_song_id)
        
    album_obj = None
    if shared_album_id:
        album_obj = Album.objects.get(id=shared_album_id)
        
    playlist_obj = None
    if shared_playlist_id:
        playlist_obj = Playlist.objects.get(id=shared_playlist_id)

    # 4. Lưu tin nhắn mới
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        content=content,
        image_url=image_url,
        shared_song=song_obj,
        shared_album=album_obj,
        shared_playlist=playlist_obj
    )

    # Cập nhật thời gian updated_at của Conversation để đẩy nó lên đầu danh sách chat
    conversation.save()

    logger.info('Tin nhắn mới được gửi bởi %s trong cuộc trò chuyện %s', sender.username, conversation_id)
    return message

def mark_messages_as_read(conversation_id, user) -> int:
    """
    Đánh dấu toàn bộ tin nhắn của đối phương trong cuộc trò chuyện này là đã đọc
    """
    conversation = get_conversation_by_id(conversation_id, user)

    # Chỉ update những tin nhắn do người khác gửi và chưa đọc
    unread_messages = conversation.messages.exclude(sender=user).filter(is_read=False)
    updated_count = unread_messages.update(is_read=True)

    if updated_count > 0:
        logger.info('%s đã đọc %d tin nhắn trong cuộc trò chuyện %s', user.username, updated_count, conversation_id)
    return updated_count