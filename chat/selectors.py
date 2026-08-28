import math
from django.db.models import Prefetch
from .models import Conversation, Message
from .exceptions import ConversationNotFoundError

def list_user_conversations(user) -> list:
    """
    Lấy danh sách các cuộc trò chuyện của user.
    """
    # prefetch_participants để giảm thiểu N+1 queries khi gọi to_dict
    conversations = Conversation.objects.filter(
        participants=user
    ).prefetch_related('participants').order_by('-updated_at')

    return [c.to_dict(viewer=user) for c in conversations]

def get_conversation_by_id(conversation_id, user) -> Conversation:
    """
    Tìm một cuộc trò chuyện bằng ID và đảm bảo user hiện tại là một người tham gia
    """
    try:
        return Conversation.objects.get(id=conversation_id, participants=user)
    except Conversation.DoesNotExist:
        raise ConversationNotFoundError()

def list_messages_in_conversation(conversation_id, user, page=1, page_size=20) -> dict:
    """
    Lấy lịch sử tin nhắn của cuộc trò chuyện có phân trang chuẩn
    """

    # Xác thực quyền truy cập trước
    conversation = get_conversation_by_id(conversation_id, user)

    # Select related để lấy luôn thông tin người gửi và các đính kèm (chống N+1 query)
    qs = conversation.messages.all().select_related(
        'sender', 
        'shared_song', 'shared_song__artist',
        'shared_album', 'shared_album__artist',
        'shared_playlist', 'shared_playlist__owner'
    ).order_by('-created_at')

    total = qs.count()
    start = (page - 1) * page_size

    messages = qs[start:start + page_size]
    items = [m.to_dict() for m in messages]

    # Đảo ngược mảng để render trên UI dễ hơn (tin cũ xếp trên, tin mới xếp dưới)
    items.reverse()

    return {
        'items': items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': math.ceil(total / page_size) if total > 0 else 1,
        }
    }