#!/usr/bin/env python3
"""ablation.py — per-family axiom ablation over OntoCBLA.
For each configuration: (a) HermiT consistency + unsatisfiable classes,
(b) OWL-RL materialization size (entailed triples beyond asserted).
Families: F1 repair(Subjetiva), F2 disjoint(KSA+Obj/Subj), F2b AllDisjoint13,
F3 existentials, F4 role hierarchy, F5 functional, plus v1.0 native families
ablated: T transitivity, I inverses.
"""
import sys, io, contextlib, copy, time
import rdflib, owlrl, owlready2
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

def hermit(g, tag):
    import tempfile, os
    tmp=os.path.join(tempfile.gettempdir(), f'abl_{tag}.owl')
    g.serialize(tmp, format='xml')
    world=owlready2.World()
    onto=world.get_ontology('file://'+tmp).load()
    buf=io.StringIO()
    try:
        t0=time.time()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            owlready2.sync_reasoner(world, debug=0)
        dt=time.time()-t0
        nothing=world['http://www.w3.org/2002/07/owl#Nothing']
        unsat=[c.name for c in world.classes() if nothing in c.is_a] if nothing else []
        return ('consistent', unsat, dt)
    except owlready2.base.OwlReadyInconsistentOntologyError:
        return ('INCONSISTENT', [], time.time()-t0)

def rl_materialize(g):
    h=copy.deepcopy(g); n0=len(h)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(h)
    # count only entailed triples in the ontology namespace (drop pure RDFS/OWL vocabulary noise)
    ent=[(s,p,o) for s,p,o in h if (s,p,o) not in g]
    dom=[t for t in ent if any(isinstance(x,URIRef) and str(x).startswith(str(NS)) for x in t)]
    return n0, len(ent), len(dom)

FAM={'F0':F0,'F1':F1,'F2':F2,'F2b':F2b,'F3':F3,'F4':F4,'F5':F5}
ALL=['F0','F1','F2','F2b','F3','F4','F5']

def build(cfg, drop_trans=False, drop_inv=False):
    g=base()
    if drop_trans: strip_transitivity(g)
    if drop_inv: strip_inverses(g)
    for f in cfg: FAM[f](g)
    return g

if __name__=='__main__':
    rows=[]
    # incremental: find the family that breaks consistency
    print('== Incremental HermiT (cumulative) ==')
    for i in range(len(ALL)+1):
        cfg=ALL[:i]; g=build(cfg)
        st,unsat,dt=hermit(g,'inc'+str(i))
        print(f"  base+{'+'.join(cfg) or '∅'}: {st}  unsat={unsat}  ({dt:.1f}s)")
    print('== Leave-one-out HermiT (v2.0 minus one family) ==')
    for f in ALL:
        cfg=[x for x in ALL if x!=f]; g=build(cfg)
        st,unsat,dt=hermit(g,'loo_'+f)
        print(f"  v2 − {f}: {st}  unsat={unsat}")
    print('== OWL-RL materialization ==')
    for tag,kw,cfg in [('v1.0',{},[]),('v1.0−T',{'drop_trans':True},[]),('v1.0−I',{'drop_inv':True},[]),
                       ('v2.0',{},ALL),('v2.0−F4',{},[x for x in ALL if x!='F4']),
                       ('v2.0−T',{'drop_trans':True},ALL),('v2.0−I',{'drop_inv':True},ALL)]:
        g=build(cfg,**kw); n0,ent,dom=rl_materialize(g)
        print(f"  {tag:10s} asserted={n0:4d}  entailed(+)={ent:5d}  domain-relevant={dom:5d}")
