import os
import json
import uuid
import datetime
from dotenv import load_dotenv

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.audio_generator import AudioGenerator
from src.rss_builder import RSSBuilder
from src.publisher import Publisher

load_dotenv()

def generate_microsoft_episode():
    print("=" * 65)
    print("🎙️ M1 PODCAST: MICROSOFT ÖZEL BÖLÜMÜ ÜRETİLİYOR")
    print("=" * 65)

    config_path = os.path.join("config", "podcast_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_url = os.getenv("PODCAST_BASE_URL", config.get("link", "https://monurium.github.io/m1-podcast-generator"))
    output_dir = config.get("output_dir", "dist")

    today_str = datetime.date.today().strftime('%Y%m%d')
    today_display = datetime.date.today().strftime('%d.%m.%Y')
    pub_date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    episode_data = {
        "title": f"M1 Podcast - Microsoft'un Yapay Zeka Hamlesi & Copilot Devrimi ({today_display})",
        "summary": "Microsoft'un yeni nesil Copilot ajanları, Windows 11 Copilot+ PC yenilikleri, Phi-4 küçük dil modelleri ve Azure AI altyapısındaki son dev gelişmeler masaya yatırılıyor.",
        "todays_topics": "Microsoft Copilot Workspace, Windows Copilot+ PC, Azure OpenAI o3 Entegrasyonu, Phi-4 Modelleri",
        "news_items": [
            {
                "headline": "Microsoft Copilot Workspace: Bağımsız Çalışan Otonom İş Ajanları Tanıtıldı",
                "key_points": [
                    "Copilot artık sadece komut bekleyen bir sohbet botu değil, arka planda görevleri tamamlayan otonom bir iş ortağı",
                    "Word, Excel, PowerPoint ve GitHub arasında çapraz iş akışlarını otomatik yürütüyor"
                ],
                "summary": "Microsoft, kurumsal üretkenliği yeni bir seviyeye taşıyan Copilot Workspace ekosistemini duyurdu. Yeni sistem, karmaşık projeleri adımlara bölerek ekip arkadaşı gibi bağımsız çalışabiliyor."
            },
            {
                "headline": "Windows 11 Copilot+ PC ve Yerel NPU Gücü: Buluta İhtiyaç Duymadan AI Deneyimi",
                "key_points": [
                    "40+ TOPS NPU gücüyle tüm işlemler cihaz üzerinde yerel olarak işleniyor",
                    "Gelişmiş Windows Recall ve canlı altyazı çevirisi sıfır gecikmeyle çalışıyor"
                ],
                "summary": "Microsoft, yeni nesil Surface ve iş ortağı dizüstü bilgisayarlarda yerel yapay zeka hızlandırmasını standart hale getirdi. Bu sayede veriler cihaz dışına çıkmadan yüksek performanslı analiz yapılabiliyor."
            },
            {
                "headline": "Microsoft Phi-4 ve Küçük Dil Modellerinde Yeni Standart: Verimlilik Zirvede",
                "key_points": [
                    "Çok daha az parametreyle devasa modellerin mantık yürütme skorlarına ulaşıldı",
                    "Mobil ve gömülü sistemlerde doğrudan çalışabilecek mimari"
                ],
                "summary": "Microsoft Araştırma ekibi tarafından geliştirilen Phi-4 modeli, matematiksel akıl yürütme ve kodlama kıyaslamalarında açık kaynak dünyasında yeni bir rekora imza attı."
            }
        ],
        "script": (
            "Ahmet: Merhaba değerli teknoloji meraklıları! M1 Podcast'e hepiniz hoş geldiniz. Bugün teknoloji dünyasının kalbine, yapay zekanın öncüsü Microsoft'un son dev hamlelerine odaklanıyoruz.\n\n"
            "Emel: Kesinlikle Ahmet! Microsoft, sadece yazılım tarafında değil, hem kurumsal iş akışlarında hem de donanım ekosisteminde kuralları baştan yazıyor. Bugün konuşacağımız çok heyecan verici başlıklar var.\n\n"
            "Ahmet: İlk ve en çarpıcı gelişmeyle başlayalım: Microsoft Copilot Workspace. Artık sohbet kutusuna bir şeyler yazıp cevap beklediğimiz günler geride kalıyor. Yeni Copilot ajanları, arka planda bağımsız olarak görevleri üstlenen otonom iş ortaklarına dönüştü.\n\n"
            "Emel: Evet Ahmet, düşünsenize; bir proje dosyasını, ilgili e-postaları ve kod deposunu Copilot'a veriyorsunuz; o sizin yerinize dökümantasyonu hazırlıyor, hataları tespit ediyor ve sunumu hazır hale getiriyor. Bu gerçekten şirketlerdeki iş yapış şeklini kökten değiştirecek bir adım.\n\n"
            "Ahmet: İşin donanım tarafında ise Copilot+ PC devrimi hız kesmeden büyüyor. Windows 11 ile entegre çalışan kırk TOPS üzeri NPU işlemciler sayesinde, yapay zeka artık buluta ihtiyaç duymadan doğrudan cihaz üzerinde çalışıyor. Bu hem sıfır gecikme hem de yüzde yüz veri gizliliği anlamına geliyor.\n\n"
            "Emel: Gizlilik konusu özellikle kurumlar için kritikti. Bunun yanı sıra Microsoft Araştırma ekibinin geliştirdiği Phi-4 küçük dil modelleri de açık kaynak dünyasını salladı. Küçük boyutuna rağmen dev modellere taş çıkaran bir mantık yürütme performansı sergiliyor.\n\n"
            "Ahmet: Microsoft'un yapay zeka ekosistemindeki bu liderliği teknoloji dünyasını şekillendirmeye devam edecek. Günün tüm detayları, önemli noktaları ve özetleri RSS beslememizde sizleri bekliyor. Yarın yeni gelişmelerle tekrar görüşmek üzere!\n\n"
            "Emel: Kendinize çok iyi bakın, teknolojiyle ve M1 Podcast ile kalın!"
        )
    }

    # Synthesize Audio
    audio_gen = AudioGenerator()
    episode_id = f"ep_{today_str}_microsoft_{uuid.uuid4().hex[:6]}"
    os.makedirs(os.path.join("output", "temp"), exist_ok=True)
    temp_audio_path = os.path.join("output", "temp", f"{episode_id}.mp3")

    print("\n[1/3] 🎙️ Türkçe 2-Sunuculu (Ahmet & Emel) Microsoft Özel Bölümü Seslendiriliyor...")
    audio_meta = audio_gen.dialogue_to_audio(episode_data["script"], temp_audio_path)

    # Save to Publisher and Manifest
    print("\n[2/3] 💾 Bölüm manifest ve dağıtım klasörüne kaydediliyor...")
    publisher = Publisher(output_dir=output_dir)
    full_episode_dict = {
        "id": episode_id,
        "title": episode_data["title"],
        "summary": episode_data["summary"],
        "todays_topics": episode_data["todays_topics"],
        "news_items": episode_data["news_items"],
        "script": episode_data["script"],
        "pub_date": pub_date,
        "file_size": audio_meta["file_size"],
        "duration_formatted": audio_meta["duration_formatted"],
        "duration_seconds": audio_meta.get("duration_seconds", 0)
    }
    all_episodes = publisher.add_episode(full_episode_dict, temp_audio_path, base_url)

    # Build fresh RSS
    print("\n[3/3] 📡 RSS 2.0 XML (podcast.xml) sıfırdan oluşturuluyor...")
    rss_builder = RSSBuilder(config=config)
    rss_dist_path = os.path.join(output_dir, config.get("feed_filename", "podcast.xml"))
    rss_root_path = config.get("feed_filename", "podcast.xml")
    
    rss_builder.build_feed(all_episodes, rss_dist_path)
    rss_builder.build_feed(all_episodes, rss_root_path)

    print("\n" + "=" * 65)
    print("🎉 MICROSOFT ÖZEL PODCAST BÖLÜMÜ VE TEMİZ RSS BAŞARIYLA OLUŞTURULDU!")
    print(f"📄 Bölüm: {episode_data['title']}")
    print(f"⏱️ Süre: {audio_meta['duration_formatted']}")
    print(f"📡 RSS Beslemesi: {base_url.rstrip('/')}/{config.get('feed_filename', 'podcast.xml')}")
    print("=" * 65)

if __name__ == "__main__":
    generate_microsoft_episode()
