# Material de verificação e validação da OntoLearn v2.1

Esta pasta reproduz as verificações e a validação funcional da OntoLearn v2.1 relatadas no Capítulo 5 e no
Apêndice G da tese *OntoLearn: Uma Ontologia para Análise de Aprendizagem Baseada em Competências*
(CIn/UFPE, 2026). Ela segue a organização do material suplementar da tese, de modo que os comandos do
Apêndice G podem ser executados a partir daqui; por isso, contém cópias dos arquivos da ontologia, idênticas
às da pasta `ontology/` do repositório.

## Conteúdo

| Pasta | O que contém |
|---|---|
| `ontologia/` | `ontolearn-v2.1.owl` e `ontolearn-v2.1.ttl` (versão 2.1), `ontolearn-v2.owl` (versão 2.0, entrada de `build_v2_1.py`), `ontolearn-abox-teste.ttl` (base de teste sintética, que importa a versão 2.1) e `catalog-v001.xml` (resolve o `owl:imports` para o arquivo local da versão 2.1) |
| `sparql/` | as consultas das oito questões de competência (`qc1.rq` a `qc8.rq`, com duas formas para a QC4) |
| `dados/` | gabarito das QCs (`gabarito_qcs.json`, registrado em 11/10/2026, antes da execução das consultas), resultados das QCs (`resultados_qcs.csv`), testes de unidade dos axiomas (`testes_axiomas.tsv`), ciclos do OOPS! (`ciclos_oops.csv`), conferência de anotações e licença (`verificacao_anotacoes.json`) e bases materializadas em `bases/` |
| `relatorios/` | perfis OWL 2 e satisfatibilidade, execução das QCs, conferência de anotações e diagnósticos do OOPS!: versões 1.0 e 2.0 pelo serviço web (`oops_2026-10-18/`) e versão 2.1 pelo código-fonte do OOPS! executado localmente (`oops_2026-10-27/`, com o `LEIAME.md` que descreve o procedimento) |
| `scripts/` | `build_v2_1.py` (versão 2.1 a partir da 2.0), `executa_qcs.py`, `verifica_anotacoes.py`, `java/` (testes de unidade dos axiomas, perfis e satisfatibilidade) e `oops/` (compilação e execução local do OOPS!) |

## Requisitos

- Java 21 (os arquivos `.java` são executados diretamente, sem compilação prévia)
- Python 3 com `rdflib` 7.6.0
- ROBOT 1.9.6 (`robot.jar`, disponível nas versões publicadas do projeto ROBOT no GitHub)
- Bibliotecas Java em uma pasta `jars/`: OWL API 5.1.9, HermiT 1.4.3.517 e Openllet 2.6.5, com suas
  dependências. As mesmas versões acompanham o pacote Python `owlapy` 1.5.0 (`pip download owlapy==1.5.0`,
  pasta de dependências Java do pacote).
- Para o OOPS!: `git`, `zip` e acesso ao GitHub, de onde `scripts/oops/compila_oops.sh` obtém o código-fonte do
  OOPS! e de suas dependências.

## Comandos

Executados a partir desta pasta:

```
# 0. Versão 2.1 a partir da versão 2.0 (cada alteração é listada pelo script)
python3 scripts/build_v2_1.py ontologia/ontolearn-v2.owl \
        ontologia/ontolearn-v2.1.ttl ontologia/ontolearn-v2.1.owl

# 1. Bases: referência (o próprio arquivo da v2.1) e ampliada
#    (v2.1 + ABox de teste; o catálogo resolve o owl:imports)
cp ontologia/ontolearn-v2.1.owl dados/bases/base_referencia.owl
robot merge --catalog ontologia/catalog-v001.xml \
      --input ontologia/ontolearn-abox-teste.ttl \
      --output dados/bases/base_ampliada.owl

# 2. Regime inferido: materialização com o HermiT
for b in base_referencia base_ampliada; do
  robot reason --input dados/bases/$b.owl --reasoner HermiT \
        --axiom-generators "SubClass ClassAssertion PropertyAssertion" \
        --include-indirect true --output dados/bases/${b}_inferida.owl
done

# 3. Perfis OWL 2, satisfatibilidade e subsunções inesperadas
java -cp "jars/*" scripts/java/PerfisESatisfatibilidade.java \
     ontologia/ontolearn-v2.1.owl dados/bases/base_ampliada.owl

# 4. Testes de unidade dos axiomas (16 testes x 2 bases x 2 raciocinadores)
java -cp "jars/*" scripts/java/TestesAxiomas.java \
     v2.1=ontologia/ontolearn-v2.1.owl \
     "v2.1+ABox teste"=dados/bases/base_ampliada.owl > dados/testes_axiomas.tsv

# 5. Questões de competência: 20 casos, regimes declarado e inferido
python3 scripts/executa_qcs.py .

# 6. Diagnóstico do OOPS! (código-fonte publicado pelos autores, compilado
#    e executado localmente) e conferência das condições de armadilhas e
#    da licença por script próprio
bash scripts/oops/compila_oops.sh oops robot.jar jars
bash scripts/oops/executa_oops.sh oops ontologia/ontolearn-v2.1.owl \
     relatorios/oops_2026-10-27/oops_v2.1
python3 scripts/verifica_anotacoes.py dados/verificacao_anotacoes.json \
        ontologia/ontolearn-v2.1.owl
```

## Resultados esperados

- A versão 2.1 e a base ampliada são consistentes, sem classes insatisfatíveis, e pertencem ao perfil OWL 2 DL
  (`relatorios/perfis_satisfatibilidade.txt`).
- Os 16 testes de unidade, nas duas bases e com os dois raciocinadores, conferem com o resultado esperado em 64
  de 64 execuções (`dados/testes_axiomas.tsv`).
- As consultas respondem aos 20 casos do gabarito nos regimes declarado e inferido (`relatorios/resultados_qcs.md`).
- O OOPS! não aponta armadilhas na versão 2.1 (`relatorios/oops_2026-10-27/oops_v2.1.txt`).
