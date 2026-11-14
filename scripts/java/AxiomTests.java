/*
 * AxiomTests.java - E2: semantic test cases for the OntoLearn axiom families.
 *
 * Each test adds a small set of facts to a released version and asks one question
 * of an OWL 2 DL reasoner: is the result consistent, and is a given axiom entailed?
 * The expected outcome is REGISTERED PER VERSION in this file, before execution;
 * the output marks every (version, reasoner, test) as matching or not.
 *
 * The suite contains positive tests (an intended consequence is derived), negative
 * tests (a population error must be rejected), controls (legitimate data must NOT
 * be rejected), and two exhaustive sweeps: the 15 pairs of Bloom tiers and the 78
 * pairs of root classes.
 *
 * No build step (Java 11+ single-file launch):
 *
 *   java -cp "jars/*" AxiomTests.java v1.0=ontolearn.owl v2.0=ontolearn-v2.owl \
 *        v2.1=ontolearn-v2.1.owl v2.2=ontolearn-v2.2.owl > E2_axiom_tests.tsv
 *
 * Libraries: OWL API 5.1.9, HermiT 1.4.3.517, Openllet 2.6.5.
 */
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.owlapi.vocab.OWL2Datatype;
import java.io.File;
import java.util.*;
import java.util.function.Function;

public class AxiomTests {
    static final String NS = "http://www.ontolearn.com/ontologia#";
    static OWLDataFactory df = OWLManager.getOWLDataFactory();
    static OWLClass C(String n) { return df.getOWLClass(IRI.create(NS + n)); }
    static OWLObjectProperty OP(String n) { return df.getOWLObjectProperty(IRI.create(NS + n)); }
    static OWLDataProperty DP(String n) { return df.getOWLDataProperty(IRI.create(NS + n)); }
    static OWLNamedIndividual I(String n) { return df.getOWLNamedIndividual(IRI.create(NS + n)); }
    static OWLAxiom type(String c, String i) { return df.getOWLClassAssertionAxiom(C(c), I(i)); }
    static OWLAxiom rel(String s, String p, String o) { return df.getOWLObjectPropertyAssertionAxiom(OP(p), I(s), I(o)); }
    static OWLAxiom some(String p, String c, String i) {
        return df.getOWLClassAssertionAxiom(df.getOWLObjectSomeValuesFrom(OP(p), C(c)), I(i));
    }

    static final String[] ROOTS = {"UsuarioDoAva", "Competencia", "RecursoDeAprendizagem", "DesempenhoDoAprendiz",
        "Questao", "Avaliacao", "Curso", "NiveisDeProficiencia", "MilestoneDeAprendizagem",
        "TrajetoriasDeAprendizagem", "Conhecimento", "Habilidade", "Atitude"};
    static final String[] TIERS = {"Lembrar", "Entender", "Aplicar", "Analisar", "AvaliarBloom", "Criar"};

    /** expected: outcomes for v1.0, v2.0, v2.1, v2.2 (a single entry applies to all). */
    static final class Test {       // a plain class, so that the file also runs on Java 11
        private final String id, kind, family, description;
        private final List<OWLAxiom> facts;
        private final Function<OWLReasoner, String> check;
        private final String[] expected;
        Test(String id, String kind, String family, String description, List<OWLAxiom> facts,
             Function<OWLReasoner, String> check, String... expected) {
            this.id = id; this.kind = kind; this.family = family; this.description = description;
            this.facts = facts; this.check = check; this.expected = expected;
        }
        String id() { return id; }
        String kind() { return kind; }
        String family() { return family; }
        String description() { return description; }
        List<OWLAxiom> facts() { return facts; }
        Function<OWLReasoner, String> check() { return check; }
        String[] expected() { return expected; }
    }

    static String ent(OWLReasoner r, OWLAxiom ax) {
        try { return r.isEntailed(ax) ? "entailed" : "not entailed"; }
        catch (Exception e) { return "not evaluable (" + e.getClass().getSimpleName() + ")"; }
    }

    static List<Test> tests() {
        List<Test> t = new ArrayList<>();
        Function<OWLReasoner, String> cons = r -> "consistent";
        t.add(new Test("S01", "positive", "-", "released file, no added fact", List.of(), cons, "consistent"));
        t.add(new Test("S02", "positive", "F1", "individual typed only Subjetiva: is it a Questao?",
            List.of(type("Subjetiva", "TS")), r -> ent(r, type("Questao", "TS")),
            "not entailed", "entailed", "entailed", "entailed"));
        t.add(new Test("S03", "positive", "T", "chain T3 -> COMP-0002 -> COMP-0001 -> T4: does T3 require T4?",
            List.of(type("Competencia", "T3"), type("Competencia", "T4"), rel("T3", "requer", "COMP-0002"), rel("COMP-0001", "requer", "T4")),
            r -> ent(r, rel("T3", "requer", "T4")), "entailed"));
        t.add(new Test("S04", "positive", "I", "performance recorded only as record -> learner: retrievable from the learner?",
            List.of(type("DesempenhoDoAprendiz", "TD"), rel("TD", "competenciasDoDesempenho", "APR-0001")),
            r -> ent(r, rel("APR-0001", "desempenhoCompetencias", "TD")), "entailed"));
        t.add(new Test("S05", "positive", "F4", "COMP-0002 ehCompostoDeConhecimento KNOW-001: temComponenteKSA?",
            List.of(), r -> ent(r, rel("COMP-0002", "temComponenteKSA", "KNOW-001")),
            "not entailed", "entailed", "entailed", "entailed"));
        t.add(new Test("S06", "negative", "F2", "one individual typed Conhecimento and Habilidade",
            List.of(type("Conhecimento", "TX"), type("Habilidade", "TX")), cons,
            "consistent", "inconsistent", "inconsistent", "inconsistent"));
        t.add(new Test("S07", "negative", "F2b", "one individual typed Aprendiz and Competencia",
            List.of(type("Aprendiz", "TY"), type("Competencia", "TY")), cons,
            "consistent", "inconsistent", "inconsistent", "inconsistent"));
        t.add(new Test("S08", "negative", "F2", "one question typed Objetiva and Subjetiva",
            List.of(type("Objetiva", "TQ"), type("Subjetiva", "TQ")), cons,
            "consistent", "inconsistent", "inconsistent", "inconsistent"));
        t.add(new Test("S09", "negative", "F2b + domain", "misuse: QUEST-0001 requer COMP-0001 (domain of requer is Competencia)",
            List.of(rel("QUEST-0001", "requer", "COMP-0001")), r -> "consistent; Competencia(QUEST-0001) " + ent(r, type("Competencia", "QUEST-0001")),
            "consistent; Competencia(QUEST-0001) entailed", "inconsistent", "inconsistent", "inconsistent"));
        t.add(new Test("S10", "negative", "F5 + F6", "contradictory record: DEMP-0003 (level NP-Aplicar) also receives NP-Lembrar",
            List.of(rel("DEMP-0003", "proficienciaAtingida", "NP-Lembrar")),
            r -> "consistent; NP-Aplicar = NP-Lembrar " + ent(r, df.getOWLSameIndividualAxiom(I("NP-Aplicar"), I("NP-Lembrar"))),
            "consistent; NP-Aplicar = NP-Lembrar not entailed", "consistent; NP-Aplicar = NP-Lembrar entailed",
            "consistent; NP-Aplicar = NP-Lembrar entailed", "inconsistent"));
        t.add(new Test("S11", "control", "F5 + F6", "record with two level individuals of the SAME tier (TLa, TLb : Aplicar)",
            List.of(type("Aplicar", "TLa"), type("Aplicar", "TLb"), type("DesempenhoDoAprendiz", "TP"),
                    rel("TP", "proficienciaAtingida", "TLa"), rel("TP", "proficienciaAtingida", "TLb")),
            r -> "consistent; TLa = TLb " + ent(r, df.getOWLSameIndividualAxiom(I("TLa"), I("TLb"))),
            "consistent; TLa = TLb not entailed", "consistent; TLa = TLb entailed",
            "consistent; TLa = TLb entailed", "consistent; TLa = TLb entailed"));
        t.add(new Test("S14", "positive", "F3", "DEMP-0004 has no recorded level: is 'some level' entailed?",
            List.of(), r -> "consistent; " + ent(r, some("proficienciaAtingida", "NiveisDeProficiencia", "DEMP-0004")),
            "consistent; not entailed", "consistent; entailed", "consistent; entailed", "consistent; entailed"));
        t.add(new Test("S15", "control", "F0b", "legitimate data: an Atitude described with :descricao",
            List.of(type("Atitude", "TA"), df.getOWLDataPropertyAssertionAxiom(DP("descricao"), I("TA"), "Valuing code readability")), cons,
            "consistent", "inconsistent", "consistent", "consistent"));
        t.add(new Test("S16", "control", "F0b", "legitimate data: performance record DEMP-0003 dated with :data",
            List.of(df.getOWLDataPropertyAssertionAxiom(DP("data"), I("DEMP-0003"), df.getOWLLiteral("2024-03-01T10:00:00Z", OWL2Datatype.XSD_DATE_TIME))),
            r -> "consistent; MilestoneDeAprendizagem(DEMP-0003) " + ent(r, type("MilestoneDeAprendizagem", "DEMP-0003")),
            "consistent; MilestoneDeAprendizagem(DEMP-0003) entailed", "inconsistent",
            "consistent; MilestoneDeAprendizagem(DEMP-0003) not entailed", "consistent; MilestoneDeAprendizagem(DEMP-0003) not entailed"));
        t.add(new Test("S17", "control", "v2.1 revision", "legitimate data: instructor INST-0001 enrolled as a learner in another course",
            List.of(type("Curso", "TC"), rel("INST-0001", "estaInscritoEm", "TC")),
            r -> "consistent; Aprendiz(INST-0001) " + ent(r, type("Aprendiz", "INST-0001")),
            "inconsistent", "inconsistent", "consistent; Aprendiz(INST-0001) entailed", "consistent; Aprendiz(INST-0001) entailed"));
        t.add(new Test("S18", "control", "v2.1 revision", "a learning resource with no competency: is 'addresses some competency' entailed?",
            List.of(type("RecursoDeAprendizagem", "TR")), r -> "consistent; " + ent(r, some("abordaCompetencia", "Competencia", "TR")),
            "consistent; not entailed", "consistent; entailed", "consistent; not entailed", "consistent; not entailed"));
        t.add(new Test("S19", "control", "F2b", "an individual typed Aprendiz and its superclass UsuarioDoAva",
            List.of(type("Aprendiz", "TU"), type("UsuarioDoAva", "TU")), cons, "consistent"));
        t.add(new Test("S20", "scope probe", "F2b", "contested pair: an assessment reused as a learning resource (Avaliacao and RecursoDeAprendizagem)",
            List.of(type("Avaliacao", "TAR"), type("RecursoDeAprendizagem", "TAR")), cons,
            "consistent", "inconsistent", "inconsistent", "inconsistent"));
        t.add(new Test("S21", "scope probe", "F2b", "contested pair: a course catalogued as a learning resource (Curso and RecursoDeAprendizagem)",
            List.of(type("Curso", "TCR"), type("RecursoDeAprendizagem", "TCR")), cons,
            "consistent", "inconsistent", "inconsistent", "inconsistent"));
        return t;
    }

    static OWLReasonerFactory factory(String name) throws Exception {
        if (name.equals("HermiT")) return new org.semanticweb.HermiT.ReasonerFactory();
        return (OWLReasonerFactory) Class.forName("openllet.owlapi.OpenlletReasonerFactory").getMethod("getInstance").invoke(null);
    }

    static boolean consistentWith(String file, String rz, List<OWLAxiom> facts) throws Exception {
        OWLOntologyManager m = OWLManager.createOWLOntologyManager();
        OWLOntology o = m.loadOntologyFromOntologyDocument(new File(file));
        o.addAxioms(new HashSet<>(facts));
        OWLReasoner r = factory(rz).createReasoner(o);
        boolean ok = r.isConsistent();
        r.dispose();
        return ok;
    }

    static void row(String v, String rz, String id, String kind, String fam, String desc, String exp, String res) {
        System.out.println(String.join("\t", v, rz, id, kind, fam, desc, exp, res, res.equals(exp) ? "yes" : "NO"));
    }

    public static void main(String[] args) throws Exception {
        List<String> versions = List.of("v1.0", "v2.0", "v2.1", "v2.2");
        System.out.println("version\treasoner\ttest\tkind\tfamily\tdescription\texpected\tobserved\tmatch");
        for (String pair : args) {
            String v = pair.substring(0, pair.indexOf('='));
            String file = pair.substring(pair.indexOf('=') + 1);
            int vi = versions.indexOf(v);
            for (String rz : List.of("HermiT", "Openllet")) {
                for (Test te : tests()) {
                    OWLOntologyManager m = OWLManager.createOWLOntologyManager();
                    OWLOntology o = m.loadOntologyFromOntologyDocument(new File(file));
                    o.addAxioms(new HashSet<>(te.facts()));
                    OWLReasoner r = factory(rz).createReasoner(o);
                    String res;
                    try { res = r.isConsistent() ? te.check().apply(r) : "inconsistent"; }
                    catch (Exception e) { res = "error: " + e.getClass().getSimpleName(); }
                    r.dispose();
                    String exp = te.expected().length == 1 ? te.expected()[0] : te.expected()[vi];
                    row(v, rz, te.id(), te.kind(), te.family(), te.description(), exp, res);
                }
                // S12: every pair of distinct Bloom tiers on one performance record
                int bad = 0, n = 0;
                for (int i = 0; i < TIERS.length; i++) for (int j = i + 1; j < TIERS.length; j++) {
                    n++;
                    List<OWLAxiom> f = List.of(type(TIERS[i], "TLi"), type(TIERS[j], "TLj"), type("DesempenhoDoAprendiz", "TP"),
                        rel("TP", "proficienciaAtingida", "TLi"), rel("TP", "proficienciaAtingida", "TLj"));
                    if (!consistentWith(file, rz, f)) bad++;
                }
                row(v, rz, "S12", "negative sweep", "F5 + F6", "one record carrying two levels of different tiers, all 15 tier pairs",
                    (vi == 3 ? "15" : "0") + " of 15 inconsistent", bad + " of " + n + " inconsistent");
                // S13: every pair of root classes on one individual
                bad = 0; n = 0;
                for (int i = 0; i < ROOTS.length; i++) for (int j = i + 1; j < ROOTS.length; j++) {
                    n++;
                    if (!consistentWith(file, rz, List.of(type(ROOTS[i], "TZ"), type(ROOTS[j], "TZ")))) bad++;
                }
                row(v, rz, "S13", "negative sweep", "F2b", "one individual typed with two root classes, all 78 root pairs",
                    (vi == 0 ? "1" : "78") + " of 78 inconsistent", bad + " of " + n + " inconsistent");
            }
        }
    }
}
