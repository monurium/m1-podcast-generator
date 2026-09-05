import sys
import os
sys.path.insert(0, os.path.abspath("."))
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import glob
from src.rss_builder import RSSBuilder

def clear_rss_and_episodes():
    print("🧹 RSS ve ses kayıtları temizleniyor...")
    
    # 1. Load config
    config_path = os.path.join("config", "podcast_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 2. Build clean empty RSS feeds
    builder = RSSBuilder(config=config)
    
    # Root podcast.xml
    builder.build_feed([], "podcast.xml")
    print("✅ Root podcast.xml temizlendi (0 bölüm)")

    # Dist podcast.xml
    os.makedirs("dist", exist_ok=True)
    builder.build_feed([], os.path.join("dist", "podcast.xml"))
    print("✅ dist/podcast.xml temizlendi (0 bölüm)")

    # 3. Clear manifests
    with open("episodes_manifest.json", "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print("✅ Root episodes_manifest.json sıfırlandı []")

    with open(os.path.join("dist", "episodes_manifest.json"), "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print("✅ dist/episodes_manifest.json sıfırlandı []")

    # 4. Remove all mp3 recordings in episodes and dist/episodes
    removed_count = 0
    for folder in ["episodes", os.path.join("dist", "episodes")]:
        os.makedirs(folder, exist_ok=True)
        # Create .gitkeep so empty directory remains in git
        gitkeep_path = os.path.join(folder, ".gitkeep")
        with open(gitkeep_path, "w", encoding="utf-8") as gf:
            gf.write("")

        for mp3_file in glob.glob(os.path.join(folder, "*.mp3")):
            try:
                os.remove(mp3_file)
                print(f"🗑️ Silindi: {mp3_file}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️ Dosya silinemedi ({mp3_file}): {e}")

    # 5. Clear temporary audio in output if any
    for mp3_file in glob.glob(os.path.join("output", "*.mp3")):
        try:
            os.remove(mp3_file)
            print(f"🗑️ Test kaydı silindi: {mp3_file}")
        except Exception:
            pass

    print(f"\n🎉 Temizlik tamamlandı! Toplam {removed_count} eski ses kaydı silindi.")

if __name__ == "__main__":
    clear_rss_and_episodes()
