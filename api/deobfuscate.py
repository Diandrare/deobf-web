"""POST /api/deobfuscate  {code, engine: auto|v15|14.7|14.8|14.9, devirt: bool} -> {ok, output, log}"""
import json, os, shutil, subprocess, sys, tempfile
from http.server import BaseHTTPRequestHandler
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ENGINE = os.path.join(ROOT, "engine")
RUN_ENGINE = "/tmp/engine" if os.access("/tmp", os.W_OK) and not os.access(ROOT, os.W_OK) else SRC_ENGINE
MAX_BYTES = int(os.environ.get("DEOBF_MAX_BYTES", 3_000_000))
TIMEOUT = int(os.environ.get("DEOBF_TIMEOUT", 270))      # hobby plan: set ~50
BACKEND = os.environ.get("BACKEND_URL", "").rstrip("/")   # optional: forward to a Docker host


def _prepare():
    if RUN_ENGINE != SRC_ENGINE and not os.path.isdir(RUN_ENGINE):
        shutil.copytree(SRC_ENGINE, RUN_ENGINE)
    for n in ("luau", "luau-ast"):
        p = os.path.join(RUN_ENGINE, "bin", n)
        if os.path.exists(p):
            os.chmod(p, 0o755)


def run_job(code: bytes, engine="auto", devirt=True):
    _prepare()
    if not os.path.exists(os.path.join(RUN_ENGINE, "bin", "luau")):
        return {"ok": False, "log": "", "error": "Linux luau binary missing in engine/bin (see README step 1)."}
    d = tempfile.mkdtemp(prefix="job_", dir="/tmp")
    try:
        inp, out = os.path.join(d, "input.lua"), os.path.join(d, "result.lua")
        open(inp, "wb").write(code)
        if engine in ("14.7", "14.8", "14.9"):
            cmd = [sys.executable, "cli.py", inp, "-o", out, "--engine", engine]
        else:
            cmd = [sys.executable, "deob.py", inp, "-o", out, "--no-pypy"]
            if engine == "v15":
                cmd += ["--obfuscator", "luraph_v15"]
        cmd += ["--timeout", str(max(10, TIMEOUT - 10))]
        if not devirt:
            cmd.append("--no-devirt")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            p = subprocess.run(cmd, cwd=RUN_ENGINE, capture_output=True, timeout=TIMEOUT, env=env)
        except subprocess.TimeoutExpired:
            return {"ok": False, "log": "", "error": f"Timed out after {TIMEOUT}s. Try 'behaviour trace only' or a longer-running backend."}
        log = (p.stderr + p.stdout).decode("utf-8", "replace")[-6000:]
        if os.path.exists(out):
            return {"ok": True, "output": open(out, "rb").read().decode("latin-1"), "log": log}
        return {"ok": False, "log": log, "error": "No result produced."}
    finally:
        shutil.rmtree(d, ignore_errors=True)


class handler(BaseHTTPRequestHandler):
    def _send(self, status, obj):
        b = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if len(raw) > MAX_BYTES * 2:
                return self._send(413, {"ok": False, "error": "Input too large."})
            if BACKEND:
                rq = urllib.request.Request(BACKEND + "/api/deobfuscate", raw, {"Content-Type": "application/json"})
                with urllib.request.urlopen(rq, timeout=TIMEOUT) as r:
                    return self._send(200, json.loads(r.read()))
            req = json.loads(raw)
            code = (req.get("code") or "").encode("latin-1", "replace")
            if not code.strip():
                return self._send(400, {"ok": False, "error": "Empty input."})
            if len(code) > MAX_BYTES:
                return self._send(413, {"ok": False, "error": "Input too large."})
            self._send(200, run_job(code, str(req.get("engine", "auto")), bool(req.get("devirt", True))))
        except Exception as e:  # noqa: BLE001
            self._send(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
