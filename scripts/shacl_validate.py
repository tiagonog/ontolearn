#!/usr/bin/env python3
"""shacl_validate.py - E4: ontological existence versus recorded data.

The F3 axioms guarantee that SOME filler exists in every model. They do not
guarantee that a link is recorded. This script checks the recorded data against
shapes/ontolearn-shapes.ttl (pyshacl; no inference, so the verdict concerns the
asserted graph only) and sets the result beside the OWL verdict for the same
graph, on four fact bases:

  reference   the released 20-individual ABox
  extended    reference + the 33-individual test ABox
  probe-F3    reference + a question, an assessment and a performance record
              with no link at all (three completeness faults)
  probe-F5    reference + one record carrying two levels of different tiers
"""
import json
from pyshacl import validate
from rdflib import Graph, RDF, URIRef, Namespace
from common import *

SH = Namespace('http://www.w3.org/ns/shacl#')
HDR = URIRef('http://www.ontolearn.com/ontologia/abox-teste')


def shacl(g):
    shapes = Graph().parse(str(locked('shapes/ontolearn-shapes.ttl')), format='turtle')
    conforms, rep, _ = validate(g, shacl_graph=shapes, inference='none', advanced=False)
    out = []
    for r in rep.subjects(RDF.type, SH.ValidationResult):
        out.append((sh(rep.value(r, SH.focusNode)), str(rep.value(r, SH.resultMessage))[:2]))
    return sorted(out)


def bases(v):
    ref = load(v)
    ext = load(v)
    for t in load('test-abox'):
        if t[0] != HDR:
            ext.add(t)
    p3 = load(v)
    for name, cls in [('PQ', 'Subjetiva'), ('PA', 'Avaliacao'), ('PD', 'DesempenhoDoAprendiz')]:
        p3.add((NS[name], RDF.type, OWL.NamedIndividual)); p3.add((NS[name], RDF.type, NS[cls]))
    p5 = load(v)
    p5.add((NS['DEMP-0003'], NS.proficienciaAtingida, NS['NP-Lembrar']))
    return {'reference': ref, 'extended': ext, 'probe-F3': p3, 'probe-F5': p5}


def main():
    res = {}
    print('== E4. OWL verdict (HermiT and Openllet agree) beside SHACL verdict (asserted graph) ==')
    for v in ['v1.0', 'v2.0', 'v2.1', 'v2.2']:
        B = bases(v)
        paths = {k: write_tmp(g, f'shacl_{v}_{k}') for k, g in B.items()}
        owl = verdict(list(paths.values()))
        for k, g in B.items():
            viol = shacl(g)
            byshape = {}
            for node, s in viol:
                byshape.setdefault(s, []).append(node)
            res[f'{v}/{k}'] = {'owl': 'consistent' if owl[paths[k].name][0] else 'inconsistent', 'shacl_violations': len(viol), 'by_shape': byshape}
            print(f"  {v:5s} {k:10s} OWL: {res[f'{v}/{k}']['owl']:12s} SHACL violations: {len(viol):2d}  " +
                  '  '.join(f'{s}: {", ".join(n)}' for s, n in sorted(byshape.items())))
    (RESULTS / 'E4_shacl.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
