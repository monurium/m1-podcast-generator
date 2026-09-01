import os
import shutil
import json
import uuid
import datetime
import re
import argparse
import sys
from dotenv import load_dotenv

from src.content_generator import ContentGenerator
from src.audio_generator import AudioGenerator
from src.rss_builder import RSSBuilder
from src.publisher import Publisher
from src.slack_notifier import SlackNotifier

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

def run_daily_podcast_pipeline(test_mode: bool = False):
    print("=" * 65)
    if test_mode:
        print("🧪 TEST / DRY-RUN MODU: Yerel test dosyaları üretiliyor (Prod RSS etkilenmez)")
    else:
        print("🎙️ M1 GÜNLÜK TÜRKÇE PODCAST & RSS YAYINLAMA BORU HATTI")
    print("=" * 65)

    # 1. Load Configurations
    config_path = os.path.join("config", "podcast_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_url = os.getenv("PODCAST_BASE_URL", config.get("link", "https://monurium.github.io/m1-podcast-generator"))
    output_dir = config.get("output_dir", "dist")

    # 2. Extract Recent Topics from Manifest for Duplicate Prevention
    recent_manifest_path = "episodes_manifest.json"
    recent_topics = []
    last_episode_script = ""
    if os.path.exists(recent_manifest_path):
        try:
            with open(recent_manifest_path, "r", encoding="utf-8") as f:
                past_episodes = json.load(f)
                if past_episodes:
                    last_episode_script = past_episodes[0].get("script", "")
                    for ep in past_episodes[:5]:
                        t_summary = ep.get("todays_topics", "") or ep.get("summary", "")
                        if t_summary:
                            recent_topics.append(t_summary)
        except Exception as e:
            print(f"⚠️ Geçmiş bülten kayıtları yüklenirken not: {e}")

    # 3. Fetch Fresh Turkish & Global News
    print("\n[Adım 1/3] Güncel Teknoloji & Yapay Zeka RSS kaynakları taranıyor...")
    content_gen = ContentGenerator()
    
    exclude_keywords = []
    for topic in recent_topics:
        exclude_keywords.extend(re.findall(r'\b[A-ZÇĞİÖŞÜa-zçğıöşü]{4,}\b', topic))

    raw_news = content_gen.fetch_fresh_news(hours_limit=24, exclude_keywords=list(set(exclude_keywords)))
    if not raw_news:
        print("⚠️ 24 saatlik filtrede yeterli haber bulunamadı, 48 saatlik aralık taranıyor...")
        raw_news = content_gen.fetch_fresh_news(hours_limit=48)

    # Generate dialogue and monologue scripts
    dialogue_script_data = content_gen.generate_dialogue_script(raw_news, recent_topics=recent_topics)
    script_data = content_gen.generate_script(raw_news)

    # Save script texts locally
    os.makedirs("output", exist_ok=True)
    dialogue_file_path = os.path.join("output", "dialogue_script.txt")
    with open(dialogue_file_path, "w", encoding="utf-8") as f:
        f.write(dialogue_script_data["script"])
        
    print(f"📄 Türkçe Podcast Metni Kaydedildi: {dialogue_file_path}")
    print(f"💡 Bölüm Başlığı: {dialogue_script_data['title']}")
    print(f"⚡ Çarpıcı Haber Sayısı: {len(dialogue_script_data.get('news_items', []))}")

    # 4. Audio Synthesis (Ahmet: Male, Emel: Female)
    audio_gen = AudioGenerator()
    today_str = datetime.date.today().strftime('%Y%m%d')
    pub_date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    if test_mode:
        print("\n[Adım 2/3] 🧪 Türkçe 2-Sunuculu (Ahmet & Emel) Test Sesi Sentezleniyor...")
        test_audio_path = os.path.join("output", "test_dialogue_podcast.mp3")
        dialogue_audio_meta = audio_gen.dialogue_to_audio(dialogue_script_data["script"], test_audio_path)

        print("\n[Adım 3/3] 🧪 Test RSS Beslemesi ve Manifest ./output/ içinde oluşturuluyor...")
        test_publisher = Publisher(output_dir="output")
        test_episode_meta = {
            "id": "ep_test_m1_podcast",
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
        print("🎉 TEST BAŞARIYLA TAMAMLANDI!")
        print(f"📄 Metin Dosyası: {dialogue_file_path}")
        print(f"🎧 Ses Dosyası: {test_audio_path}")
        print(f"📡 Test RSS XML: {test_xml_path}")
        print("=" * 65)
        return

    # --- Production Publishing Mode ---
    publisher = Publisher(output_dir=output_dir)

    dialogue_episode_id = f"ep_{today_str}_m1_{uuid.uuid4().hex[:6]}"
    temp_dialogue_path = os.path.join("output", "temp", f"{dialogue_episode_id}.mp3")
    print("\n[Adım 2/3] Türkçe 2-Sunuculu (Ahmet & Emel) MP3 Podcast Sentezleniyor...")

    try:
        dialogue_audio_meta = audio_gen.dialogue_to_audio(dialogue_script_data["script"], temp_dialogue_path)
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

    # Optional: Slack Notification if configured
    if os.getenv("SLACK_WEBHOOK_URL") or (os.getenv("SLACK_BOT_TOKEN") and os.getenv("SLACK_CHANNEL_ID")):
        try:
            slack = SlackNotifier()
            latest_ep = all_episodes[0] if all_episodes else episode_dict
            slack.send_notification(latest_ep, base_url=base_url)
        except Exception as slack_err:
            print(f"ℹ️ Slack bildirimi atlandı: {slack_err}")

    print("\n" + "=" * 65)
    print("🎉 BAŞARILI: M1 Günlük Podcast üretildi ve RSS beslemesi güncellendi!")
    print(f"📡 RSS Beslemesi: {base_url.rstrip('/')}/{config.get('feed_filename', 'podcast.xml')}")
    print(f"🎧 Web Oynatıcı: {base_url.rstrip('/')}/")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M1 Günlük Türkçe Podcast ve RSS Beslemesi")
    parser.add_argument("--test", "--dry-run", action="store_true", help="Prod RSS/dist değiştirmeden yerel test modunda çalıştır")
    args = parser.parse_args()

    run_daily_podcast_pipeline(test_mode=args.test)
