#!/usr/bin/env python3
"""profiles.py - E0 (second part): which OWL 2 profile is each release in?

The OWL API profile checkers decide, for every released file, whether it is an
OWL 2 DL ontology and whether it falls inside the tractable profiles OWL 2 EL,
QL and RL. Every violation is listed with the axiom that causes it.

Why this matters for the paper: the fault-injection experiment (E5) shows a
fault that a complete OWL 2 DL reasoner rejects and the OWL 2 RL rule engine
does not (X11, a union domain). The profile report explains it without
appeal to the behaviour of one engine: a union of classes is not allowed in
superclass position in OWL 2 RL, so the union domains and ranges of the
ontology are outside that profile, as are the existential restrictions of
family F3.

    python3 scripts/profiles.py     ->  results/E0_profiles.txt, results/E0_profiles.json
"""
import json
from collections import Counter, defaultdict
from common import *

VERS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']
PROFILES = ['OWL2DL', 'OWL2EL', 'OWL2QL', 'OWL2RL']


def kind_of(axiom_type, axiom):
    """A reader-oriented description of what makes the axiom fall outside OWL 2 RL."""
    if 'ObjectUnionOf' in axiom and axiom_type in ('DataPropertyDomain', 'ObjectPropertyDomain'):
        return 'union domain'
    if 'ObjectUnionOf' in axiom and axiom_type == 'ObjectPropertyRange':
        return 'union range'
    if 'ObjectSomeValuesFrom' in axiom and axiom_type == 'SubClassOf':
        return 'existential restriction as superclass'
    return 'other'


def main():
    paths = {v: locked(FILES[v]) for v in VERS}
    name = {paths[v].name: v for v in VERS}
    rows = harness('profiles', *paths.values())[1:]
    res = {v: {p: {'in_profile': None, 'violations': 0, 'by_kind': {}, 'axioms': []} for p in PROFILES} for v in VERS}
    for r in rows:
        f, prof, kind, atype, axiom = r.split('\t')
        d = res[name[f]][prof]
        if kind == 'SUMMARY':
            d['in_profile'] = (atype == 'in-profile'); d['violations'] = int(axiom)
        else:
            d['axioms'].append({'violation': kind, 'axiom_type': atype, 'axiom': axiom})
    lines = ['== Profile conformance of the released files (OWL API 5.1.9 profile checkers) ==',
             f"  {'release':8s} " + ' '.join(f'{p:>22s}' for p in PROFILES)]
    for v in VERS:
        cells = []
        for p in PROFILES:
            d = res[v][p]
            assert d['violations'] == len(d['axioms']), (v, p)
            cells.append('in profile' if d['in_profile'] else f"outside ({d['violations']} violations)")
        lines.append(f'  {v:8s} ' + ' '.join(f'{c:>22s}' for c in cells))
    # every release must be an OWL 2 DL ontology: the reasoning results of the paper presuppose it
    assert all(res[v]['OWL2DL']['in_profile'] for v in VERS), 'a release is not in OWL 2 DL'
    lines.append('')
    lines.append('== Axioms outside OWL 2 RL, by cause ==')
    for v in VERS:
        d = res[v]['OWL2RL']
        k = Counter(kind_of(a['axiom_type'], a['axiom']) for a in d['axioms'])
        d['by_kind'] = dict(sorted(k.items()))
        assert 'other' not in k, (v, [a for a in d['axioms'] if kind_of(a['axiom_type'], a['axiom']) == 'other'])
        lines.append(f"  {v}: {d['violations']} axioms  " + '; '.join(f'{n} {c}' for c, n in sorted(k.items())))
    lines.append('')
    lines.append('== The axioms of v2.2 outside OWL 2 RL ==')
    for a in res['v2.2']['OWL2RL']['axioms']:
        lines.append(f"  [{kind_of(a['axiom_type'], a['axiom'])}] {a['axiom']}")
    for p in ('OWL2EL', 'OWL2QL'):
        lines.append('')
        lines.append(f'== v2.2 outside {p}: violations by kind and axiom type ==')
        k = Counter((a['violation'], a['axiom_type']) for a in res['v2.2'][p]['axioms'])
        for (viol, at), n in sorted(k.items()):
            lines.append(f'  {n:3d}  {viol}  {at}')
    text = '\n'.join(lines)
    print(text)
    (RESULTS / 'E0_profiles.txt').write_text(text + '\n', encoding='utf-8')
    (RESULTS / 'E0_profiles.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
