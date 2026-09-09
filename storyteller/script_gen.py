import re
import json
import requests

# Template naskah gratis tanpa API key - dipakai jika Ollama tidak tersedia
TEMPLATE_FIRAUN = """Bayangkan hidup di zaman Firaun, lebih dari tiga ribu tahun yang lalu. Sungai Nil adalah nadi kehidupan. Setiap tahun, airnya meluap dan menyuburkan tanah gersang menjadi lahan pertanian yang sangat subur.

Di pagi hari, rakyat Mesir kuno bangun sebelum matahari terbit. Para petani pergi ke ladang membawa cangkul dari kayu. Mereka menanam gandum dan jelai yang menjadi makanan utama seluruh kerajaan.

Sementara itu di pusat kota, para pekerja membangun piramida raksasa. Balok batu seberat berton-ton diangkut dengan kereta luncur kayu dan tenaga ribuan orang. Ini adalah proyek terbesar dalam sejarah manusia.

Kehidupan di istana sangat berbeda. Firaun dianggap sebagai dewa yang hidup. Ia tinggal di istana megah dengan dinding berhiaskan emas dan permata. Para pelayan selalu siap memenuhi keinginannya.

Malam hari di Mesir kuno sangat magis. Di bawah cahaya bintang dan obor, para pendeta melakukan ritual doa kepada Dewa Ra. Mereka percaya kehidupan setelah mati jauh lebih penting daripada kehidupan sekarang."""

def generate_script_gratis(topik: str, durasi_menit: int = 3, gaya: str = "storytelling santai"):
    """
    Generate naskah gratis 100% offline tanpa API key.
    Coba Ollama dulu (jika ada di localhost:11434), kalau gagal pakai template + expander.
    """
    # 1. Coba Ollama (gratis, lokal, no API key)
    ollama_script = _try_ollama(topik, durasi_menit, gaya)
    if ollama_script:
        return ollama_script

    # 2. Fallback: Template expander gratis
    return _expand_template(topik, durasi_menit)

def _try_ollama(topik, durasi_menit, gaya):
    try:
        # Cek Ollama tersedia
        r = requests.get("http://localhost:11434/api/tags", timeout=1.5)
        if r.status_code != 200:
            return None
        models = r.json().get("models", [])
        if not models:
            return None
        model = models[0].get("name", "llama3")
        # Estimasi panjang naskah: ~130 kata per menit
        target_kata = durasi_menit * 135
        prompt = f"""Kamu adalah penulis naskah video YouTube storytelling sejarah.
Topik: {topik}
Gaya: {gaya}
Durasi: {durasi_menit} menit (sekitar {target_kata} kata)
Tulis naskah narasi yang menarik, runtut, dan mudah dipahami untuk voiceover Indonesia.
Jangan pakai label pembicara. Hanya narasi paragraf panjang. Gunakan bahasa Indonesia santai tapi informatif.
Mulai langsung ke cerita tanpa pembukaan basa-basi."""
        res = requests.post("http://localhost:11434/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.8, "num_predict": target_kata * 2}
        }, timeout=60)
        if res.status_code == 200:
            txt = res.json().get("response", "").strip()
            # Bersihkan markdown
            txt = re.sub(r'^#+\s+', '', txt, flags=re.MULTILINE)
            txt = re.sub(r'\*\*(.*?)\*\*', r'\1', txt)
            if len(txt.split()) > 80:
                return txt
    except Exception:
        pass
    return None

def _expand_template(topik: str, durasi_menit: int):
    topik_lower = topik.lower()
    # Jika topik mengandung firaun/mesir, pakai template khusus
    if any(k in topik_lower for k in ["firaun", "pharaoh", "mesir", "egypt", "piramida", "cleopatra"]):
        base = TEMPLATE_FIRAUN
    else:
        # Template umum gratis
        base = f"""Pernahkah kamu membayangkan {topik}? Ini adalah kisah yang jarang diceritakan.

Pada awalnya, semua terlihat biasa saja. Namun di balik itu, ada rahasia besar yang mengubah cara kita memandang sejarah.

Kehidupan sehari-hari pada masa itu sangat berbeda dengan sekarang. Orang-orang harus berjuang setiap hari untuk bertahan hidup, dengan alat sederhana dan kepercayaan yang kuat.

Di pusat peradaban, para pemimpin membangun sesuatu yang luar biasa. Dengan teknologi terbatas, mereka menciptakan mahakarya yang bahkan hingga hari ini masih membuat kita takjub dan bertanya-tanya, bagaimana mereka melakukannya?

Dan ketika malam tiba, di bawah langit yang penuh bintang, mereka merenungkan makna hidup dan kematian. Sebuah filosofi yang hingga kini masih relevan dan menginspirasi kita semua."""

    # Sesuaikan panjang dengan durasi
    # base ~ 200 kata = ~1.5 menit. Duplikasi dengan variasi jika butuh lebih panjang
    words = base.split()
    target_words = durasi_menit * 135
    if len(words) < target_words:
        # Tambah paragraf penutup
        extra = f"\n\nItulah gambaran {topik}. Sebuah kisah tentang keagungan, perjuangan, dan misteri yang tidak pernah lekang oleh waktu. Jika kamu hidup di zaman itu, apakah kamu siap menghadapinya?"
        base = base + extra
        # Jika masih kurang, ulangi dengan rephrase sederhana
        while len(base.split()) < target_words:
            base += " " + extra
    
    # Potong jika terlalu panjang
    words = base.split()
    if len(words) > target_words + 50:
        base = " ".join(words[:target_words + 50])
        # Akhiri di titik
        if "." in base:
            base = base[:base.rfind(".")+1]
    
    return base.strip()

def count_estimated_duration(text: str, wpm: int = 135) -> float:
    words = len(text.split())
    return round(words / wpm, 1)
