import asyncio
from typing import Optional

from bson import ObjectId
from telebot.types import InlineKeyboardButton
from telebot_views import bot
from telebot_views.base import BaseView, KeyboardMessageSender
from telebot_views.models import UserStateCb
from telebot_views.models.links import LinkModel

from project.services import reviews


class ReviewMessageSender(KeyboardMessageSender):

    async def send(self) -> None:
        user = await self.view.request.get_user()

        if not reviews.is_waiting_for_review(user):
            await bot.bot.send_message(self.view.request.msg.chat.id, 'У нас уже есть твой отзыв. Попробуй позже')
            return

        if self.view.request.msg:
            is_valid, validation_text = _validate_msg_text(self.view.request.msg.text)
            if is_valid:
                review = await reviews.create_new_review(user, self.view.request.msg.text)
                await asyncio.gather(
                    bot.bot.send_message(self.view.request.msg.chat.id, 'Спасибо за отзыв!'),
                    _send_report(review.id),
                )
                return
            if validation_text:
                await bot.bot.send_message(self.view.request.msg.chat.id, validation_text)

        return await super().send()

    async def get_keyboard(self) -> list[list[InlineKeyboardButton]]:

        r = self.view.route_resolver.routes_registry
        return [
            [await self.view.buttons.view_btn(r['MAIN_VIEW'], 1)],
        ]

    async def get_keyboard_text(self) -> str:
        text = 'Оставь, пожалуйста, свой отзыв. Это очень важно для нас.\n'
        text += 'Любые пожелания, улучшения, критика - приветствуется всё!'
        return text


class ReviewsView(BaseView):
    view_name = 'REVIEWS_VIEW'
    edit_keyboard = True
    delete_income_messages = False
    labels = [
        'Отзывы',
        '💬 Оставить отзыв',
    ]
    message_sender = ReviewMessageSender

    async def redirect(self) -> Optional['BaseView']:
        r = self.route_resolver.routes_registry
        user = await self.request.get_user()

        if not reviews.is_waiting_for_review(user) or self.request.msg and _validate_msg_text(self.request.msg.text)[0]:
            return r['MAIN_VIEW'].view(self.request, self.callback)
        return None


def _validate_msg_text(text: str) -> tuple[bool, str]:
    if len(text) > 1000:
        return False, 'Слишком длинное сообщение'
    if text.startswith('/start'):
        return False, ''
    return True, ''


async def _send_report(review_id: ObjectId) -> None:
    link = await LinkModel.manager().get_or_create(
        LinkModel(
            callback=UserStateCb(
                view_name='REVIEW_DETAIL_ADMIN_VIEW',
                view_params={'edit_keyboard': False},
                params={'review_oid': review_id},
            )
        )
    )
    await bot.reports_bot.send_message(
        bot.reports_chat_id,
        f'Новый отзыв!\n{link.get_bot_start_link()}',
        disable_web_page_preview=True,
    )
