import re
import json
import hashlib
from pathlib import Path

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')[:50] or "story"

def split_narasi_to_segments(narasi: str, max_chars: int = 280):
    """
    Pecah naskah panjang jadi segmen per kalimat / scene.
    Setiap segmen akan jadi 1 gambar + 1 potongan voiceover.
    max_chars ~ 15-20 detik per scene (ideal untuk video storytelling).
    """
    # Bersihkan naskah
    narasi = re.sub(r'\s+', ' ', narasi.strip())
    if not narasi:
        return []
    
    # Pecah per kalimat (titik, tanda seru, tanda tanya)
    sentences = re.split(r'(?<=[.!?])\s+', narasi)
    
    segments = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Jika ditambah kalimat ini masih di bawah limit, gabung
        if len(current) + len(s) + 1 <= max_chars:
            current = f"{current} {s}".strip() if current else s
        else:
            if current:
                segments.append(current.strip())
            # kalimat terlalu panjang -> paksa pecah per koma
            if len(s) > max_chars:
                parts = re.split(r',\s+|\s+dan\s+|\s+yang\s+', s)
                buf = ""
                for p in parts:
                    if len(buf) + len(p) < max_chars:
                        buf = f"{buf}, {p}".strip(", ") if buf else p
                    else:
                        if buf:
                            segments.append(buf.strip())
                        buf = p
                if buf:
                    current = buf
                else:
                    current = ""
            else:
                current = s
    if current:
        segments.append(current.strip())
    
    # Pastikan minimal 5 segmen untuk video 1 menit, maksimal 20
    return [s for s in segments if len(s) > 10]

def make_image_prompt(segment_text: str, style: str = "cinematic, ancient egypt"):
    """
    Ubah segmen narasi jadi prompt image yang optimal untuk Pollinations/Flux.
    """
    # Hapus tanda baca berlebihan untuk prompt
    clean = re.sub(r'[^\w\s,]', '', segment_text)[:200]
    base = f"{style}, highly detailed, 8k, dramatic lighting, historical accurate"
    # Tambah konteks firaun jika ada keyword sejarah
    keywords = ["firaun", "mesir", "piramida", "sungai nil", "cleopatra", "pharaoh", "egypt"]
    has_history = any(k in segment_text.lower() for k in keywords)
    if has_history:
        base = "ancient Egypt, pharaoh era, " + base
    return f"{clean}, {base} --ar 16:9"

def load_config(path="config.json"):
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    p2 = Path(__file__).parent.parent / "config.json"
    if p2.exists():
        return json.loads(p2.read_text(encoding="utf-8"))
    return {}

def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
