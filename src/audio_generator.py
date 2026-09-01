import os
import sys
import re
import asyncio
import time
import tempfile
from typing import Dict, Any, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_EDGE_VOICE = "tr-TR-AhmetNeural"
GEMINI_TTS_MODELS = ("gemini-2.5-flash-preview-tts", "gemini-2.5-flash-native-audio-latest", "gemini-2.5-flash")
GEMINI_VOICE_MAP = {"Ahmet": "Puck", "Emel": "Aoede", "Alex": "Puck", "Sarah": "Aoede"}
EDGE_VOICE_MAP = {
    "Ahmet": "tr-TR-AhmetNeural",
    "Emel": "tr-TR-EmelNeural",
    "Alex": "tr-TR-AhmetNeural",
    "Sarah": "tr-TR-EmelNeural",
    "Sunucu": "tr-TR-AhmetNeural"
}
PACING_SECONDS_PER_REQUEST = 6.5

def raw_pcm_to_mp3_bytes(pcm_bytes: bytes, sample_rate: int = 24000, num_channels: int = 1, bitrate: int = 128) -> bytes:
    """Encodes raw 24kHz 16-bit PCM audio bytes from Google AI Studio into standard compressed MP3 format using lameenc."""
    import lameenc
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(num_channels)
    encoder.set_quality(2)
    return encoder.encode(pcm_bytes) + encoder.flush()

def generate_silent_pcm_bytes(duration_ms: int = 400, sample_rate: int = 24000) -> bytes:
    """Generates standard 16-bit mono zero-PCM silence buffer."""
    num_bytes = int(sample_rate * 2 * (duration_ms / 1000.0))
    return b'\x00' * num_bytes

def generate_silent_mp3_bytes(duration_ms: int = 500) -> bytes:
    """Generates standard silent MP3 frame buffer for Edge-TTS fallback."""
    num_frames = max(1, int(duration_ms / 100))
    silent_frame = b'\xff\xfb\x90\xc4' + b'\x00' * 413
    return silent_frame * num_frames

class AudioGenerator:
    """Dual-Engine Audio Generator with full Turkish neural voice support (Ahmet: Male, Emel: Female)."""

    def __init__(self, edge_voice: str = DEFAULT_EDGE_VOICE):
        self.edge_voice = edge_voice
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_TTS_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def _build_audio_metadata(self, output_path: str, duration_seconds: int) -> Dict[str, Any]:
        """Constructs standardized audio metadata response dictionary."""
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return {
            "file_path": output_path,
            "file_size": file_size,
            "duration_seconds": duration_seconds,
            "duration_formatted": f"{duration_seconds // 3600:02d}:{(duration_seconds % 3600) // 60:02d}:{duration_seconds % 60:02d}"
        }

    def _parse_dialogue_turns(self, script_text: str) -> List[Tuple[str, str]]:
        """Parses script lines into clean (speaker_name, text) pairs."""
        turns: List[Tuple[str, str]] = []
        speaker_regex = re.compile(r'^(Ahmet|Emel|Alex|Sarah|Sunucu 1|Sunucu 2|Sunucu):\s*(.*)', re.IGNORECASE)

        for line in script_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            match = speaker_regex.match(line_str)
            if match:
                speaker_raw = match.group(1).title()
                # Normalize speaker names
                if speaker_raw in ["Sunucu 1", "Alex"]:
                    speaker = "Ahmet"
                elif speaker_raw in ["Sunucu 2", "Sarah"]:
                    speaker = "Emel"
                elif speaker_raw == "Sunucu":
                    speaker = "Ahmet"
                else:
                    speaker = speaker_raw

                text = match.group(2).strip()
                turns.append((speaker, text))
            else:
                if turns:
                    prev_speaker, prev_text = turns[-1]
                    turns[-1] = (prev_speaker, f"{prev_text} {line_str}")
                else:
                    turns.append(("Ahmet", line_str))
        return turns

    def _generate_gemini_audio(self, script_text: str, output_path: str) -> Tuple[bool, int]:
        """Synthesizes single-narrator audio using Google AI Studio with Turkish-tuned prompt."""
        if not self.gemini_api_key:
            return False, 0

        print("✨ Synthesizing Turkish audio via Google AI Studio...")
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)
            prompt = (
                "You are an enthusiastic, clear, lively, and articulate Turkish daily news podcast host. "
                "Narrate the following Turkish news script with clear vocal dynamics, natural pauses, "
                "and a warm, energetic presentation style:\n\n"
                f"{script_text}"
            )
            config = types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                    )
                )
            )

            for model_name in GEMINI_TTS_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                pcm_data = part.inline_data.data
                                audio_bytes = raw_pcm_to_mp3_bytes(pcm_data)
                                os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
                                with open(output_path, "wb") as f:
                                    f.write(audio_bytes)
                                
                                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                                duration_sec = max(30, int(len(pcm_data) / 48000))
                                print(f"🎉 Google AI Studio audio generated via '{model_name}': {output_path} ({file_size_mb:.2f} MB, {duration_sec // 60}m {duration_sec % 60}s)")
                                return True, duration_sec
                except Exception as model_err:
                    print(f"⚠️ Model '{model_name}' attempt failed: {model_err}")

            return False, 0
        except Exception as e:
            print(f"⚠️ Google AI Studio error ({e}).")
            return False, 0

    def _clean_speaker_turns(self, turns: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Merges consecutive lines by the SAME speaker and strips markdown."""
        if not turns:
            return []
        
        merged: List[Tuple[str, str]] = []
        for speaker, text in turns:
            clean = re.sub(r'\[.*?\]|\(.*?\)', '', text).strip()
            if not clean:
                continue
            if merged and merged[-1][0] == speaker:
                prev_spk, prev_txt = merged[-1]
                merged[-1] = (prev_spk, f"{prev_txt} {clean}")
            else:
                merged.append((speaker, clean))

        return merged

    async def build_audio_monologue_edge(self, script_text: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator with natural sentence pacing."""
        import edge_tts
        print(f"🎙️ Using Turkish Edge-TTS engine with voice '{self.edge_voice}'...")
        
        paragraphs = [p.strip() for p in script_text.strip().split("\n\n") if p.strip()]
        base_dir = os.path.dirname(output_mp3) if os.path.dirname(output_mp3) else "."
        os.makedirs(base_dir, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = []
            sentence_map = []
            global_idx = 0

            for para in paragraphs:
                clean_para = re.sub(r'\[.*?\]|\(.*?\)', '', para).strip()
                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_para) if s.strip()]
                for s_idx, sentence in enumerate(sentences):
                    if len(sentence) >= 2:
                        is_last = (s_idx == len(sentences) - 1)
                        sentence_map.append((global_idx, is_last))
                        t_path = os.path.join(temp_dir, f"mono_{global_idx:04d}.mp3")
                        
                        async def _synth_sentence(t=sentence, p=t_path):
                            try:
                                comm = edge_tts.Communicate(t, self.edge_voice, rate="+0%", pitch="+0Hz")
                                await comm.save(p)
                                return p
                            except Exception as ex:
                                print(f"Warning: TTS failed for sentence: {ex}")
                                return ""
                        
                        tasks.append(_synth_sentence())
                        global_idx += 1

            if not tasks:
                raise ValueError("Script text contains no valid sentences for audio synthesis.")

            temp_files = await asyncio.gather(*tasks)
            short_pause = generate_silent_mp3_bytes(550)
            long_pause = generate_silent_mp3_bytes(1100)

            with open(output_mp3, 'wb') as outfile:
                for idx, fname in enumerate(temp_files):
                    if fname and os.path.exists(fname):
                        with open(fname, 'rb') as infile:
                            outfile.write(infile.read())
                        is_para_end = sentence_map[idx][1] if idx < len(sentence_map) else False
                        outfile.write(long_pause if is_para_end else short_pause)

        print(f"🎉 Turkish Edge-TTS monologue audio generated successfully: {output_mp3}")
        return output_mp3

    async def build_audio_dialogue_edge(self, dialogue_script: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator for 2-host dialogue (Ahmet: tr-TR-AhmetNeural, Emel: tr-TR-EmelNeural)."""
        import edge_tts
        print("🎙️ Synthesizing 2-Host Turkish Dialogue via Edge-TTS (Ahmet: tr-TR-AhmetNeural & Emel: tr-TR-EmelNeural)...")
        turns = self._parse_dialogue_turns(dialogue_script)
        base_dir = os.path.dirname(output_mp3) if os.path.dirname(output_mp3) else "."
        os.makedirs(base_dir, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = []
            for idx, (speaker, text) in enumerate(turns):
                clean_text = re.sub(r'\[.*?\]|\(.*?\)', '', text).strip()
                if not clean_text:
                    continue
                voice = EDGE_VOICE_MAP.get(speaker, "tr-TR-AhmetNeural" if speaker == "Ahmet" else "tr-TR-EmelNeural")
                temp_file = os.path.join(temp_dir, f"edge_turn_{idx:04d}.mp3")

                async def _synth(v=voice, t=clean_text, f=temp_file):
                    try:
                        comm = edge_tts.Communicate(t, v, rate="+1%")
                        await comm.save(f)
                        return f
                    except Exception as ex:
                        print(f"Warning: failed edge synth turn {f}: {ex}")
                        return ""

                tasks.append(_synth())

            temp_files = await asyncio.gather(*tasks)
            pause_bytes = generate_silent_mp3_bytes(450)

            with open(output_mp3, 'wb') as outfile:
                for fname in temp_files:
                    if fname and os.path.exists(fname):
                        with open(fname, 'rb') as infile:
                            outfile.write(infile.read())
                        outfile.write(pause_bytes)

        print(f"🎉 2-Host Turkish Podcast MP3 generated: {output_mp3}")
        return output_mp3

    def _attach_intro_outro(self, output_path: str) -> int:
        """Calculates accurate duration for the podcast MP3."""
        if not os.path.exists(output_path):
            return 0
        file_size_bytes = os.path.getsize(output_path)
        exact_duration_sec = max(30, int(file_size_bytes / 16000))
        return exact_duration_sec

    def dialogue_to_audio(self, dialogue_script: str, output_path: str) -> Dict[str, Any]:
        """Synthesizes 2-host Turkish podcast conversation."""
        asyncio.run(self.build_audio_dialogue_edge(dialogue_script, output_path))
        duration_seconds = self._attach_intro_outro(output_path)
        return self._build_audio_metadata(output_path, duration_seconds)

    def text_to_audio(self, script_text: str, output_path: str) -> Dict[str, Any]:
        """Synthesizes Turkish monologue podcast to MP3."""
        asyncio.run(self.build_audio_monologue_edge(script_text, output_path))
        duration_seconds = self._attach_intro_outro(output_path)
        return self._build_audio_metadata(output_path, duration_seconds)
