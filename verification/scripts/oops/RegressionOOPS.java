import es.upm.fi.oeg.oops.Checker;
import es.upm.fi.oeg.oops.CheckersCatalogue;
import es.upm.fi.oeg.oops.Linter;
import es.upm.fi.oeg.oops.ModelLoader;
import es.upm.fi.oeg.oops.Report;
import es.upm.fi.oeg.oops.SrcModel;
import es.upm.fi.oeg.oops.SrcSpec;
import es.upm.fi.oeg.oops.SrcType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.RDFDataMgr;

/**
 * Reproduz, sem JUnit, o teste de regressão oficial do OOPS! (src/test/java/.../RegressionTests.java,
 * commit 11572ea): para cada ontologia de teste do repositório, executa todos os verificadores pelo caminho
 * RDF_CODE e compara a saída RDF, normalizada pela mesma consulta CONSTRUCT do teste oficial, com a saída
 * esperada registrada no repositório (isomorfismo de grafos). A saída obtida é serializada em Turtle por
 * Report.toTurtle e relida antes da comparação, como a saída esperada, que também é um arquivo Turtle.
 *
 * Uso: java -cp <classes do OOPS!>:<dependências> RegressionOOPS.java <pasta src/test/resources/data>
 */
public class RegressionOOPS {

    static final String NORMALIZE = "PREFIX oops: <http://oops.linkeddata.es/def#>\n" + "CONSTRUCT {\n"
            + "  ?s2 ?p ?o2 .\n" + "}\n" + "WHERE {\n" + "  ?s ?p ?o .\n" + "\n" + "  BIND(\n" + "    IF(\n"
            + "      STRSTARTS(STR(?s), \"http://oops.linkeddata.es/data/\"),\n" + "      BNODE(),\n" + "      ?s\n"
            + "    ) AS ?s2\n" + "  )\n" + "\n" + "  BIND(\n" + "    IF(\n"
            + "      (STRSTARTS(STR(?o), \"http://oops.linkeddata.es/data/\") &&\n"
            + "       REGEX(STR(?o), \"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\")),\n"
            + "      BNODE(),\n" + "      ?o\n" + "    ) AS ?o2\n" + "  )\n" + "}";

    // Mesma lista do @ValueSource do teste oficial (P34 está comentado no original).
    static final String[] TESTS = { "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P10", "P10-A", "P10-B",
            "P10-C", "P11", "P12", "P13", "P19", "P20", "P21", "P22M1", "P22M2", "P22M3", "P22M4", "P24", "P25",
            "P26", "P27", "P28", "P29", "P30", "P31", "P32", "P33", "P35", "P36", "P38", "P39", "P40", "P41" };

    static Model normalize(final Model model) {
        return QueryExecutionFactory.create(NORMALIZE, model).execConstruct();
    }

    public static void main(final String[] args) throws Exception {
        final Path data = Path.of(args[0]);
        int ok = 0;
        final StringBuilder falhas = new StringBuilder();
        for (final String name : TESTS) {
            final String content = Files.readString(data.resolve("input/" + name + ".owl"), StandardCharsets.UTF_8);
            final SrcSpec srcSpec = new SrcSpec(SrcType.RDF_CODE, null, content, null);
            final List<Checker> checkers = CheckersCatalogue.getAllCheckers();
            final SrcModel srcModel = ModelLoader.load(srcSpec);
            final Report report = new Linter().partialExecution(srcModel, Collections.emptyList(), checkers);
            final Model expected = normalize(RDFDataMgr.loadModel(data.resolve("output/" + name + ".ttl").toString()));
            // A saída esperada do repositório é um arquivo Turtle; a saída obtida passa pela mesma serialização
            // (Report.toTurtle, usada pelo serviço e pela linha de comando) antes da comparação.
            final Path tmp = Files.createTempFile("oops-" + name + "-", ".ttl");
            report.toTurtle(tmp.toFile());
            final Model actual = normalize(RDFDataMgr.loadModel(tmp.toString()));
            Files.delete(tmp);
            final boolean iso = expected.isIsomorphicWith(actual);
            System.out.println(name + "\t" + (iso ? "confere" : "DIFERE") + "\tesperado=" + expected.size()
                    + " triplas\tobtido=" + actual.size() + " triplas");
            if (iso) {
                ok++;
            } else {
                falhas.append(name).append(' ');
            }
        }
        System.out.println("Total: " + ok + "/" + TESTS.length + " conferem" + (falhas.length() > 0
                ? " | diferem: " + falhas.toString().trim() : ""));
    }
}
