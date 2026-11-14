#!/usr/bin/env python3
"""faults.py - E5: how each schema version behaves when the data are incomplete,
inconsistent or unexpected.

A clean synthetic fact base (scripts/generator.py, size index 1, 337 individuals)
is generated for each of the four prerequisite topologies and five seeds (20 bases).
One fault at a time is injected at a seeded random location, the faulty base is
laid under each released schema, and three independent channels are asked whether
they notice:

  OWL     HermiT and Openllet (which must agree): is the base inconsistent?
  SHACL   shapes/ontolearn-shapes.ttl: a violation that the clean base does not have?
  AUDIT   scripts/audit.py (no reasoner): a domain/range CONFLICT that the clean base does not have?
  RL      (v2.2 only) the OWL 2 RL rule engine (owlrl): does the closure raise an inconsistency message?

Eleven faults (X01-X11, with X03s a variant of X03) and three legitimate variations (L01-L03). A legitimate variation must
NOT be rejected; a schema that rejects it is over-restrictive.
Detection is logical, not statistical, so it does not depend on the size of the
base; the 20 bases vary where the fault lands and what surrounds it.
"""
import copy, json, random, sys
import owlrl
from rdflib import OWL, RDF, RDFS, URIRef, Literal, XSD
from common import *
from generator import *
import audit, shacl_validate

VERS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']
SIZE = SIZES[1]


def pick(g, cls, rnd, k=1):
    xs = sorted(s for s in g.subjects(RDF.type, NS[cls]) if str(s).split('#')[-1].startswith('S'))
    return rnd.sample(xs, k) if k > 1 else rnd.choice(xs)


def new(g, name, cls):
    g.add((NS[name], RDF.type, OWL.NamedIndividual)); g.add((NS[name], RDF.type, NS[cls])); return NS[name]


def X01(g, r):
    """contradictory record: a second level, of a different tier"""
    p = pick(g, 'DesempenhoDoAprendiz', r); cur = g.value(p, NS.proficienciaAtingida)
    other = r.choice([NS[n] for n, _ in LEVELS if NS[n] != cur]); g.add((p, NS.proficienciaAtingida, other))
def X02(g, r):
    """incomplete: a performance record loses its level"""
    p = pick(g, 'DesempenhoDoAprendiz', r); g.remove((p, NS.proficienciaAtingida, None))
def X03(g, r):
    """incomplete: a question loses every competency link"""
    q = pick(g, r.choice(['Objetiva', 'Subjetiva']), r); g.remove((q, NS.competenciasAvaliadas, None))
def X03s(g, r):
    """incomplete: a SUBJECTIVE question loses every competency link"""
    q = pick(g, 'Subjetiva', r); g.remove((q, NS.competenciasAvaliadas, None))
def X04(g, r):
    """incomplete: an assessment with no question"""
    new(g, 'FAULT-A', 'Avaliacao')
def X05(g, r):
    """unexpected relation: a question is made to require a competency"""
    g.add((pick(g, 'Objetiva', r), NS.requer, pick(g, 'Competencia', r)))
def X06(g, r):
    """type clash: a learner also typed as a competency"""
    g.add((pick(g, 'Aprendiz', r), RDF.type, NS.Competencia))
def X07(g, r):
    """type clash: a knowledge component also typed as a skill"""
    g.add((pick(g, 'Conhecimento', r), RDF.type, NS.Habilidade))
def X08(g, r):
    """type clash: a question typed objective and subjective"""
    g.add((pick(g, 'Objetiva', r), RDF.type, NS.Subjetiva))
def X09(g, r):
    """unexpected relation: a competency requires an undeclared, untyped resource"""
    g.add((pick(g, 'Competencia', r), NS.requer, NS['UNDECLARED-1']))
def X10(g, r):
    """prerequisite cycle: an edge closing a loop"""
    edges = sorted(g.subject_objects(NS.requer)); a, b = r.choice(edges); g.add((b, NS.requer, a))
def X11(g, r):
    """unexpected attribute: a learner carries a :descricao (its domain is a union that excludes users)"""
    g.add((pick(g, 'Aprendiz', r), NS.descricao, Literal('free text attached to a learner')))
def L01(g, r):
    """legitimate: an instructor enrolled as a learner in a course"""
    i = new(g, 'LEGIT-INST', 'Instrutor'); c = new(g, 'LEGIT-CUR', 'Curso'); g.add((i, NS.estaInscritoEm, c))
def L02(g, r):
    """legitimate: an attitude carrying a description"""
    a = new(g, 'LEGIT-ATT', 'Atitude'); g.add((a, NS.descricao, Literal('Valuing code readability')))
def L03(g, r):
    """legitimate: a performance record carrying a date"""
    g.add((pick(g, 'DesempenhoDoAprendiz', r), NS.data, Literal('2026-03-01T10:00:00Z', datatype=XSD.dateTime)))


ALL_CASES = [X01, X02, X03, X03s, X04, X05, X06, X07, X08, X09, X10, X11, L01, L02, L03]
CASES = [c for c in ALL_CASES if len(sys.argv) < 2 or c.__name__ in sys.argv[1:]]   # optional: only the named cases
CYCLE = f'PREFIX : <{NS}> ASK {{ ?c :requer+ ?c }}'


def conflicts(g):
    return {(m['individual'], tuple(m['expected'])) for m in audit.Audit(g).mismatches() if m['conflict']}


def rl_errors(g):
    h = copy.deepcopy(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(h)
    return sum(1 for _ in h.subjects(RDF.type, URIRef('http://www.daml.org/2002/03/agents/agent-ont#ErrorMessage')))


def mismatch_set(g):
    return {(m['individual'], tuple(m['expected'])) for m in audit.Audit(g).mismatches()}


def main():
    res = {c.__name__: {v: {'owl': 0, 'shacl': 0, 'audit_conflict': 0, 'audit_mismatch': 0, 'cycle_query': 0, 'rl': 0, 'n': 0} for v in VERS} for c in CASES}
    for topo in TOPOLOGIES:
        for seed in range(1, 6):
            facts = gen_facts(topo, SIZE, seed)
            clean = {v: lay(load(v), facts) for v in VERS}
            base_ok = verdict([write_tmp(clean[v], f'fl_clean_{v}') for v in VERS])
            assert all(x[0] for x in base_ok.values()), f'clean base inconsistent: {base_ok}'
            base_shacl = {v: set(shacl_validate.shacl(clean[v])) for v in VERS}
            base_conf = {v: conflicts(clean[v]) for v in VERS}
            base_mm = {v: mismatch_set(clean[v]) for v in VERS}
            assert rl_errors(clean['v2.2']) == 0
            paths, graphs = {}, {}
            for case in CASES:
                for v in VERS:
                    f = gen_facts(topo, SIZE, seed)
                    case(f, random.Random(f'{case.__name__}/{topo}/{seed}'))
                    g = lay(load(v), f)
                    graphs[(case.__name__, v)] = g
                    paths[(case.__name__, v)] = write_tmp(g, f'fl_{case.__name__}_{v}')
            owl = verdict(list(paths.values()))
            for (cn, v), g in graphs.items():
                r = res[cn][v]
                r['n'] += 1
                r['owl'] += not owl[paths[(cn, v)].name][0]
                r['shacl'] += bool(set(shacl_validate.shacl(g)) - base_shacl[v])
                r['audit_conflict'] += bool(conflicts(g) - base_conf[v])
                r['audit_mismatch'] += bool(mismatch_set(g) - base_mm[v])
                r['cycle_query'] += bool(g.query(CYCLE).askAnswer)
                if v == 'v2.2':
                    r['rl'] += rl_errors(g) > 0
            print(f'  base {topo}/{seed} done', flush=True, file=sys.stderr)
    for c in CASES:
        res[c.__name__]['description'] = c.__doc__.strip()
    out = RESULTS / 'E5_faults.json'
    if len(CASES) < len(ALL_CASES) and out.exists():          # partial run: merge into the existing results
        old = json.loads(out.read_text())
        old.update(res)
        res = {c.__name__: old[c.__name__] for c in ALL_CASES if c.__name__ in old}
    out.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    report(res)


def report(res):
    n = res['X01']['v2.2']['n']
    print(f'\n== E5. Detections out of {n} bases, per schema version: OWL inconsistency / SHACL violation / audit conflict ==')
    print(f"  {'case':5s} {'':66s} " + ' '.join(f'{v:^10s}' for v in VERS))
    for c, r in res.items():
        print(f"  {c:5s} {r['description'][:66]:66s} " + ' '.join(f"{r[v]['owl']:2d}/{r[v]['shacl']:2d}/{r[v]['audit_conflict']:2d} " for v in VERS))
    print(f'  OWL 2 RL rule engine on v2.2 (bases out of {n} with an inconsistency message): ' +
          ', '.join(f"{c} {res[c]['v2.2']['rl']}" for c in res))
    print('  Prerequisite cycles are found by the query  ASK { ?c :requer+ ?c }  in ' +
          ', '.join(f"{c} {'/'.join(str(res[c][v]['cycle_query']) for v in VERS)}" for c in res if any(res[c][v]['cycle_query'] for v in VERS)) +
          ' bases (v1.0/v2.0/v2.1/v2.2) and in no other case.')


if __name__ == '__main__':
    if sys.argv[1:] == ['--report']:
        report(json.loads((RESULTS / 'E5_faults.json').read_text()))
    else:
        main()
