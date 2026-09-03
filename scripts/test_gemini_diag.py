import os
import sys
from google import genai
from google.genai import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

api_key = os.getenv("GEMINI_FREE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_FREE_API_KEY veya GEMINI_API_KEY bulunamadı!")
    sys.exit(1)

print("🔑 Gemini API Anahtarı mevcut.")
client = genai.Client(api_key=api_key)

print("\n🔍 Hesapta kullanılabilir Gemini modelleri taranıyor:")
try:
    for m in client.models.list():
        name = getattr(m, 'name', str(m))
        if any(k in name.lower() for k in ['flash', 'tts', 'audio', '2.5', '3']):
            print("  •", name)
except Exception as e:
    print("Modeller listelenirken hata:", e)

# Test speech generation with candidate models
candidate_models = [
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash-exp"
]

test_text = "Merhaba, Migros OneCast AI yapay zeka podcastine hoş geldiniz."
print(f"\n🎙️ Test Cümlesi Sentezleniyor: '{test_text}'")

success = False
for model_name in candidate_models:
    print(f"\nTesting model: {model_name} ...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=test_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Puck"
                        )
                    )
                )
            )
        )
        audio_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                audio_data = part.inline_data.data
                break
        if audio_data:
            print(f"🎉 BAŞARILI! Model {model_name} ses verisi üretti! Boyut: {len(audio_data)} byte")
            success = True
            with open("test_gemini_sample.mp3", "wb") as f:
                # If PCM, we will encode it; for now write raw
                if isinstance(audio_data, str):
                    import base64
                    audio_data = base64.b64decode(audio_data)
                import lameenc
                encoder = lameenc.Encoder()
                encoder.set_bit_rate(128)
                encoder.set_in_sample_rate(24000)
                encoder.set_channels(1)
                encoder.set_quality(2)
                mp3 = encoder.encode(audio_data) + encoder.flush()
                f.write(mp3)
            print("💾 Örnek ses 'test_gemini_sample.mp3' olarak kaydedildi.")
            break
        else:
            print(f"⚠️ Model {model_name} yanıt verdi ancak ses verisi içermiyor.")
    except Exception as ex:
        print(f"❌ {model_name} hatası: {ex}")

if not success:
    print("\nℹ️ Gemini modelleri ücretsiz katmanda doğrudan AUDIO modalitesini desteklemiyorsa Edge-TTS en stabil çözümdür.")
