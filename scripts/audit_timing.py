#!/usr/bin/env python3
"""audit_timing.py - how long does the reasoner-free audit take?

Wall-clock time of a complete run of scripts/audit.py as a separate process
(interpreter start-up, parsing, inventory, claim check, isolated-class analysis
and domain/range check), three repetitions per file, on the four releases and
on the ten external ontologies of fetch_external.py.

    python3 scripts/audit_timing.py [label]   ->  results/E7_audit_timing_<label>.json
"""
import json, platform, subprocess, sys, time
import fetch_external
from common import *

label = sys.argv[1] if len(sys.argv) > 1 else 'local'
files = [(v, locked(v)) for v in ('v1.0', 'v2.0', 'v2.1', 'v2.2')]
files += [(e[0], fetch_external.path_of(e[0], ROOT / 'external')) for e in fetch_external.EXTERNAL]
rows = []
for name, path in files:
    ts = []
    for _ in range(3):
        t = time.perf_counter()
        subprocess.run([sys.executable, str(ROOT / 'scripts' / 'audit.py'), str(path)], capture_output=True, check=True)
        ts.append(time.perf_counter() - t)
    rows.append({'ontology': name, 'seconds': [round(x, 3) for x in ts]})
    print(f"  {name:10s} {min(ts):.2f}-{max(ts):.2f} s")
res = {'label': label, 'machine': platform.machine(), 'python': platform.python_version(),
       'runs': rows, 'max_seconds': max(max(r['seconds']) for r in rows)}
print(f"  maximum over {len(rows)} ontologies x 3 runs: {res['max_seconds']:.2f} s")
(RESULTS / f'E7_audit_timing_{label}.json').write_text(json.dumps(res, indent=1))
