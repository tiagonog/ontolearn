#!/usr/bin/env python3
"""scalability.py - E6: reasoning cost as the fact base grows, by prerequisite topology.

For every (topology, size, seed) a synthetic fact base (scripts/generator.py) is
laid under the released v2.2 schema. Measured:

  counts        triples, individuals, asserted :requer edges, closure pairs (deterministic)
  in-JVM        HermiT 1.4.3.517 through the OWL API, timed inside the JVM with
                System.nanoTime(): parsing, consistency, classification, realization.
                One cold repetition (class loading, JIT) and two warm ones.
  closure       (seed 1 only) every entailed requer(c, p) retrieved THROUGH THE
                REASONER - the cost of answering the prerequisite question in the
                entailment regime rather than with a SPARQL property path
  process       wall-clock of a whole 'java ... verdict' process, i.e. JVM start-up
                + parsing + consistency: the figure the first submission reported
  path query    SPARQL 1.1 property path :requer+ over the asserted graph (rdflib)
  OWL-RL        rule closure with owlrl, up to 7,000 triples (seeds 1-3)
  schema cost   (seed 1) the same facts under the v1.0 schema, to price the completion

Counts are asserted identical across repetitions. Results are appended to
results/E6_scalability.jsonl so that an interrupted run resumes.

Usage: python3 scalability.py [seeds=5] [platform-label]
       ONTOLEARN_SKIP_RL=1 skips the OWL-RL closure (a pure-Python measurement that is slow to repeat).
"""
import copy, json, os, platform, statistics as st, subprocess, sys, time
import owlrl
from common import *
from generator import *

SEEDS = list(range(1, (int(sys.argv[1]) if len(sys.argv) > 1 else 5) + 1))
LABEL = sys.argv[2] if len(sys.argv) > 2 else 'B'
OUT = RESULTS / f'E6_scalability_{LABEL}.jsonl'
Q_PATH = f'PREFIX : <{NS}> SELECT (COUNT(*) AS ?n) WHERE {{ ?c :requer+ ?p }}'


def done():
    if not OUT.exists():
        return set()
    return {(r['topology'], r['size'], r['seed']) for r in map(json.loads, OUT.read_text().splitlines())}


def bench(path, closure=False, reps=3, timeout=3600):
    try:
        rows = harness('bench', 'HermiT', reps, path, props=['-Dclosure=1'] if closure else [], timeout=timeout)[1:]
    except subprocess.TimeoutExpired:
        return None
    out = []
    for r in rows:
        c = r.split('\t')
        out.append({'phase': c[3], 'parse_ms': float(c[4]), 'consistency_ms': float(c[5]), 'classify_ms': float(c[6]),
                    'realize_ms': float(c[7]), 'reasoning_ms': float(c[8]), 'consistent': c[9] == 'true',
                    'closure_ms': float(c[10]), 'closure_pairs': int(c[11])})
    return out


def process_wall(path):
    t = time.time()
    harness('verdict', 'HermiT', path)
    return time.time() - t


def main():
    env = {'platform': LABEL, 'machine': platform.machine(), 'system': platform.platform(),
           'python': platform.python_version(), 'cpus': os.cpu_count(),
           'java': subprocess.run(['java', '-version'], capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != 'JAVA_TOOL_OPTIONS'}).stderr.splitlines()[0]}
    (RESULTS / f'E6_environment_{LABEL}.json').write_text(json.dumps(env, indent=1))
    print(env, flush=True)
    # JVM floor: the smallest possible job, five times
    fp = RESULTS / f'E6_jvm_floor_{LABEL}.json'
    if not fp.exists():
        floor = [process_wall(locked('v2.2')) for _ in range(5)]
        fp.write_text(json.dumps({'process_wall_s_v2.2_native_abox': floor}))
        print(f'JVM floor (whole process on the 20-individual file): {st.mean(floor):.2f} s [{min(floor):.2f}-{max(floor):.2f}]', flush=True)
    seen = done()
    for si, size in enumerate(SIZES):
        for topo in TOPOLOGIES:
            for seed in SEEDS:
                if (topo, si, seed) in seen:
                    continue
                facts = gen_facts(topo, size, seed)
                g = lay(load('v2.2'), facts)
                row = {'topology': topo, 'size': si, 'seed': seed, **stats(g)}
                t = time.time(); row['closure_pairs'] = int(list(g.query(Q_PATH))[0][0]); row['path_query_s'] = time.time() - t
                p = write_tmp(g, f'sc_{topo}_{si}_{seed}')
                b = bench(p)
                assert all(x['consistent'] for x in b)
                row['hermit'] = b
                row['process_wall_s'] = process_wall(p)
                if seed == 1:
                    bc = bench(p, closure=True, reps=2, timeout=2400)
                    row['hermit_closure'] = bc
                    if bc is not None:
                        assert bc[-1]['closure_pairs'] == row['closure_pairs'], 'reasoner closure differs from SPARQL closure'
                    g1 = lay(load('v1.0'), facts)
                    row['hermit_v1_schema'] = bench(write_tmp(g1, f'sc1_{topo}_{si}_{seed}'))
                if row['triples'] <= 7000 and seed <= 3 and not os.environ.get('ONTOLEARN_SKIP_RL'):
                    h = copy.deepcopy(g); t = time.time()
                    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(h)
                    row['owlrl_s'] = time.time() - t
                    row['owlrl_triples'] = len(h)
                with open(OUT, 'a') as fh:
                    fh.write(json.dumps(row) + '\n')
                w = [x['reasoning_ms'] for x in b if x['phase'] == 'warm']
                print(f"{topo:5s} size {si} seed {seed}: {row['triples']:6d} triples {row['individuals']:6d} ind "
                      f"{row['closure_pairs']:7d} pairs | HermiT warm {st.mean(w):8.1f} ms | process {row['process_wall_s']:.2f} s"
                      + (f" | closure {row['hermit_closure'][-1]['closure_ms']/1000:.1f} s" if row.get('hermit_closure') else ''), flush=True)


if __name__ == '__main__':
    main()
