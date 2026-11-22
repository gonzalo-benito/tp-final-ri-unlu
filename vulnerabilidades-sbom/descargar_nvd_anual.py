import argparse
import gzip
import json
import os

import requests

from lib.RegistroCVE import RegistroCVE

# La NVD publica un volcado por año (el año es el del identificador CVE, no el de publicación).
# Bajar esto es mucho más rápido que recorrer toda la API con pausas de 7 segundos.
URL_ANUAL = "https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{anio}.json.gz"


def bajar_anio(anio: int, carpeta: str) -> str:
    destino = os.path.join(carpeta, f"nvdcve-2.0-{anio}.json.gz")
    if os.path.exists(destino):
        print(f"  {destino} ya existe, no se baja de nuevo")
        return destino
    url = URL_ANUAL.format(anio=anio)
    print(f"Bajando {url}")
    with requests.get(url, stream=True, timeout=300) as respuesta:
        respuesta.raise_for_status()
        with open(destino, "wb") as f:
            for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                f.write(bloque)
    return destino


def main():
    parser = argparse.ArgumentParser(
        description="Baja los volcados anuales de la NVD y los junta en un JSONL con los campos a indexar."
    )
    parser.add_argument("--desde", type=int, default=2002, help="Primer año (la NVD arranca en 2002).")
    parser.add_argument("--hasta", type=int, default=2026, help="Último año.")
    parser.add_argument("--carpeta", default="datos/nvd/anual", help="Dónde guardar los .json.gz.")
    parser.add_argument("--salida", default="datos/nvd/cves.jsonl", help="Archivo JSONL de salida.")
    args = parser.parse_args()

    os.makedirs(args.carpeta, exist_ok=True)
    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)

    vistas = set()
    guardadas = 0
    rechazadas = 0
    con_cpe = 0
    marca_tiempo = ""
    with open(args.salida, "w", encoding="utf-8") as f:
        for anio in range(args.desde, args.hasta + 1):
            ruta = bajar_anio(anio, args.carpeta)
            with gzip.open(ruta, "rt", encoding="utf-8") as g:
                volcado = json.load(g)
            marca_tiempo = max(marca_tiempo, volcado.get("timestamp", ""))
            for item in volcado["vulnerabilities"]:
                registro = RegistroCVE.desde_nvd(item["cve"])
                if registro.id in vistas:
                    continue
                vistas.add(registro.id)
                if registro.esta_rechazada():
                    rechazadas += 1
                    continue
                if registro.tiene_cpe_nvd:
                    con_cpe += 1
                f.write(json.dumps(registro.a_dict(), ensure_ascii=False) + "\n")
                guardadas += 1
            print(f"  {anio}: {guardadas} CVE acumuladas")

    print(f"CVE guardadas: {guardadas} (rechazadas descartadas: {rechazadas})")
    if guardadas > 0:
        print(f"Con CPE de la NVD: {con_cpe} ({con_cpe / guardadas:.1%})")
    print(f"Volcado más nuevo generado el {marca_tiempo}")
    print(f"Archivo: {args.salida}")


if __name__ == "__main__":
    main()
