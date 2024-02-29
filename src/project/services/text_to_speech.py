import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

from google.cloud import texttospeech
from google.oauth2.service_account import Credentials

from project.core.settings import GENERAL, Lang
from project.db.models.words import WordExample

lang_map = {
    Lang.EN: {
        'language_code': 'en-GB',
        'name': 'en-GB-Standard-A',
        'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE,
    },
    Lang.RU: {
        'language_code': 'ru-RU',
        'name': 'ru-RU-Standard-C',
        'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE,
    },
    Lang.SR: {
        'language_code': 'sr-RS',
        'name': 'sr-RS-Standard-A',
        'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE,
    },
}
credentials = Credentials.from_service_account_file('google_creds.json')
client = texttospeech.TextToSpeechClient(credentials=credentials)
main_lang_voice = texttospeech.VoiceSelectionParams(lang_map[GENERAL.MAIN_LANG])
second_lang_voice = texttospeech.VoiceSelectionParams(lang_map[GENERAL.SECOND_LANG])
audio_config = texttospeech.AudioConfig({'audio_encoding': texttospeech.AudioEncoding.MP3})
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix='text_to_speech')


async def add_voices_to_word(word: WordExample, save: bool = True) -> None:
    """Добавляет звуковые озвучку слова через google-text-to-speech сервис"""
    loop = asyncio.get_running_loop()
    need_to_save = False

    if not word.value_voice:
        synthesis_input = texttospeech.SynthesisInput({'text': word.value})
        func = partial(
            client.synthesize_speech, input=synthesis_input, voice=second_lang_voice, audio_config=audio_config
        )
        response = await loop.run_in_executor(executor, func)
        word.value_voice = response.audio_content
        need_to_save |= True

    if not word.translation_voice:
        synthesis_input = texttospeech.SynthesisInput({'text': word.translation})
        func = partial(
            client.synthesize_speech, input=synthesis_input, voice=main_lang_voice, audio_config=audio_config
        )
        response = await loop.run_in_executor(executor, func)
        word.translation_voice = response.audio_content
        need_to_save |= True

    if save and need_to_save:
        await word.update(include={'value_voice', 'translation_voice'})


async def add_voices_to_word_example(word: WordExample, word_example: WordExample) -> None:
    await add_voices_to_word(word_example, save=False)
    await word.update(include={'examples'})
