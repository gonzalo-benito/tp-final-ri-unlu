# Recuperación de vulnerabilidades para componentes de software sin identificadores CPE: colección de prueba y evaluación comparativa de modelos léxicos, densos e híbridos

## 1. Idea general y motivación

La gestión de vulnerabilidades en una organización parte de cruzar su inventario de componentes de software (*Software Bill of Materials*, SBOM) con las vulnerabilidades publicadas. Ese cruce se apoya en la National Vulnerability Database (NVD) del NIST, que agrega a cada registro CVE la lista normalizada de productos afectados mediante identificadores CPE (*Common Platform Enumeration*). En abril de 2026 el NIST anunció que, ante un crecimiento del 263 % en los envíos de CVE entre 2020 y 2025, solo enriquecerá de manera prioritaria las vulnerabilidades del catálogo KEV, las del software usado por el gobierno federal estadounidense y las del software considerado crítico, mientras que el resto quedará sin análisis programado [1]. Una medición propia sobre la API de la NVD muestra el efecto: de las 14.933 CVE válidas publicadas en septiembre de 2026, al 1 de noviembre solo el 32 % tenía CPE, proporción que baja al 19 % entre las emitidas por GitHub para paquetes de código abierto.

Sin CPE, el cruce automático entre inventario y NVD no devuelve resultados, aunque el texto de cada CVE y los datos de producto declarados por quien la emite están disponibles desde su publicación. El problema puede plantearse, entonces, como una tarea de recuperación *ad hoc*: dado un componente, identificado por su gestor de paquetes, nombre y versión, recuperar las CVE que lo afectan. No se encontró una colección de prueba pública para esta tarea.

## 2. Objetivos

Objetivo general: evaluar empíricamente modelos de recuperación léxicos, densos e híbridos para recuperar las CVE que afectan a un componente de software sin recurrir a identificadores CPE.

Objetivos específicos:

1. Construir una colección de prueba reutilizable, con consultas derivadas de paquetes y juicios de relevancia graduados obtenidos de la base OSV.
2. Comparar TF-IDF, BM25, BM25F, modelos de lenguaje con suavizado de Dirichlet, un recuperador denso y la fusión de rankings.
3. Analizar el efecto de la tokenización, de los campos indexados y de la expansión de consultas.
4. Medir el costo computacional de cada enfoque, incluida la búsqueda aproximada de vecinos.
5. Aplicar el mejor sistema al inventario de un clúster Kubernetes con una aplicación de microservicios y contrastarlo con un escáner de vulnerabilidades.

## 3. Trabajos similares

La identificación automática de las bibliotecas afectadas por una vulnerabilidad se abordó como clasificación multietiqueta extrema [2, 3] y como generación con modelos de lenguaje [4], siempre en la dirección reporte → biblioteca. Otros trabajos asignan identificadores CPE a los resúmenes de CVE [5]. En un proyecto reciente de modelado de amenazas, el paso de componentes a CVE se resuelve de forma determinística mediante CPE y la evaluación de recuperación se limita a 45 consultas, sin pruebas de significancia [6]. Distintos estudios documentan, además, problemas de calidad en la NVD [7] e inconsistencias entre escáneres de vulnerabilidades basados en SBOM [8]. El presente trabajo invierte la dirección del problema (componente → ranking de CVE), lo evalúa con la metodología de colecciones de prueba, con juicios graduados y pruebas de significancia, sobre cinco gestores de paquetes y datos de 2026, y publica la colección resultante.

## 4. Metodología

*Datos.* Los documentos serán los registros CVE de la NVD (unos 400.000), con la descripción, los productos declarados por la autoridad emisora y las referencias como campos; los CPE no se usarán como entrada. Los juicios de relevancia se derivarán de OSV, cuyos registros vinculan cada aviso con sus CVE equivalentes y con los paquetes y versiones afectados: grado 2 si la CVE afecta la versión consultada, 1 si afecta al paquete en otras versiones y 0 en otro caso. Las consultas serán entre 300 y 500 paquetes de npm, PyPI, Maven, Go y NuGet, divididos en conjuntos de desarrollo y de prueba.

*Sistemas.* Se implementarán en PyTerrier [9] modelos TF-IDF, BM25 y de lenguaje con distintas tokenizaciones (palabras, n-gramas de caracteres y separación de nombres compuestos), BM25F por campos, un recuperador denso basado en Sentence-BERT [10] indexado con FAISS (búsqueda exacta, IVF y HNSW) y la fusión de rankings mediante RRF [11].

*Evaluación.* Se reportarán R@10, R@100, nDCG@10, MAP, MRR y P@10, curvas de precisión y exhaustividad y la distribución por consulta, con pruebas de significancia pareadas y corrección por comparaciones múltiples [12]. Los parámetros se ajustarán solo con el conjunto de desarrollo. Los resultados se estratificarán según la descripción mencione o no el nombre del paquete, la autoridad emisora, el gestor de paquetes y la fecha de publicación. Una muestra de los juicios automáticos se revisará manualmente para estimar su ruido. Se medirán también el tamaño de los índices, el tiempo de indexación y la latencia de consulta.

*Caso de estudio.* El mejor sistema se aplicará al SBOM de un clúster Kubernetes que ejecuta la aplicación de referencia Online Boutique, y sus resultados se contrastarán con los del escáner Trivy.

## 5. Cronograma

| Semanas | Actividad |
|---|---|
| 1 y 2 | Descarga de NVD y OSV, construcción de consultas y juicios, auditoría de una muestra |
| 3 | Modelos léxicos y tokenizaciones |
| 4 | Recuperador denso, índices FAISS y fusión |
| 5 | Evaluación, pruebas de significancia, estratos y eficiencia |
| 6 | Caso de estudio |
| 7 y 8 | Redacción del informe y preparación de la presentación |

## Referencias

[1] NIST (2026, 15 de abril). NIST Updates NVD Operations to Address Record CVE Growth. https://www.nist.gov/news-events/news/2026/04/nist-updates-nvd-operations-address-record-cve-growth

[2] Chen, Y., Santosa, A. E., Sharma, A. y Lo, D. (2020). Automated identification of libraries from vulnerability data. ICSE-SEIP 2020, pp. 90-99. https://doi.org/10.1145/3377813.3381360

[3] Lyu, Y., Le-Cong, T., Kang, H. J., Widyasari, R., Zhao, Z., Le, X.-B. D., Li, M. y Lo, D. (2023). CHRONOS: Time-Aware Zero-Shot Identification of Libraries from Vulnerability Reports. ICSE 2023, pp. 1033-1045. https://doi.org/10.1109/ICSE48619.2023.00094

[4] Chen, T., Li, L., Zhu, L., Li, Z., Liu, X., Liang, G., Wang, Q. y Xie, T. (2024). VulLibGen: Generating Names of Vulnerability-Affected Packages via a Large Language Model. ACL 2024, pp. 9767-9780. https://doi.org/10.18653/v1/2024.acl-long.527

[5] Wåreus, E. y Hell, M. (2020). Automated CPE Labeling of CVE Summaries with Machine Learning. DIMVA 2020, LNCS, pp. 3-22. https://doi.org/10.1007/978-3-030-52683-2_1

[6] Radaideh, R. y Khreis, A. (2026). SMSI: System Model Security Inference: Automated Threat Modeling for Cyber-Physical Systems. arXiv:2604.23905.

[7] Anwar, A., Abusnaina, A., Chen, S., Li, F. y Mohaisen, D. (2022). Cleaning the NVD: Comprehensive Quality Assessment, Improvements, and Analyses. IEEE TDSC 19, pp. 4255-4269. https://doi.org/10.1109/TDSC.2021.3125270

[8] Rosso, M., Jaffar, M. A. J., Brighente, A. y Conti, M. (2025). A Practical Solution to Systematically Monitor Inconsistencies in SBOM-based Vulnerability Scanners. arXiv:2512.17710 (SAC '26).

[9] Macdonald, C., Tonellotto, N., MacAvaney, S. y Ounis, I. (2021). PyTerrier: Declarative Experimentation in Python from BM25 to Dense Retrieval. CIKM 2021, pp. 4526-4533. https://doi.org/10.1145/3459637.3482013

[10] Reimers, N. y Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. EMNLP-IJCNLP 2019, pp. 3980-3990. https://doi.org/10.18653/v1/D19-1410

[11] Cormack, G. V., Clarke, C. L. A. y Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. SIGIR 2009, pp. 758-759. https://doi.org/10.1145/1571941.1572114

[12] Smucker, M. D., Allan, J. y Carterette, B. (2007). A comparison of statistical significance tests for information retrieval evaluation. CIKM 2007, pp. 623-632. https://doi.org/10.1145/1321440.1321528
