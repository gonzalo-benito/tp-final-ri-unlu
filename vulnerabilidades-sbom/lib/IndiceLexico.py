import json
import os
import re
from typing import Iterator

import pandas as pd
import pyterrier as pt


class IndiceLexico:
    """
    Índice de Terrier sobre las CVE, armado con PyTerrier.
    El texto de cada documento junta campos del registro: por defecto la
    descripción, los productos que declara quien emite la CVE y las URL de las
    referencias. Los CPE no entran.

    Esta es la versión de línea de base: tokenización por palabras, con la
    lista de stopwords y el stemmer de Porter que Terrier usa por defecto.
    """

    CAMPOS = ["descripcion", "productos", "referencias"]

    carpeta: str
    campos: list[str]

    def __init__(self, carpeta: str, campos: list[str] = None):
        self.carpeta = os.path.abspath(carpeta)
        self.campos = campos if campos else self.CAMPOS

    @staticmethod
    def limpiar(texto: str) -> str:
        # las URL y los nombres de paquetes traen / . - _ @; Terrier los corta
        # igual, pero así queda explícito y el parser de consultas no se queja
        return re.sub(r"[^0-9A-Za-z]+", " ", texto).strip()

    def texto_de(self, registro: dict) -> str:
        partes = []
        for campo in self.campos:
            valor = registro[campo]
            partes.extend(valor if isinstance(valor, list) else [valor])
        return self.limpiar(" ".join(partes))

    def documentos(self, ruta_jsonl: str) -> Iterator[dict]:
        with open(ruta_jsonl, encoding="utf-8") as f:
            for linea in f:
                registro = json.loads(linea)
                yield {"docno": registro["id"], "text": self.texto_de(registro)}

    def existe(self) -> bool:
        return os.path.exists(os.path.join(self.carpeta, "data.properties"))

    def construir(self, ruta_jsonl: str):
        indexador = pt.IterDictIndexer(
            self.carpeta, meta={"docno": 20}, text_attrs=["text"], overwrite=True
        )
        indexador.index(self.documentos(ruta_jsonl))

    def recuperador(self, modelo: str, k: int = 1000):
        """modelo: un weighting model de Terrier, por ejemplo "BM25" o "TF_IDF"."""
        return pt.terrier.Retriever(self.carpeta, wmodel=modelo, num_results=k)

    @classmethod
    def consultas_df(cls, consultas: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(
            [{"qid": c["qid"], "query": cls.limpiar(c["paquete"])} for c in consultas]
        )
