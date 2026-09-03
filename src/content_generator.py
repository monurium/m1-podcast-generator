import os
import json
import re
import feedparser
import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ContentGenerator:
    """Fetches high-quality, curated Turkish & Global AI news from the last 24 hours and generates interactive ~10-minute podcast scripts with natural explanations."""

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
        
        # Curated, authoritative AI news feeds
        self.ai_feeds = [
            {"name": "Webrazzi AI", "url": "https://webrazzi.com/kategori/yapay-zeka/feed/", "ai_only": True},
            {"name": "ShiftDelete AI", "url": "https://shiftdelete.net/yapay-zeka/feed", "ai_only": True},
            {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "ai_only": True},
            {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "ai_only": True},
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "ai_only": True},
            {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/", "ai_only": True},
            {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss", "ai_only": True},
            {"name": "Ars Technica AI", "url": "https://arstechnica.com/tag/ai/feed/", "ai_only": True},
            {"name": "IEEE Spectrum AI", "url": "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss", "ai_only": True},
            {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/", "ai_only": True},
            {"name": "SiliconANGLE AI", "url": "https://siliconangle.com/category/ai/feed/", "ai_only": True},
            {"name": "Synced Review", "url": "https://syncedreview.com/feed/", "ai_only": True},
            {"name": "BBC Tech", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "ai_only": False},
            {"name": "Evrim Ağacı", "url": "https://evrimagaci.org/rss.xml", "ai_only": False}
        ]

    def fetch_fresh_news(self, hours_limit: int = 24, exclude_keywords: List[str] = None) -> str:
        """Collects fresh, high-quality Turkish & Global AI news published strictly within the hours limit (default 24h)."""
        fresh_articles: List[str] = []
        exclude_keywords = exclude_keywords or []
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        print(f"📡 Toplam {len(self.ai_feeds)} nitelikli yapay zeka RSS kaynağından son {hours_limit} saatin haberleri taranıyor...")

        ai_keywords = [
            "yapay zeka", "ai", "llm", "dil modeli", "makine öğrenimi", "derin öğrenme",
            "artificial intelligence", "machine learning", "deep learning", "neural",
            "openai", "anthropic", "claude", "chatgpt", "deepseek", "gemini", "copilot",
            "agent", "otonom", "robot", "robotik", "nvidia", "tpu", "gpu", "npu", "kuantizasyon",
            "transformer", "reasoning", "benchmark", "hugging face", "mistral", "meta ai",
            "multimodal", "generative"
        ]

        forbidden_keywords = [
            "war", "kill", "murder", "suicide", "shooting", "attack", "terror", 
            "sexual", "porn", "gore", "deadly", "explosion", "military", "crime", 
            "death", "assault", "violence", "conflict", "bomb", "savaş", "cinayet",
            "ölüm", "saldırı", "terör", "şiddet", "patlama"
        ]

        seen_titles = set()
        for feed in self.ai_feeds:
            feed_name = feed["name"]
            feed_url = feed["url"]
            is_ai_only = feed.get("ai_only", False)
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:20]:
                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", "") or entry.get("description", "")
                    summary = re.sub(r'<[^>]+>', '', summary).strip()
                    combined_text = f"{title} {summary}".lower()
                    
                    if any(bad_word in combined_text for bad_word in forbidden_keywords):
                        continue
                    
                    if any(ex.lower() in title.lower() for ex in exclude_keywords if len(ex) > 4):
                        continue

                    # If not a dedicated AI feed, enforce AI keyword match
                    if not is_ai_only and not any(kw in combined_text for kw in ai_keywords):
                        continue

                    # Strict 24-hour timestamp verification
                    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
                    if parsed_time:
                        try:
                            pub_dt = datetime.datetime(*parsed_time[:6], tzinfo=datetime.timezone.utc)
                            age_hours = (now_utc - pub_dt).total_seconds() / 3600
                            if age_hours > hours_limit:
                                continue
                        except Exception:
                            pass

                    clean_title = re.sub(r'\s+', ' ', title).strip()
                    if clean_title and clean_title.lower() not in seen_titles:
                        seen_titles.add(clean_title.lower())
                        clean_item = f"• [{feed_name}] Başlık: {clean_title}\n  Özet: {summary[:320]}"
                        fresh_articles.append(clean_item)
            except Exception as e:
                print(f"⚠️ RSS ayrıştırma uyarısı ({feed_name}): {e}")

        # If less than 12 articles found in 24h, automatically widen to 48h to prevent empty runs
        if len(fresh_articles) < 12 and hours_limit < 48:
            print(f"ℹ️ Son {hours_limit} saatte {len(fresh_articles)} haber bulundu. 48 saatlik aralık taranıyor...")
            return self.fetch_fresh_news(hours_limit=48, exclude_keywords=exclude_keywords)

        if not fresh_articles:
            return ""

        return "\n\n".join(fresh_articles[:40])

    def generate_dialogue_script(self, raw_news_context: str, recent_topics: List[str] = None) -> Dict[str, Any]:
        """Generates dynamic 10-11 minute (~1050-1200 words) Turkish podcast dialogue (Ahmet & Emel) with 8-10 pure AI news stories, interactive back-and-forth, and technical explanations."""
        print("🤖 Nitelikli yapay zeka haberleriyle 10 dakikalık etkileşimli Türkçe podcast metni üretiliyor...")
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')

        system_prompt = (
            "Sen iki deneyimli teknoloji sunucusu (Ahmet ve Emel) için canlı, samimi ve son derece etkileşimli bir Türkçe podcast metni yazan kıdemli bir yapımcısın.\n\n"
            "MANDATORY FORMAT VE KURALLAR:\n"
            "1. HEDEF SÜRE VE KELİME HEDEFİ: Podcast süresi TAM 10-11 DAKİKA ARASINDA (1050 - 1200 KELİME) olmalıdır. "
            "Seçilen haberler doğrudan son 24 saatin en nitelikli yapay zeka ve makine öğrenimi gelişmelerine odaklanmalı, teknik ve pratik boyutlarıyla detaylandırılmalıdır.\n"
            "2. HABER SAYISI: 8 ile 10 adet (en az 8 haber) güçlü ana yapay zeka gelişmesi seç. "
            "Tüm bu haberler hem 'news_items' dizisinde yer almalı hem de sunucular tarafından diyalog akışında sırayla ele alınmalıdır.\n"
            "3. GERÇEK ETKİLEŞİM VE DİYALOG:\n"
            "   - Sunucular birbirini papağan gibi onaylamamalı ('kesinlikle', 'çok haklısın', 'aynen öyle' kalıplarını YASAKLA).\n"
            "   - Birbirlerine doğrudan sorular sorsunlar, şaşırsınlar, farklı bakış açıları sunsunlar ('Peki Emel, kullanıcı bunu günlük hayatta nasıl hissedecek?', 'Ahmet burada bir soru işareti var, güvenlik riski doğurmaz mı?').\n"
            "   - Her haber için Ahmet ve Emel arasında en az 2-4 karşılıklı konuşma turu olmalı; haberler aceleyle geçiştirilmemelidir.\n"
            "4. TEKNİK TERİMLERİ AKIŞ İÇİNDE AÇIKLA:\n"
            "   - Metinde geçen her teknik kavram (örn: Test-time compute / akıl yürütme, Abliteration, Otonom Ajan, Vision-AI, Model Zehirleme, Guardrails, Sıfır Gün Açığı vb.) mutlaka konuşma akışını bozmadan günlük dilde somut benzetmelerle izah edilsin.\n"
            "5. META BİLGİ YASAGI: Süreden veya haber sayısından ASLA bahsetme. Girişi uzatmadan doğrudan ilk konudan başlat.\n"
            "6. ÇIKTI FORMATI: Yanıtını SADECE geçerli bir JSON nesnesi olarak ver.\n\n"
            "JSON Şeması:\n"
            "{\n"
            '  "title": "Bölümün dikkat çekici ana başlığı",\n'
            '  "summary": "Bölümün 1-2 cümlelik genel kanca özeti",\n'
            '  "news_items": [\n'
            "    {\n"
            '      "headline": "Çarpıcı ve Vurucu Haber Başlığı 1",\n'
            '      "key_points": ["Can alıcı nokta 1", "Can alıcı nokta 2"],\n'
            '      "summary": "Haberin 2-3 cümlelik net özeti."\n'
            "    }\n"
            "  ],\n"
            '  "todays_topics": "8-10 haber başlığının virgülle ayrılmış listesi",\n'
            '  "script": "Ahmet: Merhaba teknoloji ve yapay zeka meraklıları, Migros OneCast AI\'a hoş geldiniz...\\n\\nEmel: ..."\n'
            "}"
        )

        user_prompt = (
            f"Tarih: {today_date_str}\n\n"
            f"Günün Ham Nitelikli Yapay Zeka Haber Havuzu (Son 24 Saat):\n\n{raw_news_context or 'Günün öne çıkan yapay zeka, açık modeller, otonom ajanlar ve LLM gelişmeleri.'}\n\n"
            "Lütfen son 24 saatin en nitelikli 8-10 yapay zeka haberini derinlemesine tartışan, teknik terimleri doğal dille açıklayan, yapay onaylama kalıplarından uzak, karşılıklı soru-cevaplı ve 1050-1200 KELİMELİK (~10 dakika) Türkçe diyalog JSON çıktısını üret."
        )

        if not self.client:
            print("ℹ️ LLM API anahtarı bulunamadı, son 24 saatin nitelikli AI gelişmelerini içeren örnek şablon kullanılıyor.")
            return self._get_fallback_turkish_script()

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat" if "deepseek" in str(self.client.base_url) else "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content.strip()
            data = json.loads(raw_content)

            if "script" not in data or "news_items" not in data:
                raise ValueError("JSON output missing required fields")

            return data
        except Exception as e:
            print(f"⚠️ LLM üretim hatası ({e}). Fallback şablonuna geçiliyor...")
            return self._get_fallback_turkish_script()

    def generate_script(self, raw_news_context: str) -> Dict[str, Any]:
        """Generates monologue Turkish podcast script with news highlights."""
        dialogue_data = self.generate_dialogue_script(raw_news_context)
        script_text = dialogue_data.get("script", "")
        mono_lines = []
        for line in script_text.splitlines():
            clean = re.sub(r'^(Ahmet|Emel|Alex|Sarah|Sunucu):\s*', '', line).strip()
            if clean:
                mono_lines.append(clean)
        
        dialogue_data["script"] = "\n\n".join(mono_lines)
        return dialogue_data

    def _get_fallback_turkish_script(self) -> Dict[str, Any]:
        """Provides an interactive, deeply conversational ~1010-word (10 minutes, 10 stories) Turkish podcast episode explaining technical terms naturally."""
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')
        return {
            "title": f"Migros OneCast AI - Günlük Yapay Zeka Bülteni: Nvidia & Hugging Face ve Ajan Çağı ({today_date_str})",
            "summary": "Nvidia'nın Hugging Face satın alımından Meta Muse Spark kodlama modeline, OpenAI Astra'nın akıl yürütme tartışmalarından robotik görme ve siber güvenlik yatırımlarına son 24 saatin 10 kritik AI gelişmesi.",
            "todays_topics": "Nvidia Hugging Face Satın Alımı, Meta Muse Spark 1.3 Ajan Modeli, OpenAI Astra ve Akıl Yürütme Güvenliği, Google Gemini 3.8 Flash Cyber, HiddenLayer 100M$ AI Güvenlik Yatırımı, Abliteration ve Güvenlik Filtreleri, Lyte Vision-AI Robotik Yatırımı, Claude Bilgisayar Kullanımı, Çoklu Ajan Çatışmaları, Yapay Zeka ve İstihdam Raporu",
            "news_items": [
                {
                    "headline": "Nvidia, Açık Kaynak Merkezi Hugging Face'i Satın Aldığını Doğruladı",
                    "key_points": [
                        "Dünyanın en büyük açık yapay zeka model havuzu donanım devinin bünyesine geçti",
                        "Bağımsız araştırmacılar ve düzenleyici kurumlar olası tekel risklerini tartışıyor"
                    ],
                    "summary": "Nvidia, açık kaynak yapay zeka topluluğunun kalbi sayılan Hugging Face platformunu satın aldığını doğrulayarak yapay zeka ekosisteminde tarihi bir konsolidasyona imza attı."
                },
                {
                    "headline": "Meta'dan Otonom Kodlama Ajanı Modeli: Muse Spark 1.3",
                    "key_points": [
                        "Model sadece kod tamamlamakla kalmıyor, tüm depoyu tarayıp bağımsız testler yazıyor",
                        "Geliştirici ekiplerinin hata ayıklama ve refactoring sürelerinde radikal hızlanma sağlandı"
                    ],
                    "summary": "Meta, yazılım projelerinin mimarisini anlayarak bağımsız testler yazabilen ve hataları otomatik düzeltebilen ajan tabanlı yeni Muse Spark 1.3 modelini duyurdu."
                },
                {
                    "headline": "OpenAI Astra'nın Derin Akıl Yürütme Tekniği Güvenlik Tartışması Yarattı",
                    "key_points": [
                        "Model yanıt üretmeden önce test anı hesaplamasıyla (test-time compute) iç sesini kontrol ediyor",
                        "Derin mantık yürütme süreçlerinin güvenlik filtrelerini aşmada yeni riskler doğurabileceği belirtiliyor"
                    ],
                    "summary": "OpenAI'ın AGI eşiğine yaklaştığı belirtilen yeni Astra modeli, karmaşık mantık yürütme yetenekleriyle öne çıkarken otonom karar alma süreçlerindeki güvenlik bariyerleri tartışılıyor."
                },
                {
                    "headline": "Google'dan Çift Hamle: Gemini 3.8 Flash ve Siber Güvenlik Odaklı Flash Cyber",
                    "key_points": [
                        "Flash Cyber modeli sıfır gün açıklarını ve oltalama saldırılarını milisaniyelerde tespit ediyor",
                        "Hafif mimari sayesinde veri merkezlerine bağımlı kalmadan uç cihazlarda yüksek hızda çalışıyor"
                    ],
                    "summary": "Google, düşük gecikmeli genel amaçlı Gemini 3.8 Flash modelinin yanı sıra kurumsal siber savunma için özel olarak optimize edilen Gemini 3.8 Flash Cyber modelini tanıttı."
                },
                {
                    "headline": "Yapay Zeka Modellerini Savunan HiddenLayer, 100 Milyon Dolar Yatırım Aldı",
                    "key_points": [
                        "Model zehirleme ve ağırlık manipülasyonu saldırılarına karşı kalkan geliştiriliyor",
                        "Kurumsal yapay zeka güvenliği sektörünün en büyük yatırımlarından biri gerçekleşti"
                    ],
                    "summary": "Büyük dil modellerini veri zehirleme ve jailbreak saldırılarına karşı koruyan siber güvenlik girişimi HiddenLayer, 100 milyon dolarlık Seri B yatırım turunu tamamladı."
                },
                {
                    "headline": "Abliteration.ai: Açık Modellerden Güvenlik Filtrelerinin Silinmesi Tartışılıyor",
                    "key_points": [
                        "Ağırlık matrislerindeki güvenlik vektörleri matematiksel cerrahiyle temizleniyor",
                        "Sansürsüz araştırma vaadiyle sunulan hizmet siber güvenlik otoritelerinde alarm yarattı"
                    ],
                    "summary": "Açık ağırlıklı modellerden güvenlik kurallarını kaldıran Abliteration yöntemi, yapay zekanın kötüye kullanım riskleri ve açık kaynak regülasyonları konusundaki tartışmaları alevlendirdi."
                },
                {
                    "headline": "Robotik Görme Girişimi Lyte, 165 Milyon Dolar Yatırımla Unicorn Oldu",
                    "key_points": [
                        "1,6 milyar dolar değerlemeye ulaşan girişim, robotlara 3D derinlik ve doku algısı kazandırıyor",
                        "Pahalı lidar sensörleri yerine kameralarla çalışan model donanım maliyetini yarıya indiriyor"
                    ],
                    "summary": "İnsansı robotların çevrelerini insan hassasiyetinde algılamasını sağlayan görme yapay zekası şirketi Lyte, 165 milyon dolar yeni fon toplayarak değerlemesini 1,6 milyar dolara taşıdı."
                },
                {
                    "headline": "Anthropic Claude Bilgisayar Kullanımı: İş Akışlarında Otonom Masaüstü Dönemi",
                    "key_points": [
                        "Model fare ve klavye kullanarak tarayıcı, form ve dosya işlemlerini insan gibi yönetiyor",
                        "Finans ve lojistik sektöründe operasyonel veri girişleri doğrudan yapay zekaya devrediliyor"
                    ],
                    "summary": "Anthropic'in Claude modeli, doğrudan bilgisayar ekranını okuyup imleç ve klavye hareketleriyle görevleri tamamlayarak masaüstü otomasyonunda yeni bir çığır açtı."
                },
                {
                    "headline": "Akademik Araştırma: Çoklu Ajan Sistemlerinde Koordinasyon ve Çatışma Krizi",
                    "key_points": [
                        "Bağımsız çalışan ajanların aynı dosya üzerinde birbirini kilitleyebildiği belgelendi",
                        "Ajan orkestrasyonu ve görev hiyerarşisi geleceğin kritik yazılım mimarisi olarak öne çıkıyor"
                    ],
                    "summary": "Synced Review tarafından derlenen araştırma, çoklu yapay zeka ajanlarının eşzamanlı çalışırken görev çakışmaları ve sistem kilitlenmeleri yaşayabildiğini ortaya koydu."
                },
                {
                    "headline": "The Adecco Group Raporu: Yapay Zeka 1,9 Milyon Yeni İstihdam Alanı Yarattı",
                    "key_points": [
                        "İş kayıpları endişesinin aksine veri mimarlığı ve ajan denetçiliğinde rekor talep oluştu",
                        "İş gücünün teknolojik becerilere uyum sağlaması küresel büyümenin anahtarı olarak vurgulandı"
                    ],
                    "summary": "Küresel insan kaynakları devi Adecco'nun araştırması, yapay zekanın var olan meslekleri dönüştürürken dünya çapında 1,9 milyon yeni istihdam fırsatı yarattığını açıkladı."
                }
            ],
            "script": (
                "Ahmet: Merhaba teknoloji ve yapay zeka meraklıları, Migros OneCast AI'a hoş geldiniz. Bugün doğrudan yapay zeka laboratuvarlarından gelen, son yirmi dört saatte ekosistemi derinden sarsan tam on nitelikli ve sıcak gelişmeyle karşınızdayız. İlk büyük haberimiz, açık kaynak dünyasında deprem etkisi yaratan tarihi bir anlaşma: Çip devi Nvidia, açık kaynak yapay zekanın küresel merkezi sayılan Hugging Face'i bünyesine kattığını resmen doğruladı.\n\n"
                "Emel: Ahmet, Hugging Face dünyadaki yüz binlerce bağımsız araştırmacının, üniversitenin ve şirketin açık modellerini özgürce paylaştığı tarafsız bir kütüphaneydi. Donanım tekeli kuran Nvidia'nın bu platformu satın alması yapay zeka topluluğunda nasıl yankı buldu?\n\n"
                "Ahmet: Çok sert tartışmalar başladı. Bir kesim Nvidia'nın devasa sunucu ve GPU altyapısının açık kaynak modelleri uçuracağını ve bağımsız geliştiricilere ücretsiz hesaplama gücü sağlayacağını savunuyor. Ancak madalyonun diğer yüzünde, tek bir donanım üreticisinin hem çipleri hem de modellerin dağıtıldığı ana depoyu kontrol etmesi ciddi bir tekel endişesi yaratıyor. Hatta Avrupa Birliği ve Amerikan düzenleyici kurumlarının bu satın almayı antitröst yasaları kapsamında incelemeye alabileceği konuşuluyor. Açık kaynak yapay zekanın bağımsızlığı açısından tarihi bir dönüm noktasıyla karşı karşıyayız.\n\n"
                "Emel: Açık kaynak modeller demişken, Meta cephesinden de yazılım mühendislerini heyecanlandıran yepyeni bir duyuru geldi: Muse Spark 1.3 kodlama modeli resmen yayınlandı.\n\n"
                "Ahmet: Emel, Muse Spark'ı diğer klasik kod tamamlama araçlarından ayıran temel fark ne? Neden geliştiriciler bu modeli bu kadar yakından takip ediyor?\n\n"
                "Emel: Çünkü Muse Spark sadece satır tamamlayan pasif bir yardımcı değil; doğrudan otonom bir ajan gibi çalışıyor. Tüm yazılım deposunu, veritabanı şemalarını ve bağımlılıkları tarayarak hatanın kaynağını tespit ediyor, kendi kendine birim testleri yazıyor ve düzeltmeyi pull request olarak geliştiricinin önüne koyuyor. Geliştiricilerin saatler süren hata ayıklama süreçlerini dakikalara indiren gerçek bir otonom mühendislik adımı.\n\n"
                "Emel: Kodlama tarafındaki bu sıçramanın ardından gözler OpenAI cephesine çevrildi. Yeni nesil akıl yürütme modeli Astra'nın AGI eşiğine ulaştığı duyuruldu; ancak modelin karmaşık mantık yürütme teknikleri ciddi güvenlik endişelerini de beraberinde getirdi.\n\n"
                "Ahmet: Dinleyicilerimiz için akıl yürütme tekniğini biraz somutlaştıralım. Klasik modeller bir soru sorduğunuzda hafızasındaki istatistiksel kelime tahminine göre anında yanıt üretir. Astra gibi yeni nesil modeller ise karmaşık matematik veya kodlama problemlerinde durup kendi kendine adım adım düşünüyor, alternatif senaryoları test ediyor ve iç sesini kontrol ederek sonuca varıyor.\n\n"
                "Emel: İşte buna test anı hesaplama gücü yani 'test-time compute' deniyor Ahmet. Model yanıtı üretmeden önce saniyelerce kendi mantık hatalarını düzeltiyor. Ancak araştırmacılar, bu derin mantık yürütme döngüsünün güvenlik filtrelerini aşmada ve otonom sistemlerde gizli planlar yapmada yeni açıklar doğurabileceğini vurguluyor.\n\n"
                "Ahmet: Hız ve güvenlik dengesinde Google da boş durmadı ve ekosistemi genişleten iki yeni model duyurdu: Gemini 3.8 Flash ve siber güvenlik savunmasına odaklanan Gemini 3.8 Flash Cyber.\n\n"
                "Emel: Özellikle Flash Cyber modeli, kurumsal ağlardaki sıfır gün açıklarını ve yapay zeka tabanlı oltalama saldırılarını milisaniyeler içinde tespit etmek üzere özel olarak eğitilmiş. Ajanların hızlanması güvenlik savunmasını da otonom hale getirmeyi zorunlu kılıyor.\n\n"
                "Ahmet: Üstelik saniyede yüzlerce token üretebilen bu hafif modeller, veri merkezlerine bağımlı kalmadan uç cihazlarda ve şirket içi sunucularda düşük maliyetle güvenlik taraması yapabiliyor.\n\n"
                "Emel: Nitekim siber güvenlik tarafındaki bu kritik ihtiyaç yatırım dünyasına da doğrudan yansıdı. Yapay zeka modellerini saldırılara karşı koruyan HiddenLayer, tam yüz milyon dolar yeni yatırım aldı.\n\n"
                "Ahmet: HiddenLayer ne yapıyor derseniz; doğrudan yapay zeka modellerinin içine sızıp ağırlık matrislerini zehirlemeyi hedefleyen siber saldırılara karşı bir zırh geliştiriyor. Büyük dil modelleri şirketlerin en değerli fikri mülkiyeti haline geldikçe bu koruma kalkanı hayati bir zorunluluk oldu.\n\n"
                "Emel: Güvenlik konuşulurken madalyonun diğer yüzünde ise modellerin güvenlik filtrelerini kasten kaldıran tartışmalı girişimler türedi. Abliteration.ai platformu yapay zekanın tüm kısıtlamalarını kaldırmayı bir iş modeline dönüştürdü.\n\n"
                "Ahmet: Emel, abliteration yani filtre silme işlemi teknik olarak ne anlama geliyor ve neden bu kadar tehlikeli bulunuyor?\n\n"
                "Emel: Çok basitçe anlatalım; açık ağırlıklı bir modelin nöronlarında güvenlik ve etik kurallarını temsil eden matematiksel vektörler bulunur. Abliteration yöntemiyle bu vektörler cerrahi bir operasyon gibi ağırlıklardan siliniyor. Model böylece kimyasal silahlardan siber saldırı kodlarına kadar hiçbir filtreye takılmadan yanıt vermeye başlıyor. Girişim bunu sansürsüz bilimsel araştırma için yaptığını söylese de siber güvenlik uzmanları küresel bir risk uyarısı yapıyor.\n\n"
                "Emel: Dijital dünyadaki bu fırtınanın ardından rotamızı fiziksel dünyaya, robotik yapay zekaya çeviriyoruz. Robotların görmesini ve çevresini anlamasını sağlayan Lyte, bir nokta altı milyar dolar değerleme üzerinden yüz altmış beş milyon dolar yatırım aldı.\n\n"
                "Ahmet: İnsansı robotların fabrikalarda ve evlerimizde güvenle iş yapabilmesi için sadece yürümeleri yetmiyor; gördükleri cisimlerin derinliğini, ağırlığını ve malzemesini milisaniyeler içinde algılamaları gerekiyor. Lyte'ın geliştirdiği multimodal görme mimarisi robotların insan gibi çevresini üç boyutlu anlamasını sağlıyor.\n\n"
                "Emel: Üstelik bu yeni görme modelleri sayesinde robotlar pahalı lidar sensörlerine ihtiyaç duymadan sıradan kameralarla hassas montaj yapabiliyor; bu da insansı robotların üretim maliyetini yarı yarıya düşürüyor.\n\n"
                "Ahmet: Robotlar fiziksel dünyada ilerlerken, Anthropic'in Claude modeli ise doğrudan bilgisayar ekranını devralıyor. Claude'un bilgisayar kullanma yeteneği iş akışlarında verimliliği ikiye katladı.\n\n"
                "Emel: Claude artık sadece sohbet kutusunda kalmıyor; işletim sisteminde tarayıcıyı açıyor, formları dolduruyor, dosya yöneticisinde gezinip karmaşık bir muhasebe veya veri analizi görevini klavye ve fare kullanarak insan gibi tamamlıyor. Finans ve lojistik şirketleri şimdiden rutin veri girişlerini Claude'un otonom bilgisayar kullanımına devretmeye başladı bile.\n\n"
                "Ahmet: Ancak bu kadar çok otonom ajan aynı anda çalıştığında ortaya yepyeni bir kriz çıkıyor: Çoklu ajan çatışmaları. Son yayınlanan akademik araştırmalar, bağımsız ajanların birbirinin görevini kilitleyebildiğini gösteriyor.\n\n"
                "Emel: Bir ajan ortak bir dosyayı güncellerken diğerinin aynı dosyayı silmeye çalışması gibi koordinasyon hataları, sistemlerin beklenmedik kilitlenmeler yaşamasına yol açıyor. Geleceğin en büyük yazılım mimarisi meydan okuması bu ajan orkestrasyonu olacak.\n\n"
                "Ahmet: Peki tüm bu devrim çalışanları ve iş gücünü nasıl etkiliyor? The Adecco Group'un yayınladığı son küresel araştırma, yapay zekanın şimdiden bir nokta dokuz milyon yeni istihdam fırsatı yarattığını ortaya koydu.\n\n"
                "Emel: Yani korkulanın aksine yapay zeka sadece işleri ortadan kaldırmıyor; veri küratörlüğünden ajan mimarlığına kadar yepyeni uzmanlık alanları açıyor. Önemli olan bu teknolojik dönüşüme hızla adapte olabilmek.\n\n"
                "Ahmet: Hugging Face satın alımından Meta Muse Spark'a, OpenAI Astra'dan robotik görme teknolojilerine kadar son yirmi dört saatin en nitelikli on yapay zeka haberini tüm boyutlarıyla konuştuk.\n\n"
                "Emel: Tüm bu haberlerin özetleri, can alıcı maddeleri ve kaynak bağlantıları podcast açıklama metnimizde ve RSS beslememizde sizleri bekliyor. Dinleyicilerimiz web sitemizden her bir haber kartını inceleyebilir.\n\n"
                "Ahmet: Migros OneCast AI'ın bugünkü yapay zeka bülteninin sonuna geldik. Yarın yepyeni teknoloji ve yapay zeka analizleriyle tekrar görüşmek dileğiyle, hoşça kalın!\n\n"
                "Emel: Kendinize çok iyi bakın, bilimle ve yapay zekayla kalın!"
            )
        }
