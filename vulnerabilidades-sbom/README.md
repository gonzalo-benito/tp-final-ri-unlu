# TP Final - Recuperación de vulnerabilidades para componentes de un SBOM

Trabajo final de Recuperación de la Información (UNLu). La idea es tratar como un problema
de recuperación ad hoc algo que hoy se resuelve con identificadores CPE: dado un componente
de software (gestor de paquetes, nombre y versión), recuperar las CVE que lo afectan.

Desde abril de 2026 la NVD dejó de cargar CPE para buena parte de las CVE nuevas, así que el
cruce "inventario -> NVD" por CPE deja de encontrar cosas. Acá se prueba qué tan bien funciona
recuperar por texto (TF-IDF, BM25, modelos de lenguaje, denso con FAISS e híbrido).

- Documentos: registros CVE de la NVD (API 2.0).
- Juicios de relevancia: base OSV (avisos de GitHub, PyPI, Go, etc.), que vincula cada aviso
  con sus CVE y con los paquetes y versiones afectados.
- Consultas: paquetes de npm, PyPI, Maven, Go y NuGet.

La propuesta está en `propuesta/`.

## Requisitos

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Los datos descargados van a `datos/`, que no se sube al repo.

## Descarga de CVE de la NVD
```bash
# Ejecutar desde vulnerabilidades-sbom/
# Un día, para probar
python3 -m descargar_nvd --desde 2026-09-01 --hasta 2026-09-01 --salida datos/nvd/prueba.jsonl
# Todo el corpus hasta la fecha de descarga (tarda un rato por el límite de pedidos de la API)
python3 -m descargar_nvd --desde 1999-01-01 --hasta 2026-11-07 --salida datos/nvd/cves.jsonl
```
Si se define la variable `NVD_API_KEY` (la NVD da claves gratis) se puede bajar la pausa con `--pausa 1`.
