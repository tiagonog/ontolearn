#!/usr/bin/env python3
"""lineage.py - E8: the measured structural trace of the preserved development files.

Twelve files were preserved during development (ontology/versions/, plus the
released v1.0). This script hashes them, groups byte-identical files, and takes
the same inventory on every parseable state with scripts/audit.py.

Counting criterion (stated because the numbers depend on it): an entity is counted
when it is DECLARED in the file (rdf:type owl:Class, owl:ObjectProperty,
owl:DatatypeProperty, owl:NamedIndividual). Entities that are only used, without a
declaration, are not counted in the main columns; individuals that are typed by a
declared class but lack the owl:NamedIndividual declaration are reported separately.
v0 is a LaTeX export of a Protege class tree and is not an RDF document; its classes
are counted as the entries of the export.
Every file is checked against scripts/LOCK.sha256 before it is read.

The original report tabulates the same evolution for four milestones (v0, v2, v6, v10),
with metrics read from the ontology editor. Those values are transcribed in
claims/sbie2026.json ("trace") and are compared here with the measured ones.
"""
import hashlib, json, re
from pathlib import Path
import audit
from common import ROOT, RESULTS, locked

V = ROOT / 'ontology' / 'versions'
FILES = [('v0', V / 'v0_taxonomic_export.tex'), ('v1', V / 'v1.ttl'), ('v2', V / 'v2_taxonomic.ttl'), ('v3', V / 'v3.ttl'),
         ('v4', V / 'v4.ttl'), ('v5', V / 'v5.owl'), ('v6', V / 'v6_post-oops.owl'), ('v7', V / 'v7.owl'),
         ('v8', V / 'v8.owl'), ('v9', V / 'v9.ttl'), ('v10', ROOT / 'ontology' / 'ontolearn.owl'), ('v11', V / 'v11.ttl')]


def main():
    digest = {n: hashlib.sha256(locked(str(p.relative_to(ROOT))).read_bytes()).hexdigest() for n, p in FILES}   # each file is digest-locked
    groups = {}
    for n, d in digest.items():
        groups.setdefault(d, []).append(n)
    states = sorted(groups.values(), key=lambda g: int(g[0][1:]))
    print(f'{len(FILES)} preserved files, {len(states)} distinct states; identical: {[g for g in states if len(g) > 1]}')
    rows = []
    print(f"{'state':10s} {'Cls':>4s} {'ObjP':>4s} {'DatP':>4s} {'Inv':>4s} {'Ind':>4s} {'(+undecl.)':>10s} {'rho':>5s} {'subP':>4s} {'restr':>5s} {'card':>4s} {'disj':>4s}  DL        isolated: flagged/candidates  mismatches")
    for g in states:
        name = '='.join(g)
        p = dict(FILES)[g[0]]
        if p.suffix == '.tex':
            rows.append({'state': name, 'sha256': digest[g[0]], 'rdf': False})
            print(f'{name:10s} (LaTeX export of the class tree; not an RDF document)')
            continue
        r = audit.run(p)
        i = r['inventory']
        rho = (i['object properties'] + i['data properties']) / i['classes']
        flagged = [k['class'] for k in r['isolated'] if k['verdict'] != 'ROOT']
        row = {'state': name, 'sha256': digest[g[0]], 'rdf': True, 'classes': i['classes'], 'object_properties': i['object properties'],
               'data_properties': i['data properties'], 'inverse_axioms': i['owl:inverseOf'], 'individuals': i['individuals'],
               'individuals_incl_undeclared': i['individuals incl. undeclared'], 'rho': round(rho, 2),
               'sub_property_axioms': i['rdfs:subPropertyOf'],
               'restrictions': i['owl:someValuesFrom'] + i['owl:allValuesFrom'] + i['owl:hasValue'],
               'cardinality': i['unqualified cardinality'] + i['qualified cardinality'],
               'disjointness': i['owl:disjointWith'] + i['owl:AllDisjointClasses'], 'transitive': i['owl:TransitiveProperty'],
               'expressivity': r['expressivity'], 'isolated_candidates': len(r['isolated']), 'isolated_flagged': flagged,
               'mismatches': [f"{m['individual']}/{m['property']}" for m in r['mismatches']]}
        rows.append(row)
        print(f"{name:10s} {row['classes']:4d} {row['object_properties']:4d} {row['data_properties']:4d} {row['inverse_axioms']:4d} {row['individuals']:4d} "
              f"{row['individuals_incl_undeclared']:10d} {rho:5.2f} {row['sub_property_axioms']:4d} {row['restrictions']:5d} {row['cardinality']:4d} {row['disjointness']:4d}  "
              f"{row['expressivity']:9s} {len(flagged)}/{len(r['isolated'])} {flagged}  {row['mismatches']}")
    (RESULTS / 'E8_lineage.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    report_trace(rows)


METRICS = [('classes', 'classes'), ('object properties', 'object_properties'), ('data properties', 'data_properties'),
           ('owl:inverseOf', 'inverse_axioms'), ('owl:TransitiveProperty', 'transitive'), ('individuals', 'individuals')]


def report_trace(rows):
    """The values of the report's own table of the evolution, against the preserved files."""
    doc = json.loads(locked('claims/sbie2026.json').read_text(encoding='utf-8'))['trace']
    measured = {}
    for r in rows:
        for name in r['state'].split('='):
            measured[name] = r
    # v0: the export lists one \subsubsection per class under \subsection*{Classes}
    v0 = locked('ontology/versions/v0_taxonomic_export.tex').read_text(encoding='utf-8')
    v0_classes = len(set(re.findall(r'\\subsubsection\*\{([^}]*)\}', v0.split('\\subsection*{Classes}', 1)[1])))
    out = []
    print(f"\nThe report's table of the evolution ({doc['where']}) against the preserved files:")
    print(f"  {'state':5s} {'metric':24s} {'reported':>8s} {'measured':>8s}")
    for state, vals in doc['states'].items():
        for label, key in METRICS:
            rep = vals[label]
            if rep is None:
                continue
            if state == 'v0':
                if label != 'classes':
                    continue                  # the export of v0 holds the class tree only
                got = v0_classes
            else:
                got = measured[state][key]
            out.append({'state': state, 'metric': label, 'reported': rep, 'measured': got, 'agree': rep == got})
            print(f"  {state:5s} {label:24s} {rep:8d} {got:8d}  {'' if rep == got else 'DIFFERS'}")
    early = [o for o in out if o['state'] != 'v10']
    print(f"  earlier milestones (v0, v2, v6): {sum(o['agree'] for o in early)} of {len(early)} values agree; "
          f"final version (v10 = v1.0, claims C09-C14): {sum(o['agree'] for o in out if o['state'] == 'v10')} of {sum(o['state'] == 'v10' for o in out)}")
    (RESULTS / 'E8_report_trace.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
