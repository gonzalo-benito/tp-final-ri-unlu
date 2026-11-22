import argparse
import os

import pyterrier as pt

from lib.ColeccionPrueba import ColeccionPrueba
from lib.IndiceDenso import IndiceDenso


def main():
    parser = argparse.ArgumentParser(
        description="Codifica las CVE con Sentence-BERT, las indexa con FAISS y corre las consultas."
    )
    parser.add_argument("--corpus", default="datos/nvd/cves.jsonl")
    parser.add_argument("--coleccion", default="datos/coleccion")
    parser.add_argument("--indice", default="datos/indices/denso")
    parser.add_argument("--modelo", default=IndiceDenso.MODELO)
    parser.add_argument(
        "--particion", default="desarrollo", choices=["desarrollo", "prueba"]
    )
    parser.add_argument("--resultados", default="resultados")
    parser.add_argument("--nombre", default="denso")
    args = parser.parse_args()

    indice = IndiceDenso(args.indice, args.modelo)
    if not indice.existe():
        print(
            "[INFO] Codificando el corpus (en CPU tarda bastante, se hace una sola vez)..."
        )
        indice.construir(args.corpus)

    consultas = [
        c
        for c in ColeccionPrueba.cargar_consultas(args.coleccion)
        if c["particion"] == args.particion
    ]
    corrida = indice.buscar(consultas)
    os.makedirs(args.resultados, exist_ok=True)
    destino = f"{args.resultados}/{args.particion}-{args.nombre}.run"
    pt.io.write_results(corrida, destino)
    print(f"[INFO] {len(consultas)} consultas, corrida en {destino}")


if __name__ == "__main__":
    main()
