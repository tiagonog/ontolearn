# Diagnóstico do OOPS! da versão 2.1 (nono ciclo, 27/10/2026)

O serviço web do OOPS! (<https://oops.linkeddata.es>) estava indisponível em 25 e 27 de outubro de 2026. O
diagnóstico da versão 2.1 foi feito com o código-fonte do OOPS! publicado pelos autores
(<https://github.com/oeg-upm/OOPS>, commit `11572ea`, de 27/06/2025), compilado e executado localmente pelo
mesmo caminho do formulário de entrada direta do serviço: o conteúdo RDF do arquivo é submetido a todos os 33
verificadores do catálogo.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `oops_v2.1.txt`, `oops_v2.1.ttl` | relatório da versão 2.1 (texto, no formato da página de resultados, e saída RDF do OOPS!): nenhuma armadilha, selo *Free of pitfalls* |
| `oops_v1.0_execucao_local.*`, `oops_v2.0_execucao_local.*` | a mesma execução aplicada aos arquivos das versões 1.0 e 2.0, para comparação com os diagnósticos do serviço web de 18/10/2026 (pasta `oops_2026-10-18`) |
| `regressao_oops.txt` | testes de regressão do repositório do OOPS! executados com a mesma compilação |

Os programas estão em `scripts/oops/`: `compila_oops.sh` (compilação), `executa_oops.sh` (diagnóstico),
`RunOOPS.java` (execução pelo caminho do formulário de entrada direta), `RegressionOOPS.java` (testes de
regressão) e `P06.patch` (correção aplicada antes da compilação).

## Comparação com o serviço web

| Versão | Serviço web (18/10/2026) | Execução local (27/10/2026) |
|---|---|---|
| 1.0 | P04 (1 caso, menor) e P08 (1 caso, menor) em `Subjetiva`; selo *Minor pitfalls* | idêntico |
| 2.0 | P08 (3 casos, menor) em `Subjetiva`, `temComponenteKSA` e `ehComponenteKSADe`; P11 (2 casos, importante) nas duas propriedades; selo *Important pitfalls* | idêntico |
| 2.1 | (serviço indisponível) | nenhuma armadilha; selo *Free of pitfalls* |

A execução local reproduz, nas versões 1.0 e 2.0, as armadilhas, o número de casos, os elementos afetados e o
selo do serviço web. A única diferença está na apresentação de P08: o serviço web separa os elementos sem rótulo
nem comentário dos elementos que só não têm comentário, e o código publicado lista os três elementos da versão
2.0 numa mesma subcategoria (P08-A).

## Observações sobre a execução

- **P06.** O verificador P06 (ciclos na hierarquia de classes) percorre a lista de superclasses com um laço
  *for-each* enquanto acrescenta elementos a ela, o que lança `ConcurrentModificationException` em hierarquias
  com mais de dois níveis, como a da OntoLearn (o próprio código registra a falha num comentário). A correção
  troca o laço por um percurso por índice, sem alterar o critério de detecção. Sem ela, a execução da versão
  2.1 termina com a exceção, e o relatório não chega a um selo.
- **P36, P37 e P40** exigem o IRI de publicação da ontologia e não se aplicam à entrada direta, como no serviço
  web.
- **P41** consulta o serviço externo Licensius (`www.licensius.appspot.com`), inacessível nesta execução. A
  declaração de licença da versão 2.1 (`dcterms:license` com a CC BY 4.0) é a mesma das versões 1.0 e 2.0, para
  as quais o serviço web não apontou P41, e é conferida por `scripts/verifica_anotacoes.py`.
- **Dependências.** O código publicado declara o Apache Jena 5.3.0 e a OWL API 5.5.1; a compilação local usou o
  Jena 3.17.0 (do ROBOT 1.9.6) e a OWL API 5.1.9, as versões disponíveis no ambiente de verificação da tese. Os
  testes de regressão do repositório conferem em 25 dos 37 casos; as 12 diferenças estão explicadas em
  `regressao_oops.txt` e não envolvem construções presentes na OntoLearn.
