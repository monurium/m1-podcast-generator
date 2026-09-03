import os
import sys
import re
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
    "Ahmet": "tr-TR-AhmetNeural",
    "Emel": "tr-TR-EmelNeural",
    "Alex": "tr-TR-AhmetNeural",
    "Sarah": "tr-TR-EmelNeural",
    "Sunucu": "tr-TR-AhmetNeural"
}

def generate_silent_mp3_bytes(duration_ms: int = 500) -> bytes:
    """Generates standard silent MP3 frame buffer for turn pacing."""
    num_frames = max(1, int(duration_ms / 100))
    silent_frame = b'\xff\xfb\x90\xc4' + b'\x00' * 413
    return silent_frame * num_frames

class AudioGenerator:
    """High-performance Turkish Neural TTS Audio Generator using Microsoft Edge-TTS."""

    def __init__(self, default_voice: str = DEFAULT_EDGE_VOICE):
        self.default_voice = default_voice

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
                if speaker_raw in ["Sunucu 1", "Alex", "Sunucu"]:
                    speaker = "Ahmet"
                elif speaker_raw in ["Sunucu 2", "Sarah"]:
                    speaker = "Emel"
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

    async def build_audio_monologue_edge(self, script_text: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator with natural sentence pacing."""
        import edge_tts
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
                                comm = edge_tts.Communicate(t, self.default_voice, rate="+0%", pitch="+0Hz")
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

        return output_mp3

    async def build_audio_dialogue_edge(self, dialogue_script: str, output_mp3: str) -> str:
        """Turkish Edge-TTS audio generator for 2-host dialogue (Ahmet & Emel)."""
        import edge_tts
        print("🎙️ Türkçe 2-Sunuculu Diyalog Sentezleniyor (Ahmet & Emel)...")
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

        return output_mp3

    def _calculate_duration(self, output_path: str) -> int:
        """Calculates accurate duration for the podcast MP3 based on header bitrate."""
        if not os.path.exists(output_path):
            return 0
        file_size_bytes = os.path.getsize(output_path)
        try:
            with open(output_path, 'rb') as f:
                header_bytes = f.read(4096)
            for i in range(len(header_bytes) - 4):
                if header_bytes[i] == 0xFF and (header_bytes[i+1] & 0xE0) == 0xE0:
                    ver = (header_bytes[i+1] >> 3) & 3
                    bitrate_idx = (header_bytes[i+2] >> 4) & 15
                    bitrates_m2_l3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
                    bitrates_m1_l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    kbps = bitrates_m1_l3[bitrate_idx] if ver == 3 else bitrates_m2_l3[bitrate_idx]
                    if kbps > 0:
                        bytes_per_sec = (kbps * 1000) / 8
                        return max(30, int(file_size_bytes / bytes_per_sec))
        except Exception:
            pass
        # Default fallback for Edge-TTS (48 kbps = 6,000 bytes/sec)
        return max(30, int(file_size_bytes / 6000))

    def dialogue_to_audio(self, dialogue_script: str, output_path: str) -> Dict[str, Any]:
        """Synthesizes 2-host Turkish podcast conversation."""
        asyncio.run(self.build_audio_dialogue_edge(dialogue_script, output_path))
        duration_seconds = self._calculate_duration(output_path)
        print(f"🎉 Türkçe Podcast MP3 oluşturuldu: {output_path} ({duration_seconds // 60}m {duration_seconds % 60}s)")
        return self._build_audio_metadata(output_path, duration_seconds)

    def text_to_audio(self, script_text: str, output_path: str) -> Dict[str, Any]:
        """Synthesizes Turkish monologue podcast to MP3."""
        asyncio.run(self.build_audio_monologue_edge(script_text, output_path))
        duration_seconds = self._calculate_duration(output_path)
        print(f"🎉 Türkçe Monolog MP3 oluşturuldu: {output_path} ({duration_seconds // 60}m {duration_seconds % 60}s)")
        return self._build_audio_metadata(output_path, duration_seconds)
