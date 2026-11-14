#!/usr/bin/env python3
"""audit.py - report-artifact audit of an OWL serialization (Algorithm 1 of the paper).

    python3 audit.py <ontology file> [--claims claims.json] [--json out.json] [--own-ns <namespace>]

The audit needs no reasoner. It produces:

 I  a construct-presence inventory of the file and the DL expressivity derived from it;
 U  claim verdicts, when a claims file is given: REALIZED / UNREALIZED / MISMATCH;
 K  isolated-class analysis in two stages (see below);
 M  domain/range mismatches between assertions and declared signatures.

Isolated classes (stage 1 / stage 2)
------------------------------------
A named class with neither a named superclass nor a named subclass is only a
CANDIDATE: every legitimate atomic root concept has that shape. The first
submission of the paper printed stage 1 as if it were the defect detector;
that over-flags (8 candidates in OntoLearn v1.0, 1 defect). Stage 2 keeps a
candidate as a finding only if independent evidence corroborates it:

  manifest      the accompanying report states K subClassOf P and the file lacks it;
  usage         an individual typed K is used with a property whose declared
                domain (range) is a single named class P outside K's taxonomy and not
                declared disjoint with K - the data treat K's instances as P's
                (suggested repair: K subClassOf P). If the declared signature is a
                union or an intersection, or if K and P are declared disjoint, the
                finding is a domain/range defect and is reported under M only;
  unreferenced  K occurs in no property domain, range or restriction: nothing in
                the schema relates it to anything. This is the criterion behind
                pitfall P04 of OOPS! ("unconnected ontology elements"),
                re-implemented here so that the audit needs no web service.

Verdicts: DISCONNECTED (manifest or usage evidence: a repair is suggested),
SUSPECT (unreferenced only: the class is either dead vocabulary or a missing
link), ROOT (no evidence of defect).

Scope and limits (stated, not hidden)
-------------------------------------
* Taxonomy closure follows rdfs:subClassOf between named classes, owl:equivalentClass
  between named classes, named members of an owl:intersectionOf in an equivalentClass
  or subClassOf (superclasses), and named members of an owl:unionOf / owl:disjointUnionOf
  definition (subclasses). Multiple inheritance is handled by the closure.
* Domains and ranges are evaluated when they are a named class, a union of named
  classes (any member suffices) or an intersection of named classes (all members
  required). Other class expressions are counted as "not evaluated". A mismatch is a
  CONFLICT when a declared disjointness with an asserted type of the individual excludes
  every member of a union, or at least one missing member of an intersection.
* A position held by a literal, or by a resource that has no asserted type, is not
  examined: there is no type evidence to compare with the signature.
* Domains and ranges are inherited along rdfs:subPropertyOf and exchanged along
  owl:inverseOf.
* owl:imports are NOT followed; they are listed, and a class whose only named
  superclass lives in a foreign namespace is treated as connected. With --own-ns,
  only classes of the audited ontology's own namespace are isolated-class candidates
  (re-declared foreign terms such as foaf:Agent are skipped).
* A class that carries a definition or constraint through an anonymous class
  expression (owl:equivalentClass or rdfs:subClassOf a restriction, enumeration,
  union, intersection or complement) is connected by that axiom and is not a candidate.
* The audit decides PRESENCE of constructs and structural conflicts. It cannot
  decide whether a present axiom is adequate for the domain.
"""
import argparse, hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path
import rdflib
from rdflib import OWL, RDF, RDFS, XSD, URIRef, BNode, Literal
from rdflib.collection import Collection

CONSTRUCT_PREDICATES = {
    'rdfs:subClassOf': RDFS.subClassOf, 'rdfs:subPropertyOf': RDFS.subPropertyOf,
    'owl:equivalentClass': OWL.equivalentClass, 'owl:equivalentProperty': OWL.equivalentProperty,
    'owl:someValuesFrom': OWL.someValuesFrom, 'owl:allValuesFrom': OWL.allValuesFrom,
    'owl:hasValue': OWL.hasValue, 'owl:hasSelf': OWL.hasSelf,
    'owl:disjointWith': OWL.disjointWith, 'owl:propertyDisjointWith': OWL.propertyDisjointWith,
    'owl:disjointUnionOf': OWL.disjointUnionOf, 'owl:inverseOf': OWL.inverseOf,
    'owl:unionOf': OWL.unionOf, 'owl:intersectionOf': OWL.intersectionOf,
    'owl:complementOf': OWL.complementOf, 'owl:oneOf': OWL.oneOf,
    'owl:propertyChainAxiom': OWL.propertyChainAxiom, 'owl:hasKey': OWL.hasKey,
    'owl:sameAs': OWL.sameAs, 'owl:differentFrom': OWL.differentFrom, 'owl:imports': OWL.imports,
}
CONSTRUCT_TYPES = {
    'owl:AllDisjointClasses': OWL.AllDisjointClasses, 'owl:AllDifferent': OWL.AllDifferent,
    'owl:TransitiveProperty': OWL.TransitiveProperty, 'owl:FunctionalProperty': OWL.FunctionalProperty,
    'owl:InverseFunctionalProperty': OWL.InverseFunctionalProperty,
    'owl:SymmetricProperty': OWL.SymmetricProperty, 'owl:AsymmetricProperty': OWL.AsymmetricProperty,
    'owl:ReflexiveProperty': OWL.ReflexiveProperty, 'owl:IrreflexiveProperty': OWL.IrreflexiveProperty,
}
BUILTIN_NS = (str(OWL), str(RDFS), str(RDF), str(XSD))
UNQUALIFIED_CARD = [OWL.cardinality, OWL.minCardinality, OWL.maxCardinality]
QUALIFIED_CARD = [OWL.qualifiedCardinality, OWL.minQualifiedCardinality, OWL.maxQualifiedCardinality]


def parse(path):
    g = rdflib.Graph()
    p = Path(path)
    fmt = {'.ttl': 'turtle', '.nt': 'nt', '.n3': 'n3', '.jsonld': 'json-ld'}.get(p.suffix.lower(), 'xml')
    with open(p, 'rb') as fh:
        g.parse(fh, format=fmt)
    return g


class Audit:
    def __init__(self, g, own_ns=None):
        self.g = g
        self.own_ns = own_ns          # if given, only classes in this namespace are isolated-class candidates
        self.classes = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)} | \
                       {c for c in g.subjects(RDF.type, RDFS.Class) if isinstance(c, URIRef)}
        self.obj_props = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(p, URIRef)}
        self.data_props = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(p, URIRef)}
        self.individuals = {i for i in g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(i, URIRef)}
        # individuals typed with a known class but not declared owl:NamedIndividual
        for s, o in g.subject_objects(RDF.type):
            if isinstance(s, URIRef) and o in self.classes and s not in self.classes:
                self.individuals.add(s)
        self._taxonomy()
        self._properties()

    # ------------------------------------------------------------ helpers
    def _list(self, node):
        try:
            return list(Collection(self.g, node))
        except Exception:
            return []

    def _named_members(self, expr, pred):
        out = []
        for lst in self.g.objects(expr, pred):
            out += [m for m in self._list(lst) if isinstance(m, URIRef)]
        return out

    def _taxonomy(self):
        g = self.g
        sup = defaultdict(set)   # direct named superclasses
        for c, d in g.subject_objects(RDFS.subClassOf):
            if isinstance(c, URIRef) and isinstance(d, URIRef) and d != OWL.Thing:
                sup[c].add(d)
            elif isinstance(c, URIRef) and isinstance(d, BNode):
                for m in self._named_members(d, OWL.intersectionOf):
                    sup[c].add(m)
        for c, d in g.subject_objects(OWL.equivalentClass):
            if isinstance(c, URIRef) and isinstance(d, URIRef):
                sup[c].add(d); sup[d].add(c)
            elif isinstance(c, URIRef) and isinstance(d, BNode):
                for m in self._named_members(d, OWL.intersectionOf):
                    sup[c].add(m)
                for m in self._named_members(d, OWL.unionOf):
                    sup[m].add(c)
        for c, lst in g.subject_objects(OWL.disjointUnionOf):
            for m in self._list(lst):
                if isinstance(m, URIRef):
                    sup[m].add(c)
        # classes carrying a logical definition or constraint through an anonymous class expression
        # (restriction, enumeration, complement, union/intersection): they are connected by that axiom
        self.defined = set()
        for pred in (RDFS.subClassOf, OWL.equivalentClass):
            for c, d in g.subject_objects(pred):
                if isinstance(c, URIRef) and isinstance(d, BNode):
                    self.defined.add(c)
                if isinstance(d, URIRef) and isinstance(c, BNode):
                    self.defined.add(d)
        for c in g.subjects(OWL.disjointUnionOf, None):
            if isinstance(c, URIRef):
                self.defined.add(c)
        self.sup = sup
        self.sub = defaultdict(set)
        for c, ds in sup.items():
            for d in ds:
                self.sub[d].add(c)

    def ancestors(self, c):
        seen, todo = set(), [c]
        while todo:
            x = todo.pop()
            for d in self.sup.get(x, ()):
                if d not in seen:
                    seen.add(d); todo.append(d)
        return seen

    def closure(self, types):
        out = set(types)
        for t in types:
            out |= self.ancestors(t)
        return out

    def _properties(self):
        g = self.g
        self.superprops = defaultdict(set)
        for p, q in g.subject_objects(RDFS.subPropertyOf):
            if isinstance(p, URIRef) and isinstance(q, URIRef):
                self.superprops[p].add(q)
        self.inverse = defaultdict(set)
        for p, q in g.subject_objects(OWL.inverseOf):
            if isinstance(p, URIRef) and isinstance(q, URIRef):
                self.inverse[p].add(q); self.inverse[q].add(p)

    def _signature(self, expr):
        """('any'|'all', [named classes]) or None if the expression is not evaluated."""
        if isinstance(expr, URIRef):
            return ('any', [expr])
        u = self._named_members(expr, OWL.unionOf)
        if u and len(u) == sum(len(self._list(l)) for l in self.g.objects(expr, OWL.unionOf)):
            return ('any', u)
        i = self._named_members(expr, OWL.intersectionOf)
        if i and len(i) == sum(len(self._list(l)) for l in self.g.objects(expr, OWL.intersectionOf)):
            return ('all', i)
        return None

    def _allprops(self, p):
        seen, todo = {p}, [p]
        while todo:
            x = todo.pop()
            for q in self.superprops.get(x, ()):
                if q not in seen:
                    seen.add(q); todo.append(q)
        return seen

    def signatures(self, p, side):
        """Declared class expressions constraining the subject (side='domain') or
        object (side='range') of p, inherited from super-properties and inverses."""
        res, skipped = [], 0
        for q in self._allprops(p):
            for pred, prop in ((RDFS.domain if side == 'domain' else RDFS.range, q),):
                for e in self.g.objects(prop, pred):
                    s = self._signature(e)
                    if s: res.append((q, s))
                    else: skipped += 1
            for inv in self.inverse.get(q, ()):
                for e in self.g.objects(inv, RDFS.range if side == 'domain' else RDFS.domain):
                    s = self._signature(e)
                    if s: res.append((inv, s))
                    else: skipped += 1
        return res, skipped

    def types(self, a):
        """Asserted class types of a resource. Types from the OWL, RDFS, RDF and XSD vocabularies
        (owl:NamedIndividual, owl:Thing, owl:Class, ...) say nothing about the domain and are left out."""
        return {t for t in self.g.objects(a, RDF.type) if isinstance(t, URIRef) and not str(t).startswith(BUILTIN_NS)}

    # ---------------------------------------------------------- inventory
    def inventory(self):
        g = self.g
        inv = {}
        for name, pred in CONSTRUCT_PREDICATES.items():
            inv[name] = len(list(g.triples((None, pred, None))))
        for name, t in CONSTRUCT_TYPES.items():
            inv[name] = len(list(g.subjects(RDF.type, t)))
        inv['unqualified cardinality'] = sum(len(list(g.triples((None, p, None)))) for p in UNQUALIFIED_CARD)
        inv['qualified cardinality'] = sum(len(list(g.triples((None, p, None)))) for p in QUALIFIED_CARD)
        inv['datatype ranges'] = sum(1 for p in self.data_props for r in g.objects(p, RDFS.range) if isinstance(r, URIRef))
        inv['classes'] = len(self.classes)
        inv['object properties'] = len(self.obj_props)
        inv['data properties'] = len(self.data_props)
        inv['individuals'] = len({i for i in self.g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(i, URIRef)})
        inv['individuals incl. undeclared'] = len(self.individuals)
        inv['triples'] = len(g)
        return inv

    def expressivity(self, inv):
        """DL name derived from the inventory by the standard naming rules.
        AL is the base; C if complement, union or existential/disjointness is used
        (ALC); S abbreviates ALC with transitive roles; H role hierarchy; O nominals;
        I inverse roles; F functional roles, N unqualified and Q qualified number
        restrictions (Q subsumes N subsumes F); (D) datatypes."""
        g = self.g
        rules = []
        complex_concepts = any(inv[k] for k in ('owl:unionOf', 'owl:complementOf', 'owl:someValuesFrom',
                                                'owl:disjointWith', 'owl:AllDisjointClasses', 'owl:disjointUnionOf'))
        trans = inv['owl:TransitiveProperty'] > 0
        base = 'S' if trans else ('ALC' if complex_concepts else 'AL')
        rules.append(f'base {base}: transitive roles={inv["owl:TransitiveProperty"]}, full concept negation/union/existential used={complex_concepts}')
        name = base
        complex_roles = any(inv[k] for k in ('owl:propertyChainAxiom', 'owl:propertyDisjointWith', 'owl:hasSelf',
                                             'owl:AsymmetricProperty', 'owl:ReflexiveProperty', 'owl:IrreflexiveProperty'))
        if complex_roles:
            name += 'R'; rules.append('R: complex role inclusions, role disjointness, self-restriction or (ir)reflexive/asymmetric roles')
        elif inv['rdfs:subPropertyOf'] or inv['owl:equivalentProperty']:
            name += 'H'; rules.append(f'H: {inv["rdfs:subPropertyOf"]} sub-property axioms')
        if inv['owl:oneOf'] or inv['owl:hasValue']:
            name += 'O'; rules.append('O: nominals')
        if inv['owl:inverseOf'] or inv['owl:InverseFunctionalProperty'] or inv['owl:SymmetricProperty']:
            name += 'I'; rules.append(f'I: {inv["owl:inverseOf"]} inverse-property axioms')
        func_obj = [p for p in g.subjects(RDF.type, OWL.FunctionalProperty) if p in self.obj_props]
        if inv['qualified cardinality']:
            name += 'Q'; rules.append('Q: qualified number restrictions')
        elif inv['unqualified cardinality']:
            name += 'N'; rules.append('N: unqualified number restrictions')
        elif func_obj or inv['owl:InverseFunctionalProperty']:
            name += 'F'; rules.append(f'F: {len(func_obj)} functional object properties, no number restrictions')
        if self.data_props:
            name += '(D)'; rules.append(f'(D): {len(self.data_props)} data properties')
        return name, rules

    # -------------------------------------------------- isolated classes
    def disjoint_pairs(self):
        pairs = set()
        for a, b in self.g.subject_objects(OWL.disjointWith):
            pairs.add(frozenset((a, b)))
        for node in self.g.subjects(RDF.type, OWL.AllDisjointClasses):
            for lst in self.g.objects(node, OWL.members):
                m = self._list(lst)
                for i in range(len(m)):
                    for j in range(i + 1, len(m)):
                        pairs.add(frozenset((m[i], m[j])))
        for c, lst in self.g.subject_objects(OWL.disjointUnionOf):
            m = self._list(lst)
            for i in range(len(m)):
                for j in range(i + 1, len(m)):
                    pairs.add(frozenset((m[i], m[j])))
        return pairs

    def are_disjoint(self, a, b, pairs=None):
        """Structural test: some ancestor-or-self of a is declared disjoint with one of b."""
        pairs = self.disjoint_pairs() if pairs is None else pairs
        A, B = self.closure({a}), self.closure({b})
        return any(frozenset((x, y)) in pairs for x in A for y in B if x != y)

    def referenced_classes(self):
        """Classes that some property relates to the rest of the schema: they occur in a
        domain, a range, or as the filler of a restriction (directly or inside a union
        or intersection used there)."""
        g, ref = self.g, set()

        def collect(expr):
            if isinstance(expr, URIRef):
                ref.add(expr)
            else:
                for pred in (OWL.unionOf, OWL.intersectionOf):
                    for lst in g.objects(expr, pred):
                        for m in self._list(lst):
                            collect(m)
                for o in g.objects(expr, OWL.complementOf):
                    collect(o)
        for pred in (RDFS.domain, RDFS.range, OWL.someValuesFrom, OWL.allValuesFrom, OWL.onClass):
            for o in g.objects(None, pred):
                collect(o)
        for cls, r in g.subject_objects(RDFS.subClassOf):       # a class carrying a restriction is related by it
            if isinstance(cls, URIRef) and isinstance(r, BNode) and (r, OWL.onProperty, None) in g:
                ref.add(cls)
        return ref

    def isolated(self, manifest_edges=()):
        cand = sorted(c for c in self.classes if not self.sup.get(c) and not self.sub.get(c)
                      and c not in self.defined
                      and (self.own_ns is None or str(c).startswith(self.own_ns)))
        mismatches = self.mismatches()
        ref = self.referenced_classes()
        want = {}
        for child, parent in manifest_edges:
            want[child] = parent
        rows = []
        for k in cand:
            ev = []
            if k in want and want[k] not in self.ancestors(k):
                ev.append({'evidence': 'manifest', 'suggest': want[k]})
            # usage evidence: K's instances are used where exactly ONE named class P is expected and
            # nothing declares K and P disjoint. When the signature is a union or an intersection, or
            # when the use contradicts a declared disjointness (CONFLICT), the finding is a domain/range
            # defect (reported under M), not evidence about K's place in the taxonomy.
            sugg = defaultdict(set)
            for m in mismatches:
                if k in m['types_set'] and m['single'] and not m['conflict']:
                    sugg[next(iter(m['expected_set']))].add(m['individual'])
            for c, inds in sorted(sugg.items(), key=lambda kv: -len(kv[1])):
                ev.append({'evidence': 'usage', 'suggest': c, 'individuals': sorted(inds)})
            if k not in ref:
                ev.append({'evidence': 'unreferenced'})
            verdict = 'ROOT'
            if any(e['evidence'] in ('manifest', 'usage') for e in ev):
                verdict = 'DISCONNECTED'
            elif ev:
                verdict = 'SUSPECT'
            rows.append({'class': k, 'verdict': verdict, 'evidence': ev})
        return rows

    # ------------------------------------------------ domain/range check
    def mismatches(self):
        if hasattr(self, '_mm'):
            return self._mm
        g, out, self.not_evaluated = self.g, [], 0
        pairs = self.disjoint_pairs()
        props = self.obj_props | self.data_props
        # every subject of a property assertion; a position is examined only if the resource
        # that holds it has an asserted type (no type, no evidence)
        subjects = set(self.individuals) | {s for s, p in g.subject_predicates() if p in props and isinstance(s, URIRef)}
        for a in sorted(subjects):
            ta = self.types(a)
            ca = self.closure(ta)
            for p, b in sorted(g.predicate_objects(a)):
                if p not in props:
                    continue
                checks = [('domain', a, ta, ca)] if ta else []
                if p in self.obj_props and isinstance(b, URIRef) and self.types(b):
                    tb = self.types(b)
                    checks.append(('range', b, tb, self.closure(tb)))
                for side, ind, t, c in checks:
                    sigs, skipped = self.signatures(p, side)
                    self.not_evaluated += skipped
                    for q, (mode, members) in sigs:
                        hit = [m for m in members if m in c]
                        okay = bool(hit) if mode == 'any' else len(hit) == len(members)
                        if okay:
                            continue
                        expected = set(members) if mode == 'any' else set(members) - set(hit)
                        # conflict: the entailed membership contradicts a declared disjointness.
                        # A union is contradicted only if EVERY alternative is excluded by a type of the
                        # individual; an intersection, as soon as ONE required member is excluded.
                        excluded = [any(self.are_disjoint(x, m, pairs) for x in t) for m in sorted(expected)]
                        conflict = all(excluded) if mode == 'any' else any(excluded)
                        out.append({'individual': ind, 'property': p, 'side': side, 'declared_on': q,
                                    'types': sorted(t), 'expected': sorted(expected),
                                    'types_set': set(t), 'expected_set': expected,
                                    'single': mode == 'any' and len(members) == 1,   # the signature is one named class
                                    'conflict': conflict})
        # de-duplicate (the same finding can be reached through a property and its inverse)
        seen, uniq = set(), []
        for m in out:
            key = (m['individual'], tuple(m['expected']))
            if key not in seen:
                seen.add(key); uniq.append(m)
        self._mm = uniq
        return uniq

    # ----------------------------------------------------------- claims
    def check_claims(self, claims, inv, dl, ns):
        res = []
        pairs = self.disjoint_pairs()
        N = lambda n: URIRef(ns + n)
        for c in claims:
            k = c['check']
            if k == 'expressivity':
                ok = dl == c['value']; got = dl
            elif k == 'construct':
                got = inv[c['construct']]; ok = got >= c['min']
            elif k == 'count':
                got = inv[c['metric']]; ok = got == c['value']
            elif k == 'absent':
                got = inv[c['construct']]; ok = got == 0
            elif k == 'disjoint':
                have = [p for p in c['pairs'] if self.are_disjoint(N(p[0]), N(p[1]), pairs)]
                got = f'{len(have)} of {len(c["pairs"])} pairs'; ok = len(have) == len(c['pairs'])
            elif k == 'term':
                pool = self.data_props if c['kind'] == 'data property' else self.obj_props
                hits = sorted(str(p).split('#')[-1] for p in pool if re.search(c['pattern'], str(p).split('#')[-1]))
                got = hits or 'no matching term'; ok = bool(hits)
            elif k == 'taxonomy':
                have = [e for e in c['edges'] if N(e[1]) in self.ancestors(N(e[0]))]
                got = f'{len(have)} of {len(c["edges"])} edges'; ok = len(have) == len(c['edges'])
            elif k == 'characteristic':
                p = N(c['property'])
                t_ok = all((p, RDF.type, URIRef(str(OWL) + t.split(':')[1])) in self.g for t in c['types'])
                i_ok = N(c['inverse']) in self.inverse.get(p, ())
                got = f'characteristics={t_ok}, inverse={i_ok}'; ok = t_ok and i_ok
            else:
                raise ValueError(k)
            verdict = 'REALIZED' if ok else ('MISMATCH' if k in ('count', 'expressivity') else 'UNREALIZED')
            res.append({'id': c['id'], 'where': c['where'], 'claim': c['text'], 'measured': got, 'verdict': verdict})
        return res


def run(path, claims_path=None, ns='http://www.ontolearn.com/ontologia#', own_ns=None):
    g = parse(path)
    A = Audit(g, own_ns)
    inv = A.inventory()
    dl, rules = A.expressivity(inv)
    claims, edges = [], []
    if claims_path:
        doc = json.loads(Path(claims_path).read_text(encoding='utf-8'))
        claims = A.check_claims(doc['claims'], inv, dl, ns)
        for c in doc['claims']:
            if c['check'] == 'taxonomy':
                edges += [(URIRef(ns + a), URIRef(ns + b)) for a, b in c['edges']]
    iso = A.isolated(edges)
    mm = A.mismatches()
    short = lambda x: str(x).split('#')[-1] if '#' in str(x) else str(x).rsplit('/', 1)[-1]
    for r in iso:
        r['class'] = short(r['class'])
        for e in r['evidence']:
            if 'suggest' in e: e['suggest'] = short(e['suggest'])
            if 'individuals' in e: e['individuals'] = [short(i) for i in e['individuals']]
    mm_out = [{'individual': short(m['individual']), 'property': short(m['property']), 'side': m['side'],
               'declared_on': short(m['declared_on']), 'types': [short(t) for t in m['types']],
               'expected': [short(t) for t in m['expected']], 'conflict': m['conflict']} for m in mm]
    return {'file': str(path), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'triples': len(g), 'inventory': inv, 'expressivity': dl,
            'expressivity_rules': rules, 'imports': [str(o) for o in g.objects(None, OWL.imports)],
            'claims': claims, 'isolated': iso, 'mismatches': mm_out,
            'signatures_not_evaluated': A.not_evaluated}


def render(r):
    L = [f'AUDIT  {r["file"]}  ({r["triples"]} triples)', f'       sha256 {r["sha256"]}', '']
    L.append('I. Construct inventory')
    for k, v in r['inventory'].items():
        L.append(f'   {k:32s} {v}')
    L.append(f'   derived DL expressivity          {r["expressivity"]}')
    for rule in r['expressivity_rules']:
        L.append(f'      - {rule}')
    if r['imports']:
        L.append(f'   owl:imports NOT followed: {r["imports"]}')
    if r['claims']:
        L += ['', 'U. Claims of the accompanying report']
        for c in r['claims']:
            L.append(f'   {c["id"]} {c["verdict"]:10s} {c["claim"]}  [{c["where"]}]  measured: {c["measured"]}')
    L += ['', f'K. Isolated classes: {len(r["isolated"])} stage-1 candidates']
    for k in r['isolated']:
        ev = '; '.join(e['evidence'] + (f' -> subClassOf {e["suggest"]}' if 'suggest' in e else '') +
                       (f' (via {", ".join(e["individuals"])})' if 'individuals' in e else '') for e in k['evidence'])
        L.append(f'   {k["verdict"]:13s} {k["class"]:28s} {ev}')
    L += ['', f'M. Domain/range mismatches: {len(r["mismatches"])}  (signatures not evaluated: {r["signatures_not_evaluated"]})']
    for m in r['mismatches']:
        L.append(f'   {"CONFLICT" if m["conflict"] else "mismatch"}  {m["individual"]} (types {m["types"]}) used with '
                 f'{m["property"]}: declared {m["side"]} on {m["declared_on"]} expects one of {m["expected"]}')
    return '\n'.join(L) + '\n'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file'); ap.add_argument('--claims'); ap.add_argument('--json')
    ap.add_argument('--ns', default='http://www.ontolearn.com/ontologia#', help='namespace used to resolve the local names in the claims file')
    ap.add_argument('--own-ns', default=None, help="restrict isolated-class candidates to this namespace")
    a = ap.parse_args()
    r = run(a.file, a.claims, a.ns, a.own_ns)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, ensure_ascii=False, default=str))
    sys.stdout.write(render(r))
