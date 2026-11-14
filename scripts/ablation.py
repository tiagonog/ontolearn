#!/usr/bin/env python3
"""ablation.py - E1: what does each axiom family contribute?

Every configuration is derived from a LOCKED RELEASED FILE by deleting the
triples of one or more families (scripts/common.py). The full configuration
is the released v2.2 file itself; nothing is reconstructed.

 A  Consistency and unsatisfiable classes (HermiT and Openllet):
    incremental (families added back one at a time), leave-one-out, and the
    pre-repair order that exposed defect D2.
 B  Entailment census under OWL 2 DL (HermiT and Openllet, which must return the
    same set): entailed atomic assertions over
    the 20 named individuals, i.e. C(a) and p(a,b) that are NOT asserted.
    The assertional layer is identical in every configuration (check E6), so
    differences between configurations are attributable to the schema alone.
    Entailments are split by vocabulary: terms that already exist in v1.0
    versus terms introduced by the completion (the two KSA super-properties).
 C  The same census under OWL 2 RL rules (owlrl), to expose what the rule
    profile misses, plus the triple-level counts used in the first submission.
"""
import copy, json, sys
import owlrl
from rdflib import OWL, RDF, RDFS, URIRef
from common import *

V1_TERMS = None


def v1_vocab():
    global V1_TERMS
    if V1_TERMS is None:
        g = load('v1.0')
        V1_TERMS = {sh(x) for t in g for x in t if isinstance(x, URIRef) and str(x).startswith(str(NS))}
    return V1_TERMS


def split(census_set):
    """Counts of inferred assertions, by kind and by vocabulary."""
    v1 = v1_vocab()
    inf = [r for r in census_set if r[1] == 'I']
    def new_vocab(r):
        term = r[3] if r[0] == 'T' else (r[3] if r[0] == 'P' else None)
        return term is not None and term not in v1
    return {
        'class_assertions': sum(1 for r in inf if r[0] == 'T'),
        'property_assertions': sum(1 for r in inf if r[0] == 'P'),
        'equalities': sum(1 for r in inf if r[0] == 'S'),
        'inferred_total': sum(1 for r in inf if r[0] in 'TP'),
        'inferred_shared_vocabulary': sum(1 for r in inf if r[0] in 'TP' and not new_vocab(r)),
        'inferred_new_vocabulary': sum(1 for r in inf if r[0] in 'TP' and new_vocab(r)),
        'asserted': sum(1 for r in census_set if r[1] == 'A' and r[0] in 'TP'),
        'subsumptions_asserted': sum(1 for r in census_set if r[0] == 'C' and r[1] == 'A'),
        'subsumptions_inferred': sum(1 for r in census_set if r[0] == 'C' and r[1] == 'I'),
    }


def rl_census(g):
    """Atomic assertions over named individuals after OWL 2 RL closure, same definition as the DL census."""
    h = copy.deepcopy(g)
    n0 = len(h)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(h)
    inds = set(g.subjects(RDF.type, OWL.NamedIndividual))
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(p, URIRef)}
    out = set()
    for s, p, o in h:
        if s not in inds:
            continue
        tag = 'A' if (s, p, o) in g else 'I'
        if p == RDF.type and o in classes:
            out.add(('T', tag, sh(s), sh(o)))
        elif p in props and o in inds:
            out.add(('P', tag, sh(s), sh(p), sh(o)))
    ent = [t for t in h if t not in g]
    dom = [t for t in ent if any(isinstance(x, URIRef) and str(x).startswith(str(NS)) for x in t)]
    # What the "domain-relevant" count of the first submission is made of: atomic assertions over
    # the named individuals (the quantity the census reports), other triples whose subject is a
    # named individual (membership in anonymous class expressions and in owl:Thing, reflexive
    # owl:sameAs), and triples about classes, properties and restriction nodes.
    atomic = sum(1 for s, p, o in dom if s in inds and ((p == RDF.type and o in classes) or (p in props and o in inds)))
    ind_all = sum(1 for s, p, o in dom if s in inds)
    return out, {'asserted_triples': n0, 'entailed_triples': len(ent), 'domain_relevant_triples': len(dom),
                 'domain_relevant_atomic': atomic, 'domain_relevant_individual_other': ind_all - atomic,
                 'domain_relevant_schema': len(dom) - ind_all}


def main():
    res = {'A': [], 'B': {}, 'C': {}}
    # ------------------------------------------------------------------ A
    confs = [('v1.0 (released file)', load('v1.0'))]
    confs.append(('core = v2.2 minus F0..F6', config(ORDER)))
    for i in range(1, len(ORDER) + 1):
        confs.append((f'core + {"+".join(ORDER[:i])}', config(ORDER[i:])))
    confs.append(('core + F2b only (pre-repair order)', config([f for f in ORDER if f != 'F2b'])))
    for f in ORDER:
        confs.append((f'v2.2 - {f}', config([f])))
    confs.append(('v2.2 - F0a (D2 repair only)', config(['F0a'])))
    confs.append(('v2.2 - F0b (v2.1 domain extensions only)', config(['F0b'])))
    for v in ('v2.0', 'v2.1', 'v2.2'):
        confs.append((f'{v} (released file)', load(v)))
    paths = {}
    for k, (name, g) in enumerate(confs):
        paths[name] = write_tmp(g, f'A{k:02d}')
    vh = verdict(list(paths.values()), 'HermiT')        # part A shows the two reasoners side by side;
    vo = verdict(list(paths.values()), 'Openllet')      # every other verdict and census uses both by default
    print('== A. Consistency (HermiT 1.4.3.517 | Openllet 2.6.5) and unsatisfiable named classes ==')
    for name, p in paths.items():
        h, o = vh[p.name], vo[p.name]
        row = {'configuration': name, 'hermit': 'consistent' if h[0] else 'inconsistent', 'openllet': 'consistent' if o[0] else 'inconsistent',
               'unsat_hermit': h[1], 'unsat_openllet': o[1], 'agree': h == o}
        res['A'].append(row)
        print(f"  {name:44s} {row['hermit']:12s} | {row['openllet']:12s}  unsat: {h[1]} | {o[1]}  {'' if row['agree'] else '<< REASONERS DISAGREE'}")
    assert all(r['agree'] for r in res['A']), 'reasoners disagree'

    # --------------------------------------------------------------- B, C
    ent_confs = [('v1.0', load('v1.0')), ('v1.0 - T', config(['T'], 'v1.0')), ('v1.0 - I', config(['I'], 'v1.0')),
                 ('core', config(ORDER)), ('v2.0', load('v2.0')), ('v2.1', load('v2.1')), ('v2.2', load('v2.2'))]
    for f in ORDER:
        if f != 'F0':                       # v2.2 - F0 is inconsistent: no census
            ent_confs.append((f'v2.2 - {f}', config([f])))
    ent_confs += [('v2.2 - T', config(['T'])), ('v2.2 - I', config(['I']))]
    full_dl = None
    print('\n== B/C. Entailed atomic assertions over the 20 named individuals (asserted layer identical in all rows) ==')
    print(f"  {'configuration':12s} {'asserted':>8s} | {'DL inferred':>11s} {'C(a)':>5s} {'p(a,b)':>6s} {'shared':>6s} {'new':>4s} | {'RL inferred':>11s} {'DL-RL':>5s} | RL triples: asserted/entailed/domain-relevant")
    for k, (name, g) in enumerate(ent_confs):
        c = census(write_tmp(g, f'B{k:02d}'))
        d = split(c)
        rl, legacy = rl_census(g)
        dl_inf = {r[2:] + (r[0],) for r in c if r[1] == 'I' and r[0] in 'TP'}
        rl_inf = {r[2:] + (r[0],) for r in rl if r[1] == 'I'}
        missed = sorted(dl_inf - rl_inf)
        extra = sorted(rl_inf - dl_inf)
        assert not extra, f'OWL-RL derived assertions that the DL reasoners did not: {extra[:5]}'
        d.update({'rl_inferred': len(rl_inf), 'dl_minus_rl': len(missed), 'dl_minus_rl_examples': [' '.join(m[:-1]) for m in missed[:6]], **legacy})
        res['B'][name] = d
        res['C'][name] = legacy
        if name == 'v2.2':
            full_dl = c
        print(f"  {name:12s} {d['asserted']:8d} | {d['inferred_total']:11d} {d['class_assertions']:5d} {d['property_assertions']:6d} "
              f"{d['inferred_shared_vocabulary']:6d} {d['inferred_new_vocabulary']:4d} | {d['rl_inferred']:11d} {d['dl_minus_rl']:5d} | "
              f"{legacy['asserted_triples']}/{legacy['entailed_triples']}/{legacy['domain_relevant_triples']}"
              f" (= {legacy['domain_relevant_atomic']} atomic + {legacy['domain_relevant_individual_other']} other individual-level + {legacy['domain_relevant_schema']} schema-level)"
              f"  | named subsumptions {d['subsumptions_asserted']}+{d['subsumptions_inferred']}")
    # which assertions each family is responsible for (leave-one-out difference against the full release)
    print('\n== Attribution: inferred assertions lost when one family is removed from v2.2 ==')
    full_inf = {r for r in full_dl if r[1] == 'I'}
    res['attribution'] = {}
    for k, (name, g) in enumerate(ent_confs):
        if not name.startswith('v2.2 - '):
            continue
        c = census(write_tmp(g, f'B{k:02d}'))
        lost = sorted(full_inf - {r for r in c if r[1] == 'I'})
        gained = sorted({r for r in c if r[1] == 'I'} - full_inf)
        res['attribution'][name] = {'lost': len(lost), 'gained': len(gained), 'lost_examples': [' '.join(x[2:]) for x in lost[:4]]}
        print(f"  {name:10s} lost {len(lost):3d}  gained {len(gained):2d}   e.g. {[' '.join(x[2:]) for x in lost[:2]]}")
    # ------------------------------------------------ extended fact base
    # The 20-individual ABox contains one :requer edge, so it cannot exercise
    # transitivity. The 33-individual test ABox (four-competency prerequisite
    # chain, one-directional inverse assertions, negative cases) can.
    print('\n== D. Same census on the extended fact base (released schema + 33-individual test ABox; 53 individuals) ==')
    test = load('test-abox')
    hdr = URIRef('http://www.ontolearn.com/ontologia/abox-teste')
    facts = [t for t in test if t[0] != hdr]
    ext_confs = [('v1.0 schema', load('v1.0')), ('v2.2', load('v2.2'))] + \
                [(f'v2.2 - {f}', config([f])) for f in ['F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6', 'T', 'I']]
    res['D'] = {}
    full = None
    print(f"  {'configuration':12s} {'asserted':>8s} | {'DL inferred':>11s} {'C(a)':>5s} {'p(a,b)':>6s} {'shared':>6s} {'new':>4s} | {'RL inferred':>11s} {'DL-RL':>5s} | lost vs v2.2")
    for k, (name, g) in enumerate(ext_confs):
        for t in facts:
            g.add(t)
        c = census(write_tmp(g, f'D{k:02d}'))
        if c is None:
            res['D'][name] = 'inconsistent'
            print(f'  {name:12s} INCONSISTENT'); continue
        d = split(c)
        rl, _ = rl_census(g)
        dl_inf = {r[2:] + (r[0],) for r in c if r[1] == 'I' and r[0] in 'TP'}
        rl_inf = {r[2:] + (r[0],) for r in rl if r[1] == 'I'}
        d.update({'rl_inferred': len(rl_inf), 'dl_minus_rl': len(dl_inf - rl_inf), 'rl_minus_dl': len(rl_inf - dl_inf)})
        if name == 'v2.2':
            full = {r for r in c if r[1] == 'I' and r[0] in 'TP'}
        lost = len(full - {r for r in c if r[1] == 'I'}) if full is not None else None
        d['lost_vs_full'] = lost
        res['D'][name] = d
        print(f"  {name:12s} {d['asserted']:8d} | {d['inferred_total']:11d} {d['class_assertions']:5d} {d['property_assertions']:6d} "
              f"{d['inferred_shared_vocabulary']:6d} {d['inferred_new_vocabulary']:4d} | {d['rl_inferred']:11d} {d['dl_minus_rl']:5d} | {lost}")
    (RESULTS / 'E1_ablation.json').write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
