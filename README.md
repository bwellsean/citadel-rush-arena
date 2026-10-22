# Citadel Rush for TCG Arena

Game files that load Citadel Rush into [TCG Arena](https://tcg-arena.fr), a free online card table.

- `game.json`: board (5 lanes x 6 rows), counters, tokens, deck rules, mulligan, quick-reference help
- `cards.json`: all 100 Set 1 cards plus the Halcyte resource token
- `decks.json`: starter decks (Radiant Battery, Pathfinders, Drone Swarm, Iron Line, Rift Ambush)
- `images/`: card faces (rendered from the print-and-play kit), card back, tokens, banner, playmat

## Play

Open TCG Arena, go to Custom games, and paste the game file URL:

https://raw.githubusercontent.com/bwellsean/citadel-rush-arena/main/game.json

## Update cards

1. Refresh `tools/Card.dc.html` from the kit and run `node tools/extract.mjs tools/Card.dc.html tools/kitdata.json`.
2. Render faces: `node tools/render.mjs <folder with the kit's art blobs> render`, then `python3 tools/towebp.py`.
3. Rebuild the JSON: `python3 tools/build.py`. Bump `VERSION` in `build.py` so players' caches refresh.
4. Commit and push. Players get the new version the next time they load the game.
