import asyncio

from telebot.types import InlineKeyboardButton
from telebot_views.base import BaseMessageSender, BaseView
from telebot_views.models import UserStateCb

from project.db.models.words import UserWordGroupModel, UserWordModel, WordGroupModel
from project.views.word_learn.utils import MIN_WORDS_TO_START_GAME


class UserGroupMessageSender(BaseMessageSender):
    """User Group Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        cb = UserStateCb
        r = self.view.route_resolver.routes_registry
        user = await self.view.request.get_user()
        group_id = self.view.callback.params.get('group_id')
        page_num = self.view.callback.page_num or 1

        manager = UserWordModel.manager().by_user(user.id).by_wordgroup(group_id)
        word_count = await manager.count()
        group, user_words = await asyncio.gather(
            WordGroupModel.manager().find_one(group_id),
            self.view.paginator.paginate(manager, page_num, word_count, prefetch_words=True),
        )  # type: WordGroupModel, list[UserWordModel]

        # Вывод слов на клавиатуре, если слова вообще есть
        async def prepare_word(user_word: UserWordModel) -> list[InlineKeyboardButton]:
            callback = cb(
                view_name=r['WORD_VIEW'].value,
                params={'group_id': group_id, 'word_id': user_word.word_id},
                page_num=page_num,
            )
            return [await self.view.buttons.btn(await user_word.get_label(), callback)]

        additional_btns = []
        private_btns = [
            [
                await self.view.buttons.view_btn(
                    r['DELETE_USER_GROUP_VIEW'], 1, params={'group_id': group_id}, page_num=page_num
                )
            ],
        ]
        if not group.is_public:
            additional_btns += [
                [await self.view.buttons.view_btn(r['ADD_WORD_VIEW'], 0, params={'group_id': group_id})]
            ]
            if word_count >= MIN_WORDS_TO_START_GAME:
                private_btns.append(
                    [await self.view.buttons.view_btn(r['PUBLISH_USER_GROUP_VIEW'], 1, params={'group_id': group_id})]
                )

        if word_count >= MIN_WORDS_TO_START_GAME:
            additional_btn = await self.view.buttons.view_btn(
                r['LEARN_WORDS_VIEW'], 0, params={'group_id': group_id}, page_num=page_num
            )
            if additional_btns:
                additional_btns[0].append(additional_btn)
            else:
                additional_btns.append([additional_btn])

        return [
            *(await asyncio.gather(*map(prepare_word, user_words))),
            *(await self.view.paginator.get_pagination(word_count, page_num, params={'group_id': group_id})),
            *additional_btns,
            *private_btns,
            [await self.view.buttons.view_btn(r['USER_GROUPS_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        group_id = self.view.callback.params.get('group_id')
        user = await self.view.request.get_user()
        groups = UserWordGroupModel.manager().by_wordgroup(group_id).by_user(user.id)
        group: UserWordGroupModel = await groups.find_one()

        words_total = await UserWordModel.manager().by_user(user.id).by_wordgroup(group_id).count()

        text = f'{self.view.labels[0]} {await group.get_label()}'
        if words_total:
            text += f'\nСлов: {words_total}'
        return text


class UserGroupView(BaseView):
    """Отображение списка слов в подборке"""

    view_name = 'USER_GROUP_VIEW'
    edit_keyboard = True
    delete_income_messages = True
    ignore_income_messages = True
    labels = [
        'Подборка',
        '🚶 В Подборку',
        'Подборки',
    ]

    message_sender = UserGroupMessageSender
