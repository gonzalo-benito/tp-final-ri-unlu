El tercer artículo que has proporcionado, **"Financial news semantic search engine"** de Lupiani-Ruiz et al., aporta una perspectiva complementaria muy valiosa para tu proyecto: el uso de **tecnologías semánticas y ontologías** para estructurar la información financiera, algo que puedes integrar perfectamente con el enfoque de LLMs que ya tenías.

Aquí te detallo cómo este nuevo documento puede enriquecer tu propuesta y cómo utilizarlo para los desafíos que te planteó tu profesor:

### 1. Evolución del Índice: De Índice Plano a Ontología Financiera
Mientras que los otros artículos se enfocan en vectores o jerarquías de documentos, este trabajo propone que el "corazón" del sistema sea una **ontología financiera**.
*   **Aplicación a tu proyecto:** En lugar de solo tener un índice de noticias por *ticker*, podrías definir una estructura jerárquica (clases de activos, sectores económicos, tipos de eventos como "dividendos" o "fusiones"). Esto te permitiría implementar los **filtros por actividad económica** o categorías que el artículo menciona como una ventaja clave sobre buscadores tradicionales como Yahoo Finance.

### 2. Población Automática desde Fuentes Heterogéneas
El artículo describe un módulo de **población de ontologías** que extrae datos de tablas HTML y feeds RSS para crear "instancias" de forma automática.
*   **Relevancia técnica:** Esto valida tu idea de hacer *crawling* de sitios como Yahoo Finance. Puedes citar este paper para justificar tu metodología de extracción de datos estructurados (precios, volúmenes, nombres de empresas) a partir de tablas web para mantener tu base de conocimientos actualizada en tiempo real.

### 3. Procesamiento Semántico de Consultas (Query Processing)
A diferencia de los otros textos, este detalla un pipeline claro para procesar la intención del usuario:
*   **Expansión de Consultas:** El sistema realiza etiquetado POS (Part-of-Speech), lematización y búsqueda de **sinónimos financieros** antes de ejecutar la búsqueda.
*   **Uso en tu agente:** Puedes usar este enfoque para que tu agente no solo busque el ticker (ej. "AAPL"), sino que entienda conceptos relacionados (ej. "tecnología", "iPhone", "Alphabet" vs "Google") para recuperar noticias más ricas semánticamente.

### 4. Justificación y Evaluación (Lo que pidió tu profe)
Este artículo te da argumentos sólidos para la sección de "Trabajos Relacionados" y para definir tu marco de evaluación:
*   **Comparación con lo tradicional:** El paper argumenta que los buscadores basados en palabras clave sufren de **ambigüedad lingüística** (sinonimia y polisemia). Tu proyecto puede evaluarse midiendo cuánto mejora tu agente la precisión al usar un enfoque semántico/LLM frente a una búsqueda por palabras clave simple.
*   **Validación mediante Casos de Uso:** Los autores validaron su arquitectura con el mercado español (IBEX35). Tú puedes proponer una validación similar para los CEDEARs o Wall Street, utilizando la **precisión y el recall** de las anotaciones semánticas como métricas de éxito.

### Integración de Tecnologías Sugeridas
El profesor te mencionó usar **Terrier o PISA (rala)** y **FAISS (densa)**. Según las fuentes:
*   Puedes usar el enfoque de **anotación semántica** de este nuevo paper para etiquetar tus documentos antes de indexarlos.
*   Luego, podrías usar la búsqueda rala (Terrier) para los términos de la ontología y la búsqueda densa (FAISS) para la similitud de significado, uniendo ambos mundos en un sistema híbrido avanzado, tal como sugiere el artículo de **FinGEAR**.

En resumen, el **Paper 3** te ofrece la base teórica para organizar tu base de datos de noticias de una manera mucho más "inteligente" y profesional que un simple repositorio de archivos, permitiendo que tu LLM consulte una base de conocimientos estructurada y validada.