import argparse
import json
import os
from datetime import datetime

from lib.ClienteNVD import ClienteNVD
from lib.RegistroCVE import RegistroCVE


def main():
    parser = argparse.ArgumentParser(
        description="Baja de la NVD las CVE publicadas en un rango de fechas y las guarda en JSONL."
    )
    parser.add_argument("--desde", required=True, help="Fecha inicial, AAAA-MM-DD.")
    parser.add_argument(
        "--hasta", required=True, help="Fecha final (inclusive), AAAA-MM-DD."
    )
    parser.add_argument(
        "--salida", default="datos/nvd/cves.jsonl", help="Archivo JSONL de salida."
    )
    parser.add_argument(
        "--pausa", type=float, default=7.0, help="Segundos entre pedidos a la API."
    )
    args = parser.parse_args()

    desde = datetime.strptime(args.desde, "%Y-%m-%d")
    hasta = datetime.strptime(args.hasta, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59
    )

    os.makedirs(os.path.dirname(args.salida) or ".", exist_ok=True)
    cliente = ClienteNVD(pausa=args.pausa)

    vistas = set()
    guardadas = 0
    rechazadas = 0
    con_cpe = 0
    with open(args.salida, "w", encoding="utf-8") as f:
        for cve in cliente.cves_publicadas(desde, hasta):
            registro = RegistroCVE.desde_nvd(cve)
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

    print(f"CVE guardadas: {guardadas} (rechazadas descartadas: {rechazadas})")
    if guardadas > 0:
        print(f"Con CPE de la NVD: {con_cpe} ({con_cpe / guardadas:.1%})")
    print(f"Archivo: {args.salida}")


if __name__ == "__main__":
    main()
