import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'music_platform.settings')

# Khởi tạo django (phải gọi trước khi import các thư viện)
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

import chat.routing
import notifications.routing
import posts.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        'websocket': AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns +
                notifications.routing.websocket_urlpatterns +
                posts.routing.websocket_urlpatterns
            )
        ),
    }
)