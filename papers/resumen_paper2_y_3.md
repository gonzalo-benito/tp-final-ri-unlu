Para tu proyecto final de Recuperación de Información (RI), los artículos proporcionados ofrecen un marco sólido para definir **cómo evaluar** tu sistema de alertas de inversión. Según las fuentes, puedes dividir tu evaluación en tres ejes principales: la calidad de la recuperación (retrieval), la precisión en la extracción de entidades (tickers) y la utilidad de las respuestas generadas por el LLM.

A continuación, se detalla cómo aprovechar estos documentos para tu metodología de evaluación:

### 1. Evaluación de la Calidad de Recuperación (Ranking y Retrieval)
El artículo sobre **FinGEAR** sugiere un marco de evaluación muy completo para sistemas que combinan búsqueda densa y rala, similar a lo que propuso tu profesor.

*   **Métricas Estándar de RI:** Debes medir la **Precisión (Precision)**, el **Recall** y el **Fama (F1 Score)** de las noticias recuperadas. El F1 Score es especialmente útil para medir el equilibrio entre encontrar todas las noticias relevantes (frescura y relevancia) y no incluir ruido.
*   **Evaluación por Profundidad (Top-k):** Evalúa tu ranking en diferentes niveles, como **Top-5, Top-10 y Top-15**. Esto te permitirá observar cómo varía la precisión a medida que entregas más noticias al usuario o al LLM.
*   **Marco RAGAS:** El artículo menciona el uso de **RAGAS**, un framework para evaluar componentes de generación aumentada por recuperación, que incluye métricas de **Relevancia (Relevancy)** para asegurar que los pasajes recuperados realmente apoyen la intención de la consulta.

### 2. Evaluación de la Extracción de Datos (Tickers y Entidades)
El trabajo de **Dolphin et al.** es ideal para tu caso, ya que trata específicamente sobre noticias financieras y el mapeo de empresas a *tickers* de Wall Street.

*   **Comparación contra "Ground Truth":** Puedes evaluar tu agente comparando los tickers que extrae automáticamente contra los tags originales de los proveedores de noticias (como Yahoo Finance). 
*   **Análisis de "Misses" y Tickers Adicionales:** 
    *   Calcula el porcentaje de artículos donde tu sistema no omitió ningún ticker relevante (el estudio logró un 90%).
    *   Identifica **tickers adicionales** que tu sistema encuentre y que no estaban en la fuente original, evaluando si estos agregan valor (cobertura).
*   **Validación de Alucinaciones:** Implementa una evaluación de la fidelidad del mapeo empresa-ticker para detectar cuando el LLM "alucina" un símbolo (ej. confundir Pfizer con PFI en lugar de PFE).

### 3. Evaluación del Impacto y Sentimiento (LLM)
Dado que planeas usar un LLM para resumir y generar alertas ("mantener/vender"), puedes adoptar las siguientes estrategias de los artículos:

*   **Razonamiento de Sentimiento (Chain-of-Thought):** En lugar de solo evaluar si la alerta es "positiva" o "negativa", evalúa el **razonamiento intermedio**. Puedes realizar una inspección manual de una muestra para ver si la interpretación del impacto financiero es coherente con la noticia.
*   **Precisión de la Respuesta Final (Answer Accuracy):** Si tu agente responde preguntas o genera alertas, mide la precisión de estas respuestas finales utilizando un subconjunto de datos donde la respuesta sea conocida (por ejemplo, usando el dataset **FinQA** si decides incluir preguntas sobre informes 10-K).

### 4. Realización de Estudios de Ablación
Una recomendación metodológica clave de las fuentes es realizar **estudios de ablación**. En tu proyecto, esto significaría evaluar el rendimiento de tu sistema desactivando componentes uno por uno:
*   ¿Qué pasa con la relevancia si quitas el ranking por "frescura"?
*   ¿Cómo afecta al F1 Score si solo usas búsqueda densa (FAISS) sin la búsqueda rala (Terrier/PISA) que sugirió tu profesor?.

### Sugerencia de Dataset
Para tu evaluación objetiva, el profesor te sugirió el dataset de **Yahoo Finance News en Kaggle**. Puedes usarlo como tu "estándar de oro" para medir qué tan bien tu agente recupera noticias que ya están categorizadas por tickers y sectores en ese dataset.

**Nota importante:** La información sobre el uso específico de Terrier, PISA y la mención del CIDETIC provienen de tu conversación con el profesor y no están detalladas en los artículos científicos proporcionados, por lo que deberás seguir las guías técnicas de tu cátedra para la implementación de esas herramientas específicas.