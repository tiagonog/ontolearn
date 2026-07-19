# OntoLearn: A Formal Ontology for Competency-Based Learning Analytics

Research artifacts for the paper **"OntoLearn: A Formal Ontology for Competency-Based Learning Analytics and Semantic Modeling"** (SBIE 2026) and the associated PhD thesis (CIn/UFPE).

OntoLearn is an OWL 2 DL ontology (ALCHIF(D) expressivity, as classified by Protégé) for modeling the Knowledge, Skills, and Attitudes (KSA/CHA) triad, proficiency levels, and prerequisite chains in competency-based Learning Analytics.

## Repository contents

| Folder | Contents |
|---|---|
| `ontology/` | `ontolearn.owl` — final version (v10, OWL/RDF-XML), validated with HermiT 1.4.3 and OOPS! |
| `ontology/versions/` | Milestone versions documenting the refinement trajectory (v0, v2, v6) |
| `competency-questions/` | The 8 Competency Questions (CQs) used as functional requirements |
| `sparql/` | Final SPARQL queries answering each CQ (`cq1.rq` … `cq8.rq`) |
| `validation/` | Prompt template used with Gemini 3 (PT-BR original + EN translation) and validation notes |
| `slr-protocol/` | Systematic Literature Review protocol (databases, search strings, inclusion/exclusion criteria, QA) |

## How to use

1. Open `ontology/ontolearn.owl` in [Protégé](https://protege.stanford.edu/) 5.5+.
2. Activate the **HermiT** reasoner (Reasoner → HermiT → Start reasoner) to materialize inferences (e.g., transitive prerequisite chains via `:requer`).
3. Run the queries in `sparql/` using the SPARQL Query tab (results depend on inferred knowledge — keep the reasoner active).

Base namespace: `http://www.ontolearn.com/ontologia#`


## Version evolution

The ontology was consolidated through iterative OOPS!/SAMOD refinement cycles. Milestone metrics (from Protégé):

| Metric | v0 (initial) | v2 | v6 (post-OOPS!) | v10 (final) |
|---|---|---|---|---|
| Classes | 82 | 55 | 28 | 29 |
| Object properties | — | 26 | 48 | 48 |
| Data properties | — | 0 | 27 | 27 |
| Inverse properties | — | 4 | 24 | 24 |
| Transitive properties | — | 1 | 2 | 2 |
| Individuals (test ABox) | 0 | 0 | 32 | 40 |

v0 enumerated entire knowledge domains and ISCED education levels as classes; successive cycles (OOPS! pitfalls P04, P08, P11, P13, P20, P41) replaced this enumerative taxonomy with a leaner, domain-agnostic relational core. Milestone files are in `ontology/versions/`.

## Key modeling notes

- `:requer` (Competencia → Competencia) is declared `owl:TransitiveProperty`; `:ehRequeridaPor` is its declared inverse (also transitive). In the paper, `:ehRequeridaPor` is presented as *isPrerequisiteOf* for readability.
- KSA disjointness is enforced pairwise: Knowledge ⊓ Skill ⊑ ⊥, Knowledge ⊓ Attitude ⊑ ⊥, Skill ⊓ Attitude ⊑ ⊥.
- The ABox contains only **synthetic instances** generated from the schema's constraints. No real student data is included.

## Citation

If you use these artifacts, please cite the SBIE 2026 paper:

> Nogueira, T. J. D. D.; Lima, R. M. F.; Nogueira, J. C. A. (2026). OntoLearn: A Formal Ontology for Competency-Based Learning Analytics and Semantic Modeling. In: *Anais do XXXVII Simpósio Brasileiro de Informática na Educação (SBIE 2026)*. SBC.

## License

- Ontology and datasets: CC BY 4.0
- Documentation: CC BY 4.0

## AI Disclosure

Google Gemini 3 (extended-reasoning mode, accessed November 2025) was used as a methodological assistant for translating CQs into SPARQL and for semantic plausibility assessment of axioms, under a human-in-the-loop paradigm. All outputs were executed, verified, and corrected by the authors. See `validation/prompt-template.md`.
