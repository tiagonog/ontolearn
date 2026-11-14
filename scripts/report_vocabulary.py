#!/usr/bin/env python3
"""report_vocabulary.py - the vocabulary that the original report names, checked on each release.

Besides the 15 structural claims of claims/sbie2026.json, the report names classes, object
properties and individuals in its figures, states the signature of six properties in its
prompt listing, draws subclass links, and shows seven assertions of the test ABox. Those
statements are not counted as claims; they are transcribed under "named" in the same file and
checked here, so that the reader can see what the count of claims leaves out and how it fares.

For each release the script reports, per kind of statement, how many hold of the file:
  class / object property   the term is declared with that kind;
  individual                the term is declared and has the stated asserted type;
  signature                 the declared domain and range are exactly the stated classes;
  subclass link             the superclass is reached through the named taxonomy;
  assertion                 the triple is in the file.
"""
import json
from rdflib import OWL, RDF, RDFS, URIRef
import audit
from common import NS, RESULTS, load, locked

VERS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']


def check(g, named):
    A = audit.Audit(g)
    N = lambda n: NS[n]
    res = {}
    res['classes'] = [(c, N(c) in A.classes) for c in named['classes']]
    res['object properties'] = [(p, N(p) in A.obj_props) for p in named['object_properties']]
    res['individuals'] = [(f'{i} : {t}', (N(i), RDF.type, OWL.NamedIndividual) in g and (N(i), RDF.type, N(t)) in g)
                          for i, t in named['individuals'].items()]
    res['signatures'] = [(f'{p} ({d} -> {r})', set(g.objects(N(p), RDFS.domain)) == {N(d)} and set(g.objects(N(p), RDFS.range)) == {N(r)})
                         for p, d, r in named['signatures']]
    res['subclass links'] = [(f'{a} < {b}', N(b) in A.ancestors(N(a))) for a, b in named['subclass_links']]
    res['assertions'] = [(f'{s} {p} {o}', (N(s), N(p), N(o)) in g) for s, p, o in named['assertions']]
    return res


def main():
    named = json.loads(locked('claims/sbie2026.json').read_text(encoding='utf-8'))['named']
    out = {}
    print(f"Vocabulary named by the original report ({named['where']}),")
    print('checked on each release: statements that hold / statements made.\n')
    kinds = ['classes', 'object properties', 'individuals', 'signatures', 'subclass links', 'assertions']
    print(f"  {'kind':18s} " + ' '.join(f'{v:>8s}' for v in VERS))
    table = {v: check(load(v), named) for v in VERS}
    for k in kinds:
        print(f'  {k:18s} ' + ' '.join(f"{sum(ok for _, ok in table[v][k]):3d}/{len(table[v][k]):<4d}" for v in VERS))
    for v in VERS:
        missing = [f'{k}: {name}' for k in kinds for name, ok in table[v][k] if not ok]
        out[v] = {'counts': {k: [sum(ok for _, ok in table[v][k]), len(table[v][k])] for k in kinds}, 'not_holding': missing}
        print(f"\n  {v}: {sum(c[0] for c in out[v]['counts'].values())} of {sum(c[1] for c in out[v]['counts'].values())} statements hold"
              + ('' if not missing else '; not holding: ' + '; '.join(missing)))
    (RESULTS / 'audit_report_vocabulary.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
