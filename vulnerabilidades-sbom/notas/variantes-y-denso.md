# N-gramas, denso y fusión (22/11/2026)

Todo sobre la partición de desarrollo (601 consultas). La de prueba sigue sin tocarse.
Holm ajusta sobre las 18 comparaciones de la tabla de significancia (6 sistemas x 3 métricas).

## N-gramas de caracteres (BM25)
Los nombres compuestos (fast-http, lodash.merge) se mantienen como una unidad antes de cortarlos,
con "_" en los bordes y en los separadores. Sin stopwords ni stemmer.

| n | nDCG@10 | MAP | R@100 | Índice |
|---|---|---|---|---|
| palabras (base) | 0,831 | 0,805 | 0,960 | 131 MB |
| 3 | 0,828 | 0,803 | 0,963 | 272 MB |
| 4 | 0,864 | 0,842 | 0,978 | 385 MB |
| 5 | 0,865 | 0,844 | 0,979 | 581 MB |

Se elige n=4: rinde igual que 5 con dos tercios del índice. Contra BM25 por palabras, la mejora
en MAP es significativa con Wilcoxon después de Holm (p=0,031); en nDCG@10 no llega (p=0,24).
La ganancia está en el estrato "todas" (0,860 -> 0,905). En "ninguna" empeora (0,703 -> 0,670):
sin el nombre en el texto, los n-gramas solo agregan coincidencias parciales.

## Denso
all-MiniLM-L6-v2 sin ajuste, índice exacto de FAISS (coseno). Documento = productos + descripción;
consulta = "npm package <nombre>". Codificar las 411.242 CVE en CPU llevó 1 h 48 min.

nDCG@10 0,544, MAP 0,501, R@100 0,861. Mucho peor que BM25 en todos los estratos, también en
"ninguna" (0,377), que era donde se esperaba que ayudara. Lectura: la consulta es un nombre propio,
sin semántica que el modelo pueda aprovechar, y el modelo nunca vio nombres de paquetes de npm.

## Fusión con RRF (k=60)

| Sistema | nDCG@10 | MAP | R@100 |
|---|---|---|---|
| BM25 + denso | 0,835 | 0,799 | 0,976 |
| BM25 n-gramas + denso | 0,837 | 0,802 | 0,983 |
| BM25 + BM25 n-gramas + denso | 0,861 | 0,833 | 0,986 |

Ninguna fusión supera a BM25 con n-gramas solo en nDCG@10 ni en MAP, y ninguna diferencia contra
BM25 sobrevive a Holm. Lo que sí sube es R@100 (hasta 0,986), o sea que el denso trae algunas CVE
que lo léxico no encuentra, pero las ubica lejos del principio del ranking.

## Para el informe
- El resultado negativo del denso es un hallazgo en sí, no un error a esconder: en esta tarea la
  consulta es un identificador y lo que pesa es la coincidencia exacta del nombre.
- Lo que queda por probar, si la cátedra quiere más: usar el denso solo para reordenar los primeros
  100 de BM25 (lo que sugirió Tolosa) o un modelo entrenado sobre código o seguridad. Ninguno está en
  la propuesta, así que no se agrega sin que lo pidan.
- Falta la auditoría manual de una muestra de juicios y, al final, correr la partición de prueba
  una sola vez con los sistemas elegidos.
