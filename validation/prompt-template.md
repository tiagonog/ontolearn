# Gemini 3 Prompt Template — Functional Validation

Model: Google Gemini 3, extended-reasoning mode. Accessed via web interface, November 2025, default generation parameters.

All generated queries were executed in Protégé 5.5.0 with the HermiT 1.4.3 reasoner active, and manually verified by the authors against a gold-standard answer set defined prior to query generation (human-in-the-loop).

## Original prompt (PT-BR, as used)

```
Você é um especialista em Web Semântica e um programador experiente
na linguagem de consulta SPARQL.

## Contexto da Ontologia OntoLearn:
A ontologia descreve o domínio de Learning Analytics baseado em
competências. As classes principais são: 'Aprendiz', 'Competencia',
'DesempenhoDoAprendiz', 'RecursoDeAprendizagem', 'Avaliacao' e
'Questao' (com subclasses 'Objetiva' e 'Subjetiva').
As propriedades principais incluem:
- :desempenhoCompetencias (Aprendiz -> DesempenhoDoAprendiz)
- :proficienciaAtingida (DesempenhoDoAprendiz -> NiveisDeProficiencia)
- :questaoRespondida (DesempenhoDoAprendiz -> Questao)
- :competenciasAvaliadas (Questao -> Competencia)
- :requer (Competencia -> Competencia, Transitiva)
- :abordaCompetencia (RecursoDeAprendizagem -> Competencia)
O prefixo base é : <http://www.ontolearn.com/ontologia#>

## Tarefa:
Traduza a seguinte Pergunta de Competência (CQ), que está em
linguagem natural, para uma consulta SPARQL executável. Utilize o
comando STR() para comparar rótulos (labels) se necessário.
Retorne apenas o bloco de código SPARQL.

## Pergunta de Competência (CQ):
[CQ inserida aqui — ver ../competency-questions/cqs.md]
```

## English translation (for reference)

```
You are an expert in Semantic Web and an experienced SPARQL programmer.

## OntoLearn Ontology Context:
The ontology describes the domain of competency-based Learning
Analytics. Main classes: 'Aprendiz' (Learner), 'Competencia'
(Competency), 'DesempenhoDoAprendiz' (LearnerPerformance),
'RecursoDeAprendizagem' (LearningResource), 'Avaliacao' (Assessment),
and 'Questao' (Question; subclasses 'Objetiva', 'Subjetiva').
Main properties:
- :desempenhoCompetencias (hasPerformance)
- :proficienciaAtingida (achievedProficiency)
- :questaoRespondida (answeredQuestion)
- :competenciasAvaliadas (evaluatesCompetency)
- :requer (requires, Transitive)
- :abordaCompetencia (addressesCompetency)
Base prefix: <http://www.ontolearn.com/ontologia#>

## Task:
Translate the following Competency Question (CQ), given in natural
language, into an executable SPARQL query. Use STR() to compare
labels if necessary. Return only the SPARQL code block.

## Competency Question (CQ): [CQ inserted here]
```

## Semantic plausibility assessment

The structural axioms were additionally submitted to Gemini 3 for plausibility rating on a 1–5 Likert scale (mean 4.8/5). Constructive remarks (e.g., annotation enrichment suggestions) were incorporated into the final model.
