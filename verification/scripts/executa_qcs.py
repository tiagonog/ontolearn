"""Executa as Questões de Competência (QC) da OntoLearn v2.1 e compara com o gabarito.

Para cada caso do gabarito (dados/gabarito_qcs.json), a consulta SPARQL é
parametrizada e executada em dois regimes:
  - declarado: somente as triplas declaradas (o que a aba SPARQL do Protégé vê);
  - inferido : triplas declaradas + inferências materializadas pelo HermiT
               (ROBOT reason, geradores SubClass/ClassAssertion/PropertyAssertion,
               --include-indirect true).
As chaves de base do gabarito (registrado em 11/10/2026) designam a ABox de
referência ("v2.0") e a base ampliada ("v2.0+teste"); a v2.1 não altera os
indivíduos nem as asserções dessas bases usados pelas consultas.
Uso: python3 executa_qcs.py <pasta Material_Suporte_Revisao>
"""
import csv, hashlib, json, re, sys
from pathlib import Path
from rdflib import Graph

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SPARQL = BASE / "sparql"
BASES = BASE / "dados" / "bases"
ARQ = {
    ("v2.0", "declarado"): BASES / "base_referencia.owl",
    ("v2.0", "inferido"): BASES / "base_referencia_inferida.owl",
    ("v2.0+teste", "declarado"): BASES / "base_ampliada.owl",
    ("v2.0+teste", "inferido"): BASES / "base_ampliada_inferida.owl",
}
NOME = {"v2.0": "ABox de referência", "v2.0+teste": "base ampliada"}

def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()

def parametriza(texto, params):
    linhas = []
    for linha in texto.splitlines():
        m = re.search(r"#\s*parâmetro:\s*(\w+)", linha)
        if m and m.group(1) in params:
            chave, valor = m.group(1), params[m.group(1)]
            termo = f":{valor}" if chave == "nivel" else json.dumps(valor, ensure_ascii=False)
            linha = re.sub(r"\{[^}]*\}", "{ " + termo + " }", linha, count=1)
        linhas.append(linha)
    return "\n".join(linhas)

def executa(g, consulta):
    res = g.query(consulta)
    return {tuple("" if v is None else str(v) for v in linha) for linha in res}

def main():
    gab = json.loads((BASE / "dados" / "gabarito_qcs.json").read_text(encoding="utf-8"))
    grafos = {}
    for chave, arq in ARQ.items():
        g = Graph(); g.parse(arq)
        grafos[chave] = g
    saida, relat = [], []
    relat.append("# Resultados das Questões de Competência - OntoLearn v2.1\n")
    relat.append("Arquivos de entrada (MD5):\n")
    for (b, r), arq in ARQ.items():
        relat.append(f"- {NOME[b]} / {r}: `{arq.name}` - {md5(arq)} - {len(grafos[(b, r)])} triplas")
    relat.append("")
    for caso in gab["casos"]:
        q = parametriza((SPARQL / caso["consulta"]).read_text(encoding="utf-8"), caso["parametros"])
        esperado = {tuple(t) for t in caso["esperado"]}
        dep = {tuple(t) for t in caso["dependem_de_inferencia"]}
        esp_decl = esperado - dep
        obt_decl = executa(grafos[(caso["base"], "declarado")], q)
        obt_inf = executa(grafos[(caso["base"], "inferido")], q)
        ok_decl = obt_decl == esp_decl
        ok_inf = obt_inf == esperado
        saida.append({
            "id": caso["id"], "qc": caso["qc"], "consulta": caso["consulta"], "base": caso["base"],
            "parametros": "; ".join(f"{k}={v}" for k, v in caso["parametros"].items()),
            "n_esperado": len(esperado), "n_dependem_inferencia": len(dep),
            "n_declarado": len(obt_decl), "n_inferido": len(obt_inf),
            "confere_declarado": "sim" if ok_decl else "NÃO",
            "confere_inferido": "sim" if ok_inf else "NÃO",
            "obtido_inferido": " | ".join(", ".join(t) for t in sorted(obt_inf)) or "(vazio)",
        })
        relat.append(f"## {caso['id']} ({caso['consulta']}, {NOME[caso['base']]})")
        relat.append(f"Parâmetros: {caso['parametros']}")
        relat.append(f"- Esperado ({len(esperado)}): {sorted(esperado)}")
        relat.append(f"- Declarado ({len(obt_decl)}): {sorted(obt_decl)} -> {'confere' if ok_decl else 'DIVERGE'}")
        relat.append(f"- Inferido  ({len(obt_inf)}): {sorted(obt_inf)} -> {'confere' if ok_inf else 'DIVERGE'}")
        if caso.get("nota"):
            relat.append(f"- Nota: {caso['nota']}")
        relat.append("")
    with open(BASE / "dados" / "resultados_qcs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(saida[0].keys())); w.writeheader(); w.writerows(saida)
    (BASE / "relatorios" / "resultados_qcs.md").write_text("\n".join(relat), encoding="utf-8")
    tot = len(saida); okd = sum(r["confere_declarado"] == "sim" for r in saida); oki = sum(r["confere_inferido"] == "sim" for r in saida)
    print(f"{tot} casos | conferem (declarado vs. esperado sem inferência): {okd}/{tot} | conferem (inferido vs. esperado): {oki}/{tot}")
    for r in saida:
        print(f"{r['id']:7} {r['base']:11} esp={r['n_esperado']} dep={r['n_dependem_inferencia']} decl={r['n_declarado']} inf={r['n_inferido']} {r['confere_declarado']}/{r['confere_inferido']}  {r['obtido_inferido']}")

if __name__ == "__main__":
    main()
