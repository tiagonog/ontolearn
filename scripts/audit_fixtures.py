#!/usr/bin/env python3
"""audit_fixtures.py - E7, part F: the stated assumptions of the audit, exercised one at a time.

The paper states what scripts/audit.py assumes about multiple inheritance, equivalent
classes, anonymous class expressions, union and intersection signatures, signatures
inherited from a super-property or obtained through an inverse, imports and untyped
positions, and how the three kinds of stage-2 evidence lead to a verdict. Each fixture
below is a minimal OWL 2 DL ontology, written inline, that exercises one of those
statements. Its expected outcome is known by construction and is fixed here, next to the
fixture, so that the table printed by this script is a small manually verified reference set.

For every fixture the audit's prediction - at least one domain/range mismatch flagged
CONFLICT, or none - is also compared with the consistency verdict of the two DL reasoners
(HermiT and Openllet, which must agree): the audit predicts CONFLICT if and only if the
ontology is inconsistent.

The script exits with an error if any outcome differs from the expected one.
"""
import json, sys
import rdflib
from rdflib import URIRef
import audit
from common import RESULTS, verdict, write_tmp

FX = 'http://example.org/fx#'
HEAD = '''@prefix : <http://example.org/fx#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://example.org/fx> a owl:Ontology .
'''

# Each fixture: id, the assumption it exercises, the ontology, and the expected outcome:
#   candidates  {class: verdict} for the stage-1 candidates (exactly these). A class that occurs in no
#               signature is expected to be SUSPECT even when the fixture is about something else:
#               that is the advisory verdict the paper describes, raised here by construction
#   mismatches  {individual: 'CONFLICT' | 'mismatch'} (exactly these)
#   skipped     number of signatures counted as not evaluated
#   imports     number of owl:imports listed (not followed)
#   consistent  verdict expected from the DL reasoners
#   manifest    specialization links stated by a (fictitious) report
FIXTURES = [
    ('FX01', 'multiple inheritance and a chain of specializations: the closure reaches every ancestor', '''
:A a owl:Class . :B a owl:Class . :C a owl:Class ; rdfs:subClassOf :A , :B . :D a owl:Class ; rdfs:subClassOf :C .
:p a owl:ObjectProperty ; rdfs:domain :A . :q a owl:ObjectProperty ; rdfs:domain :B .
:x a owl:NamedIndividual , :D ; :p :x ; :q :x .
''', dict(candidates={}, mismatches={}, consistent=True)),

    ('FX02', 'equivalent named classes are connected and interchangeable in a signature', '''
:A a owl:Class . :B a owl:Class ; owl:equivalentClass :A .
:p a owl:ObjectProperty ; rdfs:domain :B .
:x a owl:NamedIndividual , :A ; :p :x .
''', dict(candidates={}, mismatches={}, consistent=True)),

    ('FX03', 'a class defined or constrained by an anonymous expression is not a candidate', '''
:A a owl:Class . :r a owl:ObjectProperty .
:D a owl:Class ; owl:equivalentClass [ a owl:Restriction ; owl:onProperty :r ; owl:someValuesFrom :A ] .
:E a owl:Class ; rdfs:subClassOf [ a owl:Restriction ; owl:onProperty :r ; owl:allValuesFrom :A ] .
''', dict(candidates={'A': 'ROOT'}, mismatches={}, consistent=True)),

    ('FX04', 'named members of an intersection are superclasses; named members of a union are subclasses', '''
:A a owl:Class . :B a owl:Class . :F a owl:Class . :G a owl:Class .
:E a owl:Class ; owl:equivalentClass [ a owl:Class ; owl:intersectionOf ( :A :B ) ] .
:U a owl:Class ; owl:equivalentClass [ a owl:Class ; owl:unionOf ( :F :G ) ] .
:p a owl:ObjectProperty ; rdfs:domain :A . :q a owl:ObjectProperty ; rdfs:domain :U .
:x a owl:NamedIndividual , :E ; :p :x . :y a owl:NamedIndividual , :F ; :q :y .
''', dict(candidates={}, mismatches={}, consistent=True)),

    ('FX05', 'the members of a disjoint union are subclasses and are pairwise disjoint', '''
:P a owl:Class ; owl:disjointUnionOf ( :Q :R ) . :Q a owl:Class . :R a owl:Class .
:p a owl:ObjectProperty ; rdfs:domain :R .
:x a owl:NamedIndividual , :Q ; :p :x .
''', dict(candidates={}, mismatches={'x': 'CONFLICT'}, consistent=False)),

    ('FX06', 'union signature with one alternative excluded: a mismatch, not a conflict', '''
:A a owl:Class . :B a owl:Class . :C a owl:Class ; owl:disjointWith :A .
:p a owl:ObjectProperty ; rdfs:domain [ a owl:Class ; owl:unionOf ( :A :B ) ] .
:x a owl:NamedIndividual , :C ; :p :x .
''', dict(candidates={'A': 'ROOT', 'B': 'ROOT', 'C': 'SUSPECT'}, mismatches={'x': 'mismatch'}, consistent=True)),

    ('FX07', 'union signature with every alternative excluded: a conflict', '''
:A a owl:Class . :B a owl:Class . :C a owl:Class ; owl:disjointWith :A , :B .
:p a owl:ObjectProperty ; rdfs:domain [ a owl:Class ; owl:unionOf ( :A :B ) ] .
:x a owl:NamedIndividual , :C ; :p :x .
''', dict(candidates={'A': 'ROOT', 'B': 'ROOT', 'C': 'SUSPECT'}, mismatches={'x': 'CONFLICT'}, consistent=False)),

    ('FX08', 'intersection signature with one member missing and none excluded: a mismatch', '''
:A a owl:Class . :B a owl:Class .
:p a owl:ObjectProperty ; rdfs:domain [ a owl:Class ; owl:intersectionOf ( :A :B ) ] .
:x a owl:NamedIndividual , :A ; :p :x .
''', dict(candidates={'A': 'ROOT', 'B': 'ROOT'}, mismatches={'x': 'mismatch'}, consistent=True)),

    ('FX09', 'intersection signature with one required member excluded: a conflict', '''
:A a owl:Class . :B a owl:Class . :C a owl:Class ; owl:disjointWith :B .
:p a owl:ObjectProperty ; rdfs:domain [ a owl:Class ; owl:intersectionOf ( :A :B ) ] .
:x a owl:NamedIndividual , :C ; :p :x .
''', dict(candidates={'A': 'ROOT', 'B': 'ROOT', 'C': 'SUSPECT'}, mismatches={'x': 'CONFLICT'}, consistent=False)),

    ('FX10', 'a signature is inherited from a super-property', '''
:A a owl:Class . :C a owl:Class ; owl:disjointWith :A .
:q a owl:ObjectProperty ; rdfs:domain :A . :p a owl:ObjectProperty ; rdfs:subPropertyOf :q .
:x a owl:NamedIndividual , :C ; :p :x .
''', dict(candidates={'A': 'ROOT', 'C': 'SUSPECT'}, mismatches={'x': 'CONFLICT'}, consistent=False)),

    ('FX11', 'a signature is obtained from the declared inverse', '''
:A a owl:Class . :C a owl:Class ; owl:disjointWith :A .
:r a owl:ObjectProperty ; rdfs:range :A . :p a owl:ObjectProperty ; owl:inverseOf :r .
:y a owl:NamedIndividual . :x a owl:NamedIndividual , :C ; :p :y .
''', dict(candidates={'A': 'ROOT', 'C': 'SUSPECT'}, mismatches={'x': 'CONFLICT'}, consistent=False)),

    ('FX12', 'a signature that is another kind of class expression is counted and not evaluated', '''
:A a owl:Class . :C a owl:Class . :r a owl:ObjectProperty .
:p a owl:ObjectProperty ; rdfs:domain [ a owl:Restriction ; owl:onProperty :r ; owl:someValuesFrom :A ] .
:x a owl:NamedIndividual , :C ; :p :x .
''', dict(candidates={'A': 'ROOT', 'C': 'SUSPECT'}, mismatches={}, skipped=1, consistent=True)),

    ('FX13', 'a position held by an untyped resource is not examined (the reasoner types it instead)', '''
:A a owl:Class . :B a owl:Class ; owl:disjointWith :A .
:p a owl:ObjectProperty ; rdfs:domain :A ; rdfs:range :B .
:x a owl:NamedIndividual , :A ; :p :u .
''', dict(candidates={'A': 'ROOT', 'B': 'ROOT'}, mismatches={}, consistent=True)),

    ('FX14', 'the object position is examined even when the subject has no asserted type', '''
:A a owl:Class . :B a owl:Class ; owl:disjointWith :A .
:p a owl:ObjectProperty ; rdfs:range :A .
:s a owl:NamedIndividual ; :p :y . :y a owl:NamedIndividual , :B .
''', dict(candidates={'A': 'ROOT', 'B': 'SUSPECT'}, mismatches={'y': 'CONFLICT'}, consistent=False)),

    ('FX15', 'imports are listed and not followed; a superclass in an unresolved import connects a class', '''
<http://example.org/fx> owl:imports <http://example.org/not-fetched> .
:K a owl:Class ; rdfs:subClassOf <http://example.org/not-fetched#Foreign> .
:Z a owl:Class .
''', dict(candidates={'Z': 'SUSPECT'}, mismatches={}, imports=1, consistent=True)),

    ('FX16', 'stage 2: manifest and usage evidence give Disconnected, unreferenced alone gives Suspect, none gives Root', '''
:P a owl:Class . :S a owl:Class ; rdfs:subClassOf :P .
:K a owl:Class . :M a owl:Class . :Z a owl:Class . :R a owl:Class .
:p a owl:ObjectProperty ; rdfs:range :P . :q a owl:ObjectProperty ; rdfs:domain :R .
:k a owl:NamedIndividual , :K . :x a owl:NamedIndividual , :S ; :p :k .
''', dict(candidates={'K': 'DISCONNECTED', 'M': 'DISCONNECTED', 'Z': 'SUSPECT', 'R': 'ROOT'},
          evidence={'K': ['usage', 'unreferenced'], 'M': ['manifest', 'unreferenced'], 'Z': ['unreferenced'], 'R': []},
          mismatches={'k': 'mismatch'}, manifest=[('M', 'P')], consistent=True)),
]

short = lambda x: str(x).split('#')[-1]


def run_fixture(ttl, manifest=()):
    g = rdflib.Graph()
    g.parse(data=HEAD + ttl, format='turtle')
    A = audit.Audit(g)
    iso = A.isolated([(URIRef(FX + a), URIRef(FX + b)) for a, b in manifest])
    mm = A.mismatches()
    return g, {
        'candidates': {short(k['class']): k['verdict'] for k in iso},
        'evidence': {short(k['class']): [e['evidence'] for e in k['evidence']] for k in iso},
        'mismatches': {short(m['individual']): 'CONFLICT' if m['conflict'] else 'mismatch' for m in mm},
        'skipped': A.not_evaluated,
        'imports': len(list(g.objects(None, rdflib.OWL.imports))),
    }


def main():
    rows, paths = [], []
    for fid, what, ttl, exp in FIXTURES:
        g, got = run_fixture(ttl, exp.get('manifest', ()))
        want = {'candidates': exp['candidates'], 'mismatches': exp['mismatches'],
                'skipped': exp.get('skipped', 0), 'imports': exp.get('imports', 0)}
        ok = all(got[k] == v for k, v in want.items())
        if 'evidence' in exp:
            ok = ok and got['evidence'] == exp['evidence']
        rows.append({'id': fid, 'assumption': what, 'expected': {**want, 'consistent': exp['consistent']},
                     'audit': {k: got[k] for k in want}, 'audit_as_expected': ok,
                     'audit_predicts_conflict': 'CONFLICT' in got['mismatches'].values()})
        paths.append(write_tmp(g, f'fixture_{fid}'))
    owl = verdict(paths)                                   # HermiT and Openllet; aborts if they disagree
    print('== F. Fixtures: one stated assumption of the audit per fixture (expected outcomes fixed by construction) ==')
    print(f"  {'id':5s} {'audit':8s} {'DL verdict':13s} {'conflict <=> inconsistent':26s} assumption exercised")
    for r, p in zip(rows, paths):
        cons = owl[p.name][0]
        r['dl_consistent'] = cons
        r['dl_as_expected'] = cons == r['expected']['consistent']
        r['prediction_agrees'] = r['audit_predicts_conflict'] == (not cons)
        print(f"  {r['id']:5s} {'as exp.' if r['audit_as_expected'] else 'DIFFERS':8s} {'consistent' if cons else 'INCONSISTENT':13s} "
              f"{'agree' if r['prediction_agrees'] else 'DISAGREE':26s} {r['assumption']}")
    n = len(rows)
    a = sum(r['audit_as_expected'] for r in rows); d = sum(r['dl_as_expected'] for r in rows); c = sum(r['prediction_agrees'] for r in rows)
    inc = sum(not r['dl_consistent'] for r in rows)
    print(f'  audit outcome as expected: {a}/{n}; DL verdict as expected: {d}/{n} ({inc} inconsistent); '
          f'audit CONFLICT prediction equals the DL verdict: {c}/{n}')
    (RESULTS / 'E7_audit_fixtures.json').write_text(json.dumps(
        {'fixtures': rows, 'n': n, 'audit_as_expected': a, 'dl_as_expected': d, 'prediction_agrees': c, 'inconsistent': inc},
        indent=1, ensure_ascii=False))
    if not (a == d == c == n):
        sys.exit('audit_fixtures: an outcome differs from the expected one')


if __name__ == '__main__':
    main()
