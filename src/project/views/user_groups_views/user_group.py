from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.db.models.words import UserWordGroupModel, UserWordModel


class UserGroupMessageSender(BaseMessageSender):
    """User Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        group_id = self.view.callback.params.get('group_id')
        page_num = self.view.callback.page_num or 1

        manager = UserWordModel.manager().by_user(user.id).by_wordgroup(group_id)
        user_words: list[UserWordModel] = await self.view.paginator.paginate(manager, page_num, prefetch_words=True)

        # Вывод слов на клавиатуре, если слова вообще есть
        words_btns = []
        for user_word in user_words:
            callback = cb(
                view_name=r['WORD_VIEW'].value,
                params={'group_id': group_id, 'word_id': user_word.word_id},
                page_num=page_num,
            )
            btn = [await self.view.buttons.btn(await user_word.get_label(), callback)]
            words_btns.append(btn)

        additional_btns = [[await self.view.buttons.view_btn(r['ADD_WORD_VIEW'], 0, params={'group_id': group_id})]]
        if bool(user_words):
            additional_btns[0].append(
                await self.view.buttons.view_btn(r['LEARN_WORDS_VIEW'], 0, params={'group_id': group_id})
            )

        return [
            *words_btns,
            *(await self.view.paginator.get_pagination(await manager.count(), page_num, params={'group_id': group_id})),
            *additional_btns,
            [
                await self.view.buttons.view_btn(r['DELETE_USER_GROUP_VIEW'], 1, params={'group_id': group_id}),
                await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 1),
            ],
        ]

    async def get_keyboard_text(self) -> str:
        group_id = self.view.callback.params.get('group_id')
        user = await self.view.request.get_user()
        groups = UserWordGroupModel.manager().by_wordgroup(group_id).by_user(user.id)
        group: UserWordGroupModel = await groups.find_one()
        return f'{self.view.labels[0]} {await group.get_label()}'


class UserGroupView(BaseView):
    """Отображение списка слов в подборке"""

    view_name = 'USER_GROUP_VIEW'
    edit_keyboard = True
    labels = [
        'Подборка',
        'В Подборку',
        'Подборки',
    ]

    message_sender = UserGroupMessageSender
