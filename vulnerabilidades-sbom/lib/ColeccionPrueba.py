import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field

from lib.LectorOSV import LectorOSV


@dataclass
class Consulta:
    """
    Una consulta de la colección: un paquete de npm, sin versión.
    - particion: "desarrollo" o "prueba".
    - relevantes: las CVE que OSV asocia al paquete y que están en el corpus.
    - mencionan: cuántas de esas CVE nombran al paquete en su descripción.
    """

    id: str
    paquete: str
    particion: str
    relevantes: list[str] = field(default_factory=list)
    mencionan: int = 0

    def estrato(self) -> str:
        """
        "todas" si todas las CVE relevantes nombran al paquete en la descripción,
        "ninguna" si ninguna lo nombra y "algunas" en el resto de los casos.
        """
        if self.mencionan == len(self.relevantes):
            return "todas"
        if self.mencionan == 0:
            return "ninguna"
        return "algunas"


class ColeccionPrueba:
    """
    Arma las consultas y los juicios de relevancia a partir de OSV.
    Un juicio es binario: la CVE afecta (1) o no al paquete. Lo que no está en
    los juicios se toma como no relevante, como en las colecciones de TREC.

    La partición se decide con un hash del nombre del paquete, así sale siempre
    igual sin guardar una semilla y un paquete nunca cae en las dos.
    """

    ECOSISTEMA = "npm"

    consultas: list[Consulta]
    porcentaje_desarrollo: int

    def __init__(self, porcentaje_desarrollo: int = 20):
        self.consultas = []
        self.porcentaje_desarrollo = porcentaje_desarrollo

    def particion_de(self, paquete: str) -> str:
        valor = int(hashlib.md5(paquete.encode("utf-8")).hexdigest(), 16) % 100
        return "desarrollo" if valor < self.porcentaje_desarrollo else "prueba"

    @staticmethod
    def menciona(descripcion: str, paquete: str) -> bool:
        """
        True si la descripción nombra al paquete: el nombre completo o, en los
        paquetes con scope (@scope/nombre), la parte final. Se pide que no esté
        pegado a otra letra o número, para que "ws" no aparezca dentro de "always".
        """
        texto = descripcion.lower()
        nombres = {paquete.lower(), paquete.lower().split("/")[-1]}
        for nombre in nombres:
            patron = r"(?<![a-z0-9])" + re.escape(nombre) + r"(?![a-z0-9])"
            if re.search(patron, texto):
                return True
        return False

    def armar(self, ruta_osv: str, descripciones: dict[str, str]) -> dict:
        """
        descripciones: id de CVE -> descripción, para las CVE del corpus.
        Devuelve un resumen con lo que se descartó en el camino.
        """
        cves_por_paquete = defaultdict(set)
        for aviso in LectorOSV(ruta_osv).avisos_con_cve():
            for paquete in aviso.paquetes:
                if paquete.ecosistema != self.ECOSISTEMA:
                    continue
                for cve in aviso.cves:
                    cves_por_paquete[paquete.nombre].add(cve)

        pares_osv = sum(len(c) for c in cves_por_paquete.values())
        fuera_del_corpus = set()
        sin_relevantes = 0
        for numero, paquete in enumerate(sorted(cves_por_paquete), start=1):
            relevantes = []
            for cve in sorted(cves_por_paquete[paquete]):
                if cve in descripciones:
                    relevantes.append(cve)
                else:
                    fuera_del_corpus.add(cve)
            if len(relevantes) == 0:
                sin_relevantes += 1
                continue
            mencionan = sum(
                1 for cve in relevantes if self.menciona(descripciones[cve], paquete)
            )
            self.consultas.append(
                Consulta(
                    id=f"q{numero}",
                    paquete=paquete,
                    particion=self.particion_de(paquete),
                    relevantes=relevantes,
                    mencionan=mencionan,
                )
            )

        return {
            "paquetes_en_osv": len(cves_por_paquete),
            "pares_en_osv": pares_osv,
            "cve_fuera_del_corpus": len(fuera_del_corpus),
            "paquetes_sin_relevantes": sin_relevantes,
            "consultas": len(self.consultas),
            "juicios": sum(len(c.relevantes) for c in self.consultas),
        }

    def guardar(self, carpeta: str):
        """
        consultas.tsv: id, paquete, partición, cantidad de relevantes, cuántas lo mencionan, estrato.
        qrels.txt: formato de TREC (consulta 0 documento relevancia).
        """
        with open(f"{carpeta}/consultas.tsv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["qid", "paquete", "particion", "relevantes", "mencionan", "estrato"])
            for c in self.consultas:
                w.writerow(
                    [c.id, c.paquete, c.particion, len(c.relevantes), c.mencionan, c.estrato()]
                )
        with open(f"{carpeta}/qrels.txt", "w", encoding="utf-8") as f:
            for c in self.consultas:
                for cve in c.relevantes:
                    f.write(f"{c.id} 0 {cve} 1\n")

    @staticmethod
    def cargar_consultas(carpeta: str) -> list[dict]:
        with open(f"{carpeta}/consultas.tsv", encoding="utf-8") as f:
            return list(csv.DictReader(f, delimiter="\t"))


def leer_descripciones(ruta_jsonl: str) -> dict[str, str]:
    descripciones = {}
    with open(ruta_jsonl, encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            descripciones[registro["id"]] = registro["descripcion"]
    return descripciones
