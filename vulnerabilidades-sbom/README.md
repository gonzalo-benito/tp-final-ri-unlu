# TP Final - Recuperación de vulnerabilidades para componentes de un SBOM

Trabajo final de Recuperación de la Información (UNLu). La idea es tratar como un problema
de recuperación ad hoc algo que hoy se resuelve con identificadores CPE: dado un componente
de software (gestor de paquetes y nombre), recuperar las CVE que lo afectan.

Desde abril de 2026 la NVD dejó de cargar CPE para buena parte de las CVE nuevas, así que el
cruce "inventario -> NVD" por CPE deja de encontrar cosas. Acá se prueba qué tan bien funciona
recuperar por texto (TF-IDF, BM25, modelos de lenguaje, denso con FAISS e híbrido).

- Documentos: registros CVE de la NVD (API 2.0).
- Juicios de relevancia: base OSV (avisos de GitHub, PyPI, Go, etc.), que vincula cada aviso
  con sus CVE y con los paquetes y versiones afectados.
- Consultas: paquetes de npm, sin versión (los juicios son binarios por paquete).

La propuesta está en `propuesta/`.

## Requisitos

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Los datos descargados van a `datos/`, que no se sube al repo.

## Descarga de CVE de la NVD
Lo más rápido es bajar los volcados anuales (unos minutos para todo el corpus):
```bash
# Ejecutar desde vulnerabilidades-sbom/
python3 -m descargar_nvd_anual                  # 2002 a 2026 -> datos/nvd/cves.jsonl
```
También se puede usar la API, que permite pedir un rango de fechas de publicación:
```bash
# Ejecutar desde vulnerabilidades-sbom/
# Un día, para probar
python3 -m descargar_nvd --desde 2026-09-01 --hasta 2026-09-01 --salida datos/nvd/prueba.jsonl
# Todo el corpus hasta la fecha de descarga (tarda un rato por el límite de pedidos de la API)
python3 -m descargar_nvd --desde 1999-01-01 --hasta 2026-11-07 --salida datos/nvd/cves.jsonl
```
Si se define la variable `NVD_API_KEY` (la NVD da claves gratis) se puede bajar la pausa con `--pausa 1`.

## Descarga de OSV
```bash
# Ejecutar desde vulnerabilidades-sbom/
python3 -m descargar_osv --ecosistemas npm      # el único que usa la colección
python3 -m descargar_osv                        # npm, PyPI, Maven, Go y NuGet
```
Los avisos de GitHub, PyPI y Go que vienen en OSV tienen licencia CC-BY 4.0.

## Colección de prueba
```bash
# Ejecutar desde vulnerabilidades-sbom/
python3 -m armar_coleccion
```
Deja en `datos/coleccion/`:
- `consultas.tsv`: una consulta por paquete de npm, con su partición (desarrollo o prueba,
  20/80 según un hash del nombre), cuántas CVE relevantes tiene y cuántas lo nombran en la
  descripción. Con eso se arma el estrato: `todas`, `algunas` o `ninguna`.
- `qrels.txt`: juicios de relevancia en formato TREC.
- `resumen.json`: cuántos paquetes y pares había en OSV y cuántos se descartaron porque la CVE
  no está en el corpus (rechazada o todavía no cargada en la NVD).

## Modelos léxicos (línea de base)
```bash
# Ejecutar desde vulnerabilidades-sbom/. La primera vez construye el índice (~1 minuto).
python3 -m correr_lexicos                                  # BM25 y TF-IDF, partición de desarrollo
# Variante con n-gramas de caracteres (n=4 fue el mejor en desarrollo)
python3 -m correr_lexicos --tokenizacion ngramas --n 4 --indice datos/indices/ngramas4 --nombre=_ngramas4 --modelos BM25
# Para ver qué aporta cada campo, otro índice con menos campos
python3 -m correr_lexicos --campos descripcion --indice datos/indices/palabras_descripcion --nombre=_descripcion
```
Las corridas (formato TREC) y la tabla de métricas quedan en `resultados/`. La partición de
prueba no se toca hasta tener los sistemas ajustados sobre desarrollo.

## Recuperador denso (Sentence-BERT + FAISS)
```bash
# Ejecutar desde vulnerabilidades-sbom/. La primera vez codifica todo el corpus:
# en una CPU de 4 núcleos tardó 1 h 48 min. Después cada corrida tarda segundos.
python3 -m correr_denso
```

## Fusión y comparación
```bash
# Ejecutar desde vulnerabilidades-sbom/
python3 -m fusionar --corridas resultados/desarrollo-BM25.run resultados/desarrollo-denso.run \
    --salida resultados/desarrollo-RRF_BM25_denso.run
python3 -m evaluar --corridas BM25=resultados/desarrollo-BM25.run \
    BM25_ng4=resultados/desarrollo-BM25_ngramas4.run \
    RRF_BM25_denso=resultados/desarrollo-RRF_BM25_denso.run \
    --salida resultados/desarrollo-comparacion
```
`evaluar` compara cada corrida contra la de base (BM25 por defecto) con t pareada y Wilcoxon,
y ajusta los p-valores con Holm por la cantidad total de comparaciones.
