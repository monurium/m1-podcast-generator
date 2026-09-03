import os
import json
import re
import feedparser
import datetime
from typing import List, Dict, Any, Optional
from openai import OpenAI

class ContentGenerator:
    """Fetches latest Turkish & Global tech news and generates interactive 10-11 minute (~1150 words) podcast scripts with 8-10 news stories and natural explanations."""

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
        """Generates dynamic 10-11 minute (~1150-1250 words) Turkish podcast dialogue (Ahmet & Emel) with 8-10 news stories, interactive back-and-forth, and technical explanations."""
        print("🤖 Etkileşimli, 8-10 haberli (%25 dengeli, ~1150 kelime, 10-11 dakika) Türkçe podcast metni üretiliyor...")
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')

        system_prompt = (
            "Sen iki deneyimli teknoloji sunucusu (Ahmet ve Emel) için canlı, samimi ve son derece etkileşimli bir Türkçe podcast metni yazan kıdemli bir yapımcısın.\n\n"
            "MANDATORY FORMAT VE KURALLAR:\n"
            "1. HEDEF SÜRE VE KELİME HEDEFİ: Podcast süresi TAM 10-11 DAKİKA ARASINDA (1150 - 1250 KELİME) olmalıdır. "
            "Seçilen tüm haberler akıcı, teknik ve pratik boyutlarıyla detaylandırılmalı, karşılıklı soru-cevaplarla geliştirilmelidir.\n"
            "2. HABER SAYISI: 8 ile 10 adet (en az 8 haber) güçlü ana teknoloji & yapay zeka haberi seç. "
            "Tüm bu haberler hem 'news_items' dizisinde yer almalı hem de sunucular tarafından diyalog akışında sırayla ele alınmalıdır.\n"
            "3. GERÇEK ETKİLEŞİM VE DİYALOG:\n"
            "   - Sunucular birbirini papağan gibi onaylamamalı ('kesinlikle', 'çok haklısın', 'aynen öyle' kalıplarını YASAKLA).\n"
            "   - Birbirlerine doğrudan sorular sorsunlar, şaşırsınlar, farklı bakış açıları sunsunlar ('Peki Emel, kullanıcı bunu günlük hayatta nasıl hissedecek?', 'Ahmet burada bir soru işareti var, güvenlik riski doğurmaz mı?').\n"
            "   - Her haber için Ahmet ve Emel arasında en az 2-4 karşılıklı konuşma turu olmalı; haberler aceleyle geçiştirilmemelidir.\n"
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
            "Lütfen 8-10 haberi derinlemesine tartışan, teknik terimleri doğal dille açıklayan, yapay onaylama kalıplarından uzak, karşılıklı soru-cevaplı ve 1150-1250 KELİMELİK (~10-11 dakika) Türkçe diyalog JSON çıktısını üret."
        )

        if not self.client:
            print("ℹ️ LLM API anahtarı bulunamadı, %25 azaltılmış dengeli (~1135 kelime) örnek şablon kullanılıyor.")
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
        """Provides an interactive, deeply conversational ~1135-word (10-11 minutes, 10 stories) Turkish podcast episode explaining technical terms naturally."""
        today_date_str = datetime.date.today().strftime('%d.%m.%Y')
        return {
            "title": f"M1 Podcast - Günlük Teknoloji & Yapay Zeka Bülteni ({today_date_str})",
            "summary": "Otonom yazılım ajanlarından kuantum sonrası şifrelemeye, nöromorfik çiplerden katı hal bataryalara teknolojinin en sıcak 10 gelişmesi ve derinlemesine analizi.",
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
                "Emel: Ahmet, burada otonom ajan derken tam olarak neyi kastediyoruz? Yani yıllardır kullandığımız akıllı asistanlardan veya sohbet botlarından farkı ne tam olarak?\n\n"
                "Ahmet: Çok kritik bir ayrım. Klasik yardımcılar sizden tekil bir fonksiyon veya kod parçası yazmanızı bekler. Otonom ajan ise projenin tüm git geçmişini, veritabanı şemasını, mikroservis bağlarını ve birim testlerini aynı anda hafızasında tutuyor. Sistemde bir hata bildirdiğinizde sadece hatanın olduğu satırı değil, o değişikliğin tetikleyeceği diğer tüm servisleri analiz ediyor, kendi kendine yeni testler yazıyor ve doğrulanmış düzeltmeyi doğrudan bir pull request olarak geliştiricinin önüne koyuyor. Büyük teknoloji şirketlerinde yapılan kapsamlı testlerde ekiplerin hata çözme süresinde yüzde kırk beşlik devasa bir hızlanma kaydedildi.\n\n"
                "Emel: Peki Ahmet, bu ajanların yazdığı kodlar sisteme bilmeden yeni güvenlik açıkları sokabilir mi? Denetim mekanizması pratikte nasıl kurgulanıyor?\n\n"
                "Ahmet: Çok haklı ve yerinde bir endişe. Ajanlar kodu doğrudan canlı sisteme basmıyor; izole sanal alanlarda güvenlik taramasından geçirip statik kod analiziyle test ettikten sonra kıdemli mühendisin onayına sunuyor. Yani yazılımcı artık rutin sözdizimi hatalarıyla vakit kaybetmek yerine sistem mimarı ve nihai karar verici rolüne geçiyor. İş mantığını ve sınırları insan belirliyor, ham işçiliği ise ajanlar üstleniyor.\n\n"
                "Emel: Kodlama tarafındaki bu hızlanma, açık kaynak modellerin yerel cihazlarda çalıştırılabilmesiyle birleştiğinde etkisi ikiye katlanıyor. Eskiden bu düzeyde akıl yürüten modeller için mutlaka dev bulut sağlayıcılarının API'lerine bağlanmak ve yüksek faturalar ödemek zorundaydık. Ancak son günlerde kuantizasyon teknolojisindeki atılımlar, GPT-4 sınıfı modelleri standart dizüstü bilgisayarlara kadar indirdi.\n\n"
                "Ahmet: Emel, dinleyicilerimizin zihninde netleşmesi için kuantizasyon kavramını biraz somutlaştıralım mı? Teknik olarak arka planda ne yapılıyor da devasa bir model sıradan bir bilgisayarda çalışabiliyor?\n\n"
                "Emel: Kuantizasyonu devasa bir yüksek çözünürlüklü RAW fotoğrafı, insan gözünün fark edemeyeceği kadar az kayıpla sıkıştırmaya benzetebiliriz. Normalde on altı bitlik yüksek hassasiyetli kayan noktalı sayılarla saklanan model ağırlıklarını özel algoritmalarla dört veya sekiz bite indiriyoruz. Böylece modelin kapladığı bellek alanı dörtte birine düşerken, mantık yürütme kabiliyeti yüzde doksan beşin üzerinde korunuyor.\n\n"
                "Ahmet: İşte bu sayede bankalar, hastaneler ve savunma sanayii firmaları en kritik verilerini üçüncü parti sunuculara göndermeden, kendi ofis bilgisayarlarında yerel olarak yapay zeka çalıştırabiliyor. Veri gizliliği ve kurumsal egemenlik açısından tarihi bir eşik. Ancak modeller büyüdükçe elektrik tüketimi de katlandı ve bu noktada nöromorfik çipler sahneye çıktı.\n\n"
                "Emel: Nöromorfik derken insan beyninin biyolojisinden ilham alan donanımları kastediyoruz değil mi Ahmet? Klasik işlemcilerden farkı ne tam olarak?\n\n"
                "Ahmet: Aynen öyle. Geleneksel işlemciler saat frekansına göre sürekli elektrik çekerken, nöromorfik çipler insan beynindeki biyolojik nöron ve sinapslar gibi çalışır; yani sadece bir uyarı, bir sinyal geldiğinde elektrik harcar. Bilgi akışı yoksa bekleme modundadır ve enerji tüketimi neredeyse sıfıra iner. Yeni tanıtılan prototipler, derin öğrenme çıkarımlarını klasik çiplere kıyasla tam on kat enerji tasarrufuyla ve mikrosaniye gecikmeyle tamamlıyor.\n\n"
                "Emel: Düşünsenize, akıllı saatler ve minyatür dronların şarja ihtiyaç duymadan günlerce cihaz üzerinde yapay zeka çalıştırabilmesi harika bir kazanım. Donanımdaki bu hafifleme bizi dördüncü sıcak konumuza, yani insansı robotlardaki multimodal haritalama devrimine götürüyor.\n\n"
                "Ahmet: Robotik sistemler artık laboratuvarlardan çıkıp doğrudan fabrika zeminine indi. Kameralardan gelen görsel veri ile parmak uçlarındaki dokunma sensörleri tek bir sinir ağında birleşiyor. Böylece robot tuttuğu parçanın ağırlığını ve dengesini anlık hissedip tutuş kuvvetini milisaniyeler içinde ayarlayabiliyor.\n\n"
                "Emel: Otomotiv montaj hatlarında insan işçilerle yan yana çalışan robotlar tehlikeli ve hassas montaj görevlerini hatasız tamamlıyor. İş güvenliğinde devrim yaşanırken, fabrikayı ve bulutu birbirine bağlayan dijital altyapılarda ise kuantum tehdidine karşı yeni bir kalkan kuruldu: Kuantum sonrası kriptografi standartları resmen yürürlüğe girdi.\n\n"
                "Ahmet: Emel, kuantum bilgisayarlar bugünkü şifreleri çözebilir denildiğinde soyut bir korku doğuyor. Tehlike nereden kaynaklanıyordu ve yeni PQC standartları bunu nasıl engelliyor?\n\n"
                "Emel: Bugün kullandığımız e-ticaret ve bankacılık şifreleri çok büyük asal sayıların çarpanlarına dayanıyor. Klasik makineler bu sayıları çözemez ama kuantum bilgisayarlar dakikalar içinde bulabilir. Yeni onaylanan kuantum sonrası kriptografi ise asal sayılar yerine çok boyutlu karmaşık matematiksel kafes yapılarına dayanıyor. Kuantum bilgisayarlar bile bu kafes problemlerini çözemiyor.\n\n"
                "Ahmet: Bankalar ve kamu kurumları sunucularını şimdiden bu yeni kafes protokollerine taşımaya başladı bile. Güvenlik cephesindeki bu kalkanın ardından rotamızı biyoteknolojiye çeviriyoruz. Generatif yapay zeka artık yalnızca metin veya görsel üretmiyor, doğrudan atomik düzeyde sentetik protein tasarlıyor.\n\n"
                "Emel: Normalde bir proteinin üç boyutlu katlanmasını ve bir hastalığın reseptörüne nasıl kilitleneceğini laboratuvarda simüle etmek aylar hatta yıllar alıyordu. Şimdi derin öğrenme modelleri bu karmaşık moleküler tasarımları birkaç saate indirmiş durumda. Nadir genetik hastalıklar için hedefe yönelik aday moleküller şimdiden klinik deney aşamasına ulaştı bile.\n\n"
                "Ahmet: Kişiye özel tedavi çağı hızlanırken, gökyüzünde de dev bir haberleşme dönüşümü var. Alçak dünya yörüngesindeki uydu takımyıldızlarında optik lazer haberleşmesi küresel internet omurgasını baştan yazıyor.\n\n"
                "Emel: Uydular arası optik lazer bağlantıları, veriyi uzay boşluğunda karasal fiber kablolardan yüzde kırk daha hızlı taşıyor. Işık uzay boşluğunda cam ortama göre çok daha hızlı ilerlediği için kıtalararası finansal işlemler ve kutup araştırma istasyonları artık doğrudan gigabit hızında uzay internetine kavuşuyor.\n\n"
                "Ahmet: Hatta okyanuslardaki kargo gemileri veya uzak adalar hiçbir deniz altı kablosuna ihtiyaç duymadan doğrudan küresel ağa bağlanabiliyor. Uzaydaki bu iletişim dünyadaki elektrikli mobilite devrimiyle birleştiğinde geleceğin akıllı şehirleri şekilleniyor. Mobilite alanındaki en büyük haberimiz ise katı hal, yani solid-state bataryaların seri üretim takviminin nihayet netleşmesi.\n\n"
                "Emel: Mevcut lityum iyon pillerdeki sıvı elektrolit yerine yanmayan katı seramik polimer malzeme kullanılıyor. Bu sayede aşırı ısınma ve termal kaçak riski sıfırlanıyor; batarya hem iki kat fazla enerji depoluyor hem de on dakikada yüzde seksen şarj olarak bin kilometrenin üzerinde menzil vadediyor. Üstelik dondurucu kış şartlarında yaşanan menzil kaybı sorunu da tamamen tarihe karışıyor. İlk ticari araçların 2027 yılı başında yollara çıkacağı duyuruldu.\n\n"
                "Ahmet: Şarj bekleme süresini tarihe gömen bu gelişmenin ardından yazılıma dönüyoruz: Otonom web ve tarayıcı ajanları interneti insanlar yerine gezmeye başladı.\n\n"
                "Emel: Kullanıcı sadece 'Önümüzdeki ay Roma seyahatim için bütçeme en uygun uçak ve otel rezervasyonlarını ayarla' diyor. Ajan tarayıcıyı açıyor, siteleri ziyaret ediyor, filtreleri uyguluyor, şartları inceliyor ve satın alma adımına kadar tüm süreci uçtan uca yürütüyor.\n\n"
                "Ahmet: Web sayfalarındaki butonları ve formları bir insan gibi algılayan bu çok modlu modeller internet kullanım alışkanlıklarımızı kökten değiştirecek. Ve günün son büyük başlığı: Açık ağırlıklı modeller için küresel kırmızı takım ve güvenlik standartlarının duyurulması.\n\n"
                "Emel: Modellerin biyolojik, kimyasal veya kritik siber saldırılarda kötüye kullanılmasını engellemek için bağımsız etik hackerların denetiminden geçmesi zorunlu hale getirildi. Böylece yapay zeka inovasyonunun güvenli temeller üzerinde büyümesi güvence altına alınıyor.\n\n"
                "Ahmet: Otonom mühendislerden kuantizasyona, nöromorfik çiplerden uzay lazerlerine, katı hal pillerden yapay zeka güvenliğine kadar tam on büyük gelişmeyi tüm boyutlarıyla masaya yatırdık.\n\n"
                "Emel: Tüm bu haberlerin özetleri, can alıcı maddeleri ve kaynak bağlantıları podcast açıklama metnimizde ve RSS beslememizde sizleri bekliyor. Dinleyicilerimiz web oynatıcımızdan tüm kartları inceleyebilir.\n\n"
                "Ahmet: M1 Podcast'in bugünkü bölümünün sonuna geldik. Yarın yepyeni teknoloji başlıklarıyla tekrar görüşmek dileğiyle, hoşça kalın!\n\n"
                "Emel: Kendinize çok iyi bakın, bilimle ve teknolojiyle kalın!"
            )
        }
