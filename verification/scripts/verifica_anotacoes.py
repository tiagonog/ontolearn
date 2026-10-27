"""Verificações locais inspiradas em armadilhas do catálogo OOPS!.

Não substitui o OOPS! (diagnóstico em scripts/oops/): reproduz apenas as
condições de algumas armadilhas, como conferência complementar, e confere a
declaração de licença, que o verificador P41 do OOPS! obtém de um serviço externo.
  P08 - elemento sem rdfs:label ou sem rdfs:comment
  P11 - propriedade sem rdfs:domain ou sem rdfs:range
  P13 - propriedade de objeto sem inversa declarada
  P04 - classe sem superclasse nomeada, sem subclasses e fora de domínio/imagem
  P41 - ausência de licença (dcterms:license ou cc:license) no cabeçalho
Uso: python verifica_anotacoes.py saida.json ontologia.owl [outra.owl ...]
"""
import sys
from rdflib import Graph, RDF, RDFS, OWL, URIRef, BNode
from rdflib.namespace import DCTERMS

NS = "http://www.ontolearn.com/ontologia#"

def local(u):
    return str(u).split("#")[-1]

def analisa(caminho):
    g = Graph()
    g.parse(caminho)
    classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef) and str(c).startswith(NS)}
    ops = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if str(p).startswith(NS)}
    dps = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if str(p).startswith(NS)}
    elementos = classes | ops | dps
    sem_label = sorted(local(e) for e in elementos if (e, RDFS.label, None) not in g)
    sem_coment = sorted(local(e) for e in elementos if (e, RDFS.comment, None) not in g)
    sem_dom = sorted(local(p) for p in ops | dps if (p, RDFS.domain, None) not in g)
    sem_img = sorted(local(p) for p in ops | dps if (p, RDFS.range, None) not in g)
    inversas = set()
    for a, b in g.subject_objects(OWL.inverseOf):
        inversas.add(a); inversas.add(b)
    sem_inv = sorted(local(p) for p in ops if p not in inversas)
    # P04 aproximado
    usadas = set()
    for p in (RDFS.domain, RDFS.range):
        for o in g.objects(None, p):
            usadas.add(o)
            # uniões
            for lst in g.objects(o, OWL.unionOf):
                for item in g.items(lst):
                    usadas.add(item)
    isoladas = []
    for c in classes:
        sup = [s for s in g.objects(c, RDFS.subClassOf) if isinstance(s, URIRef)]
        sub = list(g.subjects(RDFS.subClassOf, c))
        if not sup and not sub and c not in usadas:
            isoladas.append(local(c))
    onto = next(g.subjects(RDF.type, OWL.Ontology), None)
    licenca = [str(o) for o in g.objects(onto, DCTERMS.license)] + \
              [str(o) for o in g.objects(onto, URIRef("http://creativecommons.org/ns#license"))]
    return {
        "elementos": len(elementos),
        "P08 sem rdfs:label": sem_label,
        "P08 sem rdfs:comment": sem_coment,
        "P11 sem domínio": sem_dom,
        "P11 sem imagem": sem_img,
        "P13 sem inversa": sem_inv,
        "P04 classes isoladas (aprox.)": sorted(isoladas),
        "P41 licença": licenca,
    }

if __name__ == "__main__":
    import json, os
    saida = sys.argv[1]
    todos = {}
    for caminho in sys.argv[2:]:
        r = analisa(caminho)
        todos[os.path.basename(caminho)] = r
        n = r["elementos"]
        print(f"### {caminho} ({n} classes e propriedades)")
        for k, v in r.items():
            if k != "elementos":
                print(f"- {k}: {len(v)} -> {v}")
        print()
    with open(saida, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
