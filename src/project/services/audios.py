from io import BytesIO

from pydub import AudioSegment


def concat_audios(*data_list: bytes, silence_duration: int = 500) -> bytes:
    result = AudioSegment.empty()
    silence = AudioSegment.silent(silence_duration)
    for data in data_list:
        with BytesIO(data) as file:
            segment = AudioSegment.from_mp3(file)
            result = result + segment + silence

    with BytesIO() as result_file:
        result.export(result_file)
        result_file.seek(0)
        return result_file.read()
