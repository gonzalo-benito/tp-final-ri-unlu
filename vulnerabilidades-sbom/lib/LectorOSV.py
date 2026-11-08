import json
import zipfile
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class PaqueteAfectado:
    """
    Un paquete afectado por un aviso: gestor (ecosystem), nombre y versiones.
    OSV casi siempre trae la lista explícita de versiones afectadas; cuando no,
    quedan solo los rangos (introduced / fixed / last_affected).
    """

    ecosistema: str
    nombre: str
    versiones: list[str] = field(default_factory=list)
    rangos: list[dict] = field(default_factory=list)


@dataclass
class AvisoOSV:
    id: str
    publicado: str
    cves: list[str]
    paquetes: list[PaqueteAfectado]


class LectorOSV:
    """
    Lee el all.zip de OSV de un gestor de paquetes y devuelve los avisos que
    tienen al menos una CVE asociada (en el id o en los aliases).
    - Saltea los avisos retirados (withdrawn).
    - Saltea los MAL-* (paquetes maliciosos), que no tienen CVE.
    """

    ruta_zip: str

    def __init__(self, ruta_zip: str):
        self.ruta_zip = ruta_zip

    def registros(self) -> Iterator[dict]:
        with zipfile.ZipFile(self.ruta_zip) as z:
            for nombre in z.namelist():
                if not nombre.endswith(".json") or nombre.startswith("MAL-"):
                    continue
                yield json.loads(z.read(nombre))

    def avisos_con_cve(self) -> Iterator[AvisoOSV]:
        for registro in self.registros():
            if registro.get("withdrawn"):
                continue

            ids = [registro["id"]] + registro.get("aliases", [])
            cves = sorted({i for i in ids if i.startswith("CVE-")})
            if len(cves) == 0:
                continue

            paquetes = []
            for afectado in registro.get("affected", []):
                paquete = afectado.get("package", {})
                if "name" not in paquete:
                    continue
                paquetes.append(
                    PaqueteAfectado(
                        ecosistema=paquete.get("ecosystem", ""),
                        nombre=paquete["name"],
                        versiones=afectado.get("versions", []),
                        rangos=afectado.get("ranges", []),
                    )
                )
            if len(paquetes) == 0:
                continue

            yield AvisoOSV(
                id=registro["id"],
                publicado=registro.get("published", ""),
                cves=cves,
                paquetes=paquetes,
            )
