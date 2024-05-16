import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()

from telebot_views.log import configure_logging  # pylint: disable=wrong-import-position

configure_logging({})


class Lang(str, Enum):
    """Lang"""

    RU = 'RUSSIAN'
    EN = 'ENGLISH'
    SR = 'SERBIAN'


class GENERAL:
    """General Settings"""

    REPORTS_TELEGRAM_BOT_TOKEN: str = str(os.environ.get('GENERAL_REPORTS_TELEGRAM_BOT_TOKEN', ''))
    REPORTS_TELEGRAM_CHAT_ID: str = str(os.environ.get('GENERAL_REPORTS_TELEGRAM_CHAT_ID', ''))
    MAIN_LANG: Lang = Lang(os.environ.get('GENERAL_MAIN_LANG', ''))
    SECOND_LANG: Lang = Lang(os.environ.get('GENERAL_SECOND_LANG', ''))


class TELEGRAM:
    """Telegram Settings"""

    BOT_TOKEN: str = str(os.environ.get('TELEGRAM_BOT_TOKEN', ''))
    MAIN_CHANNEL: int = int(os.environ.get('TELEGRAM_BOT_MAIN_CHANNEL') or 0)


class MONGODB:
    """MongoDB Settings"""

    USER: str = str(os.environ.get('MONGO_USER', 'project'))
    PASSWORD: str = str(os.environ.get('MONGO_PASSWORD', 'project'))
    HOSTS: str = str(os.environ.get('MONGO_HOSTS', '127.0.0.1:27017'))
    AUTHDB: str = str(os.environ.get('MONGO_AUTHDB', ''))
    ARGS: str = str(os.environ.get('MONGO_ARGS', ''))
    DATABASE: str = str(os.environ.get('MONGO_DATABASE', 'project'))


class OPENAI:
    """OpenAI Settings"""

    API_KEY: str = str(os.environ.get('OPENAI_API_KEY', ''))
