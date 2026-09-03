# 🎙️ M1 Podcast Generator

Günün en sıcak yapay zeka ve teknoloji gelişmelerini otomatik olarak toplayan, her haber için **çarpıcı başlıklar ve özetler** oluşturan ve **doğal Türkçe Neural ses modelleri** ile ~10 dakikalık diyalog podcast üreten açık kaynaklı otomatik podcast yayınlama sistemi.

---

## 🌟 Temel Özellikler

* **📡 Güncel Haber Taraması:** Webrazzi, ShiftDelete, Chip TR, DonanımHaber, Evrim Ağacı, TechCrunch, The Verge ve Wired gibi önde gelen teknoloji kaynaklarını tarar.
* **⚡ 8 Başlıca Haber & Çarpıcı Özetler:** Her haber için vurucu başlık (`headline`), can alıcı noktalar (`key_points`) ve 2-3 cümlelik net özet (`summary`) üretir.
* **🗣️ Türkçe 2-Sunuculu Doğal Seslendirme:** Microsoft Edge-TTS Neural sesleri ile **Ahmet** (`tr-TR-AhmetNeural`) ve **Emel** (`tr-TR-EmelNeural`) arasında akıcı, samimi radyo diyaloğu.
* **📻 Apple Podcasts & Spotify Uyumlu RSS 2.0:** Podcast oynatıcılarının bölüm açıklamalarına haberlerin çarpıcı başlık ve özetlerini otomatik yerleştirir.
* **🎧 Modern Web Oynatıcı:** GitHub Pages üzerinde çalışan, ses dalgası görselleştiricili, hız kontrollü ve haber kartlarını listeleyen modern koyu mod web arayüzü.
* **⚙️ GitHub Actions Otomasyonu:** İsteğe bağlı olarak (`workflow_dispatch`) tek tıkla GitHub Actions üzerinden yeni bölüm üretir ve RSS beslemesini günceller.

---

## 📁 Proje Dizin Yapısı

```
├── config/
│   └── podcast_config.json      # Podcast başlık, yazar, dil ve besleme ayarları
├── src/
│   ├── content_generator.py     # Haber tarama ve LLM prompt modülü
│   ├── audio_generator.py       # Türkçe Edge-TTS ses sentezi
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
DEEPSEEK_API_KEY=your_api_key_here
PODCAST_BASE_URL=https://monurium.github.io/m1-podcast-generator
```

### 3. Çalıştırma

* **Test Modu (Yerel Önizleme):**
  ```bash
  python main.py --test
  ```
* **Canlı Bölüm Üretimi & Yayınlama:**
  ```bash
  python main.py
  ```

---

## 📡 Canlı Bağlantılar

* **RSS Beslemesi:** [https://monurium.github.io/m1-podcast-generator/podcast.xml](https://monurium.github.io/m1-podcast-generator/podcast.xml)
* **Web Oynatıcı:** [https://monurium.github.io/m1-podcast-generator/](https://monurium.github.io/m1-podcast-generator/)
