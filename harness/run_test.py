"""Run one JUnit test against one commit of an old Apache Commons Lang checkout.

The commit is exported with `git archive` from a local clone, optional test files are laid on
top (for example the developer's test from the fixed commit, or an agent-written test), and
everything is compiled and run with JDK 8 inside Docker without network access.

Result is one of PASS, FAIL (the test ran and failed), NOCOMPILE (the test does not compile
against this commit, e.g. the code under test does not exist yet) or ERROR (infrastructure).
Only PASS and FAIL count as evidence; ERROR is never read as "the bug is present".

Usage:
  python3 run_test.py --git-dir REPO.git --commit SHA --test pkg.Class::method \
      [--overlay-from SHA_OR_DIR] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIB = Path(os.environ.get("RUNNER_LIB", HERE.parent / ".cache" / "lib"))
IMAGE = "eclipse-temurin:8-jdk"
MAIN_DIRS = ["src/main/java", "src/java"]
TEST_DIRS = ["src/test/java", "src/test"]


def git(git_dir: str, *args: str, binary: bool = False):
    out = subprocess.run(["git", "--git-dir", git_dir, *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode()


def export(git_dir: str, commit: str, dest: Path) -> None:
    tar = git(git_dir, "archive", "--format=tar", commit, binary=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=tar, check=True)


def first_existing(root: Path, candidates: list[str]) -> str | None:
    return next((c for c in candidates if (root / c).is_dir()), None)


def test_file(test_dir: str, cls: str) -> str:
    return f"{test_dir}/{cls.replace('.', '/')}.java"


def read_test_source(git_dir: str, source: str, cls: str) -> bytes:
    """Read a test class from another commit (any known layout or package name) or a directory."""
    base = cls.replace("org.apache.commons.lang3.", "org.apache.commons.lang.")
    names = [base, base.replace("org.apache.commons.lang.", "org.apache.commons.lang3.", 1)]
    for d, cls in [(d, n) for n in names for d in TEST_DIRS]:
        rel = test_file(d, cls)
        if os.path.isdir(source):
            if (Path(source) / rel).is_file():
                return (Path(source) / rel).read_bytes()
        else:
            try:
                return git(git_dir, "show", f"{source}:{rel}", binary=True)
            except subprocess.CalledProcessError:
                continue
    raise FileNotFoundError(cls)


def run(git_dir: str, commit: str, test: str, overlay_from: str | None, timeout: int = 300) -> dict:
    started = time.time()
    cls = test.split("::")[0]
    with tempfile.TemporaryDirectory(prefix="lang-") as tmp:
        work = Path(tmp)
        src = work / "src"
        src.mkdir()
        export(git_dir, commit, src)
        main_dir, test_dir = first_existing(src, MAIN_DIRS), first_existing(src, TEST_DIRS)
        if not main_dir or not test_dir:
            return {"result": "ERROR", "reason": "unknown source layout", "seconds": 0}
        # Commons Lang 3 renamed the package org.apache.commons.lang -> lang3. Older commits
        # get the test translated back so one test can be bisected across the rename.
        old_pkg = (not (src / main_dir / "org/apache/commons/lang3").is_dir()
                   and (src / main_dir / "org/apache/commons/lang").is_dir())
        if old_pkg:
            cls = cls.replace("org.apache.commons.lang3.", "org.apache.commons.lang.")
            test = test.replace("org.apache.commons.lang3.", "org.apache.commons.lang.")
        rel = test_file(test_dir, cls)
        if overlay_from:
            try:
                body = read_test_source(git_dir, overlay_from, cls)
            except FileNotFoundError:
                return {"result": "ERROR", "reason": f"test class {cls} not in {overlay_from}"}
            if old_pkg:
                body = body.replace(b"org.apache.commons.lang3", b"org.apache.commons.lang")
            else:
                body = body.replace(b"org.apache.commons.lang.", b"org.apache.commons.lang3.")
                cls = cls.replace("org.apache.commons.lang.", "org.apache.commons.lang3.")
                test = test.replace("org.apache.commons.lang.", "org.apache.commons.lang3.")
                rel = test_file(test_dir, cls)
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            (src / rel).write_bytes(body)
        if not (src / rel).exists():
            return {"result": "ERROR", "reason": f"test file {rel} missing at {commit[:10]}"}
        # Lang 2.x has a package named `enum`, which is a keyword from Java 5 on.
        source = "1.4" if (src / main_dir / "org/apache/commons/lang/enum").is_dir() else "1.6"
        shutil.copy(HERE / "SingleTest.java", work / "SingleTest.java")
        local = os.environ.get("RUNNER_MODE") == "local"  # already inside the JDK 8 image
        wdir, deps = (str(work), str(LIB)) if local else ("/w", "/deps")
        script = f"""
set -e
cd {wdir}
mkdir -p out/main out/test out/h
find src/{main_dir} -name '*.java' > main.txt
DEPS=$(ls {deps}/*.jar | tr '\\n' ':')
for enc in UTF-8 ISO-8859-1; do
  if javac -nowarn -source {source} -target {source} -encoding $enc -cp "$DEPS" -d out/main @main.txt 2> main.err; then ok=1; break; fi
done
[ -n "$ok" ] || {{ echo 'RESULT ERROR main compile'; tail -20 main.err; exit 2; }}
CP=out/main:$(ls {deps}/*.jar | tr '\\n' ':')
javac -nowarn -encoding UTF-8 -source 1.6 -target 1.6 -cp "$CP" -sourcepath src/{test_dir} \
   -d out/test src/{rel} 2> test.err || javac -nowarn -encoding ISO-8859-1 -source 1.6 -target 1.6 \
   -cp "$CP" -sourcepath src/{test_dir} -d out/test src/{rel} 2> test.err || \
   {{ echo 'RESULT NOCOMPILE test compile'; tail -30 test.err; exit 2; }}
javac -nowarn -cp "$CP" -d out/h SingleTest.java
cd src && timeout {timeout} java -cp "../out/test:../out/main:{test_dir}:$(echo $CP | sed 's#out/main#../out/main#'):../out/h" SingleTest '{test}'
"""
        cmd = (["bash", "-c", script] if local else
               ["docker", "run", "--rm", "--network", "none", "-v", f"{work}:/w", "-v", f"{LIB}:/deps:ro",
                IMAGE, "bash", "-c", script])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        line = next((l for l in out.splitlines() if l.startswith("RESULT ")), "RESULT ERROR no result")
        verdict = line.split()[1]
        return {"result": verdict, "commit": commit, "test": test, "source_level": source,
                "seconds": round(time.time() - started, 1), "detail": line,
                "log_tail": "\n".join(out.splitlines()[-15:])}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--git-dir", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--test", required=True)
    p.add_argument("--overlay-from")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    r = run(a.git_dir, a.commit, a.test, a.overlay_from)
    print(json.dumps(r, indent=1) if a.json else f"{r['result']} {r.get('detail', r.get('reason'))}")
    sys.exit({"PASS": 0, "FAIL": 1}.get(r["result"], 2))


if __name__ == "__main__":
    main()
