#!/usr/bin/env python3
"""build_v2_1.py - OntoLearn v2.1: revision of v2.0 after the OOPS! diagnosis
and the plausibility evaluation. Every change is listed explicitly; nothing
else is modified. Blank nodes are relabelled canonically, so the output is
byte-for-byte reproducible from the same input.

Usage: python3 build_v2_1.py <ontolearn-v2.owl> <output.ttl> <output.owl>
"""
import sys
import rdflib
from rdflib import OWL, RDF, RDFS, URIRef, BNode, Literal
from rdflib.collection import Collection
from rdflib.compare import to_canonical_graph

NS = rdflib.Namespace('http://www.ontolearn.com/ontologia#')
DCT = rdflib.Namespace('http://purl.org/dc/terms/')
ONT = URIRef('http://www.ontolearn.com/ontologia')

src, out_ttl, out_owl = sys.argv[1], sys.argv[2], sys.argv[3]
g = rdflib.Graph()
with open(src, 'rb') as fh:
    g.parse(fh, format='xml')
log = []


def pt(text):
    return Literal(text, lang='pt')


def union(*members):
    node, lst = BNode(), BNode()
    Collection(g, lst, list(members))
    g.add((node, RDF.type, OWL.Class))
    g.add((node, OWL.unionOf, lst))
    return node


def remove_tree(node):
    """Remove a blank node and everything reachable from it (restrictions, lists)."""
    for p, o in list(g.predicate_objects(node)):
        g.remove((node, p, o))
        if isinstance(o, BNode):
            remove_tree(o)


def set_annotation(entity, prop, text, why):
    old = [str(o) for o in g.objects(entity, prop)]
    g.remove((entity, prop, None))
    g.add((entity, prop, pt(text)))
    log.append((entity, prop, why, old))


# ---- R1. Plausibility evaluation (statement 17): learner and instructor are
# roles that the same user may hold in different courses. Remove the disjointness.
g.remove((NS.Aprendiz, OWL.disjointWith, NS.Instrutor))
g.remove((NS.Instrutor, OWL.disjointWith, NS.Aprendiz))
log.append((NS.Aprendiz, OWL.disjointWith, 'R1 removed: Aprendiz disjointWith Instrutor', []))

# ---- R2. Plausibility evaluation (statement 10): a learning resource may exist
# without being mapped to a competency. Remove RecursoDeAprendizagem ⊑ ∃abordaCompetencia.Competencia.
for r in list(g.objects(NS.RecursoDeAprendizagem, RDFS.subClassOf)):
    if isinstance(r, BNode) and (r, OWL.onProperty, NS.abordaCompetencia) in g:
        g.remove((NS.RecursoDeAprendizagem, RDFS.subClassOf, r))
        remove_tree(r)
        log.append((NS.RecursoDeAprendizagem, RDFS.subClassOf, 'R2 removed: ⊑ ∃abordaCompetencia.Competencia', []))

# ---- R3. OOPS! P11: domain and range of the KSA composition super-properties.
g.add((NS.temComponenteKSA, RDFS.range, union(NS.Conhecimento, NS.Habilidade, NS.Atitude)))
g.add((NS.ehComponenteKSADe, RDFS.domain, union(NS.Conhecimento, NS.Habilidade, NS.Atitude)))
g.add((NS.ehComponenteKSADe, RDFS.range, NS.Competencia))
log.append((NS.temComponenteKSA, RDFS.range, 'R3 added: Conhecimento ⊔ Habilidade ⊔ Atitude', []))
log.append((NS.ehComponenteKSADe, RDFS.domain, 'R3 added: Conhecimento ⊔ Habilidade ⊔ Atitude', []))
log.append((NS.ehComponenteKSADe, RDFS.range, 'R3 added: Competencia', []))

# ---- R4. Domain of :descricao also covers Atitude (the other two KSA classes were already there).
for dom in g.objects(NS.descricao, RDFS.domain):
    for lst in g.objects(dom, OWL.unionOf):
        Collection(g, lst).append(NS.Atitude)
log.append((NS.descricao, RDFS.domain, 'R4 changed: union extended with Atitude', []))

# ---- R5. :data also dates performance records (domain: Milestone ⊔ DesempenhoDoAprendiz).
g.remove((NS.data, RDFS.domain, NS.MilestoneDeAprendizagem))
g.add((NS.data, RDFS.domain, union(NS.MilestoneDeAprendizagem, NS.DesempenhoDoAprendiz)))
log.append((NS.data, RDFS.domain, 'R5 changed: MilestoneDeAprendizagem ⊔ DesempenhoDoAprendiz', []))

# ---- R6. Annotations (OOPS! P08 and the clarity results of the plausibility evaluation).
set_annotation(NS.Subjetiva, RDFS.label, 'Subjetiva', 'R6 P08')
C = {
    NS.Subjetiva: 'Questão de resposta aberta, redigida pelo aprendiz, cuja correção depende de critérios de avaliação ou do julgamento do instrutor.',
    NS.Objetiva: 'Questão de resposta fechada, com alternativas e resposta correta predefinidas.',
    NS.Conhecimento: 'Componente cognitivo de uma competência (saber): informações, fatos, conceitos e princípios de um domínio que o aprendiz precisa compreender, como a definição de superclasse e de subclasse.',
    NS.Habilidade: 'Componente prático de uma competência (saber fazer): capacidade de aplicar conhecimentos para executar tarefas ou resolver problemas, como implementar uma subclasse que sobrescreve um método.',
    NS.Atitude: 'Componente atitudinal de uma competência (saber ser): disposições, valores e posturas que orientam a ação do aprendiz ao mobilizar conhecimentos e habilidades, como valorizar a legibilidade do código.',
    NS.Avaliacao: 'Instrumento aplicado em um curso para obter evidências da aprendizagem, como uma prova ou um questionário, composto por uma ou mais questões.',
    NS.Curso: 'Oferta formativa disponibilizada no AVA, com título, nível e descrição, na qual os aprendizes se inscrevem e à qual se vinculam os instrutores responsáveis, os recursos e as avaliações.',
    NS.DesempenhoDoAprendiz: 'Registro da resposta de um aprendiz a uma questão, que associa o aprendiz avaliado, a questão respondida e o nível de proficiência atingido; é a unidade de evidência da qual se obtém o nível do aprendiz em cada competência.',
    NS.Formativo: 'Registro de desempenho obtido em uma avaliação de caráter formativo.',
    NS.MilestoneDeAprendizagem: 'Marco de progresso conquistado por um aprendiz, como a conclusão de um curso ou de uma trilha, registrado com data e associado às competências cuja conquista ele atesta.',
    NS.NiveisDeProficiencia: 'Nível de domínio demonstrado ou exigido em uma competência, na escala dos seis níveis do domínio cognitivo da Taxonomia de Bloom revisada (Lembrar, Entender, Aplicar, Analisar, Avaliar e Criar), representados pelas subclasses. Cada instância é um nível da escala.',
    NS.TrajetoriasDeAprendizagem: 'Percurso de aprendizagem realizado por um aprendiz, descrito por uma sequência ordenada de etapas e associado às competências que ele desenvolve.',
    NS.desempenhoCompetencias: 'Relaciona o aprendiz a cada registro de desempenho que documenta uma de suas respostas. A relação aponta para o registro, e não para a competência: as competências evidenciadas são obtidas pela questão respondida e pelas competências que ela avalia.',
    NS.competenciasDoDesempenho: 'Relaciona o registro de desempenho ao aprendiz que o produziu; inversa de desempenhoCompetencias.',
    NS.historicoAprendizagem: 'Relaciona o aprendiz aos recursos de aprendizagem que ele acessou no AVA, tenha ou não concluído o seu uso.',
    NS.competenciasEnvolvidas: 'Relaciona um marco ou uma trajetória de aprendizagem às competências a que se refere: no marco, as competências cuja conquista ele atesta; na trajetória, as competências que ela desenvolve.',
    NS.temComponenteKSA: 'Relaciona uma competência a cada um de seus componentes CHA (conhecimento, habilidade ou atitude); generaliza ehCompostoDeConhecimento, ehCompostoDeHabilidade e ehCompostoDeAtitude.',
    NS.ehComponenteKSADe: 'Relaciona um componente CHA (conhecimento, habilidade ou atitude) à competência que ele compõe; inversa de temComponenteKSA, generaliza compoeConhecimentoEm, compoeHabilidadeEm e compoeAtitudeEm.',
    NS.data: 'Data e hora do evento registrado: a conquista de um marco de aprendizagem ou a resposta de um registro de desempenho.',
}
for e, text in C.items():
    set_annotation(e, RDFS.comment, text, 'R6 comment')
L = {
    NS.NiveisDeProficiencia: 'Nível de Proficiência',
    NS.TrajetoriasDeAprendizagem: 'Trajetória de Aprendizagem',
    NS.desempenhoCompetencias: 'registros de desempenho',
    NS.competenciasDoDesempenho: 'aprendiz do registro',
}
for e, text in L.items():
    set_annotation(e, RDFS.label, text, 'R6 label')

# ---- R7. Version metadata (the ontology IRI is unchanged).
g.set((ONT, OWL.versionInfo, Literal('2.1')))
g.remove((ONT, RDFS.comment, None))
g.add((ONT, RDFS.comment, Literal(
    'OntoLearn v2.1 - revisão da v2.0 após o diagnóstico do OOPS! e a avaliação de plausibilidade: '
    'rótulos, comentários, domínio e imagem das superpropriedades da composição CHA; Atitude no domínio '
    'de descricao; data aplicável também a registros de desempenho; retirada da disjunção entre Aprendiz '
    'e Instrutor e da restrição de que todo recurso aborda uma competência; definições reescritas. '
    'Gerada por build_v2_1.py.', lang='pt')))
g.add((ONT, RDFS.comment, Literal(
    'OntoLearn v2.1 - revision of v2.0 after the OOPS! diagnosis and the plausibility evaluation: labels, '
    'comments, domain and range of the KSA composition super-properties; Atitude added to the domain of '
    'descricao; data extended to performance records; Aprendiz/Instrutor disjointness and the existential '
    'restriction on RecursoDeAprendizagem removed; definitions rewritten. Generated by build_v2_1.py.',
    lang='en')))

# Canonical blank-node labels, renamed b1, b2, ... in sorted order, and sorted
# subjects/predicates in the RDF/XML output -> byte-for-byte reproducible files.
class SortedGraph(rdflib.Graph):
    def subjects(self, predicate=None, object=None, unique=False):
        return iter(sorted(set(super().subjects(predicate, object)), key=lambda x: x.n3()))

    def predicate_objects(self, subject=None, unique=False):
        return iter(sorted(set(super().predicate_objects(subject)), key=lambda po: (po[0].n3(), po[1].n3())))


canon = sorted(to_canonical_graph(g), key=lambda t: tuple(x.n3() for x in t))
bnodes = sorted({x for t in canon for x in t if isinstance(x, BNode)}, key=lambda x: x.n3())
rename = {b: BNode(f'b{i}') for i, b in enumerate(bnodes, 1)}
cg = SortedGraph()
for t in canon:
    cg.add(tuple(rename.get(x, x) for x in t))
for prefix, ns in g.namespaces():
    cg.bind(prefix, ns, override=True)
cg.bind('', NS)
cg.bind('dcterms', DCT)
cg.serialize(out_ttl, format='turtle')
cg.serialize(out_owl, format='xml')
print(f'v2.1 written. Triples: {len(cg)}  |  changes: {len(log)}')
for s, p, why, old in log:
    fmt = lambda x: str(x).replace(str(NS), ':').replace(str(RDFS), 'rdfs:').replace(str(OWL), 'owl:')
    print(f'  {fmt(s)} {fmt(p)}  # {why}' + (f'  (was: {old[0][:60]!r})' if old else ''))
