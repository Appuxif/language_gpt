from telebot.types import InlineKeyboardButton
from telebot_views.views.main import MainMessageSender as BaseMainMessageSender, MainView as BaseMainView

from project.core import settings
from project.services import reviews


class MainMessageSender(BaseMainMessageSender):
    """Main Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        results = await super().get_keyboard()
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()

        additional_btns = []
        if user.is_superuser:
            additional_btns += [
                [await self.view.buttons.view_btn(r['MAIN_ADMIN_VIEW'], 0)],
            ]
        if reviews.is_waiting_for_review(user):
            additional_btns += [
                [await self.view.buttons.view_btn(r['REVIEWS_VIEW'], 1, view_params={'edit_keyboard': False})],
            ]

        return results + [
            [await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 1)],
            [await self.view.buttons.view_btn(r['PUBLIC_GROUPS_VIEW'], 1)],
            *additional_btns,
            # [await self.view.buttons.btn('Переводчик', cb(view_name=r['TRANSLATOR_VIEW']))],
            # [await self.view.buttons.btn('Общение с AI', cb(view_name=r['AI_CHAT_VIEW']))],
            # [await self.view.buttons.btn('Статистика', cb(view_name=r['STATISTICS_VIEW']))],
            # [await self.view.buttons.btn('Настройки', cb(view_name=r['SETTINGS_VIEW']))],
        ]

    async def get_keyboard_text(self) -> str:
        return self.view.labels[0]


class MainView(BaseMainView):
    """Отображение главного меню"""

    message_sender = MainMessageSender
    labels = list(BaseMainView.labels)
    labels[1] = '🚶‍ ' + labels[1]
    ensure_subscription_chat_id = settings.TELEGRAM.MAIN_CHANNEL
