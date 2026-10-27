/*
 * Testes de unidade dos axiomas da OntoLearn.
 * Cada teste acrescenta à ontologia apenas os fatos do próprio teste e
 * verifica, com um raciocinador OWL 2 DL, o comportamento esperado
 * (consistência, acarretamento ou inconsistência). A coluna "confere"
 * compara o resultado obtido com o esperado, registrado em cada teste.
 *
 * Execução (Java 11+; jars da OWL API 5.1.9, HermiT 1.4.3.517 e Openllet 2.6.5):
 *   java -Dstdout.encoding=UTF-8 -cp "jars/*" TestesAxiomas.java \
 *        v2.1=ontolearn-v2.1.owl "v2.1+ABox teste"=base_ampliada.owl > testes_axiomas.tsv
 */
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.owlapi.vocab.OWL2Datatype;
import java.io.File;
import java.util.*;
import java.util.function.Function;

public class TestesAxiomas {
    static final String NS = "http://www.ontolearn.com/ontologia#";
    static OWLDataFactory df = OWLManager.getOWLDataFactory();
    static OWLClass C(String n) { return df.getOWLClass(IRI.create(NS + n)); }
    static OWLObjectProperty OP(String n) { return df.getOWLObjectProperty(IRI.create(NS + n)); }
    static OWLDataProperty DP(String n) { return df.getOWLDataProperty(IRI.create(NS + n)); }
    static OWLNamedIndividual I(String n) { return df.getOWLNamedIndividual(IRI.create(NS + n)); }
    static OWLAxiom tipo(String c, String i) { return df.getOWLClassAssertionAxiom(C(c), I(i)); }
    static OWLAxiom rel(String s, String p, String o) { return df.getOWLObjectPropertyAssertionAxiom(OP(p), I(s), I(o)); }

    record Teste(String id, String familia, String descricao, String esperado, List<OWLAxiom> fatos,
                 Function<OWLReasoner, String> verificacao) {}

    static String acarreta(OWLReasoner r, OWLAxiom ax, String rotulo) {
        try {
            return (r.isEntailed(ax) ? "acarreta " : "não acarreta ") + rotulo;
        } catch (Exception e) {
            return "não avaliável (" + e.getClass().getSimpleName() + ")";
        }
    }

    static List<Teste> testes() {
        List<Teste> t = new ArrayList<>();
        t.add(new Teste("T01", "Consistência", "Ontologia com a ABox de 20 indivíduos", "consistente",
            List.of(), r -> "consistente"));
        t.add(new Teste("T02", "Taxonomia (Subjetiva ⊑ Questao)",
            "Indivíduo declarado apenas como Subjetiva é inferido como Questao?", "acarreta Questao(TS)",
            List.of(tipo("Subjetiva", "TS")), r -> acarreta(r, tipo("Questao", "TS"), "Questao(TS)")));
        t.add(new Teste("T03", "Transitividade (requer)",
            "Cadeia T3→COMP-0002→COMP-0001→T4: T3 requer T4?", "acarreta requer(T3, T4)",
            List.of(tipo("Competencia", "T3"), tipo("Competencia", "T4"),
                    rel("T3", "requer", "COMP-0002"), rel("COMP-0001", "requer", "T4")),
            r -> acarreta(r, rel("T3", "requer", "T4"), "requer(T3, T4)")));
        t.add(new Teste("T04", "Propriedades inversas",
            "Desempenho registrado só no sentido Desempenho→Aprendiz é recuperado a partir do aprendiz?", "acarreta desempenhoCompetencias(APR-0001, TD)",
            List.of(tipo("DesempenhoDoAprendiz", "TD"), rel("TD", "competenciasDoDesempenho", "APR-0001")),
            r -> acarreta(r, rel("APR-0001", "desempenhoCompetencias", "TD"), "desempenhoCompetencias(APR-0001, TD)")));
        t.add(new Teste("T05", "Hierarquia de propriedades (CHA)",
            "COMP-0002 ehCompostoDeConhecimento KNOW-001 ⇒ temComponenteKSA?", "acarreta temComponenteKSA(COMP-0002, KNOW-001)",
            List.of(), r -> acarreta(r, rel("COMP-0002", "temComponenteKSA", "KNOW-001"), "temComponenteKSA(COMP-0002, KNOW-001)")));
        t.add(new Teste("T06", "Disjunção CHA",
            "Indivíduo declarado Conhecimento e Habilidade", "inconsistente",
            List.of(tipo("Conhecimento", "TX"), tipo("Habilidade", "TX")), r -> "consistente"));
        t.add(new Teste("T07", "Disjunção das classes-raiz",
            "Indivíduo declarado Aprendiz e Competencia", "inconsistente",
            List.of(tipo("Aprendiz", "TY"), tipo("Competencia", "TY")), r -> "consistente"));
        t.add(new Teste("T08", "Disjunção Objetiva/Subjetiva",
            "Questão declarada Objetiva e Subjetiva", "inconsistente",
            List.of(tipo("Objetiva", "TQ"), tipo("Subjetiva", "TQ")), r -> "consistente"));
        t.add(new Teste("T09", "Domínio + disjunção",
            "Uso indevido: QUEST-0001 requer COMP-0001 (domínio de requer é Competencia)", "inconsistente",
            List.of(rel("QUEST-0001", "requer", "COMP-0001")),
            r -> acarreta(r, tipo("Competencia", "QUEST-0001"), "Competencia(QUEST-0001)")));
        t.add(new Teste("T10", "Funcionalidade sem UNA",
            "DEMP-0003 recebe um segundo nível (NP-Lembrar)", "acarreta NP-Aplicar = NP-Lembrar",
            List.of(rel("DEMP-0003", "proficienciaAtingida", "NP-Lembrar")),
            r -> acarreta(r, df.getOWLSameIndividualAxiom(I("NP-Aplicar"), I("NP-Lembrar")), "NP-Aplicar = NP-Lembrar")));
        t.add(new Teste("T11", "Funcionalidade + nomes distintos",
            "T10 + DifferentIndividuals(NP-Aplicar, NP-Lembrar)", "inconsistente",
            List.of(rel("DEMP-0003", "proficienciaAtingida", "NP-Lembrar"),
                    df.getOWLDifferentIndividualsAxiom(I("NP-Aplicar"), I("NP-Lembrar"))), r -> "consistente"));
        t.add(new Teste("T12", "Restrição existencial (mundo aberto)",
            "DEMP-0004 não tem nível registrado", "consistente; acarreta ∃proficienciaAtingida.NiveisDeProficiencia(DEMP-0004)",
            List.of(), r -> "consistente; " + acarreta(r,
                df.getOWLClassAssertionAxiom(df.getOWLObjectSomeValuesFrom(OP("proficienciaAtingida"), C("NiveisDeProficiencia")), I("DEMP-0004")),
                "∃proficienciaAtingida.NiveisDeProficiencia(DEMP-0004)")));
        t.add(new Teste("T13", "Domínio de descricao",
            "Atitude descrita com a propriedade descricao", "consistente",
            List.of(tipo("Atitude", "TA"), df.getOWLDataPropertyAssertionAxiom(DP("descricao"), I("TA"), "Valorizar a legibilidade do código")),
            r -> "consistente"));
        t.add(new Teste("T14", "Domínio de data",
            "Registro de desempenho DEMP-0003 datado com a propriedade data", "consistente; não acarreta MilestoneDeAprendizagem(DEMP-0003)",
            List.of(df.getOWLDataPropertyAssertionAxiom(DP("data"), I("DEMP-0003"),
                    df.getOWLLiteral("2024-03-01T10:00:00Z", OWL2Datatype.XSD_DATE_TIME))),
            r -> "consistente; " + acarreta(r, tipo("MilestoneDeAprendizagem", "DEMP-0003"), "MilestoneDeAprendizagem(DEMP-0003)")));
        t.add(new Teste("T15", "Papéis acumulados (Aprendiz e Instrutor)",
            "Instrutor INST-0001 inscrito como aprendiz em um curso (estaInscritoEm)", "consistente; acarreta Aprendiz(INST-0001)",
            List.of(tipo("Curso", "TC"), rel("INST-0001", "estaInscritoEm", "TC")),
            r -> "consistente; " + acarreta(r, tipo("Aprendiz", "INST-0001"), "Aprendiz(INST-0001)")));
        t.add(new Teste("T16", "Participação opcional (recurso)",
            "Recurso de aprendizagem sem competência associada", "consistente; não acarreta ∃abordaCompetencia.Competencia(TR)",
            List.of(tipo("RecursoDeAprendizagem", "TR")),
            r -> "consistente; " + acarreta(r,
                df.getOWLClassAssertionAxiom(df.getOWLObjectSomeValuesFrom(OP("abordaCompetencia"), C("Competencia")), I("TR")),
                "∃abordaCompetencia.Competencia(TR)")));
        return t;
    }

    static OWLReasonerFactory fabrica(String nome) throws Exception {
        if (nome.equals("HermiT")) return new org.semanticweb.HermiT.ReasonerFactory();
        return (OWLReasonerFactory) Class.forName("openllet.owlapi.OpenlletReasonerFactory").getMethod("getInstance").invoke(null);
    }

    public static void main(String[] args) throws Exception {
        System.out.println("versao\traciocinador\tteste\tfamilia\tdescricao\tesperado\tresultado\tconfere");
        for (String par : args) {
            String versao = par.substring(0, par.indexOf('='));
            String arq = par.substring(par.indexOf('=') + 1);
            for (String rz : List.of("HermiT", "Openllet")) {
                for (Teste te : testes()) {
                    OWLOntologyManager m = OWLManager.createOWLOntologyManager();
                    OWLOntology o = m.loadOntologyFromOntologyDocument(new File(arq));
                    o.addAxioms(new HashSet<>(te.fatos()));
                    OWLReasoner r = fabrica(rz).createReasoner(o);
                    String res;
                    try {
                        res = r.isConsistent() ? te.verificacao().apply(r) : "inconsistente";
                    } catch (Exception e) {
                        res = "erro: " + e.getClass().getSimpleName();
                    }
                    r.dispose();
                    System.out.println(versao + "\t" + rz + "\t" + te.id() + "\t" + te.familia() + "\t" + te.descricao() + "\t" + te.esperado() + "\t" + res + "\t" + (res.equals(te.esperado()) ? "sim" : "NÃO"));
                }
            }
        }
    }
}
