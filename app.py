"""
Gradio Web UI - 100% Gratis
Jalankan: python app.py
Buka: http://localhost:7860
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

import gradio as gr
from storyteller.script_gen import generate_script_gratis, count_estimated_duration
from storyteller.utils import split_narasi_to_segments, make_image_prompt, slugify, load_config
from storyteller.tts import generate_tts_segments, combine_audios_to_one
from storyteller.images import generate_images_for_segments
from storyteller.video import create_video_from_assets

config = load_config()

def generate_from_topic(topik, durasi, gaya, voice, progress=gr.Progress(track_tqdm=True)):
    if not topik.strip():
        return "Topik kosong!", None, None
    naskah = generate_script_gratis(topik, durasi_menit=int(durasi), gaya=gaya)
    info = f"Generated {len(naskah.split())} kata, estimasi {count_estimated_duration(naskah)} menit."
    return naskah, info, None

def create_video_full(judul, naskah, voice, bg_music, progress=gr.Progress(track_tqdm=True)):
    if not naskah.strip():
        return None, "Naskah kosong!", ""
    if not judul.strip():
        judul = "Video Storytelling"
    
    slug = slugify(judul)
    out_dir = Path("output") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "naskah.txt").write_text(naskah, encoding="utf-8")
    
    progress(0.1, desc="Pecah naskah jadi scene...")
    segments = split_narasi_to_segments(naskah, max_chars=280)
    log = f"Judul: {judul}\nVoice: {voice}\nScene: {len(segments)}\n"
    for i,s in enumerate(segments):
        log += f"{i+1}. {s[:60]}...\n"
    
    progress(0.25, desc="Generate voiceover (edge-tts)...")
    audio_dir = out_dir / "audio"
    audios, srts = generate_tts_segments(segments, out_dir=str(audio_dir), voice=voice, rate="+0%")
    combine_audios_to_one(audios, str(out_dir / "voiceover.mp3"))
    log += f"\n✓ Voiceover {len(audios)} segmen\n"
    
    progress(0.5, desc="Generate gambar (Pollinations)...")
    prompts = [make_image_prompt(s) for s in segments]
    img_paths = generate_images_for_segments(segments, prompts, out_dir=str(out_dir / "images"), width=1280, height=720, model="flux")
    log += f"✓ {len(img_paths)} gambar\n"
    
    progress(0.75, desc="Assembly video...")
    final_path = str(out_dir / f"{slug}.mp4")
    bg_path = None
    if bg_music is not None:
        # bg_music dari gr.Audio adalah path file
        bg_path = bg_music
    # cari default bg jika tidak ada
    if not bg_path:
        md = Path("assets/music")
        if md.exists():
            mp3s = list(md.glob("*.mp3"))
            if mp3s:
                bg_path = str(mp3s[0])
    
    video_path = create_video_from_assets(img_paths, audios, final_path, srt_paths=srts, bg_music_path=bg_path)
    log += f"\n✓ VIDEO JADI: {video_path}\n"
    progress(1.0, desc="Selesai!")
    return video_path, log, video_path

with gr.Blocks(title="StoryTelling Generator Gratis", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🎬 StoryTelling Video Generator - GRATIS 100%
    **Tanpa API Key** | TTS: `edge-tts` | Gambar: `Pollinations AI` | Video: `FFmpeg`
    Bikin video seperti *"Hidup di Zaman Firaun"* cukup dari topik/judul.
    """)
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 1️⃣ Generate Naskah (Gratis, Offline)")
            topik = gr.Textbox(label="Topik Video", placeholder="contoh: Kehidupan di zaman Firaun, Misteri Piramida", value="Kehidupan di zaman Firaun")
            durasi = gr.Slider(1, 5, value=2, step=1, label="Durasi target (menit)")
            gaya = gr.Textbox(label="Gaya cerita", value="storytelling santai dan informatif")
            voice = gr.Dropdown(choices=["id-ID-ArdiNeural", "id-ID-GadisNeural"], value="id-ID-ArdiNeural", label="Suara Voiceover")
            btn_gen = gr.Button("✨ Generate Naskah", variant="secondary")
            info_naskah = gr.Textbox(label="Info", interactive=False)
        
        with gr.Column():
            gr.Markdown("### 2️⃣ Edit Naskah & Generate Video")
            judul = gr.Textbox(label="Judul Video", value="Bagaimana Keseruan Hidup di Zaman Firaun")
            naskah = gr.Textbox(label="Naskah (bisa edit manual)", lines=12, placeholder="Tulis naskah di sini atau generate dari topik...")
            bg_music = gr.Audio(label="Background Music (optional, mp3)", type="filepath")
            btn_video = gr.Button("🎥 Bikin Video Sekarang", variant="primary")
    
    with gr.Row():
        with gr.Column():
            log = gr.Textbox(label="Log Proses", lines=12)
        with gr.Column():
            video_out = gr.Video(label="Hasil Video")
    
    # Contoh cepat
    gr.Markdown("### 📚 Contoh Cepat")
    gr.Examples(
        examples=[
            ["Kehidupan di zaman Firaun", 2, "Bagaimana Keseruan Hidup di Zaman Firaun"],
            ["Misteri Piramida Giza", 2, "Misteri Piramida yang Belum Terpecahkan"],
            ["Kehidupan suku Maya kuno", 3, "Rahasia Peradaban Maya"],
        ],
        inputs=[topik, durasi, judul]
    )
    
    btn_gen.click(generate_from_topic, inputs=[topik, durasi, gaya, voice], outputs=[naskah, info_naskah, video_out])
    btn_video.click(create_video_full, inputs=[judul, naskah, voice, bg_music], outputs=[video_out, log, video_out])

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
