# Propuesta TP Final — Agente de Alertas y Recuperación para Acciones USA/CEDEARs/ETFs

Objetivo
- Reducir la necesidad de monitoreo 24/7: el sistema ingiere precios y noticias, recupera y rankea documentos relevantes para cada instrumento del portfolio (acciones USA y ETFs con CEDEARs), y emite alertas accionables (venta/mantener/atención) basadas en señales de precio, eventos y sentimiento.
- Todo con herramientas y fuentes gratuitas, reutilizando solo la teoría y componentes de RI necesarios (tokenización, índice invertido, BM25, DAAT/TAAT; opcional compresión y embeddings).

Alcance
- Instrumentos: acciones listadas en Wall Street (incluye casos como MELI, YPF si cotizan en USA) y ETFs con CEDEAR (SPY/VOO, QQQ, XLK, GLD, SLV, etc.).
- Portfolio: carga manual mediante interfaz interactiva (CLI inicialmente). Campos: `ticker` (USA o CEDEAR, sin sufijos como `.BA`), `cantidad`, `precio_entrada`, `fecha_entrada`. Internamente se manejará el mapeo CEDEAR↔subyacente cuando sea necesario, pero se evita exponer sufijos en la interfaz.
- Idiomas: inglés/español; normalización básica.

Fuentes Gratuitas
- Precios: `yfinance` (Yahoo Finance) para USA y CEDEARs `.BA` cuando existan; histórico y pseudo‑intraday.
- Noticias:
  - `GDELT 2.0` (Docs API) — cobertura global y acceso gratuito.
  - RSS públicos: Reuters Business, CNBC, MarketWatch, Yahoo Finance.
  - SEC/EDGAR RSS para filings (8‑K, 10‑Q, 10‑K, earnings).
- Reddit:
  - API oficial (app gratuita con límites) y/o RSS; subreddits: `r/investing`, `r/stocks`, `r/wallstreetbets`, `r/ArgentinaEconomics` (si aplica al caso).

Arquitectura
- Pipeline: ingesta diaria → normalización → persistencia → indexación → consulta → ranking → alertas → resumen diario por LLM.
- Ingesta: ejecución diaria (y refrescos intraday opcionales) para precios y documentos (RSS/GDELT/Reddit) por palabras clave y ticker.
- Normalización: extracción de texto/título/fecha/fuente; detección de tickers/empresa (diccionario + regex); idioma; deduplicación por `url` y hash.
- Persistencia (gratis y simple):
  - `SQLite`: tablas `portfolio` (posiciones), `docs` (texto/fuente/timestamp/tickers), `signals` (precio/volumen/eventos), `alerts` (historial y umbrales), `digests` (resúmenes diarios generados por LLM por ticker/fecha).
  - Motor de búsqueda open source (prioritario): `Meilisearch` local (BM25/sparse) para indexar y recuperar documentos con filtros; integración simple vía API. Alternativa 100% Python: `Whoosh` (BM25) si preferimos evitar servicios. Opcional: `FAISS` para representaciones densas (embeddings `sentence-transformers`) y ranking híbrido. (El BSBI propio queda como alternativa si se requiere análisis de estructuras; priorizamos integración sencilla con LLM/LangChain.)
  - Alternativas IR (a discutir con profesor): `Terrier`/`PISA` para indexación sparse + `FAISS` para re‑rank denso; `Vespa` u `OpenSearch` local si se quiere un engine completo con ranking flexible.
 - Frontend: React (Vite) con `MUI`/`Ant Design` y gráficos `Recharts`/`Plotly`.
 - Backend: `FastAPI` exponiendo endpoints para portfolio, ingesta, búsqueda, alertas y digests.

Consultas e Índice
- Consultas por instrumento: query base `[ticker|empresa] + eventos (earnings, downgrade, lawsuit, guidance, insider, dividend, buyback)` + alias/sinónimos.
- Filtros: por `ticker`, ventana temporal (últimas X horas/días), tipo de fuente (RSS/GDELT/Reddit/SEC).
- Índice invertido: tokenización, stopwords y stemming; postings con TF, DF y longitud de documento; DAAT/TAAT según necesidad. 
- Modelo BM25 como columna vertebral:
  - $BM25(q,d)=\sum_{t\in q}idf(t)\cdot\frac{f(t,d)(k_1+1)}{f(t,d)+k_1\cdot(1-b+b\cdot\frac{|d|}{avgdl})}$
 - Uso de resúmenes diarios (LLM): cuando existan `digests` para un ticker/fecha, las consultas del día siguiente pueden apoyarse primero en esos resúmenes para reducir costos, y sólo ampliar al índice completo si se requiere más contexto.

  Integración LLM y Automatización de Consultas
    - Nota (feedback profesor): es viable prescindir de `LangChain/LangGraph` y construir el pipeline explícito en Python (módulos puros + cron), evitando ocultar detalles. LangGraph queda como opcional si se justifica su uso.
    - `Tool: search_sparse(query, filters)` → consulta Meilisearch (BM25) con filtros (`ticker`, ventana temporal, fuente) o Whoosh si se elige la alternativa Python.
    - `Tool: search_dense(embedding_query)` → consulta FAISS sobre embeddings (opcional) para recuperación semántica.
    - `Tool: get_digest(ticker, date)` → recupera resúmenes diarios persistidos y los usa como contexto previo.
    - `Tool: upsert_docs(docs)` → inserta documentos nuevos en `SQLite` y los publica en el índice.
    - `Tool: get_portfolio()` / `Tool: set_portfolio()` → lectura/escritura del portfolio.
     - El agente construye y programa consultas automáticamente a partir del portfolio y del calendario de eventos (earnings, downgrades, filings). Con `LangGraph` implementamos el grafo de estados del agente (planificación → recuperación → síntesis → alertado) y usamos componentes LangChain para RAG y tool‑calling manteniendo todo gratuito/local.

Ranking (¿Para qué sirve y cómo?)
- Propósito: priorizar lo más relevante y urgente para decidir si actuar (vender/mantener), reduciendo ruido.
- Híbrido: `score = w1*BM25 + w2*sentimiento + w3*recencia + w4*autoridad` (pesos y funciones sencillos, privilegiando técnicas comunes).
  - Recencia: decaimiento temporal para favorecer documentos recientes.
  - Sentimiento: VADER (rápido/gratis) o `finbert` opcional si recursos.
  - Autoridad: prior simple por whitelist (Reuters/SEC > blogs/foros).
- Uso del índice: consultas eficientes sobre corpus grande; DAAT/TAAT aceleran respuesta; el ranking alimenta las alertas (se disparan sólo si `score` supera umbrales configurables).
 - Componente LLM: generación de resúmenes diarios y respuesta a consultas explicativas (RAG sobre top‑k documentos y/o sobre `digests` del día). Se prioriza un flujo simple, con modelos locales/gratuitos cuando sea posible.

Alertas
- Precio: 
  - Caída intraday/daily > umbral (p.ej., −3% intraday, −5% diario).
  - Volumen inusual vs promedio (siempre con datos gratis disponibles).
  - Gap post‑earnings.
- Noticias: 
  - Top‑k documentos de alta relevancia y sentimiento negativo fuerte recientes.
 - Entrega inicial: interfaz web simple (React) para cargar/editar portfolio y ver alertas con resúmenes (LLM) del día. Si se prefiere, puede mantenerse una CLI como alternativa.

Señales y Recomendaciones (reactivas y preventivas)
- Señales reactivas (precio): a partir de `yfinance`, se calcula la variación entre los dos últimos cierres (diario/intraday). Si `|Δ%| ≥ umbral` (p.ej., 3%), se genera una señal `price_change` con dirección positiva/negativa y se lanza una consulta explicativa (por ejemplo, `[ticker] (downgrade|upgrade|earnings|guidance|lawsuit|buyback|dividend)` en ventana temporal reciente) para entender la causa.
- Señales preventivas (noticias): para cada documento reciente por ticker del portfolio se calcula un `score` preventivo que combina:
  - Sentimiento (`VADER` sobre título+texto, `compound ∈ [-1,1]`).
  - Autoridad de fuente (peso mayor para `reuters.com`, `sec.gov`; medio para `marketwatch.com`, `finance.yahoo.com`, `cnbc.com`).
  - Recencia (decaimiento exponencial con vida media 48h para favorecer lo reciente).
  - Evento por keywords (boost por `upgrade`, `beat earnings`, `buyback`, `dividend increase`, `guidance raise`, `approval`; penalización por `downgrade`, `lawsuit`, `miss earnings`, `guidance cut`, `layoff`, `investigation`).
  - Fórmula simple: `score_preventivo = sentimiento * autoridad * recencia + event_boost`.
  - Umbral típico: `|score| ≥ 0.6` → se crea señal `news_sentiment` y una alerta preventiva con recomendación.
- Recomendaciones: mapeo directo por score de noticia (ajustable por instrumento):
  - `score ≥ +0.6` → recomendación: comprar (buy).
  - `score ≤ −0.6` → recomendación: vender (sell).
  - En el intervalo → mantener (hold).
- Volumen (planificado): comparar volumen del día vs promedio de 20 días; si `vol_actual ≥ 2× vol_promedio`, generar señal `volume_spike` (dirección según contexto de precio/noticias).
- Orquestación: las señales (precio/noticias/volumen) se persisten en `SQLite` (`signals`) y alimentan el agente (LangGraph) para: 1) lanzar búsquedas explicativas, 2) generar resúmenes diarios (`digests`), y 3) emitir alertas con la recomendación cuando corresponda.

Persistencia y BD
- `SQLite` para estado del sistema, portfolio, trazabilidad de documentos/señales/alertas; índices simples en columnas clave (`ticker`, `timestamp`).
- Índice BSBI en disco: separación vocabulario/postings; amigable a crecimiento del corpus y pruebas de eficiencia.
- Políticas de retención: ventana temporal configurable (p. ej., 30–90 días) para control de tamaño.

Evaluación (cumplir consigna RI, foco principal)
- Objetivo: medir performance de recuperación de información (lo visto en teoría). La evaluación de LLM es secundaria/optativa.
- Dataset: dos opciones según disponibilidad:
  - Dataset existente (TREC, Reuters‑21578, MSMARCO u otro) para validar ranking sparse/denso con métricas estándar.
  - Dataset propio con 5–10 tickers/ETFs en un período con eventos; etiquetar documentos por relevancia para “alerta” (sí/no) usando reglas + verificación manual.
- Métricas IR: P@k, MAP, NDCG@k, MRR y Recall@k; además tiempos de consulta (DAAT vs TAAT), tamaño de índice y memoria.
- Experimentos/Ablations: BM25 vs híbrido; con/sin sentimiento; con/sin recencia; variaciones de pesos `w1..w4`.
- Criterios de éxito: mejora significativa de NDCG@10 y Recall@k con latencia aceptable (<1–2s por consulta típica).
- Evaluación objetiva: separar ajuste de parámetros vs evaluación final; reportar trade‑off precisión/recall y análisis de errores.

Entregables
- Propuesta en prosa de 1–2 páginas (este documento guía) para revisión y aprobación.
 - Código modular (`backend` FastAPI + `frontend` React, `ingesta`, `persistencia`, `busqueda` Meilisearch/Whoosh, `ranking`, `alertas`, `llm_agent`) con `README` de uso.
 - Demo web: cargar/editar portfolio manualmente, ver feed de documentos y gráficos, ejecutar consultas programadas y mostrar alertas/top‑k.
 - Informe: diseño mapeado a guías necesarias (solo las imprescindibles), evaluación con métricas comunes y discusión.

Selección Tecnológica y Alternativas (rationale)
- Motores de búsqueda (RI tradicional):
  - Elegido: `Meilisearch` local — rendimiento muy bueno, API simple, filtros por campos (ticker/fecha/fuente), BM25, despliegue liviano y gratuito.
  - Alternativa: `Whoosh` (100% Python) — evita servicios externos, ideal para prototipos; rendimiento menor y menos cómodo para servir vía API; viable si se prioriza “todo en Python”.
  - Alternativa académica/industrial: `Terrier`/`PISA` para indexación sparse + `FAISS` para re‑rank denso (pipeline híbrido).
  - Alternativa industrial: `Vespa`/`OpenSearch` local si se quiere un engine completo con ranking custom.
  - No elegido: `Elasticsearch` — potente pero pesado (recursos y gestión), complejidad de despliegue que excede el MVP “simple/gratis”; integra bien con LangChain, pero no es necesario.
  - No elegido: `MongoDB Atlas Search` — servicio gestionado con posibles costos/límites; el objetivo es local/gratuito.
  - No elegido: `Vertex AI Search` — cloud/$$, fuera del alcance “todo gratis”.
  - Considerado: `BM25Retriever` (LangChain) — capa de integración útil para RAG sobre `digests`, pero no reemplaza un motor para indexar el corpus completo.
- Orquestación LLM:
  - Elegido: `LangGraph` (sobre LangChain) — grafo de estados para agentes, mejor control del bucle (stop/continue), manejo de memoria/estado, determinismo y observabilidad; integra herramientas de LangChain sin fricción.
  - Alternativa: `LangChain` puro — suficiente para RAG y tool‑calling; elegimos LangGraph por la robustez del ciclo de agente y la claridad del flujo multi‑paso.
  - Alternativa: `LlamaIndex` — opción válida para indexación y RAG; priorizamos LangGraph/LangChain por ecosistema y flexibilidad.
  - Modelos: preferencia por resúmenes extractivos (TextRank) y, si hace falta, modelos locales/gratuitos; evitar dependencias de pago.
- Frontend:
  - Elegido: React (Vite) + `MUI`/`Ant Design` + `Recharts`/`Plotly` — amplio ecosistema de componentes, rápido de construir y mantener.
  - Simplicidad: UI mínima; el front no es determinante para la nota final; se prioriza claridad y mantenibilidad (CLI opcional).
- Almacenamiento:
  - Elegido: `SQLite` — simple, local y suficiente para MVP; gratis y fácil de portar.
  - Alternativas (Postgres/Elastic stack): más pesadas; innecesarias para el alcance inicial.
- Índice propio (BSBI del TP):
  - Uso opcional para análisis académico/eficiencia. Para producción y agentes LLM, preferimos Meilisearch/Whoosh por su API y facilidad.
- Recuperación densa:
  - `FAISS` opcional para embeddings de `sentence-transformers`. Se activará sólo si aporta mejoras claras (ablation), manteniendo costos cero y ejecución local.

Papers y relación con el proyecto
- Paper 1 (arXiv 2407.15788, “Extracting Structured Insights from Financial News”): propone extraer tickers, sentimiento por compañía y resúmenes desde noticias crudas con validación de mapeo ticker‑empresa; reporta evaluación en 5530 artículos. Relevancia: justifica la etapa de extracción de tickers y sentimiento, y provee dataset auxiliar (noticias con sentimiento a nivel ticker).
- Paper 2 (Findings EMNLP 2025, “FinGEAR”): enfoque retrieval‑first para documentos financieros largos (10‑K), con estructura jerárquica, léxico financiero y re‑ranker. Relevancia: inspira recuperación estructurada para filings SEC y uso de señales léxicas/jerárquicas + re‑ranking.
- Paper 3 (Expert Systems with Applications 2011, “Financial news semantic search engine”): arquitectura con crawling, anotación semántica y búsqueda para noticias financieras. Relevancia: respalda la arquitectura crawler→indexación→ranking y la necesidad de integración de fuentes heterogéneas.
- Dataset sugerido: Kaggle “Yahoo Finance News” como corpus base de noticias para evaluación IR; complementario al dataset del Paper 1.
- Teoría de evaluación (Guía 3 – Evaluación de la Recuperación): usar métricas estándar (P@k, MAP, NDCG, MRR, Recall) y análisis de trade‑offs; justificar pooling/etiquetado y separación ajuste vs evaluación final.


Consideraciones Iniciales
- Mapping CEDEAR↔USA: `tickers_map.json` mantenible; se evita mostrar sufijos `.BA` en la interfaz; confirmar casos especiales (MELI, YPF).
- Portfolio: carga manual mediante CLI interactiva; sin dependencia de export/formatos externos.
- Umbrales por defecto (ajustables por instrumento): precio −3% intraday/−5% diario; sentimiento ≤ −0.6; top‑k=5; recencia ≤ 72h.
- LLM gratis: empezar con resumen extractivo (TextRank) y, opcionalmente, embeddings (`sentence-transformers`) + `FAISS` para semántica sin costo. Generar y persistir resúmenes diarios (`digests`) para agilizar el procesamiento futuro.
- Simplificación y foco: usar técnicas sencillas y métricas comunes; no es necesario aplicar toda la teoría ni todo el código, solo lo imprescindible.

Propuesta final (1 hoja)

Este trabajo propone un agente de recuperación y alertas para inversiones que reduce el monitoreo manual mediante un pipeline de crawling, indexación y ranking sobre noticias y filings financieros. El sistema permite cargar un portfolio (tickers USA/ETFs con CEDEAR) y automáticamente ingiere noticias (RSS/GDELT/SEC), normaliza y deduplica documentos, los indexa con un motor BM25 (Meilisearch/Whoosh o Terrier/PISA) y recupera evidencia relevante por ticker y ventana temporal. Sobre los resultados, aplica ranking híbrido (BM25 + recencia + autoridad + sentimiento) y dispara alertas con recomendaciones. La recuperación es el foco principal de evaluación: se reportan P@k, MAP, NDCG@k, MRR y Recall@k, además de latencia (DAAT/TAAT), tamaño de índice y memoria. La evaluación se realiza con un dataset existente (p. ej. Yahoo Finance News) y/o un dataset propio de 5–10 tickers en períodos con eventos, separando ajuste de parámetros y evaluación final.

El diseño se apoya en trabajos recientes: (1) el paper de arXiv 2407.15788 sobre extracción de tickers y sentimiento desde noticias crudas, que respalda la etapa de extracción y ofrece un dataset de 5530 artículos; (2) FinGEAR (EMNLP 2025), que demuestra mejoras significativas en recuperación para documentos financieros largos con estructura jerárquica y léxico especializado; (3) la arquitectura de búsqueda semántica para noticias financieras (ESWA 2011), que valida el enfoque crawler→indexación→ranking. El componente LLM es opcional y se limita a resúmenes diarios; no es el eje de evaluación. El sistema se ejecuta localmente y sin costo (Meilisearch/Whoosh o Terrier/PISA + FAISS opcional) cumpliendo la consigna de RI y priorizando métricas objetivas de recuperación.

Este proyecto propone un agente de recuperación y alertas para inversiones que reduzca la necesidad de monitoreo constante de fuentes financieras. El sistema permite cargar tu portfolio de manera manual (interfaz gráfica) con acciones de USA y ETFs que tengan CEDEAR, y se encarga de buscar, normalizar y priorizar información relevante para cada instrumento: movimientos de precio, noticias, eventos corporativos y señales provenientes de foros. A partir de esta información, produce alertas accionables y resúmenes diarios que facilitan decidir si conviene vender, mantener o simplemente estar atento.

El alcance se centra en instrumentos listados en Wall Street (incluyendo casos como MELI o YPF si cotizan en USA) y en ETFs populares con CEDEAR (por ejemplo, SPY/VOO, QQQ, XLK, GLD, SLV). La carga del portfolio será manual, sin dependencia de formatos externos: la interfaz gráfica solicitará el `ticker` (sin sufijos como `.BA`), la cantidad, el precio y la fecha de entrada. Internamente, el sistema mantiene un mapeo CEDEAR↔subyacente cuando haga falta, pero la experiencia de usuario siempre muestra el ticker sencillo.

La ingesta se realizará diariamente (con refrescos intraday opcionales) desde fuentes gratuitas. Para precios se usará `yfinance` (Yahoo Finance), que provee histórico y actualizaciones cercanas al tiempo real sin costo. Para noticias se combinarán `GDELT 2.0` (Docs API) y RSS públicos de medios financieros (Reuters, CNBC, MarketWatch, Yahoo Finance), además de los RSS de SEC/EDGAR para filings relevantes. En foros, se consultarán subreddits como `r/investing`, `r/stocks` y `r/wallstreetbets` mediante API o RSS. Cada documento detectado se normaliza (texto, título, fecha, fuente, tickers mencionados), se deduplica por URL y hash, y se persiste.

La persistencia se resuelve con `SQLite`, manteniendo tablas para `portfolio` (posiciones), `docs` (documentos y metadatos), `signals` (señales de precio/volumen/eventos), `alerts` (historial de alertas) y `digests` (resúmenes diarios por ticker y fecha). Además, se construye un índice invertido en disco (BSBI) para el corpus de noticias/foros, con tokenización, stopwords y stemming; el índice guarda TF/DF, longitud de documento y permite consultas eficientes. Las consultas por instrumento combinan el nombre/ticker con términos de eventos frecuentes (earnings, downgrade, lawsuit, guidance, insider, dividend, buyback) y filtros por ventana temporal, fuente y ticker.

El ranking utiliza BM25 como columna vertebral y añade señales sencillas pero útiles: recencia (favorecer lo reciente), sentimiento (VADER como opción gratuita, con finbert opcional si se dispone de recursos) y autoridad de la fuente (prior simple que pondera Reuters/SEC sobre blogs/foros). La puntuación final es híbrida y fácil de ajustar: `score = w1*BM25 + w2*sentimiento + w3*recencia + w4*autoridad`. Este ranking alimenta el motor de alertas: solo dispara cuando el score supera umbrales configurables o cuando se detectan condiciones de precio (por ejemplo, caída diaria > −5% o intraday > −3%) y volumen inusual. Para mejorar la experiencia diaria, el sistema genera resúmenes por instrumento utilizando un LLM gratuito/local o un sumarizador extractivo (TextRank), y los guarda como `digests`. Así, las consultas del día siguiente pueden apoyarse primero en esos resúmenes (datos “masticados”), ampliando al índice completo solo si se requiere contexto adicional.

La interfaz será web, por su flexibilidad y facilidad de uso: un backend en `FastAPI` (o Flask) servirá endpoints para ingesta, consultas y alertas, y un frontend ligero mostrará paneles con tu portfolio, precios recientes, feed de documentos rankeados y alertas activas. Para gráficos, se empleará `Plotly` o `Chart.js`: por ejemplo, curvas de precio y variación diaria por ticker, volumen vs promedio, conteo de alertas por tipo, y paneles de evaluación (P@k/MAP/NDCG). La interfaz incluirá controles para ajustar umbrales de alertas y pesos del ranking, y una vista de “resumen diario” generado por el LLM con enlaces a los documentos clave.

La evaluación del sistema, en línea con la consigna de Recuperación de la Información, usará métricas comunes y sencillas: Precisión@k, MAP y NDCG@k para medir la calidad del ranking en un conjunto de tickers y un período con eventos relevantes (earnings, downgrades, filings), junto a tiempos de respuesta (DAAT vs TAAT) para eficiencia. Se realizarán comparaciones simples: BM25 puro vs ranking híbrido; con/sin sentimiento; con/sin recencia; variaciones de pesos. Los criterios de éxito incluyen elevar NDCG@10, reducir alertas falsas y mantener latencias prácticas (<1–2s por consulta típica).

En resumen, este agente combina ingesta diaria gratuita, un índice invertido eficiente, un ranking interpretable y un LLM para resúmenes, entregando una experiencia web clara: cargar tu portfolio, ver cambios y noticias clave, recibir alertas cuando importan y revisar un resumen diario que condense lo más relevante. La solución prioriza la simplicidad y la robustez: técnicas estándar, métricas comunes y componentes gratuitos para cumplir la consigna del TP final sin complejidad innecesaria.
