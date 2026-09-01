import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from typing import Dict, Any, List

class RSSBuilder:
    """Generates and updates Apple Podcasts and Spotify compliant RSS 2.0 XML feeds with rich Turkish metadata."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def _build_rich_description(self, ep: Dict[str, Any]) -> str:
        """Constructs a structured HTML/text description containing striking headlines and summaries."""
        lines = []
        summary = ep.get("summary", "")
        if summary:
            lines.append(f"{summary}\n")

        news_items = ep.get("news_items", [])
        if news_items:
            lines.append("⚡ GÜNÜN ÇARPICI HABERLERİ:")
            for idx, item in enumerate(news_items, 1):
                headline = item.get("headline") or item.get("title", f"Haber {idx}")
                item_summary = item.get("summary", "")
                key_points = item.get("key_points", [])
                
                lines.append(f"\n{idx}. {headline}")
                if item_summary:
                    lines.append(f"{item_summary}")
                if key_points:
                    points_str = " • ".join(key_points) if isinstance(key_points, list) else str(key_points)
                    lines.append(f"Önemli Noktalar: {points_str}")
        elif ep.get("todays_topics"):
            lines.append(f"\nÖne Çıkan Konular: {ep.get('todays_topics')}")

        return "\n".join(lines).strip()

    def build_feed(self, episodes: List[Dict[str, Any]], output_xml_path: str):
        """Builds or updates the RSS podcast.xml file."""
        rss = ET.Element("rss", {
            "version": "2.0",
            "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
            "xmlns:atom": "http://www.w3.org/2005/Atom"
        })

        channel = ET.SubElement(rss, "channel")

        base_url = self.config.get("link", "https://monurium.github.io/m1-podcast-generator").rstrip("/")
        feed_filename = self.config.get("feed_filename", "podcast.xml")
        feed_url = f"{base_url}/{feed_filename}"

        # Atom Self Link
        ET.SubElement(channel, "atom:link", {
            "href": feed_url,
            "rel": "self",
            "type": "application/rss+xml"
        })

        # Channel Metadata
        ET.SubElement(channel, "title").text = self.config.get("title", "M1 Podcast")
        ET.SubElement(channel, "link").text = base_url
        ET.SubElement(channel, "language").text = self.config.get("language", "tr-TR")
        ET.SubElement(channel, "description").text = self.config.get("description", "Günlük Türkçe Yapay Zeka & Teknoloji Podcast Bülteni")

        # iTunes Channel Metadata
        ET.SubElement(channel, "itunes:author").text = self.config.get("author", "M1")
        ET.SubElement(channel, "itunes:summary").text = self.config.get("description", "")
        ET.SubElement(channel, "itunes:explicit").text = "true" if self.config.get("explicit", False) else "false"

        # iTunes Owner
        owner_elem = ET.SubElement(channel, "itunes:owner")
        ET.SubElement(owner_elem, "itunes:name").text = self.config.get("author", "M1")
        ET.SubElement(owner_elem, "itunes:email").text = self.config.get("email", "mehmetonurberber@gmail.com")

        # Category
        cat_elem = ET.SubElement(channel, "itunes:category", {"text": self.config.get("category", "Technology")})
        if self.config.get("subcategory"):
            ET.SubElement(cat_elem, "itunes:category", {"text": self.config.get("subcategory")})

        # Image
        if self.config.get("cover_image_url"):
            ET.SubElement(channel, "itunes:image", {"href": self.config["cover_image_url"]})
            image_elem = ET.SubElement(channel, "image")
            ET.SubElement(image_elem, "url").text = self.config["cover_image_url"]
            ET.SubElement(image_elem, "title").text = self.config.get("title", "M1 Podcast")
            ET.SubElement(image_elem, "link").text = base_url

        # Add Episode Items
        for ep in episodes:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = ep.get("title")
            
            rich_desc = self._build_rich_description(ep)
            ET.SubElement(item, "description").text = rich_desc
            ET.SubElement(item, "itunes:summary").text = ep.get("summary", rich_desc[:300])
            ET.SubElement(item, "pubDate").text = ep.get("pub_date", datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"))
            ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = ep.get("guid", ep.get("id"))

            # iTunes Item attributes
            ET.SubElement(item, "itunes:author").text = self.config.get("author", "M1")
            ET.SubElement(item, "itunes:duration").text = str(ep.get("duration_formatted", "00:06:00"))
            ET.SubElement(item, "itunes:explicit").text = "false"

            # Enclosure tag (Audio file download link)
            ET.SubElement(item, "enclosure", {
                "url": ep.get("audio_url"),
                "length": str(ep.get("file_size", 0)),
                "type": "audio/mpeg"
            })

        # Format XML cleanly
        xml_str = ET.tostring(rss, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        pretty_xml = parsed.toprettyxml(indent="  ")
        clean_pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])

        dir_name = os.path.dirname(output_xml_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(output_xml_path, "w", encoding="utf-8") as f:
            f.write(clean_pretty_xml)
        
        print(f"📡 RSS beslemesi başarıyla güncellendi: {output_xml_path}")
