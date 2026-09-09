#!/usr/bin/env python3
"""
StoryTelling Video Generator - 100% GRATIS
Tanpa API key, pakai:
- edge-tts (Microsoft) untuk voiceover Indonesia
- Pollinations AI (Flux) untuk gambar
- MoviePy + FFmpeg untuk video

Cara pakai:
  python main.py --topik "Kehidupan di zaman Firaun" --durasi 2
  python main.py --naskah "file.txt"
  python main.py --contoh firaun
  python main.py --judul "Misteri Piramida" --naskah-file naskah.txt --voice id-ID-GadisNeural
"""

import argparse
import json
import sys
from pathlib import Path

# Pastikan import lokal
sys.path.insert(0, str(Path(__file__).parent))

from storyteller.script_gen import generate_script_gratis, count_estimated_duration
from storyteller.utils import split_narasi_to_segments, make_image_prompt, slugify, load_config
from storyteller.tts import generate_tts_segments, combine_audios_to_one
from storyteller.images import generate_images_for_segments
from storyteller.video import create_video_from_assets

def load_naskah_from_args(args, config):
    # 1. Mode contoh
    if args.contoh:
        contoh_path = Path(f"examples/{args.contoh}.json")
        if not contoh_path.exists():
            contoh_path = Path(__file__).parent / f"examples/{args.contoh}.json"
        if contoh_path.exists():
            data = json.loads(contoh_path.read_text(encoding="utf-8"))
            print(f"[INFO] Pakai contoh: {data.get('judul')}")
            return data.get("naskah"), data.get("judul"), data.get("voice", config["tts"]["voice"])
        else:
            print(f"[ERROR] contoh {args.contoh} tidak ditemukan di examples/")
            sys.exit(1)
    
    # 2. File naskah
    if args.naskah_file:
        p = Path(args.naskah_file)
        if not p.exists():
            print(f"[ERROR] file naskah tidak ditemukan: {p}")
            sys.exit(1)
        text = p.read_text(encoding="utf-8")
        judul = args.judul or p.stem
        return text, judul, args.voice or config["tts"]["voice"]
    
    # 3. Naskah langsung
    if args.naskah:
        return args.naskah, args.judul or "Video Storytelling", args.voice or config["tts"]["voice"]
    
    # 4. Generate dari topik
    if args.topik:
        print(f"[SCRIPT] Generate naskah gratis untuk topik: {args.topik}")
        naskah = generate_script_gratis(args.topik, durasi_menit=args.durasi, gaya=args.gaya)
        print(f"[SCRIPT] Panjang: {len(naskah.split())} kata, estimasi {count_estimated_duration(naskah)} menit")
        print(f"[SCRIPT] Preview: {naskah[:200]}...")
        judul = args.judul or args.topik
        return naskah, judul, args.voice or config["tts"]["voice"]
    
    print("[ERROR] Harus isi salah satu: --topik / --naskah / --naskah-file / --contoh")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="StoryTelling Video Generator GRATIS")
    parser.add_argument("--topik", type=str, help="Topik video, nanti di-generate jadi naskah (gratis, offline)")
    parser.add_argument("--durasi", type=int, default=2, help="Durasi target menit (default 2)")
    parser.add_argument("--gaya", type=str, default="storytelling santai dan informatif", help="Gaya naskah")
    parser.add_argument("--naskah", type=str, help="Naskah langsung (string)")
    parser.add_argument("--naskah-file", type=str, help="Path file .txt berisi naskah")
    parser.add_argument("--contoh", type=str, help="Pakai contoh: firaun")
    parser.add_argument("--judul", type=str, help="Judul video (untuk nama file)")
    parser.add_argument("--voice", type=str, help="Voice edge-tts: id-ID-ArdiNeural / id-ID-GadisNeural")
    parser.add_argument("--no-images", action="store_true", help="Skip generate gambar (pakai placeholder)")
    parser.add_argument("--bg-music", type=str, help="Path musik latar mp3 (optional)")
    parser.add_argument("--output", type=str, help="Path output mp4")
    
    args = parser.parse_args()
    config = load_config()
    
    print("="*60)
    print(" STORYTELLING VIDEO GENERATOR - GRATIS 100%")
    print(" TTS: edge-tts | Images: Pollinations AI | Video: FFmpeg")
    print("="*60)
    
    naskah, judul, voice = load_naskah_from_args(args, config)
    
    slug = slugify(judul)
    out_dir = Path("output") / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Simpan naskah
    (out_dir / "naskah.txt").write_text(naskah, encoding="utf-8")
    print(f"[INFO] Judul: {judul}")
    print(f"[INFO] Voice: {voice}")
    print(f"[INFO] Output dir: {out_dir}")
    
    # 1. Pecah jadi segmen
    segments = split_narasi_to_segments(naskah, max_chars=280)
    print(f"[INFO] Naskah dipecah jadi {len(segments)} scene")
    for i, s in enumerate(segments):
        print(f"  {i+1}. {s[:70]}...")
    
    # 2. Generate TTS
    print("\n[STEP 2/4] Generate Voiceover (edge-tts gratis)...")
    audio_dir = out_dir / "audio"
    audios, srts = generate_tts_segments(segments, out_dir=str(audio_dir), voice=voice, rate=config["tts"]["rate"], volume=config["tts"]["volume"])
    combined = combine_audios_to_one(audios, output_path=str(out_dir / "voiceover.mp3"))
    print(f"[OK] Voiceover: {combined}")
    
    # 3. Generate Images
    print("\n[STEP 3/4] Generate Gambar (Pollinations AI gratis)...")
    prompts = [make_image_prompt(s, style=config["video"].get("visual_style", "cinematic, ancient egypt") if "visual_style" in config["video"] else "cinematic, ancient egypt") for s in segments]
    # Simpan prompts
    (out_dir / "prompts.txt").write_text("\n".join([f"Scene {i+1}: {p}" for i,p in enumerate(prompts)]), encoding="utf-8")
    if args.no_images:
        # Buat placeholder saja
        from storyteller.images import _make_placeholder
        from pathlib import Path as P
        img_paths = []
        for i, seg in enumerate(segments):
            dest = out_dir / "images" / f"scene_{i:03d}.jpg"
            _make_placeholder(seg, dest, 1280, 720)
            img_paths.append(str(dest))
    else:
        img_paths = generate_images_for_segments(segments, prompts, out_dir=str(out_dir / "images"), width=config["image"]["width"], height=config["image"]["height"], model=config["image"]["model"])
    print(f"[OK] {len(img_paths)} gambar siap")
    
    # 4. Assembly Video
    print("\n[STEP 4/4] Assembly Video (MoviePy + FFmpeg)...")
    final_name = args.output or str(out_dir / f"{slug}.mp4")
    # Cari bg music jika tidak disediakan
    bg = args.bg_music
    if not bg:
        # cek assets/music
        music_dir = Path("assets/music")
        if music_dir.exists():
            mp3s = list(music_dir.glob("*.mp3"))
            if mp3s:
                bg = str(mp3s[0])
    try:
        final_path = create_video_from_assets(
            image_paths=img_paths,
            audio_paths=audios,
            output_path=final_name,
            srt_paths=srts,
            bg_music_path=bg,
            width=config["video"]["width"],
            height=config["video"]["height"],
            fps=config["video"]["fps"]
        )
        print("\n" + "="*60)
        print(f" SELESAI! Video jadi: {final_path}")
        print(f" Durasi estimasi: {count_estimated_duration(naskah)} menit")
        print(f" Folder: {out_dir}")
        print("="*60)
        print("\nTips: upload ke YouTube Shorts / Reels, tambahkan thumbnail di Canva gratis.")
    except Exception as e:
        print(f"[ERROR] Video gagal: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
