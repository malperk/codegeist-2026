"""HTTP front end of the runner, for Cloud Run.

POST /jobs        {"buggy": sha, "fixed": sha (optional), "test": "pkg.Class::method", "source": "<java>"}
                  -> 202 {"id": ...}; bisection runs in the background
GET  /jobs/<id>   -> {"status": "running" | "done" | "error", "result": {...}, "log": [...]}
POST /check       {"commit": sha, "test": "pkg.Class::method", "source": "<java>"}
                  -> 200 {"result": PASS|FAIL|NOCOMPILE|ERROR, "output": "...", "api": [...]}
                  runs the test once on one commit, synchronously (well under a minute), so the
                  agent can see whether its test reproduces the bug before asking for a bisection
GET  /health     -> ok

Every /jobs call must carry a Forge Invocation Token (FIT) issued to our app: a JWT signed
by Atlassian, checked against Atlassian's published keys, the app id (audience) and
expiry. No shared secret exists anywhere. Set ALLOW_UNAUTHENTICATED=1 only for local tests.

Jobs live in memory; the service runs with one instance and CPU always allocated, so a job
survives between requests but not a restart. That is enough for a demo and the benchmark.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jwt  # PyJWT

import sys
sys.path.insert(0, "/opt/app/harness")
from bisect_bic import bisect, class_under_test  # noqa: E402
from run_test import run  # noqa: E402
import re
import subprocess

GIT = os.environ.get("RUNNER_GIT", "/opt/commons-lang.git")
APP_ID = os.environ.get("FORGE_APP_ID", "")  # ari:cloud:ecosystem::app/<uuid>
JWKS_URL = "https://forge.cdn.prod.atlassian-dev.net/.well-known/jwks.json"
ALLOW_UNAUTH = os.environ.get("ALLOW_UNAUTHENTICATED") == "1"
MAX_SOURCE = 200_000

jobs: dict[str, dict] = {}
lock = threading.Lock()
jwks = jwt.PyJWKClient(JWKS_URL, cache_keys=True)


def authorised(header: str | None) -> bool:
    if ALLOW_UNAUTH:
        return True
    if not header or not header.startswith("Bearer ") or not APP_ID:
        return False
    token = header[7:]
    try:
        key = jwks.get_signing_key_from_jwt(token)
        # The docs do not name the algorithm; accept asymmetric ones only (never "none" or HMAC).
        jwt.decode(token, key.key, algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "PS256"],
                   audience=APP_ID,
                   issuer="forge/invocation-token", options={"require": ["exp", "aud", "iss"]})
        return True
    except Exception:  # any verification failure is a refusal
        return False


def write_test(test: str, source: str) -> str:
    cls = test.split("::")[0]
    d = tempfile.mkdtemp(prefix="agenttest-")
    path = Path(d) / "src/test/java" / (cls.replace(".", "/") + ".java")
    path.parent.mkdir(parents=True)
    path.write_text(source)
    return d


def public_api(commit: str, test: str, source: str, limit: int = 60) -> list[str]:
    """Public method signatures of the class under test at commit, those the test calls first."""
    cls = class_under_test(test)
    if not cls:
        return []
    text = None
    for name in (cls, cls.replace(".lang3.", ".lang.")):
        for d in ("src/main/java", "src/java"):
            r = subprocess.run(["git", "--git-dir", GIT, "show", f"{commit}:{d}/{name.replace('.', '/')}.java"],
                               capture_output=True)
            if r.returncode == 0:
                text = r.stdout.decode("utf-8", "replace")
                break
        if text:
            break
    if text is None:
        return [f"{cls} does not exist at {commit[:10]}"]
    sigs = [" ".join(m.group(0).split()) for m in
            re.finditer(r"public\s+(?:static\s+|final\s+|synchronized\s+)*[\w<>\[\],.? ]+?\s+\w+\s*\([^)]*\)", text)]
    simple = cls.rsplit(".", 1)[-1]
    sigs = [" ".join(m.group(0).split()) for m in
            re.finditer(rf"public\s+{simple}\s*\([^)]*\)", text)] + sigs  # constructors
    called = set(re.findall(r"\.(\w+)\s*\(", source)) | {simple}
    first = [s for s in sigs if re.search(r"\s(\w+)\s*\(", s).group(1) in called]
    rest = [s for s in sigs if s not in first]
    return (first + rest)[:limit]


def check(req: dict) -> dict:
    d = write_test(req["test"], req["source"])
    r = run(GIT, req["commit"], req["test"], d, timeout=30)
    out = r.get("log_tail") or r.get("reason") or ""
    out = re.sub(r"/(?:w|tmp)/[\w./-]*?(src/)", r"\1", out).replace("src/src/", "src/")
    body = {"result": r["result"], "commit": req["commit"], "seconds": r.get("seconds"), "output": out[-3000:]}
    if r["result"] == "NOCOMPILE":
        body["api"] = public_api(req["commit"], req["test"], req["source"])
    return body


def run_job(job_id: str, req: dict) -> None:
    job = jobs[job_id]
    try:
        d = write_test(req["test"], req["source"])
        job["result"] = bisect(GIT, req["buggy"], req["fixed"], req["test"], d,
                               log=lambda m: job["log"].append(m))
        job["status"] = "done"
    except Exception as e:
        job["status"] = "error"
        job["result"] = {"error": f"{type(e).__name__}: {e}"}
        job["log"].append(traceback.format_exc()[-1500:])


class Handler(BaseHTTPRequestHandler):
    def send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            return self.send(200, {"ok": True})
        if not authorised(self.headers.get("Authorization")):
            return self.send(401, {"error": "unauthorised"})
        if self.path.startswith("/jobs/"):
            job = jobs.get(self.path[6:])
            return self.send(200, job) if job else self.send(404, {"error": "no such job"})
        self.send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path not in ("/jobs", "/check"):
            return self.send(404, {"error": "not found"})
        if not authorised(self.headers.get("Authorization")):
            return self.send(401, {"error": "unauthorised"})
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_SOURCE:
            return self.send(413, {"error": "too large"})
        if self.path == "/check":
            try:
                req = json.loads(self.rfile.read(length))
                for k in ("commit", "test", "source"):
                    assert isinstance(req.get(k), str) and req[k], k
                assert re.fullmatch(r"[0-9a-f]{7,40}", req["commit"]), "commit"
                assert re.fullmatch(r"[\w.$]+::test\w*", req["test"]), "test must be pkg.Class::testMethod"
            except Exception as e:
                return self.send(400, {"error": f"bad request: {e}"})
            try:
                return self.send(200, check(req))
            except Exception as e:
                return self.send(500, {"error": f"{type(e).__name__}: {e}"})
        try:
            req = json.loads(self.rfile.read(length))
            for k in ("buggy", "test", "source"):
                assert isinstance(req.get(k), str) and req[k], k
            req["fixed"] = req.get("fixed") or ""  # optional: only the benchmark knows it
            assert "::" in req["test"], "test must be pkg.Class::method"
        except Exception as e:
            return self.send(400, {"error": f"bad request: {e}"})
        job_id = uuid.uuid4().hex[:12]
        with lock:
            jobs[job_id] = {"id": job_id, "status": "running", "request": {k: req[k] for k in ("buggy", "fixed", "test")},
                            "result": None, "log": []}
        threading.Thread(target=run_job, args=(job_id, req), daemon=True).start()
        self.send(202, {"id": job_id})

    def log_message(self, fmt, *args):  # one line per request on stdout for Cloud Logging
        print(json.dumps({"request": fmt % args}), flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("", int(os.environ.get("PORT", 8080))), Handler).serve_forever()
