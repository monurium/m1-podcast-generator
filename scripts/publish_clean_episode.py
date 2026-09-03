import json
import os
import sys
import datetime
import shutil

sys.path.insert(0, os.path.abspath("."))
from src.rss_builder import RSSBuilder

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 1. Read metadata from downloaded test manifest
test_manifest_path = "downloaded_artifacts/gemini-tts-test-output/output/episodes_manifest.json"
with open(test_manifest_path, "r", encoding="utf-8") as f:
    test_manifest = json.load(f)

test_ep = test_manifest[0]
raw_title = test_ep["title"].replace("[TEST] ", "").strip()
if not raw_title.startswith("Migros OneCast AI"):
    title = f"Migros OneCast AI - {raw_title}"
else:
    title = raw_title

summary = test_ep["summary"]
todays_topics = test_ep.get("todays_topics", "")
news_items = test_ep.get("news_items", [])
script = test_ep.get("script", "")

config_path = os.path.join("config", "podcast_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

base_url = os.getenv("PODCAST_BASE_URL", config.get("link", "https://monurium.github.io/m1-podcast-generator")).rstrip("/")
output_dir = config.get("output_dir", "dist")

# 2. Reset manifest: clear old episodes completely
new_ep_id = "ep_20260903_onecast_01"
combined_mp3 = "temp_test/combined.mp3"
file_size = os.path.getsize(combined_mp3)
pub_date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

new_episode = {
    "id": new_ep_id,
    "guid": new_ep_id,
    "title": title,
    "summary": summary,
    "todays_topics": todays_topics,
    "news_items": news_items,
    "script": script,
    "pub_date": pub_date,
    "file_size": file_size,
    "duration_formatted": "10m 39s",
    "duration_seconds": 639,
    "audio_url": f"{base_url}/episodes/{new_ep_id}.mp3"
}

# Clean old audio files in episodes and dist/episodes
for d in ["episodes", os.path.join(output_dir, "episodes")]:
    os.makedirs(d, exist_ok=True)
    for existing in os.listdir(d):
        if existing.endswith(".mp3"):
            try:
                os.remove(os.path.join(d, existing))
            except Exception as e:
                print(f"Warning removing {existing}: {e}")

# Copy combined MP3 to both locations
target_root_audio = os.path.join("episodes", f"{new_ep_id}.mp3")
target_dist_audio = os.path.join(output_dir, "episodes", f"{new_ep_id}.mp3")
shutil.copy2(combined_mp3, target_root_audio)
shutil.copy2(combined_mp3, target_dist_audio)

# Save cleaned manifest with ONLY this episode
manifest_list = [new_episode]
with open("episodes_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest_list, f, ensure_ascii=False, indent=2)

with open(os.path.join(output_dir, "episodes_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest_list, f, ensure_ascii=False, indent=2)

# 3. Build fresh RSS feeds
rss_builder = RSSBuilder(config=config)
rss_builder.build_feed(manifest_list, "podcast.xml")
rss_builder.build_feed(manifest_list, os.path.join(output_dir, "podcast.xml"))

# 4. Copy index.html and cover.jpg
if os.path.exists("index.html"):
    shutil.copy2("index.html", os.path.join(output_dir, "index.html"))
if os.path.exists("cover.jpg"):
    shutil.copy2("cover.jpg", os.path.join(output_dir, "cover.jpg"))

print("=" * 65)
print("🎉 MEVCUT RSS TEMİZLENDİ VE YENİ BÖLÜM YÜKLENDİ!")
print(f"📻 Başlık: {title}")
print(f"⏱️ Süre: 10m 39s (Intro + Ana Yayın + Outro)")
print(f"📁 Dosya: episodes/{new_ep_id}.mp3 ({file_size} bytes)")
print(f"📡 RSS Beslemesi: {base_url}/podcast.xml")
print(f"🌐 Web Oynatıcı: {base_url}/")
print("=" * 65)
