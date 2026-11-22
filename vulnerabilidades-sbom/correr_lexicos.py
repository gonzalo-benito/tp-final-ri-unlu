import argparse
import os

import ir_measures
import pandas as pd
import pyterrier as pt
from ir_measures import AP, P, R, RR, nDCG
from scipy import stats

from lib.ColeccionPrueba import ColeccionPrueba
from lib.IndiceLexico import IndiceLexico

METRICAS = [R @ 10, R @ 100, nDCG @ 10, AP, RR, P @ 10]


def evaluar(qrels, corrida: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    corrida = corrida.rename(columns={"qid": "query_id", "docno": "doc_id"})
    agregadas = ir_measures.calc_aggregate(METRICAS, qrels, corrida)
    por_consulta = pd.DataFrame(
        [(m.query_id, str(m.measure), m.value) for m in ir_measures.iter_calc(METRICAS, qrels, corrida)],
        columns=["qid", "metrica", "valor"],
    )
    return {str(m): v for m, v in agregadas.items()}, por_consulta


def main():
    parser = argparse.ArgumentParser(
        description="Indexa las CVE con Terrier y evalúa los modelos léxicos de base."
    )
    parser.add_argument("--corpus", default="datos/nvd/cves.jsonl")
    parser.add_argument("--coleccion", default="datos/coleccion")
    parser.add_argument("--indice", default="datos/indices/palabras")
    parser.add_argument(
        "--campos",
        nargs="+",
        default=IndiceLexico.CAMPOS,
        choices=IndiceLexico.CAMPOS,
        help="Campos del registro que entran al índice (usar otra carpeta de índice si se cambian).",
    )
    parser.add_argument("--tokenizacion", default="palabras", choices=["palabras", "ngramas"])
    parser.add_argument("--n", type=int, default=4, help="Largo de los n-gramas de caracteres.")
    parser.add_argument("--particion", default="desarrollo", choices=["desarrollo", "prueba"])
    parser.add_argument("--modelos", nargs="+", default=["BM25", "TF_IDF"])
    parser.add_argument("--resultados", default="resultados")
    parser.add_argument("--nombre", default="", help="Sufijo para los archivos de resultados.")
    args = parser.parse_args()

    if not pt.java.started():
        pt.java.init()

    indice = IndiceLexico(args.indice, args.campos, args.tokenizacion, args.n)
    if not indice.existe():
        print("Construyendo el índice (tarda unos minutos)...")
        indice.construir(args.corpus)

    consultas = [
        c for c in ColeccionPrueba.cargar_consultas(args.coleccion) if c["particion"] == args.particion
    ]
    estrato = {c["qid"]: c["estrato"] for c in consultas}
    topicos = indice.consultas_df(consultas)
    qrels = [q for q in ir_measures.read_trec_qrels(f"{args.coleccion}/qrels.txt") if q.query_id in estrato]
    print(f"Partición {args.particion}: {len(topicos)} consultas, {len(qrels)} juicios")

    os.makedirs(args.resultados, exist_ok=True)
    filas = []
    por_consulta = {}
    for modelo in args.modelos:
        corrida = indice.recuperador(modelo).transform(topicos)
        pt.io.write_results(corrida, f"{args.resultados}/{args.particion}-{modelo}{args.nombre}.run")
        agregadas, detalle = evaluar(qrels, corrida)
        por_consulta[modelo] = detalle
        filas.append({"modelo": modelo, "estrato": "todos", **agregadas})
        detalle["estrato"] = detalle["qid"].map(estrato)
        for nombre, grupo in detalle.groupby("estrato"):
            # ir_measures no devuelve fila para las consultas sin resultados, se cuentan como 0
            n = sum(1 for e in estrato.values() if e == nombre)
            medias = (grupo.groupby("metrica")["valor"].sum() / n).to_dict()
            filas.append({"modelo": modelo, "estrato": f"{nombre} (n={n})", **medias})

    tabla = pd.DataFrame(filas)
    tabla.to_csv(f"{args.resultados}/{args.particion}-lexicos{args.nombre}.tsv", sep="\t", index=False)
    print(tabla.round(4).to_string(index=False))

    # comparación pareada contra BM25, que es la línea de base
    if "BM25" in por_consulta:
        base = por_consulta["BM25"]
        for modelo, detalle in por_consulta.items():
            if modelo == "BM25":
                continue
            for metrica in ["nDCG@10", "AP", "R@100"]:
                a = base[base.metrica == metrica].set_index("qid")["valor"]
                b = detalle[detalle.metrica == metrica].set_index("qid")["valor"]
                a, b = a.align(b, fill_value=0.0)
                t = stats.ttest_rel(a, b)
                w = stats.wilcoxon(a, b, zero_method="zsplit")
                print(
                    f"BM25 vs {modelo} en {metrica}: {a.mean():.4f} vs {b.mean():.4f}, "
                    f"t pareada p={t.pvalue:.2g}, Wilcoxon p={w.pvalue:.2g}"
                )


if __name__ == "__main__":
    main()
