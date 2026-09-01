import os
import shutil
import json
from typing import Dict, Any, List

MAX_MANIFEST_ITEMS = 100  # Keep latest 100 episodes in manifest to prevent bloat

class Publisher:
    """Manages episode storage, manifest persistence, deduplication, and web hosting directory output."""

    def __init__(self, output_dir: str = "dist"):
        self.output_dir = output_dir
        self.manifest_path = os.path.join(output_dir, "episodes_manifest.json")
        os.makedirs(self.output_dir, exist_ok=True)

    def load_manifest(self) -> List[Dict[str, Any]]:
        """Loads historical episode metadata manifest."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load manifest ({e}). Starting fresh.")
        return []

    def save_manifest(self, episodes: List[Dict[str, Any]]):
        """Saves updated episode metadata manifest to output_dir and root."""
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(episodes, f, indent=2, ensure_ascii=False)
        if self.output_dir != "output":
            with open("episodes_manifest.json", "w", encoding="utf-8") as f:
                json.dump(episodes, f, indent=2, ensure_ascii=False)

    def add_episode(self, episode_meta: Dict[str, Any], temp_audio_path: str, base_url: str) -> List[Dict[str, Any]]:
        """Copies audio to output folder, computes public URL, deduplicates, and updates episode registry."""
        episodes = self.load_manifest()

        # Filename based on GUID / slug
        filename = f"{episode_meta['id']}.mp3"
        dest_path = os.path.join(self.output_dir, "episodes", filename)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(temp_audio_path, dest_path)

        # Copy to root episodes folder so GitHub Pages root URL matches perfectly (production only)
        if self.output_dir != "output":
            root_episodes_path = os.path.join("episodes", filename)
            os.makedirs("episodes", exist_ok=True)
            shutil.copy2(temp_audio_path, root_episodes_path)

        # Build public HTTPS URL for Spotify & Apple Podcasts enclosure tag
        public_audio_url = f"{base_url.rstrip('/')}/episodes/{filename}"
        
        new_entry = {
            "guid": episode_meta["id"],
            "title": episode_meta["title"],
            "summary": episode_meta["summary"],
            "todays_topics": episode_meta.get("todays_topics", episode_meta["summary"]),
            "script": episode_meta["script"],
            "pub_date": episode_meta["pub_date"],
            "audio_url": public_audio_url,
            "file_size": episode_meta["file_size"],
            "duration_formatted": episode_meta["duration_formatted"],
            "duration_seconds": episode_meta.get("duration_seconds", 0),
            "bulletin_summary": episode_meta.get("bulletin_summary", episode_meta["summary"]),
            "news_items": episode_meta.get("news_items", []),
            "chapters": episode_meta.get("chapters", []),
            "vocabulary": episode_meta.get("vocabulary", []),
            "sentences": episode_meta.get("sentences", [])
        }

        # Deduplicate: Remove existing entry with same guid if re-run
        episodes = [ep for ep in episodes if ep.get("guid") != episode_meta["id"]]

        # Prepend latest episode to the list
        episodes.insert(0, new_entry)

        # Trim manifest history to MAX_MANIFEST_ITEMS
        if len(episodes) > MAX_MANIFEST_ITEMS:
            episodes = episodes[:MAX_MANIFEST_ITEMS]

        self.save_manifest(episodes)
        self.cleanup_orphan_audio(episodes)
        return episodes

    def cleanup_orphan_audio(self, episodes: List[Dict[str, Any]]):
        """Purges orphan .mp3 files from dist/episodes and episodes folders not listed in manifest."""
        active_filenames = {f"{ep['guid']}.mp3" for ep in episodes if "guid" in ep}
        if self.output_dir == "output":
            target_dirs = [os.path.join(self.output_dir, "episodes")]
        else:
            target_dirs = [os.path.join(self.output_dir, "episodes"), "episodes"]

        for target_dir in target_dirs:
            if not os.path.exists(target_dir):
                continue
            for item in os.listdir(target_dir):
                if item.endswith(".mp3") and item not in active_filenames:
                    file_path = os.path.join(target_dir, item)
                    try:
                        os.remove(file_path)
                        print(f"🧹 Cleaned up orphan audio file: {file_path}")
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to remove orphan audio file {file_path}: {e}")

