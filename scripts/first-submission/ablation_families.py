#!/usr/bin/env python3
"""ablation_families.py - the family definitions of first-submission/ablation.py
(its lines 14-60 and 88-96, verbatim), without the reasoner code, kept so that
check_release_equivalence.py (E7) can reproduce the defect documented in the
README erratum: this reconstruction of "v2.0" is not the released v2.0."""
import sys
import rdflib
from rdflib import OWL, RDF, RDFS, URIRef, BNode, Literal
from rdflib.collection import Collection
NS = rdflib.Namespace('http://www.ontolearn.com/ontologia#')
SRC = sys.argv[1] if len(sys.argv) > 1 else 'ontolearn_v10'

def base():
    g = rdflib.Graph()
    with open(SRC, 'rb') as _fh:      # file handle: immune to spaces in paths
        g.parse(_fh, format='xml')
    g.bind('', NS)
    return g

def F0(g):
    from rdflib.collection import Collection as _C
    for _,_,dn in g.triples((NS.descricao, RDFS.domain, None)):
        for _,_,lst in g.triples((dn, OWL.unionOf, None)):
            _C(g, lst).append(NS.NiveisDeProficiencia)
def F1(g): g.add((NS.Subjetiva, RDFS.subClassOf, NS.Questao))
def F2(g):
    for a,b in [(NS.Conhecimento,NS.Habilidade),(NS.Conhecimento,NS.Atitude),
                (NS.Habilidade,NS.Atitude),(NS.Objetiva,NS.Subjetiva)]:
        g.add((a,OWL.disjointWith,b))
def F2b(g):
    roots=[NS.UsuarioDoAva,NS.Competencia,NS.RecursoDeAprendizagem,NS.DesempenhoDoAprendiz,
           NS.Questao,NS.Avaliacao,NS.Curso,NS.NiveisDeProficiencia,NS.MilestoneDeAprendizagem,
           NS.TrajetoriasDeAprendizagem,NS.Conhecimento,NS.Habilidade,NS.Atitude]
    b=BNode(); lst=BNode()
    g.add((b,RDF.type,OWL.AllDisjointClasses)); Collection(g,lst,roots); g.add((b,OWL.members,lst))
def F3(g):
    for cls,prop,fil in [(NS.Questao,NS.competenciasAvaliadas,NS.Competencia),
                         (NS.Avaliacao,NS.questoesIncluidas,NS.Questao),
                         (NS.RecursoDeAprendizagem,NS.abordaCompetencia,NS.Competencia),
                         (NS.DesempenhoDoAprendiz,NS.proficienciaAtingida,NS.NiveisDeProficiencia)]:
        r=BNode(); g.add((r,RDF.type,OWL.Restriction)); g.add((r,OWL.onProperty,prop))
        g.add((r,OWL.someValuesFrom,fil)); g.add((cls,RDFS.subClassOf,r))
def F4(g):
    for sup,subs in [(NS.temComponenteKSA,[NS.ehCompostoDeConhecimento,NS.ehCompostoDeHabilidade,NS.ehCompostoDeAtitude]),
                     (NS.ehComponenteKSADe,[NS.compoeConhecimentoEm,NS.compoeHabilidadeEm,NS.compoeAtitudeEm])]:
        g.add((sup,RDF.type,OWL.ObjectProperty))
        for sb in subs: g.add((sb,RDFS.subPropertyOf,sup))
    g.add((NS.temComponenteKSA,OWL.inverseOf,NS.ehComponenteKSADe))
def F5(g): g.add((NS.proficienciaAtingida,RDF.type,OWL.FunctionalProperty))

def strip_transitivity(g):
    for s in list(g.subjects(RDF.type, OWL.TransitiveProperty)):
        g.remove((s, RDF.type, OWL.TransitiveProperty))
def strip_inverses(g):
    for s,p,o in list(g.triples((None, OWL.inverseOf, None))):
        g.remove((s,p,o))
FAM={'F0':F0,'F1':F1,'F2':F2,'F2b':F2b,'F3':F3,'F4':F4,'F5':F5}
ALL=['F0','F1','F2','F2b','F3','F4','F5']

def build(cfg, drop_trans=False, drop_inv=False):
    g=base()
    if drop_trans: strip_transitivity(g)
    if drop_inv: strip_inverses(g)
    for f in cfg: FAM[f](g)
    return g
