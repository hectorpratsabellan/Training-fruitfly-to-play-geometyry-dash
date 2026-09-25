# Fruit fly brain plays Geometry Dash

A simulated FlyWire fruit fly brain plays Geometry Dash. Obstacles reach the fly
as looming stimuli on LPLC2 / LC4; a Giant Fiber (DNp01) spike means jump.

## Read first

The project notes live in the Obsidian vault, not here:
`C:\Users\Hector\Desktop\Vault\fruitfly_geometry`. At the start of every session
read its `CLAUDE.md` (working agreement, voice rules, end-of-session routine),
then the hub `Fruitfly Geometry.md`, then `log/Fly Status.md`. The vault's rules
apply to everything in this repo, including the Voice section (no em dashes).

## Layout

- This repo: our code. MIT, Hector.
- `..\dino-fly`: reference clone of tairqaldy/dino-fly (MIT). Brain engine,
  connectome loader, transducers. Don't commit there; credit anything borrowed.
- `..\dino-fly\data\`: FlyWire connectome files, ~330 MB, not in git.

## Rules

- Connectome weights stay frozen as reconstructed.
- Every number in a note or README comes from a script and names its log.
- Claims about the fly need the controls in the vault's `Fly Evaluation` note.
- Log breakages in the vault's `log/Fly Issues.md` when they happen.
- Explain design decisions before writing code. Hector is new to neuroscience
  and still learning Git and PyTorch; explain git commands the first few times.
- Never submit bot runs to Geometry Dash leaderboards.

## Environment

Windows 11, PowerShell. RTX 4070 Laptop 8 GB. `uv` is installed through pip, so
call it as `python -m uv`. Inside `dino-fly\brain` always use
`python -m uv run --no-sync ...` (a plain `uv run` uninstalls the CUDA torch) and
set `$env:PYTHONUTF8=1`. One GPU experiment at a time.
