from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "storyteling", "gratis": True, "tts": "edge-tts", "image": "pollinations", "note": "Vercel Hobby timeout 10s, video full butuh backend long-run"}).encode())
