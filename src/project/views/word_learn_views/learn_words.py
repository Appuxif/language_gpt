from telebot.types import InlineKeyboardButton

from project.core.views.base import BaseMessageSender, BaseView
from project.db.models.users import UserStateCb
from project.db.models.words import UserWordGroupModel, UserWordModel, UserWordModelManager


class LearnWordsMessageSender(BaseMessageSender):
    """Learn Words Message Sender"""

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:
        r = self.view.route_resolver.routes_registry
        cb = UserStateCb
        group_id = self.view.callback.group_id
        page_num = self.view.callback.page_num or 1

        manager = await self.get_manager()

        if self.view.callback.id == 'select_all':
            await manager.update_many({'$set': {'is_chosen': True}})

        elif self.view.callback.id == 'deselect_all':
            await manager.update_many({'$set': {'is_chosen': False}})

        elif self.view.callback.word_id is not None:
            await manager.by_word(self.view.callback.word_id).update_many(
                [{'$set': {'is_chosen': {'$not': '$is_chosen'}}}]
            )

        user_words: list[UserWordModel] = await self.view.paginator.paginate(manager, page_num, prefetch_words=True)

        # Вывод слов на клавиатуре, если слова вообще есть
        words_btns = []
        for user_word in user_words:
            is_chosen = '✗✓'[user_word.is_chosen]
            btn = await self.view.buttons.btn(
                f'{is_chosen}{await user_word.get_label()}',
                cb(
                    view_name=self.view.view_name,
                    group_id=group_id,
                    word_id=user_word.word_id,
                    page_num=page_num,
                ),
            )
            words_btns.append([btn])

        return [
            *words_btns,
            *(await self.view.paginator.get_pagination(await manager.count(), page_num, group_id=group_id)),
            [
                await self.view.buttons.btn(
                    'Выбрать все',
                    cb(id='select_all', view_name=self.view.view_name, group_id=group_id, page_num=page_num),
                ),
                await self.view.buttons.btn(
                    'Отменить выбор',
                    cb(id='deselect_all', view_name=self.view.view_name, group_id=group_id, page_num=page_num),
                ),
            ],
            [
                await self.view.buttons.view_btn(r['LEARNING_GAME_VIEW'], 0, group_id=group_id),
                await self.view.buttons.view_btn(r['USER_GROUP_VIEW'], 1, group_id=group_id),
            ],
        ]

    async def get_keyboard_text(self) -> str:
        user = await self.view.request.get_user()
        manager = await self.get_manager()
        words_total = await manager.count()
        words_chosen = await manager.by_chosen(True).count()
        group_id = self.view.callback.group_id
        groups = UserWordGroupModel.manager().by_user(user.id).by_wordgroup(group_id)
        group: UserWordGroupModel = await groups.find_one()
        text = f'Выбрано {words_chosen} слов из {words_total}'
        return f'{self.view.labels[0]}. Подборка {await group.get_label()}.\n{text}'

    async def get_manager(self) -> UserWordModelManager:
        user = await self.view.request.get_user()
        group_id = self.view.callback.group_id
        return UserWordModel.manager().by_user(user.id).by_wordgroup(group_id)


class LearnWordsView(BaseView):
    """Отображение страницы начала изучения слов"""

    view_name = 'LEARN_WORDS_VIEW'
    labels = [
        'Учить слова',
        'К изучению слов',
    ]

    message_sender = LearnWordsMessageSender
