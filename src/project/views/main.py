from telebot.types import InlineKeyboardButton

from project.core.views.base import BaseMessageSender, BaseView, RouteResolver


class MainRouteResolver(RouteResolver):
    """Main Route Resolver"""

    async def resolve(self) -> bool:
        return self.request.message.text == '/start' or await super().resolve()


class MainMessageSender(BaseMessageSender):
    """Main Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        # cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        return [
            [await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 0)],
            # [await self.view.buttons.btn('Публичные подборки', cb(view_name=r['PUBLIC_GROUPS_VIEW']))],
            # [await self.view.buttons.btn('Переводчик', cb(view_name=r['TRANSLATOR_VIEW']))],
            # [await self.view.buttons.btn('Общение с AI', cb(view_name=r['AI_CHAT_VIEW']))],
            # [await self.view.buttons.btn('Статистика', cb(view_name=r['STATISTICS_VIEW']))],
            # [await self.view.buttons.btn('Настройки', cb(view_name=r['SETTINGS_VIEW']))],
        ]

    async def get_keyboard_text(self) -> str:
        return self.view.labels[0]


class MainView(BaseView):
    """Отображение главного меню"""

    view_name = 'MAIN_VIEW'
    edit_keyboard = False
    labels = [
        'Главное меню',
        'В главное меню',
    ]

    route_resolver = MainRouteResolver
    message_sender = MainMessageSender
