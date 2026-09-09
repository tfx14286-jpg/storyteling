import asyncio
import re
from pathlib import Path

# Edge-TTS gratis dari Microsoft - tidak butuh API key, suara Indonesia natural
try:
    import edge_tts
    HAS_EDGE = True
except ImportError:
    HAS_EDGE = False

async def _edge_tts_save(text: str, output_path: Path, voice: str = "id-ID-ArdiNeural", rate: str = "+0%", volume: str = "+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    # Gunakan SubMaker untuk dapat SRT - support edge-tts 6.x dan 7.x
    from edge_tts import SubMaker
    submaker = SubMaker()
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                # edge-tts 7.x pakai feed(), 6.x pakai create_sub()
                if hasattr(submaker, "feed"):
                    submaker.feed(chunk)
                elif hasattr(submaker, "create_sub"):
                    submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
    # Simpan SRT jika ada word boundary
    srt_path = output_path.with_suffix(".srt")
    srt_text = None
    try:
        if hasattr(submaker, "get_srt"):
            # edge-tts 7.x
            if getattr(submaker, "cues", None):
                srt_text = submaker.get_srt()
        elif hasattr(submaker, "generate_subs"):
            if getattr(submaker, "subs", None):
                srt_text = submaker.generate_subs()
        elif hasattr(submaker, "subs") and submaker.subs:
            srt_text = str(submaker)
    except Exception:
        pass
    if srt_text and srt_text.strip():
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_text)
        return str(output_path), str(srt_path)
    # Fallback: buat SRT kasar kalau SubMaker kosong
    coarse = _make_coarse_srt(text, srt_path)
    return str(output_path), coarse

def _gtts_fallback(text: str, output_path: Path, lang: str = "id"):
    from gtts import gTTS
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(str(output_path))
    # gTTS tidak support SRT word-level, buat SRT kasar per kalimat
    srt_path = _make_coarse_srt(text, output_path.with_suffix(".srt"))
    return str(output_path), str(srt_path)

def _make_coarse_srt(text: str, srt_path: Path):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences or sentences == ['']:
        return None
    # Estimasi 2.5 kata per detik (~150 wpm)
    srt_lines = []
    t = 0.0
    for idx, sent in enumerate(sentences, 1):
        words = len(sent.split())
        dur = max(1.5, words / 2.5)
        start = _sec_to_srt(t)
        end = _sec_to_srt(t + dur)
        srt_lines.append(f"{idx}\n{start} --> {end}\n{sent.strip()}\n")
        t += dur + 0.3
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return str(srt_path)

def _sec_to_srt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

async def _generate_all_segments_async(segments, out_dir: Path, voice, rate, volume):
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    results = []
    for i, seg in enumerate(segments):
        out_path = out_dir / f"seg_{i:03d}.mp3"
        tasks.append((i, seg, out_path))
    
    # Generate sekuensial agar tidak rate-limited
    audios = []
    srts = []
    for i, seg, out_path in tasks:
        try:
            if HAS_EDGE:
                a, s = await _edge_tts_save(seg, out_path, voice=voice, rate=rate, volume=volume)
            else:
                raise ImportError("edge-tts not installed")
        except Exception as e:
            print(f"[TTS] seg {i} edge-tts gagal ({e}), fallback gTTS...")
            a, s = _gtts_fallback(seg, out_path)
        audios.append(a)
        srts.append(s)
        print(f"[TTS] seg {i+1}/{len(segments)} OK -> {out_path.name}")
    return audios, srts

def generate_tts_segments(segments, out_dir="output/audio", voice="id-ID-ArdiNeural", rate="+0%", volume="+0%"):
    """
    Generate TTS per segmen, return list path mp3 dan srt.
    Gratis 100% - pakai edge-tts, fallback gTTS.
    """
    out_dir = Path(out_dir)
    # Jalankan async loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    audios, srts = loop.run_until_complete(_generate_all_segments_async(segments, out_dir, voice, rate, volume))
    return audios, srts

def combine_audios_to_one(audios, output_path="output/voiceover.mp3"):
    """
    Gabungkan semua segmen mp3 jadi satu file pakai FFmpeg concat (gratis, tanpa pydub dependency berat).
    """
    from pathlib import Path
    import subprocess
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(audios) == 1:
        # Copy saja
        import shutil
        shutil.copy(audios[0], output_path)
        return str(output_path)
    
    # Buat file list untuk ffmpeg concat
    list_file = output_path.parent / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for a in audios:
            # ffmpeg concat butuh path dengan slash
            p = Path(a).resolve().as_posix()
            f.write(f"file '{p}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: pakai pydub/movepy concat jika ffmpeg copy gagal (beda codec)
        print("[TTS] ffmpeg concat copy gagal, coba re-encode...")
        cmd2 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c:a", "libmp3lame", str(output_path)]
        subprocess.run(cmd2, check=True)
    return str(output_path)

def get_available_voices():
    """Daftar voice Indonesia gratis edge-tts"""
    return [
        "id-ID-ArdiNeural (Pria, santai)",
        "id-ID-GadisNeural (Wanita, ceria)",
        "id-ID-ArdiNeural - rate +5% (lebih cepat)",
        "id-ID-GadisNeural - rate -5% (lebih pelan)",
    ]
