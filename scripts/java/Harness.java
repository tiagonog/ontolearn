/*
 * Harness.java - OWL 2 DL reasoning harness for the OntoLearn audit.
 *
 * One file, six commands, no build step (Java 11+ single-file launch):
 *
 *   java -cp "jars/*" Harness.java verdict  <HermiT|Openllet> <file.owl>...
 *   java -cp "jars/*" Harness.java census   <HermiT|Openllet> <file.owl>
 *   java -cp "jars/*" Harness.java bench    <HermiT|Openllet> <reps> <file.owl>...
 *   java -cp "jars/*" Harness.java metrics  <file.owl>...
 *   java -cp "jars/*" Harness.java profiles <file.owl>...
 *   java -cp "jars/*" Harness.java diff     <a.owl> <b.owl>
 *
 * verdict : consistency, unsatisfiable named classes and a timing breakdown.
 *           Unsatisfiable-class counts are reported as "n/a" for inconsistent
 *           ontologies (every class is trivially unsatisfiable there, so a
 *           count carries no information).
 * census  : every entailed atomic assertion over the named individuals:
 *           class assertions C(a) (T lines), object-property assertions p(a,b)
 *           (P lines), equalities a = b (S lines), and the strict subsumptions
 *           between named classes (C lines). Each line is tagged A (asserted in the file)
 *           or I (inferred only). This is the complete OWL 2 DL counterpart
 *           of the rule-based OWL-RL materialization.
 * metrics : axiom counts and the DL expressivity name computed by the OWL API
 *           (DLExpressivityChecker), as an independent check of scripts/audit.py.
 * profiles: conformance of each file to the OWL 2 DL, EL, QL and RL profiles, as
 *           decided by the OWL API profile checkers; every violation is listed
 *           with its kind and the axiom that causes it.
 * diff    : the logical axioms that only the first file contains and those that
 *           only the second contains, as parsed by the OWL API.
 * bench   : repeated in-JVM measurements (parse, consistency, classification,
 *           realization) with System.nanoTime(), so that reasoning time is
 *           separated from JVM start-up. The first repetition is reported as
 *           "cold" (class loading, JIT); the remaining ones as "warm".
 *           With -Dclosure the entailed prerequisite closure (every requer(c,p)
 *           the reasoner derives) is also retrieved and timed.
 *
 * Libraries: OWL API 5.1.9, HermiT 1.4.3.517, Openllet 2.6.5.
 */
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.owlapi.search.EntitySearcher;
import java.io.File;
import java.util.*;
import java.util.stream.*;

public class Harness {
    static final String NS = "http://www.ontolearn.com/ontologia#";
    static final boolean CLOSURE = System.getProperty("closure") != null;   // -Dclosure: also time the requer closure

    static OWLReasonerFactory factory(String name) throws Exception {
        if (name.equals("HermiT")) return new org.semanticweb.HermiT.ReasonerFactory();
        return (OWLReasonerFactory) Class.forName("openllet.owlapi.OpenlletReasonerFactory")
                .getMethod("getInstance").invoke(null);
    }

    static String sh(OWLEntity e) { return e.getIRI().toString().replace(NS, ":"); }
    static double ms(long t0) { return (System.nanoTime() - t0) / 1e6; }

    static OWLOntology load(File f) throws Exception {
        OWLOntologyManager m = OWLManager.createOWLOntologyManager();
        // owl:imports are not followed (no network access is assumed); a missing import is not an error
        OWLOntologyLoaderConfiguration cfg = new OWLOntologyLoaderConfiguration()
                .setMissingImportHandlingStrategy(MissingImportHandlingStrategy.SILENT);
        return m.loadOntologyFromOntologyDocument(new org.semanticweb.owlapi.io.FileDocumentSource(f), cfg);
    }

    // ---------------------------------------------------------------- verdict
    static void verdict(String rz, List<String> files) throws Exception {
        System.out.println("file\treasoner\tconsistent\tunsat_classes\tlogical_axioms\tindividuals");
        for (String f : files) {
            OWLOntology o = load(new File(f));
            OWLReasoner r = factory(rz).createReasoner(o);
            boolean ok = r.isConsistent();
            String unsat = "n/a";
            if (ok) {
                Set<OWLClass> u = r.getUnsatisfiableClasses().getEntitiesMinusBottom();
                unsat = u.isEmpty() ? "0" : u.size() + " " + u.stream().map(Harness::sh).sorted().collect(Collectors.toList());
            }
            System.out.println(new File(f).getName() + "\t" + rz + "\t" + (ok ? "consistent" : "INCONSISTENT")
                    + "\t" + unsat + "\t" + o.getLogicalAxiomCount() + "\t" + o.getIndividualsInSignature().size());
            r.dispose();
        }
    }

    // ----------------------------------------------------------------- census
    static void census(String rz, String f) throws Exception {
        OWLOntology o = load(new File(f));
        OWLDataFactory df = o.getOWLOntologyManager().getOWLDataFactory();
        OWLReasoner r = factory(rz).createReasoner(o);
        if (!r.isConsistent()) { System.out.println("INCONSISTENT"); return; }
        r.precomputeInferences(InferenceType.CLASS_HIERARCHY, InferenceType.CLASS_ASSERTIONS,
                InferenceType.OBJECT_PROPERTY_ASSERTIONS);
        List<OWLNamedIndividual> inds = o.getIndividualsInSignature().stream()
                .sorted(Comparator.comparing(i -> i.getIRI().toString())).collect(Collectors.toList());
        List<OWLObjectProperty> props = o.getObjectPropertiesInSignature().stream()
                .filter(p -> !p.isOWLTopObjectProperty() && !p.isOWLBottomObjectProperty())
                .sorted(Comparator.comparing(p -> p.getIRI().toString())).collect(Collectors.toList());
        Set<String> lines = new TreeSet<>();
        // strict subsumptions between named classes (C lines), asserted or inferred
        for (OWLClass c : o.getClassesInSignature()) {
            if (c.isOWLThing() || c.isOWLNothing()) continue;
            Set<OWLClass> direct = EntitySearcher.getSuperClasses(c, o).filter(x -> !x.isAnonymous())
                    .map(x -> x.asOWLClass()).collect(Collectors.toSet());
            for (OWLClass d : r.getSuperClasses(c, false).getFlattened()) {
                if (d.isOWLThing()) continue;
                lines.add("C\t" + (direct.contains(d) ? "A" : "I") + "\t" + sh(c) + "\t" + sh(d));
            }
        }
        for (OWLNamedIndividual i : inds) {
            Set<OWLClass> asserted = EntitySearcher.getTypes(i, o).filter(c -> !c.isAnonymous())
                    .map(c -> c.asOWLClass()).collect(Collectors.toSet());
            for (OWLClass c : r.getTypes(i, false).getFlattened()) {
                if (c.isOWLThing()) continue;
                lines.add("T\t" + (asserted.contains(c) ? "A" : "I") + "\t" + sh(i) + "\t" + sh(c));
            }
            for (OWLObjectProperty p : props) {
                Set<OWLIndividual> as = EntitySearcher.getObjectPropertyValues(i, p, o).collect(Collectors.toSet());
                for (OWLNamedIndividual v : r.getObjectPropertyValues(i, p).getFlattened()) {
                    lines.add("P\t" + (as.contains(v) ? "A" : "I") + "\t" + sh(i) + "\t" + sh(p) + "\t" + sh(v));
                }
            }
            for (OWLNamedIndividual s : r.getSameIndividuals(i).getEntities()) {
                if (!s.equals(i) && sh(i).compareTo(sh(s)) < 0) lines.add("S\tI\t" + sh(i) + "\t" + sh(s));
            }
        }
        lines.forEach(System.out::println);
        r.dispose();
    }

    // ---------------------------------------------------------------- metrics
    static void metrics(List<String> files) throws Exception {
        System.out.println("file\taxioms\tlogical_axioms\tclasses\tobject_properties\tdata_properties\tindividuals\tdl_name_owlapi");
        for (String f : files) {
            OWLOntology o = load(new File(f));
            String dl = new org.semanticweb.owlapi.util.DLExpressivityChecker(Collections.singleton(o)).getDescriptionLogicName();
            System.out.println(new File(f).getName() + "\t" + o.getAxiomCount() + "\t" + o.getLogicalAxiomCount() + "\t"
                    + o.getClassesInSignature().size() + "\t" + o.getObjectPropertiesInSignature().size() + "\t"
                    + o.getDataPropertiesInSignature().size() + "\t" + o.getIndividualsInSignature().size() + "\t" + dl);
        }
    }

    // --------------------------------------------------------------- profiles
    static void profiles(List<String> files) throws Exception {
        Map<String, org.semanticweb.owlapi.profiles.OWLProfile> ps = new LinkedHashMap<>();
        ps.put("OWL2DL", new org.semanticweb.owlapi.profiles.OWL2DLProfile());
        ps.put("OWL2EL", new org.semanticweb.owlapi.profiles.OWL2ELProfile());
        ps.put("OWL2QL", new org.semanticweb.owlapi.profiles.OWL2QLProfile());
        ps.put("OWL2RL", new org.semanticweb.owlapi.profiles.OWL2RLProfile());
        System.out.println("file\tprofile\tkind\taxiom_type\taxiom");
        for (String f : files) {
            OWLOntology o = load(new File(f));
            for (Map.Entry<String, org.semanticweb.owlapi.profiles.OWLProfile> e : ps.entrySet()) {
                org.semanticweb.owlapi.profiles.OWLProfileReport rep = e.getValue().checkOntology(o);
                List<String> lines = new ArrayList<>();
                for (org.semanticweb.owlapi.profiles.OWLProfileViolation v : rep.getViolations()) {
                    OWLAxiom ax = v.getAxiom();
                    lines.add(new File(f).getName() + "\t" + e.getKey() + "\t" + v.getClass().getSimpleName() + "\t"
                            + (ax == null ? "-" : ax.getAxiomType().getName()) + "\t"
                            + (ax == null ? "-" : ax.toString().replace(NS, ":").replace("\n", " ")));
                }
                Collections.sort(lines);
                System.out.println(new File(f).getName() + "\t" + e.getKey() + "\tSUMMARY\t"
                        + (rep.isInProfile() ? "in-profile" : "not-in-profile") + "\t" + rep.getViolations().size());
                lines.forEach(System.out::println);
            }
        }
    }

    // ------------------------------------------------------------------- diff
    static void diff(String fa, String fb) throws Exception {
        Set<OWLLogicalAxiom> a = load(new File(fa)).getLogicalAxioms();
        Set<OWLLogicalAxiom> b = load(new File(fb)).getLogicalAxioms();
        System.out.println("side\taxiom_type\taxiom");
        List<String> lines = new ArrayList<>();
        for (OWLLogicalAxiom x : a) if (!b.contains(x))
            lines.add("ONLY_A\t" + x.getAxiomType().getName() + "\t" + x.getAxiomWithoutAnnotations().toString().replace(NS, ":"));
        for (OWLLogicalAxiom x : b) if (!a.contains(x))
            lines.add("ONLY_B\t" + x.getAxiomType().getName() + "\t" + x.getAxiomWithoutAnnotations().toString().replace(NS, ":"));
        Collections.sort(lines);
        lines.forEach(System.out::println);
    }

    // ------------------------------------------------------------------ bench
    static void bench(String rz, int reps, List<String> files) throws Exception {
        System.out.println("file\treasoner\trep\tphase\tparse_ms\tconsistency_ms\tclassify_ms\trealize_ms\treasoning_ms\tconsistent\tclosure_ms\tclosure_pairs");
        for (String f : files) {
            for (int k = 0; k < reps; k++) {
                long t = System.nanoTime();
                OWLOntology o = load(new File(f));
                double parse = ms(t);
                t = System.nanoTime();
                OWLReasoner r = factory(rz).createReasoner(o);
                boolean ok = r.isConsistent();
                double cons = ms(t);
                double cls = 0, rea = 0;
                if (ok) {
                    t = System.nanoTime();
                    r.precomputeInferences(InferenceType.CLASS_HIERARCHY);
                    cls = ms(t);
                    t = System.nanoTime();
                    r.precomputeInferences(InferenceType.CLASS_ASSERTIONS);
                    rea = ms(t);
                }
                // entailment-regime prerequisite closure: every entailed requer(c, p), through the reasoner
                double clo = -1; long pairs = -1;
                if (ok && CLOSURE) {
                    OWLDataFactory df = o.getOWLOntologyManager().getOWLDataFactory();
                    OWLObjectProperty requer = df.getOWLObjectProperty(IRI.create(NS + "requer"));
                    OWLClass comp = df.getOWLClass(IRI.create(NS + "Competencia"));
                    t = System.nanoTime();
                    pairs = 0;
                    for (OWLNamedIndividual c : r.getInstances(comp, false).getFlattened())
                        pairs += r.getObjectPropertyValues(c, requer).getFlattened().size();
                    clo = ms(t);
                }
                r.dispose();
                System.out.println(String.format(Locale.ROOT, "%s\t%s\t%d\t%s\t%.1f\t%.1f\t%.1f\t%.1f\t%.1f\t%s\t%.1f\t%d",
                        new File(f).getName(), rz, k + 1, k == 0 ? "cold" : "warm", parse, cons, cls, rea,
                        cons + cls + rea, ok, clo, pairs));
                System.out.flush();
            }
        }
    }

    public static void main(String[] a) throws Exception {
        List<String> rest = Arrays.asList(a);
        switch (a[0]) {
            case "verdict": verdict(a[1], rest.subList(2, rest.size())); break;
            case "census": census(a[1], a[2]); break;
            case "metrics": metrics(rest.subList(1, rest.size())); break;
            case "profiles": profiles(rest.subList(1, rest.size())); break;
            case "diff": diff(a[1], a[2]); break;
            case "bench": bench(a[1], Integer.parseInt(a[2]), rest.subList(3, rest.size())); break;
            default: throw new IllegalArgumentException("unknown command " + a[0]);
        }
    }
}
