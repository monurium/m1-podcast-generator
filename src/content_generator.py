import os
import json
import re
import feedparser
import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ContentGenerator:
    """Fetches latest Turkish & Global tech news and generates 10-minute 7-8 news story podcast scripts with striking headlines and summaries."""

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
            "https://webrazzi.com/feed/",
            "https://shiftdelete.net/feed",
            "https://www.chip.com.tr/rss/",
            "https://www.donanimhaber.com/rss/tum/",
            "https://evrimagaci.org/rss.xml",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://arstechnica.com/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.wired.com/feed/category/business/latest/rss",
            "https://feeds.bbci.co.uk/news/technology/rss.xml"
        ]

    def fetch_fresh_news(self, hours_limit: int = 24, exclude_keywords: List[str] = None) -> str:
        """Collects fresh Turkish & Global AI & Tech news entries."""
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
                for entry in parsed.entries[:10]:
                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", "") or entry.get("description", "")
                    summary = re.sub(r'<[^>]+>', '', summary).strip()
                    combined_text = f"{title} {summary}".lower()
                    
                    if any(bad_word in combined_text for bad_word in forbidden_keywords):
                        continue
                    
                    if any(ex.lower() in title.lower() for ex in exclude_keywords if len(ex) > 4):
                        continue

                    if title and title.lower() not in seen_titles:
                        seen_titles.add(title.lower())
                        clean_item = f"• Başlık: {title}\n  Özet: {summary[:350]}"
                        fresh_articles.append(clean_item)
            except Exception as e:
                print(f"⚠️ RSS ayrıştırma uyarısı ({feed_url}): {e}")

        if not fresh_articles:
            return ""

        return "\n\n".join(fresh_articles[:25])

    def generate_dialogue_script(self, raw_news_context: str, recent_topics: List[str] = None) -> Dict[str, Any]:
        """Generates 10-minute 7-8 story Turkish podcast dialogue (Ahmet & Emel) with striking headlines & summaries."""
        print("🤖 Türkçe 2-Sunuculu (Ahmet & Emel) 10 dakikalık (7-8 Başlıca Haber) podcast metni üretiliyor...")
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')

        system_prompt = (
            "Sen profesyonel, samimi, dinamik ve bilgili bir teknoloji podcast yapımcısısın.\n"
            "Görevin: Günün teknoloji ve yapay zeka gündemini kapsayan, TAM 7 VEYA 8 ADET BAŞLICA HABER içeren, "
            "yaklaşık 10 DAKİKA (1400-1600 KELİME) sürecek dinamik bir Türkçe podcast diyalog metni (Ahmet ve Emel) "
            "ve her haber için çarpıcı başlıklar/özetler hazırlamaktır.\n\n"
            "MANDATORY KURALLAR:\n"
            "1. HABER SAYISI: Kesinlikle 7 veya 8 farklı başlıca haberi ele al. Her haberi yüzeysel geçme; arka planını, "
            "teknolojik önemini, sektöre ve kullanıcılara etkisini Ahmet ve Emel'in karşılıklı paslaşmalarıyla detaylandır.\n"
            "2. HEDEF KELİME UZUNLUĞU: Script metni KESİNLİKLE 1400 İLE 1600 KELİME ARASINDA OLMALIDIR (10 dakikalık konuşma süresi).\n"
            "3. SUNUCU ROLLERİ:\n"
            "   - 'Ahmet:' (Analitik, vizyoner, teknolojinin perde arkasını ve mimarisini aktaran erkek sunucu)\n"
            "   - 'Emel:' (Meraklı, dinamik, sorular soran, kullanıcı deneyimini ve pratik sonuçları sorgulayan kadın sunucu)\n"
            "4. DİL & TON: %100 akıcı, doğal, samimi Türkçe. Diyaloglar yapay hissettirmemeli, radyo/podcast doğallığında olmalı.\n"
            "5. ÇARPICI HABER ÖZETLERİ: `news_items` listesinde tam 7-8 haber nesnesi bulunmalı. Her haber için `headline` (çarpıcı başlık), "
            "`key_points` (2-3 can alıcı nokta) ve `summary` (2-3 cümlelik net özet) eksiksiz girilmeli.\n"
            "6. ÇIKTI FORMATI: Yanıtını SADECE geçerli bir JSON nesnesi olarak ver. Başka hiçbir markdown veya açıklama ekleme.\n\n"
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
            '  "todays_topics": "7-8 haber başlığının virgülle ayrılmış kısa listesi",\n'
            '  "script": "Ahmet: Merhaba teknoloji meraklıları! M1 Podcast\'e hepiniz hoş geldiniz...\\n\\nEmel: Evet Ahmet..."\n'
            "}"
        )

        user_prompt = (
            f"Tarih: {today_date_str}\n\n"
            f"Günün Ham Teknoloji & Yapay Zeka Haber Havuzu:\n\n{raw_news_context or 'Günün 7-8 öne çıkan yapay zeka, yazılım, donanım ve teknoloji gelişmeleri.'}\n\n"
            "Lütfen 7-8 haberi kapsayan, 1400-1600 kelimelik (~10 dakika) zengin diyalog metnini ve structured JSON çıktısını üret."
        )

        if not self.client:
            print("ℹ️ LLM API anahtarı bulunamadı, 7-8 haberli 10 dakikalık zengin Türkçe örnek podcast şablonu kullanılıyor.")
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

            if "script" not in data or "news_items" not in data:
                raise ValueError("JSON output missing required fields")

            return data
        except Exception as e:
            print(f"⚠️ LLM üretim hatası ({e}). Fallback şablonuna geçiliyor...")
            return self._get_fallback_turkish_script()

    def generate_script(self, raw_news_context: str) -> Dict[str, Any]:
        """Generates monologue Turkish podcast script with 7-8 news highlights."""
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
        """Provides a complete ~10-minute (1450+ words) 8-story Turkish podcast episode with striking headlines & summaries."""
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')
        return {
            "title": f"M1 Podcast - Günlük Teknoloji & Yapay Zeka Bülteni ({today_date_str})",
            "summary": "Otonom yazılım ajanlarından kuantum işlemcilere, açık kaynak modellerden robotik vizyona günün en sıcak 8 büyük teknoloji gelişmesi ve derinlemesine 10 dakikalık analizleri.",
            "todays_topics": "Otonom AI Mühendisleri, Açık Kaynak LLM Devrimi, Nöromorfik Çipler, İnsansı Robotlar, Kuantum Dayanıklı Şifreleme, Yeni Nesil Tarayıcı Motorları, Uzay Tabanlı Veri Merkezleri, Yapay Zeka Destekli Biyoteknoloji",
            "news_items": [
                {
                    "headline": "Otonom Yazılım Ajanları: Kod Yazımından Canlıya Alma Sürecine Tam Otomasyon",
                    "key_points": [
                        "Yapay zeka modelleri artık hata ayıklamadan deploy aşamasına kadar tüm döngüyü bağımsız yönetiyor",
                        "Geliştirici ekiplerinin hata çözme süresinde %45 kısalma kaydedildi"
                    ],
                    "summary": "Yeni nesil otonom kodlama ajanları, karmaşık kurumsal projelerin kod tabanını analiz ederek bağımsız birim testleri yazabiliyor ve güvenlik açıklarını otomatik kapatıyor."
                },
                {
                    "headline": "Açık Kaynak Modellerde Devrim: Yerel Cihazlarda GPT-4 Seviyesinde Akıl Yürütme",
                    "key_points": [
                        "Dizüstü bilgisayarlarda çalışan optimize küçük modeller kapalı sistemlere kafa tutuyor",
                        "Veri gizliliği ve yerel işlem önceliği şirketlerin açık kaynağa ilgisini ikiye katladı"
                    ],
                    "summary": "Son yayınlanan açık ağırlıklı modeller, yüksek kuantizasyon verimliliği sayesinde bulut sunucularına bağlanmadan güçlü mantık yürütme imkanı sunuyor."
                },
                {
                    "headline": "Nöromorfik Çip Mimarileri: Enerji Tüketiminde 10 Kat Verimlilik",
                    "key_points": [
                        "İnsan beyninin sinaps yapısını taklit eden yeni donanım mimarileri tanıtıldı",
                        "Yapay zeka veri merkezlerinin yüksek elektrik tüketimine sürdürülebilir çözüm"
                    ],
                    "summary": "Donanım üreticileri, derin öğrenme modellerini mikrosaniye seviyesinde gecikmeyle ve onda bir enerjiyle çalıştıran yeni nöromorfik işlemcilerini duyurdu."
                },
                {
                    "headline": "İnsansı Robotlarda Vizyon ve Hareket Uyumu: Fabrikalardan Günlük Yaşama",
                    "key_points": [
                        "Gelişmiş multimodal görsel modellerle robotlar çevrelerini 3 boyutlu olarak anlık haritalandırıyor",
                        "Otomotiv ve lojistik tesislerinde ilk otonom pilot testleri başladı"
                    ],
                    "summary": "Yeni insansı robot modelleri, uçtan uca sinir ağları sayesinde insan hareketlerini taklit ederek karmaşık montaj ve taşıma görevlerini hatasız tamamlayabiliyor."
                },
                {
                    "headline": "Kuantum Sonrası Kriptografi (PQC): Siber Güvenlikte Yeni Küresel Standartlar",
                    "key_points": [
                        "Kuantum bilgisayarların mevcut şifreleme algoritmalarını kırma riskine karşı yeni protokoller onaylandı",
                        "Bankacılık ve kamu altyapıları kuantum dayanıklı şifrelemeye geçişe başladı"
                    ],
                    "summary": "Uluslararası siber güvenlik otoriteleri, kuantum tehditlerine karşı geliştirilen yeni matematiksel kafes tabanlı şifreleme standartlarını resmi olarak yürürlüğe koydu."
                },
                {
                    "headline": "Yeni Nesil Yapay Zeka Destekli Web Motorları: Tarayıcı Deneyimi Yeniden Tanımlanıyor",
                    "key_points": [
                        "Statik arama sonuçları yerine kişiselleştirilmiş, sentezlenmiş bilgi panelleri",
                        "Kullanıcı adına web formlarını dolduran ve bilet alan otonom tarayıcı asistanları"
                    ],
                    "summary": "Web tarayıcıları, entegre yerel modeller sayesinde kullanıcıların gezindiği sayfaları anlık olarak özetleyen ve karmaşık çok adımlı araştırmaları otomatik tamamlayan akıllı arayüzlere dönüşüyor."
                },
                {
                    "headline": "Yörüngede Veri Merkezleri: Güneş Enerjisiyle Çalışan Uzay Bilişim Projeleri",
                    "key_points": [
                        "Güneş enerjisini kesintisiz kullanan uydu tabanlı veri işleme modülleri test edildi",
                        "Yerküredeki su ve soğutma kaynaklarına olan baskıyı hafifletme hedefi"
                    ],
                    "summary": "Uzay teknolojisi girişimleri, yörüngede doğrudan güneş ışığından güç alan ve soğutma maliyeti sıfıra yakın olan modüler yapay zeka işlem merkezlerini uzaya fırlattı."
                },
                {
                    "headline": "Yapay Zeka Destekli Biyoteknoloji: Protein Tasarımı ve Hızlı İlaç Keşfi",
                    "key_points": [
                        "Aylar süren moleküler simülasyonlar saatler seviyesine indirildi",
                        "Hedefe yönelik kişiselleştirilmiş tedavi yöntemlerinde klinik aşamaya geçildi"
                    ],
                    "summary": "Biyoteknoloji laboratuvarları, generatif yapay zeka kullanarak sentetik protein yapıları tasarladı ve nadir hastalıkların tedavisinde kritik aday moleküller keşfetti."
                }
            ],
            "script": (
                "Ahmet: Merhaba değerli teknoloji ve yapay zeka meraklıları! M1 Podcast'in yeni bölümüne hepiniz hoş geldiniz. Bugün gerçekten dopdolu bir bülten hazırladık. Yazılım dünyasından donanıma, insansı robotlardan uzay bilişimine kadar tam sekiz büyük ve çarpıcı başlığı ayrıntılarıyla masaya yatıracağız.\n\n"
                "Emel: Merhaba herkese! Ben de çok heyecanlıyım Ahmet. Çünkü bugün konuşacağımız her bir başlık, teknolojinin sadece geleceğini değil, doğrudan bugünümüzü nasıl şekillendirdiğini gösteriyor. Dinleyicilerimiz arkalarına yaslansın, yaklaşık on dakikalık harika bir teknoloji yolculuğuna çıkıyoruz. İlk haberimizle başlayalım istersen!\n\n"
                "Ahmet: Harika bir başlangıç noktası Emel. İlk ve belki de en çok ses getiren haberimiz: Otonom Yazılım Ajanları. Bugüne kadar yapay zekayı sadece kod tamamlama veya fonksiyon yazma gibi yardımcı rollerde görüyorduk. Ancak yeni yayınlanan bağımsız benchmark raporlarına göre, artık projenin mimarisini baştan sona anlayan, güvenlik açıklarını tarayan, birim testleri yazıp sistemi canlı ortama kadar taşıyan tam teşekküllü otonom yazılım ajanları devri başladı. Yapılan testlerde ekiplerin hata çözme süresinde yüzde kırk beşe varan bir hızlanma ölçüldü.\n\n"
                "Emel: Bu rakam inanılmaz Ahmet. Düşünsenize, gece siz uyurken projenizdeki bir bellek sızıntısını veya performans darboğazını fark eden ajan, ilgili kodu düzeltiyor, testlerini koşuyor ve sabah önünüze onaylanmaya hazır bir çekme isteği olarak sunuyor. Bu durum yazılımcıların işini ellerinden almaktan ziyade, onları satır satır rutin kod yazmaktan kurtarıp gerçek bir sistem mimarı ve stratejist konumuna yükseltiyor.\n\n"
                "Ahmet: Kesinlikle çok doğru bir tespit Emel. Rutin angaryadan kurtulan yazılımcılar daha yaratıcı ürünler geliştirebilecek. İkinci büyük haberimiz ise açık kaynak dünyasındaki büyük devrim. Son dönemde yayınlanan açık ağırlıklı dil modelleri, artık devasa sunucu çiftliklerine ihtiyaç duymadan doğrudan dizüstü bilgisayarlarda veya yerel iş istasyonlarında GPT-4 seviyesinde akıl yürütme performansı sunabiliyor. Kuantizasyon teknikleri ve optimize ağırlık mimarileri sayesinde kaynak tüketimi yarı yarıya düştü.\n\n"
                "Emel: Bu gelişmenin şirketler açısından anlamı çok büyük. Özellikle bankacılık, sağlık ve hukuk gibi hassas veriyle çalışan sektörler, verilerini buluta göndermek zorunda kalmadan kurum içinde yüzde yüz gizlilikle kendi yapay zeka altyapılarını çalıştırabilecek. Veri egemenliği kavramı bu sayede gerçek bir temele oturuyor.\n\n"
                "Ahmet: Çok haklısın Emel. Üçüncü haberimiz ise donanım dünyasındaki en kritik konulardan birine, yani enerji tüketimine odaklanıyor: Yeni nesil nöromorfik çipler. Biliyorsunuz, geleneksel ekran kartları ve GPU'lar yapay zekayı çalıştırırken devasa miktarda elektrik tüketiyor. Yeni tanıtılan nöromorfik mimariler ise insan beynindeki biyolojik nöron ve sinapsların çalışma prensibini taklit ederek bilgiyi olay tabanlı işliyor. Bu sayede enerji tüketiminde tam on kat verimlilik sağlanırken, işlem gecikmesi mikrosaniyeler seviyesine iniyor.\n\n"
                "Emel: Veri merkezlerinin soğutma ve elektrik maliyetlerinin küresel boyutta tartışıldığı bu dönemde nöromorfik işlemciler adeta can simidi olacak. Ayrıca akıllı saatler, dronlar ve otonom araçlar gibi pil ömrünün hayati olduğu uç cihazlarda yapay zekayı kesintisiz çalıştırmanın önünü açacak. Peki dördüncü başlığımız olan robotik tarafında neler oluyor Ahmet?\n\n"
                "Ahmet: İşte dördüncü ve en heyecan verici haberimiz: İnsansı robotlarda vizyon ve hareket uyumu. Yeni nesil multimodal görsel modeller sayesinde insansı robotlar artık sadece önceden tanımlanmış mekanik hareketleri yapmıyor. Çevrelerini üç boyutlu olarak anlık haritalandırıyor, insan hareketlerini izleyerek öğreniyor ve karmaşık montaj görevlerini hatasız tamamlayabiliyor. Hatta küresel otomotiv üreticileri fabrikalarındaki lojistik ve montaj hatlarında ilk resmi pilot testleri başlattı bile.\n\n"
                "Emel: Bilim kurgu filmlerinde gördüğümüz o sahneler artık fabrikalarda gerçeğe dönüşüyor Ahmet. Robotların insanlarla yan yana, güvenli bir şekilde ağır ve tehlikeli işleri üstlenmesi hem iş güvenliğini artıracak hem de üretim kapasitesini katlayacak. Beşinci başlığımız ise tüm bu dijital dünyanın görünmez kalkanı olan siber güvenlikle ilgili, değil mi?\n\n"
                "Ahmet: Evet Emel, beşinci haberimiz kuantum sonrası kriptografi, yani PQC standartları. Kuantum bilgisayarların hızla gelişmesiyle birlikte, şu an kullandığımız RSA ve eliptik eğri gibi geleneksel şifreleme yöntemlerinin kırılma riski ortaya çıkmıştı. Uluslararası siber güvenlik otoriteleri bu tehdidi bertaraf etmek amacıyla kuantum bilgisayarların bile çözemeyeceği matematiksel kafes tabanlı yeni şifreleme algoritmalarını onayladı ve küresel bankacılık altyapıları şimdiden geçiş sürecine başladı.\n\n"
                "Emel: Geleceğin kuantum tehditlerine bugünden proaktif önlem almak kritik önem taşıyor. Çünkü aksi halde geçmişte kaydedilen şifreli verilerin gelecekte kuantum makinelerle çözülmesi büyük bir güvenlik açığı yaratabilirdi. Altıncı haberimize gelirsek, günlük hayatımızda her an kullandığımız web tarayıcıları köklü bir kabuk değişimine gidiyor Ahmet.\n\n"
                "Ahmet: Kesinlikle öyle Emel. Altıncı haberimiz: Yapay zeka destekli yeni nesil web motorları. Artık bir arama motoruna girdiğinizde onlarca mavi link arasında kaybolmak zorunda kalmıyorsunuz. Tarayıcıya entegre yerel modeller gezindiğiniz web sayfalarını anlık olarak sentezliyor, karşılaştırmalı tablolar çıkarıyor ve hatta sizin adınıza form doldurma veya rezervasyon yapma gibi çok adımlı görevleri otonom olarak tamamlayabiliyor.\n\n"
                "Emel: Web tarayıcıları sadece statik içerik görüntüleyen pencereler olmaktan çıkıp kişisel bir dijital asistana dönüşüyor. Bu da internette bilgiye ulaşma hızımızı katbekat artırıyor. Yedinci başlığımız ise sınırları yerkürenin ötesine taşıyor: Uzay tabanlı veri merkezleri!\n\n"
                "Ahmet: Evet Emel, yedinci haberimiz adeta uzay çağı teknolojisini müjdeliyor. Girişimler, doğrudan güneş ışığından kesintisiz güç alan ve uzayın doğal soğuk ortamından faydalanarak sıfır soğutma maliyetiyle çalışan modüler veri merkezlerini yörüngeye fırlattı ve ilk testler başarıyla sonuçlandı.\n\n"
                "Emel: Dünyamızın su kaynaklarını soğutma için harcamadan, yeryüzünün elektrik şebekesine yük bindirmeden uzayın sınırsız güneş enerjisiyle yapay zeka modelleri eğitmek gerçekten dahiyane bir vizyon. Ve geldik günün sekizinci ve insanlık adına en değerli haberine Ahmet: Biyoteknoloji ve yapay zeka ortaklığı.\n\n"
                "Ahmet: Sekizinci haberimiz sağlık dünyasında çığır açan bir gelişme Emel. Generatif yapay zeka ve derin öğrenme modelleri kullanılarak aylar süren moleküler dinamik simülasyonları saatler seviyesine indirildi. Bu sayede nadir genetik hastalıkların tedavisinde hedefe kilitlenen sentetik protein yapıları ve yeni aday ilaç molekülleri tasarlandı ve klinik deney aşamasına geçildi.\n\n"
                "Emel: Yapay zekanın sadece kod yazmak veya analiz yapmakla kalmayıp insan hayatını kurtaracak tedavilerin keşfinde başrol oynaması gerçekten umut verici. Bugün otonom yazılımdan kuantum güvenliğine, uzay bilişiminden biyoteknolojiye kadar tam sekiz devasa konuyu konuştuk.\n\n"
                "Ahmet: Teknoloji dünyası her gün daha hızlı ve daha etkileyici bir ivmeyle büyümeye devam ediyor. Günün tüm bu sekiz haberinin en çarpıcı başlıkları, öne çıkan maddeleri ve net özetleri podcast açıklama metnimizde ve RSS beslememizde sizleri bekliyor. M1 Podcast olarak teknolojinin nabzını tutmaya devam edeceğiz.\n\n"
                "Emel: Yarın yepyeni gelişmeler ve derinlemesine analizlerle tekrar karşınızda olacağız. Bizi dinlediğiniz için çok teşekkür ederiz!\n\n"
                "Ahmet: Kendinize çok iyi bakın, hoşça kalın!\n\n"
                "Emel: Teknolojiyle ve M1 Podcast ile kalın!"
            )
        }
