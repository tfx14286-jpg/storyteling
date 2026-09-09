# StoryTelling Video Generator - GRATIS 100%

Bikin video storytelling kayak YouTube "Hidup di Zaman Firaun" otomatis, tanpa API key berbayar.

## Gratis pakai:
- **TTS**: `edge-tts` (Microsoft Edge, suara Indonesia `id-ID-ArdiNeural`/`GadisNeural` natural)
- **Images**: `Pollinations AI` (model Flux, no API key)
- **Video**: `MoviePy` + `FFmpeg` (sudah terinstall)
- **Naskah**: Generator offline + Ollama (jika ada) - tanpa OpenAI

## Install (sekali)
```bash
python -m pip install -r requirements.txt
```

## Cara Pakai - CLI

### 1. Dari topik (generate naskah otomatis)
```bash
python main.py --topik "Kehidupan di zaman Firaun" --durasi 2 --voice id-ID-ArdiNeural
```

### 2. Dari contoh firaun
```bash
python main.py --contoh firaun
```

### 3. Dari file naskah
```bash
python main.py --naskah-file naskah.txt --judul "Misteri Piramida"
```

### 4. Pakai background music
```bash
python main.py --contoh firaun --bg-music assets/music/bgm.mp3
```

Output di `output/<judul-slug>/<judul>.mp4`

## Cara Pakai - Web UI (Gradio)
```bash
python app.py
# buka http://localhost:7860
```

## Struktur Output
```
output/bagaimana-keseruan-hidup-di-zaman-firaun/
  naskah.txt
  prompts.txt
  audio/seg_000.mp3 ...
  images/scene_000.jpg ...
  voiceover.mp3
  bagaimana-keseruan-hidup-di-zaman-firaun.mp4
```

## Config
Edit `config.json` untuk ganti voice, ukuran video, model gambar.

## Tips YouTube
- Voice `ArdiNeural` untuk sejarah serius, `GadisNeural` untuk ceria
- Durasi 2-3 menit ideal untuk storytelling
- Tambah musik latar pelan (volume 15% otomatis)
- Subtitle otomatis dibakar ke video
