import os
import time
from datetime import datetime, timedelta
from typing import Iterator, Optional

import requests


class ClienteNVD:
    """
    Cliente simple para la API 2.0 de la NVD.
    - Pide las CVE publicadas en un rango de fechas, de a páginas de 2000.
    - La API no acepta rangos de más de 120 días, así que el rango se parte.
    - Sin clave hay un límite de pedidos, por eso se espera entre pedido y pedido.
      Si existe la variable de entorno NVD_API_KEY se manda como clave.
    """

    URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    FORMATO_FECHA = "%Y-%m-%dT%H:%M:%S.000"
    MAX_DIAS_POR_RANGO = 120
    RESULTADOS_POR_PAGINA = 2000

    pausa: float
    api_key: Optional[str]

    def __init__(self, pausa: float = 7.0, api_key: Optional[str] = None):
        self.pausa = pausa
        self.api_key = api_key if api_key else os.environ.get("NVD_API_KEY")

    def pedir(self, parametros: dict) -> dict:
        """
        Hace un pedido a la API y devuelve el JSON. Reintenta si la API
        responde con error (suele pasar por el límite de pedidos).
        """
        headers = {"User-Agent": "tp-final-ri-unlu"}
        if self.api_key:
            headers["apiKey"] = self.api_key

        for intento in range(5):
            respuesta = requests.get(
                self.URL, params=parametros, headers=headers, timeout=120
            )
            if respuesta.status_code == 200:
                return respuesta.json()
            espera = self.pausa * (intento + 2)
            print(f"  la NVD respondió {respuesta.status_code}, reintento en {espera:.0f} s")
            time.sleep(espera)

        raise RuntimeError(f"La NVD no respondió bien después de 5 intentos: {parametros}")

    def partir_rango(
        self, desde: datetime, hasta: datetime
    ) -> list[tuple[datetime, datetime]]:
        """
        Parte [desde, hasta] en tramos de 120 días como máximo.
        """
        tramos = []
        inicio = desde
        while inicio <= hasta:
            fin = min(inicio + timedelta(days=self.MAX_DIAS_POR_RANGO), hasta)
            tramos.append((inicio, fin))
            # el siguiente tramo arranca un segundo después para no repetir CVEs
            inicio = fin + timedelta(seconds=1)
        return tramos

    def cves_publicadas(self, desde: datetime, hasta: datetime) -> Iterator[dict]:
        """
        Devuelve (de a una) las CVE publicadas entre desde y hasta, tal cual las da la API.
        """
        for inicio, fin in self.partir_rango(desde, hasta):
            indice = 0
            total = 1
            while indice < total:
                parametros = {
                    "pubStartDate": inicio.strftime(self.FORMATO_FECHA),
                    "pubEndDate": fin.strftime(self.FORMATO_FECHA),
                    "resultsPerPage": self.RESULTADOS_POR_PAGINA,
                    "startIndex": indice,
                }
                datos = self.pedir(parametros)
                total = datos["totalResults"]
                vulnerabilidades = datos["vulnerabilities"]
                print(
                    f"  {inicio:%Y-%m-%d} a {fin:%Y-%m-%d}: "
                    f"{indice + len(vulnerabilidades)} de {total}"
                )
                for item in vulnerabilidades:
                    yield item["cve"]
                if len(vulnerabilidades) == 0:
                    break
                indice += len(vulnerabilidades)
                time.sleep(self.pausa)
