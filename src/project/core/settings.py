import os

from dotenv import load_dotenv

load_dotenv()


class TELEGRAM:
    """Telegram Settings"""

    BOT_TOKEN: str = str(os.environ.get('TELEGRAM_BOT_TOKEN', ''))


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
