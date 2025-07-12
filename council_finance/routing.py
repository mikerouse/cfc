from django.urls import re_path

from .consumers import ContributeConsumer

# URL patterns for WebSocket connections.
websocket_urlpatterns = [
    re_path(r"^ws/contribute/$", ContributeConsumer.as_asgi()),
]
