"""Installed skills must have valid metadata, policies and reachable local references."""
from pathlib import Path
import importlib.util
import json
import re

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SKILLS = ROOT / "skills"
SKILL_NAMES = ["codeart2d", "generate2dmap", "generate2dmedia", "generate2dsprite", "video2dsprite"]
EXPLICIT_ONLY = {"generate2dmedia", "codeart2d"}
# Agent Skills spec keys plus the Claude Code extensions we accept.
FRONTMATTER_ALLOWED = {
    "name", "description", "license", "compatibility", "metadata", "allowed-tools",
    "argument-hint", "disable-model-invocation", "user-invocable", "model",
}
SCRIPT_REF = re.compile(
    r"(?:\$\{CLAUDE_SKILL_DIR\}/|(?P<owner>(?:skills|\.\.)/[\w-]+)/)?"
    r"(?P<path>scripts/[\w./-]+?\.(?:py|mjs|js))\b"
)


def _load_check_links():
    spec = importlib.util.spec_from_file_location("check_links", ROOT / "tools" / "check_links.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frontmatter(skill: str) -> tuple[dict, str]:
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    head = re.match(r"\A---\s*\n(.*?)\n---", text, re.S)
    assert head, f"Missing frontmatter in skills/{skill}/SKILL.md"
    return yaml.safe_load(head.group(1)), text


def test_expected_skill_set():
    found = sorted(p.name for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))
    assert found == SKILL_NAMES


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_skill_metadata(skill):
    metadata, _ = _frontmatter(skill)
    assert metadata["name"] == skill
    description = metadata.get("description")
    assert isinstance(description, str) and description.strip()
    assert len(description) <= 1024, f"{skill}: description is {len(description)} chars (max 1024)"
    unknown = set(metadata) - FRONTMATTER_ALLOWED
    assert not unknown, f"{skill}: frontmatter keys outside the allowlist: {sorted(unknown)}"


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_referenced_scripts_exist(skill):
    _, text = _frontmatter(skill)
    missing = []
    for m in SCRIPT_REF.finditer(text):
        owner = m.group("owner")
        base = SKILLS / skill if owner is None else (SKILLS / skill / owner if owner.startswith("..") else ROOT / owner)
        if not (base / m.group("path")).exists():
            missing.append(m.group(0))
    assert not missing, f"{skill}: SKILL.md names missing scripts: {sorted(set(missing))}"


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_commands_are_host_path_neutral(skill):
    """Commands must not assume the repo root or skill dir is the CWD."""
    _, text = _frontmatter(skill)
    bad = [line.strip() for line in text.splitlines()
           if re.search(r"\bpython3?\s+(?:skills|scripts)/", line)]
    assert not bad, f"{skill}: CWD-relative commands: {bad[:5]}"


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_commands_are_single_line(skill):
    _, text = _frontmatter(skill)
    continued = [line.strip() for line in text.splitlines()
                 if re.search(r"\bpython3?\b.*(?:\\|\^)\s*$", line)]
    assert not continued, f"{skill}: multi-line commands (use one line): {continued[:5]}"


ART_SKILLS = ["generate2dsprite", "generate2dmap"]
# Routing statements of designs that do not apply to the Arena Edition: the code-art-first
# routing the upstream owner rejected, and the upstream API-key/CLI routing that does not exist
# for an Arena agent.
STALE_ROUTING = ("48 px", "code-art envelope", "code art first", "codeart2d first", "inside the envelope",
                 "envelope first", "within the session cap", "consent for that request",
                 "consent for each request", "openai_api_key", "xai_api_key", "gemini_api_key",
                 "ark_api_key", "fal_key", "codex cli", "grok cli", "image-to-video clip per action",
                 "one clip per action")


@pytest.mark.parametrize("skill", SKILL_NAMES)
def test_no_stale_routing(skill):
    _, text = _frontmatter(skill)
    lowered = text.lower()
    stale = [phrase for phrase in STALE_ROUTING if phrase in lowered]
    assert not stale, f"{skill}: SKILL.md still routes by the old rules: {stale}"


@pytest.mark.parametrize("skill", ART_SKILLS)
def test_art_source_follows_the_arena_order(skill):
    """generate_image first, codeart2d only on request or with no image tool; every generation
    is staged and committed through generate2dmedia route_media.py."""
    _, text = _frontmatter(skill)
    section = text[text.index("## Art source"):]
    section = section[:section.index("\n## ", 1)]
    marks = [section.index(mark) for mark in ("generate_image", "codeart2d")]
    assert marks == sorted(marks), f"{skill}: Art source order {marks}"
    assert "route_media.py" in section


def test_video2dsprite_never_generates():
    _, text = _frontmatter("video2dsprite")
    lowered = text.lower()
    assert "no image-to-video" in lowered or "cannot generate video" in lowered
    assert "never generates" in lowered


def test_codeart2d_is_an_explicit_last_resort():
    metadata, _ = _frontmatter("codeart2d")
    description = metadata["description"].lower()
    assert "explicit-only" in description and "last resort" in description and "only when the user" in description


def test_no_broken_local_links():
    broken = _load_check_links().check(ROOT)
    report = [f"{d.relative_to(ROOT).as_posix()} -> {t} ({why})" for d, t, why in broken]
    assert not report, "Broken local links:\n" + "\n".join(report)


def test_arena_readme_present():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Arena" in readme and "generate_image" in readme
