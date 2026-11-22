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

    Hay dos tokenizaciones:
    - "palabras": la línea de base, con el tokenizador, las stopwords y el
      stemmer de Porter que Terrier usa por defecto.
    - "ngramas": n-gramas de caracteres armados acá, sin stopwords ni stemmer.
      Los nombres compuestos (fast-http, lodash.merge) se mantienen como una
      unidad antes de cortarlos, así sobreviven los n-gramas que cruzan el
      guion o el punto y que son los que distinguen "fast-http" de un texto que
      dice "fast" en un lado y "http" en otro.
    """

    CAMPOS = ["descripcion", "productos", "referencias"]

    carpeta: str
    campos: list[str]
    tokenizacion: str
    n: int

    def __init__(
        self,
        carpeta: str,
        campos: list[str] = None,
        tokenizacion: str = "palabras",
        n: int = 4,
    ):
        self.carpeta = os.path.abspath(carpeta)
        self.campos = campos if campos else self.CAMPOS
        self.tokenizacion = tokenizacion
        self.n = n

    @staticmethod
    def limpiar(texto: str) -> str:
        # las URL y los nombres de paquetes traen / . - _ @; Terrier los corta
        # igual, pero así queda explícito y el parser de consultas no se queja
        return re.sub(r"[^0-9A-Za-z]+", " ", texto).strip()

    def ngramas(self, texto: str) -> str:
        """
        Pasa el texto a n-gramas de caracteres separados por espacios.
        Una unidad es una secuencia de letras y números que puede tener - . _ en
        el medio; los separadores y los bordes se marcan con "_".
        Ejemplo con n=4: "fast-http" -> _fas fast ast_ st_h t_ht _htt http ttp_
        """
        gramas = []
        for unidad in re.findall(r"[a-z0-9]+(?:[-._][a-z0-9]+)*", texto.lower()):
            marcada = "_" + re.sub(r"[-._]", "_", unidad) + "_"
            if len(marcada) <= self.n:
                gramas.append(marcada)
                continue
            for i in range(len(marcada) - self.n + 1):
                gramas.append(marcada[i : i + self.n])
        return " ".join(gramas)

    def preparar(self, texto: str) -> str:
        """Lo que se le hace a un texto antes de indexarlo o de usarlo como consulta."""
        if self.tokenizacion == "ngramas":
            return self.ngramas(texto)
        return self.limpiar(texto)

    def texto_de(self, registro: dict) -> str:
        partes = []
        for campo in self.campos:
            valor = registro[campo]
            partes.extend(valor if isinstance(valor, list) else [valor])
        return self.preparar(" ".join(partes))

    def documentos(self, ruta_jsonl: str) -> Iterator[dict]:
        with open(ruta_jsonl, encoding="utf-8") as f:
            for linea in f:
                registro = json.loads(linea)
                yield {"docno": registro["id"], "text": self.texto_de(registro)}

    def existe(self) -> bool:
        return os.path.exists(os.path.join(self.carpeta, "data.properties"))

    def construir(self, ruta_jsonl: str):
        opciones = {}
        if self.tokenizacion == "ngramas":
            opciones = {"tokeniser": "whitespace", "stemmer": None, "stopwords": None}
        indexador = pt.IterDictIndexer(
            self.carpeta,
            meta={"docno": 20},
            text_attrs=["text"],
            overwrite=True,
            **opciones
        )
        indexador.index(self.documentos(ruta_jsonl))

    def recuperador(self, modelo: str, k: int = 1000):
        """modelo: un weighting model de Terrier, por ejemplo "BM25" o "TF_IDF"."""
        propiedades = {}
        if self.tokenizacion == "ngramas":
            propiedades = {"tokeniser": "WhitespaceTokeniser", "termpipelines": ""}
        return pt.terrier.Retriever(
            self.carpeta, wmodel=modelo, num_results=k, properties=propiedades
        )

    def consultas_df(self, consultas: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(
            [{"qid": c["qid"], "query": self.preparar(c["paquete"])} for c in consultas]
        )
