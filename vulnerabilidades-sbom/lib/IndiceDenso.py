import json
import os

import faiss
import numpy as np
import pandas as pd


class IndiceDenso:
    """
    Recuperador denso: cada CVE se codifica con un modelo de Sentence-BERT y
    los vectores se guardan en un índice exacto de FAISS (producto interno
    sobre vectores normalizados, o sea similitud coseno).

    El texto del documento es "productos. descripción": las URL de las
    referencias no se usan acá porque no son lenguaje natural.
    La consulta es "npm package <nombre>", para que el modelo tenga algo de
    contexto además del nombre suelto.
    """

    MODELO = "sentence-transformers/all-MiniLM-L6-v2"

    carpeta: str
    nombre_modelo: str

    def __init__(self, carpeta: str, nombre_modelo: str = MODELO):
        self.carpeta = carpeta
        self.nombre_modelo = nombre_modelo
        self._modelo = None

    def modelo(self):
        if self._modelo is None:
            from sentence_transformers import SentenceTransformer

            self._modelo = SentenceTransformer(self.nombre_modelo, device="cpu")
        return self._modelo

    @staticmethod
    def texto_de(registro: dict) -> str:
        productos = ", ".join(registro["productos"])
        return (
            f"{productos}. {registro['descripcion']}"
            if productos
            else registro["descripcion"]
        )

    @staticmethod
    def texto_consulta(paquete: str) -> str:
        return f"npm package {paquete}"

    def existe(self) -> bool:
        return os.path.exists(os.path.join(self.carpeta, "faiss.index"))

    def construir(self, ruta_jsonl: str, lote: int = 256):
        os.makedirs(self.carpeta, exist_ok=True)
        ids, textos = [], []
        with open(ruta_jsonl, encoding="utf-8") as f:
            for linea in f:
                registro = json.loads(linea)
                ids.append(registro["id"])
                textos.append(self.texto_de(registro))

        vectores = (
            self.modelo()
            .encode(
                textos,
                batch_size=lote,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            .astype("float32")
        )

        indice = faiss.IndexFlatIP(vectores.shape[1])
        indice.add(vectores)
        faiss.write_index(indice, os.path.join(self.carpeta, "faiss.index"))
        with open(os.path.join(self.carpeta, "ids.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(ids) + "\n")

    def buscar(self, consultas: list[dict], k: int = 1000) -> pd.DataFrame:
        indice = faiss.read_index(os.path.join(self.carpeta, "faiss.index"))
        with open(os.path.join(self.carpeta, "ids.txt"), encoding="utf-8") as f:
            ids = [linea.strip() for linea in f]

        textos = [self.texto_consulta(c["paquete"]) for c in consultas]
        vectores = (
            self.modelo()
            .encode(textos, convert_to_numpy=True, normalize_embeddings=True)
            .astype("float32")
        )
        puntajes, posiciones = indice.search(vectores, k)

        filas = []
        for c, fila_puntajes, fila_posiciones in zip(consultas, puntajes, posiciones):
            for rank, (puntaje, posicion) in enumerate(
                zip(fila_puntajes, fila_posiciones)
            ):
                filas.append(
                    {
                        "qid": c["qid"],
                        "docno": ids[posicion],
                        "rank": rank,
                        "score": float(puntaje),
                    }
                )
        return pd.DataFrame(filas)
