#!/usr/bin/env python3
"""generator.py - synthetic fact bases for the scalability and fault-injection studies.

gen_facts() returns a set of ABox triples that uses only vocabulary present in
EVERY released version (v1.0 included), so the same facts can be laid under any
schema. The base is clean by construction: consistent under v2.2 and free of
SHACL violations (both are asserted by the experiments that use it).

Prerequisite topologies (edges always point from a competency to an earlier one,
so the prerequisite graph is acyclic):

  chain   disjoint chains of length 10                        (first submission)
  tree    forest of ternary trees: each node requires its parent
  dag     each competency requires up to 3 of the 20 preceding ones
  dense   each competency requires each of the 8 preceding ones with probability 0.5

Besides competencies and prerequisites the generator emits learners, courses,
assessments with their questions (objective and subjective), performance records
(learner, question, level), learning resources, and KSA components.
All data are fictitious. Deterministic for a given (topology, size, seed).
"""
import random
from rdflib import OWL, RDF, RDFS, URIRef, Literal, Graph
from common import NS

TOPOLOGIES = ['chain', 'tree', 'dag', 'dense']
SIZES = [(5, 10, 2), (25, 50, 4), (100, 200, 4), (400, 500, 4), (1000, 1000, 5)]   # learners, competencies, records/learner
LEVELS = [('NP-Lembrar', 'Lembrar'), ('NP-Entender', 'Entender'), ('NP-Aplicar', 'Aplicar'),
          ('NP-Analisar', 'Analisar'), ('NP-Avaliar', 'AvaliarBloom'), ('NP-Criar', 'Criar')]


def prerequisite_edges(topology, n, rnd):
    """Pairs (i, j): competency i requires competency j, with j < i."""
    e = set()
    if topology == 'chain':
        for i in range(1, n):
            if i % 10 != 0:
                e.add((i, i - 1))
    elif topology == 'tree':
        for i in range(1, n):
            if i % 40 != 0:                       # a new root every 40 nodes
                base = (i // 40) * 40
                e.add((i, base + (i - base - 1) // 3))
    elif topology == 'dag':
        for i in range(1, n):
            lo = max(0, i - 20)
            for j in rnd.sample(range(lo, i), min(3, i - lo)):
                e.add((i, j))
    elif topology == 'dense':
        for i in range(1, n):
            for j in range(max(0, i - 8), i):
                if rnd.random() < 0.5:
                    e.add((i, j))
    else:
        raise ValueError(topology)
    return sorted(e)


def gen_facts(topology, size, seed):
    n_learners, n_comp, per_learner = size
    rnd = random.Random(f'{topology}/{size}/{seed}')
    g = Graph()
    ind = lambda name, cls: (g.add((NS[name], RDF.type, OWL.NamedIndividual)), g.add((NS[name], RDF.type, NS[cls])), NS[name])[2]

    levels = [ind(n, c) for n, c in LEVELS]
    comps = []
    for c in range(n_comp):
        u = ind(f'SC-{c:05d}', 'Competencia')
        g.add((u, NS.nome, Literal(f'Synthetic competency {c}')))
        comps.append(u)
        if c % 5 == 0:                            # KSA components for every fifth competency
            k = ind(f'SK-{c:05d}', 'Conhecimento'); g.add((u, NS.ehCompostoDeConhecimento, k))
            s = ind(f'SS-{c:05d}', 'Habilidade'); g.add((u, NS.ehCompostoDeHabilidade, s))
    for i, j in prerequisite_edges(topology, n_comp, rnd):
        g.add((comps[i], NS.requer, comps[j]))
    for c in range(0, n_comp, 4):                 # a resource for every fourth competency
        r = ind(f'SR-{c:05d}', 'RecursoDeAprendizagem'); g.add((r, NS.abordaCompetencia, comps[c]))

    n_assess = max(1, n_learners // 5)
    assessments = [ind(f'SA-{a:05d}', 'Avaliacao') for a in range(n_assess)]
    for l in range(n_learners):
        lu = ind(f'SL-{l:05d}', 'Aprendiz')
        g.add((lu, NS.nome, Literal(f'Synthetic learner {l}')))
        for k in range(per_learner):
            q = ind(f'SQ-{l:05d}-{k}', 'Objetiva' if k % 2 == 0 else 'Subjetiva')
            for comp in rnd.sample(comps, rnd.randint(1, 2)):
                g.add((q, NS.competenciasAvaliadas, comp))
            a = assessments[l % n_assess]
            # half of the links are recorded from the assessment, half from the question
            if k % 2 == 0: g.add((a, NS.questoesIncluidas, q))
            else: g.add((q, NS.fazParteDaAvaliacao, a))
            p = ind(f'SP-{l:05d}-{k}', 'DesempenhoDoAprendiz')
            g.add((p, NS.aprendizAvaliado, lu))
            g.add((p, NS.questaoRespondida, q))
            g.add((p, NS.proficienciaAtingida, rnd.choice(levels)))
    for a in assessments:                         # no assessment is left without a question
        if (a, NS.questoesIncluidas, None) not in g and (None, NS.fazParteDaAvaliacao, a) not in g:
            q = ind(f'SQ-fill-{str(a)[-5:]}', 'Objetiva'); g.add((q, NS.competenciasAvaliadas, comps[0])); g.add((a, NS.questoesIncluidas, q))
    return g


def lay(schema, facts):
    """schema graph + facts (level individuals already present in the schema are merged by IRI)."""
    for t in facts:
        schema.add(t)
    return schema


def stats(g):
    inds = set(g.subjects(RDF.type, OWL.NamedIndividual))
    return {'triples': len(g), 'individuals': len(inds), 'requer_edges': len(list(g.triples((None, NS.requer, None))))}
