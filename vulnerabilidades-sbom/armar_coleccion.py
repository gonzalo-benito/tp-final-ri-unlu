import argparse
import json
import os
from collections import Counter

from lib.ColeccionPrueba import ColeccionPrueba, leer_descripciones


def main():
    parser = argparse.ArgumentParser(
        description="Arma consultas (paquetes de npm) y juicios de relevancia desde OSV."
    )
    parser.add_argument(
        "--osv", default="datos/osv/npm/all.zip", help="Volcado de OSV de npm."
    )
    parser.add_argument(
        "--corpus", default="datos/nvd/cves.jsonl", help="CVE de la NVD (JSONL)."
    )
    parser.add_argument(
        "--carpeta", default="datos/coleccion", help="Carpeta de salida."
    )
    parser.add_argument(
        "--desarrollo",
        type=int,
        default=20,
        help="Porcentaje de consultas para desarrollo.",
    )
    args = parser.parse_args()

    os.makedirs(args.carpeta, exist_ok=True)
    print("[INFO] Leyendo el corpus...")
    descripciones = leer_descripciones(args.corpus)
    print(f"  {len(descripciones)} CVE")

    coleccion = ColeccionPrueba(porcentaje_desarrollo=args.desarrollo)
    resumen = coleccion.armar(args.osv, descripciones)
    coleccion.guardar(args.carpeta)

    particiones = Counter(c.particion for c in coleccion.consultas)
    estratos = Counter((c.particion, c.estrato()) for c in coleccion.consultas)
    resumen["por_particion"] = dict(particiones)
    resumen["por_estrato"] = {f"{p}/{e}": n for (p, e), n in sorted(estratos.items())}
    with open(f"{args.carpeta}/resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=1, ensure_ascii=False)
    print(json.dumps(resumen, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
