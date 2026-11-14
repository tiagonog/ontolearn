#!/usr/bin/env python3
"""cq_suite.py - E3: the competency questions, executed rather than reported.

 A  The eight queries DEPOSITED with the SBIE 2026 paper (sparql/cq1.rq ... cq8.rq),
    executed as deposited against every released version under three regimes,
    with an automatic diagnosis of every term or literal that cannot match.
 B  The corrected, parameterized suite (verification/sparql/, 20 cases with an
    answer key registered on 2026-10-11, before execution), executed against
    every released version, on the 20-individual ABox and on the extended fact
    base, under three regimes:
        asserted : the triples as written in the files;
        DL       : asserted + every atomic assertion entailed under OWL 2 DL
                   (HermiT and Openllet, which must return the same set);
        RL       : asserted + OWL 2 RL rule closure (owlrl).
 C  Axiom-utilization matrix: every case is re-executed (DL regime) on v2.2 with
    one family removed. A case "uses" a family iff its answer changes.
    This is what separates a question answered by the query engine from a
    question answered by the ontology's axioms.
 D  Three probe queries for the families that no competency question touches.
"""
import copy, json, re, sys
import owlrl
from rdflib import Graph, OWL, RDF, RDFS, URIRef, Literal
from common import *

VERSIONS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']
HDR = URIRef('http://www.ontolearn.com/ontologia/abox-teste')


def test_facts():
    return [t for t in load('test-abox') if t[0] != HDR]


def dl_materialize(g, tag):
    c = census(write_tmp(g, tag))
    if c is None:
        return None
    h = copy.deepcopy(g)
    N = lambda s: URIRef(str(NS) + s[1:]) if s.startswith(':') else URIRef(s)
    for r in c:
        if r[1] != 'I':
            continue
        if r[0] == 'T':
            h.add((N(r[2]), RDF.type, N(r[3])))
        elif r[0] == 'P':
            h.add((N(r[2]), N(r[3]), N(r[4])))
        elif r[0] == 'C':
            h.add((N(r[2]), RDFS.subClassOf, N(r[3])))
    return h


def rl_materialize(g):
    h = copy.deepcopy(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(h)
    return h


def regimes(g, tag):
    dl = dl_materialize(g, tag)
    # an inconsistent base entails everything: no regime with inference answers anything meaningful
    return {'asserted': g, 'DL': dl, 'RL': rl_materialize(g) if dl is not None else None}


def run(g, q):
    if g is None:
        return None
    return {tuple('' if v is None else str(v) for v in row) for row in g.query(q)}


def parametrize(text, params):
    """Replace the VALUES block of every line tagged '# parâmetro: <name>'."""
    out = []
    for line in text.splitlines():
        m = re.search(r'#\s*parâmetro:\s*(\w+)', line)
        if m and m.group(1) in params:
            key, val = m.group(1), params[m.group(1)]
            term = f':{val}' if key == 'nivel' else json.dumps(val, ensure_ascii=False)
            line = re.sub(r'\{[^}]*\}', '{ ' + term + ' }', line, count=1)
        out.append(line)
    return '\n'.join(out)


def diagnose(qtext, g):
    """Why can a deposited query not match? Terms absent from the ontology, and literals bound to nothing."""
    body = '\n'.join(l.split('#')[0] if not l.strip().startswith('PREFIX') else '' for l in qtext.splitlines())
    declared = {str(s) for s in g.subjects() if isinstance(s, URIRef)}
    issues = []
    for term in sorted(set(re.findall(r'(?<![\w<]):([A-Za-z][\w-]*)', body))):
        iri = str(NS) + term
        if iri not in declared:
            issues.append(f'term :{term} is not declared in the ontology')
    for prop, lit in re.findall(r'(rdfs:label|:\w+)\s+"([^"]+)"', body):
        p = RDFS.label if prop == 'rdfs:label' else URIRef(str(NS) + prop[1:])
        if not any(str(o) == lit for o in g.objects(None, p)):
            where = [sh(pp) for s, pp, o in g if isinstance(o, Literal) and str(o) == lit]
            alt = sorted({sh(pp) + ' "' + str(o) + '"' for s, pp, o in g if isinstance(o, Literal)
                          and _fold(str(o)) == _fold(lit) and str(o) != lit})
            msg = f'no resource has {prop} "{lit}"'
            if where: msg += f' (that literal occurs under {sorted(set(where))})'
            if alt: msg += f' (the data hold {alt})'
            issues.append(msg)
    for cls in re.findall(r':proficienciaAtingida\s+:(\w+)', body):
        if (URIRef(str(NS) + cls), RDF.type, OWL.Class) in g:
            issues.append(f':{cls} is a class used where a level individual is required')
    return issues


def _fold(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def main():
    res = {'A': {}, 'B': [], 'C': {}, 'D': {}}
    facts = test_facts()
    bases = {}
    for v in VERSIONS:
        ref = load(v)
        ext = load(v)
        for t in facts:
            ext.add(t)
        bases[v] = {'reference': regimes(ref, f'cq_{v}_ref'), 'extended': regimes(ext, f'cq_{v}_ext')}
        for b in ('reference', 'extended'):
            if bases[v][b]['DL'] is None:
                print(f'NOTE: {v} + {b} fact base is INCONSISTENT; inference regimes are reported as "inc".')
    res['inconsistent_bases'] = [f'{v}/{b}' for v in VERSIONS for b in ('reference', 'extended') if bases[v][b]['DL'] is None]

    # ------------------------------------------------------------------ A
    print('== A. Queries as deposited with the SBIE 2026 paper: number of solutions ==')
    print(f"  {'query':8s} " + ' '.join(f'{v + " " + r:>13s}' for v in VERSIONS for r in ('asserted', 'DL')) + '   diagnosis (v1.0)')
    for k in range(1, 9):
        q = locked(f'sparql/cq{k}.rq').read_text(encoding='utf-8')
        counts = {v: {r: len(run(bases[v]['reference'][r], q)) for r in ('asserted', 'DL', 'RL')} for v in VERSIONS}
        diag = diagnose(q, bases['v1.0']['reference']['asserted'])
        res['A'][f'cq{k}.rq'] = {'solutions': counts, 'diagnosis_v1.0': diag}
        print(f"  cq{k}.rq   " + ' '.join(f'{counts[v][r]:13d}' for v in VERSIONS for r in ('asserted', 'DL')))
        for d in diag:
            print(f'{"":12s}- {d}')
    assert all(n == 0 for q in res['A'].values() for v in q['solutions'].values() for n in v.values())

    # ------------------------------------------------------------------ B
    key = json.loads(locked('verification/dados/gabarito_qcs.json').read_text(encoding='utf-8'))
    base_of = {'v2.0': 'reference', 'v2.0+teste': 'extended'}
    print('\n== B. Corrected suite: 20 cases x 4 versions x 3 regimes (answer key registered 2026-10-11) ==')
    print(f"  {'case':7s} {'base':9s} {'exp':>3s} {'dep':>3s} | " + ' | '.join(f'{v:^11s}' for v in VERSIONS) + ' |  (asserted/DL/RL solutions; * = differs from the answer key)')
    ok_all = {v: {r: 0 for r in ('asserted', 'DL', 'RL')} for v in VERSIONS}
    for case in key['casos']:
        q = parametrize(locked('verification/sparql/' + case['consulta']).read_text(encoding='utf-8'), case['parametros'])
        expected = {tuple(t) for t in case['esperado']}
        dep = {tuple(t) for t in case['dependem_de_inferencia']}
        b = base_of[case['base']]
        row = {'id': case['id'], 'query': case['consulta'], 'base': b, 'expected': len(expected), 'inference_dependent': len(dep), 'results': {}}
        cells = []
        for v in VERSIONS:
            got = {r: run(bases[v][b][r], q) for r in ('asserted', 'DL', 'RL')}
            conf = {'asserted': got['asserted'] == expected - dep, 'DL': got['DL'] == expected, 'RL': got['RL'] == expected}
            for r in conf:
                ok_all[v][r] += conf[r]
            row['results'][v] = {r: {'n': None if got[r] is None else len(got[r]), 'conforms': conf[r]} for r in got}
            cells.append('/'.join('inc' if got[r] is None else f'{len(got[r])}{"" if conf[r] else "*"}' for r in ('asserted', 'DL', 'RL')))
        res['B'].append(row)
        print(f"  {case['id']:7s} {b:9s} {len(expected):3d} {len(dep):3d} | " + ' | '.join(f'{c:^11s}' for c in cells) + ' |')
    res['B_summary'] = ok_all
    print('  conforming cases (of 20): ' + '; '.join(f'{v}: ' + '/'.join(str(ok_all[v][r]) for r in ('asserted', 'DL', 'RL')) for v in VERSIONS))
    tot = sum(len(c['esperado']) for c in key['casos']); dep = sum(len(c['dependem_de_inferencia']) for c in key['casos'])
    print(f'  expected tuples: {tot}, of which {dep} depend on inference')

    # ------------------------------------------------------------------ C
    print('\n== C. Axiom-utilization matrix: cases whose DL-regime answer changes when a family is removed from v2.2 ==')
    fams = ['F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6', 'T', 'I']
    changed = {f: [] for f in fams}
    for f in fams:
        gr = config([f]); ge = config([f])
        for t in facts:
            ge.add(t)
        mat = {'reference': dl_materialize(gr, f'cqC_{f}_ref'), 'extended': dl_materialize(ge, f'cqC_{f}_ext')}
        for case in key['casos']:
            q = parametrize(locked('verification/sparql/' + case['consulta']).read_text(encoding='utf-8'), case['parametros'])
            b = base_of[case['base']]
            full = run(bases['v2.2'][b]['DL'], q)
            got = run(mat[b], q)
            if got != full:
                changed[f].append({'case': case['id'], 'lost': len(full - got), 'gained': len(got - full)})
    for f in fams:
        print(f"  v2.2 - {f:4s} {len(changed[f]):2d} cases change  " + ', '.join(f"{c['case']}(-{c['lost']})" for c in changed[f]))
    res['C'] = changed
    print('  (v2.2 - F0 is inconsistent and therefore answers nothing; see E1.)')

    # ------------------------------------------------------------------ D
    print('\n== D. Probe queries for families outside the reach of the eight questions ==')
    P = f'PREFIX : <{NS}> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> '
    probes = {
        'P1 question items by subsumption path (?q a/rdfs:subClassOf* :Questao)': P + 'SELECT DISTINCT ?q WHERE { ?q a/rdfs:subClassOf* :Questao }',
        'P2 question items by direct type (?q a :Questao)': P + 'SELECT DISTINCT ?q WHERE { ?q a :Questao }',
        'P3 KSA components of a competency (?c :temComponenteKSA ?k)': P + 'SELECT DISTINCT ?c ?k WHERE { ?c :temComponenteKSA ?k }',
    }
    for name, q in probes.items():
        row = {v: {r: len(run(bases[v]['reference'][r], q)) for r in ('asserted', 'DL', 'RL')} for v in VERSIONS}
        res['D'][name] = row
        print(f'  {name}')
        print('      ' + '   '.join(f'{v}: ' + '/'.join(str(row[v][r]) for r in ('asserted', 'DL', 'RL')) for v in VERSIONS) + '   (asserted/DL/RL)')
    (RESULTS / 'E3_cq_suite.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
