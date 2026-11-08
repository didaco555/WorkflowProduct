# Art brief — Humans Apocalypse

You can find or design the final graphics while the gameplay systems develop. **Nothing is blocked on art right now.**

## Visual direction to explore

- Clear 2D top-down or 3/4 perspective, colourful readable silhouettes, funny-but-macabre zombie point of view.
- The player is an approachable zombie; the invading humans should be recognisable by occupation and behaviour.
- Avoid backgrounds with excessive visual noise: the player must be able to read incoming projectiles and warning zones.
- No need to copy Brotato/Isaac sprites: their silhouettes and presentation can inspire readability, not asset reuse.

## First assets (priority order)

| Game key | Purpose | Suggested master size |
| --- | --- | --- |
| `zombie` | Main player, 4–8 directional frames later | 128×128 transparent |
| `worker` | Basic invading human | 128×128 transparent |
| `runner` | Orange speedster, readable during dash | 128×128 transparent |
| `ranger` | Ranged human, distinct silhouette | 128×128 transparent |
| `brute` | Large heavy human with shockwave | 160×160 transparent |
| `boss` | Wave-5 exterminator | 256×256 transparent |

Preferred: PNG or lossless WebP, transparent background, sprites centred, feet aligned near the bottom. Keep consistent drawing scale. Export frame sequences or sprite sheets with clear frame dimensions. Keep original layered source files separately if available.

## Integration contract

`src/game.js` contains `SPRITE_URLS`: place each asset in `assets/actors/` and map its URL. The renderer falls back to a simple vector actor if no image is supplied.

Artwork needs animation states eventually: idle, run, hurt, dash, death, shoot, throw-arm. The prototype currently animates with code; the final sprite system will support orientation and state.

## Safe sourcing

Before putting sourced assets in a public/commercial game, check whether the exact licence permits modification, redistributing it in a game and commercial use. Keep source URLs/licence copies. No ripped game sprites or unlicensed image packs.