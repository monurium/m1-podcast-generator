import os
import json
import requests
from typing import Dict, Any, List, Optional

class SlackNotifier:
    """Handles publishing daily podcast notifications and news highlights to Slack channels."""

    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None, channel_id: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = channel_id or os.getenv("SLACK_CHANNEL_ID")

    def build_slack_payload(self, episode_data: Dict[str, Any], base_url: str = "") -> Dict[str, Any]:
        """Constructs a polished Slack Block Kit message with headlines, summaries, and audio links."""
        title = episode_data.get("title", "M1 Günlük Podcast")
        pub_date = episode_data.get("pub_date", "")
        duration = episode_data.get("duration_formatted", "")
        summary = episode_data.get("summary", "")
        news_items = episode_data.get("news_items", [])
        audio_url = episode_data.get("audio_url", "")
        web_url = base_url.rstrip("/") if base_url else "https://monurium.github.io/m1-podcast-generator"
        rss_url = f"{web_url}/podcast.xml"

        blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🎙️ M1 Podcast: Günlük Teknoloji & Yapay Zeka Bülteni",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*📅 Tarih:*\n{pub_date[:16] if pub_date else 'Bugün'}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*⏱️ Süre:*\n{duration or '7-8 dk'}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📌 Bölüm Başlığı:*\n*{title}*\n\n_{summary}_"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔥 GÜNÜN ÇARPICI HABER BAŞLIKLARI VE ÖZETLERİ*"
                }
            }
        ]

        if news_items:
            for idx, item in enumerate(news_items, 1):
                headline = item.get("headline") or item.get("title") or f"Haber {idx}"
                item_summary = item.get("summary", "")
                key_points = item.get("key_points", [])

                item_text = f"*{idx}. ⚡ {headline}*\n{item_summary}"
                if key_points:
                    if isinstance(key_points, list):
                        points_str = " • ".join(key_points)
                    else:
                        points_str = str(key_points)
                    item_text += f"\n> _Öne Çıkanlar:_ {points_str}"

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": item_text
                    }
                })
        else:
            # Fallback if structured news_items is empty
            topics = episode_data.get("todays_topics", summary)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {topics}"
                }
            })

        blocks.append({"type": "divider"})

        # Action links section
        action_elements = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🎧 Web'de Dinle",
                    "emoji": True
                },
                "url": web_url or "https://monurium.github.io/m1-podcast-generator",
                "style": "primary"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📡 RSS Beslemesi",
                    "emoji": True
                },
                "url": rss_url
            }
        ]

        if audio_url:
            action_elements.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⬇️ MP3 İndir",
                    "emoji": True
                },
                "url": audio_url
            })

        blocks.append({
            "type": "actions",
            "elements": action_elements
        })

        return {
            "text": f"🎙️ M1 Podcast Yeni Bölüm: {title}",
            "blocks": blocks
        }

    def send_notification(self, episode_data: Dict[str, Any], base_url: str = "") -> bool:
        """Sends episode notification to Slack via Webhook or Bot Token."""
        payload = self.build_slack_payload(episode_data, base_url)

        if not self.webhook_url and not self.bot_token:
            print("ℹ️ SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN not configured. Previewing Slack message payload:")
            print("=" * 50)
            print(f"Text: {payload['text']}")
            for block in payload.get("blocks", []):
                if "text" in block and isinstance(block["text"], dict):
                    print(block["text"].get("text", ""))
            print("=" * 50)
            return True

        if self.webhook_url:
            try:
                print(f"🚀 Sending Slack notification via Webhook URL...")
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                if response.status_code == 200:
                    print("✅ Slack notification sent successfully via Webhook!")
                    return True
                else:
                    print(f"⚠️ Slack Webhook returned status code {response.status_code}: {response.text}")
            except Exception as e:
                print(f"❌ Error sending Slack notification via Webhook: {e}")

        if self.bot_token and self.channel_id:
            try:
                print(f"🚀 Sending Slack notification to channel {self.channel_id} via Bot Token...")
                bot_payload = payload.copy()
                bot_payload["channel"] = self.channel_id
                response = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    json=bot_payload,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Authorization": f"Bearer {self.bot_token}"
                    },
                    timeout=15
                )
                res_data = response.json()
                if res_data.get("ok"):
                    print("✅ Slack notification sent successfully via Bot API!")
                    return True
                else:
                    print(f"⚠️ Slack Bot API error: {res_data.get('error')}")
            except Exception as e:
                print(f"❌ Error sending Slack notification via Bot API: {e}")

        return False
