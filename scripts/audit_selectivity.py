#!/usr/bin/env python3
"""audit_selectivity.py - E7: how selective is the audit, and where does it stop working?

 A  Released versions. Stage-1 candidates and stage-2 verdicts on v1.0-v2.2, on the
    20-individual ABox and on the extended fact base, against the adjudicated defects.
 B  Mutation testing on v2.2 (ground truth by construction):
      B1  each of the 16 specialization links is deleted in turn - is the orphaned
          class flagged, and by which evidence?
      B2  each member of each union domain/range is deleted in turn - is the
          uncovered usage reported?
      B3  each axiom family is deleted in turn - does the claim check flag the
          corresponding claim of claims/audit-paper-v2.2.json?
 C  Negative controls:
      C1  the 13 legitimate root classes, in every version and fact base;
      C2  100 meaning-preserving mutants (one annotation triple removed);
      C3  ten external ontologies of different style (fetch_external.py).
 D  The DL name derived by the audit versus the constructs reported by the
    OWL API (DLExpressivityChecker), on all 14 ontologies.

No reasoner is used by the audit itself; D uses the OWL API only as an oracle.
"""
import copy, json, random, re, sys
from rdflib import Graph, OWL, RDF, RDFS, URIRef, BNode
from rdflib.collection import Collection
import audit, fetch_external
from common import *

HDR = URIRef('http://www.ontolearn.com/ontologia/abox-teste')
VERS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']
CLAIMS = json.loads(locked('claims/audit-paper-v2.2.json').read_text(encoding='utf-8'))['claims']
EDGES = next(c['edges'] for c in CLAIMS if c['check'] == 'taxonomy')
short = lambda x: str(x).split('#')[-1]


def with_ext(g):
    for t in load('test-abox'):
        if t[0] != HDR:
            g.add(t)
    return g


def findings(g, edges=(), own_ns=None):
    A = audit.Audit(g, own_ns)
    iso = A.isolated([(NS[a], NS[b]) for a, b in edges])
    mm = A.mismatches()
    return A, iso, mm


def part_A(res):
    # adjudicated defects of the released versions (authors' ground truth)
    truth_iso = {'v1.0': {'Subjetiva'}}
    print('== A. Released versions: isolated-class analysis and domain/range mismatches ==')
    print(f"  {'version':6s} {'facts':9s} {'stage-1':>7s} {'flagged':>7s} {'TP':>3s} {'FP':>3s} {'FN':>3s}   mismatches (C = contradicts a declared disjointness)")
    for v in VERS:
        for base in ('reference', 'extended'):
            g = load(v) if base == 'reference' else with_ext(load(v))
            A, iso, mm = findings(g)
            flagged = {short(k['class']) for k in iso if k['verdict'] != 'ROOT'}
            truth = truth_iso.get(v, set())
            tp, fp, fn = len(flagged & truth), len(flagged - truth), len(truth - flagged)
            mms = sorted({f"{short(m['individual'])}/{short(m['property'])}{'(C)' if m['conflict'] else ''}" for m in mm})
            res['A'][f'{v}/{base}'] = {'stage1': len(iso), 'flagged': sorted(flagged), 'tp': tp, 'fp': fp, 'fn': fn,
                                       'evidence': {short(k['class']): [e['evidence'] for e in k['evidence']] for k in iso if k['verdict'] != 'ROOT'},
                                       'mismatches': mms}
            print(f"  {v:6s} {base:9s} {len(iso):7d} {len(flagged):7d} {tp:3d} {fp:3d} {fn:3d}   {mms}")


def part_B(res):
    print('\n== B1. Mutation: one specialization link deleted (16 mutants x 2 fact bases), no manifest ==')
    print(f"  {'deleted link':40s} | reference: stage-1  evidence            | extended: stage-1  evidence")
    out = []
    for child, parent in EDGES:
        row = {'edge': f'{child} < {parent}'}
        for base in ('reference', 'extended'):
            g = load('v2.2') if base == 'reference' else with_ext(load('v2.2'))
            assert (NS[child], RDFS.subClassOf, NS[parent]) in g
            g.remove((NS[child], RDFS.subClassOf, NS[parent]))
            A, iso, mm = findings(g)
            me = next((k for k in iso if short(k['class']) == child), None)
            ev = sorted({e['evidence'] for e in me['evidence']}) if me else []
            # usage evidence can also surface as a mismatch when the orphaned class keeps subclasses
            via_mm = any(NS[child] in A.closure(m['types_set']) for m in mm)
            row[base] = {'stage1': me is not None, 'evidence': ev, 'mismatch': via_mm,
                         'detected': bool(ev) or via_mm}
        out.append(row)
        f = lambda r: f"{'yes' if r['stage1'] else 'no ':3s}      {','.join(r['evidence']) or ('mismatch only' if r['mismatch'] else '-'):20s}"
        print(f"  {row['edge']:40s} | {f(row['reference'])} | {f(row['extended'])}")
    res['B1'] = out
    for base in ('reference', 'extended'):
        n = len(out)
        det = sum(r[base]['detected'] for r in out)
        unr = sum('unreferenced' in r[base]['evidence'] for r in out)
        use = sum('usage' in r[base]['evidence'] or r[base]['mismatch'] for r in out)
        print(f'  {base}: detected {det}/{n}  (by unreferenced: {unr}; by usage: {use})')
        res[f'B1_summary_{base}'] = {'mutants': n, 'detected': det, 'by_unreferenced': unr, 'by_usage': use}

    print('\n== B2. Mutation: one member deleted from a union domain/range; audit (no reasoner) vs the DL reasoners (HermiT and Openllet agree) ==')
    g0 = load('v2.2')
    unions = []
    for pred in (RDFS.domain, RDFS.range):
        for p in sorted(set(g0.subjects(pred, None))):
            for e in g0.objects(p, pred):
                for lst in g0.objects(e, OWL.unionOf):
                    for m in Collection(g0, lst):
                        unions.append((p, pred, m))
    summary = {}
    for base in ('reference', 'extended'):
        clean = load('v2.2') if base == 'reference' else with_ext(load('v2.2'))
        before = {(m['individual'], m['property']) for m in audit.Audit(clean).mismatches()}
        pred_conflict, paths = [], []
        for k, (p, pred, member) in enumerate(unions):
            g = load('v2.2') if base == 'reference' else with_ext(load('v2.2'))
            for e in g.objects(p, pred):
                for lst in list(g.objects(e, OWL.unionOf)):
                    items = [x for x in Collection(g, lst) if x != member]
                    g.remove((e, OWL.unionOf, lst))
                    new = BNode(); Collection(g, new, items); g.add((e, OWL.unionOf, new))
            new_mm = [m for m in audit.Audit(g).mismatches() if (m['individual'], m['property']) not in before]
            pred_conflict.append(any(m['conflict'] for m in new_mm))
            paths.append(write_tmp(g, f'B2_{base}_{k:02d}'))
        owl = verdict(paths)
        incons = [not owl[p.name][0] for p in paths]
        tp = sum(a and b for a, b in zip(pred_conflict, incons)); tn = sum((not a) and (not b) for a, b in zip(pred_conflict, incons))
        fp = sum(a and not b for a, b in zip(pred_conflict, incons)); fn = sum((not a) and b for a, b in zip(pred_conflict, incons))
        summary[base] = {'mutants': len(unions), 'dl_inconsistent': sum(incons), 'audit_conflict': sum(pred_conflict),
                         'both': tp, 'neither': tn, 'audit_only': fp, 'dl_only': fn}
        print(f'  {base}: {len(unions)} mutants; inconsistent under OWL 2 DL: {sum(incons)}; audit CONFLICT: {sum(pred_conflict)}; '
              f'agree on {tp + tn}/{len(unions)} (both {tp}, neither {tn}, audit only {fp}, reasoners only {fn})')
    res['B2'] = summary

    print('\n== B3. Mutation: one axiom family deleted; claims of this paper re-checked ==')
    full = audit.Audit(load('v2.2'))
    inv = full.inventory(); dl, _ = full.expressivity(inv)
    base_ok = full.check_claims(CLAIMS, inv, dl, str(NS))
    assert all(c['verdict'] == 'REALIZED' for c in base_ok)
    print(f'  released v2.2: {len(base_ok)}/{len(base_ok)} claims REALIZED')
    res['B3'] = {}
    for f in ['F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6', 'T', 'I']:
        A = audit.Audit(config([f]))
        inv = A.inventory(); dl, _ = A.expressivity(inv)
        bad = [c['id'] for c in A.check_claims(CLAIMS, inv, dl, str(NS)) if c['verdict'] != 'REALIZED']
        res['B3'][f] = bad
        print(f'  v2.2 - {f:3s}: {len(bad)} claim(s) no longer realized: {bad}')
    assert all(res['B3'].values())


def part_C(res):
    print('\n== C1. Negative control: the 13 root classes are never flagged ==')
    fp = 0
    for v in VERS:
        for base in ('reference', 'extended'):
            g = load(v) if base == 'reference' else with_ext(load(v))
            _, iso, _ = findings(g)
            fp += sum(1 for k in iso if short(k['class']) in ROOTS13 and k['verdict'] != 'ROOT')
    print(f'  false positives over 13 roots x 4 versions x 2 fact bases = {13 * 8} checks: {fp}')
    res['C1'] = {'checks': 13 * 8, 'false_positives': fp}

    print('== C2. Negative control: meaning-preserving mutants (one annotation triple removed) ==')
    g0 = load('v2.2')
    sig = lambda g: (json.dumps(audit.Audit(g).isolated(), default=str, sort_keys=True),
                     sorted((str(m['individual']), str(m['property'])) for m in audit.Audit(g).mismatches()))
    ref = sig(g0)
    annots = sorted(t for t in g0 if t[1] in (RDFS.label, RDFS.comment))
    rnd = random.Random(42)
    changed = 0
    for t in rnd.sample(annots, 100):
        g = copy.deepcopy(g0); g.remove(t)
        changed += sig(g) != ref
    print(f'  100 mutants: {changed} with a different audit result')
    res['C2'] = {'mutants': 100, 'changed': changed}

    print('== C3. External ontologies (own-namespace classes only) ==')
    print(f"  {'ontology':7s} {'triples':>7s} {'classes':>7s} {'ind.':>5s} {'stage-1':>7s} {'DISCONN.':>8s} {'SUSPECT':>7s} {'mism.':>5s} {'not eval.':>9s} {'imports':>7s}")
    ext = []
    for name, src, ns, _ in fetch_external.EXTERNAL:
        p = fetch_external.path_of(name, ROOT / 'external')
        r = audit.run(p, own_ns=ns)
        g = audit.parse(p)
        alt = len(list(g.triples((None, URIRef('http://schema.org/domainIncludes'), None)))) + \
              len(list(g.triples((None, URIRef('https://schema.org/domainIncludes'), None))))
        row = {'name': name, 'source': src, 'triples': r['triples'], 'classes': r['inventory']['classes'],
               'individuals': r['inventory']['individuals incl. undeclared'], 'stage1': len(r['isolated']),
               'disconnected': [k['class'] for k in r['isolated'] if k['verdict'] == 'DISCONNECTED'],
               'suspect': [k['class'] for k in r['isolated'] if k['verdict'] == 'SUSPECT'],
               'mismatches': len(r['mismatches']), 'not_evaluated': r['signatures_not_evaluated'],
               'imports': len(r['imports']), 'schema_domainIncludes_triples': alt, 'expressivity': r['expressivity']}
        ext.append(row)
        print(f"  {name:7s} {row['triples']:7d} {row['classes']:7d} {row['individuals']:5d} {row['stage1']:7d} {len(row['disconnected']):8d} {len(row['suspect']):7d} "
              f"{row['mismatches']:5d} {row['not_evaluated']:9d} {row['imports']:7d}   {'SUSPECT: ' + ', '.join(row['suspect'][:4]) + (' ...' if len(row['suspect']) > 4 else '') if row['suspect'] else ''}"
              + (f'  [{alt} schema:domainIncludes annotations]' if alt else ''))
    res['C3'] = ext


TOKENS = ['RRESTR', 'UNIVRESTR', 'CINT', '(D)', 'C', 'U', 'E', 'H', '+', 'O', 'I', 'N', 'Q', 'F', 'R']


def owlapi_name(s):
    """Classical DL name from the construct string of the OWL API's DLExpressivityChecker."""
    toks, i = [], 0
    while i < len(s):
        for t in TOKENS:
            if s.startswith(t, i):
                toks.append(t); i += len(t); break
        else:
            raise ValueError(s[i:])
    alc = 'C' in toks or ('U' in toks and 'E' in toks)
    name = 'S' if alc and ('+' in toks or 'R' in toks) else ('ALC' if alc else 'AL')
    name += 'R' if 'R' in toks else ('H' if 'H' in toks else '')
    name += 'O' if 'O' in toks else ''
    name += 'I' if 'I' in toks else ''
    name += 'Q' if 'Q' in toks else ('N' if 'N' in toks else ('F' if 'F' in toks else ''))
    name += '(D)' if '(D)' in toks else ''
    return name


def part_D(res):
    print('\n== D. DL name: audit derivation vs OWL API construct report ==')
    files = [(v, locked(v), None) for v in VERS] + [(e[0], fetch_external.path_of(e[0], ROOT / 'external'), e[2]) for e in fetch_external.EXTERNAL]
    rows = harness('metrics', *[f[1] for f in files])[1:]
    agree = 0
    res['D'] = []
    for (name, p, ns), r in zip(files, rows):
        c = r.split('\t')
        mine = audit.run(p)['expressivity']
        theirs = owlapi_name(c[7])
        agree += mine == theirs
        res['D'].append({'ontology': name, 'audit': mine, 'owlapi_constructs': c[7], 'owlapi_name': theirs, 'agree': mine == theirs,
                         'axioms': int(c[1]), 'logical_axioms': int(c[2])})
        print(f"  {name:7s} audit {mine:10s} OWL API {theirs:10s} ({c[7]})  {'agree' if mine == theirs else 'DIFFER'}")
    print(f'  agreement: {agree}/{len(files)}')
    res['D_agreement'] = [agree, len(files)]


if __name__ == '__main__':
    res = {'A': {}}
    part_A(res); part_B(res); part_C(res); part_D(res)
    (RESULTS / 'E7_audit_selectivity.json').write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
