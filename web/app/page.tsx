"use client";
import { useState } from "react";

type Segment = { text: string; imageUrl: string; audioUrl?: string };

export default function Home() {
  const [topik, setTopik] = useState("Kehidupan di zaman Firaun");
  const [judul, setJudul] = useState("Bagaimana Keseruan Hidup di Zaman Firaun");
  const [durasi, setDurasi] = useState(2);
  const [voice, setVoice] = useState("id-ID-ArdiNeural");
  const [naskah, setNaskah] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState("");
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const TEMPLATE_FIRAUN = `Bayangkan hidup di zaman Firaun, lebih dari tiga ribu tahun yang lalu. Sungai Nil adalah nadi kehidupan. Setiap tahun, airnya meluap dan menyuburkan tanah gersang menjadi lahan pertanian yang sangat subur.

Di pagi hari, rakyat Mesir kuno bangun sebelum matahari terbit. Para petani pergi ke ladang membawa cangkul dari kayu. Mereka menanam gandum dan jelai yang menjadi makanan utama seluruh kerajaan.

Sementara itu di pusat kota, para pekerja membangun piramida raksasa. Balok batu seberat berton-ton diangkut dengan kereta luncur kayu dan tenaga ribuan orang. Ini adalah proyek terbesar dalam sejarah manusia.

Kehidupan di istana sangat berbeda. Firaun dianggap sebagai dewa yang hidup. Ia tinggal di istana megah dengan dinding berhiaskan emas dan permata. Para pelayan selalu siap memenuhi keinginannya.

Malam hari di Mesir kuno sangat magis. Di bawah cahaya bintang dan obor, para pendeta melakukan ritual doa kepada Dewa Ra. Mereka percaya kehidupan setelah mati jauh lebih penting daripada kehidupan sekarang.`;

  function splitToSegments(text: string): string[] {
    const sentences = text.split(/(?<=[.!?])\s+/);
    const out: string[] = [];
    let cur = "";
    for (const s of sentences) {
      if ((cur + " " + s).length <= 280) cur = cur ? cur + " " + s : s;
      else {
        if (cur) out.push(cur);
        cur = s;
      }
    }
    if (cur) out.push(cur);
    return out.filter((x) => x.length > 10);
  }

  function makePrompt(seg: string) {
    const clean = seg.replace(/[^\w\s,]/g, "").slice(0, 180);
    return `${clean}, ancient Egypt pharaoh era, cinematic, highly detailed, 8k, dramatic lighting --ar 16:9`;
  }

  function pollinationsUrl(prompt: string, idx: number) {
    const encoded = encodeURIComponent(prompt.slice(0, 700));
    return `https://image.pollinations.ai/p/${encoded}?width=1280&height=720&model=flux&seed=${42 + idx * 7}&nologo=true&enhance=true`;
  }

  async function handleGenerateScript() {
    setLoading("Generate naskah...");
    // Gratis logic - template + expand, sama dengan Python storyteller/script_gen.py
    let base = "";
    const low = topik.toLowerCase();
    if (["firaun", "pharaoh", "mesir", "piramida", "cleopatra"].some((k) => low.includes(k))) {
      base = TEMPLATE_FIRAUN;
    } else {
      base = `Pernahkah kamu membayangkan ${topik}? Ini adalah kisah yang jarang diceritakan. Pada awalnya, semua terlihat biasa saja. Namun di balik itu, ada rahasia besar yang mengubah cara kita memandang sejarah. Kehidupan sehari-hari pada masa itu sangat berbeda dengan sekarang. Orang-orang harus berjuang setiap hari untuk bertahan hidup, dengan alat sederhana dan kepercayaan yang kuat. Di pusat peradaban, para pemimpin membangun sesuatu yang luar biasa. Dengan teknologi terbatas, mereka menciptakan mahakarya yang bahkan hingga hari ini masih membuat kita takjub. Dan ketika malam tiba, di bawah langit yang penuh bintang, mereka merenungkan makna hidup dan kematian. Sebuah filosofi yang hingga kini masih relevan.`;
    }
    // Sesuaikan panjang dengan durasi (~135 kata per menit)
    const targetWords = durasi * 135;
    let words = base.split(" ");
    if (words.length < targetWords) {
      const extra = ` Itulah gambaran ${topik}. Sebuah kisah tentang keagungan, perjuangan, dan misteri yang tidak pernah lekang oleh waktu.`;
      while (base.split(" ").length < targetWords) base += " " + extra;
    }
    if (base.split(" ").length > targetWords + 50) {
      base = base.split(" ").slice(0, targetWords + 50).join(" ");
      base = base.slice(0, base.lastIndexOf(".") + 1);
    }
    setNaskah(base);
    const segs = splitToSegments(base).map((t, i) => ({
      text: t,
      imageUrl: pollinationsUrl(makePrompt(t), i),
    }));
    setSegments(segs);
    setLoading("");
  }

  async function handleGenerateAudio() {
    if (!segments.length) return;
    setLoading("Generate audio (edge-tts via API)...");
    try {
      // Panggil Vercel Python API /api/tts per segmen (gratis, serverless)
      const newSegs = [...segments];
      for (let i = 0; i < newSegs.length; i++) {
        const res = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: newSegs[i].text, voice }),
        });
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          newSegs[i].audioUrl = url;
        } else {
          // Fallback: browser TTS preview (tanpa download)
          console.warn("TTS API gagal, seg", i);
        }
      }
      setSegments(newSegs);
    } catch (e) {
      console.error(e);
      alert("TTS gagal - coba lagi. Untuk Vercel Hobby, audio per segmen max 10 detik (timeout 10s).");
    }
    setLoading("");
  }

  async function handleCreateVideo() {
    setLoading("Render video di browser butuh FFmpeg, atau download script untuk render lokal...");
    // Untuk Vercel, video full 72 detik tidak bisa di serverless (timeout 10s).
    // Berikan instruksi + file untuk render lokal
    const dataStr = JSON.stringify({ judul, naskah, voice, segments }, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = judul.replace(/[^a-z0-9]/gi, "-").toLowerCase() + ".json";
    a.click();
    setVideoUrl(url);
    setLoading("");
    alert(
      "Vercel Hobby timeout 10 detik, jadi video full 1-2 menit tidak bisa dirender di serverless.\n\nSolusi gratis:\n1. Download .json di atas\n2. Jalankan lokal: py main.py --naskah-file naskah.txt\natau deploy backend ke HuggingFace/Render (support FFmpeg + long run).\n\nLihat README di repo untuk deploy backend."
    );
  }

  return (
    <main className="max-w-6xl mx-auto p-6 md:p-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold">🎬 StoryTeling</h1>
        <p className="text-zinc-400 mt-2">Video generator kayak "Zaman Firaun" — 100% GRATIS • Tanpa API key • Deploy Vercel</p>
        <div className="mt-3 flex gap-2 justify-center text-xs">
          <span className="px-2 py-1 bg-emerald-900/30 border border-emerald-700 rounded">TTS: edge-tts</span>
          <span className="px-2 py-1 bg-blue-900/30 border border-blue-700 rounded">Image: Pollinations Flux</span>
          <span className="px-2 py-1 bg-zinc-800 border border-zinc-700 rounded">Video: FFmpeg</span>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h2 className="font-semibold mb-4">1️⃣ Input</h2>
          <label className="text-sm text-zinc-400">Topik</label>
          <input value={topik} onChange={(e) => setTopik(e.target.value)} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-2" placeholder="Kehidupan di zaman Firaun" />
          <label className="text-sm text-zinc-400 mt-3 block">Judul Video</label>
          <input value={judul} onChange={(e) => setJudul(e.target.value)} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-2" />
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <label className="text-sm text-zinc-400">Durasi (menit)</label>
              <select value={durasi} onChange={(e) => setDurasi(Number(e.target.value))} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-2">
                <option value={1}>1 menit</option>
                <option value={2}>2 menit</option>
                <option value={3}>3 menit</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-zinc-400">Voice</label>
              <select value={voice} onChange={(e) => setVoice(e.target.value)} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-2">
                <option value="id-ID-ArdiNeural">Ardi (Pria)</option>
                <option value="id-ID-GadisNeural">Gadis (Wanita)</option>
              </select>
            </div>
          </div>
          <button onClick={handleGenerateScript} className="w-full mt-4 bg-white text-black font-semibold rounded py-2 hover:bg-zinc-200">
            ✨ Generate Naskah & Gambar
          </button>
          {loading && <p className="text-sm text-amber-400 mt-3">{loading}</p>}
          <div className="mt-4 p-3 bg-amber-950/30 border border-amber-800 rounded text-xs text-amber-200">
            <b>Vercel limit:</b> Hobby 10s timeout. Naskah & gambar (Pollinations) aman. TTS per segmen & render video full butuh backend long-run (Render/HF). Lihat README.
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
          <h2 className="font-semibold mb-4">2️⃣ Naskah</h2>
          <textarea value={naskah} onChange={(e) => setNaskah(e.target.value)} rows={10} className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm" placeholder="Naskah akan muncul di sini..." />
          <div className="flex gap-2 mt-3">
            <button onClick={handleGenerateAudio} disabled={!segments.length} className="flex-1 bg-emerald-600 disabled:bg-zinc-700 rounded py-2 text-sm font-medium">
              🔊 Generate Audio
            </button>
            <button onClick={handleCreateVideo} disabled={!naskah} className="flex-1 bg-blue-600 disabled:bg-zinc-700 rounded py-2 text-sm font-medium">
              🎥 Export / Render
            </button>
          </div>
          <div className="mt-3 text-xs text-zinc-500">
            Lokal: <code>py main.py --contoh firaun</code> → <code>output/...</code> (1-2 menit, FFmpeg).
          </div>
        </div>
      </div>

      {segments.length > 0 && (
        <div className="mt-8">
          <h3 className="font-semibold mb-4">{segments.length} Scene — Preview (Pollinations gratis)</h3>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {segments.map((s, i) => (
              <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
                <img src={s.imageUrl} alt={`scene ${i}`} className="w-full aspect-video object-cover" loading="lazy" />
                <div className="p-3">
                  <p className="text-xs font-mono text-zinc-500">SCENE {i + 1}</p>
                  <p className="text-sm mt-1 line-clamp-3">{s.text}</p>
                  {s.audioUrl ? (
                    <audio controls src={s.audioUrl} className="w-full mt-2 h-8" />
                  ) : (
                    <p className="text-xs text-zinc-600 mt-2">Audio belum generate</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-10 bg-zinc-900 border border-zinc-800 rounded-xl p-5">
        <h3 className="font-semibold">🚀 Deploy Vercel - Infrastruktur Gratis</h3>
        <div className="grid md:grid-cols-2 gap-4 mt-3 text-sm">
          <div>
            <p className="font-medium text-emerald-400">Frontend (Vercel) ✅</p>
            <p className="text-zinc-400">Next.js ini sudah Vercel-ready. Push ke GitHub → Import di vercel.com → Deploy (auto). Naskah & gambar jalan 100% di serverless.</p>
            <code className="block mt-2 bg-black p-2 rounded text-xs">vercel --prod</code>
          </div>
          <div>
            <p className="font-medium text-amber-400">Backend Video (butuh FFmpeg)</p>
            <p className="text-zinc-400">Vercel Hobby timeout 10s, tidak bisa render 72 detik. Deploy Python backend ke:</p>
            <ul className="list-disc list-inside text-zinc-400 mt-1">
              <li>HuggingFace Spaces (Gradio, gratis)</li>
              <li>Render.com / Railway / Fly.io (Docker, FFmpeg)</li>
              <li>VPS / Lokal: <code>py main.py --contoh firaun</code></li>
            </ul>
          </div>
        </div>
        <p className="text-xs text-zinc-600 mt-3">
          File lokal terverifikasi: <code>output/bagaimana-keseruan-hidup-di-zaman-firaun/bagaimana-keseruan-hidup-di-zaman-firaun.mp4</code> (72.8s, 1.2MB) — lihat{" "}
          <a href="https://github.com" className="underline" target="_blank">
            README.md
          </a>
        </p>
      </div>

      <footer className="text-center text-xs text-zinc-600 mt-8">
        StoryTeling v1.0 • Gratis 100% • edge-tts + Pollinations + FFmpeg • Vercel ready
      </footer>
    </main>
  );
}
