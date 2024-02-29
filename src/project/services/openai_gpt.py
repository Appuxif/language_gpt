import json
from datetime import timedelta
from logging import getLogger
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from telebot_views.models.cache import CacheModel
from telebot_views.utils import now_utc

from project.core.settings import GENERAL, OPENAI
from project.db.models.words import WordExample, WordModel

logger = getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI.API_KEY)


EXAMPLES_TO_WORD_PROMPT = """\
Return three different SENTENCES-examples in different tenses with word "{label}" in form of JSON with keys "value" and "translation" {second_lang} to {main_lang}:

Example:
[
{{
"value": {second_lang} string,
"translation": {main_lang} string,
}}
]

"""

SYSTEM_MESSAGE = f"""\
You are the teacher of the {GENERAL.SECOND_LANG.value} language for {GENERAL.MAIN_LANG.value} students.\
"""


async def add_examples_to_word(word: WordModel, save: bool = True) -> None:
    """Запрашивает у GPT примеры использования слова и добавляет их в поле examples с сохранением слова"""
    prompt = EXAMPLES_TO_WORD_PROMPT.format(
        label=word.label, main_lang=GENERAL.MAIN_LANG.value, second_lang=GENERAL.SECOND_LANG.value
    )
    result = await client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        model='gpt-3.5-turbo',
        max_tokens=2048 - len(prompt),
        temperature=0.5,
    )

    result_list = _json_loads(result.choices[0].message.content)
    word.add_examples(result_list)
    if save:
        await word.update()

    log_debug_prompt_result_chat_completion(prompt, result)


ABOUT_THE_SAME_PROMPT = """\
Here is the {value_lang} word "{word_value}" that translated to {translation_lang} as "{word_translation}".
I need to translate from {value_lang} to {translation_lang} the sentence-example:
"{word_example_value}"

The possible translation is:
"{word_example_translation}"


My variant should contain the word "{word_translation}" in any form.
My variant should imply the correct meaning.
My variant should be a good translation to the sentence-example.

My variant:
"{my_variant}"


Think carefully and give a detailed answer to the question: is my variant a good translation of the sentence-example?

Provide the answer in the JSON form {{"answer": true/false, "explanation": string}}. \
The explanation should be on the {main_lang} language.
"""


async def whether_translation_is_correct(
    word: WordModel, word_example: WordExample, sentence: str, value_or_translation: bool
) -> tuple[bool, str]:

    cache_key = f'word:{word.id}:word_example:{word_example.id}:sentence:{sentence}:v2'

    cache = await CacheModel.manager().by_key(cache_key).is_valid().find_one(raise_exception=False)
    if cache is not None:
        logger.debug('Translation %s found in cache', cache_key)
        return cache.data['decision'], cache.data['result_string']

    if value_or_translation:
        prompt = ABOUT_THE_SAME_PROMPT.format(
            main_lang=GENERAL.MAIN_LANG,
            translation_lang=GENERAL.MAIN_LANG,
            value_lang=GENERAL.SECOND_LANG,
            word_value=word.value,
            word_translation=word.translation,
            word_example_value=word_example.value,
            word_example_translation=word_example.translation,
            my_variant=sentence,
        )
    else:
        prompt = ABOUT_THE_SAME_PROMPT.format(
            main_lang=GENERAL.MAIN_LANG,
            translation_lang=GENERAL.SECOND_LANG,
            value_lang=GENERAL.MAIN_LANG,
            word_value=word.translation,
            word_translation=word.value,
            word_example_value=word_example.translation,
            word_example_translation=word_example.value,
            my_variant=sentence,
        )

    result = await client.chat.completions.create(
        messages=[
            {'role': 'system', 'content': SYSTEM_MESSAGE},
            {'role': 'user', 'content': prompt},
        ],
        model="gpt-3.5-turbo",
        max_tokens=1024,
        temperature=0,
    )
    log_debug_prompt_result_chat_completion(prompt, result)

    result_dict = _json_loads(result.choices[0].message.content)

    decision, result_string = result_dict['answer'], result_dict['explanation']
    if decision is True:
        result_string = ''
    else:
        result_string = f'{sentence}\n\n{result_string}\n'

    await CacheModel(
        key=cache_key,
        data={'decision': decision, 'result_string': result_string},
        valid_until=now_utc() + timedelta(days=30),
    ).insert()

    return decision, result_string


def log_debug_prompt_result_chat_completion(prompt: str, result: ChatCompletion):
    logger.debug(
        'Got completion result of `%s` (Response %s. Usage %s):\n`%s`',
        prompt,
        result.created,
        dict(result.usage),
        [choice.dict() for choice in result.choices],
    )


def _json_loads(data: str) -> Any:
    data = data.strip()
    if data.startswith('```json'):
        data = data[7:-3].strip()
    return json.loads(data)
