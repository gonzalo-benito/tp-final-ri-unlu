# Línea de base léxica (22/11/2026)

## Datos
- Corpus: volcados anuales de la NVD generados el 22/11/2026. 411.242 CVE sin contar las
  rechazadas (19.197). El 79,5 % tiene CPE de la NVD, pero eso es el histórico: las nuevas casi no.
- OSV npm bajado el 22/11/2026: 3.030 paquetes con al menos una CVE, 7.403 pares paquete-CVE.
  45 CVE no están en el corpus y 23 paquetes quedan sin ninguna relevante.
- Colección: 3.007 consultas y 7.358 juicios. Desarrollo 601 consultas, prueba 2.406.
  La mediana es 1 CVE relevante por paquete; el máximo, 533 (openclaw).
- Estratos en desarrollo: 483 consultas donde todas las CVE nombran al paquete en la descripción,
  40 donde lo nombran algunas y 78 donde no lo nombra ninguna.

## Resultados en desarrollo (601 consultas)
Terrier con la configuración por defecto (stopwords y stemmer de Porter), top 1000.
Documento = descripción + productos declarados por la CNA + URL de las referencias.

| Modelo | nDCG@10 | MAP | MRR | R@10 | R@100 | P@10 |
|---|---|---|---|---|---|---|
| BM25 | 0,831 | 0,805 | 0,831 | 0,883 | 0,960 | 0,161 |
| TF-IDF | 0,836 | 0,811 | 0,837 | 0,885 | 0,967 | 0,161 |

BM25 contra TF-IDF: la t pareada da p < 0,05 en nDCG@10, MAP y R@100, pero Wilcoxon no
(p entre 0,31 y 0,75). La diferencia es chica y se concentra en pocas consultas; no alcanza para
decir que uno sea mejor.

Qué aporta cada campo (BM25):

| Campos | nDCG@10 | MRR | R@100 | nDCG@10 en "ninguna" |
|---|---|---|---|---|
| descripción | 0,737 | 0,731 | 0,922 | 0,454 |
| descripción + productos | 0,809 | 0,805 | 0,954 | 0,626 |
| descripción + referencias | 0,799 | 0,796 | 0,957 | 0,602 |
| los tres | 0,831 | 0,831 | 0,960 | 0,703 |

## Lectura
- La tarea es más fácil de lo esperado cuando la descripción nombra al paquete. Lo difícil está en
  el estrato "ninguna" (13 % de las consultas), donde con la descripción sola el MRR cae a 0,43.
- Los productos de la CNA y las referencias recuperan buena parte de esos casos: en GitHub el
  producto suele ser el nombre del repositorio y las URL traen el nombre del proyecto. Son datos
  que están en el registro desde la publicación, así que valen como entrada. Hay que decirlo en el
  informe, porque explica por qué la línea de base ya es alta.
- 44 consultas de desarrollo tienen MRR < 0,1. Casi todas son nombres que también son palabras
  comunes (color, diff, forms, angular, aws-sdk) o nombres compuestos que el tokenizador parte
  (fast-http, base-x, error-ex). Es lo que tendría que mejorar la variante con n-gramas de
  caracteres y, quizás, el denso.
- OSV trae algún paquete repetido con otra capitalización (Openclaw y openclaw). Revisar si conviene
  normalizar a minúsculas al armar las consultas.

## Próximos pasos
1. Variante con n-gramas de caracteres sobre los nombres (semana 3 del cronograma).
2. Recuperador denso con Sentence-BERT y FAISS, y fusión con RRF (semana 4).
3. Auditoría manual de una muestra de juicios.
