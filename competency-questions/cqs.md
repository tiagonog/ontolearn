# Competency Questions (CQs)

The eight CQs act as formal functional requirements for OntoLearn, derived from the Systematic Literature Review. Each CQ has a corresponding final SPARQL query in `../sparql/`.

| ID | English | Português (original) |
|---|---|---|
| CQ1 | Which specific competencies has a given learner demonstrated? | Quais competências específicas um determinado aprendiz já demonstrou? |
| CQ2 | What is the proficiency level (Bloom's Taxonomy) achieved by a learner in a specific competency? | Qual o nível de proficiência (Bloom) alcançado por um aprendiz em uma competência específica? |
| CQ3 | Which assessments in the VLE are mapped to evaluate competency "X"? | Quais avaliações disponíveis no AVA estão mapeadas para testar a competência "X"? |
| CQ4 | What are the direct and indirect prerequisites required to start competency "Y"? | Quais são os pré-requisitos (diretos e indiretos) necessários para iniciar a competência "Y"? |
| CQ5 | Which learning resources address competency "Z"? | Quais recursos de aprendizagem (vídeos, textos, jogos) abordam a competência "Z"? |
| CQ6 | Which learners have reached the "Apply" proficiency level in "Programming"? | Quais aprendizes atingiram o nível de proficiência "Aplicar" em competências da área de Programação? |
| CQ7 | What are the URLs of resources accessed by a learner in their development history for a specific competency? | Quais foram as URLs dos recursos acessados por um aprendiz no seu histórico para uma competência? |
| CQ8 | Is there a disparity between the learner's proficiency in objective versus subjective assessment tasks? | Existe disparidade entre o nível de proficiência do aprendiz em questões objetivas e subjetivas? |

## Validation outcome

All eight CQs were answered successfully in the final validation cycle (100% functional coverage), after an iterative test–fail–refine process. Initial failures and corrective actions:

- **CQ4**: returned only direct prerequisites → `:requer` redefined as `owl:TransitiveProperty`.
- **CQ8**: empty results → `Questao` refactored with `Objetiva`/`Subjetiva` subclasses for granularity.
- **CQ2/CQ3**: metadata inconsistencies → label normalization (systematic use of `STR()`).
- **CQ7**: underpopulated ABox → learning-history instances enriched.
