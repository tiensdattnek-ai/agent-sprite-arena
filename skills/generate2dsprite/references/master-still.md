# Master still: one approved still per character

Every character animation starts from one approved **master still**. Each action (idle, walk, run, attack, jump, hurt, cast) is then one generated sprite sheet made from that same still (Arena has no image-to-video; see [sheet-set-handoff.md](sheet-set-handoff.md)). `scripts/master_still.py` makes the master: it writes the prompt, applies fixes as edit prompts, pads the chosen still to the class framing and writes `master.json`, the record that every motion step reads.

The recipe is the one that shipped in game-opus55 (base_kanetsugu.txt, base_nobu_v2a.txt and the `_pad` stills). The prompt wording behind it is in [prompt-rules.md](prompt-rules.md).

## The flow (Arena)

1. Write a spec: a JSON file, flags, or both (flags win).
2. Run `prompt`; it writes `prompt.txt`, `spec.json` and `run.json`.
3. Generate 1-3 takes with your own `generate_image` tool using that prompt (and the references of `run.json` `references`, in order); save them as `<run>/take1.png`, `<run>/take2.png`, ... and stage/commit each through generate2dmedia `route_media.py` for provenance.
4. LOOK at every take with `read_file` and pick one. Check the identity, the facing, that nothing touches an edge and that no text appears.
5. Fix a near-miss with `edit --prompt-only` ("Reproduce the FIRST image exactly ... THE ONLY CHANGE: ...") and generate that prompt with the chosen take as the FIRST reference. Never re-roll a good still for a small fix.
6. Run `approve` with the chosen still. It pads the still and writes `master.png` and `master.json`.
7. Make the action sheets from `master.png`, reusing `identity_recap` verbatim in every sheet prompt.

Run each command as one line from the project root. `<skill-dir>` is this skill's folder.

```text
python "<skill-dir>/scripts/master_still.py" prompt --spec art/specs/fox.json --output-dir art/master/fox-prompt
# agent: generate_image with art/master/fox-prompt/prompt.txt -> art/master/fox-prompt/take1.png ...
python "<skill-dir>/scripts/master_still.py" pad --input art/master/fox-prompt/take2.png --spec art/specs/fox.json --output-dir art/master/fox-pad2
python "<skill-dir>/scripts/master_still.py" edit --run art/master/fox-prompt --take 2 --change "make the cloak dark blue" --prompt-only --output-dir art/master/fox-edit1
# agent: generate_image with the edit prompt and take2 as FIRST reference -> art/master/fox-edit1/take1.png
python "<skill-dir>/scripts/master_still.py" approve --run art/master/fox-prompt --still art/master/fox-prompt/take1.png --route arena:generate_image --output-dir art/master/fox
python "<skill-dir>/scripts/master_still.py" edit --master art/master/fox --change "repaint the face to match the SECOND image" --extra-reference art/refs/fox-face.png --extra-role "her portrait: it shows her real face" --prompt-only --output-dir art/master/fox-edit2
```

Every command writes a new `--output-dir`: it refuses an existing one, stages its work beside it and publishes only a finished folder. It prints one ASCII JSON line. Errors print `error: ...` and exit 1; usage errors exit 2. The `generate` and `edit` verbs without `--prompt-only` still call route_media.py, which on Arena stages an `agent-request` (exit 4) instead of generating: use the `prompt`/`--prompt-only` flow above.

## The spec

`generate2dsprite.master_spec.v1`. Relative paths in a spec file are relative to that file. Flags use the same names with dashes (`--facing-parts`, `--identity-ref`, ...). The reference details are `--identity-ref-what`, `--identity-copy`, `--style-ref-what` and `--style-dont-copy`. `--identity-file` reads a long description from a UTF-8 file, and `--ban` adds to `extra_bans`.

| Field | Meaning | Default |
|---|---|---|
| `name` | asset id: 1-64 letters, digits, `.`, `_`, `-` | required |
| `subject` | short noun phrase: what it is ("a young fox ranger, full body") | required |
| `identity` | long, precise visual description: face, hair, body, costume colours, held items | required |
| `pose` | stance or pose of the still | none |
| `recap` | identity recap for motion prompts, a noun phrase that reads after "The same" | `subject (identity)` |
| `facing` | `left`, `right`, `front`, `back`, `none` | `right` (props `none`) |
| `facing_parts` | parts named in the facing sentence | `face, gaze and chest` (props `front`) |
| `view` | camera words | `side view (profile to three-quarter)` for left and right |
| `class` | framing preset: `hero`, `mob`, `boss`, `prop` | `hero` |
| `finish` | `hd` or `pixel`: sets the style line | `hd` |
| `key` | flat key colour (`#RRGGBB`, `magenta`, `green`, `blue`) | `#FF00FF` |
| `genre` | the game, written into the style line ("for a side-scrolling action game") | none |
| `pronoun` | `he`, `she`, `it`, `they` | `they` |
| `identity_ref` | `{path, what, copy}`: the FIRST attached image, copied exactly | none |
| `style_ref` | `{path, what, do_not_copy}`: an approved in-game peer sprite; an empty `do_not_copy` drops that clause | none |
| `allowed_text` | the one written mark allowed (a crest symbol); all other text stays banned | none |
| `extra_bans` | extra "no ..." items | `[]` |
| `opaque_parts` | parts named in the opaque-pixels sentence ("hair, spear, flames") | none |
| `extra` | one more art-direction paragraph, placed before the background line | none |

On PowerShell, quote a hex key (`--key "#00FF00"`), or the `#` starts a comment; `--key green` works everywhere. Choose green or blue for purple and pink designs. `pad` and `approve` warn when more than 0.5% of the subject's colours lean to the key.

## What the prompt says

`build_prompt` writes the game-opus55 contract, one paragraph per part:

1. `Create exactly ONE square image (1024x1024).` Host tools return about 1254x1254; the pad normalises the size.
2. The style line of the finish, then the text bans: `No text, no letters, no numbers, no logo, no watermark, no signature, no UI, no border, no frame, no grid.`
3. The reference roles: the FIRST attached image is the identity ("copy ... exactly"). The SECOND is an approved in-game peer sprite: "match its style, outline weight, shading, figure size and position on the canvas; do NOT copy ...".
4. The subject with the facing stated three ways (`clearly FACING LEFT:`, the parts turned toward the LEFT edge, forward and back), then the identity and the pose.
5. The framing as canvas-edge percentages, "nothing touching or crossing the edges", and "solid, fully opaque pixels: no transparency, no semi-transparent glow, no soft aura".
6. `Background: solid flat pure magenta #FF00FF everywhere outside the character, no shadow, no ground, no glow on the background.`

The route adds its own tool instructions and saves the file, so the prompt holds art direction only.

## Class framing

Each class has one framing, identical for every character of that class. The prompt asks for some margin, because generators draw larger than asked. The pad then moves the subject to the exact target on the 1024x1024 canvas.

| Class | The prompt asks for | Pad target | Evidence |
|---|---|---|---|
| `hero` | top 14%, bottom 14% (72% tall), centred | 788 px tall, top margin 138 px, centred | base_kanetsugu_pad, base_chiyome_pad |
| `mob` | top 35%, bottom 15% (50% tall), body behind centre | 471 px tall, top margin 406 px, centre 100 px away from the facing side | base_ashigaru_pad, base_akazonae_pad |
| `boss` | top 14%, bottom 8% (78% tall), centred | 728 px tall, top margin 221 px, centred | base_kage_pad |
| `prop` | top 20%, bottom 20% (60% tall), centred | 614 px tall, top margin 205 px, centred | none |

These are generation framings. Display sizes come later: one body height per character, mobs no taller than the hero, a boss about twice the hero. `--subject-height`, `--top-margin` and `--lead` override a preset; the record then says `"preset": "custom"`.

## generate: the Arena route

On Arena the agent's own `generate_image` tool makes the takes; Python cannot call it, so the
flow is `prompt` -> agent generates -> `approve`:

1. `prompt` writes `prompt.txt`, `spec.json` and `run.json`; `run.json` lists the references to
   attach, in order.
2. The agent calls `generate_image` once per take (1-3 takes; `offer_options` when the look is
   open), saves them as `<run>/take1.png`, `<run>/take2.png`, ... and optionally stages/commits
   each through generate2dmedia `route_media.py` for the sha256/ledger record.
3. `approve --run <prompt dir> --still <take> --route arena:generate_image` pads it and writes
   the master.

For scripted pipelines the staging contract is the three-step protocol of
[generate2dmedia](../../generate2dmedia/SKILL.md): `route_media.py image --prompt-file
<run>/prompt.txt --reference <identity> --reference <peer> --size 1024x1024 --out-dir
<run>/takes/take-NN` stages the job (exit 4, `status: agent-request`), the agent saves its
`generate_image` result as `<out-dir>/generated.png`, and `route_media.py commit --out-dir
<out-dir>` prints the canonical `{"status": "ok", "route": "arena:generate_image", ...}` line
that decides the take.

The legacy `generate` verb still exists and calls route_media.py once per take; on Arena each
call stages an `agent-request` (exit 4) instead of producing an image, so the verb records
failed takes. Use the flow above instead. `FORGE_ROUTE_MEDIA_FAKE=<script.py>` substitutes a
fake for tests; a fake is recorded in `run.json` (`media.cli_source`), printed as a warning and
warned again by `approve`, so a fake take is never mistaken for a real generation.

## edit: fix by edit

`edit` writes the base_nobu_v2a.txt prompt:

```text
The FIRST attached image is the approved master still on a flat magenta #FF00FF background: <subject>. The SECOND attached image is <role>.
Reproduce the FIRST image exactly: the same single figure at exactly the same size and the same position on the canvas (<measured framing>), the same pose, <view>, facing LEFT, the same <identity_recap>. Same <style> as the FIRST image: <traits>.
THE ONLY CHANGE: <change>. Everything else (<keep>) stays exactly as in the FIRST image.
```

- The FIRST image is `--master` (its `master.png`, spec and recap), a run take (`--run --take`) or `--still`. Each `--extra-reference` follows it, in order, with its `--extra-role`.
- The FIRST image's framing is measured and written as canvas-edge percentages.
- `--prompt-only` writes the prompt and `run.json` without generating, for the host's own image tool.
- Make one change per edit, and approve the result like any take.

## pad

`pad` keys the still with forge_matte: the key is estimated from the border ring (generated backdrops drift, for example (252, 3, 251)), and the soft matte un-mixes the edges. It then:

- builds the subject box from every part with at least 24 px of alpha > 16, so the specks are dropped;
- crops the subject with a 6 px margin;
- places it on the 1024 canvas at the class framing: premultiplied LANCZOS, or box below 0.5x, and the top of the box lands exactly on the top margin;
- clears the alpha 1-4 ringing and composites the result over the pure key.

Every pixel outside the subject is then exactly the key colour. It writes `padded.png` (opaque RGB), `padded_rgba.png` and `pad.json` (`generate2dsprite.master_pad.v1`: framing, transform, matte QA, key choice, warnings).

Re-padding game-opus55's raw kanetsugu still with `--class hero` gives the subject box (208, 138, 816, 926), against (208, 138, 815, 927) for the hand-made pad, with a mean pixel difference of 3.1. Re-padding the ashigaru still with `--class mob --facing left` gives (257, 406, 966, 877), against (259, 405, 970, 878).

Warnings: the subject touches an edge of the still, so it may be cut; the subject was upscaled, so detail is soft; the subject is too wide for the class framing, so it was scaled to fit the width; the subject's colours lean to the key; opaque key-coloured pixels remain. The pad refuses a still that has no flat key backdrop and no real alpha.

## approve and master.json

`approve` takes the chosen still (`--run --take`, or `--still` with `--run` or `--spec`), pads it and writes:

| File | Content |
|---|---|
| `master.png` | 1024x1024 RGB at the class framing; every pixel outside the subject is the pure key. This is the FIRST reference of every action-sheet generation. |
| `master_rgba.png` | the same placement with transparency (the cut-out) |
| `source.<ext>` | a byte copy of the chosen still |
| `spec.json` | the spec, with `recap` set to the final identity recap |
| `prompt.txt` | the prompt that made the still, when known |
| `master.json` | `generate2dsprite.master.v1` |

`master.json` fields. These names are stable; motion steps read them and never re-measure the still:

| Field | Meaning |
|---|---|
| `schema` | `"generate2dsprite.master.v1"` |
| `tool`, `created` | `{name: "master_still", version}`, RFC 3339 UTC time |
| `name` | asset id |
| `subject` | the short noun phrase |
| `identity_recap` | long, precise visual description, a noun phrase reused verbatim after "The same" in every motion prompt |
| `facing`, `view` | `left`/`right`/`front`/`back`/`none`; camera words |
| `finish` | `hd` or `pixel` |
| `class` | `hero`, `mob`, `boss` or `prop` |
| `framing` | `canvas` [1024, 1024], `subject_height_px`, `top_margin_px`, `lead_px`, `preset`; measured on `master.png`: `subject_bbox` [x0, y0, x1, y1], `anchor` (stance midpoint on the feet line), `opaque_area_px` (alpha >= 128), `width_limited` |
| `key` | `"#FF00FF"` (upper-case hex) |
| `files` | `master`, `cutout`, `source` (fileRefs with `path`, `sha256`, `bytes`, `size`), `spec`, `prompt` (fileRef or null); paths are relative to `master.json` |
| `references` | `[{role: identity or style, path, sha256, bytes, what}]` in attachment order |
| `transform` | `master = scale * source + offset` in continuous pixel coordinates: `scale`, `offset` [x, y], `source_size`, `source_subject_bbox`, `crop_box`, `crop_margin_px` (6), `canvas`, `resampler`, `key_rgb`, speck counts |
| `route` | the route that made the still (from the take, `--route`, or `external`) |
| `provenance` | `command` (generate, edit, prompt or external), `run`, `take`, `source_sha256`, `media` (the route's summary without local paths), `media_cli_source`, `edit` (`from`, `change`) |
| `matte` | keyer, key estimate, matte QA and key choice |
| `warnings` | every warning, verbatim |

An action-sheet prompt built from it: "The same `<identity_recap>`, sprite sheet of N frames in one horizontal row, `<one action>` with absolute phase per frame, facing LEFT in every frame and never turning around; the loop starts AND ends in exactly the same pose; same side view, same camera height, no zoom; each frame the same body size; solid flat pure magenta background only, no shadow, no ground; keep the exact `<finish>` look" plus the negatives collected from failed takes ([prompt-rules.md](prompt-rules.md)).

## Limits

- The pad measures framing; it does not judge identity, anatomy or facing. Look at `master.png` before you approve.
- A reference on another drive is stored by file name and sha256 only (manifests never hold absolute paths). Keep the references inside the project.
- Without the agent's image tool, nothing is generated and nothing is claimed: the prompt is still published, and codeart2d ([SKILL.md](../../codeart2d/SKILL.md)) is the fallback. Say "code-drawn, no image model" when you use it.
