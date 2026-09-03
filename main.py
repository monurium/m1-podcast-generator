import os
import sys
import json
import argparse
import datetime
import uuid
import shutil
from dotenv import load_dotenv

from src.content_generator import ContentGenerator
from src.audio_generator import AudioGenerator
from src.publisher import Publisher
from src.rss_builder import RSSBuilder

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

def run_daily_podcast_pipeline(test_mode: bool = False, tts_engine: str = None):
    if not tts_engine:
        tts_engine = os.getenv("TTS_ENGINE", "gemini" if (os.getenv("GEMINI_FREE_API_KEY") or os.getenv("GEMINI_API_KEY")) else "edge")
    print("=" * 65)
    if test_mode:
        print(f"🧪 TEST / DRY-RUN MODU [{tts_engine.upper()}]: Yerel test dosyaları üretiliyor (Prod RSS etkilenmez)")
    else:
        print(f"🎙️ MIGROS ONECAST AI [{tts_engine.upper()}] - GÜNLÜK TÜRKÇE YAPAY ZEKA PODCAST BORU HATTI")
    print("=" * 65)

    # 1. Load Configurations
    config_path = os.path.join("config", "podcast_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_url = os.getenv("PODCAST_BASE_URL", config.get("link", "https://monurium.github.io/m1-podcast-generator"))
    output_dir = config.get("output_dir", "dist")

    # 2. Extract Recent Topics from Manifest for Duplicate Prevention
    manifest_path = "episodes_manifest.json"
    recent_topics = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                prev_manifest = json.load(f)
                for ep in prev_manifest[:3]:
                    if "news_items" in ep:
                        for it in ep["news_items"]:
                            recent_topics.append(it.get("headline", ""))
                    elif "todays_topics" in ep:
                        recent_topics.extend([t.strip() for t in ep["todays_topics"].split(",")])
        except Exception as e:
            print(f"Manifest okuma uyarısı: {e}")

    # 3. Content Generation
    print("\n[Adım 1/3] Güncel Teknoloji & Yapay Zeka RSS kaynakları taranıyor...")
    generator = ContentGenerator()
    news_context = generator.fetch_fresh_news(hours_limit=24, exclude_keywords=recent_topics)

    dialogue_script_data = generator.generate_dialogue_script(news_context, recent_topics=recent_topics)
    script_data = generator.generate_script(news_context)

    # Save scripts to output
    os.makedirs("output", exist_ok=True)
    dialogue_file_path = os.path.join("output", "dialogue_script.txt")
    with open(dialogue_file_path, "w", encoding="utf-8") as f:
        f.write(dialogue_script_data.get("script", ""))

    print(f"📄 Türkçe Podcast Metni Kaydedildi: {dialogue_file_path}")
    print(f"💡 Bölüm Başlığı: {dialogue_script_data.get('title')}")
    print(f"⚡ Çarpıcı Haber Sayısı: {len(dialogue_script_data.get('news_items', []))}")

    # 4. Audio Synthesis (Ahmet: Male, Emel: Female)
    audio_gen = AudioGenerator()
    today_str = datetime.date.today().strftime('%Y%m%d')
    pub_date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    if test_mode:
        print(f"\n[Adım 2/3] 🧪 Türkçe 2-Sunuculu (Ahmet & Emel) Test Sesi Sentezleniyor [{tts_engine.upper()}]...")
        test_audio_path = os.path.join("output", "test_dialogue_podcast.mp3")
        dialogue_audio_meta = audio_gen.dialogue_to_audio(dialogue_script_data["script"], test_audio_path, engine=tts_engine)

        print("\n[Adım 3/3] 🧪 Test RSS Beslemesi ve Manifest ./output/ içinde oluşturuluyor...")
        test_publisher = Publisher(output_dir="output")
        test_episode_meta = {
            "id": "ep_test_onecast_podcast",
            "title": "[TEST] " + dialogue_script_data["title"],
            "summary": dialogue_script_data["summary"],
            "todays_topics": dialogue_script_data.get("todays_topics", ""),
            "news_items": dialogue_script_data.get("news_items", []),
            "script": dialogue_script_data["script"],
            "pub_date": pub_date,
            "file_size": dialogue_audio_meta["file_size"],
            "duration_formatted": dialogue_audio_meta["duration_formatted"]
        }
        test_episodes = test_publisher.add_episode(test_episode_meta, test_audio_path, base_url)

        test_rss_builder = RSSBuilder(config=config)
        test_xml_path = os.path.join("output", "test_podcast.xml")
        test_rss_builder.build_feed(test_episodes, test_xml_path)

        print("\n" + "=" * 65)
        print(f"🎉 TEST BAŞARIYLA TAMAMLANDI [{tts_engine.upper()}]!")
        print(f"📄 Metin Dosyası: {dialogue_file_path}")
        print(f"🎧 Ses Dosyası: {test_audio_path}")
        print(f"📡 Test RSS XML: {test_xml_path}")
        print("=" * 65)
        return

    # --- Production Publishing Mode ---
    publisher = Publisher(output_dir=output_dir)

    dialogue_episode_id = f"ep_{today_str}_m1_{uuid.uuid4().hex[:6]}"
    temp_dialogue_path = os.path.join("output", "temp", f"{dialogue_episode_id}.mp3")
    print(f"\n[Adım 2/3] Türkçe 2-Sunuculu (Ahmet & Emel) MP3 Podcast Sentezleniyor [{tts_engine.upper()}]...")

    try:
        dialogue_audio_meta = audio_gen.dialogue_to_audio(dialogue_script_data["script"], temp_dialogue_path, engine=tts_engine)
        episode_dict = {
            "id": dialogue_episode_id,
            "title": dialogue_script_data["title"],
            "summary": dialogue_script_data["summary"],
            "todays_topics": dialogue_script_data.get("todays_topics", dialogue_script_data["summary"]),
            "news_items": dialogue_script_data.get("news_items", []),
            "script": dialogue_script_data["script"],
            "pub_date": pub_date,
            "file_size": dialogue_audio_meta["file_size"],
            "duration_formatted": dialogue_audio_meta["duration_formatted"],
            "duration_seconds": dialogue_audio_meta.get("duration_seconds", 0)
        }
        all_episodes = publisher.add_episode(episode_dict, temp_dialogue_path, base_url)
    except Exception as dialogue_err:
        print(f"⚠️ Diyalog podcast sentezleme hatası ({dialogue_err}). Monolog yedeğe geçiliyor...")
        mono_episode_id = f"ep_{today_str}_mono_{uuid.uuid4().hex[:6]}"
        temp_mono_path = os.path.join("output", "temp", f"{mono_episode_id}.mp3")
        mono_audio_meta = audio_gen.text_to_audio(script_data["script"], temp_mono_path)
        episode_dict = {
            "id": mono_episode_id,
            "title": script_data["title"],
            "summary": script_data["summary"],
            "todays_topics": script_data.get("todays_topics", script_data["summary"]),
            "news_items": script_data.get("news_items", []),
            "script": script_data["script"],
            "pub_date": pub_date,
            "file_size": mono_audio_meta["file_size"],
            "duration_formatted": mono_audio_meta["duration_formatted"],
            "duration_seconds": mono_audio_meta.get("duration_seconds", 0)
        }
        all_episodes = publisher.add_episode(episode_dict, temp_mono_path, base_url)

    # 5. RSS XML Feed Generation
    print("\n[Adım 3/3] RSS XML Beslemesi ve Web Dosyaları Güncelleniyor...")
    rss_builder = RSSBuilder(config=config)
    rss_dist_path = os.path.join(output_dir, config.get("feed_filename", "podcast.xml"))
    rss_root_path = config.get("feed_filename", "podcast.xml")
    
    rss_builder.build_feed(all_episodes, rss_dist_path)
    rss_builder.build_feed(all_episodes, rss_root_path)

    # Copy web landing page and cover artwork to dist
    if os.path.exists("index.html"):
        shutil.copy2("index.html", os.path.join(output_dir, "index.html"))
    if os.path.exists("cover.jpg"):
        shutil.copy2("cover.jpg", os.path.join(output_dir, "cover.jpg"))

    print("\n" + "=" * 65)
    print("🎉 BAŞARILI: Migros OneCast AI Podcast üretildi ve RSS beslemesi güncellendi!")
    print(f"📡 RSS Beslemesi: {base_url.rstrip('/')}/{config.get('feed_filename', 'podcast.xml')}")
    print(f"🎧 Web Oynatıcı: {base_url.rstrip('/')}/")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migros OneCast AI - Günlük Türkçe Yapay Zeka Podcasti ve RSS Beslemesi")
    parser.add_argument("--test", "--dry-run", action="store_true", help="Prod RSS/dist değiştirmeden yerel test modunda çalıştır")
    parser.add_argument("--tts", choices=["edge", "gemini"], default=None, help="TTS motoru (edge veya gemini)")
    args = parser.parse_args()

    run_daily_podcast_pipeline(test_mode=args.test, tts_engine=args.tts)
