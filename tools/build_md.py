#!/usr/bin/env python3
"""Render picks.json to a Markdown report."""
import json, sys
sys.path.insert(0, '.')
def to_min(t): h, m = t.split(':'); return int(h)*60+int(m)
def fmt_ranges(slots):
    s = sorted(set(slots))
    if not s: return []
    if len(s) == 1: return [s[0]]
    step = min(to_min(b)-to_min(a) for a, b in zip(s, s[1:]))
    out=[]; start=prev=s[0]
    for t in s[1:]:
        if to_min(t)-to_min(prev)==step: prev=t
        else: out.append(f"{start}–{prev}" if start!=prev else start); start=prev=t
    out.append(f"{start}–{prev}" if start!=prev else start)
    return out
d = json.load(open('picks.json', encoding='utf-8'))
L = []
L.append("# Twintig tafels op dinsdag — Amsterdam, dinsdag 8 september 2026, 3 personen\n")
L.append(f"Beschikbaarheid live gecheckt op {d['checked']}. " + d['how'] + "\n")
L.append("Legenda: **vrij** = direct online te boeken voor 3; *wachtlijst* = alleen wachtlijst.\n")
i = 0
for g in d['groups']:
    L.append(f"\n## {g['name']} — {g.get('sub','')}\n")
    for p in g['items']:
        i += 1
        slots = fmt_ranges([t for t in p['slots'] if t >= '17:00'])
        wl = fmt_ranges([t for t in p.get('waitlist', []) if t >= '17:00'])
        line = f"{i}. **{p['name']}** ({p['tag']}) — {p['desc']}  \n   {p['addr']} · vrij: {', '.join(slots)}"
        if wl: line += f" · wachtlijst: {', '.join(wl)}"
        if p.get('note'): line += f"  \n   {p['note']}"
        line += f"  \n   Reserveer via {p['via']}: {p['book']}"
        if p.get('site') and p['site'] != p['book']: line += f" · website: {p['site']}"
        L.append(line)
L.append("\n## Ook nog plek\n")
L.append("| Restaurant | Buurt | Vrij (diner) | Boeken via |\n|---|---|---|---|")
for a in d['alternates']:
    L.append(f"| {a['name']} ({a['tag']}) | {a['hood']} | {', '.join(fmt_ranges([t for t in a['slots'] if t >= '17:00']))} | [{a['via']}]({a['book']}) |")
L.append("\n## Niet gelukt op dinsdag\n")
for n in d['not_available']:
    L.append(f"- **{n['name']}** — {n['why']}")
open('amsterdam-dinsdag.md', 'w', encoding='utf-8').write("\n".join(L) + "\n")
print("md written", sum(len(x) for x in L))
