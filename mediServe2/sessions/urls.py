from django.urls import path
from .views import ConversationLogAPIView, SessionStatsAPIView

urlpatterns = [
    path('conversations/log/', ConversationLogAPIView.as_view(), name='conversation-log'),
    path('sessions/stats/', SessionStatsAPIView.as_view(), name='session-stats'),
]