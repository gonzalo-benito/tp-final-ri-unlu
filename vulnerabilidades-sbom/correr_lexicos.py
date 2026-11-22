import argparse
import os

import pandas as pd
import pyterrier as pt

from lib.ColeccionPrueba import ColeccionPrueba
from lib.Evaluacion import Evaluacion
from lib.IndiceLexico import IndiceLexico


def main():
    parser = argparse.ArgumentParser(
        description="Indexa las CVE con Terrier y evalúa los modelos léxicos."
    )
    parser.add_argument("--corpus", default="datos/nvd/cves.jsonl")
    parser.add_argument("--coleccion", default="datos/coleccion")
    parser.add_argument("--indice", default="datos/indices/palabras")
    parser.add_argument(
        "--campos",
        nargs="+",
        default=IndiceLexico.CAMPOS,
        choices=IndiceLexico.CAMPOS,
        help="Campos que entran al índice (usar otra carpeta de índice si se cambian).",
    )
    parser.add_argument(
        "--tokenizacion", default="palabras", choices=["palabras", "ngramas"]
    )
    parser.add_argument("--n", type=int, default=4, help="Largo de los n-gramas.")
    parser.add_argument(
        "--particion", default="desarrollo", choices=["desarrollo", "prueba"]
    )
    parser.add_argument("--modelos", nargs="+", default=["BM25", "TF_IDF"])
    parser.add_argument("--resultados", default="resultados")
    parser.add_argument(
        "--nombre", default="", help="Sufijo para los archivos de resultados."
    )
    args = parser.parse_args()

    if not pt.java.started():
        pt.java.init()

    indice = IndiceLexico(args.indice, args.campos, args.tokenizacion, args.n)
    if not indice.existe():
        print("[INFO] Construyendo el índice (tarda unos minutos)...")
        indice.construir(args.corpus)

    consultas = [
        c
        for c in ColeccionPrueba.cargar_consultas(args.coleccion)
        if c["particion"] == args.particion
    ]
    evaluacion = Evaluacion(f"{args.coleccion}/qrels.txt", consultas)
    topicos = indice.consultas_df(consultas)
    print(
        f"[INFO] Partición {args.particion}: {len(topicos)} consultas, "
        f"{len(evaluacion.qrels)} juicios"
    )

    os.makedirs(args.resultados, exist_ok=True)
    filas = []
    for modelo in args.modelos:
        corrida = indice.recuperador(modelo).transform(topicos)
        destino = f"{args.resultados}/{args.particion}-{modelo}{args.nombre}.run"
        pt.io.write_results(corrida, destino)
        filas.extend(
            evaluacion.resumen(modelo + args.nombre, evaluacion.por_consulta(corrida))
        )

    tabla = pd.DataFrame(filas)
    tabla.to_csv(
        f"{args.resultados}/{args.particion}-lexicos{args.nombre}.tsv",
        sep="\t",
        index=False,
    )
    print(tabla.round(4).to_string(index=False))
    print(
        "[INFO] Para comparar corridas con pruebas de significancia: python3 -m evaluar"
    )


if __name__ == "__main__":
    main()
