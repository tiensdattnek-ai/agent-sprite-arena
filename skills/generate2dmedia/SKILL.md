---
name: generate2dmedia
description: The art-route layer of the Forge skills, Arena Edition. The Arena agent's only image route is its own generate_image tool and it has no image-to-video route. route_media.py stages every image job (prompt file, references, job.json), the agent calls generate_image and saves the result, and route_media.py commit records it (sha256, size, one JSON line, ledger) so provenance stays exact; video answers no-route (exit 3) and names the sheet or supplied-clip fallback. Also the capability check (forge_doctor.py) and the generation ledger (media_ledger.py). Use when a Forge skill needs a generated image, for the capability check, or when the user asks about routes, generations or spend. Not for planning, processing or QA of sprites, video frames or maps (generate2dsprite, video2dsprite, generate2dmap) or for code-drawn art (codeart2d).
---

# Generate 2D Media (Arena Edition)

The route layer. It makes raw media; the owning skill plans the asset before and checks it after.
On Arena there is exactly one image route - the calling agent's own `generate_image` tool - and
no video route at all. This skill is the deterministic protocol around that tool.

## Use when

- Any Forge skill (or its pipeline script) needs a generated image or a reference edit.
- Once per session, to see what works here (`forge_doctor.py`).
- The user asks about routes, past generations or the ledger.

## Do not use when

- Planning, keying, registering or packaging: [generate2dsprite](../generate2dsprite/SKILL.md), [video2dsprite](../video2dsprite/SKILL.md), [generate2dmap](../generate2dmap/SKILL.md).
- Code-drawn art the user asked for: [codeart2d](../codeart2d/SKILL.md).

## Route table

1. **arena:generate_image** (images): the agent's own `generate_image` tool. One call makes ONE
   image; the `images` parameter carries reference images (edits keep identity, references set
   style). No API key exists and none is needed; no per-call consent question.
2. **video**: MISSING by design. The Arena agent cannot make image-to-video clips. `resolve
   --kind video` and `video ...` print `no-route` and exit 3; the fallback is named in the JSON:
   sprite sheets from the approved master still ([generate2dsprite](../generate2dsprite/SKILL.md)),
   a user-supplied clip ([video2dsprite](../video2dsprite/SKILL.md)), or code-drawn animation on
   request ([codeart2d](../codeart2d/SKILL.md)). Never pretend a clip was generated.

## Capability check (once per session)

Run `python "<skill-dir>/scripts/forge_doctor.py" --host-tools generate_image --save <output>/doctor.json`
(`--host-tools none` if your tool list has no image tool). Its `ROUTES` block shows the image
route OK and the video route MISSING. If `encoding.stdout` fails, set `PYTHONUTF8=1`.

## Generate: the three-step protocol

Every generated image goes through one staging command, your own tool call, and one commit:

| Step | What happens |
|---|---|
| 1. Stage | `python "<skill-dir>/scripts/route_media.py" image --prompt-file <txt> --reference <png> --size 1024x1024 --out-dir <new>` (`--reference` repeatable, in the order the prompt names them). Writes `prompt.txt`, copies the references, writes `job.json`, prints one JSON line with `status: "agent-request"` and exits 4 (agent action required). |
| 2. Generate | You call your own `generate_image` tool with that exact prompt and those references in that order, then save the result as `<out-dir>/generated.png`. |
| 3. Commit | `python "<skill-dir>/scripts/route_media.py" commit --out-dir <staged>` checks the image, records sha256 and size, appends the ledger line and prints the canonical line: `{"status":"ok","route":"arena:generate_image","artifact":...,"sha256":...,"width":...,"height":...,"estimateUsd":null}`. |

- `resolve --kind image` answers `arena:generate_image`; `resolve --kind video` answers
  `no-route` and exits 3. `video ...` does the same and never touches a file.
- Errors print `error: ...` and exit 1; usage errors exit 2. Never claim a generation that did
  not happen; the commit line is the only proof, and its `sha256` is the provenance.
- Report the real returned size from the commit line, never the requested `--size`.
- Reference edits (fix one thing on an approved image): stage with the approved image as the
  FIRST reference and a prompt of the form "Reproduce the FIRST image exactly ... THE ONLY
  CHANGE: ..."; your `generate_image` call takes it through its `images` parameter.

## Arena tool notes (generate_image semantics)

- One call = one standalone image. Never ask for grids or multi-panels inside one prompt; a
  sprite SHEET is one image that happens to contain a grid, described as such in the prompt.
- `offer_options` shows the user two candidate images when the look is uncertain; use it for
  master stills and key art, not for every FX frame.
- Look at every generated PNG with `read_file` before approving anything; numbers cannot see
  identity, facing or text artifacts.
- The tool writes the file itself into the workspace; copy or move it to the staged
  `generated.png` path, then commit.

## Ledger

`route_media.py commit` appends `<project>/.forge/ledger.jsonl` (one ASCII JSON line: ts, route,
kind, artifact, sha256, promptSha256, `estimateUsd: null`). There is no money on Arena; counts
are the currency.

| Need | Command |
|---|---|
| What was generated in this project | `python "<skill-dir>/scripts/media_ledger.py" summary` |
| Newest generations with hashes | `python "<skill-dir>/scripts/media_ledger.py" show --last 10` |

## Commands

Run each tool as one line from the user's project root: `python "<skill-dir>/scripts/<tool>.py" ...`.
Staged jobs live in a new `--out-dir` inside the project. Results are raw media: hand them to the
owning skill for identity, size, alpha, motion and seam checks. Details: [route-media.md](references/route-media.md);
data contracts: `references/schemas/media.schema.json`.
