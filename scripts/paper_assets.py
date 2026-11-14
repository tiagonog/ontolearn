#!/usr/bin/env python3
"""paper_assets.py - every table and every number of the audit paper, generated from results/.

Writes LaTeX fragments to paper/gen/. The manuscript \\input{}s the tables and uses the macros of
paper/gen/numbers.tex for the numbers quoted in running text, so that no measured value in the
paper is typed by hand. Run after scripts/run_all.sh (and after results of a second platform, if
any, have been copied to results/).
"""
import csv, collections, json, statistics as st
from pathlib import Path
import audit
from common import *

GEN = ROOT / 'paper' / 'gen'
GEN.mkdir(parents=True, exist_ok=True)
VERS = ['v1.0', 'v2.0', 'v2.1', 'v2.2']
NUM = collections.OrderedDict()


def num(name, value):
    assert name.isalpha(), name
    NUM[name] = value


def num_get(name):
    return NUM[name]


def tt(s):
    return '\\texttt{' + s.replace('_', '\\_') + '}'


def tth(s):
    """\\texttt that may be broken before an inner capital, for narrow table columns.
    The break carries no hyphen: a hyphen would read as part of the identifier."""
    import re
    return '\\texttt{' + re.sub(r'(?<=[a-z])(?=[A-Z])', r'\\allowbreak{}', s).replace('_', '\\_') + '}'


def write(name, text):
    (GEN / name).write_text(text)


def J(name):
    return json.loads((RESULTS / name).read_text())


def thousands(n):
    return f'{n:,}'.replace(',', '{,}')


# ------------------------------------------------------------------ releases
def releases():
    rows = harness('metrics', *[locked(v) for v in VERS])[1:]
    met = {v: r.split('\t') for v, r in zip(VERS, rows)}
    inv, dl = {}, {}
    for v in VERS:
        r = audit.run(locked(v))
        inv[v], dl[v] = r['inventory'], r['expressivity']
    prof = J('E0_profiles.json')
    assert all(prof[v]['OWL2DL']['in_profile'] for v in VERS)
    for v, tag in (('v1.0', 'One'), ('v2.0', 'TwoZero'), ('v2.1', 'TwoOne'), ('v2.2', 'TwoTwo')):
        k = prof[v]['OWL2RL']['by_kind']
        num('RlOutside' + tag, prof[v]['OWL2RL']['violations'])
        num('RlOutsideUnion' + tag, k.get('union domain', 0) + k.get('union range', 0))
        num('RlOutsideExist' + tag, k.get('existential restriction as superclass', 0))
        assert num_get('RlOutsideUnion' + tag) + num_get('RlOutsideExist' + tag) == prof[v]['OWL2RL']['violations']
    line = lambda label, f: label + ' & ' + ' & '.join(str(f(v)) for v in VERS) + ' \\\\'
    dlname = lambda v: '\\ensuremath{\\mathcal{' + dl[v].replace('(D)', '') + '}(\\mathcal{D})}'
    body = [
        line('RDF triples', lambda v: inv[v]['triples']),
        line('Axioms (OWL API)', lambda v: met[v][1]),
        line('Logical axioms', lambda v: met[v][2]),
        line('Classes', lambda v: inv[v]['classes']),
        line('Object properties', lambda v: inv[v]['object properties']),
        line('Data properties', lambda v: inv[v]['data properties']),
        line('Named individuals', lambda v: inv[v]['individuals']),
        '\\hline',
        line('Sub-property axioms', lambda v: inv[v]['rdfs:subPropertyOf']),
        line('Existential restrictions', lambda v: inv[v]['owl:someValuesFrom']),
        line('Universal restrictions', lambda v: inv[v]['owl:allValuesFrom']),
        line('Cardinality restrictions', lambda v: inv[v]['unqualified cardinality'] + inv[v]['qualified cardinality']),
        line('Disjointness, binary / $n$-ary', lambda v: f"{inv[v]['owl:disjointWith']} / {inv[v]['owl:AllDisjointClasses']}"),
        line('Inverse-property axioms', lambda v: inv[v]['owl:inverseOf']),
        line('Transitive properties', lambda v: inv[v]['owl:TransitiveProperty']),
        line('Functional properties', lambda v: inv[v]['owl:FunctionalProperty']),
        line('Datatype ranges', lambda v: inv[v]['datatype ranges']),
        line('DL name (derived)', dlname),
        line('In the OWL~2~DL profile', lambda v: 'yes' if prof[v]['OWL2DL']['in_profile'] else 'no'),
        line('Axioms outside OWL~2~RL', lambda v: prof[v]['OWL2RL']['violations']),
        '\\hline',
        line('SHA-256 (first 8 hex)', lambda v: '{\\scriptsize' + tt(sha256(locked(v))[:8]) + '}'),
    ]
    write('tab_releases.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{The four releases studied: entity counts and construct inventory, measured on the released RDF/XML files (inventory: \\texttt{scripts/audit.py}; axiom counts and profile conformance: OWL~API~5.1.9). The complete digests are in \\texttt{scripts/LOCK.sha256}.}',
        '\\label{tab:releases}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{2pt}',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.55cm}cccc}', '\\hline',
        '\\textbf{Measure} & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table}', '']))
    for v in VERS:
        tag = {'v1.0': 'One', 'v2.0': 'TwoZero', 'v2.1': 'TwoOne', 'v2.2': 'TwoTwo'}[v]
        num('Logical' + tag, met[v][2]); num('Axioms' + tag, met[v][1]); num('Triples' + tag, inv[v]['triples'])


# -------------------------------------------------------------------- claims
def claims():
    doc = json.loads(locked('claims/sbie2026.json').read_text(encoding='utf-8'))
    res = {}
    for v in ('v1.0', 'v2.2'):
        res[v] = {c['id']: c for c in audit.run(locked(v), locked('claims/sbie2026.json'))['claims']}
    sym = {'REALIZED': 'yes', 'UNREALIZED': '\\textbf{no}', 'MISMATCH': '\\textbf{differs}'}
    short = {
        'C01': 'Expressivity is \\ensuremath{\\mathcal{ALCHIF}(\\mathcal{D})}', 'C02': 'Role hierarchy (the $\\mathcal{H}$ of the profile)',
        'C03': 'KSA triad pairwise disjoint', 'C04': 'Existential restrictions', 'C05': 'Qualified cardinality restrictions',
        'C06': 'Score-valued data property', 'C07': 'Transitive prerequisite property with declared inverse',
        'C08': 'Functional properties', 'C09': '29 classes', 'C10': '48 object properties', 'C11': '27 data properties',
        'C12': '24 inverse-property axioms', 'C13': '2 transitive properties', 'C14': 'ABox of 40 named individuals',
        'C15': '\\texttt{Questao} specialized into \\texttt{Objetiva} and \\texttt{Subjetiva}'}

    def measured(c):
        m = c['measured']
        if isinstance(m, list):
            return ', '.join(m)
        m = str(m)
        if m.startswith('characteristics='):
            return 'present'
        if m == 'no matching term':
            return 'none'
        return m.replace('SIF(D)', '\\ensuremath{\\mathcal{SIF}(\\mathcal{D})}').replace('SHIF(D)', '\\ensuremath{\\mathcal{SHIF}(\\mathcal{D})}')
    rows = []
    for c in doc['claims']:
        i = c['id']
        rows.append(f"{i} & {short[i]} & {measured(res['v1.0'][i])} & {sym[res['v1.0'][i]['verdict']]} & {measured(res['v2.2'][i])} & {sym[res['v2.2'][i]['verdict']]} \\\\")
    write('tab_claims.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{The 15 structural claims of the original report \\cite{nogueira_sbie} that can be decided on a single file, checked against the released v1.0 and v2.2 (\\texttt{claims/sbie2026.json} locates each claim in the report). The column \\emph{Realized} is \\emph{yes} when the file satisfies the claim, \\emph{no} when the construct or link is absent, and \\emph{differs} when a stated value does not match.}',
        '\\label{tab:claims}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{llllll}', '\\hline',
        '& & \\multicolumn{2}{c}{\\textbf{v1.0 (the file the report describes)}} & \\multicolumn{2}{c}{\\textbf{v2.2}} \\\\',
        '\\textbf{ID} & \\textbf{Claim of the report} & \\textbf{Measured} & \\textbf{Realized} & \\textbf{Measured} & \\textbf{Realized} \\\\', '\\hline',
        *rows, '\\hline', '\\end{tabular}', '\\end{table*}', '']))
    for v, tag in (('v1.0', 'One'), ('v2.2', 'TwoTwo')):
        vs = [c['verdict'] for c in res[v].values()]
        num('ClaimsRealized' + tag, vs.count('REALIZED')); num('ClaimsUnrealized' + tag, vs.count('UNREALIZED'))
        num('ClaimsMismatch' + tag, vs.count('MISMATCH')); num('ClaimsNot' + tag, len(vs) - vs.count('REALIZED'))
    num('ClaimsTotal', len(doc['claims']))
    # of the claims that fail on v1.0: how many v2.2 realizes, and how many it still does not
    num('ClaimsRepaired', sum(res['v1.0'][i]['verdict'] != 'REALIZED' and res['v2.2'][i]['verdict'] == 'REALIZED' for i in res['v1.0']))
    num('ClaimsStillNot', sum(res['v1.0'][i]['verdict'] != 'REALIZED' and res['v2.2'][i]['verdict'] != 'REALIZED' for i in res['v1.0']))
    # what the count of claims leaves out: the vocabulary that the report merely names (scripts/report_vocabulary.py)
    voc = J('audit_report_vocabulary.json')
    c1 = voc['v1.0']['counts']
    num('NamedClasses', c1['classes'][1]); num('NamedObjProps', c1['object properties'][1]); num('NamedIndividuals', c1['individuals'][1])
    num('NamedSignatures', c1['signatures'][1]); num('NamedLinks', c1['subclass links'][1]); num('NamedAssertions', c1['assertions'][1])
    num('NamedTotal', sum(v[1] for v in c1.values())); num('NamedHoldOne', sum(v[0] for v in c1.values()))
    num('NamedHoldTwoTwo', sum(v[0] for v in voc['v2.2']['counts'].values()))
    assert voc['v1.0']['not_holding'] == ['subclass links: Subjetiva < Questao'], voc['v1.0']['not_holding']   # the text names this one


# ------------------------------------------------------------------- classes
KINDS = [('Agent', ['UsuarioDoAva']), ('Competency', ['Competencia']),
         ('Competency component', ['Conhecimento', 'Habilidade', 'Atitude']),
         ('Instructional artifact', ['Curso', 'RecursoDeAprendizagem']),
         ('Assessment instrument', ['Avaliacao', 'Questao']),
         ('Evidence record', ['DesempenhoDoAprendiz']), ('Scale value', ['NiveisDeProficiencia']),
         ('Progress record', ['MilestoneDeAprendizagem', 'TrajetoriasDeAprendizagem'])]
GLOSS = {'UsuarioDoAva': 'VLE user', 'Competencia': 'Competency', 'Conhecimento': 'Knowledge', 'Habilidade': 'Skill',
         'Atitude': 'Attitude', 'Curso': 'Course', 'RecursoDeAprendizagem': 'Learning resource', 'Avaliacao': 'Assessment',
         'Questao': 'Question item', 'DesempenhoDoAprendiz': 'Performance record', 'NiveisDeProficiencia': 'Proficiency level',
         'MilestoneDeAprendizagem': 'Learning milestone', 'TrajetoriasDeAprendizagem': 'Learning trajectory'}


def classes():
    """The 13 root concepts, their kind and their subclasses, read from the released v2.2 file."""
    from rdflib import RDFS, OWL, RDF, URIRef
    g = load('v2.2')
    cls = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
    sub = collections.defaultdict(list)
    for c, p in g.subject_objects(RDFS.subClassOf):
        if c in cls and p in cls:
            sub[sh(p).lstrip(':')].append(sh(c).lstrip(':'))
    roots = sorted(sh(c).lstrip(':') for c in cls if not any(isinstance(p, URIRef) and p in cls for p in g.objects(c, RDFS.subClassOf)))
    listed = [c for _, cs in KINDS for c in cs]
    assert sorted(listed) == roots == sorted(ROOTS13), (roots, listed)

    def subs(c):                                     # direct subclasses; a nested one is shown after an arrow
        out = []
        for k in sub.get(c, []):
            out.append(tth(k) + (' ($\\rightarrow$ ' + ', '.join(tth(x) for x in sub[k]) + ')' if sub.get(k) else ''))
        return ', '.join(out) if out else '---'
    order = {'NiveisDeProficiencia': TIERS}
    for c in sub:
        sub[c] = sorted(sub[c], key=lambda k: order.get(c, sorted(sub[c])).index(k))
    body = []
    for kind, cs in KINDS:
        for i, c in enumerate(cs):
            body.append(f"{kind if i == 0 else ''} & {tth(c)} & {GLOSS[c]} & {subs(c)} \\\\")
    n_cls = len(cls); n_spec = sum(len(v) for v in sub.values())
    within = sum(len(cs) * (len(cs) - 1) // 2 for _, cs in KINDS); total = len(roots) * (len(roots) - 1) // 2
    num('RootConcepts', len(roots)); num('Specializations', n_spec)
    num('RootPairs', total); num('RootPairsWithinKind', within); num('RootPairsBetweenKinds', total - within)
    assert n_cls == len(roots) + n_spec == 29
    write('tab_classes.tex', '\n'.join([
        '\\begin{table}[!t]',
        f'\\caption{{The {len(roots)} root concepts of OntoLearn, grouped by the kind of thing they denote, and their specializations ({n_cls} OWL classes in total; read from the released v2.2 file). In v1.0 the class \\texttt{{Subjetiva}} is declared but not linked to \\texttt{{Questao}}.}}',
        '\\label{tab:classes}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{3pt}',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{1.5cm}>{\\raggedright\\arraybackslash}p{2.3cm}>{\\raggedright\\arraybackslash}p{1.5cm}>{\\raggedright\\arraybackslash}p{2.35cm}}', '\\hline',
        '\\textbf{Kind} & \\textbf{Root concept} & \\textbf{Gloss} & \\textbf{Subclasses} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table}', '']))


# --------------------------------------------------------------------- delta
def delta():
    """Table of the completion families, with the number of logical axioms of each family counted
    on the released files (axiom-level difference computed by the OWL API)."""
    def diff(a, b):
        rows = [r.split('\t') for r in harness('diff', locked(a), locked(b))[1:]]
        return [r[1:] for r in rows if r[0] == 'ONLY_A'], [r[1:] for r in rows if r[0] == 'ONLY_B']

    def family(t, ax):
        if t == 'DataPropertyAssertion': return 'lexical'
        if t == 'DataPropertyDomain': return 'F0'
        if t == 'SubClassOf': return 'F3' if 'ObjectSomeValuesFrom' in ax else 'F1'
        if t == 'DisjointClasses': return {2: 'F2', 13: 'F2b', 6: 'F6'}[ax.count('<:')]
        if t in ('SubObjectPropertyOf', 'InverseObjectProperties', 'ObjectPropertyDomain', 'ObjectPropertyRange'): return 'F4'
        if t == 'FunctionalObjectProperty': return 'F5'
        raise ValueError((t, ax))

    gone, new = diff('v1.0', 'v2.2')
    fam = collections.Counter(family(t, ax) for t, ax in new)
    # one dateTime literal changes lexical form (E0); two domain axioms are widened, not added
    assert fam.pop('lexical') == 1 and sum(t == 'DataPropertyAssertion' for t, _ in gone) == 1
    widened = fam.pop('F0')
    assert widened == sum(t == 'DataPropertyDomain' for t, _ in gone) == 2
    withdrawn = [ax for t, ax in gone if t not in ('DataPropertyAssertion', 'DataPropertyDomain')]
    assert withdrawn == ['DisjointClasses(<:Aprendiz> <:Instrutor>)'], withdrawn
    total = sum(fam.values())
    assert int(NUM['LogicalTwoTwo']) - int(NUM['LogicalOne']) == total - len(withdrawn)
    num('AddedRetained', total); num('InheritedWithdrawn', len(withdrawn))
    for f, tag in (('F1', 'One'), ('F2', 'Two'), ('F2b', 'TwoB'), ('F3', 'Three'), ('F4', 'Four'), ('F5', 'Five'), ('F6', 'Six')):
        num('Fam' + tag, fam[f])
    # the steps: what v2.0 added, what v2.1 added and withdrew, what v2.2 added
    g20, n20 = diff('v1.0', 'v2.0')
    f20 = collections.Counter(family(t, ax) for t, ax in n20); f20.pop('lexical'); f20.pop('F0')
    num('AddedTwoZero', sum(f20.values())); num('FamThreeTwoZero', f20['F3']); num('FamFourTwoZero', f20['F4'])
    assert int(NUM['LogicalTwoZero']) - int(NUM['LogicalOne']) == sum(f20.values())
    g21, n21 = diff('v2.0', 'v2.1')
    add21 = [(t, ax) for t, ax in n21 if t != 'DataPropertyDomain']; rem21 = [(t, ax) for t, ax in g21 if t != 'DataPropertyDomain']
    num('AddedTwoOne', len(add21)); num('WithdrawnTwoOne', len(rem21))
    assert all(family(t, ax) == 'F4' for t, ax in add21) and len(rem21) == 2
    assert int(NUM['LogicalTwoOne']) - int(NUM['LogicalTwoZero']) == len(add21) - len(rem21)
    g22, n22 = diff('v2.1', 'v2.2')
    assert not g22 and [family(t, ax) for t, ax in n22] == ['F6']
    rows = [
        ('F0', 'Union domain of \\texttt{descricao} extended with \\texttt{NiveisDe\\allowbreak{}Proficiencia} (v2.0) and \\texttt{Atitude} (v2.1); domain of \\texttt{data} extended to performance records (v2.1)', '2.0, 2.1', '0$^{*}$', 'repairs D2, D3'),
        ('F1', '\\texttt{Subjetiva} $\\sqsubseteq$ \\texttt{Questao}', '2.0', fam['F1'], 'repairs D1; realizes C15'),
        ('F2', 'Pairwise disjointness of the KSA triad; \\texttt{Objetiva}$\\,\\bot\\,$\\texttt{Subjetiva}', '2.0', fam['F2'], 'realizes C03; restores'),
        ('F2b', '\\texttt{owl:AllDisjointClasses} over the 13 root concepts', '2.0', fam['F2b'], 'restores; detection'),
        ('F3', 'Three existential participation axioms, e.g., \\texttt{Questao} $\\sqsubseteq \\exists$\\texttt{competencias\\allowbreak{}Avaliadas}.\\texttt{Competencia}', '2.0, 2.1', fam['F3'], 'realizes C04'),
        ('F4', 'KSA role hierarchy: six sub-property axioms, the inverse pairing, and the domains and ranges of two super-properties', '2.0, 2.1', fam['F4'], 'realizes C02'),
        ('F5', '\\texttt{proficienciaAtingida} functional', '2.0', fam['F5'], 'one level per record'),
        ('F6', '\\texttt{owl:AllDisjointClasses} over the six Bloom categories', '2.2', fam['F6'], 'restores; lets F5 detect'),
    ]
    write('tab_delta.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{Axiom families of the completion as they stand in v2.2. Ax.: logical axioms added and retained, counted by the OWL~API on the released files (OWL axioms, not RDF triples). ``Restores\'\' marks a commitment present in development states v2--v3 and lost afterwards (Section~\\ref{sec:lineage}).}',
        '\\label{tab:delta}', '\\centering', '\\footnotesize',
        '\\setlength{\\tabcolsep}{3pt}',
        '\\begin{tabular}{p{0.65cm}>{\\raggedright\\arraybackslash}p{4.0cm}>{\\raggedright\\arraybackslash}p{0.6cm}p{0.4cm}>{\\raggedright\\arraybackslash}p{1.7cm}}', '\\hline',
        '\\textbf{Fam.} & \\textbf{Content} & \\textbf{Ver.} & \\textbf{Ax.} & \\textbf{Tie} \\\\', '\\hline',
        *[f'{a} & {b} & {c} & {d} & {e} \\\\' for a, b, c, d, e in rows],
        '\\hline',
        f'\\multicolumn{{3}}{{l}}{{\\textbf{{Logical axioms added and retained}}}} & \\textbf{{{total}}} & \\\\',
        '\\multicolumn{5}{p{8.0cm}}{\\footnotesize Withdrawn in v2.1: \\texttt{Aprendiz}$\\,\\bot\\,$\\texttt{Instrutor} (inherited from v1.0) and a fourth F3 axiom, \\texttt{RecursoDe\\allowbreak{}Aprendizagem} $\\sqsubseteq \\exists$\\texttt{aborda\\allowbreak{}Competencia}.\\texttt{Competencia} (added in v2.0).} \\\\',
        '\\multicolumn{5}{p{8.0cm}}{\\footnotesize $^{*}$F0 widens existing domain axioms rather than adding any.} \\\\',
        '\\hline', '\\end{tabular}', '\\end{table}', '']))


# ---------------------------------------------------------------- candidates
def candidates():
    """Complete output of the isolated-class analysis on v1.0 (reviewer request): every stage-1
    candidate, the evidence found for it, the verdict, and its adjudication."""
    r = audit.run(locked('v1.0'), locked('claims/sbie2026.json'))
    roots = set(ROOTS13)
    body, tp, fp, fn, tn = [], 0, 0, 0, 0
    for k in sorted(r['isolated'], key=lambda k: (k['verdict'] == 'ROOT', k['class'])):
        ev = [e['evidence'] for e in k['evidence']]
        flagged = k['verdict'] == 'DISCONNECTED'
        defect = k['class'] not in roots          # adjudication: the 13 root concepts are legitimate; D1 is the only defect
        tp += flagged and defect; fp += flagged and not defect; fn += (not flagged) and defect; tn += (not flagged) and not defect
        adj = ('defect D1' if flagged else 'defect, missed') if defect else ('root, flagged' if flagged else 'root')
        body.append(f"{tth(k['class'])} & {'no' if 'unreferenced' in ev else 'yes'} & {', '.join(ev) if ev else '---'} & "
                    f"{'\\vd{Disconnected}' if flagged else '\\vd{' + k['verdict'].capitalize() + '}'} & {adj} \\\\")
    assert (tp, fp, fn) == (1, 0, 0) and tn == len(r['isolated']) - 1
    num('CandidatesOne', len(r['isolated'])); num('CandidatesOneRoots', tn)
    write('tab_candidates.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{Complete output of the isolated-class analysis on v1.0 (\\texttt{scripts/audit.py} with \\texttt{claims/sbie2026.json}). '
        'Stage~1 returns every named class with neither a named superclass nor a named subclass; stage~2 looks for evidence. '
        'Sig.: the class is named in a property signature. Adjudication: what the class is, a legitimate root concept or the defect D1; the analysis has one true positive, no false positive and no false negative. The other six root concepts have subclasses and are not candidates.}',
        '\\label{tab:candidates}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{2.5pt}',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.3cm}p{0.45cm}>{\\raggedright\\arraybackslash}p{1.9cm}>{\\raggedright\\arraybackslash}p{1.95cm}>{\\raggedright\\arraybackslash}p{1.05cm}}', '\\hline',
        '\\textbf{Stage-1 candidate} & \\textbf{Sig.} & \\textbf{Stage-2 evidence} & \\textbf{Verdict} & \\textbf{Adjud.} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table}', '']))


# ------------------------------------------------------------------- lineage
def lineage():
    rows = J('E8_lineage.json')
    body = []
    for r in rows:
        if not r['rdf']:
            continue
        name = r['state'].replace('=', '$\\equiv$')
        if r['state'] == 'v10':
            name = 'v10 (= v1.0)'
        ind = str(r['individuals']) + (f"$^{{\\dagger}}$" if r['individuals_incl_undeclared'] != r['individuals'] else '')
        body.append(f"{name} & {r['classes']} & {r['object_properties']} & {r['data_properties']} & {r['inverse_axioms']} & {r['disjointness']} & "
                    f"{r['sub_property_axioms'] + r['restrictions'] + r['cardinality']} & {ind} & {r['rho']:.2f} \\\\")
    und = [(r['state'], r['individuals_incl_undeclared'] - r['individuals']) for r in rows if r['rdf'] and r['individuals_incl_undeclared'] != r['individuals']]
    note = '; '.join(f"{s.replace('=', '$\\equiv$')}: {n}" for s, n in und)
    write('tab_lineage.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{Measured structural trace across the nine RDF states (\\texttt{scripts/lineage.py}). An entity is counted when it is declared in the file. Disj: disjointness axioms, binary and $n$-ary; H/R/C: sub-property axioms, class restrictions and cardinality constraints, together; $\\rho$ = (object $+$ data properties) / classes.}',
        '\\label{tab:lineage}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{3.5pt}',
        '\\begin{tabular}{lrrrrrrrr}', '\\hline',
        '\\textbf{State} & \\textbf{Cls} & \\textbf{ObjP} & \\textbf{DatP} & \\textbf{Inv} & \\textbf{Disj} & \\textbf{H/R/C} & \\textbf{Ind} & $\\bm{\\rho}$ \\\\', '\\hline',
        *body, '\\hline',
        f'\\multicolumn{{9}}{{p{{7.6cm}}}}{{\\footnotesize $^{{\\dagger}}$Further individuals are typed by a declared class without an \\texttt{{owl:NamedIndividual}} declaration ({note}).}} \\\\',
        '\\end{tabular}', '\\end{table}', '']))
    num('LineageStates', sum(1 for r in rows)); num('LineageRdfStates', sum(1 for r in rows if r['rdf']))
    # the report's own table of the evolution (its Table 3), compared with the preserved files
    tr = J('E8_report_trace.json')
    early = [t for t in tr if t['state'] != 'v10']
    num('TraceEarlyValues', len(early)); num('TraceEarlyAgree', sum(t['agree'] for t in early))
    diff = {(t['state'], t['metric']): t for t in early if not t['agree']}
    assert set(diff) == {('v2', 'classes'), ('v6', 'individuals')}, diff        # the sentence in Section V names these two
    num('TraceClassesTwoReported', diff[('v2', 'classes')]['reported']); num('TraceClassesTwoMeasured', diff[('v2', 'classes')]['measured'])
    num('TraceIndSixReported', diff[('v6', 'individuals')]['reported']); num('TraceIndSixMeasured', diff[('v6', 'individuals')]['measured'])
    num('TraceClassesZero', next(t['measured'] for t in tr if t['state'] == 'v0' and t['metric'] == 'classes'))


# ------------------------------------------------------------------ ablation
def ablation():
    r = J('E1_ablation.json')
    A = {x['configuration']: x for x in r['A']}
    def cell(name):
        x = A[name]
        assert x['agree']
        return ('consistent', x['unsat_hermit']) if x['hermit'] == 'consistent' else ('\\textbf{inconsistent}', 'n/a')
    inc = [k for k in A if k.startswith('core + F0') or k == 'core = v2.2 minus F0..F6']
    assert all(A[k]['hermit'] == 'consistent' and A[k]['unsat_hermit'] == '0' for k in inc)
    loo = [f'v2.2 - {f}' for f in ['F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6']]
    assert all(A[k]['hermit'] == 'consistent' and A[k]['unsat_hermit'] == '0' for k in loo)
    rows = [
        ('v1.0 (released file)', *cell('v1.0 (released file)')),
        ('v2.2 without F0--F6', *cell('core = v2.2 minus F0..F6')),
        ('\\quad + F2b only (order in which D2 was found)', *cell('core + F2b only (pre-repair order)')),
        (f'\\quad + F0, then F1, \\dots, F6 ({len(inc) - 1} cumulative steps)', 'consistent (all)', '0 (all)'),
        ('v2.2 $-$ F0', *cell('v2.2 - F0')),
        ('\\quad v2.2 $-$ F0a (repair of D2 alone)', *cell('v2.2 - F0a (D2 repair only)')),
        ('\\quad v2.2 $-$ F0b (v2.1 domain extensions alone)', *cell('v2.2 - F0b (v2.1 domain extensions only)')),
        ('v2.2 $-$ each of F1, F2, F2b, F3, F4, F5, F6', 'consistent (all)', '0 (all)'),
        ('v2.0, v2.1, v2.2 (released files)', 'consistent (all)', '0 (all)'),
    ]
    assert all(A[f'{v} (released file)']['hermit'] == 'consistent' for v in ('v2.0', 'v2.1', 'v2.2'))
    write('tab_hermit.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{Consistency ablation over the axiom families on the 20-individual ABox. Every configuration is the released v2.2 file minus the triples of the named families. HermiT~1.4.3 and Openllet~2.6.5 agree on every row. The number of unsatisfiable named classes is not applicable (n/a) to an inconsistent ontology.}',
        '\\label{tab:hermit}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{4.6cm}>{\\raggedright\\arraybackslash}p{1.75cm}p{0.85cm}}', '\\hline',
        '\\textbf{Configuration} & \\textbf{Verdict} & \\textbf{Unsat.} \\\\', '\\hline',
        *[f'{a} & {b} & {c} \\\\' for a, b, c in rows], '\\hline', '\\end{tabular}', '\\end{table}', '']))
    num('AblationConfigs', len(A))

    B, D = r['B'], r['D']
    def crow(label, key, src):
        d = src[key]
        return f"{label} & {d['asserted']} & {d['class_assertions']} & {d['property_assertions']} & {d['inferred_total']} & {d['inferred_new_vocabulary']} & {d['rl_inferred']} \\\\"
    nat = [('v1.0', 'v1.0'), ('\\quad $-$ transitivity', 'v1.0 - T'), ('\\quad $-$ inverses', 'v1.0 - I'),
           ('v2.0', 'v2.0'), ('v2.1', 'v2.1'), ('v2.2', 'v2.2'),
           ('\\quad $-$ F1', 'v2.2 - F1'), ('\\quad $-$ F2', 'v2.2 - F2'), ('\\quad $-$ F2b', 'v2.2 - F2b'), ('\\quad $-$ F3', 'v2.2 - F3'),
           ('\\quad $-$ F4', 'v2.2 - F4'), ('\\quad $-$ F5', 'v2.2 - F5'), ('\\quad $-$ F6', 'v2.2 - F6'),
           ('\\quad $-$ transitivity', 'v2.2 - T'), ('\\quad $-$ inverses', 'v2.2 - I')]
    ext = [('v1.0 schema', 'v1.0 schema'), ('v2.2', 'v2.2'), ('\\quad $-$ F4', 'v2.2 - F4'),
           ('\\quad $-$ transitivity', 'v2.2 - T'), ('\\quad $-$ inverses', 'v2.2 - I')]
    same = [k for k in ['v2.2 - F1', 'v2.2 - F2', 'v2.2 - F2b', 'v2.2 - F3', 'v2.2 - F5', 'v2.2 - F6'] if D[k]['lost_vs_full'] == 0]
    assert len(same) == 6
    assert all(B[k]['dl_minus_rl'] == 0 for k in B) and all(D[k]['dl_minus_rl'] == 0 and D[k]['rl_minus_dl'] == 0 for k in D if isinstance(D[k], dict))
    write('tab_census.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{Entailment census: atomic assertions over the named individuals that are entailed but not asserted. The asserted facts are identical within each block, so differences are due to the schema alone. DL: complete OWL~2~DL entailment (HermiT and Openllet return the same set); RL: OWL~2~RL rule closure (\\texttt{owlrl}). New: inferred assertions that use a term absent from v1.0. A leading $-$ removes one family from the configuration above it.}',
        '\\label{tab:census}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{4pt}',
        '\\begin{tabular}{lrrrrrr}', '\\hline',
        '& & \\multicolumn{4}{c}{\\textbf{Inferred (DL)}} & \\\\',
        '\\textbf{Configuration} & \\textbf{Asserted} & $C(a)$ & $p(a,b)$ & \\textbf{Total} & \\textbf{New} & \\textbf{RL} \\\\', '\\hline',
        '\\multicolumn{7}{l}{\\emph{20-individual ABox}} \\\\',
        *[crow(a, b, B) for a, b in nat], '\\hline',
        '\\multicolumn{7}{l}{\\emph{Extended fact base (53 individuals)}} \\\\',
        *[crow(a, b, D) for a, b in ext],
        '\\multicolumn{7}{l}{\\quad $-$ each of F1, F2, F2b, F3, F5, F6: identical to v2.2} \\\\',
        '\\hline', '\\end{tabular}', '\\end{table}', '']))
    num('InfOne', B['v1.0']['inferred_total']); num('InfTwoTwo', B['v2.2']['inferred_total'])
    num('InfNewTwoTwo', B['v2.2']['inferred_new_vocabulary']); num('InfSharedTwoTwo', B['v2.2']['inferred_shared_vocabulary'])
    num('AssertedNative', B['v2.2']['asserted'])
    num('InvOne', B['v1.0']['inferred_total'] - B['v1.0 - I']['inferred_total'])
    num('InvTwoTwo', B['v2.2']['inferred_total'] - B['v2.2 - I']['inferred_total'])
    num('TransNative', B['v2.2']['inferred_total'] - B['v2.2 - T']['inferred_total'])
    num('RoleHierNative', B['v2.2']['inferred_total'] - B['v2.2 - F4']['inferred_total'])
    num('ExtAsserted', D['v2.2']['asserted']); num('ExtInfOne', D['v1.0 schema']['inferred_total']); num('ExtInfTwoTwo', D['v2.2']['inferred_total'])
    num('ExtNew', D['v2.2']['inferred_new_vocabulary']); num('ExtTrans', D['v2.2 - T']['lost_vs_full'])
    num('ExtInv', D['v2.2 - I']['lost_vs_full']); num('ExtRoleHier', D['v2.2 - F4']['lost_vs_full'])
    num('LegacyDomOne', B['v1.0']['domain_relevant_triples']); num('LegacyDomTwoZero', B['v2.0']['domain_relevant_triples'])
    num('LegacyDomTwoTwo', B['v2.2']['domain_relevant_triples'])
    for tag, v in (('One', 'v1.0'), ('TwoZero', 'v2.0'), ('TwoTwo', 'v2.2')):
        num('LegacyAtomic' + tag, B[v]['domain_relevant_atomic'])
        num('LegacyIndOther' + tag, B[v]['domain_relevant_individual_other'])
        num('LegacySchema' + tag, B[v]['domain_relevant_schema'])
        assert B[v]['domain_relevant_atomic'] + B[v]['domain_relevant_individual_other'] + B[v]['domain_relevant_schema'] == B[v]['domain_relevant_triples']
        assert B[v]['domain_relevant_atomic'] == B[v]['rl_inferred']        # the atomic part IS the census
    num('SubsumptionsOne', B['v1.0']['subsumptions_asserted'] + B['v1.0']['subsumptions_inferred'])
    num('SubsumptionsTwoTwo', B['v2.2']['subsumptions_asserted'] + B['v2.2']['subsumptions_inferred'])


# --------------------------------------------------------------------- tests
def tests():
    rows = list(csv.DictReader(open(RESULTS / 'E2_axiom_tests.tsv', encoding='utf-8'), delimiter='\t'))
    assert all(r['match'] == 'yes' for r in rows)
    by = collections.OrderedDict()
    for r in rows:
        d = by.setdefault(r['test'], {'kind': r['kind'], 'family': r['family'], 'desc': r['description']})
        d.setdefault(r['version'], set()).add(r['observed'])
    assert all(len(d[v]) == 1 for d in by.values() for v in VERS), 'reasoners disagree'

    def code(s):
        if s == 'inconsistent':
            return '\\textbf{inc.}'
        if s == 'consistent':
            return 'cons.'
        if s == 'entailed':
            return 'yes'
        if s == 'not entailed':
            return 'no'
        if ' of ' in s and s.endswith('inconsistent'):
            a, _, b = s.split()[:3]
            return f'{a}/{b} inc.'
        assert s.startswith('consistent; ')
        tail = s[len('consistent; '):]
        if '=' in tail:
            return 'cons.; yes' if tail.endswith(' entailed') and not tail.endswith('not entailed') else 'cons.; no'
        return 'cons.; yes' if not tail.endswith('not entailed') else 'cons.; no'
    text = {
        'S01': 'Released file, no added fact: verdict',
        'S02': 'Individual typed only \\texttt{Subjetiva}: is it a \\texttt{Questao}?',
        'S03': 'Chain of three \\texttt{requer} links: is the end-to-end link entailed?',
        'S04': 'Record linked to a learner in one direction only: is the inverse link entailed?',
        'S05': 'Competency with a knowledge component: is \\texttt{temComponenteKSA} entailed?',
        'S06': 'One individual typed \\texttt{Conhecimento} and \\texttt{Habilidade}',
        'S07': 'One individual typed \\texttt{Aprendiz} and \\texttt{Competencia}',
        'S08': 'One question typed \\texttt{Objetiva} and \\texttt{Subjetiva}',
        'S09': 'A question used as subject of \\texttt{requer} (domain \\texttt{Competencia})',
        'S10': 'Contradictory record: a second level of a \\emph{different} category; are the two levels entailed equal?',
        'S11': 'Record with two level individuals of the \\emph{same} category; are they entailed equal?',
        'S12': 'Sweep: two levels of different categories on one record, all 15 pairs',
        'S13': 'Sweep: one individual typed with two root classes, all 78 pairs',
        'S14': "Record with no recorded level: is ``some level'' entailed?",
        'S15': 'Legitimate: an attitude carrying a description',
        'S16': 'Legitimate: a performance record carrying a date; is it entailed to be a milestone?',
        'S17': 'Legitimate: an instructor enrolled as a learner; is it entailed to be a learner?',
        'S18': "A resource with no competency: is ``addresses some competency'' entailed?",
        'S19': 'An individual typed with a class and its superclass',
        'S20': 'Contested: one individual typed \\texttt{Avaliacao} and \\texttt{RecursoDeAprendizagem}',
        'S21': 'Contested: one individual typed \\texttt{Curso} and \\texttt{RecursoDeAprendizagem}',
    }
    kind = {'positive': 'pos.', 'negative': 'neg.', 'negative sweep': 'neg.', 'control': 'ctrl.', 'scope probe': 'scope'}
    body = []
    for t in sorted(by):
        d = by[t]
        fam = d['family'].replace('v2.1 revision', 'v2.1').replace('F2b + domain', 'F2b').replace(' + ', ', ').replace('-', '---')
        body.append(f"{t} & {kind[d['kind']]} & {fam} & {text[t]} & " + ' & '.join(code(next(iter(d[v]))) for v in VERS) + ' \\\\')
    write('tab_tests.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{Semantic test cases (\\texttt{scripts/java/AxiomTests.java}). Each test adds a few facts to a released file and asks one question of an OWL~2~DL reasoner. Expected outcomes were registered per version before execution; all ' + str(len(rows)) + ' runs (' + str(len(by)) + ' tests, four versions, HermiT and Openllet) matched them, and the two reasoners agree on every run. pos.: an intended consequence; neg.: a fault that should be rejected; ctrl.: data that should not be rejected; scope: a contested exclusion. cons.: consistent; \\textbf{inc.}: inconsistent; yes/no: the stated axiom is/is not entailed.}',
        '\\label{tab:tests}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{4pt}',
        '\\begin{tabular}{ll>{\\raggedright\\arraybackslash}p{0.9cm}>{\\raggedright\\arraybackslash}p{7.3cm}llll}', '\\hline',
        '\\textbf{Test} & \\textbf{Kind} & \\textbf{Family} & \\textbf{Added facts and question} & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table*}', '']))
    num('TestRuns', len(rows)); num('TestCount', len(by))


# ----------------------------------------------------------------------- CQs
def cqs():
    r = J('E3_cq_suite.json')
    why = {
        'cq1.rq': 'binds the learner by \\texttt{rdfs:label} (names are held in \\texttt{:nome}); literal without diacritics; undeclared property \\texttt{:competenciaAvaliada}',
        'cq2.rq': 'as CQ1, for the learner and for the competency',
        'cq3.rq': 'binds the competency by \\texttt{rdfs:label}; undeclared property \\texttt{:temQuestao}',
        'cq4.rq': 'binds the competency by \\texttt{rdfs:label}; literal without diacritics',
        'cq5.rq': 'binds the competency by \\texttt{rdfs:label}; literal without diacritics',
        'cq6.rq': 'undeclared property \\texttt{:competenciaAvaliada}; the class \\texttt{:Aplicar} used where a level individual is required; no \\texttt{:area} value equal to the literal',
        'cq7.rq': 'binds the learner by \\texttt{rdfs:label}; literal without diacritics; undeclared property \\texttt{:acessouRecurso}',
        'cq8.rq': 'binds the learner by \\texttt{rdfs:label}; literal without diacritics',
    }
    # every stated cause must be backed by the script's own diagnosis
    for q, d in r['A'].items():
        assert all(n == 0 for v in d['solutions'].values() for n in v.values())
        txt = ' '.join(d['diagnosis_v1.0'])
        for term in ['competenciaAvaliada', 'temQuestao', 'acessouRecurso', 'Aplicar']:
            if term in why[q]:
                assert term in txt, (q, term)
        if 'rdfs:label' in why[q]:
            assert 'rdfs:label' in txt, q
        if 'without diacritics' in why[q]:
            assert 'the data hold' in txt, q        # the diagnosis found the accented form of the literal in the data
        if 'no \\texttt{:area} value' in why[q]:
            assert 'no resource has :area' in txt, q
    body = [f"CQ{q[2]} & 0 & {why[q]} \\\\" for q in sorted(r['A'])]
    num('CqUndeclaredProp', sum(1 for d in r['A'].values() if any('is not declared' in x for x in d['diagnosis_v1.0'])))
    num('CqDeposited', len(r['A'])); num('CqDepositedRuns', len(r['A']) * 4 * 3)
    write('tab_cq_deposited.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{The eight queries deposited with the original report (\\texttt{sparql/cq1.rq}--\\texttt{cq8.rq}), executed as deposited. Solutions: number of results on each of the four releases, over the asserted graph, under OWL~2~DL materialization and under OWL~2~RL closure (twelve executions per query, all equal). Causes are those reported by the automatic diagnosis of \\texttt{scripts/cq\\_suite.py} on v1.0.}',
        '\\label{tab:cqdep}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{p{0.75cm}p{0.5cm}>{\\raggedright\\arraybackslash}p{6.0cm}}', '\\hline',
        '\\textbf{Query} & \\textbf{Sol.} & \\textbf{Why nothing can match} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table}', '']))

    changed = collections.defaultdict(list)
    for f, cs in r['C'].items():
        for c in cs:
            changed[c['case']].append(f)
    def cell(x):
        return 'inc.' if x['n'] is None else (str(x['n']) + ('' if x['conforms'] else '$^{\\times}$'))
    body = []
    for c in r['B']:
        res = c['results']
        body.append(f"{c['id'].replace('QC', 'CQ')} & {c['base'][:3]}. & {c['expected']} & {c['inference_dependent']} & "
                    + ' & '.join(f"{cell(res[v]['asserted'])} / {cell(res[v]['DL'])}" for v in VERS)
                    + f" & {', '.join(changed.get(c['id'], [])) or '---'} \\\\")
    S = r['B_summary']
    write('tab_cq_suite.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{Corrected competency-question suite: 20 cases with an answer key registered before execution \\cite{nogueira_thesis}, executed on each release. ref.: the 20-individual ABox; ext.: the extended fact base. Exp.: expected tuples; Inf.: expected tuples that are not in the asserted graph. Each cell gives the number of solutions over the asserted graph / after OWL~2~DL materialization (the OWL~2~RL closure returns the same numbers as the DL column in every cell). inc.: the fact base is inconsistent under that release. Last column: families whose removal from v2.2 changes the DL answer (I: inverse-property axioms; T: transitivity); no case changes when any of F1--F6 is removed.}',
        '\\label{tab:cqsuite}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{llrrccccl}', '\\hline',
        '\\textbf{Case} & \\textbf{Base} & \\textbf{Exp.} & \\textbf{Inf.} & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} & \\textbf{Depends on} \\\\', '\\hline',
        *body, '\\hline',
        'Conforming cases & & & & ' + ' & '.join(f"{S[v]['asserted']} / {S[v]['DL']}" for v in VERS) + ' & \\\\',
        '\\hline', '\\end{tabular}', '\\end{table*}', '']))
    for v in VERS:
        for reg in ('asserted', 'DL', 'RL'):
            assert all((c['results'][v]['RL']['n'] == c['results'][v]['DL']['n']) for c in r['B'])
    QTEXT = {'QC1': 'Which competencies has a given learner demonstrated?',
             'QC2': 'Which Bloom level did a learner reach in a competency?',
             'QC3': 'Which assessments are mapped to competency X?',
             'QC4': 'What are the direct and indirect prerequisites of Y?',
             'QC5': 'Which learning resources address competency Z?',
             'QC6': "Which learners reached ``Apply'' in programming?",
             'QC7': "Which resource URLs are in a learner's history for a competency?",
             'QC8': 'Is there a disparity between objective and subjective questions?'}
    rows8 = []
    for q in sorted(QTEXT):
        cs = [c for c in r['B'] if c['id'].startswith(q + '-')]
        dep = sorted({f for c in cs for f in changed.get(c['id'], [])})
        cells = []
        for v in VERS:
            a_ok = sum(c['results'][v]['asserted']['conforms'] for c in cs)
            d_ok = sum(bool(c['results'][v]['DL']['conforms']) for c in cs)
            inc = sum(c['results'][v]['DL']['n'] is None for c in cs)
            cells.append(f"{a_ok} / {d_ok}" + ('$^{\\dagger}$' if inc else ''))
        star = '$^{*}$' if q == 'QC4' else ''
        rows8.append(f"{q.replace('QC', 'CQ')} & {QTEXT[q]} & {len(cs)} & {sum(c['expected'] for c in cs)} ({sum(c['inference_dependent'] for c in cs)}) & "
                     + ' & '.join(cells) + f" & {', '.join(dep) + star if dep else '---'} \\\\")
    assert sum(len([c for c in r['B'] if c['id'].startswith(q + '-')]) for q in QTEXT) == len(r['B'])
    write('tab_cq_summary.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{The eight competency questions and their re-execution with the corrected suite (' + str(len(r['B'])) + ' cases, answer key fixed before execution). '
        'Tuples: expected answer tuples, with those that are not in the asserted graph in parentheses. Each version cell gives the number of cases whose result '
        'equals the expected set over the asserted graph / after OWL~2~DL materialization; the OWL~2~RL closure gives the same results as the DL column throughout. '
        'Depends on: axiom families whose removal from v2.2 changes the answer of at least one case (I: inverse-property axioms; T: transitivity); '
        'no case changes when any of F1--F6 is removed. The per-case results are in \\texttt{results/E3\\_cq\\_suite.txt}.}',
        '\\label{tab:cqsuite}', '\\centering', '\\footnotesize', '\\setlength{\\tabcolsep}{5.5pt}',
        '\\begin{tabular}{llccccccl}', '\\hline',
        '\\textbf{ID} & \\textbf{Question (abridged)} & \\textbf{Cases} & \\textbf{Tuples} & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} & \\textbf{Depends on} \\\\', '\\hline',
        *rows8, '\\hline',
        f"\\multicolumn{{2}}{{l}}{{All questions}} & {len(r['B'])} & {sum(c['expected'] for c in r['B'])} ({sum(c['inference_dependent'] for c in r['B'])}) & "
        + ' & '.join(f"{S[v]['asserted']} / {S[v]['DL']}" + ('$^{\\dagger}$' if v == 'v2.0' else '') for v in VERS) + ' & \\\\',
        '\\hline',
        '\\multicolumn{9}{p{15.5cm}}{\\footnotesize $^{\\dagger}$The extended fact base is inconsistent under v2.0 (defect D3), so its cases cannot be answered under inference. '
        '$^{*}$Only when the query is a plain triple pattern; with a property path (\\texttt{:requer+}) the answer depends on no axiom.} \\\\',
        '\\end{tabular}', '\\end{table*}', '']))
    num('CqCases', len(r['B'])); num('CqTuples', sum(c['expected'] for c in r['B'])); num('CqInfTuples', sum(c['inference_dependent'] for c in r['B']))
    num('CqConformOneDL', S['v1.0']['DL']); num('CqConformTwoTwoDL', S['v2.2']['DL']); num('CqConformTwoZeroDL', S['v2.0']['DL'])
    num('CqInvCases', len(r['C']['I'])); num('CqTransCases', len(r['C']['T']))
    assert all(len(r['C'][f]) == 0 for f in ['F1', 'F2', 'F2b', 'F3', 'F4', 'F5', 'F6'])
    P = r['D']
    p1 = next(v for k, v in P.items() if k.startswith('P1')); p2 = next(v for k, v in P.items() if k.startswith('P2')); p3 = next(v for k, v in P.items() if k.startswith('P3'))
    num('ProbeOneAssertedOne', p1['v1.0']['asserted']); num('ProbeOneAssertedTwoTwo', p1['v2.2']['asserted']); num('ProbeOneDLOne', p1['v1.0']['DL'])
    num('ProbeTwoAssertedOne', p2['v1.0']['asserted']); num('ProbeTwoDLOne', p2['v1.0']['DL'])
    num('ProbeThreeDLOne', p3['v1.0']['DL']); num('ProbeThreeDLTwoTwo', p3['v2.2']['DL']); num('ProbeThreeAssertedTwoTwo', p3['v2.2']['asserted'])


# --------------------------------------------------------------------- SHACL
def shacl_tab():
    r = J('E4_shacl.json')
    names = {'reference': '20-individual ABox', 'extended': 'Extended fact base',
             'probe-F3': '+ a subjective question, an assessment and a record with no link',
             'probe-F5': '+ a second level, of another category, on one record'}
    def cell(v, b):
        x = r[f'{v}/{b}']
        return ('cons.' if x['owl'] == 'consistent' else '\\textbf{inc.}') + f" / {x['shacl_violations']}"
    body = [f"{names[b]} & " + ' & '.join(cell(v, b) for v in VERS) + ' \\\\' for b in names]
    write('tab_shacl.tex', '\n'.join([
        '\\begin{table}[!t]',
        '\\caption{OWL verdict (HermiT and Openllet agree) / number of SHACL violations (\\texttt{shapes/ontolearn-shapes.ttl}, validated on the asserted graph) for the same fact base. The violation present in every cell is the released record \\texttt{DEMP-0004}, which has no recorded level.}',
        '\\label{tab:shacl}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.55cm}cccc}', '\\hline',
        '\\textbf{Fact base} & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table}', '']))
    num('ShaclProbeOne', r['v1.0/probe-F3']['shacl_violations']); num('ShaclProbeTwoTwo', r['v2.2/probe-F3']['shacl_violations'])
    num('ShaclNative', r['v2.2/reference']['shacl_violations'])


# -------------------------------------------------------------------- faults
def faults():
    r = J('E5_faults.json')
    X = [c for c in r if c.startswith('X') and c != 'X03s']
    L = [c for c in r if c.startswith('L')]
    n = r['X01']['v2.2']['n']
    for v, tag in zip(VERS, ['One', 'TwoZero', 'TwoOne', 'TwoTwo']):
        num('FaultsOwl' + tag, sum(1 for c in X if r[c][v]['owl'] == n))
        num('LegitRejected' + tag, sum(1 for c in L if r[c][v]['owl'] == n))
        # every count is all-or-nothing except the documented X03 under v1.0
        for c in r:
            for ch in ('owl', 'shacl', 'audit_conflict'):
                assert r[c][v][ch] in (0, n) or (c == 'X03' and v == 'v1.0' and ch == 'shacl'), (c, v, ch, r[c][v][ch])
    num('FaultClasses', len(X)); num('FaultBases', n); num('LegitClasses', len(L))
    num('FaultsShaclTwoTwo', sum(1 for c in X if r[c]['v2.2']['shacl'] == n))
    num('FaultsShaclOne', sum(1 for c in X if r[c]['v1.0']['shacl'] == n))       # the shapes do not depend on the completion
    num('FaultsAnyTwoTwo', sum(1 for c in X if r[c]['v2.2']['owl'] == n or r[c]['v2.2']['shacl'] == n))
    num('FaultsNoneTwoTwo', sum(1 for c in X if r[c]['v2.2']['owl'] == 0 and r[c]['v2.2']['shacl'] == 0 and r[c]['v2.2']['audit_conflict'] == 0))
    num('FaultsRlTwoTwo', sum(1 for c in X if r[c]['v2.2']['rl'] == n))
    num('FaultsAuditTwoTwo', sum(1 for c in X if r[c]['v2.2']['audit_conflict'] == n))
    num('XThreeShaclOne', r['X03']['v1.0']['shacl']); num('XThreeSubjShaclOne', r['X03s']['v1.0']['shacl']); num('XThreeSubjShaclTwoTwo', r['X03s']['v2.2']['shacl'])
    desc = {
        'X01': 'Contradictory record: a second level, of a different category', 'X02': 'A performance record loses its level',
        'X03': 'A question loses every competency link', 'X03s': '\\quad the same, on a subjective question',
        'X04': 'An assessment with no question', 'X05': 'A question made the subject of \\texttt{requer}',
        'X06': 'A learner also typed as a competency', 'X07': 'A knowledge component also typed as a skill',
        'X08': 'A question typed objective and subjective', 'X09': 'A competency requires an undeclared, untyped resource',
        'X10': 'A prerequisite cycle', 'X11': 'A learner carrying a \\texttt{descricao} (union domain)',
        'L01': 'Legitimate: an instructor enrolled as a learner', 'L02': 'Legitimate: an attitude carrying a description',
        'L03': 'Legitimate: a performance record carrying a date'}
    def cell(c, v):
        x = r[c][v]
        m = lambda k: ('$\\bullet$' if x[k] == n else ('$\\circ$' if x[k] == 0 else f"{x[k]}/{n}"))
        return f"{m('owl')} {m('shacl')} {m('audit_conflict')}"
    body = []
    for c in r:
        if c == 'L01':
            body.append('\\hline')
        rl = '$\\bullet$' if r[c]['v2.2']['rl'] == n else '$\\circ$'
        body.append(f"{'' if c == 'X03s' else c} & {desc[c]} & " + ' & '.join(cell(c, v) for v in VERS) + f" & {rl} \\\\")
    write('tab_faults.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{Fault injection: one fault (X) or one legitimate variation (L) injected into each of ' + str(n) + ' clean synthetic fact bases (four prerequisite topologies, five seeds; 337 individuals), laid under each release. Each cell shows three channels in the order OWL / SHACL / audit: an inconsistency reported by the DL reasoners (HermiT and Openllet agree), a SHACL violation that the clean base does not have, and a \\vd{Conflict} reported by the reasoner-free audit. $\\bullet$: noticed in all ' + str(n) + ' bases; $\\circ$: in none; a fraction otherwise. RL: an inconsistency raised by the OWL~2~RL rule engine on v2.2. For a legitimate variation, $\\bullet$ under OWL means that valid data are rejected.}',
        '\\label{tab:faults}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{llccccc}', '\\hline',
        '& & \\textbf{v1.0} & \\textbf{v2.0} & \\textbf{v2.1} & \\textbf{v2.2} & \\textbf{RL} \\\\',
        '\\textbf{Case} & \\textbf{Injected change} & \\multicolumn{4}{c}{\\footnotesize OWL\\; SHACL\\; audit} & \\textbf{(v2.2)} \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table*}', '']))


# --------------------------------------------------------------- selectivity
def selectivity():
    timing = J('E7_audit_timing_B.json')
    num('AuditMaxSecondsB', f"{timing['max_seconds']:.2f}"); num('AuditTimedOntologies', len(timing['runs']))
    r = J('E7_audit_selectivity.json')
    A = r['A']
    num('StageOneOne', A['v1.0/reference']['stage1']); num('StageOneTwoTwo', A['v2.2/reference']['stage1'])
    num('FlaggedAllVersions', sum(len(x['flagged']) for x in A.values()))
    num('IsoFalsePositives', sum(x['fp'] for x in A.values())); num('IsoFalseNegatives', sum(x['fn'] for x in A.values()))
    b1r, b1e = r['B1_summary_reference'], r['B1_summary_extended']
    b2 = r['B2']
    num('MutEdges', b1r['mutants']); num('MutEdgesDetRef', b1r['detected']); num('MutEdgesDetExt', b1e['detected'])
    num('MutEdgesUnrefRef', b1r['by_unreferenced']); num('MutEdgesUsageRef', b1r['by_usage']); num('MutEdgesUsageExt', b1e['by_usage'])
    num('MutUnion', b2['reference']['mutants']); num('MutUnionTotal', b2['reference']['mutants'] + b2['extended']['mutants'])
    num('MutUnionAgree', sum(b2[k]['both'] + b2[k]['neither'] for k in b2))
    num('MutUnionIncRef', b2['reference']['dl_inconsistent']); num('MutUnionIncExt', b2['extended']['dl_inconsistent'])
    assert all(b2[k]['audit_only'] == 0 and b2[k]['dl_only'] == 0 for k in b2)
    num('MutFamilies', len(r['B3'])); num('MutFamiliesCaught', sum(1 for v in r['B3'].values() if v))
    num('CtrlRoots', r['C1']['checks']); num('CtrlRootsFp', r['C1']['false_positives'])
    num('CtrlAnnot', r['C2']['mutants']); num('CtrlAnnotChanged', r['C2']['changed'])
    ext = r['C3']
    num('ExtOntologies', len(ext)); num('ExtDisconnected', sum(len(e['disconnected']) for e in ext))
    num('ExtSuspect', sum(len(e['suspect']) for e in ext)); num('ExtMismatches', sum(e['mismatches'] for e in ext))
    num('ExtSuspectSosa', len(next(e for e in ext if e['name'] == 'sosa')['suspect']))
    num('ExtSosaDomainIncludes', next(e for e in ext if e['name'] == 'sosa')['schema_domainIncludes_triples'])
    num('DlAgree', r['D_agreement'][0]); num('DlTotal', r['D_agreement'][1])
    num('ExtIndividuals', sum(e['individuals'] for e in ext))
    fx = J('E7_audit_fixtures.json')
    num('Fixtures', fx['n']); num('FixturesAsExpected', fx['audit_as_expected']); num('FixturesAgree', fx['prediction_agrees'])
    num('FixturesInconsistent', fx['inconsistent'])
    assert fx['dl_as_expected'] == fx['n']
    rows = [
        ('Released versions (4 versions $\\times$ 2 fact bases)', 'isolated classes flagged', f"{NUM['FlaggedAllVersions']} flagged: \\texttt{{Subjetiva}} in v1.0 (both bases); {NUM['IsoFalsePositives']} false positives, {NUM['IsoFalseNegatives']} false negatives"),
        (f"Deleted specialization link ({b1r['mutants']} mutants of v2.2)", 'defect reported', f"{b1r['detected']}/{b1r['mutants']} on the 20-individual ABox ({b1r['by_unreferenced']} by \\textit{{unreferenced}} evidence, {b1r['by_usage']} through the data); {b1e['detected']}/{b1e['mutants']} on the extended base ({b1e['by_unreferenced']} and {b1e['by_usage']})"),
        (f"Deleted union member ({b2['reference']['mutants']} mutants $\\times$ 2 fact bases)", '\\vd{Conflict} $\\Leftrightarrow$ inconsistent under OWL~2~DL', f"agreement on {NUM['MutUnionAgree']}/{NUM['MutUnionTotal']} ({b2['reference']['dl_inconsistent']} and {b2['extended']['dl_inconsistent']} inconsistent mutants)"),
        (f"Deleted axiom family ({len(r['B3'])} mutants of v2.2)", 'a claim of this paper becomes unrealized', f"{NUM['MutFamiliesCaught']}/{len(r['B3'])}"),
        (f"Fixtures ({fx['n']} minimal ontologies, one stated assumption each)", 'outcome as fixed by construction; \\vd{Conflict} $\\Leftrightarrow$ inconsistent under OWL~2~DL', f"{fx['audit_as_expected']}/{fx['n']}; {fx['prediction_agrees']}/{fx['n']} ({fx['inconsistent']} inconsistent fixtures)"),
        ('Root classes (13 $\\times$ 4 versions $\\times$ 2 bases)', 'flagged', f"{r['C1']['false_positives']}/{r['C1']['checks']}"),
        (f"Annotation removed ({r['C2']['mutants']} mutants of v2.2)", 'audit result changes', f"{r['C2']['changed']}/{r['C2']['mutants']}"),
        (f"External ontologies ({len(ext)})", '\\vd{Disconnected} / \\vd{Suspect} / mismatches', f"{NUM['ExtDisconnected']} / {NUM['ExtSuspect']} / {NUM['ExtMismatches']}"),
        (f"DL name ({r['D_agreement'][1]} ontologies)", 'same as OWL~API construct report', f"{r['D_agreement'][0]}/{r['D_agreement'][1]}"),
    ]
    write('tab_selectivity.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{Selectivity of the audit (\\texttt{scripts/audit\\_selectivity.py}, \\texttt{scripts/audit\\_fixtures.py}). Mutants and fixtures have ground truth by construction; the last four rows are negative controls and cross-checks.}',
        '\\label{tab:selectivity}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{>{\\raggedright\\arraybackslash}p{5.6cm}>{\\raggedright\\arraybackslash}p{4.6cm}>{\\raggedright\\arraybackslash}p{6.2cm}}', '\\hline',
        '\\textbf{Input} & \\textbf{Outcome counted} & \\textbf{Result} \\\\', '\\hline',
        *[f'{a} & {b} & {c} \\\\' for a, b, c in rows], '\\hline', '\\end{tabular}', '\\end{table*}', '']))


# --------------------------------------------------------------- scalability
def scalability():
    plats = [p for p in ['A', 'B'] if (RESULTS / f'E6_scalability_{p}.jsonl').exists()]
    data = {p: [json.loads(l) for l in (RESULTS / f'E6_scalability_{p}.jsonl').read_text().splitlines()] for p in plats}
    if len(plats) == 2:
        a = {(r['topology'], r['size'], r['seed']): r for r in data['A']}; b = {(r['topology'], r['size'], r['seed']): r for r in data['B']}
        assert set(a) == set(b) and all((a[k]['triples'], a[k]['individuals'], a[k]['requer_edges'], a[k]['closure_pairs']) ==
                                        (b[k]['triples'], b[k]['individuals'], b[k]['requer_edges'], b[k]['closure_pairs']) for k in a)
    rows0 = data[plats[-1]]
    body = []
    f = lambda xs: f'{st.mean(xs):.2f} [{min(xs):.2f}--{max(xs):.2f}]'
    for si in range(5):
        rs0 = [r for r in rows0 if r['size'] == si]
        tri = f"{thousands(min(r['triples'] for r in rs0))}--{thousands(max(r['triples'] for r in rs0))}"
        cells = []
        for p in plats:
            rs = [r for r in data[p] if r['size'] == si]
            warm = [x['reasoning_ms'] / 1000 for r in rs for x in r['hermit'] if x['phase'] == 'warm']
            proc = [r['process_wall_s'] for r in rs]
            cells += [f(warm), f(proc)]
        body.append(f"{thousands(rs0[0]['individuals'])} & {tri} & " + ' & '.join(cells) + ' \\\\')
    hdr1 = ' & '.join(f'\\multicolumn{{2}}{{c}}{{\\textbf{{Platform {p}}}}}' for p in plats)
    hdr2 = ' & '.join('\\textbf{reasoning} & \\textbf{whole process}' for _ in plats)
    n_bases = len([r for r in rows0 if r['size'] == 0])
    write('tab_scal.tex', '\n'.join([
        '\\begin{table*}[!t]',
        '\\caption{HermiT on synthetic fact bases laid under v2.2: ' + str(n_bases) + ' bases per size (four prerequisite topologies, five seeds). Seconds, mean [min--max]. \\emph{Reasoning}: consistency, classification and realization, timed inside the JVM on warm repetitions. \\emph{Whole process}: wall-clock of one process, including JVM start-up, parsing, and a check of consistency and class satisfiability. Counts of triples, individuals, prerequisite edges and closure pairs are identical on both platforms for all ' + str(len(rows0)) + ' bases.}',
        '\\label{tab:scal}', '\\centering', '\\footnotesize',
        '\\begin{tabular}{rr' + 'cc' * len(plats) + '}', '\\hline',
        '& & ' + hdr1 + ' \\\\',
        '\\textbf{Individuals} & \\textbf{Triples} & ' + hdr2 + ' \\\\', '\\hline',
        *body, '\\hline', '\\end{tabular}', '\\end{table*}', '']))
    for p in plats:
        rs = [r for r in data[p] if r['size'] == 4]
        warm = [x['reasoning_ms'] / 1000 for r in rs for x in r['hermit'] if x['phase'] == 'warm']
        cold = [x['reasoning_ms'] / 1000 for r in rs for x in r['hermit'] if x['phase'] == 'cold']
        num('ScalWarmLargest' + p, f'{st.mean(warm):.2f}'); num('ScalWarmLargestMin' + p, f'{min(warm):.2f}'); num('ScalWarmLargestMax' + p, f'{max(warm):.2f}')
        num('ScalColdLargest' + p, f'{st.mean(cold):.2f}')
        num('ScalProcLargest' + p, f"{st.mean(r['process_wall_s'] for r in rs):.2f}")
        rs0 = [r for r in data[p] if r['size'] == 0]
        num('ScalWarmSmallest' + p, f"{st.mean(x['reasoning_ms'] / 1000 for r in rs0 for x in r['hermit'] if x['phase'] == 'warm'):.2f}")
        num('ScalProcSmallest' + p, f"{st.mean(r['process_wall_s'] for r in rs0):.2f}")
        fl = J(f'E6_jvm_floor_{p}.json')['process_wall_s_v2.2_native_abox']
        num('ScalFloor' + p, f'{st.mean(fl):.2f}')
        clo = {r['topology']: r for r in data[p] if r['size'] == 4 and r.get('hermit_closure')}
        for topo in ('chain', 'dense'):
            num('Closure' + topo.capitalize() + p, f"{clo[topo]['hermit_closure'][-1]['closure_ms'] / 1000:.1f}")
            num('Path' + topo.capitalize() + p, f"{clo[topo]['path_query_s']:.2f}")
        v1 = [x['reasoning_ms'] / 1000 for r in rs if r.get('hermit_v1_schema') for x in r['hermit_v1_schema'] if x['phase'] == 'warm']
        v2 = [x['reasoning_ms'] / 1000 for r in rs if r.get('hermit_v1_schema') for x in r['hermit'] if x['phase'] == 'warm']
        num('ScalSchemaOne' + p, f'{st.mean(v1):.2f}'); num('ScalSchemaTwoTwo' + p, f'{st.mean(v2):.2f}')
    rs = [r for r in rows0 if r['size'] == 4]
    num('ScalIndividuals', thousands(rs[0]['individuals']))
    num('ScalTriplesMin', thousands(min(r['triples'] for r in rs))); num('ScalTriplesMax', thousands(max(r['triples'] for r in rs)))
    num('ScalBases', len(rows0))
    num('ClosurePairsChain', thousands(next(r['closure_pairs'] for r in rs if r['topology'] == 'chain' and r['seed'] == 1)))
    num('ClosurePairsDense', thousands(next(r['closure_pairs'] for r in rs if r['topology'] == 'dense' and r['seed'] == 1)))
    B = data.get('B', rows0)
    rl = lambda topo, si: st.mean(r['owlrl_s'] for r in B if r['topology'] == topo and r['size'] == si and 'owlrl_s' in r)
    num('RlChainMid', f"{rl('chain', 2):.1f}"); num('RlDenseMid', f"{rl('dense', 2):.1f}"); num('RlChainSmall', f"{rl('chain', 0):.1f}")
    num('RlTriplesMid', thousands(int(round(st.mean(r['triples'] for r in B if r['size'] == 2), -2))))
    env = {p: J(f'E6_environment_{p}.json') for p in plats}
    (GEN / 'environments.json').write_text(json.dumps(env, indent=1))


def pipeline():
    """Wall-clock time of the deterministic part of scripts/run_all.sh on platform B."""
    import re
    log = (RESULTS / 'run_all_B.log').read_text()
    total = int(re.search(r'deterministic experiments, total\s+(\d+) s', log).group(1))
    steps = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r'^(.*?)\s+(\d+) s$', log, re.M)}
    num('PipelineSecondsB', total); num('PipelineMinutesB', round(total / 60))
    num('PipelineLongestStepSecondsB', max(v for k, v in steps.items() if not k.startswith('deterministic')))


WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']


def numbers():
    # small counts are also available spelled out (\N<Name>Word), for use in running text
    for k, v in list(NUM.items()):
        if str(v).isdigit() and int(v) < len(WORDS):
            NUM[k + 'Word'] = WORDS[int(v)]
    lines = ['% numbers.tex - generated by scripts/paper_assets.py from results/. Do not edit.']
    for k, v in NUM.items():
        lines.append(f'\\newcommand{{\\N{k}}}{{{v}}}')
    write('numbers.tex', '\n'.join(lines) + '\n')
    (GEN / 'numbers.json').write_text(json.dumps(NUM, indent=1))


if __name__ == '__main__':
    releases(); classes(); delta(); claims(); candidates(); lineage(); ablation(); tests(); cqs(); shacl_tab(); faults(); selectivity(); scalability(); pipeline(); numbers()
    print(f'{len(NUM)} numbers and {len(list(GEN.glob("tab_*.tex")))} tables written to {GEN}')
