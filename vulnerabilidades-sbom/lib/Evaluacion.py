import ir_measures
import pandas as pd
from ir_measures import AP, P, R, RR, nDCG
from scipy import stats

METRICAS = [R @ 10, R @ 100, nDCG @ 10, AP, RR, P @ 10]


class Evaluacion:
    """
    Evalúa corridas en formato TREC contra los qrels de una partición.
    - Las consultas sin ningún resultado cuentan con 0 en todas las métricas.
    - Los promedios se reportan en total y por estrato.
    - Las comparaciones contra la línea de base son pareadas (t de Student y
      Wilcoxon) con corrección de Holm por la cantidad de comparaciones.
    """

    qrels: list
    estrato: dict[str, str]

    def __init__(self, ruta_qrels: str, consultas: list[dict]):
        self.estrato = {c["qid"]: c["estrato"] for c in consultas}
        self.qrels = [
            q
            for q in ir_measures.read_trec_qrels(ruta_qrels)
            if q.query_id in self.estrato
        ]

    def por_consulta(self, corrida: pd.DataFrame) -> pd.DataFrame:
        """Tabla consulta x métrica, con 0 para las consultas que no devolvieron nada."""
        corrida = corrida.rename(columns={"qid": "query_id", "docno": "doc_id"})
        corrida = corrida[["query_id", "doc_id", "score"]].astype(
            {"query_id": str, "doc_id": str}
        )
        filas = [
            (m.query_id, str(m.measure), m.value)
            for m in ir_measures.iter_calc(METRICAS, self.qrels, corrida)
        ]
        tabla = pd.DataFrame(filas, columns=["qid", "metrica", "valor"]).pivot(
            index="qid", columns="metrica", values="valor"
        )
        return tabla.reindex(sorted(self.estrato), fill_value=0.0).fillna(0.0)

    def resumen(self, nombre: str, detalle: pd.DataFrame) -> list[dict]:
        filas = [{"sistema": nombre, "estrato": "todos", **detalle.mean().to_dict()}]
        estratos = pd.Series(self.estrato)
        for nombre_estrato, grupo in detalle.groupby(estratos.reindex(detalle.index)):
            filas.append(
                {
                    "sistema": nombre,
                    "estrato": f"{nombre_estrato} (n={len(grupo)})",
                    **grupo.mean().to_dict(),
                }
            )
        return filas

    @staticmethod
    def comparar(
        base: pd.DataFrame, otros: dict[str, pd.DataFrame], metricas: list[str]
    ) -> pd.DataFrame:
        filas = []
        for nombre, detalle in otros.items():
            for metrica in metricas:
                a, b = base[metrica], detalle[metrica]
                filas.append(
                    {
                        "sistema": nombre,
                        "metrica": metrica,
                        "base": a.mean(),
                        "sistema_media": b.mean(),
                        "diferencia": b.mean() - a.mean(),
                        "p_t": stats.ttest_rel(a, b).pvalue,
                        "p_wilcoxon": stats.wilcoxon(a, b, zero_method="zsplit").pvalue,
                    }
                )
        tabla = pd.DataFrame(filas)
        # Holm sobre todas las comparaciones hechas, para cada prueba por separado
        for columna in ["p_t", "p_wilcoxon"]:
            orden = tabla[columna].sort_values().index
            m = len(orden)
            ajustado, maximo = {}, 0.0
            for i, indice in enumerate(orden):
                maximo = max(maximo, min(1.0, (m - i) * tabla.loc[indice, columna]))
                ajustado[indice] = maximo
            tabla[columna + "_holm"] = pd.Series(ajustado)
        return tabla
