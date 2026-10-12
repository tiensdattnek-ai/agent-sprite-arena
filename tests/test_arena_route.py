"""The Arena route layer: staging, commit, no-route video, doctor and ledger."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).parents[1]
MEDIA = ROOT / "skills" / "generate2dmedia" / "scripts"


def run_cli(args, cwd=None, env_extra=None):
    import os
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          cwd=cwd or ROOT, env=env, timeout=120)


def last_json(stdout: str) -> dict:
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    return json.loads(lines[-1])


def make_image(path: Path, size=(64, 48), color=(255, 0, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


@pytest.fixture()
def project(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("a test sprite on flat magenta\n", encoding="utf-8")
    ref = tmp_path / "ref.png"
    make_image(ref)
    return tmp_path, prompt, ref


def test_resolve_image_names_the_arena_route():
    result = run_cli([str(MEDIA / "route_media.py"), "resolve", "--kind", "image"])
    assert result.returncode == 0
    summary = last_json(result.stdout)
    assert summary["status"] == "ok" and summary["route"] == "arena:generate_image"


def test_resolve_video_is_no_route():
    result = run_cli([str(MEDIA / "route_media.py"), "resolve", "--kind", "video"])
    assert result.returncode == 3
    summary = last_json(result.stdout)
    assert summary["status"] == "no-route" and summary["route"] is None
    assert "generate2dsprite" in summary["fallback"] and "video2dsprite" in summary["fallback"]


def test_video_verb_is_always_no_route(project, tmp_path):
    _, prompt, _ = project
    out = tmp_path / "vid"
    result = run_cli([str(MEDIA / "route_media.py"), "video", "--prompt-file", str(prompt),
                      "--duration", "6", "--out-dir", str(out)])
    assert result.returncode == 3
    summary = last_json(result.stdout)
    assert summary["status"] == "no-route"
    assert not out.exists(), "a video request must not touch the filesystem"


def test_stage_commit_and_ledger_round_trip(project, tmp_path):
    root, prompt, ref = project
    out = root / "media" / "take1"
    staged = run_cli([str(MEDIA / "route_media.py"), "image", "--prompt-file", str(prompt),
                      "--reference", str(ref), "--size", "1024x1024",
                      "--route", "auto", "--dry-run", "--out-dir", str(out)], cwd=root)
    assert staged.returncode == 4, staged.stderr
    summary = last_json(staged.stdout)
    assert summary["status"] == "agent-request" and summary["route"] == "arena:generate_image"
    assert (out / "job.json").is_file() and (out / "prompt.txt").is_file()
    assert (out / "reference01.png").is_file()
    job = json.loads((out / "job.json").read_text(encoding="utf-8"))
    assert job["status"] == "agent-request" and job["size"] == "1024x1024"

    # the agent step: save the generate_image result as generated.png
    make_image(out / "generated.png", size=(128, 96))
    committed = run_cli([str(MEDIA / "route_media.py"), "commit", "--out-dir", str(out)], cwd=root)
    assert committed.returncode == 0, committed.stderr
    line = last_json(committed.stdout)
    assert line["status"] == "ok" and line["route"] == "arena:generate_image"
    assert line["width"] == 128 and line["height"] == 96 and line["estimateUsd"] is None
    assert len(line["sha256"]) == 64

    job = json.loads((out / "job.json").read_text(encoding="utf-8"))
    assert job["status"] == "committed" and job["sha256"] == line["sha256"]

    ledger = (root / ".forge" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(ledger) == 1
    entry = json.loads(ledger[0])
    assert entry["route"] == "arena:generate_image" and entry["sha256"] == line["sha256"]
    assert entry["status"] == "done" and entry["estimateUsd"] is None

    summary = last_json(run_cli([str(MEDIA / "media_ledger.py"), "summary"], cwd=root).stdout)
    assert summary["entries"] == 1 and summary["perRoute"] == {"arena:generate_image": 1}
    show = run_cli([str(MEDIA / "media_ledger.py"), "show", "--last", "5"], cwd=root)
    assert line["sha256"] in show.stdout


def test_commit_refuses_a_missing_artifact(project):
    root, prompt, ref = project
    out = root / "media" / "take2"
    run_cli([str(MEDIA / "route_media.py"), "image", "--prompt-file", str(prompt),
             "--reference", str(ref), "--out-dir", str(out)], cwd=root)
    result = run_cli([str(MEDIA / "route_media.py"), "commit", "--out-dir", str(out)], cwd=root)
    assert result.returncode == 1
    assert "artifact missing" in result.stderr


def test_stage_refuses_an_existing_out_dir(project):
    root, prompt, ref = project
    out = root / "media" / "take3"
    out.mkdir(parents=True)
    result = run_cli([str(MEDIA / "route_media.py"), "image", "--prompt-file", str(prompt),
                      "--reference", str(ref), "--out-dir", str(out)], cwd=root)
    assert result.returncode == 1


def test_doctor_declares_the_arena_route(tmp_path):
    save = tmp_path / "doctor" / "doctor.json"
    result = run_cli([str(MEDIA / "forge_doctor.py"), "--host-tools", "generate_image",
                      "--save", str(save)])
    assert result.returncode == 0, result.stderr
    report = json.loads(save.read_text(encoding="utf-8"))
    routes = {r["kind"]: r for r in report["routes"]}
    assert routes["image"]["route"] == "arena:generate_image" and routes["image"]["status"] == "OK"
    assert routes["video"]["status"] == "MISSING" and routes["video"].get("remedy")
    assert report["routeOrder"] == ["arena:generate_image"]


def test_doctor_undeclared_tool_is_agent_status():
    result = run_cli([str(MEDIA / "forge_doctor.py"), "--host-tools", "none", "--json"])
    report = json.loads(result.stdout)
    image_route = next(r for r in report["routes"] if r["kind"] == "image")
    assert image_route["status"] == "AGENT" and report["routeOrder"] == []
