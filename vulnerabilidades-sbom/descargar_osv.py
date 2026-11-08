import argparse
import os

import requests

URL_OSV = "https://osv-vulnerabilities.storage.googleapis.com/{ecosistema}/all.zip"

# Los gestores de paquetes de los lenguajes de Online Boutique (Go, C#, Node.js, Python, Java)
ECOSISTEMAS = ["npm", "PyPI", "Maven", "Go", "NuGet"]


def descargar(ecosistema: str, carpeta: str) -> str:
    destino_dir = os.path.join(carpeta, ecosistema)
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, "all.zip")

    url = URL_OSV.format(ecosistema=ecosistema)
    print(f"Bajando {url}")
    with requests.get(url, stream=True, timeout=300) as respuesta:
        respuesta.raise_for_status()
        with open(destino, "wb") as f:
            for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                f.write(bloque)

    tamanio_mb = os.path.getsize(destino) / (1024 * 1024)
    print(f"  {destino} ({tamanio_mb:.1f} MB)")
    return destino


def main():
    parser = argparse.ArgumentParser(
        description="Baja los volcados de OSV (all.zip) de cada gestor de paquetes."
    )
    parser.add_argument(
        "--ecosistemas",
        nargs="+",
        default=ECOSISTEMAS,
        help=f"Gestores a bajar (por defecto: {' '.join(ECOSISTEMAS)}).",
    )
    parser.add_argument("--carpeta", default="datos/osv", help="Carpeta de salida.")
    args = parser.parse_args()

    for ecosistema in args.ecosistemas:
        descargar(ecosistema, args.carpeta)


if __name__ == "__main__":
    main()
