import os
import json
import re
import feedparser
import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ContentGenerator:
    """Fetches latest Turkish & Global tech news and generates Turkish podcast scripts with striking headlines and summaries."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if self.api_key and not self.api_key.startswith("your_"):
            base_url = "https://api.deepseek.com" if os.getenv("DEEPSEEK_API_KEY") else None
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
        else:
            self.client = None
        
        self.rss_feeds = [
            # Turkish Tech Feeds
            "https://webrazzi.com/feed/",
            "https://shiftdelete.net/feed",
            "https://www.chip.com.tr/rss/",
            "https://www.donanimhaber.com/rss/tum/",
            "https://evrimagaci.org/rss.xml",
            # Global Top AI & Tech Feeds
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://arstechnica.com/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.wired.com/feed/category/business/latest/rss"
        ]

    def fetch_fresh_news(self, hours_limit: int = 24, exclude_keywords: List[str] = None) -> str:
        """Collects fresh Turkish & Global AI & Tech news entries, applying safety and novelty filters."""
        fresh_articles: List[str] = []
        exclude_keywords = exclude_keywords or []
        print(f"📡 Toplam {len(self.rss_feeds)} teknoloji ve yapay zeka RSS kaynağından son haberler taranıyor...")

        forbidden_keywords = [
            "war", "kill", "murder", "suicide", "shooting", "attack", "terror", 
            "sexual", "porn", "gore", "deadly", "explosion", "military", "crime", 
            "death", "assault", "violence", "conflict", "bomb", "savaş", "cinayet",
            "ölüm", "saldırı", "terör", "şiddet", "patlama"
        ]

        seen_titles = set()
        for feed_url in self.rss_feeds:
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:8]:
                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", "") or entry.get("description", "")
                    # Clean HTML tags
                    summary = re.sub(r'<[^>]+>', '', summary).strip()
                    combined_text = f"{title} {summary}".lower()
                    
                    if any(bad_word in combined_text for bad_word in forbidden_keywords):
                        continue
                    
                    if any(ex.lower() in title.lower() for ex in exclude_keywords if len(ex) > 4):
                        continue

                    if title and title.lower() not in seen_titles:
                        seen_titles.add(title.lower())
                        clean_item = f"• Başlık: {title}\n  Özet: {summary[:300]}"
                        fresh_articles.append(clean_item)
            except Exception as e:
                print(f"⚠️ RSS ayrıştırma uyarısı ({feed_url}): {e}")

        if not fresh_articles:
            return ""

        return "\n\n".join(fresh_articles[:15])

    def generate_dialogue_script(self, raw_news_context: str, recent_topics: List[str] = None) -> Dict[str, Any]:
        """Generates engaging Turkish podcast dialogue (Ahmet & Emel) with striking headlines & summaries for Slack and RSS."""
        print("🤖 Türkçe 2-Sunuculu (Ahmet & Emel) podcast metni ve çarpıcı haber özetleri üretiliyor...")
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')

        system_prompt = (
            "Sen profesyonel, samimi, dinamik ve bilgili bir teknoloji podcast yapımcısısın.\n"
            "Görevin: Günün en önemli yapay zeka ve teknoloji haberlerini analiz ederek hem dinleyicileri ekrana/kulaklığa bağlayan "
            "doğal bir Türkçe podcast diyalog metni (Sunucular: Ahmet ve Emel) hazırlamak hem de her haber için Slack ve bültende "
            "paylaşılacak çarpıcı başlıklar, can alıcı noktalar ve özetler oluşturmaktır.\n\n"
            "KURALLAR:\n"
            "1. DİL: %100 akıcı, doğal, samimi Türkçe. Dinleyiciyi sıkan robotik ifadelerden kaçın.\n"
            "2. SUNUCULAR:\n"
            "   - 'Ahmet:' (Analitik, vizyoner, teknolojinin perde arkasını aktaran erkek sunucu)\n"
            "   - 'Emel:' (Meraklı, dinamik, sorular soran ve pratik etkileri sorgulayan kadın sunucu)\n"
            "3. İÇERİK ODAĞI: Yapay zeka modelleri, yazılım dünyası, çip teknolojileri, robotik ve geleceğin teknolojileri.\n"
            "4. ÇARPICI BAŞLIKLAR: Her haber için merak uyandıran, vurucu ve net bir başlık (`headline`) ve en can alıcı 2-3 madde (`key_points`) belirle.\n"
            "5. SÜRE / UZUNLUK: Konuşma metni yaklaşık 900-1100 kelime olmalıdır (yaklaşık 6-7 dakika akıcı konuşma).\n"
            "6. ÇIKTI FORMATI: Yanıtını SADECE geçerli bir JSON nesnesi olarak ver. Başka hiçbir markdown veya açıklama ekleme.\n"
            "JSON Şeması:\n"
            "{\n"
            '  "title": "Bölümün dikkat çekici ana başlığı",\n'
            '  "summary": "Bölümün 1-2 cümlelik genel kanca özeti",\n'
            '  "news_items": [\n'
            "    {\n"
            '      "headline": "Çarpıcı ve Vurucu Haber Başlığı",\n'
            '      "key_points": ["Can alıcı nokta 1", "Can alıcı nokta 2"],\n'
            '      "summary": "Haberin 2-3 cümlelik net özeti."\n'
            "    }\n"
            "  ],\n"
            '  "todays_topics": "Haber başlıklarının virgülle ayrılmış kısa listesi",\n'
            '  "script": "Ahmet: Merhaba teknoloji meraklıları! Bugün...\\n\\nEmel: Evet Ahmet, inanılmaz gelişmeler var..."\n'
            "}"
        )

        user_prompt = (
            f"Tarih: {today_date_str}\n\n"
            f"Günün Ham Teknoloji & Yapay Zeka Haberleri:\n\n{raw_news_context or 'Günün öne çıkan yapay zeka modelleri, otonom yazılım ajanları ve açık kaynak gelişmeler.'}\n\n"
            "Lütfen yukarıdaki şemaya tam uyumlu JSON çıktısını üret."
        )

        if not self.client:
            print("ℹ️ LLM API anahtarı bulunamadı, zengin Türkçe örnek podcast şablonu kullanılıyor.")
            return self._get_fallback_turkish_script()

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat" if "deepseek" in str(self.client.base_url) else "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content.strip()
            data = json.loads(raw_content)

            # Ensure required keys
            if "script" not in data or "news_items" not in data:
                raise ValueError("JSON output missing required fields")

            return data
        except Exception as e:
            print(f"⚠️ LLM üretim hatası ({e}). Fallback şablonuna geçiliyor...")
            return self._get_fallback_turkish_script()

    def generate_script(self, raw_news_context: str) -> Dict[str, Any]:
        """Generates monologue Turkish podcast script with news highlights."""
        dialogue_data = self.generate_dialogue_script(raw_news_context)
        # Convert dialogue to monologue format if needed
        script_text = dialogue_data.get("script", "")
        mono_lines = []
        for line in script_text.splitlines():
            clean = re.sub(r'^(Ahmet|Emel|Alex|Sarah|Sunucu):\s*', '', line).strip()
            if clean:
                mono_lines.append(clean)
        
        dialogue_data["script"] = "\n\n".join(mono_lines)
        return dialogue_data

    def _get_fallback_turkish_script(self) -> Dict[str, Any]:
        """Provides a comprehensive, realistic Turkish podcast episode with striking news headlines and summaries."""
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')
        return {
            "title": f"M1 Podcast - Yapay Zeka Çağında Yeni Dönem ({today_date_str})",
            "summary": "Yeni nesil yapay zeka ajanları kod yazma süreçlerini dönüştürürken, açık kaynak modeller ve kuantum hesaplamada çığır açan yenilikler gündemde.",
            "todays_topics": "Otonom Yazılım Ajanları, Açık Kaynak LLM Devrimi, Yeni Nesil Çip Mimarileri",
            "news_items": [
                {
                    "headline": "Otonom AI Mühendisleri: Yazılım Geliştirme Süreçleri Baştan Yazılıyor",
                    "key_points": [
                        "Yapay zeka modelleri artık hata ayıklamadan deploy aşamasına kadar tüm döngüyü yönetiyor",
                        "Geliştirici ekiplerinin verimliliğinde %40'a varan artış ölçüldü"
                    ],
                    "summary": "Son yayınlanan kıyaslama testlerine göre yeni nesil yapay zeka kodlama ajanları, karmaşık yazılım mimarilerini analiz edip bağımsız olarak test yazabiliyor ve güvenlik açıklarını yamayabiliyor."
                },
                {
                    "headline": "Açık Kaynak Modellerde Performans Patlaması: Kapalı Sistemlere Büyük Meydan Okuma",
                    "key_points": [
                        "Cihaz üzerinde (on-device) çalışan optimize modeller standart dizüstü bilgisayarlarda çalışıyor",
                        "Gizlilik odaklı yerel çözümlere talep katlanarak artıyor"
                    ],
                    "summary": "Açık ağırlıklı yeni modeller, kaynak tüketimini yarı yarıya düşürürken mantık yürütme ve problem çözme testlerinde tescilli büyük modellere yaklaştı."
                },
                {
                    "headline": "Yeni Nesil Nöromorfik Çipler: Enerji Tüketiminde 10 Kat Verimlilik",
                    "key_points": [
                        "İnsan beyninin sinaps yapısını taklit eden yeni donanımlar tanıtıldı",
                        "Veri merkezlerinin yüksek elektrik tüketimine sürdürülebilir alternatif"
                    ],
                    "summary": "Donanım üreticileri, yapay zeka modellerini mikrosaniye seviyesinde gecikmeyle ve geleneksel GPU'lara kıyasla onda bir enerjiyle çalıştıran yeni mimarilerini duyurdu."
                }
            ],
            "script": (
                "Ahmet: Merhaba değerli teknoloji meraklıları! M1 Podcast'e hepiniz hoş geldiniz. Bugün teknoloji ve yapay zeka dünyasında gerçekten baş döndürücü gelişmeler var.\n\n"
                "Emel: Kesinlikle Ahmet! Özellikle yazılım mühendisliğini kökten değiştiren otonom yapay zeka ajanları ve açık kaynak dünyasındaki son hamleler bugün gündemimizin ilk sırasında.\n\n"
                "Ahmet: İlk çarpıcı haberimizle başlayalım. Artık sadece kod tamamlayan asistanlar değil; projenin tamamını kavrayan, hataları bulan, testleri yazıp sistemi yayına alan tam teşekküllü otonom yazılım ajanları devri başladı. Yapılan son bağımsız ölçümlerde bu sistemlerin geliştirici ekiplerin hızını neredeyse ikiye katladığı görüldü.\n\n"
                "Emel: Bu durum yazılımcıların rolünü bir kod yazıcısından bir sistem mimarı ve denetleyicisine dönüştürüyor aslında. Diğer yandan açık kaynak dünyasında da inanılmaz bir hareketlilik var. Artık kendi bilgisayarınızda, hiçbir veriyi buluta göndermeden çalıştırabileceğiniz kompakt ve güçlü modeller kapalı dev modellere kafa tutuyor.\n\n"
                "Ahmet: Gizlilik ve veri egemenliği açısından bu devrim niteliğinde bir adım Emel. Şirketler artık hassas verilerini dışarıya çıkarmadan kurum içi yapay zeka çözümlerini güvenle kurabiliyor.\n\n"
                "Emel: Donanım tarafında ise yeni nesil nöromorfik çipler sahneye çıktı. İnsan beyninin çalışma prensibini taklit eden bu yeni mimariler, devasa veri merkezlerinin enerji krizine çare olmayı hedefliyor.\n\n"
                "Ahmet: Teknoloji dünyasının nabzını tutmaya devam edeceğiz. Günün tüm detayları ve özetleri bültenimizde yer alıyor. Yarın yeni gelişmelerle tekrar görüşmek üzere, hoşça kalın!\n\n"
                "Emel: Kendinize çok iyi bakın, teknolojiyle kalın!"
            )
        }
