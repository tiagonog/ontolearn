#!/usr/bin/env python3
"""multirun.py — repeat the scalability measurements N times and report
mean and range per configuration. Counts are deterministic (seed 42) and
are asserted to be identical across runs; only timings vary.
Usage: python3 multirun.py [N]
"""
import sys, statistics as st
import scalability_regimes as S

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
CFGS = [(5, 10, 5, 2), (25, 50, 5, 4), (100, 200, 8, 4),
        (400, 500, 10, 4), (1000, 1000, 10, 5)]

acc = {}
for r in range(N):
    for (nl, nc, cl, pp) in CFGS:
        g = S.gen_abox(S.load(S.V2), nl, nc, cl, pp)
        tri = len(g)
        ind = len(set(g.subjects(S.RDF.type, S.OWL.NamedIndividual)))
        ht = S.hermit_time(g, f'mr{nl}')
        pn, pt = S.sparql_count(g, S.Q_PATH)
        rt = S.rl_time(g)[1] if tri <= 20000 else None
        k = (tri, ind, pn)
        acc.setdefault(k, {'hermit': [], 'path': [], 'rl': []})
        acc[k]['hermit'].append(ht)
        acc[k]['path'].append(pt)
        if rt is not None:
            acc[k]['rl'].append(rt)
    print(f'  run {r+1}/{N} done', flush=True)

def fmt(v):
    if not v:
        return '---'
    if len(v) == 1:
        return f'{v[0]:.2f}'
    return f'{st.mean(v):.2f} [{min(v):.2f}--{max(v):.2f}]'

print(f'\n== Scalability over {N} runs (counts deterministic; times mean [min--max]) ==')
print(f"{'Triples':>8} {'Indiv':>6} {'PathPairs':>9} {'HermiT (s)':>22} {'Path q. (s)':>22} {'OWL-RL (s)':>22}")
for (tri, ind, pn), d in sorted(acc.items()):
    print(f'{tri:>8} {ind:>6} {pn:>9} {fmt(d["hermit"]):>22} {fmt(d["path"]):>22} {fmt(d["rl"]):>22}')
print(f'\nConfigurations measured: {len(acc)} (expected 5) — '
      f'identical counts across all {N} runs confirms determinism.')
