import json
from datetime import timedelta
from logging import getLogger

import openai
from openai.openai_object import OpenAIObject
from telebot_views.models.cache import CacheModel

from project.core.settings import OPENAI
from project.db.models.words import WordExample, WordModel
from project.utils.timezones import now_utc

logger = getLogger(__name__)
openai.api_key = OPENAI.API_KEY


EXAMPLES_TO_WORD_PROMPT = """\
Three sentences in different tenses with word "{label}" in JSON with keys "value" and "translation" English to Russian:
["""


async def add_examples_to_word(word: WordModel, save: bool = True) -> None:
    """Запрашивает у GPT примеры использования слова и добавляет их в поле examples с сохранением слова"""
    prompt = EXAMPLES_TO_WORD_PROMPT.format(label=word.label)
    result = await openai.Completion.acreate(
        prompt=prompt,
        model="text-davinci-003",
        max_tokens=2048 - len(prompt),
        temperature=0.5,
    )
    result_list = json.loads('[' + result['choices'][0]['text'].strip())
    word.add_examples(result_list)
    if save:
        await word.update()

    log_debug_prompt_result(prompt, result)


ABOUT_THE_SAME_PROMPT = """\
Read the next sentences and give detailed answer the questions in JSON \
like {{"1": true, "2": false, ...}}:


Data: {{"correct-sentence-english": "{sentence2.value}", \
"correct-sentence-russian": "{sentence2.translation}", \
"guess-sentence": "{sentence1}"}}


Questions: {{\
"1": "Is the guess-sentence using the word "{word}"?", \
"2": "Does the guess-sentence imply the same as correct-sentence?", \
"3": "Are the guess-sentence and the correct-sentence syntactic similar?", \
"4": "Are the guess-sentence and the correct-sentence logically similar", \
"5": "Could the guess-sentence be the correct translation of the correct-sentence?",\
"6": "Are the guess-sentence and the correct-sentence in the same tense?"\
}}


Result: {{"1":"""


async def whether_translation_is_correct(word: WordModel, word_example: WordExample, sentence: str) -> tuple[bool, str]:

    cache_key = f'word:{word.id}:word_example:{word_example.id}:sentence:{sentence}:v2'

    cache = await CacheModel.manager().by_key(cache_key).is_valid().find_one(raise_exception=False)
    if cache is not None:
        logger.debug('Translation %s found in cache', cache_key)
        return cache.data['decision'], cache.data['result_string']

    prompt = ABOUT_THE_SAME_PROMPT.format(
        word=word.label,
        sentence1=sentence,
        sentence2=word_example,
    )
    result = await openai.Completion.acreate(prompt=prompt, model="text-davinci-003", max_tokens=1024, temperature=0)
    log_debug_prompt_result(prompt, result)

    result_string = result['choices'][0]['text'].strip()
    result_dict = json.loads('{"1":' + result_string)

    decision = False
    if result_dict['1'] is False:
        result_string = 'Перевод не содержит загаданное слово'
    elif result_dict['2'] is False:
        result_string = 'Перевод содержит ошибки'
    elif result_dict['3'] is False:
        result_string = 'Перевод составлен синтаксически неверно'
    elif result_dict['4'] is False:
        result_string = 'Перевод составлен логически неверно'
    elif result_dict['5'] is False:
        result_string = 'Неверный перевод'
    elif result_dict['6'] is False:
        result_string = 'Перевод имеет неверное время'
    else:
        decision = True
        result_string = ''

    await CacheModel(
        key=cache_key,
        data={'decision': decision, 'result_string': result_string},
        valid_until=now_utc() + timedelta(days=30),
    ).insert()
    return decision, result_string


def log_debug_prompt_result(prompt: str, result: OpenAIObject):
    logger.debug(
        'Got completion result of `%s` (Response %s. Usage %s):\n`%s`',
        prompt,
        result.response_ms,
        dict(result.usage),
        [dict(choice) for choice in result['choices']],
    )
