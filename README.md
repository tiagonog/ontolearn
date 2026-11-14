# OntoLearn: A Formal Ontology for Competency-Based Learning Analytics

Research artifacts for two papers by the same authors (CIn/UFPE):

1. **"OntoLearn: A Formal Ontology for Competency-Based Learning Analytics and Semantic Modeling"** — SBIE 2026, pp. 44–56, [doi:10.5753/sbie.2026.25639](https://doi.org/10.5753/sbie.2026.25639). Introduces the ontology (**v1.0**, file `ontology/ontolearn.owl`).
2. **"Closing the Report–Artifact Gap in an Ontology for Competency-Based Learning Analytics"** — under review (revised version). Audits v1.0 against its published description, releases the completed versions **v2.0, v2.1 and v2.2**, and measures what the completion contributes. Every number in that paper is produced by the scripts in `scripts/` from the files in this repository.

OntoLearn is an OWL 2 DL domain ontology for modeling the Knowledge, Skills, and Attitudes (KSA) triad, proficiency levels, and prerequisite chains in competency-based Learning Analytics.

Base namespace: `http://www.ontolearn.com/ontologia#` (unchanged across versions).

---

## Releases

| Version | File | Triples | Logical axioms | What it is |
|---|---|---|---|---|
| **v1.0** | `ontology/ontolearn.owl` | 699 | 294 | The artifact described in the SBIE 2026 paper. Never modified. |
| **v2.0** | `ontology/ontolearn-v2.owl`, `.ttl` | 765 | 313 | Axiomatic completion: 19 logical axioms in six families, generated from v1.0 by `scripts/build_v2.py`. |
| **v2.1** | `ontology/ontolearn-v2.1.owl`, `.ttl` | 791 | 314 | Revision of v2.0 after an OOPS! scan and a plausibility evaluation; generated from v2.0 by `scripts/build_v2_1.py`. Presented in the doctoral thesis. |
| **v2.2** | `ontology/ontolearn-v2.2.owl`, `.ttl` | 805 | 315 | **Current version.** v2.1 plus one axiom, generated from v2.1 by `scripts/build_v2_2.py`. |

All four are OWL 2 DL ontologies with 29 classes, 27 data properties and 20 named individuals (48 object properties in v1.0, 50 from v2.0 on). The SHA-256 digest of every input file (releases, development states, fact base, queries, answer key, shapes, claims) is in `scripts/LOCK.sha256`; every script checks the digest of a file before reading it, and `scripts/run_all.sh` verifies the whole table before its first step.

### What v2.2 adds

One axiom: `owl:AllDisjointClasses` over the six categories of the revised Bloom taxonomy (`Lembrar`, `Entender`, `Aplicar`, `Analisar`, `AvaliarBloom`, `Criar`).

Why. From v2.0 on, `:proficienciaAtingida` is functional. OWL makes no unique-name assumption, so a performance record linked to two level individuals was **not** inconsistent in v2.0 and v2.1: the reasoner concluded that the two levels were the same individual (`NP-Aplicar = NP-Lembrar`). With the six categories disjoint, two levels of different categories are necessarily different, and such a record is inconsistent. This was pointed out in the peer review of the audit paper and is reproduced by `scripts/java/AxiomTests.java` (tests S10–S12).

v2.2 also ships four SHACL shapes (`shapes/ontolearn-shapes.ttl`) for the requirements that OWL axioms cannot enforce on data: a question has at least one recorded competency, an assessment at least one recorded question, a performance record at least one and at most one recorded level. An existential axiom such as `Questao ⊑ ∃competenciasAvaliadas.Competencia` states that a competency exists; it does not check that one was recorded.

---

## Repository contents

| Folder | Contents |
|---|---|
| `ontology/` | The four releases (RDF/XML; from v2.0 on also Turtle) |
| `ontology/versions/` | The twelve files preserved during development (v0–v11; ten distinct states) |
| `shapes/` | SHACL shapes released with v2.2 |
| `claims/` | `sbie2026.json`: the 15 structural claims of the SBIE paper, each with the passage that makes it; `audit-paper-v2.2.json`: the claims the audit paper makes about v2.2 |
| `scripts/` | The audit pipeline (see **Reproducing the audit paper**) |
| `scripts/first-submission/` | The scripts of release v2.0.0, kept for the record (see **Errata**, part B) |
| `results/` | Output of every experiment, as produced by `scripts/run_all.sh` |
| `paper/` | Generated tables, numbers and figures of the audit paper (plus a per-case table of the competency-question suite and a lineage figure that the paper does not include) |
| `verification/` | Verification material of v2.1 reported in the thesis: axiom unit tests, competency-question queries with their answer key, test ABox, OOPS! diagnoses (documented in Portuguese) |
| `competency-questions/` | The 8 Competency Questions (CQs) used as functional requirements |
| `sparql/` | The SPARQL queries as deposited with the SBIE paper (`cq1.rq` … `cq8.rq`) — see **Errata**, part A |
| `validation/` | Prompt template used with Gemini 3 (PT-BR original + EN translation) |
| `slr-protocol/` | Systematic Literature Review protocol |

---

## Reproducing the audit paper

Requirements: Python 3.10 or later, Java 11 or later, and network access for the one-time set-up (a Python virtual environment is recommended).

```bash
python3 -m venv .venv && . .venv/bin/activate
bash scripts/setup_env.sh          # Python packages (pinned) and the Java libraries, into ./jars
bash scripts/run_all.sh            # every experiment; an optional argument labels your platform (default: local)
```

The labels `A` and `B` are those of the two platforms of the paper. With any other label the released timing files (`results/E6_*_A.*`, `results/E6_*_B.*`, `results/run_all_B.log`, `results/E7_audit_timing_B.json`) are left untouched, so the tables and numbers regenerated in `paper/gen/` should be identical to the released ones.

`run_all.sh` verifies the digest of every input file, writes its outputs to `results/`, regenerates the tables, numbers and figures of the paper in `paper/`, and logs the time of each step. The deterministic experiments take about 24 minutes on a two-core x86-64 machine, most of it in the fault-injection experiment (E5); set `ONTOLEARN_SKIP_E6=1` to leave out the scalability experiment, which adds about half an hour and is resumable. Every consistency verdict and every entailment census is computed with both HermiT and Openllet, and a script aborts if the two disagree.

Everything except timings is deterministic: the files in `results/` should be reproduced byte for byte. They were, in repeated runs on the platform that produced them (x86-64, OpenJDK 21, Python 3.13), in a clean copy of the repository with a new virtual environment, and, for every experiment except E5, on a second platform (ARM64, OpenJDK 11, Python 3.10).

| Experiment | Script | Output | What it shows |
|---|---|---|---|
| E0 | `check_release_equivalence.py`, `profiles.py` | `E0_*.txt` | Each build script reproduces the next release from the previous one; the serializations are isomorphic; the ABox is the same in the four releases; all releases are in OWL 2 DL, none in OWL 2 RL |
| audit | `audit.py`, `report_vocabulary.py` | `audit_*` | Construct inventory, claim check, isolated classes (two stages), domain/range mismatches; no reasoner needed. The second script checks the vocabulary that the SBIE 2026 paper merely names (classes, properties, individuals, signatures, subclass links, assertions), which the count of claims leaves out |
| E1 | `ablation.py` | `E1_ablation.*` | Consistency of 24 configurations; entailment census (what each axiom family derives) under OWL 2 DL (HermiT and Openllet) and OWL 2 RL |
| E2 | `java/AxiomTests.java` | `E2_axiom_tests.tsv` | 21 semantic tests on the four releases with HermiT and Openllet |
| E3 | `cq_suite.py` | `E3_cq_suite.*` | The deposited queries and a corrected suite of 20 cases under three inference regimes; which axioms each question exercises |
| E4 | `shacl_validate.py` | `E4_shacl.*` | OWL verdict beside SHACL verdict on the same data |
| E5 | `faults.py` | `E5_faults.*` | 11 kinds of fault and 3 legitimate variations injected into 20 synthetic fact bases |
| E6 | `scalability.py` | `E6_*` | Reasoning time by size and prerequisite topology, per platform, separated from JVM start-up |
| E7 | `audit_selectivity.py`, `audit_fixtures.py`, `audit_timing.py` | `E7_*` | Mutants, negative controls and ten external ontologies (downloaded by `fetch_external.py` from commit-pinned URLs, not redistributed here); 16 minimal ontologies that exercise the stated assumptions of the audit one at a time, with outcomes fixed by construction and compared with the two reasoners |
| E8 | `lineage.py` | `E8_*` | The audit applied to the preserved development states; the values that the SBIE 2026 paper tabulates for four milestones, compared with the preserved files |

Main results: over identical facts v1.0 entails 41 atomic assertions that are not asserted and v2.2 entails 45, the four additional ones in vocabulary that v1.0 does not have; the corrected competency-question suite is already satisfied by v1.0; with OWL reasoning v1.0 notices none of the 11 kinds of injected fault and v2.2 notices six, or nine together with the SHACL shapes. The completion adds almost no derivation; what it adds is the rejection of faulty data.

---

## Errata

### A. v1.0 and its description in the SBIE 2026 paper

The audit checked, on `ontology/ontolearn.owl`, the 15 claims that the paper makes about the expressivity of the artifact, the kinds of construct it uses and its entity counts, and the one specialization it states in words (`python3 scripts/audit.py ontology/ontolearn.owl --claims claims/sbie2026.json`). Of the 15 claims, 7 are realized and 8 are not. The paper also names 76 items of vocabulary in its figures and prompt listing (classes, properties, individuals, signatures, subclass links, assertions); these are not counted as claims, and 75 of them hold of the file, the exception being the link from `Subjetiva` to `Questao` (`scripts/report_vocabulary.py`). The file itself is left unmodified, because it is the artifact the published paper describes.

| Claim | Measured in `ontolearn.owl` |
|---|---|
| DL expressivity `ALCHIF(D)` | **`SIF(D)`**. No `rdfs:subPropertyOf` axiom, so the `H` is unrealized; transitive roles require `S`, not `ALC`. (v2.x is `SHIF(D)`.) |
| KSA disjointness enforced pairwise | **Absent.** The file has two `owl:disjointWith` axioms, neither about Knowledge, Skill or Attitude. Present in two early development states and lost in a refactoring (see **Version evolution**); restored in v2.0. |
| Existential restrictions; qualified cardinality; `hasScoreValue` | **Absent.** No `owl:Restriction`, no cardinality axiom, no score-valued data property. Existential restrictions were added in v2.0; qualified cardinality and a score property exist in no version. |
| `Questao` specialized into `Objetiva` and `Subjetiva` | **One of two links.** `Subjetiva` has no `rdfs:subClassOf` link to `Questao` (defect D1, repaired in v2.0). |
| ABox of 40 individuals | **20.** |

Two further defects. D1 (above): a query over the asserted class hierarchy returns two of the three question individuals; under a reasoner the range of `questaoRespondida` still classifies the third one as a question, so the defect is visible mainly to consumers that do not reason. D2: the union domain of `:descricao` omits `NiveisDeProficiencia`, which the ABox nevertheless uses; repaired in v2.0.

**Deposited SPARQL queries.** The eight queries in `sparql/` are preserved as deposited. Executed on any of the four releases, with or without inference, **all eight return the empty set** (`results/E3_cq_suite.txt`). They bind learners and competencies through `rdfs:label`, which no learner or competency carries (names are in `:nome`); they write literals without diacritics; five use properties that the ontology does not declare (`:competenciaAvaliada`, `:temQuestao`, `:acessouRecurso`); and one uses the class `:Aplicar` where a level individual is required. The working queries, with an answer key, are in `verification/sparql/` and `verification/dados/gabarito_qcs.json`.

**Evolution table.** The paper tabulates four milestones of the development (its Table 3). Against the preserved files, 11 of the 13 values given for the three earlier milestones agree; the paper gives 55 classes at v2, where 50 are declared, and 32 individuals at v6, where 16 are declared (`results/E8_lineage.txt`).

**OOPS! diagnosis.** The pitfall-free scan was obtained on a development state (`verification/dados/ciclos_oops.csv`). The released v1.0 file, scanned on 18 October 2026, shows pitfalls P04 and P08 on `Subjetiva` (`verification/relatorios/oops_2026-10-18/`).

### B. Release v2.0.0 of this repository (first submission of the audit paper)

The scripts of that release are kept in `scripts/first-submission/`. Peer review and our own re-analysis found the following errors, all corrected in the present pipeline.

| Statement or script in v2.0.0 | Correction |
|---|---|
| `ablation.py` rebuilt "v2.0" in memory | The rebuilt graph was not the released file: it lacked five triples (760 instead of 765), among them the domain axiom of `:temComponenteKSA`. `check_release_equivalence.py` reproduces the difference. No script rebuilds a version any more. |
| "v2.0 entails 10.2% more domain-relevant triples than v1.0 (919 vs 834)" | Withdrawn. The two closures were taken on graphs with different schema and vocabulary, and most of the difference is schema-level triples. The controlled measure is the entailment census of `ablation.py`. |
| "Functional `:proficienciaAtingida` makes contradictory grading detectable" | False in v2.0 and v2.1 (see **What v2.2 adds**). True from v2.2 on. |
| "Disjointness was never introduced in the lineage" | False. The first inventory counted only `owl:disjointWith`. States v2 and v3 contain seven `owl:AllDisjointClasses` axioms, lost at v4. |
| The audit algorithm labelled every isolated class a defect | It labelled seven legitimate root concepts together with `Subjetiva`. `audit.py` now treats isolated classes as candidates and requires independent evidence. |
| "Audit script released" | It was not in the deposit. It is `scripts/audit.py`. |
| HermiT times of about one second on the 20-individual ABox | Those were start-up times of the Java virtual machine. `scalability.py` times reasoning inside the JVM. |
| v2.0 itself | Over-constrained: it rejected an attitude with a description, a dated performance record, and an instructor enrolled as a learner. Corrected in v2.1. |

---

## Version evolution

Twelve files were preserved during development; content hashing reduces them to ten distinct states (v5 = v7 and v9 = v11 are byte-identical). v0 is a text export of a class tree, not an RDF document. Measured by `scripts/lineage.py`:

| State | Classes | Object prop. | Data prop. | Inverse axioms | Disjointness axioms | Individuals |
|---|---|---|---|---|---|---|
| v1 | 12 | 18 | 0 | 0 | 0 | 0 |
| v2 | 50 | 26 | 0 | 4 | 7 | 0 |
| v3 | 50 | 27 | 0 | 4 | 7 | 0 |
| v4 | 41 | 27 | 27 | 3 | 0 | 0 (+13 undeclared) |
| v5 = v7 | 41 | 41 | 27 | 3 | 0 | 16 |
| v6 | 28 | 48 | 27 | 24 | 2 | 16 |
| v8 | 28 | 48 | 27 | 24 | 2 | 16 |
| v9 = v11 | 28 | 48 | 27 | 24 | 2 | 16 (+3 undeclared) |
| v10 = v1.0 | 29 | 48 | 27 | 24 | 2 | 20 |

No state contains a sub-property axiom, a class restriction, or a cardinality constraint: those were never introduced before v2.0. Disjointness is different: the seven n-ary axioms of v2–v3 (the thirteen root concepts, the six Bloom categories, objective/subjective questions, and others) disappear at v4, and only two binary axioms return at v6. The highest-numbered file, v11, is identical to v9 and is not the final artifact.

---

## Key modeling notes

- `:requer` (Competencia → Competencia) is declared `owl:TransitiveProperty`; `:ehRequeridaPor` is its declared inverse (also transitive). OWL 2 DL does not allow a transitive property to be declared irreflexive or asymmetric, so a prerequisite cycle is not an inconsistency; check it with `ASK { ?c :requer+ ?c }`.
- The thirteen root concepts are pairwise disjoint from v2.0 on. This is a scope decision: typing one individual as, for example, both an assessment and a learning resource makes a v2.x base inconsistent. The partition is a single axiom and can be replaced by a smaller one.
- All data in this repository are synthetic. No real student data is included.
- The releases retain the legacy IRI for artifact continuity.

---

## Citation

For the ontology and its original description:

> Nogueira, T. J. D. D.; Lima, R. M. F.; Nogueira, J. C. A. (2026). OntoLearn: A Formal Ontology for Competency-Based Learning Analytics and Semantic Modeling. In: *Anais do XXXVII Simpósio Brasileiro de Informática na Educação (SBIE 2026)*, pp. 44–56. SBC. doi:10.5753/sbie.2026.25639

## License

- Ontology, datasets and scripts: CC BY 4.0
- Documentation: CC BY 4.0

## AI Disclosure

Generative AI tools were used as technical and language assistants in this research, under the direction of the authors. In the development of v1.0, Google Gemini 3 (extended-reasoning mode, accessed November 2025) supported the translation of the competency questions into SPARQL and a pilot assessment of the plausibility of axioms, under a human-in-the-loop paradigm. In the plausibility evaluation that preceded v2.1, Gemini, ChatGPT and DeepSeek acted as judges. Anthropic Claude supported the preparation and the execution of the scripts, queries and test data in `scripts/` and `verification/`, the generation of versions 2.1 and 2.2 of the ontology from the revisions decided by the authors, and the generation of the tables and figures in `paper/`. The modeling decisions, the interpretation of the results and the content of this repository are the responsibility of the authors. The pipeline is released so that every result can be re-executed and checked without AI assistance.
