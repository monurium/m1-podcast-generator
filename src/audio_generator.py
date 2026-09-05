import os
import re
import sys
import time
import base64
import asyncio
import tempfile
from typing import Dict, Any, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_EDGE_VOICE = "tr-TR-AhmetNeural"

EDGE_VOICE_MAP = {
    "Kaan":    "tr-TR-AhmetNeural",
    "Ece":     "tr-TR-EmelNeural",
    "Ahmet":   "tr-TR-AhmetNeural",
    "Emel":    "tr-TR-EmelNeural",
    "Alex":    "tr-TR-AhmetNeural",
    "Sarah":   "tr-TR-EmelNeural",
    "Sunucu":  "tr-TR-AhmetNeural",
}

GEMINI_TTS_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-tts",
    "gemini-2.0-flash",
    "gemini-2.5-flash-preview-tts",
)

GEMINI_VOICE_MAP = {
    # Türkçe teknoloji ve bülten podcasti için en doğal karakter eşleşmeleri:
    # Kaan (Erkek): "Puck"  — Dinamik, enerjik, vizyoner teknoloji sunucusu tonu
    # Ece  (Kadın): "Aoede" — Doğal, akıcı, sıcak, analitik kadın teknoloji sunucusu tonu
    "Kaan":    "Puck",
    "Ece":     "Aoede",
    "Ahmet":   "Puck",
    "Emel":    "Aoede",
    "Alex":    "Puck",
    "Sarah":   "Aoede",
    "Sunucu":  "Puck",
}

class GeminiRateLimiter:
    """
    Dakikada maksimum 10 istek (10 RPM) gitmesini kesin olarak garanti eden
    kayan pencere (sliding window) ve ardışık istek aralığı koruma mekanizması.
    """
    def __init__(self, max_rpm: int = 10, min_interval_sec: float = 6.2):
        self.max_rpm = max_rpm
        self.min_interval = min_interval_sec
        self.timestamps: List[float] = []
        self.last_call_time = 0.0

    def wait_if_needed(self):
        now = time.time()
        # 1. 60 saniyeden eski istekleri listeden temizle
        self.timestamps = [t for t in self.timestamps if now - t < 60.0]

        # 2. Son 60 saniye içindeki istek sayısı max_rpm (10) ise bekle
        if len(self.timestamps) >= self.max_rpm:
            oldest = self.timestamps[0]
            sleep_time = 60.0 - (now - oldest) + 0.5  # 0.5 sn ek güvenlik payı
            if sleep_time > 0:
                print(f"⏳ [Gemini Rate-Limit Koruması] Dakikada maks {self.max_rpm} istek sınırı devrede. {sleep_time:.1f} sn bekleniyor...")
                time.sleep(sleep_time)
                now = time.time()
                self.timestamps = [t for t in self.timestamps if now - t < 60.0]

        # 3. İki istek arasında minimum bekleme süresini zorunlu kıl (~6.2 sn)
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            gap_sleep = self.min_interval - elapsed
            print(f"⏳ [Gemini Rate-Limit] İstek aralığı korunuyor ({gap_sleep:.1f} sn bekleme, maks {self.max_rpm} RPM)...")
            time.sleep(gap_sleep)

        call_time = time.time()
        self.timestamps.append(call_time)
        self.last_call_time = call_time

# Maximum simultaneous Edge-TTS requests — prevents Microsoft rate-limit errors
_EDGE_TTS_SEMAPHORE_LIMIT = 5

# Silence durations (milliseconds) for different context types
_PAUSE_SHORT_MS  = 350   # rapid Q&A between hosts
_PAUSE_NORMAL_MS = 500   # standard turn transition
_PAUSE_LONG_MS   = 750   # new-topic / news segment boundary


# ---------------------------------------------------------------------------
# SILENT MP3 HELPERS
# ---------------------------------------------------------------------------

def _make_silent_mp3(duration_ms: int = 500) -> bytes:
    """Returns a valid silent MP3 byte buffer of approximately `duration_ms` milliseconds.

    Strategy: Use lameenc to encode true PCM silence so every byte is a valid
    MP3 frame.  If lameenc is unavailable, fall back to a mathematically
    correct MPEG1 Layer-3 128 kbps silent frame repeated N times.

    The original implementation used a hard-coded 417-byte pseudo-frame which
    is one byte short of the correct MPEG1-L3-128kbps frame size (418 bytes),
    causing click/glitch artefacts on many decoders.
    """
    try:
        import lameenc
        # 44100 Hz stereo PCM — duration_ms of silence
        num_samples = int(44100 * duration_ms / 1000)
        pcm_silence = bytes(num_samples * 2 * 2)   # 2 channels × 2 bytes (16-bit)
        enc = lameenc.Encoder()
        enc.set_bit_rate(128)
        enc.set_in_sample_rate(44100)
        enc.set_channels(2)
        enc.set_quality(3)
        return enc.encode(pcm_silence) + enc.flush()
    except Exception:
        pass

    # Fallback: valid MPEG1 Layer-3 128 kbps @ 44100 Hz stereo Huffman-coded
    # silent frame = 417 bytes (floor((144 * 128000 / 44100) + 0)) = 417.95...
    # Python struct: sync(0xFFE0) | MPEG1(0x18) | Layer3(0x04) | 128kbps(0xA0) |
    #                44100Hz(0x00) | stereo(0x00) | pad=0
    # Simplest well-formed: use standard silent-frame header for CBR 128 kbps.
    frame_header = b"\xff\xfb\x90\x00"   # sync + MPEG1 L3 128kbps 44100 stereo
    side_info    = b"\x00" * 32          # stereo side info (32 bytes)
    frame_data   = b"\x00" * (417 - 4 - 32)  # rest is zero-padded audio data
    silent_frame = frame_header + side_info + frame_data   # exactly 417 bytes

    num_frames = max(1, duration_ms // 26)  # ~26 ms per 128kbps frame at 44100
    return silent_frame * num_frames


# ---------------------------------------------------------------------------
# TTS TEXT SANITIZER
# ---------------------------------------------------------------------------

# Abbreviation / unit expansions applied before TTS synthesis
_TTS_REPLACEMENTS = [
    # Currency
    (re.compile(r"(\d+)\s*[Mm][\$€]"),      lambda m: f"{m.group(1)} milyon dolar"),
    (re.compile(r"\$(\d+)"),                 lambda m: f"{m.group(1)} dolar"),
    (re.compile(r"(\d+)\s*[Bb][\$€]"),      lambda m: f"{m.group(1)} milyar dolar"),
    # Percentages
    (re.compile(r"%\s*(\d+)"),               lambda m: f"yüzde {m.group(1)}"),
    (re.compile(r"(\d+)\s*%"),               lambda m: f"yüzde {m.group(1)}"),
    # Model names — spell out alphanumeric codes
    (re.compile(r"\bGPT-?(4o?|3\.5|5)\b", re.I),  lambda m: f"G P T {m.group(1).upper()}"),
    (re.compile(r"\bGPT\b"),                 lambda m: "G P T"),
    (re.compile(r"\bLLaMA\b", re.I),        lambda m: "Llama"),
    (re.compile(r"\bLLM\b"),                 lambda m: "dil modeli"),
    (re.compile(r"\bRAG\b"),                 lambda m: "bilgi artırımlı üretim"),
    (re.compile(r"\bRLHF\b"),                lambda m: "insan geri bildirimiyle pekiştirmeli öğrenme"),
    # Technical units
    (re.compile(r"(\d+)\s*[Kk]bps"),        lambda m: f"saniyede {m.group(1)} kilobit"),
    (re.compile(r"(\d+)\s*[Gg][Bb]"),       lambda m: f"{m.group(1)} gigabayt"),
    (re.compile(r"(\d+)\s*[Tt][Bb]"),       lambda m: f"{m.group(1)} terabayt"),
    # Dashes/ellipsis → natural pauses (comma works well for TTS)
    (re.compile(r"\s*—\s*"),                 lambda m: ", "),
    (re.compile(r"\.{3}"),                   lambda m: ", "),
    # Remove URLs
    (re.compile(r"https?://\S+"),            lambda m: ""),
    (re.compile(r"www\.\S+"),               lambda m: ""),
    # Remove emojis and special unicode symbols
    (re.compile(
        "["
        "\U0001F600-\U0001F64F"   # emoticons
        "\U0001F300-\U0001F5FF"   # symbols & pictographs
        "\U0001F680-\U0001F6FF"   # transport & map
        "\U0001F1E0-\U0001F1FF"   # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    ), lambda m: " "),
    # Remove content inside brackets/parentheses
    (re.compile(r"\[.*?\]"),                 lambda m: ""),
    (re.compile(r"\(.*?\)"),                 lambda m: ""),
    # Normalize whitespace
    (re.compile(r"[ \t]{2,}"),              lambda m: " "),
]


def _sanitize_for_tts(text: str) -> str:
    """Cleans text for neural TTS synthesis.

    Removes/replaces content that causes audio artefacts or unnatural
    pronunciation: emojis, URLs, bracket annotations, unit abbreviations,
    model name shorthand, ellipses, em-dashes.
    """
    for pattern, replacement in _TTS_REPLACEMENTS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text.strip()


def _choose_pause(idx: int, total: int, speaker_a: str, speaker_b: str) -> int:
    """Returns an appropriate inter-turn silence duration in ms.

    Short pauses for quick back-and-forth (same-length turns),
    longer pauses for news segment boundaries (assumed when turn text
    is significantly longer than previous turn — topic wrap-up).
    """
    if idx == 0 or idx >= total - 1:
        return _PAUSE_NORMAL_MS
    if speaker_a == speaker_b:
        return _PAUSE_LONG_MS   # same speaker twice → unusual, treat as segment break
    return _PAUSE_NORMAL_MS


# ---------------------------------------------------------------------------
# AUDIO GENERATOR
# ---------------------------------------------------------------------------

class AudioGenerator:
    """High-performance Turkish Neural TTS Audio Generator.

    Supports:
    - Edge-TTS (Microsoft, free): 2-host dialogue & monologue
    - Google Gemini TTS: 2-host dialogue with Edge-TTS fallback
    - Intro/Outro jingle stitching
    """

    def __init__(self, default_voice: str = DEFAULT_EDGE_VOICE):
        self.default_voice = default_voice

    # ------------------------------------------------------------------ helpers

    def _build_audio_metadata(self, output_path: str, duration_seconds: int) -> Dict[str, Any]:
        """Constructs a standardized audio metadata response dictionary."""
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        return {
            "file_path": output_path,
            "file_size": file_size,
            "duration_seconds": duration_seconds,
            "duration_formatted": f"{minutes}m {seconds:02d}s",
        }

    def _parse_dialogue_turns(self, script_text: str) -> List[Tuple[str, str]]:
        """Parses script lines into clean (speaker_name, sanitized_text) pairs."""
        turns: List[Tuple[str, str]] = []
        speaker_regex = re.compile(
            r"^(Kaan|Ece|Ahmet|Emel|Alex|Sarah|Sunucu 1|Sunucu 2|Sunucu):\s*(.*)",
            re.IGNORECASE,
        )

        for line in script_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            match = speaker_regex.match(line_str)
            if match:
                speaker_raw = match.group(1).title()
                if speaker_raw in ("Sunucu 1", "Alex", "Sunucu", "Ahmet"):
                    speaker = "Kaan"
                elif speaker_raw in ("Sunucu 2", "Sarah", "Emel"):
                    speaker = "Ece"
                else:
                    speaker = speaker_raw
                text = _sanitize_for_tts(match.group(2).strip())
                if text:
                    turns.append((speaker, text))
            else:
                # Continuation line — append to previous turn
                if turns:
                    prev_speaker, prev_text = turns[-1]
                    turns[-1] = (prev_speaker, f"{prev_text} {_sanitize_for_tts(line_str)}")
                else:
                    turns.append(("Kaan", _sanitize_for_tts(line_str)))

        return turns

    # ---------------------------------------------------------------- intro/outro

    def attach_intro_outro(
        self,
        body_mp3_path: str,
        intro_path: str = "assets/audio/intro.mp3",
        outro_path: str = "assets/audio/outro.mp3",
    ) -> str:
        """Stitches intro and outro jingles to the synthesized episode body."""
        if not (os.path.exists(intro_path) and os.path.exists(outro_path)):
            return body_mp3_path

        try:
            import miniaudio
            import lameenc

            intro_dec = miniaudio.decode_file(intro_path)
            body_dec  = miniaudio.decode_file(body_mp3_path)
            outro_dec = miniaudio.decode_file(outro_path)

            pause_samples = int(44100 * 2 * 0.5)
            pause_bytes   = b"\x00" * (pause_samples * 2)

            all_pcm = (
                intro_dec.samples.tobytes()
                + pause_bytes
                + body_dec.samples.tobytes()
                + pause_bytes
                + outro_dec.samples.tobytes()
            )

            encoder = lameenc.Encoder()
            encoder.set_bit_rate(128)
            encoder.set_in_sample_rate(44100)
            encoder.set_channels(2)
            encoder.set_quality(2)
            final_mp3 = encoder.encode(all_pcm) + encoder.flush()

            with open(body_mp3_path, "wb") as f:
                f.write(final_mp3)
            print(f"Intro ve Outro basariyla eklendi: {body_mp3_path}")
        except Exception as e:
            print(f"Intro/Outro ekleme uyarisi ({e}), orijinal ses korunuyor.")

        return body_mp3_path

    # ---------------------------------------------------------------- Edge-TTS

    async def build_audio_monologue_edge(self, script_text: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator with natural sentence pacing."""
        import edge_tts

        paragraphs = [p.strip() for p in script_text.strip().split("\n\n") if p.strip()]
        base_dir = os.path.dirname(output_mp3) if os.path.dirname(output_mp3) else "."
        os.makedirs(base_dir, exist_ok=True)

        semaphore = asyncio.Semaphore(_EDGE_TTS_SEMAPHORE_LIMIT)

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks        = []
            sentence_map = []
            global_idx   = 0

            for para in paragraphs:
                clean_para = _sanitize_for_tts(para)
                sentences  = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_para) if s.strip()]
                for s_idx, sentence in enumerate(sentences):
                    if len(sentence) < 2:
                        continue
                    is_last = s_idx == len(sentences) - 1
                    sentence_map.append((global_idx, is_last))
                    t_path = os.path.join(temp_dir, f"mono_{global_idx:04d}.mp3")

                    async def _synth_sentence(t=sentence, p=t_path):
                        async with semaphore:
                            try:
                                comm = edge_tts.Communicate(t, self.default_voice, rate="+0%", pitch="+0Hz")
                                await comm.save(p)
                                return p
                            except Exception as ex:
                                print(f"TTS sentence warning: {ex}")
                                return ""

                    tasks.append(_synth_sentence())
                    global_idx += 1

            if not tasks:
                raise ValueError("Script text contains no valid sentences for audio synthesis.")

            temp_files  = await asyncio.gather(*tasks)
            short_pause = _make_silent_mp3(_PAUSE_NORMAL_MS)
            long_pause  = _make_silent_mp3(_PAUSE_LONG_MS * 2)

            with open(output_mp3, "wb") as outfile:
                for idx, fname in enumerate(temp_files):
                    if fname and os.path.exists(fname):
                        with open(fname, "rb") as infile:
                            outfile.write(infile.read())
                        is_para_end = sentence_map[idx][1] if idx < len(sentence_map) else False
                        outfile.write(long_pause if is_para_end else short_pause)

        return output_mp3

    async def build_audio_dialogue_edge(self, dialogue_script: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator for 2-host dialogue (Ahmet & Emel).

        Changes vs previous version:
        - Applies _sanitize_for_tts() before synthesis
        - Uses asyncio.Semaphore to cap concurrent Microsoft TTS requests
        - Dynamic pause duration based on turn position
        """
        import edge_tts

        print("Turkce 2-Sunuculu Edge-TTS Sentezleniyor (Kaan & Ece)...")
        turns    = self._parse_dialogue_turns(dialogue_script)
        base_dir = os.path.dirname(output_mp3) if os.path.dirname(output_mp3) else "."
        os.makedirs(base_dir, exist_ok=True)

        semaphore = asyncio.Semaphore(_EDGE_TTS_SEMAPHORE_LIMIT)

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks     = []
            speakers  = []

            for idx, (speaker, text) in enumerate(turns):
                if not text:
                    continue
                voice     = EDGE_VOICE_MAP.get(speaker, "tr-TR-AhmetNeural")
                temp_file = os.path.join(temp_dir, f"edge_turn_{idx:04d}.mp3")
                speakers.append(speaker)

                async def _synth(v=voice, t=text, f=temp_file):
                    async with semaphore:
                        try:
                            comm = edge_tts.Communicate(t, v, rate="+1%")
                            await comm.save(f)
                            return f
                        except Exception as ex:
                            print(f"Edge-TTS turn warning ({f}): {ex}")
                            return ""

                tasks.append(_synth())

            temp_files = await asyncio.gather(*tasks)
            total      = len(temp_files)

            with open(output_mp3, "wb") as outfile:
                for i, fname in enumerate(temp_files):
                    if fname and os.path.exists(fname):
                        with open(fname, "rb") as infile:
                            outfile.write(infile.read())
                        sp_a = speakers[i] if i < len(speakers) else ""
                        sp_b = speakers[i + 1] if i + 1 < len(speakers) else ""
                        pause_ms = _choose_pause(i, total, sp_a, sp_b)
                        outfile.write(_make_silent_mp3(pause_ms))

        return output_mp3

    # ---------------------------------------------------------------- Gemini TTS

    def build_audio_dialogue_gemini(self, dialogue_script: str, output_mp3: str) -> str:
        """Turkish Gemini 2.5 Flash TTS audio generator for 2-host dialogue (Ahmet & Emel).

        Key features:
        - Strict 10 Requests-Per-Minute (10 RPM) rate limiter with rolling 60s window
        - Minimum 6.2s spacing between requests to stay safely below API rate limits
        - Exponential backoff retry on HTTP 429 / ResourceExhausted errors
        - Automatic sample-rate detection from Gemini inline audio mime_type
        - Fallback gracefully to Edge-TTS only on persistent errors
        """
        from google import genai
        from google.genai import types
        import lameenc
        import edge_tts

        gemini_api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GEMINI_FREE_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not gemini_api_key or gemini_api_key.startswith("your_"):
            print("⚠️ GEMINI API key bulunamadı, Edge-TTS motoruna geçiliyor...")
            return asyncio.run(self.build_audio_dialogue_edge(dialogue_script, output_mp3))

        print("🎙️ Türkçe 2-Sunuculu Google Gemini 2.5 Flash TTS Sentezleniyor (Kaan & Ece - Puck & Aoede)...")
        print("🛡️ Hız Sınırı Devrede: Dakikada en fazla 10 istek (10 RPM) koruması aktif.")
        client = genai.Client(api_key=gemini_api_key)
        turns = self._parse_dialogue_turns(dialogue_script)

        # Dakikada 10 istek sınırını kesin garanti eden rate-limiter
        rate_limiter = GeminiRateLimiter(max_rpm=10, min_interval_sec=6.2)

        turn_audio_buffers: List[bytes] = []
        working_model = None
        consecutive_failures = 0

        for idx, (speaker, raw_text) in enumerate(turns):
            if consecutive_failures >= 3:
                print("⚠️ Gemini TTS'te üst üste 3 hata oluştu. Kalan diyalog turları Edge-TTS ile tamamlanıyor...")
                remaining_script = "\n\n".join([f"{s}: {t}" for s, t in turns[idx:]])
                remaining_temp = os.path.join(tempfile.gettempdir(), f"edge_remaining_{idx}.mp3")
                asyncio.run(self.build_audio_dialogue_edge(remaining_script, remaining_temp))
                if os.path.exists(remaining_temp):
                    with open(remaining_temp, "rb") as rf:
                        turn_audio_buffers.append(rf.read())
                    try:
                        os.remove(remaining_temp)
                    except Exception:
                        pass
                break

            text = _sanitize_for_tts(raw_text)
            if not text:
                continue

            voice_name = GEMINI_VOICE_MAP.get(speaker, "Puck" if speaker in ("Kaan", "Ahmet") else "Aoede")
            prompt = (
                "Lütfen bu podcast diyaloğunu son derece doğal, canlı, akıcı ve samimi bir Türkçe ile seslendir, "
                f"konuşma hızında ve bir radyo sunucusu tonunda: {text}"
            )

            raw_pcm = None
            sample_rate = 24000
            candidate_models = [working_model] if working_model else list(GEMINI_TTS_MODELS)

            for model_name in candidate_models:
                # 429 / Kota hatası durumunda 3 denemeye kadar exponential backoff
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        rate_limiter.wait_if_needed()
                        print(f"  [{idx+1}/{len(turns)}] {speaker} ({voice_name}) -> {model_name}...")

                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_modalities=["AUDIO"],
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice_name
                                        )
                                    )
                                ),
                            ),
                        )

                        if response.candidates and response.candidates[0].content:
                            for part in response.candidates[0].content.parts:
                                if part.inline_data:
                                    raw_data = part.inline_data.data
                                    mime_type = part.inline_data.mime_type or ""
                                    if isinstance(raw_data, str):
                                        raw_data = base64.b64decode(raw_data)
                                    raw_pcm = raw_data

                                    rate_match = re.search(r"rate=(\d+)", mime_type)
                                    if rate_match:
                                        sample_rate = int(rate_match.group(1))
                                    break

                        if raw_pcm:
                            working_model = model_name
                            break

                    except Exception as api_err:
                        err_str = str(api_err).lower()
                        is_quota = any(k in err_str for k in ("429", "resource_exhausted", "quota", "rate"))
                        if is_quota and attempt < max_retries - 1:
                            backoff = 22.0 * (attempt + 1)
                            print(f"  ⏳ [Gemini 429 Kota] Hız sınırı koruması: {backoff:.0f}s beklenip yeniden deneniyor (deneme {attempt+1}/{max_retries})...")
                            time.sleep(backoff)
                            continue
                        else:
                            # Kota dışı hata veya denemeler tükendi, diğer modele geç
                            break

                if raw_pcm:
                    break

            try:
                if raw_pcm:
                    encoder = lameenc.Encoder()
                    encoder.set_bit_rate(128)
                    encoder.set_in_sample_rate(sample_rate)
                    encoder.set_channels(1)
                    encoder.set_quality(2)
                    mp3_buf = encoder.encode(raw_pcm) + encoder.flush()
                    turn_audio_buffers.append(mp3_buf)
                    consecutive_failures = 0
                else:
                    raise ValueError("Gemini modellerinden ses verisi alınamadı")
            except Exception as e:
                consecutive_failures += 1
                print(f"⚠️ Gemini TTS tur {idx+1} uyarısı ({e}), bu tur Edge-TTS ile tamamlanıyor...")
                voice_edge = EDGE_VOICE_MAP.get(speaker, "tr-TR-AhmetNeural" if speaker in ("Kaan", "Ahmet") else "tr-TR-EmelNeural")
                edge_file = os.path.join(tempfile.gettempdir(), f"gemini_fallback_{idx}.mp3")
                asyncio.run(
                    edge_tts.Communicate(text, voice_edge, rate="+1%").save(edge_file)
                )
                if os.path.exists(edge_file):
                    with open(edge_file, "rb") as f:
                        turn_audio_buffers.append(f.read())
                    try:
                        os.remove(edge_file)
                    except Exception:
                        pass

        if not turn_audio_buffers:
            raise ValueError("Hiçbir ses sırası sentezlenemedi.")

        base_dir = os.path.dirname(output_mp3) if os.path.dirname(output_mp3) else "."
        os.makedirs(base_dir, exist_ok=True)

        total = len(turn_audio_buffers)
        with open(output_mp3, "wb") as f:
            for i, buf in enumerate(turn_audio_buffers):
                f.write(buf)
                pause_ms = _PAUSE_NORMAL_MS if i < total - 1 else 0
                if pause_ms:
                    f.write(_make_silent_mp3(pause_ms))

        return output_mp3

    # ---------------------------------------------------------------- duration

    def _calculate_duration(self, output_path: str) -> int:
        """Calculates exact duration for the podcast MP3 using miniaudio, with fallback."""
        if not os.path.exists(output_path):
            return 0

        try:
            import miniaudio
            dec      = miniaudio.decode_file(output_path)
            duration = int(len(dec.samples) / (dec.sample_rate * dec.nchannels))
            if duration > 0:
                return duration
        except Exception:
            pass

        file_size_bytes = os.path.getsize(output_path)
        try:
            with open(output_path, "rb") as f:
                header_bytes = f.read(4096)
            for i in range(len(header_bytes) - 4):
                if header_bytes[i] == 0xFF and (header_bytes[i + 1] & 0xE0) == 0xE0:
                    ver          = (header_bytes[i + 1] >> 3) & 3
                    bitrate_idx  = (header_bytes[i + 2] >> 4) & 15
                    br_m2_l3     = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
                    br_m1_l3     = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    kbps         = br_m1_l3[bitrate_idx] if ver == 3 else br_m2_l3[bitrate_idx]
                    if kbps > 0:
                        bytes_per_sec = (kbps * 1000) / 8
                        return max(30, int(file_size_bytes / bytes_per_sec))
        except Exception:
            pass

        return max(30, int(file_size_bytes / 16000))

    # ---------------------------------------------------------------- public API

    def dialogue_to_audio(
        self,
        dialogue_script: str,
        output_path: str,
        engine: str = "edge",
        with_jingle: bool = True,
    ) -> Dict[str, Any]:
        """Synthesizes 2-host Turkish podcast using selected TTS engine and attaches jingles."""
        selected_engine = (engine or os.getenv("TTS_ENGINE", "edge")).lower()

        if selected_engine == "gemini":
            try:
                self.build_audio_dialogue_gemini(dialogue_script, output_path)
            except Exception as e:
                print(f"Gemini TTS hatasi ({e}), Edge-TTS motoruna donuluyor...")
                asyncio.run(self.build_audio_dialogue_edge(dialogue_script, output_path))
        else:
            asyncio.run(self.build_audio_dialogue_edge(dialogue_script, output_path))

        if with_jingle:
            self.attach_intro_outro(output_path)

        duration_seconds = self._calculate_duration(output_path)
        meta = self._build_audio_metadata(output_path, duration_seconds)
        print(f"Turkce Podcast MP3 olusturuldu [{selected_engine.upper()}]: {output_path} ({meta['duration_formatted']})")
        return meta

    def text_to_audio(
        self,
        script_text: str,
        output_path: str,
        with_jingle: bool = True,
    ) -> Dict[str, Any]:
        """Synthesizes Turkish monologue podcast to MP3."""
        asyncio.run(self.build_audio_monologue_edge(script_text, output_path))

        if with_jingle:
            self.attach_intro_outro(output_path)

        duration_seconds = self._calculate_duration(output_path)
        meta = self._build_audio_metadata(output_path, duration_seconds)
        print(f"Turkce Monolog MP3 olusturuldu: {output_path} ({meta['duration_formatted']})")
        return meta
