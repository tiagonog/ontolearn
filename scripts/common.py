#!/usr/bin/env python3
"""common.py - shared infrastructure of the audit pipeline.

Three guarantees are enforced here, because the first submission of the audit
paper violated the first one (its ablation script rebuilt "v2.0" in memory and
the rebuilt graph differed from the released file by five triples):

1. LOCKED INPUTS. Every experiment reads the released files, never a
   reconstruction. Each file is checked against the SHA-256 digest recorded in
   scripts/LOCK.sha256 before use; a mismatch aborts the run.
2. ONE DEFINITION OF EACH AXIOM FAMILY. Ablation configurations are obtained
   by DELETING a family's triples from the released v2.2 graph (subtractive),
   so the "full" configuration is the released file itself, by construction.
3. ONE REASONING PATH, TWO REASONERS. All OWL 2 DL reasoning goes through
   scripts/java/Harness.java (OWL API 5.1.9; HermiT 1.4.3.517; Openllet 2.6.5).
   Every consistency verdict and every entailment census is computed with both
   reasoners, and the run aborts if they disagree (verdict() and census() below).
   Only the timings of E6 (scalability.py) use HermiT alone.
"""
import hashlib, os, subprocess, sys, tempfile
from pathlib import Path
import rdflib
from rdflib import OWL, RDF, RDFS, URIRef, BNode, Literal
from rdflib.collection import Collection

ROOT = Path(__file__).resolve().parent.parent
NS = rdflib.Namespace('http://www.ontolearn.com/ontologia#')
ONT = URIRef('http://www.ontolearn.com/ontologia')
JARS = os.environ.get('ONTOLEARN_JARS', str(ROOT / 'jars'))
RESULTS = ROOT / 'results'
RESULTS.mkdir(exist_ok=True)

FILES = {
    'v1.0': 'ontology/ontolearn.owl',
    'v2.0': 'ontology/ontolearn-v2.owl',
    'v2.1': 'ontology/ontolearn-v2.1.owl',
    'v2.2': 'ontology/ontolearn-v2.2.owl',
    'test-abox': 'verification/ontologia/ontolearn-abox-teste.ttl',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lock_table():
    table = {}
    for line in (ROOT / 'scripts' / 'LOCK.sha256').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            digest, rel = line.split(None, 1)
            table[rel.strip()] = digest
    return table


def verify_lock():
    """Verify every file of the lock table; returns their number (aborts on the first mismatch)."""
    return len([locked(rel) for rel in lock_table()])


def locked(rel):
    """Absolute path of a released file, after verifying its digest."""
    rel = FILES.get(rel, rel)
    table = lock_table()
    if rel not in table:
        sys.exit(f'LOCK: {rel} is not a locked input')
    got = sha256(ROOT / rel)
    if got != table[rel]:
        sys.exit(f'LOCK: digest mismatch for {rel}\n  expected {table[rel]}\n  found    {got}')
    return ROOT / rel


def load(rel):
    """Parse a locked file into an rdflib graph."""
    p = locked(rel)
    g = rdflib.Graph()
    with open(p, 'rb') as fh:
        g.parse(fh, format='turtle' if p.suffix == '.ttl' else 'xml')
    g.bind('', NS)
    return g


def sh(x):
    """Short display form of an RDF term."""
    return str(x).replace(str(NS), ':').replace(str(OWL), 'owl:').replace(str(RDFS), 'rdfs:').replace(str(RDF), 'rdf:')


# --------------------------------------------------------------- axiom families
# Each function removes ONE family from a graph that contains the released v2.2
# axiomatization. They are the only definition of the families used anywhere
# in the pipeline.

ROOTS13 = ['UsuarioDoAva', 'Competencia', 'RecursoDeAprendizagem', 'DesempenhoDoAprendiz',
           'Questao', 'Avaliacao', 'Curso', 'NiveisDeProficiencia', 'MilestoneDeAprendizagem',
           'TrajetoriasDeAprendizagem', 'Conhecimento', 'Habilidade', 'Atitude']
TIERS = ['Lembrar', 'Entender', 'Aplicar', 'Analisar', 'AvaliarBloom', 'Criar']
KSA_SUPERS = ['temComponenteKSA', 'ehComponenteKSADe']


def _remove_tree(g, node):
    for p, o in list(g.predicate_objects(node)):
        g.remove((node, p, o))
        if isinstance(o, BNode):
            _remove_tree(g, o)


def _all_disjoint_nodes(g, members):
    want = {NS[m] for m in members}
    for node in list(g.subjects(RDF.type, OWL.AllDisjointClasses)):
        for lst in g.objects(node, OWL.members):
            if set(Collection(g, lst)) == want:
                yield node


def _drop_union_member(g, prop, member):
    hit = 0
    for dom in g.objects(prop, RDFS.domain):
        for lst in list(g.objects(dom, OWL.unionOf)):
            items = list(Collection(g, lst))
            if member in items:
                items.remove(member)
                g.remove((dom, OWL.unionOf, lst))
                _remove_tree(g, lst)
                new = BNode()
                Collection(g, new, items)
                g.add((dom, OWL.unionOf, new))
                hit += 1
    return hit


def rm_F0a(g):
    """F0a (v2.0): NiveisDeProficiencia in the union domain of :descricao (repair of D2)."""
    assert _drop_union_member(g, NS.descricao, NS.NiveisDeProficiencia) == 1


def rm_F0b(g):
    """F0b (v2.1): Atitude in the domain of :descricao; :data also dates performance records."""
    assert _drop_union_member(g, NS.descricao, NS.Atitude) == 1
    doms = list(g.objects(NS.data, RDFS.domain))
    assert len(doms) == 1 and isinstance(doms[0], BNode)
    g.remove((NS.data, RDFS.domain, doms[0]))
    _remove_tree(g, doms[0])
    g.add((NS.data, RDFS.domain, NS.MilestoneDeAprendizagem))


def rm_F0(g):
    rm_F0a(g)
    rm_F0b(g)


def rm_F1(g):
    """F1: Subjetiva subClassOf Questao (repair of D1)."""
    assert (NS.Subjetiva, RDFS.subClassOf, NS.Questao) in g
    g.remove((NS.Subjetiva, RDFS.subClassOf, NS.Questao))


F2_PAIRS = [('Conhecimento', 'Habilidade'), ('Conhecimento', 'Atitude'),
            ('Habilidade', 'Atitude'), ('Objetiva', 'Subjetiva')]


def rm_F2(g):
    """F2: pairwise KSA disjointness and Objetiva/Subjetiva disjointness."""
    for a, b in F2_PAIRS:
        n = len(g)
        g.remove((NS[a], OWL.disjointWith, NS[b]))
        g.remove((NS[b], OWL.disjointWith, NS[a]))
        assert len(g) == n - 1


def rm_F2b(g):
    """F2b: AllDisjointClasses over the 13 root classes."""
    nodes = list(_all_disjoint_nodes(g, ROOTS13))
    assert len(nodes) == 1
    _remove_tree(g, nodes[0])


def rm_F3(g):
    """F3: existential participation constraints (three in v2.2)."""
    n = 0
    for cls, r in list(g.subject_objects(RDFS.subClassOf)):
        if isinstance(r, BNode) and (r, OWL.someValuesFrom, None) in g:
            g.remove((cls, RDFS.subClassOf, r))
            _remove_tree(g, r)
            n += 1
    assert n == 3, n


def rm_F4(g):
    """F4: KSA role hierarchy - the two super-properties with everything stated about them."""
    n = 0
    for sup in KSA_SUPERS:
        for s in list(g.subjects(RDFS.subPropertyOf, NS[sup])):
            g.remove((s, RDFS.subPropertyOf, NS[sup]))
            n += 1
        for p, o in list(g.predicate_objects(NS[sup])):
            g.remove((NS[sup], p, o))
            if isinstance(o, BNode):
                _remove_tree(g, o)
        for s, p in list(g.subject_predicates(NS[sup])):
            g.remove((s, p, NS[sup]))
    assert n == 6, n


def rm_F5(g):
    """F5: proficienciaAtingida is functional."""
    assert (NS.proficienciaAtingida, RDF.type, OWL.FunctionalProperty) in g
    g.remove((NS.proficienciaAtingida, RDF.type, OWL.FunctionalProperty))


def rm_F6(g):
    """F6 (v2.2): the six Bloom-tier classes are pairwise disjoint."""
    nodes = list(_all_disjoint_nodes(g, TIERS))
    assert len(nodes) == 1
    _remove_tree(g, nodes[0])


def rm_T(g):
    """Native family T: transitivity declarations (requer, ehRequeridaPor)."""
    hits = list(g.subjects(RDF.type, OWL.TransitiveProperty))
    assert len(hits) == 2
    for s in hits:
        g.remove((s, RDF.type, OWL.TransitiveProperty))


def rm_I(g):
    """Native family I: every owl:inverseOf axiom."""
    for t in list(g.triples((None, OWL.inverseOf, None))):
        g.remove(t)


FAMILIES = {'F0': rm_F0, 'F1': rm_F1, 'F2': rm_F2, 'F2b': rm_F2b, 'F3': rm_F3,
            'F4': rm_F4, 'F5': rm_F5, 'F6': rm_F6}
ORDER = ['F0', 'F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6']
NATIVE = {'T': rm_T, 'I': rm_I}
SUB = {'F0a': rm_F0a, 'F0b': rm_F0b}


def config(without=(), base='v2.2'):
    """The released graph minus the named families. config() IS the released file."""
    g = load(base)
    for f in without:
        {**FAMILIES, **NATIVE, **SUB}[f](g)
    return g


def write_tmp(g, tag):
    d = Path(tempfile.gettempdir()) / 'ontolearn-audit'
    d.mkdir(exist_ok=True)
    p = d / f'{tag}.owl'
    g.serialize(str(p), format='xml')
    return p


# ------------------------------------------------------------------- reasoning
def harness(*args, timeout=3600, props=()):
    """Run scripts/java/Harness.java; return stdout lines."""
    env = dict(os.environ)
    env.pop('JAVA_TOOL_OPTIONS', None)
    cmd = ['java', *os.environ.get('ONTOLEARN_JAVA_OPTS', '').split(),
           '-Dstdout.encoding=UTF-8', '-Dorg.slf4j.simpleLogger.defaultLogLevel=error', *props,
           '-cp', os.path.join(JARS, '*'), str(ROOT / 'scripts' / 'java' / 'Harness.java'), *map(str, args)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    if out.returncode != 0:
        sys.exit('Harness failed:\n' + out.stderr[-2000:])
    return [l for l in out.stdout.splitlines() if l.strip()]


REASONERS = ('HermiT', 'Openllet')


def _verdict(paths, reasoner):
    rows = harness('verdict', reasoner, *paths)[1:]
    res = {}
    for r in rows:
        f, _, cons, unsat, _, _ = r.split('\t')
        res[f] = (cons == 'consistent', unsat)
    return res


def verdict(paths, reasoner=None):
    """{filename: (consistent: bool, unsat: str)}

    With reasoner=None (the default) the verdict is computed with BOTH reasoners, HermiT and
    Openllet, and the run aborts if they disagree on any file; with a name, only that reasoner."""
    if reasoner is not None:
        return _verdict(paths, reasoner)
    res = _verdict(paths, REASONERS[0])
    for other in REASONERS[1:]:
        alt = _verdict(paths, other)
        diff = sorted(f for f in res if res[f] != alt.get(f))
        if diff:
            sys.exit(f'{REASONERS[0]} and {other} disagree on: ' + ', '.join(f'{f} {res[f]} vs {alt.get(f)}' for f in diff[:5]))
    return res


def _census(path, reasoner):
    rows = harness('census', reasoner, path)
    if rows and rows[0] == 'INCONSISTENT':
        return None
    return {tuple(r.split('\t')) for r in rows}


def census(path, reasoner=None):
    """Entailed atomic assertions over named individuals, or None if inconsistent.
    Returns a set of tuples: ('T', tag, ind, cls) | ('P', tag, s, p, o) | ('S', tag, a, b) | ('C', tag, sub, sup).

    With reasoner=None (the default) the census is computed with BOTH reasoners and the run aborts
    if the two sets differ; with a name, only that reasoner."""
    if reasoner is not None:
        return _census(path, reasoner)
    res = _census(path, REASONERS[0])
    for other in REASONERS[1:]:
        alt = _census(path, other)
        if res != alt:
            a, b = res or set(), alt or set()
            sys.exit(f'{REASONERS[0]} and {other} disagree on the census of {path}: '
                     f'{sorted(a - b)[:3]} / {sorted(b - a)[:3]} (inconsistent: {res is None} / {alt is None})')
    return res
