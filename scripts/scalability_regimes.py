#!/usr/bin/env python3
"""scalability_regimes.py — two experiments on OntoCBLA v2.0:
E1) Scalability: synthetic ABox growth (learners, competency chains, performances);
    measure HermiT classification wall time, SPARQL path-query time, OWL-RL closure time.
E2) CQ inference regimes on scenario S1 (4-competency chain) and the native ABox:
    R1 asserted-only plain pattern | R2 SPARQL property path | R3 OWL-RL materialized.
    Plus the coverage defect: instances of Questao in v1.0 vs v2.0.
Deterministic (seeded). Released with the article.
"""
import time, random, copy, io, contextlib, sys
import rdflib, owlrl, owlready2
from rdflib import OWL, RDF, RDFS, URIRef, Literal, Namespace

NS = Namespace('http://www.ontolearn.com/ontologia#')
V2 = 'ontolearn_v2.owl'
V1 = 'ontolearn_v10'
random.seed(42)

def load(path):
    g = rdflib.Graph(); g.parse(path, format='xml'); g.bind('', NS); return g

def gen_abox(g, n_learners, n_comp, chain_len, perf_per_learner):
    """Add synthetic individuals typed against the real schema."""
    comps = []
    for c in range(n_comp):
        u = URIRef(NS + f'SC-{c:05d}')
        g.add((u, RDF.type, OWL.NamedIndividual)); g.add((u, RDF.type, NS.Competencia))
        g.add((u, NS.nome, Literal(f'Synthetic competency {c}')))
        comps.append(u)
    # prerequisite chains of length chain_len
    for i in range(0, n_comp - 1):
        if (i % chain_len) != chain_len - 1:
            g.add((comps[i+1], NS.requer, comps[i]))
    levels = [NS['NP-Aplicar'], NS['NP-Lembrar']]
    for l in range(n_learners):
        lu = URIRef(NS + f'SL-{l:05d}')
        g.add((lu, RDF.type, OWL.NamedIndividual)); g.add((lu, RDF.type, NS.Aprendiz))
        for k in range(perf_per_learner):
            pu = URIRef(NS + f'SP-{l:05d}-{k}')
            qu = URIRef(NS + f'SQ-{l:05d}-{k}')
            g.add((pu, RDF.type, OWL.NamedIndividual)); g.add((pu, RDF.type, NS.DesempenhoDoAprendiz))
            g.add((qu, RDF.type, OWL.NamedIndividual))
            g.add((qu, RDF.type, NS.Objetiva if (k % 2 == 0) else NS.Subjetiva))
            g.add((pu, NS.aprendizAvaliado, lu))
            g.add((pu, NS.questaoRespondida, qu))
            g.add((pu, NS.proficienciaAtingida, levels[k % 2]))
            g.add((qu, NS.competenciasAvaliadas, random.choice(comps)))
    return g

def hermit_time(g, tag):
    import tempfile, os
    tmp = os.path.join(tempfile.gettempdir(), f'sc_{tag}.owl')
    g.serialize(tmp, format='xml')
    world = owlready2.World()
    world.get_ontology('file://' + tmp).load()
    buf = io.StringIO(); t0 = time.time()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        owlready2.sync_reasoner(world, debug=0)
    return time.time() - t0

Q_PATH = f"""PREFIX : <{NS}>
SELECT (COUNT(*) AS ?n) WHERE {{ ?c :requer+ ?p . }}"""
Q_PLAIN = f"""PREFIX : <{NS}>
SELECT (COUNT(*) AS ?n) WHERE {{ ?c :requer ?p . }}"""

def sparql_count(g, q):
    t0 = time.time(); n = int(list(g.query(q))[0][0]); return n, time.time() - t0

def rl_time(g):
    h = copy.deepcopy(g); t0 = time.time()
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False,
                           datatype_axioms=False).expand(h)
    return h, time.time() - t0

if __name__ == '__main__':
    print('== E1 Scalability (v2.0 schema + synthetic ABox) ==')
    print(f"{'cfg':>22} {'triples':>8} {'indiv':>6} {'HermiT_s':>9} {'path_q_s':>9} {'path_n':>7} {'OWLRL_s':>8}")
    for (nl, nc, cl, pp) in [(5, 10, 5, 2), (25, 50, 5, 4), (100, 200, 8, 4),
                              (400, 500, 10, 4), (1000, 1000, 10, 5)]:
        g = gen_abox(load(V2), nl, nc, cl, pp)
        inds = len(set(g.subjects(RDF.type, OWL.NamedIndividual)))
        ht = hermit_time(g, f'{nl}_{nc}')
        pn, pt = sparql_count(g, Q_PATH)
        if len(g) <= 40000:
            _, rt = rl_time(g); rts = f'{rt:8.2f}'
        else:
            rts = '   (skip)'
        print(f"L{nl}/C{nc}/ch{cl}/p{pp:>2} {len(g):>8} {inds:>6} {ht:>9.2f} {pt:>9.3f} {pn:>7} {rts:>8}")

    print('\n== E2 CQ inference regimes — scenario S1: chain C4→C3→C2→C1 on v2.0 ==')
    s1 = load(V2)
    chain = [URIRef(NS + f'S1-C{i}') for i in range(1, 5)]
    for c in chain:
        s1.add((c, RDF.type, OWL.NamedIndividual)); s1.add((c, RDF.type, NS.Competencia))
    for i in range(3):
        s1.add((chain[i+1], NS.requer, chain[i]))
    # R1 asserted-only, plain pattern: direct prerequisites of C4
    q_direct = f"PREFIX : <{NS}> SELECT (COUNT(?p) AS ?n) WHERE {{ <{chain[3]}> :requer ?p }}"
    n1, _ = sparql_count(s1, q_direct)
    # R2 property path on asserted graph
    q_path = f"PREFIX : <{NS}> SELECT (COUNT(?p) AS ?n) WHERE {{ <{chain[3]}> :requer+ ?p }}"
    n2, _ = sparql_count(s1, q_path)
    # R3 OWL-RL materialized, plain pattern (with and without the transitivity axiom)
    mat, _ = rl_time(s1); n3, _ = sparql_count(mat, q_direct)
    s1_noT = copy.deepcopy(s1)
    for s in list(s1_noT.subjects(RDF.type, OWL.TransitiveProperty)):
        s1_noT.remove((s, RDF.type, OWL.TransitiveProperty))
    matNT, _ = rl_time(s1_noT); n3nt, _ = sparql_count(matNT, q_direct)
    print(f'  CQ4(S1) prerequisites of C4 — R1 asserted-plain: {n1} | R2 path(+): {n2} | '
          f'R3 materialized-plain: {n3} | R3 without T axiom: {n3nt}')

    print('\n== E2b Coverage defect: instances of :Questao (subclass closure) ==')
    qq = f"PREFIX : <{NS}> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> " \
         f"SELECT (COUNT(DISTINCT ?q) AS ?n) WHERE {{ ?q a/rdfs:subClassOf* :Questao }}"
    for tag, path in [('v1.0', V1), ('v2.0', V2)]:
        n, _ = sparql_count(load(path), qq)
        print(f'  {tag}: |instances(Questao)| = {n}')
