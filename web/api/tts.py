from http.server import BaseHTTPRequestHandler
import json
import asyncio
import tempfile
from pathlib import Path

# Vercel Python serverless - gratis edge-tts
# Note: Vercel Hobby 10s timeout, jadi 1 segmen ~3-7 detik masih aman, tapi 5 segmen harus dipanggil satu-per-satu dari frontend

async def _tts_save(text: str, voice: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = Path(tmp.name)
    tmp.close()
    await communicate.save(str(tmp_path))
    data = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    return data

def _gtts_fallback(text: str):
    from gtts import gTTS
    import io
    tts = gTTS(text=text, lang="id", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8') if length else "{}"
        try:
            data = json.loads(body)
            text = data.get("text", "")[:500]  # limit biar tidak timeout
            voice = data.get("voice", "id-ID-ArdiNeural")
            if not text:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "text kosong"}).encode())
                return
            # coba edge-tts dulu, fallback gTTS jika 403/timeout (Vercel IP kadang diblock Microsoft)
            audio_bytes = None
            last_err = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_bytes = loop.run_until_complete(_tts_save(text, voice))
                loop.close()
            except Exception as e:
                last_err = str(e)
                print(f"edge-tts gagal: {e}, fallback gTTS...")
                try:
                    audio_bytes = _gtts_fallback(text)
                except Exception as e2:
                    last_err = f"edge-tts: {last_err} | gTTS: {e2}"
            if audio_bytes and len(audio_bytes) > 1000:
                self.send_response(200)
                self.send_header('Content-type', 'audio/mpeg')
                self.send_header('Content-Length', str(len(audio_bytes)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(audio_bytes)
            else:
                raise Exception(last_err or "gagal generate audio")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
