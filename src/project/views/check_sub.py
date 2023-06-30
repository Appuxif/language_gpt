from telebot_views.views.check_sub import CheckSubView as BaseCheckSubView

from project.core import settings


class CheckSubView(BaseCheckSubView):
    """Проверка подписки"""

    ensure_subscription_chat_id: int = settings.TELEGRAM.MAIN_CHANNEL
