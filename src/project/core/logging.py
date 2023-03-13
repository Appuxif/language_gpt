from functools import partial
from logging.config import dictConfig

config = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'common': {
            'format': '%(asctime)s %(levelname)7s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'common',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        '__main__': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'project': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'TeleBot': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True,
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
        'flower': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

configure_logging = partial(dictConfig, config)
