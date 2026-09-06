#!/usr/bin/env python3
"""batch.py <tsv with name<TAB>target> [workers] -- runs rc.py check for each line in parallel."""
import sys, subprocess, concurrent.futures, os
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for line in open(sys.argv[1], encoding='utf-8'):
    line = line.rstrip('\n')
    if not line.strip() or line.startswith('#'): continue
    parts = line.split('\t')
    if len(parts) < 2 or not parts[1].strip(): continue
    rows.append((parts[0].strip(), parts[1].strip()))
workers = int(sys.argv[2]) if len(sys.argv) > 2 else 5
def run(row):
    name, target = row
    try:
        out = subprocess.run([sys.executable, os.path.join(HERE, 'rc.py'), 'check', name, target], capture_output=True, text=True, timeout=240)
        return (out.stdout + out.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"{name} | TIMEOUT | {target}"
with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
    for res in ex.map(run, rows):
        print(res, flush=True)
