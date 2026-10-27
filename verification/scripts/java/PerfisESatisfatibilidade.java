// Verifica, para cada arquivo OWL informado:
//  (1) pertinência aos perfis OWL 2 DL, EL, QL e RL (OWL API 5.1.9), com a
//      contagem de violações por tipo;
//  (2) consistência e satisfatibilidade de todas as classes nomeadas (HermiT);
//  (3) subsunções entre classes nomeadas inferidas pelo raciocinador e que
//      não decorrem do fecho transitivo da hierarquia declarada.
// Uso: java -cp "jars/*" PerfisESatisfatibilidade.java arquivo1.owl [arquivo2.owl ...]
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.profiles.*;
import org.semanticweb.owlapi.reasoner.*;
import org.semanticweb.owlapi.search.EntitySearcher;
import org.semanticweb.HermiT.ReasonerFactory;
import java.io.File;
import java.util.*;

public class PerfisESatisfatibilidade {
  public static void main(String[] args) throws Exception {
    for (String f : args) {
      OWLOntologyManager m = OWLManager.createOWLOntologyManager();
      OWLOntology o = m.loadOntologyFromOntologyDocument(new File(f));
      System.out.println("### " + new File(f).getName());
      Map<String, OWLProfile> perfis = new LinkedHashMap<>();
      perfis.put("OWL 2 DL", new OWL2DLProfile());
      perfis.put("OWL 2 EL", new OWL2ELProfile());
      perfis.put("OWL 2 QL", new OWL2QLProfile());
      perfis.put("OWL 2 RL", new OWL2RLProfile());
      for (Map.Entry<String, OWLProfile> e : perfis.entrySet()) {
        OWLProfileReport r = e.getValue().checkOntology(o);
        Map<String, Integer> c = new TreeMap<>();
        for (OWLProfileViolation v : r.getViolations()) c.merge(v.getClass().getSimpleName(), 1, Integer::sum);
        System.out.println(e.getKey() + "\tno perfil=" + r.isInProfile() + "\tviolações=" + r.getViolations().size() + "\t" + c);
      }
      OWLReasoner rz = new ReasonerFactory().createReasoner(o);
      boolean consistente = rz.isConsistent();
      System.out.println("Consistente (HermiT): " + consistente);
      if (!consistente) continue;
      Set<OWLClass> insat = rz.getUnsatisfiableClasses().getEntitiesMinusBottom();
      System.out.println("Classes insatisfatíveis: " + insat.size() + " " + insat);
      // fecho transitivo da hierarquia declarada (apenas classes nomeadas)
      Map<OWLClass, Set<OWLClass>> declarada = new HashMap<>();
      for (OWLSubClassOfAxiom ax : o.getAxioms(AxiomType.SUBCLASS_OF)) {
        if (!ax.getSubClass().isAnonymous() && !ax.getSuperClass().isAnonymous()) {
          declarada.computeIfAbsent(ax.getSubClass().asOWLClass(), k -> new HashSet<>()).add(ax.getSuperClass().asOWLClass());
        }
      }
      int novas = 0;
      List<String> lista = new ArrayList<>();
      for (OWLClass c : o.getClassesInSignature()) {
        Set<OWLClass> fecho = new HashSet<>();
        Deque<OWLClass> pilha = new ArrayDeque<>(declarada.getOrDefault(c, Set.of()));
        while (!pilha.isEmpty()) { OWLClass s = pilha.pop(); if (fecho.add(s)) pilha.addAll(declarada.getOrDefault(s, Set.of())); }
        for (OWLClass s : rz.getSuperClasses(c, false).getFlattened()) {
          if (s.isOWLThing()) continue;
          if (!fecho.contains(s)) { novas++; lista.add(c.getIRI().getShortForm() + " ⊑ " + s.getIRI().getShortForm()); }
        }
      }
      System.out.println("Subsunções inferidas entre classes nomeadas fora do fecho declarado: " + novas + " " + lista);
      rz.dispose();
      System.out.println();
    }
  }
}
