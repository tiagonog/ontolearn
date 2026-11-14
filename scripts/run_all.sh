#!/usr/bin/env bash
# run_all.sh - reproduce every result of the audit paper (run from the repository root).
#
#   bash scripts/run_all.sh [platform-label]
#
# Deterministic outputs (everything except timings) are written to results/ and can be compared
# with the files released there. E6 (scalability) measures time; its label names the platform
# and it is resumable. Set ONTOLEARN_SKIP_E6=1 to run only the deterministic experiments.
# Requirements: Python 3.10+, Java 11+ (scripts/setup_env.sh installs the pinned libraries).
# The wall-clock time of every step is written to results/run_all_<label>.log.
# A result file is replaced only if the step that produces it succeeds.
set -euo pipefail
LABEL="${1:-local}"
cd "$(dirname "$0")"
export JAVA_TOOL_OPTIONS=
# the class path is kept in an array so that the wildcard reaches the JVM unexpanded
JV=(java ${ONTOLEARN_JAVA_OPTS:-} -Dstdout.encoding=UTF-8 -Dorg.slf4j.simpleLogger.defaultLogLevel=error -cp "../jars/*")
R=../results; mkdir -p $R
LOG=$R/run_all_${LABEL}.log; : > $LOG
T0=$SECONDS
step() {            # step "<name>" command...
  local name="$1"; shift
  local t=$SECONDS
  echo "== $name"
  "$@"
  printf '%-58s %5d s\n' "$name" $((SECONDS - t)) >> $LOG
}
out() {             # out <file> command...   (stdout to <file>, kept only on success)
  local f="$1"; shift
  if "$@" > "$f.new"; then mv "$f.new" "$f"; else rm -f "$f.new"; return 1; fi
}
quiet() { "$@" > /dev/null; }

# every input file is listed with its SHA-256 digest in scripts/LOCK.sha256
lockcheck() { python3 -c "from common import verify_lock; print(verify_lock(), 'input files match scripts/LOCK.sha256')"; }
step "locked inputs (digest of every input file)" lockcheck
step "E0 release equivalence"            python3 check_release_equivalence.py
step "E0 profile conformance"            quiet python3 profiles.py
audits() {
  quiet lockcheck || return 1          # audit.py is a stand-alone tool and does not read through common.py
  for v in ontolearn ontolearn-v2 ontolearn-v2.1 ontolearn-v2.2; do
    out $R/audit_${v}_vs_sbie2026.txt python3 audit.py ../ontology/$v.owl --claims ../claims/sbie2026.json --json $R/audit_${v}_vs_sbie2026.json
  done
  out $R/audit_ontolearn-v2.2_vs_this_paper.txt python3 audit.py ../ontology/ontolearn-v2.2.owl \
      --claims ../claims/audit-paper-v2.2.json --json $R/audit_ontolearn-v2.2_vs_this_paper.json
  out $R/audit_report_vocabulary.txt python3 report_vocabulary.py
}
step "audit of each release against the claims of the report" audits
step "E1 ablation"                       out $R/E1_ablation.txt python3 ablation.py
e2() {
  quiet lockcheck || return 1          # the Java harness does not read through common.py
  "${JV[@]}" java/AxiomTests.java v1.0=../ontology/ontolearn.owl v2.0=../ontology/ontolearn-v2.owl \
      v2.1=../ontology/ontolearn-v2.1.owl v2.2=../ontology/ontolearn-v2.2.owl
}
step "E2 semantic tests"               out $R/E2_axiom_tests.tsv e2
step "E3 competency questions"           out $R/E3_cq_suite.txt python3 cq_suite.py
step "E4 OWL vs SHACL"                   out $R/E4_shacl.txt python3 shacl_validate.py
step "E5 fault injection"                out $R/E5_faults.txt python3 faults.py
step "external ontologies (download, digest check)" quiet python3 fetch_external.py
step "E7 audit selectivity"              out $R/E7_audit_selectivity.txt python3 audit_selectivity.py
step "E7 audit fixtures"                 out $R/E7_audit_fixtures.txt python3 audit_fixtures.py
step "E7 audit run time"                 quiet python3 audit_timing.py "$LABEL"
step "E8 lineage"                        out $R/E8_lineage.txt python3 lineage.py
printf '%-58s %5d s\n' "deterministic experiments, total" $((SECONDS - T0)) >> $LOG
if [ "${ONTOLEARN_SKIP_E6:-0}" != "1" ]; then
  step "E6 scalability (platform $LABEL)" python3 scalability.py 5 "$LABEL"
fi
step "tables and numbers of the paper"   python3 paper_assets.py
step "figures"                           python3 figures.py
cat $LOG
echo done
