import argparse
import os

import pandas as pd
import pyterrier as pt

from lib.ColeccionPrueba import ColeccionPrueba
from lib.Evaluacion import Evaluacion


def main():
    parser = argparse.ArgumentParser(
        description="Evalúa corridas TREC y las compara contra una línea de base."
    )
    parser.add_argument("--corridas", nargs="+", required=True, help="nombre=archivo.run")
    parser.add_argument("--base", default="BM25", help="Nombre de la corrida de base.")
    parser.add_argument("--coleccion", default="datos/coleccion")
    parser.add_argument("--particion", default="desarrollo", choices=["desarrollo", "prueba"])
    parser.add_argument("--salida", default="", help="Prefijo para guardar las tablas (TSV).")
    args = parser.parse_args()

    consultas = [
        c for c in ColeccionPrueba.cargar_consultas(args.coleccion) if c["particion"] == args.particion
    ]
    evaluacion = Evaluacion(f"{args.coleccion}/qrels.txt", consultas)

    detalles = {}
    filas = []
    for item in args.corridas:
        nombre, ruta = item.split("=", 1)
        detalles[nombre] = evaluacion.por_consulta(pt.io.read_results(ruta))
        filas.extend(evaluacion.resumen(nombre, detalles[nombre]))

    tabla = pd.DataFrame(filas)
    columnas = ["sistema", "estrato", "nDCG@10", "AP", "RR", "R@10", "R@100", "P@10"]
    print(tabla[columnas].round(4).to_string(index=False))

    otros = {n: d for n, d in detalles.items() if n != args.base}
    comparacion = Evaluacion.comparar(detalles[args.base], otros, ["nDCG@10", "AP", "R@100"])
    print()
    print(comparacion.round(4).to_string(index=False))

    if args.salida:
        os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
        tabla[columnas].to_csv(f"{args.salida}-metricas.tsv", sep="\t", index=False)
        comparacion.to_csv(f"{args.salida}-significancia.tsv", sep="\t", index=False)


if __name__ == "__main__":
    main()
