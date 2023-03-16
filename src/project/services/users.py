from telebot.types import CallbackQuery, Message

from project.db.models.users import UserModel


class UsersService:
    """Users Service"""

    @staticmethod
    async def get_user_for_message(msg: Message | CallbackQuery) -> UserModel:
        to_insert = False
        user = await UserModel.manager({'user_id': msg.from_user.id}).find_one(raise_exception=False)

        if user is None:
            to_insert = True
            user = UserModel()

        user.user_id = msg.from_user.id
        user.username = msg.from_user.username or ''
        user.first_name = msg.from_user.first_name or ''
        user.last_name = msg.from_user.last_name or ''

        if to_insert:
            await user.insert()
        else:
            await user.update()
        return user
