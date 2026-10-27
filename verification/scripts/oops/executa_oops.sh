#!/usr/bin/env bash
# Executa o diagnóstico do OOPS! compilado por compila_oops.sh sobre um arquivo RDF/XML e grava o relatório
# textual (<saida>.txt, no formato da página de resultados do serviço web), a saída RDF oficial do relatório
# (<saida>.ttl) e as mensagens de execução do OOPS! (<saida>.log).
#
# Uso: executa_oops.sh <pasta de trabalho de compila_oops.sh> <ontologia.owl> <saida sem extensão>
set -euo pipefail
W=$(realpath "$1"); ONT=$2; OUT=$3
AQUI=$(cd "$(dirname "$0")" && pwd)
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-}"
COMMIT=$(git -C "$W/src/oops" rev-parse HEAD)
DATA=$(date +"%d/%m/%Y, %Hh%M")
{
    echo "OOPS! (OntOlogy Pitfall Scanner!) - código-fonte publicado pelos autores, executado localmente"
    echo "Código: https://github.com/oeg-upm/OOPS, commit $COMMIT (27/06/2025), com scripts/oops/P06.patch"
    echo "Compilação: scripts/oops/compila_oops.sh (Apache Jena 3.17.0, OWL API 5.1.9, extJWNL 2.0.5 com WordNet 3.1)"
    echo "Execução: $DATA (horário de Recife), por scripts/oops/RunOOPS.java, que segue o caminho do formulário"
    echo "  de entrada direta do serviço web (conteúdo RDF submetido; todos os verificadores do catálogo)"
    echo "Observação: P36, P37 e P40 exigem o IRI de publicação e não se aplicam à entrada direta, como no serviço"
    echo "  web; P41 consulta o serviço externo Licensius, inacessível nesta execução, e a declaração de licença é"
    echo "  conferida por scripts/verifica_anotacoes.py"
    echo
    java -Dstdout.encoding=UTF-8 -cp "$(cat "$W/classpath.txt")" "$AQUI/RunOOPS.java" "$ONT" "$OUT.ttl" 2>"$OUT.log"
} > "$OUT.txt"
grep -q "^Evaluation results" "$OUT.txt"
echo "Relatório: $OUT.txt"
