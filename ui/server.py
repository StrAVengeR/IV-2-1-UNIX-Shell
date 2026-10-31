#!/usr/bin/env python3
"""Local server: keeps ONE persistent osh session and serves the process-tree UI.
Only for trusted local use (it runs real shell commands)."""
import json, os, subprocess, tempfile, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSH = os.path.join(ROOT, "osh")
PORT = 8765
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}

class Session:
    def __init__(self):
        self.lock = threading.Lock()
        self.cv = threading.Condition()
        self.start()

    def start(self):
        self.logpath = tempfile.mktemp(prefix="osh-", suffix=".jsonl")
        env = dict(os.environ, OSH_LOG=self.logpath, OSH_PROTO="1")
        self.p = subprocess.Popen([OSH], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, env=env, bufsize=0)
        self.buf, self.ready, self.code, self.last_out = b"", 0, 0, b""
        self.history = []
        threading.Thread(target=self.reader, daemon=True).start()
        with self.cv:
            self.cv.wait_for(lambda: self.ready >= 1, timeout=5)

    def reader(self):
        fd = self.p.stdout.fileno()
        while True:
            d = os.read(fd, 4096)
            if not d:
                break
            with self.cv:
                self.buf += d
                while True:
                    i = self.buf.find(b"\x01READY ")
                    j = self.buf.find(b"\n", i) if i >= 0 else -1
                    if i < 0 or j < 0:
                        break
                    self.last_out = self.buf[:i]
                    self.code = int(self.buf[i + 7:j] or 0)
                    self.buf = self.buf[j + 1:]
                    self.ready += 1
                self.cv.notify_all()

    def run(self, line):
        line = " ".join(line.splitlines())
        with self.lock:
            if self.p.poll() is not None:
                self.start()
            with self.cv:
                n = self.ready
            self.p.stdin.write((line + "\n").encode())
            with self.cv:
                self.cv.wait_for(lambda: self.ready > n or self.p.poll() is not None, timeout=20)
                done = self.ready > n
                out = self.last_out.decode(errors="replace") if done else ""
            if line.strip():
                self.history.append(line)
            ended = self.p.poll() is not None
            return {"output": out, "code": self.code if done else None, "ended": ended,
                    "timeout": not done and not ended}

    def tree(self):
        procs, cmds, shell = {}, {}, None
        try:
            with open(self.logpath) as f:
                events = [json.loads(l) for l in f if l.strip()]
        except OSError:
            events = []
        for e in events:
            if e["ev"] == "shell":
                shell = e["pid"]
            elif e["ev"] == "spawn":
                procs[e["pid"]] = {"pid": e["pid"], "cmd": e["cmd"], "bg": e["bg"], "seq": e["seq"],
                                   "state": "running", "code": None, "t": e["t"]}
                cmds.setdefault(e["seq"], e["line"])
            elif e["ev"] == "exit" and e["pid"] in procs:
                procs[e["pid"]].update(state="exited", code=e["code"])
        for p in procs.values():          # not yet reaped: ask the OS
            if p["state"] == "running":
                r = subprocess.run(["ps", "-o", "stat=", "-p", str(p["pid"])],
                                   capture_output=True, text=True).stdout.strip()
                if not r:
                    p["state"] = "gone"
                elif r.startswith("Z"):
                    p["state"] = "zombie"
        groups = [{"seq": s, "line": cmds[s],
                   "procs": [p for p in procs.values() if p["seq"] == s]} for s in sorted(cmds)]
        return {"shell": self.p.pid if shell is None else shell,
                "alive": self.p.poll() is None, "commands": groups, "history": self.history}

S = Session()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _ok_host(self):
        if self.headers.get("Host") not in ALLOWED_HOSTS:
            self._send(403, {"error": "bad host"}); return False
        return True
    def do_GET(self):
        if not self._ok_host(): return
        if self.path == "/api/tree": self._send(200, S.tree())
        elif self.path in ("/", "/index.html"):
            with open(os.path.join(ROOT, "ui", "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        else: self._send(404, {"error": "not found"})
    def do_POST(self):
        if not self._ok_host(): return
        n = int(self.headers.get("Content-Length") or 0)
        try: data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError: return self._send(400, {"error": "bad json"})
        if self.path == "/api/run":
            cmd = data.get("cmd")
            if not isinstance(cmd, str) or len(cmd) > 1000:
                return self._send(400, {"error": "cmd must be a string up to 1000 chars"})
            self._send(200, S.run(cmd))
        elif self.path == "/api/reset":
            with S.lock:
                if S.p.poll() is None:
                    S.p.stdin.close(); S.p.wait(timeout=5)
                S.start()
            self._send(200, {"ok": True})
        else: self._send(404, {"error": "not found"})

if __name__ == "__main__":
    if not os.path.exists(OSH):
        raise SystemExit("osh not built: run `make` first")
    print(f"Open http://127.0.0.1:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
