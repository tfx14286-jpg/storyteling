import subprocess
from pathlib import Path
import math

# Fix Pillow 10+ compatibility: Image.ANTIALIAS dihapus di Pillow 10, ganti ke LANCZOS
try:
    from PIL import Image as _PILImage
    if not hasattr(_PILImage, "ANTIALIAS"):
        _PILImage.ANTIALIAS = _PILImage.LANCZOS
    # moviepy 1.0.3 pakai PIL.Image.ANTIALIAS di resize.py, jadi patch harus global
    import PIL.Image
    if not hasattr(PIL.Image, "ANTIALIAS"):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
except Exception:
    pass

# MoviePy untuk assembly video - 100% gratis
try:
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeVideoClip, CompositeAudioClip,
        TextClip, concatenate_videoclips, concatenate_audioclips, ColorClip
    )
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

def probe_duration(audio_path: str) -> float:
    """Dapatkan durasi audio pakai ffprobe (gratis, dari ffmpeg)."""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return float(r.stdout.strip())
    except:
        # fallback tebak 5 detik
        return 5.0

def create_video_from_assets(
    image_paths,
    audio_paths,
    output_path="output/final_video.mp4",
    srt_paths=None,
    bg_music_path=None,
    width=1280,
    height=720,
    fps=24,
    style="cinematic"
):
    """
    Gabungkan image + audio per segmen jadi video final.
    - Tiap image ditampilkan selama durasi audionya
    - Ken Burns (zoom pelan) biar tidak statis
    - Subtitle dibakar ke video (jika ada)
    - Background music dicampur low volume
    100% gratis pakai MoviePy + FFmpeg.
    """
    if not HAS_MOVIEPY:
        return _create_video_ffmpeg_only(image_paths, audio_paths, output_path, bg_music_path)
    
    from PIL import Image
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0
    print("[VIDEO] Menyusun scene...")
    for i, (img_path, aud_path) in enumerate(zip(image_paths, audio_paths)):
        dur = probe_duration(aud_path)
        # Minimal 2 detik, maksimal 20 detik per scene
        dur = max(2.0, min(dur, 20.0))
        print(f"  scene {i+1}: dur {dur:.1f}s - {Path(img_path).name}")
        
        # Load image dan resize ke 1280x720 dengan crop center (cover)
        img_clip = ImageClip(img_path).set_duration(dur)
        # Resize + crop agar fill 16:9 tanpa distorsi
        img_clip = img_clip.resize(height=height)  # resize ke tinggi dulu
        # Jika lebar masih kurang, resize ke lebar
        if img_clip.w < width:
            img_clip = ImageClip(img_path).set_duration(dur).resize(width=width)
        # Crop center
        if img_clip.w > width or img_clip.h > height:
            x_center = img_clip.w / 2
            y_center = img_clip.h / 2
            img_clip = img_clip.crop(x_center=x_center, y_center=y_center, width=width, height=height)
        # Ken Burns: zoom in halus 100% -> 108% (disable jika ingin render cepat)
        # NOTE: efek zoom memperlambat render 3x, set ken_burns=False di config jika butuh cepat
        do_ken_burns = True
        try:
            from pathlib import Path as _P
            cfg = _P("config.json")
            import json as _j
            if cfg.exists():
                _c = _j.loads(cfg.read_text(encoding="utf-8"))
                do_ken_burns = _c.get("video", {}).get("ken_burns", True)
        except:
            pass
        if do_ken_burns:
            def zoom(t):
                return 1 + 0.08 * (t / dur)
            img_clip = img_clip.resize(lambda t: zoom(t))
            img_clip = img_clip.set_position("center")
        
        # Audio untuk clip ini
        audio = AudioFileClip(aud_path)
        # Potong/panjangkan audio agar match dur (seharusnya sudah match)
        if audio.duration > dur:
            audio = audio.subclip(0, dur)
        img_clip = img_clip.set_audio(audio)
        
        # Subtitle burn-in per segmen - coba TextClip (butuh ImageMagick), fallback ke Pillow
        if srt_paths and i < len(srt_paths) and srt_paths[i] and Path(srt_paths[i]).exists():
            try:
                txt = _srt_to_plain_text(srt_paths[i])
                if txt:
                    wrapped = _wrap_text(txt, 40)
                    txt_clip = None
                    # Coba TextClip dulu
                    try:
                        txt_clip = TextClip(
                            wrapped,
                            fontsize=48,
                            color="white",
                            font="Arial-Bold",
                            stroke_color="black",
                            stroke_width=2,
                            method="caption",
                            size=(width-120, None),
                            align="center"
                        ).set_duration(dur).set_position(("center", height*0.78))
                    except Exception as e_textclip:
                        # Fallback Pillow (tanpa ImageMagick) - 100% gratis
                        try:
                            txt_clip = _make_pillow_textclip(wrapped, width, height, dur)
                        except Exception as e2:
                            print(f"[VIDEO] subtitle fallback juga gagal scene {i}: {e2}")
                            txt_clip = None
                    if txt_clip:
                        img_clip = CompositeVideoClip([img_clip, txt_clip])
            except Exception as e:
                print(f"[VIDEO] subtitle gagal scene {i}: {e}")
        else:
            # Fallback subtitle dari teks segmen jika ada - skip jika tidak ada teks
            pass

        clips.append(img_clip)
        total_dur += dur

    if not clips:
        raise RuntimeError("Tidak ada clip video")

    print(f"[VIDEO] Concatenate {len(clips)} scenes, total {total_dur:.1f}s")
    final = concatenate_videoclips(clips, method="compose")

    # Tambah background music jika ada
    if bg_music_path and Path(bg_music_path).exists():
        try:
            bg = AudioFileClip(str(bg_music_path)).volumex(0.15)
            # Loop bg music jika lebih pendek dari video
            if bg.duration < final.duration:
                loops = math.ceil(final.duration / bg.duration)
                from moviepy.editor import concatenate_audioclips
                bg = concatenate_audioclips([bg]*loops).subclip(0, final.duration)
            else:
                bg = bg.subclip(0, final.duration)
            # Mix voice + bg
            final_audio = CompositeAudioClip([final.audio, bg])
            final = final.set_audio(final_audio)
            print(f"[VIDEO] BG music mixed: {bg_music_path}")
        except Exception as e:
            print(f"[VIDEO] BG music gagal: {e}")

    # Export
    print(f"[VIDEO] Rendering ke {output_path} ... (butuh waktu)")
    final.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger="bar"
    )
    # Cleanup
    final.close()
    for c in clips:
        try:
            c.close()
        except:
            pass
    print(f"[VIDEO] Selesai! {output_path} ({output_path.stat().st_size/1024/1024:.1f} MB)")
    return str(output_path)

def _make_pillow_textclip(text, width, height, duration):
    """
    Buat TextClip tanpa ImageMagick, pakai Pillow + ImageClip.
    Background semi-transparan hitam, teks putih dengan stroke.
    """
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    # Ukuran canvas teks: lebar video - margin, tinggi ~140px
    canvas_w = width - 80
    canvas_h = 150
    # Buat image transparan
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Font - coba Arial, fallback default
    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 44)
        except:
            font = ImageFont.load_default()
    # Wrap sudah dilakukan, split lines
    lines = text.split("\n")
    # Hitung total tinggi teks
    line_h = 50
    total_h = len(lines) * line_h
    y0 = (canvas_h - total_h) // 2
    # Gambar background hitam semi transparan di belakang teks
    # Hitung bounding box untuk background
    max_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
        w = bbox[2] - bbox[0]
        max_w = max(max_w, w)
    bg_pad = 18
    bg_x0 = (canvas_w - max_w)//2 - bg_pad
    bg_y0 = y0 - 10
    bg_x1 = bg_x0 + max_w + bg_pad*2
    bg_y1 = y0 + total_h + 10
    # Background hitam transparan
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle([bg_x0, bg_y0, bg_x1, bg_y1], radius=12, fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    # Gambar teks putih dengan stroke hitam
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=3)
        w = bbox[2] - bbox[0]
        x = (canvas_w - w)//2
        y = y0 + i*line_h
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255))
    # Convert ke numpy untuk ImageClip
    arr = np.array(img)
    # ImageClip butuh RGB, handle alpha sebagai mask
    clip = ImageClip(arr).set_duration(duration).set_position(("center", height*0.78))
    # Jika ImageClip tidak support RGBA, flatten ke RGB dengan mask
    return clip

def _srt_to_plain_text(srt_path):
    text = Path(srt_path).read_text(encoding="utf-8", errors="ignore")
    lines = []
    for line in text.splitlines():
        line=line.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        lines.append(line)
    return " ".join(lines)[:220]

def _wrap_text(text, width=40):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur + " " + w) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # Max 2 baris biar tidak nutupin video
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] += "..."
    return "\n".join(lines)

def _create_video_ffmpeg_only(image_paths, audio_paths, output_path, bg_music_path):
    """
    Fallback jika moviepy tidak ada: pakai ffmpeg concat langsung (lebih cepat, tapi tanpa subtitle burn).
    """
    print("[VIDEO] MoviePy tidak ada, pakai FFmpeg direct...")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Buat video per segmen lalu concat
    temp_dir = output_path.parent / "temp_ffmpeg"
    temp_dir.mkdir(exist_ok=True)
    seg_videos = []
    for i, (img, aud) in enumerate(zip(image_paths, audio_paths)):
        seg_out = temp_dir / f"seg_{i:03d}.mp4"
        dur = probe_duration(aud)
        # ffmpeg: loop image selama durasi audio
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(img),
            "-i", str(aud),
            "-c:v", "libx264", "-t", str(dur),
            "-pix_fmt", "yuv420p", "-vf", f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,zoompan=d=1:s=1280x720:fps=24",
            "-c:a", "aac", "-shortest",
            str(seg_out)
        ]
        subprocess.run(cmd, capture_output=True)
        seg_videos.append(seg_out)
    # Concat semua segmen
    list_file = temp_dir / "list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for v in seg_videos:
            f.write(f"file '{v.resolve().as_posix()}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)]
    subprocess.run(cmd, check=True)
    return str(output_path)
