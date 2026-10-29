# Regression suite

`python tests/run_regression.py` rebuilds real WorldForge regions through the importer and the
builder and scores how closely the wall placement matches the file. Fixtures:

- `fixtures/dev/` — nine regions from the game developers' own segments (Praetoseba, Blackburrow,
  Underkingdom, Axe Glacier). Their Solid Rock / Granite is bare fill, so they run with `mass_style
  bare`.
- `fixtures/tony/` — Tony's hand-corrected teaching regions from 2026-08-22 (cross, L-block, bossway,
  shell+partitions), test2 (two masses, 2026-09-01), Castle Spire (region 9, 2026-09-02) and the Forge
  L6 south corrections. These run with the canon `faces` style.

`baseline.json` holds the approved score per fixture. A run that drops any fixture by more than
0.05 points exits 1. After an intended change, run with `--update` and commit the new baseline.

Scores are on role classes (H / V / C wall piece, door H/V, mass), never on ids, and only over
tiles that carry a wall, door or mass in either file. Known, accepted differences:

- posts, pillars and columns (ids with no H/V/C name) are imported as extras and not rebuilt in a
  `--new` build (`P->-`), so Praetoseba temple and region 9 sit a few points under 100;
- the developers are inconsistent about capping an east-branching T with a corner post
  (`CV->V`): Praetoseba and Axe Glacier do, Blackburrow and Underkingdom don't; the builder follows
  the majority;
- region 7 stacks a marble wall on the Solid Dirt tile itself, which a sketch cannot hold (one layer
  per tile), so it stays around 77%.

Score history: see the commit that introduced each baseline change.
