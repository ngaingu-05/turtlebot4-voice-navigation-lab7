"""ASR smoke test on SYNTHETIC eSpeak or cached Google TTS audio, not human voice.

eSpeak generation needs libespeak-ng.so.1. Run in the voice venv with ROS sourced.
No navigation is sent. --source gtts reads the checked-in MP3s without cloud calls.
"""
import ctypes
import argparse
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import time
import wave

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1] / 'src/tb4_voice_navigation'
sys.path.insert(0, str(PACKAGE / 'scripts'))
from voice_core import RegionCatalog


def generate_samples():
    library = ctypes.CDLL('libespeak-ng.so.1')
    library.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    sample_rate = library.espeak_Initialize(2, 0, None, 0)
    if sample_rate <= 0 or library.espeak_SetVoiceByName(b'vi') != 0:
        raise RuntimeError('Vietnamese eSpeak voice unavailable')
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
    chunks = []

    @callback_type
    def collect(samples, count, _):
        if samples and count:
            chunks.append(ctypes.string_at(samples, count * 2))
        return 0

    library.espeak_SetSynthCallback.argtypes = [callback_type]
    library.espeak_SetSynthCallback(collect)
    library.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int,
                                     ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    folder = HERE / 'synthetic_audio'
    folder.mkdir(exist_ok=True)
    cases = [('Đi đến khu vực a.', ['A']),
             ('Di chuyển từ khu vực a đến khu vực bê.', ['A', 'B']),
             ('Đi đến phòng thí nghiệm.', ['B'])]
    samples = []
    for i, (text, route) in enumerate(cases, 1):
        chunks.clear()
        data = text.encode('utf-8') + b'\0'
        buffer = ctypes.create_string_buffer(data)
        if library.espeak_Synth(buffer, len(data), 0, 1, 0, 1, None, None) != 0:
            raise RuntimeError('eSpeak synthesis failed')
        library.espeak_Synchronize()
        filename = folder / f'command_{i}.wav'
        with wave.open(str(filename), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(sample_rate)
            stream.writeframes(b''.join(chunks))
        samples.append((filename, text, route))
    library.espeak_Terminate()
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='small', choices=['base', 'small'])
    parser.add_argument('--source', default='espeak', choices=['espeak', 'gtts'],
                        help='gtts reads pre-generated synthetic MP3s from gtts_audio/')
    args = parser.parse_args()
    from faster_whisper import WhisperModel
    loader = importlib.machinery.SourceFileLoader('speech', str(PACKAGE / 'scripts/speech_recognition_node'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    speech = importlib.util.module_from_spec(spec)
    loader.exec_module(speech)
    if args.source == 'espeak':
        samples = generate_samples()
        provenance = 'eSpeak-generated Vietnamese audio; NOT human microphone recordings'
        evidence_name = f'synthetic_speech_{args.model}.json'
    else:
        texts = [('Đi đến khu vực a.', ['A']),
                 ('Di chuyển từ khu vực a đến khu vực bê.', ['A', 'B']),
                 ('Đi đến phòng thí nghiệm.', ['B'])]
        samples = [(HERE / 'gtts_audio' / f'command_{i}.mp3', text, expected)
                   for i, (text, expected) in enumerate(texts, 1)]
        if any(not filename.exists() for filename, _, _ in samples):
            parser.error('Missing pre-generated gtts_audio/command_1..3.mp3')
        provenance = 'Google Translate TTS via gTTS 2.5.4; SYNTHETIC audio, NOT human microphone recordings'
        evidence_name = f'synthetic_speech_gtts_{args.model}.json'
    catalog = RegionCatalog.load(PACKAGE / 'maps/regions.yaml')
    print(f'Loading multilingual Whisper {args.model} (CPU int8)...', flush=True)
    model = WhisperModel(args.model, device='cpu', compute_type='int8')
    results = []
    for filename, text, expected in samples:
        start = time.monotonic()
        transcript = speech.transcribe(model, str(filename))
        try:
            actual = catalog.parse(transcript)
            error = None
        except ValueError as exc:
            actual, error = None, str(exc)
        result = dict(audio=str(filename.relative_to(HERE)), synthetic_text=text, transcript=transcript,
                      expected=expected, actual=actual, passed=actual == expected,
                      transcription_s=time.monotonic() - start, error=error)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    (HERE / evidence_name).write_text(json.dumps(
        {'source': provenance,
         'model': args.model, 'compute_type': 'int8', 'results': results},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
