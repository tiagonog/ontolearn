#!/usr/bin/env python3
"""check_release_equivalence.py - E0: is what the experiments read what was released?

Reviewer-driven. In the first submission the ablation script re-created "v2.0"
in memory and that graph was NOT the released v2.0 (it lacked the domain axiom
of :temComponenteKSA, two labels and two version-metadata statements; 760 vs
765 triples). This script makes the equivalence explicit and machine-checked:

 E1  build_v2.py  applied to the released v1.0 is isomorphic to the released v2.0
 E2  build_v2_1.py applied to the released v2.0 reproduces v2.1 byte for byte
 E3  build_v2_2.py applied to the released v2.1 reproduces v2.2 byte for byte
 E4  the RDF/XML and Turtle serializations of each version are isomorphic
 E5  v2.2 minus all completion families differs from v1.0 only by annotations,
     the ontology header, and the one documented logical removal of v2.1
 E6  the assertional layer (statements about the 20 individuals) is equal by
     value in v1.0, v2.0, v2.1 and v2.2; differences of lexical form are listed
 E7  erratum: the first-submission reconstruction vs the released v2.0

Exit status is non-zero if any of E1-E6 fails.
"""
import subprocess, sys, tempfile, filecmp
from pathlib import Path
from rdflib import Graph, OWL, RDF, RDFS, URIRef, BNode, Literal
from rdflib.compare import to_isomorphic, graph_diff
from common import *

ok = True
out = []


def say(tag, passed, msg):
    global ok
    ok = ok and passed
    out.append(f'{tag}  {"PASS" if passed else "FAIL"}  {msg}')
    print(out[-1])


tmp = Path(tempfile.mkdtemp())
py = sys.executable
S = ROOT / 'scripts'

# E1
subprocess.run([py, S / 'build_v2.py', locked('v1.0'), tmp / 'v2.ttl', tmp / 'v2.owl'], check=True, capture_output=True)
rb = Graph().parse(str(tmp / 'v2.owl'), format='xml')
say('E1', to_isomorphic(rb) == to_isomorphic(load('v2.0')),
    f'build_v2.py(v1.0) isomorphic to released v2.0 ({len(rb)} triples)')
# E2, E3
subprocess.run([py, S / 'build_v2_1.py', locked('v2.0'), tmp / 'v21.ttl', tmp / 'v21.owl'], check=True, capture_output=True)
say('E2', filecmp.cmp(tmp / 'v21.owl', locked('v2.1'), shallow=False), 'build_v2_1.py(v2.0) byte-identical to released v2.1')
subprocess.run([py, S / 'build_v2_2.py', locked('v2.1'), tmp / 'v22.ttl', tmp / 'v22.owl'], check=True, capture_output=True)
say('E3', filecmp.cmp(tmp / 'v22.owl', locked('v2.2'), shallow=False), 'build_v2_2.py(v2.1) byte-identical to released v2.2')
# E4
for v, ttl in [('v2.0', 'ontology/ontolearn-v2.ttl'), ('v2.1', 'ontology/ontolearn-v2.1.ttl'), ('v2.2', 'ontology/ontolearn-v2.2.ttl')]:
    a, b = load(v), load(ttl)
    say('E4', to_isomorphic(a) == to_isomorphic(b), f'{v}: RDF/XML and Turtle isomorphic ({len(a)} triples)')

# E5
ANNOT = {RDFS.label, RDFS.comment, OWL.versionInfo}


def logical(g):
    """Triples that are not annotations on named entities or on the ontology header."""
    return [t for t in g if not (t[1] in ANNOT or t[0] == ONT)]


core, v1 = config(ORDER), load('v1.0')
_, only_core, only_v1 = graph_diff(to_isomorphic(core), to_isomorphic(v1))
lc, l1 = logical(only_core), logical(only_v1)
expected_v1_only = {(NS.Aprendiz, OWL.disjointWith, NS.Instrutor)}
say('E5', len(lc) == 0 and set(l1) == expected_v1_only,
    f'v2.2 minus F0..F6 vs v1.0: {len(only_core)} + {len(only_v1)} differing triples, all annotations/header '
    f'except {[tuple(sh(x) for x in t) for t in l1]} (removed in v2.1) and {len(lc)} others')


# E6
def abox(g):
    inds = set(g.subjects(RDF.type, OWL.NamedIndividual))
    return {t for t in g if t[0] in inds}, inds


ab = {v: abox(load(v)) for v in ['v1.0', 'v2.0', 'v2.1', 'v2.2']}
same = all(ab[v][0] == ab['v1.0'][0] for v in ab)


# rdflib normalizes the lexical form of typed literals when it parses a file, so the comparison
# above is a comparison of values. A consumer that keeps lexical forms (the OWL API does) can see
# a difference where rdflib sees none; the lexical forms are therefore compared as well.
def lexical_abox(v):
    import rdflib
    keep = rdflib.NORMALIZE_LITERALS
    rdflib.NORMALIZE_LITERALS = False
    try:
        g = Graph(); g.parse(locked(v))
    finally:
        rdflib.NORMALIZE_LITERALS = keep
    inds = set(g.subjects(RDF.type, OWL.NamedIndividual))
    return {(s, p, (str(o), str(o.datatype), o.language) if isinstance(o, Literal) else o) for s, p, o in g if s in inds}


lex = {v: lexical_abox(v) for v in ab}
lex_diff = {v: (sorted(lex['v1.0'] - lex[v], key=str), sorted(lex[v] - lex['v1.0'], key=str)) for v in ('v2.0', 'v2.1', 'v2.2')}
n_lex = len(lex_diff['v2.2'][0])
same_lex_across_v2 = lex['v2.0'] == lex['v2.1'] == lex['v2.2']
say('E6', same and same_lex_across_v2, f'assertional layer equal by value in v1.0, v2.0, v2.1, v2.2 '
    f'({len(ab["v1.0"][1])} individuals, {len(ab["v1.0"][0])} triples); lexical forms identical in v2.0, v2.1, v2.2; '
    f'{n_lex} literal written in a different, value-equal lexical form from v2.0 on:')
for (s1, p1, o1), (s2, p2, o2) in zip(*lex_diff['v2.2']):
    line = f'          {sh(s1)} {sh(p1)}  "{o1[0]}"  (v1.0)  ->  "{o2[0]}"  (v2.x)   [{o1[1].split("#")[-1]}]'
    print(line); out.append(line)

# E7 (erratum; informational)
sys.argv = ['ablation.py', str(locked('v1.0'))]
import importlib.util, io, contextlib
spec = importlib.util.spec_from_file_location('abl1', S / 'first-submission' / 'ablation_families.py')
abl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abl)
ga = abl.build(abl.ALL)
_, only_rel, only_abl = graph_diff(to_isomorphic(load('v2.0')), to_isomorphic(ga))
print(f'E7  INFO  first-submission ablation reconstructed {len(ga)} triples; released v2.0 has {len(load("v2.0"))}.')
out.append(f'E7  INFO  first-submission ablation reconstructed {len(ga)} triples; released v2.0 has {len(load("v2.0"))}. Missing from the reconstruction:')
for t in sorted(only_rel):
    line = '          ' + ' '.join(sh(x)[:70] for x in t)
    print(line); out.append(line)

(RESULTS / 'E0_release_equivalence.txt').write_text('\n'.join(out) + '\n')
sys.exit(0 if ok else 1)
