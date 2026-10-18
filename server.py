"""Docker/VPS entrypoint: same API + static UI.  python server.py  (PORT env, default 8080)"""
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from api.deobfuscate import handler as ApiHandler

class H(ApiHandler, SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(os.path.dirname(__file__), "public"), **k)
    def do_POST(self):
        if self.path.startswith("/api/deobfuscate"):
            return ApiHandler.do_POST(self)
        self.send_error(404)
    def do_OPTIONS(self):
        self.send_response(204); self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type"); self.end_headers()

ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", 8080))), H).serve_forever()
