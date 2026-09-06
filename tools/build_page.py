#!/usr/bin/env python3
import json, html, sys, re
def main():
    data = json.load(open('picks.json', encoding='utf-8'))
    
    def to_min(t): h, m = t.split(':'); return int(h)*60+int(m)
    def ranges(slots):
        """Compress sorted HH:MM slots into ranges using the dominant step (15/30 min)."""
        s = sorted(set(slots))
        if not s: return []
        if len(s) == 1: return [(s[0], s[0])]
        diffs = [to_min(b)-to_min(a) for a, b in zip(s, s[1:])]
        step = min(diffs)
        out = []; start = s[0]; prev = s[0]
        for t in s[1:]:
            if to_min(t) - to_min(prev) == step: prev = t
            else: out.append((start, prev)); start = prev = t
        out.append((start, prev))
        return out
    def fmt_ranges(slots):
        return [f"{a}–{b}" if a != b else a for a, b in ranges(slots)]
    
    def esc(x): return html.escape(str(x), quote=True)
    
    def row(p, i):
        slots = [t for t in p['slots'] if t >= '17:00']
        chips = ''.join(f'<span class="chip ok">{esc(r)}</span>' for r in fmt_ranges(slots))
        wl = [t for t in p.get('waitlist', []) if t >= '17:00']
        if wl: chips += ''.join(f'<span class="chip wait" title="alleen wachtlijst">{esc(r)}</span>' for r in fmt_ranges(wl))
        note = f'<p class="note">{esc(p["note"])}</p>' if p.get('note') else ''
        links = f'<a class="book" href="{esc(p["book"])}" target="_blank" rel="noopener">Reserveer via {esc(p["via"])}</a>'
        if p.get('site') and p['site'] != p['book']:
            links += f' <a class="site" href="{esc(p["site"])}" target="_blank" rel="noopener">website</a>'
        return f'''<li class="r">
      <div class="num" aria-hidden="true">{i}</div>
      <div class="body">
        <h3><span class="name">{esc(p["name"])}</span> <span class="tag">{esc(p["tag"])}</span></h3>
        <p class="desc">{esc(p["desc"])}</p>
        <p class="addr">{esc(p["addr"])}</p>
        <div class="slots"><span class="lbl">Vrij voor 3</span>{chips}</div>
        {note}
        <div class="actions">{links}</div>
      </div>
    </li>'''
    
    groups = []
    i = 0
    for g in data['groups']:
        items = ''
        for p in g['items']:
            i += 1; items += row(p, i)
        groups.append(f'<section class="grp"><h2>{esc(g["name"])}<span class="sub">{esc(g.get("sub",""))}</span></h2><ol class="list" start="{i-len(g["items"])+1}">{items}</ol></section>')
    
    alts = ''.join(f'<tr><td class="n">{esc(a["name"])}<span class="t">{esc(a["tag"])}</span></td><td>{esc(a["hood"])}</td><td class="tm">{esc(" · ".join(fmt_ranges([t for t in a["slots"] if t >= "17:00"])))}</td><td><a href="{esc(a["book"])}" target="_blank" rel="noopener">{esc(a["via"])}</a></td></tr>' for a in data['alternates'])
    nope = ''.join(f'<li><b>{esc(n["name"])}</b> <span>{esc(n["why"])}</span></li>' for n in data['not_available'])
    
    page = f'''<title>Twintig Tafels op Dinsdag</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75,600;75,800;100,400;100,600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
    <style>
    :root{{
      --paper:#F1F2EC; --paper-2:#E8EAE1; --ink:#1B1F1C; --ink-2:#4A5049; --muted:#6C726B; --line:#D3D6CB;
      --accent:#C8102E; --ok:#1F7A4D; --ok-bg:#E4F1E8; --wait:#9A6207; --wait-bg:#F6ECD6; --focus:#2B5FD9;
      --display:'Archivo',"Helvetica Neue",Arial,sans-serif; --body:'Source Serif 4',Georgia,"Times New Roman",serif; --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
    }}
    @media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
      --paper:#16191A; --paper-2:#1F2325; --ink:#ECEBE3; --ink-2:#C4C6BC; --muted:#9AA098; --line:#30363A;
      --accent:#FF6272; --ok:#63C48F; --ok-bg:#1B2F25; --wait:#E3AB4D; --wait-bg:#33291A; --focus:#7FA6FF;
    }} }}
    :root[data-theme="dark"]{{
      --paper:#16191A; --paper-2:#1F2325; --ink:#ECEBE3; --ink-2:#C4C6BC; --muted:#9AA098; --line:#30363A;
      --accent:#FF6272; --ok:#63C48F; --ok-bg:#1B2F25; --wait:#E3AB4D; --wait-bg:#33291A; --focus:#7FA6FF;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:17px;line-height:1.5;-webkit-font-smoothing:antialiased}}
    a{{color:inherit}}
    a:focus-visible,button:focus-visible{{outline:3px solid var(--focus);outline-offset:2px}}
    .wrap{{max-width:56rem;margin:0 auto;padding:2.5rem 1.25rem 4rem}}
    header.mast{{border-top:6px solid var(--accent);padding-top:1rem;margin-bottom:2rem}}
    .eyebrow{{font-family:var(--mono);font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-2);display:flex;flex-wrap:wrap;gap:.35rem 1.25rem;margin:0 0 .9rem}}
    .eyebrow b{{color:var(--accent);font-weight:500}}
    h1{{font-family:var(--display);font-variation-settings:"wdth" 75;font-weight:800;font-size:clamp(2.6rem,7vw,4.6rem);line-height:.95;letter-spacing:-.01em;margin:0 0 1rem;text-wrap:balance}}
    .lede{{font-size:1.1rem;max-width:38rem;margin:0;color:var(--ink-2)}}
    .lede strong{{color:var(--ink);font-weight:600}}
    .legend{{display:flex;flex-wrap:wrap;gap:.6rem 1.2rem;margin:1.25rem 0 0;font-family:var(--mono);font-size:.78rem;color:var(--muted)}}
    .legend .chip{{margin:0}}
    .grp{{margin-top:2.25rem}}
    .grp h2{{font-family:var(--display);font-variation-settings:"wdth" 75;font-weight:800;font-size:1.05rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin:0;padding:0 0 .5rem;border-bottom:1px solid var(--line);display:flex;align-items:baseline;gap:.8rem}}
    .grp h2 .sub{{font-family:var(--body);font-weight:400;font-size:.95rem;letter-spacing:0;text-transform:none;color:var(--muted)}}
    .list{{list-style:none;margin:0;padding:0}}
    .r{{display:grid;grid-template-columns:3.2rem 1fr;gap:0 .5rem;padding:1.25rem 0;border-bottom:1px solid var(--line)}}
    .num{{font-family:var(--display);font-variation-settings:"wdth" 75;font-weight:800;font-size:2rem;line-height:1;color:var(--muted);font-variant-numeric:tabular-nums;padding-top:.15rem}}
    .r h3{{font-family:var(--display);font-variation-settings:"wdth" 75;font-weight:800;font-size:1.65rem;line-height:1.05;margin:0 0 .35rem;letter-spacing:-.005em}}
    .r h3 .tag{{font-family:var(--mono);font-weight:500;font-size:.72rem;letter-spacing:.05em;text-transform:uppercase;color:var(--ink-2);vertical-align:.45em;margin-left:.4rem;white-space:nowrap}}
    .desc{{margin:0 0 .3rem;max-width:40rem}}
    .addr{{font-family:var(--mono);font-size:.8rem;color:var(--muted);margin:0 0 .7rem}}
    .slots{{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem}}
    .lbl{{font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-right:.2rem}}
    .chip{{font-family:var(--mono);font-size:.84rem;font-variant-numeric:tabular-nums;padding:.18rem .55rem;border-radius:3px;border:1px solid transparent;white-space:nowrap}}
    .chip.ok{{color:var(--ok);background:var(--ok-bg);border-color:color-mix(in srgb,var(--ok) 35%,transparent)}}
    .chip.wait{{color:var(--wait);background:var(--wait-bg);border-style:dashed;border-color:color-mix(in srgb,var(--wait) 45%,transparent)}}
    .note{{font-size:.92rem;color:var(--ink-2);margin:.6rem 0 0;max-width:40rem}}
    .actions{{margin-top:.75rem;display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;font-family:var(--display);font-size:.95rem}}
    .book{{display:inline-block;background:var(--ink);color:var(--paper);text-decoration:none;padding:.45rem .85rem;border-radius:3px;font-weight:600;font-variation-settings:"wdth" 100}}
    .book:hover{{background:var(--accent);color:#fff}}
    .site{{color:var(--ink-2);font-weight:600;text-decoration-thickness:1px;text-underline-offset:3px}}
    .alt{{margin-top:3rem}}
    .alt h2,.no h2,.how h2{{font-family:var(--display);font-variation-settings:"wdth" 75;font-weight:800;font-size:1.5rem;margin:0 0 .35rem;letter-spacing:-.005em}}
    .alt p,.no p,.how p{{margin:0 0 1rem;color:var(--ink-2);max-width:40rem}}
    .tbl{{overflow-x:auto}}
    table{{border-collapse:collapse;width:100%;font-size:.95rem}}
    th{{text-align:left;font-family:var(--mono);font-weight:500;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:.4rem .6rem .4rem 0;border-bottom:1px solid var(--line)}}
    td{{padding:.55rem .6rem .55rem 0;border-bottom:1px solid var(--line);vertical-align:top}}
    td.n{{font-family:var(--display);font-weight:600;font-variation-settings:"wdth" 100;white-space:nowrap}}
    td.n .t{{display:block;font-family:var(--mono);font-weight:400;font-size:.7rem;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);white-space:normal}}
    td.tm{{font-family:var(--mono);font-size:.82rem;font-variant-numeric:tabular-nums;color:var(--ok)}}
    td a{{color:var(--ink);text-decoration-thickness:1px;text-underline-offset:3px}}
    .no{{margin-top:3rem}}
    .no ul{{list-style:none;margin:0;padding:0;columns:2;column-gap:2rem}}
    .no li{{break-inside:avoid;padding:.35rem 0;border-bottom:1px solid var(--line);font-size:.92rem}}
    .no li b{{font-family:var(--display);font-weight:600;font-variation-settings:"wdth" 100}}
    .no li span{{color:var(--muted)}}
    .how{{margin-top:3rem;padding-top:1.25rem;border-top:6px solid var(--accent)}}
    .how p{{font-size:.95rem}}
    @media (max-width:640px){{ .r{{grid-template-columns:2.2rem 1fr}} .num{{font-size:1.4rem}} .no ul{{columns:1}} .r h3 .tag{{display:block;margin:.25rem 0 0;vertical-align:baseline}} }}
    @media (prefers-reduced-motion:no-preference){{ .book{{transition:background .15s ease}} }}
    </style>
    <div class="wrap">
    <header class="mast">
      <p class="eyebrow"><span><b>Dinsdag 8 september 2026</b></span><span>3 personen</span><span>Amsterdam</span><span>beschikbaarheid live gecheckt op {esc(data["checked"])}</span></p>
      <h1>Twintig tafels op dinsdag</h1>
      <p class="lede">{data["lede"]}</p>
      <div class="legend"><span class="chip ok">18:00–20:30</span> direct online te boeken voor 3 &nbsp; <span class="chip wait">19:00</span> alleen wachtlijst</div>
    </header>
    {''.join(groups)}
    <section class="alt">
      <h2>Ook nog plek</h2>
      <p>Iets minder hip of net buiten de top twintig, maar dinsdag wél gewoon te boeken voor drie.</p>
      <div class="tbl"><table><thead><tr><th>Restaurant</th><th>Buurt</th><th>Vrij (diner)</th><th>Boeken via</th></tr></thead><tbody>{alts}</tbody></table></div>
    </section>
    <section class="no">
      <h2>Niet gelukt op dinsdag</h2>
      <p>Ook gecheckt, maar vol, alleen wachtlijst, of op dinsdag dicht. Scheelt zoeken.</p>
      <ul>{nope}</ul>
    </section>
    <section class="how">
      <h2>Hoe dit is gecheckt</h2>
      <p>{data["how"]}</p>
    </section>
    </div>
    '''
    page = '\n'.join((l[4:] if l.startswith('    ') else l) for l in page.splitlines()) + '\n'
    open('amsterdam-dinsdag.html', 'w', encoding='utf-8').write(page)
    print("written", len(page))

if __name__ == '__main__':
    main()
