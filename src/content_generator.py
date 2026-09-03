import os
import json
import re
import feedparser
import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ContentGenerator:
    """Fetches latest Turkish & Global tech news and generates interactive 14-16 minute (~1.5x length, ~1600 words) podcast scripts with 8-10 news stories and natural explanations."""

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
            "https://techcrunch.com/feed/",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://arstechnica.com/feed/",
            "https://venturebeat.com/category/ai/feed/",
            "https://www.wired.com/feed/category/business/latest/rss",
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "https://gizmodo.com/rss"
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
                for entry in parsed.entries[:20]:
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

        return "\n\n".join(fresh_articles[:40])

    def generate_dialogue_script(self, raw_news_context: str, recent_topics: List[str] = None) -> Dict[str, Any]:
        """Generates dynamic 14-16 minute (~1600 words, 1.5x) Turkish podcast dialogue (Ahmet & Emel) with 8-10 news stories, interactive back-and-forth, and technical explanations."""
        print("🤖 Etkileşimli, 8-10 haberli ve 1.5 kat uzunlukta (~1600 kelime, 14-15 dakika) Türkçe podcast metni üretiliyor...")
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')

        system_prompt = (
            "Sen iki deneyimli teknoloji sunucusu (Ahmet ve Emel) için canlı, samimi ve son derece etkileşimli bir Türkçe podcast metni yazan kıdemli bir yapımcısın.\n\n"
            "MANDATORY FORMAT VE KURALLAR:\n"
            "1. HEDEF SÜRE VE KELİME HEDEFİ: Podcast süresi TAM 14-16 DAKİKA ARASINDA (1550 - 1700 KELİME) olmalıdır. "
            "Kesinlikle 1500 kelimenin altına düşülmemelidir. Çıktının kısa kalmaması için seçilen tüm haberler derinlemesine, teknik ve pratik boyutlarıyla detaylandırılmalı, karşılıklı sorular, benzetmeler ve zengin diyaloglarla geliştirilmelidir.\n"
            "2. HABER SAYISI: 8 ile 10 adet (en az 8 haber) güçlü ana teknoloji & yapay zeka haberi seç. "
            "Tüm bu haberler hem 'news_items' dizisinde yer almalı hem de sunucular tarafından diyalog akışında sırayla ele alınmalıdır.\n"
            "3. GERÇEK ETKİLEŞİM VE DİYALOG:\n"
            "   - Sunucular birbirini papağan gibi onaylamamalı ('kesinlikle', 'çok haklısın', 'aynen öyle' kalıplarını YASAKLA).\n"
            "   - Birbirlerine doğrudan sorular sorsunlar, şaşırsınlar, farklı bakış açıları sunsunlar ('Peki Emel, kullanıcı bunu günlük hayatta nasıl hissedecek?', 'Ahmet burada bir soru işareti var, güvenlik riski doğurmaz mı?').\n"
            "   - Her haber için Ahmet ve Emel arasında en az 3-5 karşılıklı konuşma turu olmalı; haberler aceleyle geçiştirilmemelidir.\n"
            "4. TEKNİK TERİMLERİ AKIŞ İÇİNDE AÇIKLA:\n"
            "   - Metinde geçen her teknik kavram (örn: Kuantizasyon, Nöromorfik çip, NPU / TOPS, Kuantum Sonrası Kriptografi, Otonom Ajan, Multimodal Haritalama, Katı Hal Bataryası, LEO Lazer İletişimi vb.) mutlaka konuşma akışını bozmadan günlük dilde somut benzetmelerle izah edilsin.\n"
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
            '  "script": "Ahmet: Merhaba teknoloji meraklıları, M1 Podcast\'e hoş geldiniz...\\n\\nEmel: ..."\n'
            "}"
        )

        user_prompt = (
            f"Tarih: {today_date_str}\n\n"
            f"Günün Ham Teknoloji & Yapay Zeka Haber Havuzu:\n\n{raw_news_context or 'Günün öne çıkan yapay zeka, yazılım, donanım ve teknoloji gelişmeleri.'}\n\n"
            "Lütfen 8-10 haberi derinlemesine tartışan, teknik terimleri doğal dille açıklayan, yapay onaylama kalıplarından uzak, karşılıklı soru-cevaplı ve EN AZ 1550-1700 KELİMELİK (~14-15 dakika) Türkçe diyalog JSON çıktısını üret."
        )

        if not self.client:
            print("ℹ️ LLM API anahtarı bulunamadı, 1.5 kat uzunlukta (~1600 kelime) örnek şablon kullanılıyor.")
            return self._get_fallback_turkish_script()

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat" if "deepseek" in str(self.client.base_url) else "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=5000,
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
        """Provides an interactive, deeply conversational ~1.5x length (1629 words, ~14-15 minutes, 10 stories) Turkish podcast episode explaining technical terms naturally."""
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')
        return {
            "title": f"M1 Podcast - Günlük Teknoloji & Yapay Zeka Bülteni ({today_date_str})",
            "summary": "Otonom yazılım ajanlarından kuantum sonrası şifrelemeye, nöromorfik çiplerden katı hal bataryalara teknolojinin en sıcak 10 gelişmesi ve 1.5 kat genişletilmiş derinlemesine analizi.",
            "todays_topics": "Otonom Yazılım Ajanları, Yerel Açık Kaynak LLM ve Kuantizasyon, Nöromorfik Çip Mimarisi, İnsansı Robotlarda Multimodal Haritalama, Kuantum Sonrası Kriptografi (PQC), Biyoteknolojide Sentetik Protein Tasarımı, LEO Uydularında Optik Lazer Haberleşmesi, Katı Hal (Solid-State) Bataryalar, Otonom Web ve Tarayıcı Ajanları, Açık Ağırlıklı Yapay Zeka Güvenliği",
            "news_items": [
                {
                    "headline": "Otonom Yazılım Ajanları: Kod Tamamlamadan Tam Teşekküllü Mühendisliğe",
                    "key_points": [
                        "Modeller artık tüm repo bağımlılıklarını analiz edip uçtan uca hata ayıklıyor",
                        "Geliştirici ekiplerinin hata çözme süresinde %45 kısalma kaydedildi"
                    ],
                    "summary": "Yeni nesil otonom kodlama ajanları, karmaşık kurumsal projelerin kod tabanını analiz ederek bağımsız birim testleri yazabiliyor ve güvenlik açıklarını otomatik kapatıyor."
                },
                {
                    "headline": "Açık Kaynak Modellerde Kuantizasyon Devrimi: Dizüstünde GPT-4 Seviyesi",
                    "key_points": [
                        "Kuantizasyon tekniği ile modeller sıkıştırılarak standart bilgisayarlarda çalıştırılıyor",
                        "Şirket içi veri gizliliği ve yerel işlem önceliği talebi katladı"
                    ],
                    "summary": "Son yayınlanan açık ağırlıklı modeller, yüksek kuantizasyon verimliliği sayesinde bulut sunucularına bağlanmadan güçlü mantık yürütme imkanı sunuyor."
                },
                {
                    "headline": "Nöromorfik Çipler ve Enerji Verimliliği: Beyin Biyolojisini Taklit Eden Donanım",
                    "key_points": [
                        "İnsan beyninin sinaps yapısını taklit eden yeni donanım mimarileri tanıtıldı",
                        "Veri merkezlerinin yüksek elektrik tüketimine 10 kat daha verimli sürdürülebilir çözüm"
                    ],
                    "summary": "Donanım üreticileri, derin öğrenme modellerini mikrosaniye seviyesinde gecikmeyle ve onda bir enerjiyle çalıştıran yeni nöromorfik işlemcilerini duyurdu."
                },
                {
                    "headline": "İnsansı Robotlarda Multimodal Haritalama: Fabrikalardan Günlük Yaşama",
                    "key_points": [
                        "Görsel ve dokunsal veriyi birleştiren multimodal sinir ağları kullanılıyor",
                        "Otomotiv montaj hatlarında insan işçilerle yan yana pilot testler başladı"
                    ],
                    "summary": "Yeni insansı robot modelleri, uçtan uca sinir ağları sayesinde insan hareketlerini taklit ederek karmaşık montaj ve taşıma görevlerini hatasız tamamlayabiliyor."
                },
                {
                    "headline": "Kuantum Sonrası Kriptografi (PQC): Geleceğin Siber Saldırılarına Karşı Kalkan",
                    "key_points": [
                        "Kuantum bilgisayarların mevcut şifreleme algoritmalarını kırma riskine karşı yeni protokoller onaylandı",
                        "Bankacılık ve kamu altyapıları kuantum dayanıklı şifrelemeye geçişe başladı"
                    ],
                    "summary": "Uluslararası siber güvenlik otoriteleri, kuantum tehditlerine karşı geliştirilen yeni matematiksel kafes tabanlı şifreleme standartlarını resmi olarak yürürlüğe koydu."
                },
                {
                    "headline": "Biyoteknolojide Generatif Yapay Zeka: Saatler İçinde Sentetik Protein Tasarımı",
                    "key_points": [
                        "Aylar süren moleküler simülasyonlar saatler seviyesine indirildi",
                        "Nadir hastalıklar için hedefe yönelik aday moleküller klinik aşamaya ulaştı"
                    ],
                    "summary": "Biyoteknoloji laboratuvarları, generatif yapay zeka kullanarak sentetik protein yapıları tasarladı ve nadir hastalıkların tedavisinde kritik aday moleküller keşfetti."
                },
                {
                    "headline": "LEO Takımyıldızlarında Optik Lazer İletişimi: Uzayda Gigabit İnternet Omurgası",
                    "key_points": [
                        "Uydular arası lazer ışınları, karasal fiber kablolardan %40 daha hızlı veri aktarıyor",
                        "Kıtalararası finansal işlemlerde ve kutup bölgelerinde gecikme süreleri dibe çekildi"
                    ],
                    "summary": "Alçak dünya yörüngesindeki uydular arasında devreye alınan optik lazer haberleşmesi, küresel internet omurgasını uzaya taşıyarak karasal fiber hatlara rakip oluyor."
                },
                {
                    "headline": "Yeni Nesil Katı Hal (Solid-State) Bataryalar: Seri Üretim Takvimi Netleşti",
                    "key_points": [
                        "Sıvı elektrolit yerine seramik polimer kullanılarak yangın riski tamamen sıfırlandı",
                        "10 dakikada şarj ve 1000 kilometreyi aşan menzil ile 2027 başında ticari araçlara giriyor"
                    ],
                    "summary": "Katı hal batarya teknolojisinde beklenen büyük atılım gerçekleşti; laboratuvar testleri tamamlanan hücrelerin ticari elektrikli araçlara entegrasyonu duyuruldu."
                },
                {
                    "headline": "Otonom Web ve Tarayıcı Ajanları: İnternet Gezintisinde İnsan Yerine Yapay Zeka",
                    "key_points": [
                        "Kullanıcı talimatıyla çok adımlı rezervasyon, araştırma ve satın alma görevleri tamamlanıyor",
                        "Görsel arayüzleri analiz eden yeni nesil çok modlu ajanlar siteleri otonom geziyor"
                    ],
                    "summary": "Web sitelerinde insan yerine gezinip form dolduran, uçak bileti arayan ve karmaşık e-ticaret süreçlerini yöneten otonom tarayıcı ajanları yaygınlaşıyor."
                },
                {
                    "headline": "Açık Ağırlıklı Yapay Zekada Küresel Güvenlik ve Kırmızı Takım Standartları",
                    "key_points": [
                        "Modellerin tehlikeli senaryolara karşı dayanıklılığını ölçen küresel denetim çerçevesi açıklandı",
                        "Kötü niyetli manipülasyonları engelleyen yazılımsal ve donanımsal güvenlik kalkanları devreye girdi"
                    ],
                    "summary": "Yapay zeka güvenlik otoriteleri, açık ağırlıklı modellerin güvenliğini teyit eden kapsamlı kırmızı takım ve stres testi standartlarını duyurdu."
                }
            ],
            "script": (
                "Ahmet: Merhaba teknoloji meraklıları, M1 Podcast'e hoş geldiniz. Bugün yapay zeka laboratuvarlarından kuantum şifrelemeye, nöromorfik donanımlardan yeni nesil bataryalara kadar tam on sıcak ve kritik başlıkla karşınızdayız. İlk durağımız, yazılım dünyasında ezberleri tamamen bozan otonom kodlama ajanlarındaki son sıçrama. Yayınlanan yeni benchmark raporları, yapay zekanın basit bir kod tamamlama eklentisi olmaktan çıkıp projenin tüm mimarisini anlayan bağımsız bir yazılım mühendisine dönüştüğünü gösteriyor.\n\n"
                "Emel: Ahmet, burada otonom ajan derken tam olarak neyi kastediyoruz? Yani yıllardır kullandığımız GitHub Copilot gibi akıllı asistanlardan veya sohbet botlarından farkı ne?\n\n"
                "Ahmet: Çok kritik bir ayrım. Klasik yardımcılar sizden tekil bir fonksiyon veya kod bloğu yazmanızı bekler. Otonom ajan ise projenin tüm git geçmişini, veritabanı şemasını, mikroservis bağlarını ve birim testlerini aynı anda hafızasına alıyor. Sistemde bir hata bildirdiğinizde sadece hatanın olduğu satırı değil, o değişikliğin tetikleyeceği diğer tüm servisleri analiz ediyor, kendi kendine yeni birim testleri yazıyor ve doğrulanmış düzeltmeyi doğrudan bir pull request olarak geliştiricinin önüne koyuyor. Büyük teknoloji şirketlerinde yapılan testlerde ekiplerin hata çözme süresinde yüzde kırk beşlik devasa bir kısalma görüldü.\n\n"
                "Emel: Peki Ahmet, bu ajanların yazdığı kodlar sisteme bilmeden yeni güvenlik açıkları veya mimari hatalar sokabilir mi? Denetim mekanizması pratikte nasıl kurgulanıyor?\n\n"
                "Ahmet: Çok haklı ve yerinde bir endişe. İşte bu yüzden ajanlar kodu doğrudan prodüksiyon dalına basmıyor; izole sanal alanlarda güvenlik taramasından geçirip statik kod analiziyle test ettikten sonra insan kıdemli mühendisin onayına sunuyor. Yani yazılımcı artık rutin sözdizimi hatalarıyla veya mekanik kod bloklarıyla vakit kaybetmek yerine sistem mimarı ve nihai karar verici rolüne geçiyor. İş mantığını ve sınırları insan belirliyor, ham işçiliği ise ajanlar sırtlanıyor.\n\n"
                "Emel: Kodlama tarafındaki bu hızlanma, açık kaynak modellerin yerel cihazlarda çalıştırılabilmesiyle birleştiğinde etkisi ikiye katlanıyor. Eskiden bu düzeyde akıl yürüten modelleri kullanmak için mutlaka dev bulut sağlayıcılarının API'lerine bağlanmak ve yüksek faturalar ödemek zorundaydık. Ancak son günlerde kuantizasyon teknolojisindeki atılımlar, GPT-4 sınıfı modelleri standart dizüstü bilgisayarlara kadar indirdi.\n\n"
                "Ahmet: Emel, dinleyicilerimizin zihninde netleşmesi için kuantizasyon kavramını biraz somutlaştıralım mı? Teknik olarak arka planda ne yapılıyor da devasa bir yapay zeka modeli sıradan bir bilgisayarın belleğine sığabiliyor?\n\n"
                "Emel: Kuantizasyonu devasa bir yüksek çözünürlüklü RAW fotoğrafı, insan gözünün fark edemeyeceği kadar az bir kayıpla sıkıştırmaya benzetebiliriz. Normalde on altı bitlik yüksek hassasiyetli kayan noktalı sayılarla saklanan yüz milyarlarca model ağırlığını, özel algoritmalarla dört veya sekiz bite indiriyoruz. Böylece modelin kapladığı bellek alanı dörtte birine düşerken, mantık yürütme kabiliyeti yüzde doksan beşin üzerinde korunuyor.\n\n"
                "Ahmet: İşte bu sayede bankalar, hastaneler veya savunma sanayii firmaları en kritik verilerini şirket dışındaki üçüncü parti bir bulut sunucusuna göndermeden, kendi ofislerindeki bilgisayarlarda yerel olarak yapay zeka çalıştırabiliyor. Veri gizliliği ve kurumsal egemenlik açısından tarihi bir eşik aşıldı.\n\n"
                "Emel: Kesinlikle öyle. Fakat modeller yerelleştikçe ve veri merkezleri katlanarak büyüdükçe başka bir devasa darboğazla yüzleştik: Elektrik tüketimi. Yapay zeka sunucularının enerji iştahı ülkelerin şebekelerini zorlarken, bu hafta nöromorfik çip mimarilerinde tarihi bir dönüm noktası duyuruldu.\n\n"
                "Ahmet: Nöromorfik derken insan beyninin biyolojisinden ilham alan donanımları kastediyoruz değil mi Emel? Klasik işlemcilerden mimari farkı ne tam olarak?\n\n"
                "Emel: Aynen öyle Ahmet. Geleneksel bilgisayar işlemcileri saat frekansına göre sürekli elektrik çeker ve her döngüde hafıza ile işlemci arasında veri taşır. Nöromorfik çipler ise insan beynindeki biyolojik nöron ve sinapslar gibi çalışır; yani sadece bir uyarı, bir sinyal geldiğinde elektrik harcar. Bilgi akışı yoksa bekleme modundadır ve enerji tüketimi neredeyse sıfıra iner. Yeni tanıtılan prototipler, derin öğrenme çıkarımlarını klasik çiplere göre onda bir enerjiyle ve mikrosaniye seviyesinde gecikmeyle tamamlayabiliyor.\n\n"
                "Ahmet: Düşünsenize, akıllı saatler, kalp pilleri veya minyatür dronlar şarja ihtiyaç duymadan haftalarca kendi üzerinde yapay zeka çalıştırabilecek. Donanımdaki bu hafifleme ve verimlilik, bizi dördüncü sıcak konumuza, insansı robotlardaki multimodal haritalama devrimine götürüyor.\n\n"
                "Emel: Robotik dünyası son bir yılda laboratuvar deneylerinden çıkıp doğrudan fabrika zeminine indi. İnsansı robotlar artık sadece önceden koordinatları girilmiş sabit rotaları takip etmiyor; multimodal görsel ve dokunsal algılayıcılarla çevrelerini dinamik olarak öğreniyorlar.\n\n"
                "Ahmet: Burada multimodal derken neyi kastediyoruz, biraz detaylandıralım. Robot sadece kameralardan gelen iki boyutlu piksellere bakmıyor. Parmak uçlarındaki basınç sensörleri, gövdesindeki jiroskoplar ve derinlik kameralarından gelen tüm veriler tek bir sinir ağında birleşiyor. Böylece robot yumuşak bir meyveyi ezip ezmediğini, elindeki ağır bir otomotiv parçasının dengesini anlık olarak hissedip tutuş kuvvetini milisaniyeler içinde ayarlayabiliyor.\n\n"
                "Emel: Hatta küresel otomotiv devlerinin montaj hatlarında insansı robotlar insan işçilerle yan yana çalışmaya başladı bile. Tehlikeli, yüksek sıcaklıklı veya tekrarlı montaj görevlerini hatasız şekilde üstleniyorlar.\n\n"
                "Ahmet: İş güvenliği ve verimlilikte devrim yaşanırken, fabrikayı, finansı ve bulutu birbirine bağlayan dijital altyapılarda ise çok büyük bir alarm çalıyordu: Kuantum tehdidi. Ve bu hafta siber güvenlik dünyası için tarihi bir gün yaşandı; kuantum sonrası kriptografi standartları resmi olarak yürürlüğe girdi.\n\n"
                "Emel: Ahmet, kuantum bilgisayarlar bugünkü şifreleme sistemlerini kırabilir denildiğinde genelde insanlarda soyut bir korku oluşuyor. Tehlike tam olarak nereden kaynaklanıyordu ve yeni onaylanan PQC protokolleri bunu nasıl engelliyor?\n\n"
                "Ahmet: Harika bir soru. Bugün e-ticaretten bankacılık uygulamalarına kadar internetteki güvenliğin temeli RSA ve eliptik eğri şifrelemesine dayanıyor. Bu sistemlerin güvenliği, çok büyük iki asal sayının çarpımını asal çarpanlarına ayırmanın klasik bilgisayarlar için yüzlerce yıl sürmesi prensibine dayanır. Oysa yeterince güçlü bir kuantum bilgisayar, Shor algoritması sayesinde bu çarpanları birkaç dakika içinde bulabilir.\n\n"
                "Emel: Yani bugüne kadar saklanan tüm şifreli yazışmalar, devlet sırları ve banka kayıtları geriye dönük olarak çözülebilir riski taşıyordu.\n\n"
                "Ahmet: Kesinlikle. İşte yeni onaylanan kuantum sonrası kriptografi, yani PQC algoritmaları, asal sayılar yerine çok boyutlu karmaşık matematiksel kafes yapılarına dayanıyor. Bu kafes problemleri öylesine çetrefilli ki, kuantum bilgisayarlar bile bilinen hiçbir algoritmayla bu şifreyi çözemiyor. Bankalar ve kamu kurumları şimdiden sunucularını bu yeni kafes tabanlı şifreleme kütüphanelerine güncellemeye başladı.\n\n"
                "Emel: Güvenlik tarafında bu kalkan kurulurken, biyoteknoloji laboratuvarlarından gelen haberler ise insan ömrünü ve sağlığını doğrudan etkileyecek cinsten. Generatif yapay zeka artık yalnızca metin veya resim üretmiyor, atomik düzeyde sentetik proteinler tasarlıyor.\n\n"
                "Ahmet: Emel, bir proteinin yapısını tasarlamak neden tıp dünyası için bu kadar devasa bir mesele?\n\n"
                "Emel: Ahmet, vücudumuzdaki her bir hastalık veya virüs, belirli hücre reseptörlerine kilit-anahtar uyumuyla bağlanır. Bir hastalığı durdurmak için o kilide tam oturan yepyeni bir molekül veya protein tasarlamanız gerekir. Eskiden bir proteinin üç boyutlu olarak nasıl katlanacağını laboratuvarda deneme yanılma yoluyla simüle etmek aylar, bazen yıllar sürerdi. Şimdi derin öğrenme modelleri, hedeflenen hastalığa kilitlenecek yepyeni sentetik protein tasarımlarını birkaç saat içinde üretebiliyor.\n\n"
                "Ahmet: Hatta nadir görülen genetik hastalıklar ve kanser türleri için tasarlanan sentetik aday moleküller klinik deney aşamasına ulaştı bile. Kişiye özel hedefe yönelik ilaçların geliştirilme süresi yıllardan aylara iniyor.\n\n"
                "Emel: Tıptaki bu mucizevi sıçramanın ardından rotamızı gökyüzüne, hatta dünyanın yörüngesine çeviriyoruz. Alçak dünya yörüngesindeki uydu takımyıldızlarında optik lazer haberleşmesi küresel internet ağını baştan aşağı değiştiriyor.\n\n"
                "Ahmet: Emel, uydudan internet dediğimizde çoğu insanın aklına klasik radyo frekansları ve baz istasyonları gelir. Lazer ile veri iletimi neyi farklı kılıyor?\n\n"
                "Emel: Klasik radyo dalgaları uzay boşluğunda geniş bir alana yayılır, bant genişliği sınırlıdır ve atmosferik parazitlerden kolayca etkilenir. Yeni nesil optik lazer bağlantıları ise binlerce kilometre ötedeki uyduları saç teli kalınlığında odaklanmış ışık demetleriyle birbirine bağlıyor. Işık uzay boşluğunda, karasal fiber optik kablolardaki cam ortamına göre yüzde kırk daha hızlı ilerler.\n\n"
                "Ahmet: Yani Londra ile Tokyo arasındaki bir finans işlemi veya kritik veri paketi, yerin altındaki fiber kablolardan daha hızlı bir şekilde uzaydaki lazer ağı üzerinden hedefine ulaşıyor. Hem gecikme süresi dramatik biçimde düşüyor hem de okyanusun ortasındaki bir gemi ya da kutuplardaki bir araştırma istasyonu gigabit hızında internete kavuşuyor.\n\n"
                "Emel: Uzaydaki bu iletişim ağı dünyadaki elektrikli mobilite devrimiyle birleştiğinde geleceğin akıllı şehirleri şekilleniyor. Ve mobilite alanındaki en büyük haberimiz, katı hal batarya teknolojilerinde nihayet seri üretim takviminin netleşmesi.\n\n"
                "Ahmet: Katı hal, yani solid-state piller otomotiv sektörünün kutsal kasesi olarak görülüyordu Emel. Mevcut lityum iyon pillerden temel farkı ve kullanıcının hayatına getireceği değişim nedir?\n\n"
                "Emel: Mevcut lityum iyon pillerde anot ve katot arasında sıvı bir elektrolit bulunur. Bu sıvı aşırı ısınmada yanma riski taşır, soğuk havalarda verimi düşer ve şarj süresini sınırlar. Katı hal bataryalarda ise bu sıvı katı seramik veya polimer bir malzeme ile değiştiriliyor. Bu sayede pil yanma riski taşımıyor, aynı hacimde iki kat daha fazla enerji depolayabiliyor ve on dakikada yüzde seksen şarj olabiliyor. Üstelik dondurucu kış şartlarında yaşanan menzil düşüşü de tarihe karışıyor.\n\n"
                "Ahmet: Yani bir elektrikli otomobil tek şarjla bin kilometrenin üzerinde yol yapabilecek ve şarj istasyonunda kahvenizi alana kadar bataryası dolmuş olacak. İlk ticari araçların 2027 yılı başında yollara çıkacağı duyuruldu.\n\n"
                "Emel: Mobilitedeki bu konforun ardından yazılım tarafındaki bir diğer dev yeniliğe, otonom web ajanlarına bakalım. Artık web siteleri sadece insanların tıklaması için değil, arkada görev koşan yapay zeka ajanlarının gezinmesi için optimize ediliyor.\n\n"
                "Ahmet: Emel, tarayıcı ajanları dediğimizde ne anlamalıyız? Mesela bir tatil planı veya karmaşık bir uçak bileti rezervasyonunda nasıl çalışıyorlar?\n\n"
                "Emel: Siz sadece 'Önümüzdeki ay Roma seyahatim için bütçeme en uygun uçak ve otel rezervasyonlarını ayarla' diyorsunuz. Ajan tarayıcıyı açıyor, siteleri ziyaret ediyor, filtreleri uyguluyor, şartları inceliyor ve satın alma adımına kadar tüm süreci uçtan uca yürütüyor.\n\n"
                "Ahmet: Web sayfalarındaki butonları ve formları bir insan gibi algılayan bu çok modlu modeller internet kullanım alışkanlıklarımızı kökten değiştirecek. Ve günün son büyük başlığı: Açık ağırlıklı modeller için küresel kırmızı takım ve güvenlik standartlarının duyurulması.\n\n"
                "Emel: Modellerin biyolojik, kimyasal veya siber saldırılarda kötüye kullanılmasını engellemek için bağımsız etik hackerların denetiminden geçmesi zorunlu hale getirildi. Böylece yapay zeka inovasyonu güvenli temeller üzerinde büyüyecek.\n\n"
                "Ahmet: Otonom mühendislerden kuantizasyona, nöromorfik çiplerden uzay lazerlerine, katı hal pillerden yapay zeka güvenliğine kadar tam on büyük gelişmeyi tüm boyutlarıyla masaya yatırdık.\n\n"
                "Emel: Tüm bu haberlerin özetleri, can alıcı maddeleri ve kaynak bağlantıları podcast açıklama metnimizde ve RSS beslememizde sizleri bekliyor.\n\n"
                "Ahmet: M1 Podcast'in bugünkü bölümünün sonuna geldik. Yarın yepyeni teknoloji başlıklarıyla tekrar görüşmek dileğiyle, hoşça kalın!\n\n"
                "Emel: Kendinize çok iyi bakın, bilimle ve teknolojiyle kalın!"
            )
        }
