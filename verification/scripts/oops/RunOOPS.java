import es.upm.fi.oeg.oops.Checker;
import es.upm.fi.oeg.oops.CheckerInfo;
import es.upm.fi.oeg.oops.CheckersCatalogue;
import es.upm.fi.oeg.oops.Importance;
import es.upm.fi.oeg.oops.Linter;
import es.upm.fi.oeg.oops.ModelLoader;
import es.upm.fi.oeg.oops.Pitfall;
import es.upm.fi.oeg.oops.PitfallId;
import es.upm.fi.oeg.oops.PitfallInfo;
import es.upm.fi.oeg.oops.Report;
import es.upm.fi.oeg.oops.RuleScope;
import es.upm.fi.oeg.oops.SrcModel;
import es.upm.fi.oeg.oops.SrcSpec;
import es.upm.fi.oeg.oops.SrcType;
import es.upm.fi.oeg.oops.Warning;
import es.upm.fi.oeg.oops.WarningType;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Collection;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.apache.jena.ontology.OntResource;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;

/**
 * Executa o OOPS! sobre um arquivo local reproduzindo o caminho do formulário de entrada direta do
 * serviço web (report-advanced.jsp): SrcSpec(RDF_CODE), ModelLoader.load, todos os verificadores do
 * catálogo e Linter.partialExecution(srcModel, null, checkers). Imprime o resultado no mesmo formato
 * textual da página de resultados e grava a saída RDF oficial do relatório (Turtle).
 *
 * Uso: java -cp <classes do OOPS!>:<dependências> RunOOPS.java <ontologia> [<saida.ttl>]
 */
public class RunOOPS {

    private static String nome(final Resource res) {
        return res.isURIResource() ? res.getURI() : "(nó anônimo)";
    }

    public static void main(final String[] args) throws Exception {
        final Path in = Path.of(args[0]);
        final byte[] bytes = Files.readAllBytes(in);
        final String rdf = new String(bytes, StandardCharsets.UTF_8);
        final String sha = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));

        final SrcSpec srcSpec = new SrcSpec(SrcType.RDF_CODE, null, rdf, null);
        final SrcModel srcModel = ModelLoader.load(srcSpec);
        final List<Checker> checkers = CheckersCatalogue.getAllCheckers();
        final Report report = new Linter().partialExecution(srcModel, null, checkers);
        final Map<PitfallId, PitfallInfo> pitfallInfos = checkers.stream()
                .map((checker) -> checker.getInfo().detectsPitfalls()).flatMap(Collection::stream)
                .collect(Collectors.toMap(PitfallInfo::getId, Function.identity()));
        final Model model = report.getOutputModel();
        final Property affected = model.getProperty(Linter.NS_OOPS_DEF + "hasAffectedElement");

        final StringBuilder out = new StringBuilder();
        out.append("Arquivo submetido: ").append(in.getFileName()).append('\n');
        out.append("  ").append(bytes.length).append(" bytes; SHA-256 ").append(sha).append('\n');
        out.append("Verificadores executados: ").append(checkers.size()).append(" (catálogo completo)\n");
        out.append("Pitfalls cobertos pelos verificadores: ")
                .append(pitfallInfos.keySet().stream().sorted().map(PitfallId::toString)
                        .collect(Collectors.joining(", ")))
                .append('\n');
        out.append("Elementos contados pelo OOPS!: ").append(report.getNumClasses()).append(" classes, ")
                .append(report.getNumProperties()).append(" propriedades\n");
        out.append("Exceções durante a análise: ").append(report.getExceptions().size()).append('\n');
        for (final Throwable exc : report.getExceptions()) {
            out.append("  ! ").append(exc).append('\n');
        }
        out.append('\n').append("Evaluation results\n");

        final Map<PitfallId, List<Pitfall>> pitfalls = report.getPitfalls();
        Importance highest = null;
        if (pitfalls.isEmpty()) {
            if (!report.getExceptions().isEmpty()) {
                out.append("Something went wrong.\n");
            } else {
                out.append("Congratulations! No pitfalls detected.\n");
                out.append("Conformance badge: \"Free of pitfalls\"\n");
            }
        } else {
            out.append("Pitfalls detected:\n");
            for (final Map.Entry<PitfallId, List<Pitfall>> entry : pitfalls.entrySet()) {
                final PitfallId pfId = entry.getKey();
                final PitfallInfo info = pitfallInfos.get(pfId);
                final List<Pitfall> pfs = entry.getValue();
                final Importance importance = info.getImportance();
                if (highest == null || highest.compareTo(importance) < 0) {
                    highest = importance;
                }
                final String scope;
                if (info.getScope() == RuleScope.ONTOLOGY) {
                    scope = "Ontology*";
                } else if (pfs.size() == 1) {
                    scope = "1 case";
                } else {
                    scope = pfs.size() + " cases";
                }
                out.append("Results for ").append(pfId).append(": ").append(info.getTitle()).append(". ")
                        .append(importance).append(" - ").append(scope).append('\n');
                if (info.getScope() == RuleScope.ONTOLOGY) {
                    out.append("  *This pitfall applies to the ontology in general instead of specific elements.\n");
                    continue;
                }
                boolean compound = false;
                for (final Pitfall pf : pfs) {
                    for (final Resource res : pf.getResources()) {
                        compound |= res.hasProperty(affected);
                    }
                }
                if (!compound) {
                    out.append("  • ").append(info.getAccomp() == null
                            ? "This pitfall appears in the following elements" : info.getAccomp()).append(":\n");
                }
                for (final Pitfall pf : pfs) {
                    for (final Resource res : pf.getResources()) {
                        if (res.hasProperty(affected)) {
                            out.append("  • ").append(info.getAccomp()).append(":\n");
                            for (final Statement stmt : res.listProperties(affected).toList()) {
                                final RDFNode obj = stmt.getObject();
                                out.append("    › ").append(obj.isResource() ? nome(obj.asResource()) : "unknown")
                                        .append('\n');
                            }
                        } else {
                            out.append("  › ").append(nome(res)).append('\n');
                        }
                    }
                }
            }
        }
        if (!report.getWarnings().isEmpty()) {
            out.append("\nWarnings:\n");
            for (final Map.Entry<WarningType, List<Warning>> wEntry : report.getWarnings().entrySet()) {
                final List<Warning> ws = wEntry.getValue();
                out.append(wEntry.getKey()).append(" related warnings | ").append(ws.size())
                        .append(ws.size() > 1 ? " cases" : " case").append('\n');
                for (final Warning w : ws) {
                    final CheckerInfo ci = w.getCheckerInfo();
                    out.append("  ").append(w.toString().replace('\n', ' ')).append(" (Origin: Checker ")
                            .append(ci.getId()).append(")\n");
                    final Set<OntResource> sc = w.getScope();
                    for (final OntResource r : sc) {
                        out.append("    - ").append(nome(r)).append('\n');
                    }
                }
            }
        }
        if (highest != null) {
            out.append("\nAccording to the highest importance level of pitfall found in your ontology, ")
                    .append("the conformance badge suggested is \"").append(highest).append(" pitfalls\".\n");
        }
        System.out.print(out);
        if (args.length > 1) {
            report.toTurtle(new File(args[1]));
        }
    }
}
