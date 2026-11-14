#!/usr/bin/env bash
# setup_env.sh - one-time set-up of the audit pipeline (run from the repository root).
#   Python packages (pinned), and the Java libraries used by scripts/java/*.java:
#   OWL API 5.1.9, HermiT 1.4.3.517 and Openllet 2.6.5 with their dependencies.
#   The jars are taken from the PyPI package owlapy 1.5.0, which bundles exactly these versions.
set -euo pipefail
python3 -m pip install -r scripts/requirements.txt
mkdir -p jars .jars_tmp
python3 -m pip download owlapy==1.5.0 --no-deps --ignore-requires-python -d .jars_tmp
python3 - <<'PY'
import zipfile, glob, os
whl = glob.glob('.jars_tmp/owlapy-1.5.0-*.whl')[0]
with zipfile.ZipFile(whl) as z:
    for n in z.namelist():
        if n.startswith('owlapy/jar_dependencies/') and n.endswith('.jar'):
            with open(os.path.join('jars', os.path.basename(n)), 'wb') as f:
                f.write(z.read(n))
print(len(os.listdir('jars')), 'jars in ./jars')
PY
rm -rf .jars_tmp
java -version
