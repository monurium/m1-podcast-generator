# 🎙️ Migros OneCast AI

Günün en sıcak yapay zeka ve teknoloji gelişmelerini otomatik olarak toplayan, her haber için **çarpıcı başlıklar ve özetler** oluşturan, **Google Gemini 2.5 Flash TTS** ve **Microsoft Edge-TTS** çift sunuculu ses modelleriyle ~10 dakikalık diyalog podcast üreten açık kaynaklı otomatik podcast yayınlama sistemi.

---

## 🌟 Temel Özellikler

* **📡 14 Nitelikli Yapay Zeka Kaynağı:** Webrazzi AI, ShiftDelete AI, TechCrunch AI, The Verge AI, VentureBeat AI, MIT Tech Review AI, Wired AI, Ars Technica AI, IEEE Spectrum AI, MarkTechPost, SiliconANGLE AI, Synced Review kaynaklarından son 24 saatin filtrelenmiş haberleri.
* **⚡ 8-10 Başlıca Haber & Çarpıcı Özetler:** Her haber için vurucu başlık (`headline`), can alıcı noktalar (`key_points`) ve 2-3 cümlelik net özet (`summary`) üretir; podcast süresini ~10 dakikaya taşır.
* **🗣️ Çift Motorlu Doğal Seslendirme (Ahmet & Emel):**
  * **Google Gemini TTS (Varsayılan):** `gemini-2.5-flash-preview-tts` ile Ahmet (`Puck`) ve Emel (`Aoede`) ses modelleri.
  * **Microsoft Edge-TTS (Yedek/Hızlı):** `tr-TR-AhmetNeural` ve `tr-TR-EmelNeural` sesleri ile kesintisiz diyalog.
* **🎵 Otomatik Intro & Outro Entegrasyonu:** Her bölümün başına kurumsal jingle (`assets/audio/intro.mp3`) ve sonuna kapanış müziği (`assets/audio/outro.mp3`) 44.1 kHz stüdyo kalitesinde otomatik eklenir.
* **📻 Apple Podcasts & Spotify Uyumlu RSS 2.0:** Podcast oynatıcılarının bölüm açıklamalarına haberlerin çarpıcı başlık ve özetlerini otomatik yerleştirir.
* **🎧 Modern Web Oynatıcı:** GitHub Pages üzerinde çalışan, ses dalgası görselleştiricili, hız kontrollü ve haber kartlarını listeleyen modern koyu mod web arayüzü.
* **⚙️ GitHub Actions Otomasyonu:** Her sabah 06:00 UTC (09:00 TRT) veya tek tıkla (`workflow_dispatch`) otomatik podcast üretir ve yayına alır.

---

## 📁 Proje Dizin Yapısı

```
├── assets/
│   └── audio/
│       ├── intro.mp3            # Başlangıç jingle müziği
│       └── outro.mp3            # Kapanış jingle müziği
├── config/
│   └── podcast_config.json      # Podcast başlık, yazar, dil ve besleme ayarları
├── src/
│   ├── content_generator.py     # Haber tarama ve LLM prompt modülü (Gemini / DeepSeek / OpenAI)
│   ├── audio_generator.py       # Gemini TTS ve Edge-TTS motorları + Intro/Outro miksajı
│   ├── rss_builder.py           # Apple & Spotify RSS 2.0 XML üreticisi
│   └── publisher.py             # MP3 dağıtımı ve manifest yöneticisi
├── episodes/                    # Üretilen MP3 ses dosyaları
├── episodes_manifest.json       # Bölüm geçmişi ve meta verileri
├── index.html                   # Web oynatıcı arayüzü
├── main.py                      # Ana pipeline çalıştırıcı
├── podcast.xml                  # Canlı RSS 2.0 beslemesi
└── requirements.txt             # Python bağımlılıkları
```

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum
```bash
git clone https://github.com/monurium/m1-podcast-generator.git
cd m1-podcast-generator
pip install -r requirements.txt
```

### 2. Çevresel Değişkenler
`.env.example` dosyasını `.env` olarak kopyalayın:
```env
GEMINI_FREE_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
PODCAST_BASE_URL=https://monurium.github.io/m1-podcast-generator
```

### 3. Çalıştırma

* **Test Modu (Yerel Önizleme):**
  ```bash
  python main.py --test --tts gemini
  ```
* **Canlı Bölüm Üretimi & Yayınlama:**
  ```bash
  python main.py --tts gemini
  ```

---

## 📡 Canlı Bağlantılar

* **RSS Beslemesi:** [https://monurium.github.io/m1-podcast-generator/podcast.xml](https://monurium.github.io/m1-podcast-generator/podcast.xml)
* **Web Oynatıcı:** [https://monurium.github.io/m1-podcast-generator/](https://monurium.github.io/m1-podcast-generator/)
