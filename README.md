# Amsterdam: tafel voor 3 op dinsdag 8 september 2026

Onderzoek naar welke toffe Amsterdamse restaurants op dinsdag 8 september 2026 nog een tafel voor drie personen hebben.

- `amsterdam-dinsdag-8-september-2026.md` — het rapport: top 20 met tijden en reserveerlinks, extra opties, en wat vol of dicht is.
- `amsterdam-dinsdag-8-september-2026.html` — dezelfde inhoud als deelbare pagina.
- `tools/rc.py` — checker die de reserveringssystemen (Zenchef, Tebi, Formitable, Guestplan, SevenRooms) rechtstreeks bevraagt.
  - `python3 tools/rc.py check "<Naam>" <website-url> [datum] [personen]`
  - directe doelen: `zc:<zenchef rid>`, `tebi:<widget token>`, `ft:<formitable uid>`, `gp:<guestplan key>`, `sr:<sevenrooms venue>`
- `tools/batch.py` — draait `rc.py check` parallel over een TSV (naam<TAB>doel).
- `tools/summarize.py` — vat `results.jsonl` samen; `tools/build_page.py` en `tools/build_md.py` renderen `tools/picks.json` naar HTML en Markdown.
- `tools/candidates.txt` — de kandidatenlijst waarmee begonnen is.

Beschikbaarheid is gecheckt op zondagavond 6 september 2026 en verandert continu.
