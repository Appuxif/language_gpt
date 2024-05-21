"""Рассылает уведомление "Оставь отзыв" всем пользователям, которые еще ни разу не оставляли отзыв."""

import asyncio
from datetime import timedelta
from logging import getLogger

from asyncio_functools import async_lru_cache
from bson import ObjectId
from telebot.asyncio_helper import ApiTelegramException
from telebot_views import bot
from telebot_views.bot import ParseMode
from telebot_views.models import UserModel, UserStateCb, get_user_model
from telebot_views.models.links import LinkModel
from telebot_views.utils import now_utc

from project.main import run_loop
from project.services import reviews
from project.views.reviews import ReviewsView

logger = getLogger(__name__)


def run() -> None:
    run_loop(_run)


async def _run():
    manager = (
        get_user_model()
        .manager()
        .filter(
            {
                'is_available': True,
                '_id': {'$lt': ObjectId.from_datetime(now_utc() - timedelta(days=7))},
                '$and': [
                    {
                        '$or': [
                            {f'constants.{reviews.REVIEWS_INFO_KEY}': None},
                            {f'constants.{reviews.REVIEWS_INFO_KEY}.is_waiting_for_review': None},
                            {f'constants.{reviews.REVIEWS_INFO_KEY}.is_waiting_for_review': False},
                        ]
                    },
                    {
                        '$or': [
                            {f'constants.{reviews.REVIEWS_INFO_KEY}.last_review_at': None},
                            {
                                f'constants.{reviews.REVIEWS_INFO_KEY}.last_review_at': {
                                    '$lt': ObjectId.from_datetime(now_utc() - timedelta(days=30))
                                }
                            },
                        ]
                    },
                ],
            }
        )
    )

    total = await manager.count()
    page_size = 30
    page_num = 0
    logger.info('Starting sending notifications to %s users by chunks', total)
    while True:
        page_num += 1
        logger.info('Sending notifications for chunk %s...', page_num)
        chunk = await manager.find_all(
            sort=[('_id', 1)],
            limit=page_size,
            skip=(page_num - 1) * page_size,
        )
        if not chunk:
            logger.info('Users not found. Break')
            break
        logger.info('Got %s users', len(chunk))

        for user in chunk:
            await send_notification(user)
        logger.info('Sleeping...')
        await asyncio.sleep(1.1)

    logger.info('Notifications finished')


async def send_notification(user: UserModel) -> None:
    link = await _get_link()
    logger.info('Sending notification for user %s', user.id)

    try:
        reviews.set_waiting_for_review(user)
        await reviews.save_reviews_info(user)
        await bot.bot.send_message(
            user.user_id,
            'Привет! Как насчет оставить отзыв? Это очень важно для нас. '
            f'Ты можешь найти кнопку "{ReviewsView.labels[1]}" в главном меню. '
            f'Или перейди по [ссылке]({link.get_bot_start_link()}).',
            parse_mode=ParseMode.MARKDOWN.value,
            disable_web_page_preview=True,
        )
    except ApiTelegramException as err:  # pylint: disable=broad-except
        if (
            'chat not found' in err.description
            or 'bot was blocked by the user' in err.description
            or 'user is deactivated' in err.description
            or 'bots can\'t send messages to bots' in err.description
        ):
            await get_user_model().manager().filter({'_id': user.id}).update_many({'$set': {'is_available': False}})
            logger.info('%s. User % is not available any more', err.description, user.user_id)
        else:
            raise
    logger.info('Sending notification for user %s finished', user.id)


@async_lru_cache()
async def _get_link() -> LinkModel:
    return await LinkModel.manager().get_or_create(
        LinkModel(callback=UserStateCb(view_name='REVIEWS_VIEW', view_params={'edit_keyboard': False}))
    )


if __name__ == '__main__':
    run()
