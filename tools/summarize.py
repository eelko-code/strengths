import json, sys
latest = {}
for line in open('results.jsonl', encoding='utf-8'):
    try: r = json.loads(line)
    except Exception: continue
    if r.get('target','').startswith('| ') or '\t' in r.get('name',''): continue
    if r.get('status') in ('NO_ZENCHEF_ID',) and r['name'] in latest and latest[r['name']].get('status') not in ('NO_ZENCHEF_ID',): continue
    latest[r['name']] = r
def dinner(slots): return [t for t in (slots or []) if t >= '17:00']
rows = []
for name, r in latest.items():
    info = r.get('info') or {}
    st = r.get('status'); via = r.get('used_platform')
    if via is None and r.get('zenchef_rid'): via = 'zenchef'
    zi = r.get('zc_info') or {}
    pname = info.get('name') or zi.get('name')
    addr = info.get('address') or (f"{zi.get('address')}, {zi.get('city')}" if zi.get('address') else None)
    notes = []
    av = r.get('availability') or {}
    for sh in av.get('shifts', []):
        if sh.get('slots_for_pax'):
            if sh.get('offer_required'): notes.append(f"zc shift '{sh['name']}' offer/menu keuze verplicht")
            pp = sh.get('prepayment') or {}
            if pp and pp.get('charge_per_guests') and (pp.get('min_guests') or 0) <= 3: notes.append(f"aanbetaling/garantie €{pp['charge_per_guests']/100:.0f} p.p. ({pp.get('deposit_type')})")
    if via == 'tebi':
        for sv in (info.get('services') or []):
            if sv.get('prepayment_cents'): notes.append(f"tebi service '{sv['name']}' aanbetaling €{sv['prepayment_cents']/100:.0f}")
        if info.get('by_service'): notes.append('slots per service: ' + '; '.join(f"{k}: {v['available']}" for k,v in info['by_service'].items() if v['available']))
    if via == 'guestplan':
        for sid, sv in (info.get('services') or {}).items():
            if sv.get('isRequired'): notes.append(f"gp ticket verplicht: {sv.get('title')}")
    if via == 'sevenrooms':
        for sh in (info.get('shifts') or []):
            if sh.get('book_times'): notes.append(f"sr shift {sh['name']}: {sh['descriptions']}")
    rows.append({'name': name, 'status': st, 'via': via, 'pname': pname, 'addr': addr, 'dinner': dinner(r.get('slots')), 'all': r.get('slots') or [], 'waitlist': dinner(r.get('slots_waitlist')), 'notes': notes, 'target': r.get('target'), 'rid': r.get('zenchef_rid'), 'platforms': r.get('platforms')})
order = {'AVAILABLE':0,'WAITLIST_ONLY':1,'FULL_OR_NOT_BOOKABLE':2,'NOT_AVAILABLE':3,'CLOSED':4}
rows.sort(key=lambda x: (order.get(x['status'], 9), x['name']))
json.dump(rows, open('summary.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
mode = sys.argv[1] if len(sys.argv) > 1 else 'avail'
for x in rows:
    if mode == 'avail' and x['status'] != 'AVAILABLE': continue
    if mode == 'other' and x['status'] == 'AVAILABLE': continue
    d = x['dinner']
    span = f"{d[0]}–{d[-1]} ({len(d)} slots)" if d else '-'
    print(f"{x['name']} | {x['status']} | {x['via']} | {x['pname']} | {x['addr']} | dinner {span} | wl {x['waitlist'][:6]} | {x['notes']}")
