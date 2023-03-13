import asyncio
from functools import cache

from bson.codec_options import CodecOptions
from motor.motor_asyncio import AsyncIOMotorClient, core

from project.core import settings


@cache
def get_url() -> str:
    user = settings.MONGODB.USER
    password = settings.MONGODB.PASSWORD
    hosts = settings.MONGODB.HOSTS
    auth_db = settings.MONGODB.AUTHDB
    args = settings.MONGODB.ARGS
    return f'mongodb://{user}:{password}@{hosts}/{auth_db}?{args}'


def get_database() -> core.AgnosticDatabase:
    loop = asyncio.get_event_loop()
    return _get_database(loop)


def get_collection(name: str) -> core.AgnosticCollection:
    options = CodecOptions(tz_aware=True)
    return get_database().get_collection(name, codec_options=options)


@cache
def _get_database(loop: asyncio.BaseEventLoop) -> core.AgnosticDatabase:
    return AsyncIOMotorClient(get_url(), io_loop=loop)[settings.MONGODB.DATABASE]
