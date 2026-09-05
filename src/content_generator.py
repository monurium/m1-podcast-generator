import sys
import os
import re
import json
import socket
import datetime
import feedparser
from typing import List, Dict, Any, Optional
from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ContentGenerator:
    """Fetches high-quality, curated Turkish & Global AI news from the last 24 hours and generates
    interactive ~10-minute podcast scripts with natural explanations."""

    def __init__(self, api_key: str = None):
        # 1. Gemini Client (Birincil: gemini-2.5-pro / gemini-2.5-flash)
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_FREE_API_KEY")
        if self.gemini_key and not self.gemini_key.startswith("your_"):
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print(f"⚠️ Gemini SDK başlatılamadı: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None

        # 2. DeepSeek Client (Yedek 1: deepseek-chat / DeepSeek-V3)
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key and not deepseek_key.startswith("your_"):
            self.deepseek_client = OpenAI(
                api_key=deepseek_key,
                base_url="https://api.deepseek.com"
            )
        else:
            self.deepseek_client = None

        # 3. OpenAI Client (Yedek 2: gpt-4o-mini)
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        if openai_key and not openai_key.startswith("your_"):
            self.openai_client = OpenAI(api_key=openai_key)
        else:
            self.openai_client = None

        # Geriye dönük uyumluluk için alias
        self.client = self.deepseek_client or self.openai_client

        # Curated, authoritative AI & tech news feeds (24 sources)
        self.ai_feeds = [
            # --- Türkçe Kaynaklar ---
            {"name": "Webrazzi AI",        "url": "https://webrazzi.com/kategori/yapay-zeka/feed/",         "ai_only": True},
            {"name": "ShiftDelete AI",     "url": "https://shiftdelete.net/yapay-zeka/feed",                "ai_only": True},
            {"name": "Evrim Ağacı",        "url": "https://evrimagaci.org/rss.xml",                         "ai_only": False},
            {"name": "Habertürk Teknoloji","url": "https://www.haberturk.com/rss/kategori/teknoloji.xml",   "ai_only": False},
            {"name": "Donanimhaber",       "url": "https://www.donanimhaber.com/rss/",                       "ai_only": False},

            # --- Küresel AI Odaklı Kaynaklar ---
            {"name": "TechCrunch AI",      "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "ai_only": True},
            {"name": "The Verge AI",       "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "ai_only": True},
            {"name": "VentureBeat AI",     "url": "https://venturebeat.com/category/ai/feed/",              "ai_only": True},
            {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "ai_only": True},
            {"name": "Wired AI",           "url": "https://www.wired.com/feed/tag/ai/latest/rss",           "ai_only": True},
            {"name": "Ars Technica AI",    "url": "https://arstechnica.com/tag/ai/feed/",                   "ai_only": True},
            {"name": "IEEE Spectrum AI",   "url": "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss", "ai_only": True},
            {"name": "MarkTechPost",       "url": "https://www.marktechpost.com/feed/",                     "ai_only": True},
            {"name": "SiliconANGLE AI",    "url": "https://siliconangle.com/category/ai/feed/",             "ai_only": True},
            {"name": "Synced Review",      "url": "https://syncedreview.com/feed/",                         "ai_only": True},
            {"name": "AI Business",        "url": "https://aibusiness.com/rss.xml",                          "ai_only": True},
            {"name": "Analytics India Mag","url": "https://analyticsindiamag.com/feed/",                     "ai_only": True},
            {"name": "KDNuggets",          "url": "https://www.kdnuggets.com/feed",                          "ai_only": False},
            {"name": "Import AI (Clark)",  "url": "https://importai.substack.com/feed",                     "ai_only": True},
            {"name": "DeepLearning.AI",    "url": "https://www.deeplearning.ai/the-batch/feed.xml",         "ai_only": True},
            {"name": "Towards Data Science","url": "https://towardsdatascience.com/feed",                   "ai_only": False},
            {"name": "AI Magazine",        "url": "https://aimagazine.com/rss.xml",                          "ai_only": True},

            # --- Genel Teknoloji (AI filtreli) ---
            {"name": "BBC Tech",           "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",       "ai_only": False},
            {"name": "Hacker News AI",     "url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT&points=50", "ai_only": True},
        ]

    # ------------------------------------------------------------------
    # NEWS FETCHING
    # ------------------------------------------------------------------

    def fetch_fresh_news(self, hours_limit: int = 24, exclude_keywords: List[str] = None) -> str:
        """Collects fresh, high-quality Turkish & Global AI news published strictly within the
        hours_limit window (default 24 h). Applies timeout, entity-based semantic dedup, and
        forbidden-content filtering."""
        fresh_articles: List[str] = []
        exclude_keywords = exclude_keywords or []
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        print(f"📡 Toplam {len(self.ai_feeds)} nitelikli yapay zeka RSS kaynağından son {hours_limit} saatin haberleri taranıyor...")

        ai_keywords = [
            "yapay zeka", "ai", "llm", "dil modeli", "makine öğrenimi", "derin öğrenme",
            "artificial intelligence", "machine learning", "deep learning", "neural",
            "openai", "anthropic", "claude", "chatgpt", "deepseek", "gemini", "copilot",
            "agent", "otonom", "robot", "robotik", "nvidia", "tpu", "gpu", "npu",
            "transformer", "reasoning", "benchmark", "hugging face", "mistral", "meta ai",
            "multimodal", "generative", "gpt", "llama", "falcon", "stable diffusion",
            "image generation", "text-to-speech", "voice cloning", "agentic",
        ]

        forbidden_keywords = [
            "war", "kill", "murder", "suicide", "shooting", "attack", "terror",
            "sexual", "porn", "gore", "deadly", "explosion", "military", "crime",
            "death", "assault", "violence", "conflict", "bomb", "savaş", "cinayet",
            "ölüm", "saldırı", "terör", "şiddet", "patlama",
        ]

        # Entity-based semantic dedup: normalize title to key tokens
        seen_normalized = set()

        def _normalize_title(t: str) -> str:
            """Returns a deduplicated fingerprint of the title's key words."""
            t = t.lower()
            # Remove common stop words and punctuation
            t = re.sub(r"[^\w\s]", " ", t)
            stop = {"the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for",
                    "is", "are", "was", "were", "by", "with", "from", "that", "this",
                    "bir", "ve", "ile", "da", "de", "bu", "o", "için", "olan", "oldu"}
            tokens = [w for w in t.split() if w not in stop and len(w) > 2]
            # Keep first 6 meaningful tokens as fingerprint
            return " ".join(sorted(tokens[:6]))

        # Apply global RSS timeout to prevent pipeline hang on slow sources
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)

        try:
            for feed in self.ai_feeds:
                feed_name = feed["name"]
                feed_url = feed["url"]
                is_ai_only = feed.get("ai_only", False)
                try:
                    parsed = feedparser.parse(
                        feed_url,
                        request_headers={"User-Agent": "M1-PodcastBot/2.0 (+https://monurium.github.io/m1-podcast-generator)"},
                    )
                    for entry in parsed.entries[:20]:
                        title = entry.get("title", "").strip()
                        summary = entry.get("summary", "") or entry.get("description", "")
                        summary = re.sub(r"<[^>]+>", "", summary).strip()
                        combined_text = f"{title} {summary}".lower()

                        # Forbidden content filter
                        if any(bad in combined_text for bad in forbidden_keywords):
                            continue

                        # Recent-topic exclusion (dedup with previous episodes)
                        if any(ex.lower() in title.lower() for ex in exclude_keywords if len(ex) > 4):
                            continue

                        # AI keyword enforcement for non-dedicated feeds
                        if not is_ai_only and not any(kw in combined_text for kw in ai_keywords):
                            continue

                        # Strict timestamp verification
                        parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
                        if parsed_time:
                            try:
                                pub_dt = datetime.datetime(*parsed_time[:6], tzinfo=datetime.timezone.utc)
                                age_hours = (now_utc - pub_dt).total_seconds() / 3600
                                if age_hours > hours_limit:
                                    continue
                            except Exception:
                                pass  # No timestamp → include (some feeds omit dates)

                        clean_title = re.sub(r"\s+", " ", title).strip()
                        if not clean_title:
                            continue

                        # Semantic deduplication
                        norm = _normalize_title(clean_title)
                        if norm in seen_normalized:
                            continue
                        seen_normalized.add(norm)

                        clean_item = f"• [{feed_name}] Başlık: {clean_title}\n  Özet: {summary[:320]}"
                        fresh_articles.append(clean_item)

                except Exception as e:
                    print(f"⚠️ RSS ayrıştırma uyarısı ({feed_name}): {e}")
        finally:
            socket.setdefaulttimeout(original_timeout)

        # Auto-widen window if not enough articles found
        if len(fresh_articles) < 12 and hours_limit < 48:
            print(f"ℹ️ Son {hours_limit} saatte {len(fresh_articles)} haber bulundu. 48 saatlik aralık taranıyor...")
            return self.fetch_fresh_news(hours_limit=48, exclude_keywords=exclude_keywords)

        if not fresh_articles:
            return ""

        print(f"✅ {len(fresh_articles)} özgün haber toplandı.")
        return "\n\n".join(fresh_articles[:45])

    # ------------------------------------------------------------------
    # SCRIPT GENERATION
    # ------------------------------------------------------------------

    def generate_dialogue_script(self, raw_news_context: str, recent_topics: List[str] = None) -> Dict[str, Any]:
        """Generates a dynamic 10-11 minute (~1100-1250 words) Turkish podcast dialogue
        (Kaan & Ece) with 8-10 pure AI news stories, natural back-and-forth conversation,
        and TTS-optimized clean text output."""
        print("🤖 Nitelikli yapay zeka haberleriyle 10 dakikalık etkileşimli Türkçe podcast metni üretiliyor (Kaan & Ece)...")
        today_date_str = datetime.date.today().strftime("%d.%m.%Y")

        system_prompt = (
            "Sen iki deneyimli, modern teknoloji sunucusu (Kaan ve Ece) için canlı, samimi ve son derece "
            "etkileşimli bir Türkçe podcast metni yazan kıdemli bir yapımcısın.\n\n"

            "═══ SUNUCU KİMLİKLERİ (PERSONA) ═══\n"
            "• Kaan (Erkek): Vizyoner, enerjik, manşeti ve büyük resmi yakalayan, sektörel ve endüstriyel etkileri vurgulayan teknoloji sunucusu.\n"
            "• Ece (Kadın): Analitik, meraklı, teknik perde arkasını, algoritma detaylarını ve kullanıcıya doğrudan etkisini sorgulayan teknoloji sunucusu.\n\n"

            "═══ ZORUNLU KURALLAR ═══\n\n"

            "1. HEDEF SÜRE VE KELİME HEDEFİ\n"
            "   Podcast süresi TAM 10-11 DAKİKA (1100-1250 KELİME) olmalıdır. "
            "Seçilen haberler son 24 saatin en nitelikli yapay zeka ve makine öğrenimi gelişmelerine odaklanmalı, "
            "teknik ve pratik boyutlarıyla detaylandırılmalıdır.\n\n"

            "2. HABER SAYISI\n"
            "   8 ile 10 adet (en az 8 haber) güçlü ana yapay zeka gelişmesi seç. "
            "Tüm haberler hem 'news_items' dizisinde hem de diyalog akışında sırayla ele alınmalıdır.\n\n"

            "3. GERÇEK ETKİLEŞİM VE DİYALOG\n"
            "   • Sunucular birbirini papağan gibi onaylamamalı. "
            "YASAK ifadeler: 'kesinlikle', 'çok haklısın', 'aynen öyle', 'tam olarak', 'harika bir nokta', "
            "'güzel bir soru', 'iyi ki sordun', 'tabii ki', 'şüphesiz'.\n"
            "   • Her haber için Kaan ve Ece arasında en az 2-4 karşılıklı konuşma turu olmalı.\n"
            "   • Sunucular farklı bakış açıları sunsun, zaman zaman hafifçe birbirine itiraz etsin.\n"
            "   • Bir önceki haberin sonundaki detayı bir sonrakine köprü olarak kullan "
            "(mekanik 'Bir diğer konu...' geçişleri YASAK).\n\n"

            "4. TEKNİK TERİMLERİ DOĞAL AÇIKLA\n"
            "   Her teknik kavram (Test-time compute, Abliteration, Otonom Ajan, Vision-AI, "
            "Model Zehirleme, Guardrails, RLHF, RAG, Fine-tuning, vb.) konuşma akışını bozmadan "
            "somut günlük benzetmelerle izah edilsin.\n\n"

            "5. AÇILIŞ VE KAPANIŞ ÇEŞİTLİLİĞİ\n"
            "   • Açılışta YASAK: 'Merhaba herkese!', 'Bugün harika haberlerimiz var', "
            "'Haydi başlayalım', 'Sizlerle tekrar buluşmaktan mutluluk duyuyoruz'. "
            "Bunlar yerine doğrudan ilk haberin çarpıcı bir detayıyla veya provokatif bir soruyla başla.\n"
            "   • Kapanışta YASAK: 'Yarın yepyeni haberlerle tekrar görüşmek dileğiyle', "
            "'Kendinize iyi bakın', 'Hoşça kalın', 'Bizimle kalmaya devam edin'. "
            "Her bölümün kapanışı farklı olmalı: Merak uyandıran açık bir soruyla, "
            "dinleyiciye eylem çağrısıyla veya kısa bir anekdotla bitir.\n\n"

            "6. TTS UYUMU (ZORUNLU)\n"
            "   Script metni doğrudan ses sentezi motoruna (Text-to-Speech) gidecek. Bu yüzden:\n"
            "   • Emoji, ikon, özel karakter KULLANMA (✅ ❌ 🎙️ ⚡ vb.)\n"
            "   • Parantez içi notlar ve köşeli parantezler KULLANMA\n"
            "   • URL ve web adresleri YAZMA\n"
            "   • Rakamsal kısaltmalar açık yaz: '100M$' → 'yüz milyon dolar', "
            "'GPT-4o' → 'G P T 4 o', '%15' → 'yüzde on beş'\n"
            "   • Noktalama işaretleri doğal konuşma ritmine göre kullan\n\n"

            "7. META BİLGİ YASAĞI\n"
            "   Süreden veya haber sayısından ASLA bahsetme. Bölüm içinde 'on dakikalık', "
            "'sekiz haberimiz var' gibi meta bilgiler YASAK.\n\n"

            "8. ÇIKTI FORMATI\n"
            "   Yanıtını SADECE geçerli bir JSON nesnesi olarak ver, başında veya sonunda "
            "kod bloğu işareti olmadan.\n\n"

            "JSON Şeması:\n"
            "{\n"
            '  "title": "Bölümün dikkat çekici ana başlığı",\n'
            '  "summary": "Bölümün 1-2 cümlelik kanca özeti",\n'
            '  "news_items": [\n'
            "    {\n"
            '      "headline": "Çarpıcı Haber Başlığı",\n'
            '      "key_points": ["Can alıcı nokta 1", "Can alıcı nokta 2"],\n'
            '      "summary": "Haberin 2-3 cümlelik net özeti."\n'
            "    }\n"
            "  ],\n"
            '  "todays_topics": "8-10 haber başlığının virgülle ayrılmış listesi",\n'
            '  "script": "Kaan: [Doğrudan ilk haberin çarpıcı detayıyla veya bir soruyla başla]...\\n\\nEce: ..."\n'
            "}"
        )

        user_prompt = (
            f"Tarih: {today_date_str}\n\n"
            f"Günün Ham Nitelikli Yapay Zeka Haber Havuzu (Son 24 Saat):\n\n"
            f"{raw_news_context or 'Günün öne çıkan yapay zeka, açık modeller, otonom ajanlar ve LLM gelişmeleri.'}\n\n"
            "Lütfen son 24 saatin en nitelikli 8-10 yapay zeka haberini derinlemesine tartışan, "
            "teknik terimleri doğal dille açıklayan, yapay onaylama kalıplarından uzak, "
            "karşılıklı soru-cevaplı, TTS uyumlu (emoji/URL/parantez yok), "
            "farklı bir açılış ve kapanışla biten 1100-1250 KELİMELİK (~10-11 dakika) "
            "Türkçe diyalog JSON çıktısını üret."
        )

        # ==============================================================
        # 1. BİRİNCİL SEÇENEK: Google Gemini (Öncelik: gemini-2.5-pro -> gemini-2.5-flash)
        # (Yüksek edebi zeka, doğal radyo diyalogu, kusursuz JSON şeması)
        # ==============================================================
        if self.gemini_client:
            for g_model in ["gemini-2.5-pro", "gemini-2.5-flash"]:
                try:
                    print(f"🎙️ Podcast metni üretiliyor: Google {g_model}...")
                    from google.genai import types
                    response = self.gemini_client.models.generate_content(
                        model=g_model,
                        contents=f"{system_prompt}\n\n{user_prompt}",
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.75,
                        ),
                    )
                    data = json.loads(response.text.strip())
                    if "script" in data and "news_items" in data:
                        print(f"✅ {g_model} ile podcast metni başarıyla üretildi!")
                        return data
                except Exception as e:
                    print(f"⚠️ Gemini ({g_model}) çağrısı başarısız oldu: {e}")

            print("⚠️ Gemini denemeleri tükendi. DeepSeek yedeğine geçiliyor...")

        # ==============================================================
        # 2. İKİNCİ SEÇENEK (YEDEK 1): DeepSeek-V3 (deepseek-chat)
        # (Samimi Türkçe diyalog, yüksek akıcılık, ekonomik)
        # ==============================================================
        if self.deepseek_client:
            try:
                print("🎙️ Podcast metni üretiliyor: DeepSeek-V3 (deepseek-chat)...")
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.75,
                    max_tokens=6000,
                    response_format={"type": "json_object"},
                )
                raw_content = response.choices[0].message.content.strip()
                data = json.loads(raw_content)
                if "script" in data and "news_items" in data:
                    print("✅ DeepSeek-V3 ile podcast metni başarıyla üretildi!")
                    return data
            except Exception as e:
                print(f"⚠️ DeepSeek üretim hatası: {e}. OpenAI / Fallback şablonuna geçiliyor...")

        # ==============================================================
        # 3. ÜÇÜNCÜ SEÇENEK (YEDEK 2): OpenAI (gpt-4o-mini)
        # ==============================================================
        if self.openai_client:
            try:
                print("🎙️ Podcast metni üretiliyor: OpenAI (gpt-4o-mini)...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.75,
                    max_tokens=6000,
                    response_format={"type": "json_object"},
                )
                raw_content = response.choices[0].message.content.strip()
                data = json.loads(raw_content)
                if "script" in data and "news_items" in data:
                    print("✅ OpenAI gpt-4o-mini ile podcast metni başarıyla üretildi!")
                    return data
            except Exception as e:
                print(f"⚠️ OpenAI üretim hatası: {e}. Dahili şablona geçiliyor...")

        # ==============================================================
        # 4. DÖRDÜNCÜ SEÇENEK: Dahili Çevrimdışı TTS Şablonu
        # ==============================================================
        print("ℹ️ Çevrimiçi LLM anahtarı bulunamadı veya tüm API'ler yanıt vermedi. Dahili TTS şablonu devreye alınıyor.")
        return self._get_fallback_turkish_script()

    def generate_script(self, raw_news_context: str) -> Dict[str, Any]:
        """Generates monologue Turkish podcast script derived from the dialogue script."""
        dialogue_data = self.generate_dialogue_script(raw_news_context)
        script_text = dialogue_data.get("script", "")
        mono_lines = []
        for line in script_text.splitlines():
            clean = re.sub(r"^(Kaan|Ece|Ahmet|Emel|Alex|Sarah|Sunucu):\s*", "", line).strip()
            if clean:
                mono_lines.append(clean)

        dialogue_data["script"] = "\n\n".join(mono_lines)
        return dialogue_data

    # ------------------------------------------------------------------
    # FALLBACK SCRIPT
    # ------------------------------------------------------------------

    def _get_fallback_turkish_script(self) -> Dict[str, Any]:
        """Provides a TTS-optimized, naturally conversational ~1150-word (10 min) Turkish podcast
        episode. No emojis, no URLs, no parentheses — clean for direct TTS synthesis."""
        today_date_str = datetime.date.today().strftime("%d.%m.%Y")
        return {
            "title": f"Migros OneCast AI - Gunluk Yapay Zeka Bulteni: Nvidia ve Hugging Face, Ajan Cagi ({today_date_str})",
            "summary": (
                "Nvidia'nin Hugging Face satin alimidan Meta Muse Spark kodlama modeline, "
                "OpenAI Astra'nin akil yurutme tartismalarina robotik gorme ve siber guvenlik "
                "yatirimlarindan yapay zekanin istihdam etkisine kadar bugunun dokuz kritik AI gelismesi."
            ),
            "todays_topics": (
                "Nvidia Hugging Face Satin Alimi, Meta Muse Spark 1.3 Ajan Modeli, "
                "OpenAI Astra Akil Yurutme, Google Gemini Flash Cyber, HiddenLayer 100 Milyon Dolar Yatirim, "
                "Abliteration Guvensizlik Tartismasi, Lyte Robotik Gorme, "
                "Claude Bilgisayar Kullanimi, Yapay Zeka Istihdam Raporu"
            ),
            "news_items": [
                {
                    "headline": "Nvidia, Acik Kaynak Merkezi Hugging Face'i Satin Aldigini Dogruladi",
                    "key_points": [
                        "Dunyanin en buyuk acik yapay zeka model havuzu donanim devinin bunyesine gecti",
                        "Bagimsiz arastirmacilar ve duzenleyici kurumlar olasi tekel risklerini tartisiyor",
                    ],
                    "summary": (
                        "Nvidia, acik kaynak yapay zeka toplulugunun kalbi sayilan Hugging Face platformunu "
                        "satin aldigini dogrulayarak yapay zeka ekosisteminde tarihi bir konsolidasyona imza atti."
                    ),
                },
                {
                    "headline": "Meta'dan Otonom Kodlama Ajani Modeli: Muse Spark 1.3",
                    "key_points": [
                        "Model sadece kod tamamlamakla kalmiyor, tum depoyu tarayip bagimsiz testler yaziyor",
                        "Gelistirici ekiplerinin hata ayiklama surelerinde radikal hizlanma saglandi",
                    ],
                    "summary": (
                        "Meta, yazilim projelerinin mimarisini anlayarak bagimsiz testler yazabilen "
                        "ve hatalari otomatik duzeltebilen ajan tabanli yeni Muse Spark 1.3 modelini duyurdu."
                    ),
                },
                {
                    "headline": "OpenAI Astra'nin Derin Akil Yurutme Teknigi Guvenlik Tartismasi Yaratti",
                    "key_points": [
                        "Model yanit uretmeden once test ani hesaplamasiyla ic sesini kontrol ediyor",
                        "Derin mantik yurutme sureclerinin guvenligi asmada yeni riskler dogurdugu belirtiliyor",
                    ],
                    "summary": (
                        "OpenAI'in yeni Astra modeli, karmask mantik yurutme yetenekleriyle one cikarken "
                        "otonom karar alma sureclerindeki guvenlik bariyerleri tartisiliyor."
                    ),
                },
                {
                    "headline": "Google'dan Cift Hamle: Gemini Flash ve Siber Guvenlik Odakli Flash Cyber",
                    "key_points": [
                        "Flash Cyber modeli sifir gun aciklari ve oltalama saldirilarini milisaniyelerde tespit ediyor",
                        "Hafif mimari sayesinde uc cihazlarda yuksek hizda guvenlik taramasi yapabiliyor",
                    ],
                    "summary": (
                        "Google, dusuk gecikmeli genel amacli Gemini Flash modelinin yani sira kurumsal "
                        "siber savunma icin ozel optimize edilen Flash Cyber modelini tanitti."
                    ),
                },
                {
                    "headline": "Yapay Zeka Modellerini Savunan HiddenLayer, 100 Milyon Dolar Yatirim Aldi",
                    "key_points": [
                        "Model zehirleme ve agirlik manipulasyonu saldirilarindan korunmak icin kalkan gelistiriliyor",
                        "Kurumsal yapay zeka guvenligi sektorunun en buyuk yatirimlarindan biri gerceklesti",
                    ],
                    "summary": (
                        "Buyuk dil modellerini veri zehirleme ve jailbreak saldirilarindan koruyan siber guvenlik "
                        "girisimi HiddenLayer, 100 milyon dolarlik Seri B yatirim turunu tamamladi."
                    ),
                },
                {
                    "headline": "Abliteration: Acik Modellerden Guvenlik Filtrelerinin Silinmesi Tartisiliyor",
                    "key_points": [
                        "Agirlik matrislerindeki guvenlik vektorleri matematiksel cerrahiyle temizleniyor",
                        "Sansursuz arastirma vaadiyle sunulan hizmet siber guvenlik otoritelerinde alarm yaratti",
                    ],
                    "summary": (
                        "Acik agirlikli modellerden guvenlik kurallarini kaldiran Abliteration yontemi, "
                        "yapay zekanin kotüye kullanim riskleri ve acik kaynak regulasyonlari "
                        "konusundaki tartismalari alevlendirdi."
                    ),
                },
                {
                    "headline": "Robotik Gorme Girisimi Lyte, 165 Milyon Dolar Yatirimla Unicorn Oldu",
                    "key_points": [
                        "1 milyar 600 milyon dolar degerlemeye ulasan girisim robotlara uc boyutlu algi kazandiriyor",
                        "Pahali lidar sensorleri yerine kameralarla calisan model donanim maliyetini yariya indiriyor",
                    ],
                    "summary": (
                        "Insansi robotlarin cevrelerini insan hassasiyetinde algilamasini saglayan gorme yapay "
                        "zekasi sirketi Lyte, 165 milyon dolar yeni fon toplayarak degerlemesini 1 milyar "
                        "600 milyon dolara tasidi."
                    ),
                },
                {
                    "headline": "Anthropic Claude Bilgisayar Kullanimi: Is Akislarinda Otonom Masaustu Donemi",
                    "key_points": [
                        "Model fare ve klavye kullanarak tarayici, form ve dosya islemlerini insan gibi yonetiyor",
                        "Finans ve lojistik sektorunde operasyonel veri girisleri yapay zekaya devrediliyor",
                    ],
                    "summary": (
                        "Anthropic'in Claude modeli, dogrudan bilgisayar ekranini okuyup imleg ve klavye "
                        "hareketleriyle gorevleri tamamlayarak masaustu otomasyonunda yeni bir cigir acti."
                    ),
                },
                {
                    "headline": "The Adecco Group Raporu: Yapay Zeka 1 Milyon 900 Bin Yeni Istihdam Alani Yaratti",
                    "key_points": [
                        "Is kayiplari endisesinin aksine veri mimarliginda ve ajan denetciliginde rekor talep olusту",
                        "Is gucunun teknolojik becerilere uyum saglamasi kuresel buyumenin anahtari olarak vurgulandi",
                    ],
                    "summary": (
                        "Kuresel insan kaynaklari devi Adecco'nun arastirmasi, yapay zekanin var olan meslekleri "
                        "donustururken dunya capinda 1 milyon 900 bin yeni istihdam firsati yaratitigini acikladi."
                    ),
                },
            ],
            "script": (
                "Ahmet: Dunya artik bir soru soruyor: Acik kaynak yapay zeka modelleri kime ait olmali? "
                "Cunku bugun sabah Nvidia, acik kaynak toplulugunun kalbi sayilan Hugging Face'i satin "
                "aldigini resmi olarak dogruladi. Bu haber yapay zeka dunyasinda deprem etkisi yaratti.\n\n"

                "Emel: Ahmet, Hugging Face dusun ki yuz binlerce arastirmacinin, universitenin ve bagimsiz "
                "geliştiricinin modellerini ozgurce paylastigi tarafsiz bir kutuphane gibiydi. Nvidia ise "
                "dunya GPU pazarinin buyuk cogunlugunu elinde tutmakta. Tek bir sirketin hem cipsleri "
                "hem de modellerin dagitim merkezini kontrolunde tutmasi... bu tehlikeli bir tablo degil mi?\n\n"

                "Ahmet: Tehlikeli mi yoksa kacinilmaz mi, tam orada bir anlasmazlik var. Nvidia taraftarlari, "
                "devasa hesaplama altyapisiyla bagimsiz arastirmacilara ucretsiz islem gucu verecegini savunuyor. "
                "Karsi taraf ise Avrupa Birligi'nin ve Amerikan duzeneleyicilerinin bu satin alimi antitrost "
                "yasalari cercevesinde inceleyecegini vurguluyor. Acik kaynak tanim olarak 'bagimsizdir', "
                "ama artik bu bagimsizligi bir donanim devi finanse edecek.\n\n"

                "Emel: Acik kaynak modellerden konuyu kesmeden, Meta cephesinden de geliştiricileri "
                "heyecanlandiran bir duyuru geldi: Muse Spark 1.3 kodlama ajani yayinlandi. "
                "Peki bu model diger kod tamamlama araçlarindan ne ile ayriliyor?\n\n"

                "Ahmet: Muse Spark, geleneksel bir kod tamamlayici gibi yalnizca bir sonraki satiri "
                "onermekle kalmiyor. Tum yazilim deposunu, veritabani sematalarini ve bagimliliklari "
                "tarayarak hatanin kaynagini bulabiliyor; kendi kendine birim testleri yazip duzeltmeyi "
                "gelistiricinin onune bir taslak olarak koyuyor. Saatler suren hata ayiklama sureclerini "
                "dakikalara indirmek iddiasi bu.\n\n"

                "Emel: Yazilim dunyasindaki bu otomasyon dalgasi simdiden korkutucu bir soru doguruyor. "
                "Ama konuyu tamamen degistirmeden once, OpenAI'in Astra modelinden gelen flaş habere gecmeliyiz. "
                "Model akil yurutme kapasitesiyle dikkat cekiyor, ama birlikte ciddi bir guvenlik sorununu "
                "da beraberinde getiriyor.\n\n"

                "Ahmet: Simdi bunu biraz acacak olursak; eski nesil modeller bir soru geldiginde aninda, "
                "istatistiksel en olasilikli yaniti uretiyor. Astra ise karmask matematik veya strateji "
                "problemlerinde durup kendi kendine adim adim dusunuyor, alternatif senaryolari test ediyor. "
                "Buna test ani hesaplama gucu deniyor.\n\n"

                "Emel: Ve tam burada arastirmacilarin endisesi baslıyor. Bu derin mantikyurutme dongusu, "
                "modelin guvenlık filtrelerini kendi basindan asmasina zemin hazirlıyor olabilir mi? "
                "Yani model, 'bu zararlı' diyen filtresiyle ama baska bir mantikyurutme yoluyla "
                "o filtreyi atlatmanin yolunu bulabilir mi?\n\n"

                "Ahmet: Kesin cevap henuz yok, ama bu endise yapay zeka guvenlik camiasinda ciddi bir "
                "arastirma gundemine donustu. Google ise bu guvenlik boslugunu firsata ceviriyor. "
                "Hem genel amacli Gemini Flash modelini hem de sifir gun aciklari ve oltalama saldirilarini "
                "milisaniyelerde tespit eden Flash Cyber modelini ayni hafta icinde tanitti.\n\n"

                "Emel: Flash Cyber'in ilginc yani, dogrudan veri merkezine bagli kalmadan sirket icindeki "
                "yerel sunucularda calisabilmesi. Buyuk kurumlar icin bu muazzam bir avantaj cunku "
                "hassas verileri disariya cikarmadan yapay zeka destekli siber savunma yapabiliyorlar.\n\n"

                "Ahmet: Siber guvenlik konusunu canlı tutarken, bu alanda yapay zeka modellerini savunan "
                "girişim HiddenLayer bugun 100 milyon dolar yatirim aldıgını acikladi. Model zehirleme "
                "saldirilarinı tanımayanlar icin kisa bir aciklama: Bir buyuk dil modelinin egitim verisine "
                "zararli ornekler eklenerek modelin belli konularda yanlis yanit vermesi saglanabiliyor. "
                "HiddenLayer bu tur saldırilara karsi bir kalkani gelistiriyor.\n\n"

                "Emel: Peki o kalkani delmeye calisan bir taraf var mi? Evet, var. Abliteration adli "
                "platform, acik agirlikli modellerden guvenlik filtrelerini cerrahi hassasiyetle "
                "silen bir yontem sunuyor. Teknik olarak, modelin noronlarinda etik kurallari "
                "kodlayan vektor'leri matematiksel olarak sifirliyor.\n\n"

                "Ahmet: Emel, bu noktada ben biraz kararsizim. Bir yanda bilimsel arastirma ozgurlugu "
                "var: Sansursuz bir modele ihtiyac duyan akademisyenler olabilir. Ote yanda ise "
                "bu yontemin kim tarafindan, ne icin kullanilacagi tamamen belirsiz. Siber guvenlik "
                "toplulugunun kuresel bir uyari verdigi bu konuda senin bakis acin ne?\n\n"

                "Emel: Teknik cozumun mevcudiyeti, onu kullanmanin etik oldugu anlamina gelmiyor. "
                "Neyse ki dijital dunya tartisirken, fiziksel dunya da hizla donusuyor. "
                "Robotik gorme girisimi Lyte, bugun 165 milyon dolar yatirimla unicorn statusune yükseldi. "
                "Sirketin gelistirdigi sistem, insansi robotlarin cevresini ucboyutlu olarak "
                "insan hassasiyetinde algilamasini sagliyor.\n\n"

                "Ahmet: Ustelik pahali lidar sensorleri yerine sıradan kameralarla calismasi, "
                "uretim maliyetini yaklasik yariya indiriyor. Bu detay kucuk gibi gorunuyor ama "
                "insansi robotlarin fabrikadan evinize girmesi icin gereken ekonomik esigi "
                "dogrudan etkiliyor.\n\n"

                "Emel: Ve son olarak, Anthropic'in Claude modeli artik sadece sohbet kutusunda degil; "
                "dogrudan bilgisayari yonetiyor. Tarayiciyi aciyor, formlari dolduruyor, "
                "dosya yonetiminde gorev tamamliyor. Finans sektorundeki bazi sirketler halihazirda "
                "rutin veri girisi islerini Claude'a devretmeye basladi.\n\n"

                "Ahmet: Bu da bizi bugunun belki de en buyuk sorusuna gotüruyor. Adecco Group'un "
                "yeni raporu, yapay zekanin surdurdugu donusum surecinde dunya capinda 1 milyon "
                "900 bin yeni is alani ortaya ciktigini gosteriyor. Veri mimarliginda, ajan "
                "denetciliginde ve yapay zeka guvenliginde rekor duzeyinde is talebinden bahsediliyor.\n\n"

                "Emel: Yani en tehlikeli senaryo yapay zekanin is alanlari ortadan kaldirmasi degil, "
                "yeni alanlar acilirken mevcut is gucunun uyum hizinin geri kalmasi olabilir. "
                "Bugunku haberlerden cikartilacak en net ders bu sanırim.\n\n"

                "Ahmet: Peki siz ne dusunuyorsunuz? Yapay zekayla butunlesen is modelleri "
                "gercekten istihdam yaratıyor mu, yoksa bu rakamlar sadece bir iyimserlik mi? "
                "Bu soruyu onunuzde birakiyoruz. Migros OneCast AI'in bugunun bulteni burada son buluyor."
            ),
        }
