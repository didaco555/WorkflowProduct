# Humans Apocalypse — Combat Lab 0.3

> The humans invaded the world of the zombies. Survive the living.

This repository is a **mechanics-first HTML5 prototype** of an original top-down arena shooter. Graphics are temporary. The game is playable in a browser, with no installation or backend.

## Controls

| Input | Action |
| --- | --- |
| WASD / arrows | Move |
| Mouse | Aim |
| Left mouse button (hold) | Shoot **manually** |
| R | Reload |
| Space + movement | Dash with brief invulnerability |
| Q | Throw a boomerang zombie arm |
| Esc | Pause / resume |

## Play online

This project is published through **GitHub Pages** from the repository's configured branch. In Settings → Pages, choose **GitHub Actions** as the deployment source.

The expected URL for the repository `didaco555/WorkflowProduct` is: https://didaco555.github.io/WorkflowProduct/

## Implemented in 0.3

- Manual shooting, aiming, finite magazine, and reload timing
- Dash with cooldown and brief invulnerability
- Boomerang arm special ability, cooldown, and piercing hits
- Damage, hitstun, pushback, feedback particles, screen shake, synthesised impact sounds
- Enemy behaviours: chaser, telegraphed charger, ranged attacker, shockwave brute, and wave-5 boss
- Five escalating waves with a survival timer, DNA/health drops, and mutation choices
- Pause, lose/win, HUD, fixed 60-Hz simulation, high-DPI scaling
- No dependencies and no external asset requests
- Temporary **visual placeholders** that can be replaced with PNG/WebP sprites

## Code structure

- `index.html` — game shell and HUD
- `src/game.js` — movement, shooting, enemy AI, game state, rendering
- `src/style.css` — interface styling
- `docs/ART_BRIEF.md` — graphic delivery contract
- `tests/smoke.py` — automated Playwright smoke checks

The code currently uses one gameplay module: this is an **experimental combat lab**, not yet production architecture. Before scaling content, separate player/enemy/combat/renderer systems, add regression tests and profiles, and decide on the production engine.

## Testing

Start a local static server in this directory (e.g. `python -m http.server 8000`) or open the site through GitHub Pages. For Playwright tests, install `playwright` and a Chromium browser, then run `python tests/smoke.py`. Test script runs an inline bundle, so it can work in restricted browser runners.

## Release status and rights

Not ready for Steam or itch.io distribution. Do not add third-party graphics, audio, fonts or code without checking licences and attribution. Previous project contents are preserved on `backup/workflowproduct-before-humans-apocalypse`.