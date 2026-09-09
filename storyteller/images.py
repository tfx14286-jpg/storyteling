import time
import requests
from pathlib import Path
from urllib.parse import quote
import hashlib

# Pollinations AI - 100% gratis, tanpa API key
# Dokumentasi: https://github.com/pollinations/pollinations

def pollinations_url(prompt: str, width=1280, height=720, model="flux", seed=None, nologo=True, enhance=True):
    """
    Generate URL Pollinations. Setiap URL unik akan generate image baru.
    Model: flux, turbo, etc.
    """
    if seed is None:
        # Seed dari hash prompt biar konsisten tapi unik per segmen
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16) % 100000
    # Encode prompt untuk URL
    encoded = quote(prompt[:800])  # limit 800 char
    base = f"https://image.pollinations.ai/p/{encoded}"
    params = f"?width={width}&height={height}&model={model}&seed={seed}&nologo={str(nologo).lower()}&enhance={str(enhance).lower()}"
    return base + params

def download_image(url: str, dest: Path, timeout=30, retries=2):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StoryTellingTool/1.0"
    }
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, stream=True)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                # Validasi file > 5KB
                if dest.stat().st_size > 5000:
                    return True
                else:
                    print(f"[IMG] file terlalu kecil, retry...")
            else:
                print(f"[IMG] status {r.status_code} content-type {r.headers.get('Content-Type')}")
        except Exception as e:
            print(f"[IMG] error attempt {attempt+1}: {e}")
        if attempt < retries:
            time.sleep(2)
    return False

def generate_images_for_segments(segments, prompts, out_dir="output/images", width=1280, height=720, model="flux"):
    """
    Generate 1 gambar per segmen pakai Pollinations gratis.
    Returns list path gambar.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []
    
    for i, (seg, prompt) in enumerate(zip(segments, prompts)):
        dest = out_dir / f"scene_{i:03d}.jpg"
        # Jika sudah ada dan valid, skip
        if dest.exists() and dest.stat().st_size > 5000:
            print(f"[IMG] scene {i+1}/{len(segments)} sudah ada -> skip")
            image_paths.append(str(dest))
            continue
        
        url = pollinations_url(prompt, width=width, height=height, model=model, seed=42+i*7)
        print(f"[IMG] scene {i+1}/{len(segments)} generating...")
        print(f"      prompt: {prompt[:80]}...")
        ok = download_image(url, dest)
        if ok:
            print(f"      -> OK {dest.name} ({dest.stat().st_size//1024} KB)")
            image_paths.append(str(dest))
        else:
            # Fallback: buat placeholder image dengan teks
            print(f"      -> GAGAL, buat placeholder")
            _make_placeholder(seg, dest, width, height)
            image_paths.append(str(dest))
        
        # Jeda sopan biar tidak rate-limit (Pollinations gratis tapi jangan spam)
        if i < len(segments) - 1:
            time.sleep(1.2)
    
    return image_paths

def _make_placeholder(text: str, dest: Path, width, height):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (width, height), color=(20, 25, 40))
    draw = ImageDraw.Draw(img)
    # Coba font default
    try:
        # Wrap text
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur + " " + w) < 45:
                cur = f"{cur} {w}".strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        lines = lines[:6]
        y = height // 2 - len(lines)*22
        for line in lines:
            # center
            bbox = draw.textbbox((0,0), line)
            w = bbox[2]-bbox[0]
            draw.text(((width-w)//2, y), line, fill=(220, 220, 220))
            y += 44
        # Watermark
        draw.text((20, height-40), "StoryTelling - Placeholder", fill=(120,120,120))
    except Exception:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=85)
