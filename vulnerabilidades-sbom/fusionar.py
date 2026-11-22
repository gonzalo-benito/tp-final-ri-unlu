import argparse
from collections import defaultdict

import pandas as pd
import pyterrier as pt


def rrf(corridas: list[pd.DataFrame], k: int = 60, profundidad: int = 1000) -> pd.DataFrame:
    """
    Reciprocal Rank Fusion: puntaje(d) = suma sobre las corridas de 1 / (k + posición de d),
    con la posición contada desde 1. No mira los puntajes originales, solo las posiciones.
    """
    puntajes = defaultdict(float)
    for corrida in corridas:
        corrida = corrida.sort_values(["qid", "score"], ascending=[True, False])
        corrida["posicion"] = corrida.groupby("qid").cumcount() + 1
        for qid, docno, posicion in corrida[["qid", "docno", "posicion"]].itertuples(index=False):
            if posicion <= profundidad:
                puntajes[(qid, docno)] += 1.0 / (k + posicion)

    filas = pd.DataFrame(
        [(qid, docno, puntaje) for (qid, docno), puntaje in puntajes.items()],
        columns=["qid", "docno", "score"],
    ).sort_values(["qid", "score"], ascending=[True, False])
    filas["rank"] = filas.groupby("qid").cumcount()
    return filas[filas["rank"] < profundidad]


def main():
    parser = argparse.ArgumentParser(description="Fusiona corridas TREC con RRF.")
    parser.add_argument("--corridas", nargs="+", required=True)
    parser.add_argument("--k", type=int, default=60)
    parser.add_argument("--salida", required=True)
    args = parser.parse_args()

    corridas = [pt.io.read_results(r) for r in args.corridas]
    pt.io.write_results(rrf(corridas, args.k), args.salida)
    print(f"Fusión de {len(corridas)} corridas con k={args.k} en {args.salida}")


if __name__ == "__main__":
    main()
