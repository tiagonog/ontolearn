#!/usr/bin/env bash
# Compila o OOPS! (OntOlogy Pitfall Scanner!) a partir do código-fonte publicado pelos autores
# (https://github.com/oeg-upm/OOPS, commit 11572ea, de 27/06/2025) para executá-lo localmente.
#
# Uso: compila_oops.sh <pasta de trabalho> <robot.jar> <pasta jars/ com a OWL API 5.1.9>
#
#   <robot.jar>  ROBOT 1.9.6, que fornece o Apache Jena 3.17.0 e as bibliotecas comuns
#                (a OWL API 4 embutida no ROBOT é descartada);
#   <jars/>      OWL API 5.1.9, HermiT 1.4.3.517 e Openllet 2.6.5 com suas dependências, as mesmas
#                usadas nos testes de unidade (pasta de dependências Java do pacote Python owlapy 1.5.0).
#
# As demais dependências do OOPS! (extJWNL 2.0.5 com os dados do WordNet 3.1, jackson-dataformat-xml
# e jackson-module-jaxb-annotations 2.11.3, concurrentlinkedhashmap-lru 1.3.2, metainf-services 1.11 e
# picocli 4.7.6) são compiladas a partir das etiquetas correspondentes de seus repositórios.
# O pacote es.upm.fi.oeg.oops.service (serviço REST) não é compilado, pois não participa do diagnóstico.
#
# Antes da compilação, aplica-se P06.patch: o verificador P06 percorre a lista de superclasses com um
# laço for-each enquanto acrescenta elementos a ela, o que lança ConcurrentModificationException em
# hierarquias com mais de dois níveis (o próprio código registra a falha num comentário TODO); a correção
# troca o laço por um percurso por índice, sem alterar o critério de detecção.
#
# Ao final, a pasta de trabalho contém cls/ (classes do OOPS!), lib/ (dependências) e classpath.txt.
# Execução do diagnóstico (mesmo caminho do formulário de entrada direta do serviço web):
#   java -Dstdout.encoding=UTF-8 -cp "$(cat <pasta>/classpath.txt)" RunOOPS.java <ontologia.owl> <saida.ttl>
set -euo pipefail
W=$(realpath -m "$1"); ROBOT=$(realpath "$2"); JARS=$(realpath "$3")
AQUI=$(cd "$(dirname "$0")" && pwd)
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-}"
mkdir -p "$W/src" "$W/lib" "$W/cls"
cd "$W/src"

clona() { # clona <url> <etiqueta ou commit> <pasta>
    [ -d "$3" ] && return 0
    if [[ "$2" =~ ^[0-9a-f]{40}$ ]]; then
        git clone -q "$1" "$3" && git -C "$3" -c advice.detachedHead=false checkout -q "$2"
    else
        git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3"
    fi
}
clona https://github.com/oeg-upm/OOPS.git 11572ea6b31cba29dd3f8a443e24311652f059de oops
clona https://github.com/extjwnl/extjwnl.git extjwnl-parent-2.0.5 extjwnl
clona https://github.com/extjwnl/extjwnl-data-wn31.git extjwnl-data-wn31-1.2 wn31
clona https://github.com/FasterXML/jackson-dataformat-xml.git jackson-dataformat-xml-2.11.3 jxml
clona https://github.com/FasterXML/jackson-modules-base.git jackson-modules-base-2.11.3 jmb
clona https://github.com/ben-manes/concurrentlinkedhashmap.git concurrentlinkedhashmap-lru-1.3.2 clhm
clona https://github.com/kohsuke/metainf-services.git metainf-services-1.11 mis
clona https://github.com/remkop/picocli.git v4.7.6 picocli
git -C oops apply --check "$AQUI/P06.patch" 2>/dev/null && git -C oops apply "$AQUI/P06.patch"
cd "$W"

compila() { # compila <saida> <classpath> <fontes...>
    local out=$1 cp=$2; shift 2
    rm -rf "cls/$out"; mkdir -p "cls/$out"
    javac -nowarn -encoding UTF-8 -proc:none -d "cls/$out" ${cp:+-cp "$cp"} "$@" 2>&1 | grep -v "^Note:\|JAVA_TOOL" || true
}
empacota() { (cd "cls/$1" && rm -f "$W/lib/$2" && zip -qr "$W/lib/$2" .); }

# 1) Dependências comuns do ROBOT 1.9.6 (Jena 3.17.0 etc.), sem a OWL API 4 e sem o próprio ROBOT
python3 - "$ROBOT" "$W/lib/robot-deps.jar" <<'EOF'
import sys, zipfile
src, dst = sys.argv[1], sys.argv[2]
skip = ('org/semanticweb/', 'uk/ac/manchester/', 'org/obolibrary/', 'META-INF/services/org.semanticweb.',
        'org/geneontology/', 'org/liveontologies/', 'edu/stanford/', 'de/derivo/')
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        if it.filename.startswith(skip) or it.filename.endswith(('.SF', '.RSA', '.DSA')):
            continue
        zo.writestr(it, zi.read(it.filename))
EOF
J=$W/lib/robot-deps.jar

# 2) concurrentlinkedhashmap-lru 1.3.2 e extJWNL 2.0.5 com os dados do WordNet 3.1
compila clhm "$J" $(find src/clhm/src/main/java -name "*.java"); empacota clhm concurrentlinkedhashmap-lru-1.3.2.jar
compila extjwnl "$J:$W/lib/concurrentlinkedhashmap-lru-1.3.2.jar" $(find src/extjwnl/extjwnl/src/main/java -name "*.java")
[ -d src/extjwnl/extjwnl/src/main/resources ] && cp -r src/extjwnl/extjwnl/src/main/resources/. cls/extjwnl/
empacota extjwnl extjwnl-2.0.5.jar
(cd src/wn31/src/main/resources && rm -f "$W/lib/extjwnl-data-wn31-1.2.jar" && zip -qr "$W/lib/extjwnl-data-wn31-1.2.jar" .)

# 3) jackson-module-jaxb-annotations e jackson-dataformat-xml 2.11.3 (PackageVersion gerado como no Maven)
mkdir -p gen/jaxb/com/fasterxml/jackson/module/jaxb gen/jxml/com/fasterxml/jackson/dataformat/xml
sed -e 's/@package@/com.fasterxml.jackson.module.jaxb/' -e 's/@projectversion@/2.11.3/' \
    -e 's/@projectgroupid@/com.fasterxml.jackson.module/' -e 's/@projectartifactid@/jackson-module-jaxb-annotations/' \
    src/jmb/jaxb/src/main/java/com/fasterxml/jackson/module/jaxb/PackageVersion.java.in \
    > gen/jaxb/com/fasterxml/jackson/module/jaxb/PackageVersion.java
compila jaxb "$J" $(find src/jmb/jaxb/src/main/java gen/jaxb -name "*.java")
[ -d src/jmb/jaxb/src/main/resources ] && cp -r src/jmb/jaxb/src/main/resources/. cls/jaxb/
empacota jaxb jackson-module-jaxb-annotations-2.11.3.jar
sed -e 's/@package@/com.fasterxml.jackson.dataformat.xml/' -e 's/@projectversion@/2.11.3/' \
    -e 's/@projectgroupid@/com.fasterxml.jackson.dataformat/' -e 's/@projectartifactid@/jackson-dataformat-xml/' \
    src/jxml/src/main/java/com/fasterxml/jackson/dataformat/xml/PackageVersion.java.in \
    > gen/jxml/com/fasterxml/jackson/dataformat/xml/PackageVersion.java
compila jxml "$J:$W/lib/jackson-module-jaxb-annotations-2.11.3.jar" $(find src/jxml/src/main/java gen/jxml -name "*.java")
cp -r src/jxml/src/main/resources/. cls/jxml/
empacota jxml jackson-dataformat-xml-2.11.3.jar

# 4) picocli 4.7.6 e metainf-services 1.11 (processador de anotações que registra os verificadores)
compila picocli "" $(find src/picocli/src/main/java/picocli -maxdepth 1 -name "*.java"); empacota picocli picocli-4.7.6.jar
compila mis "" $(find src/mis/src/main/java -name "*.java")
[ -d src/mis/src/main/resources ] && cp -r src/mis/src/main/resources/. cls/mis/
empacota mis metainf-services-1.11.jar

# 5) OOPS!
CP="$(ls "$JARS"/*.jar | tr '\n' ':')"
for j in extjwnl-2.0.5 extjwnl-data-wn31-1.2 concurrentlinkedhashmap-lru-1.3.2 jackson-dataformat-xml-2.11.3 \
         jackson-module-jaxb-annotations-2.11.3 picocli-4.7.6 metainf-services-1.11 robot-deps; do
    CP="$CP$W/lib/$j.jar:"
done
CP=${CP%:}
rm -rf cls/oops; mkdir -p cls/oops
javac -nowarn -encoding UTF-8 -d cls/oops -cp "$CP" -processorpath "$W/lib/metainf-services-1.11.jar" \
    -processor org.kohsuke.metainf_services.AnnotationProcessorImpl \
    $(find src/oops/src/main/java -name "*.java" | grep -v "/service/") 2>&1 | grep -v "^Note:\|JAVA_TOOL" || true
cp -r src/oops/src/main/resources/. cls/oops/
echo "$W/cls/oops:$CP" > "$W/classpath.txt"
echo "OOPS! compilado: $(find cls/oops -name '*.class' | wc -l) classes; $(grep -c . cls/oops/META-INF/services/es.upm.fi.oeg.oops.Checker) verificadores registrados"
echo "Classpath em $W/classpath.txt"
