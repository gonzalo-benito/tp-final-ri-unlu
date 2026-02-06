# Agente de Inversiones (MVP)

Stack:
- Backend: FastAPI + SQLite
- Búsqueda: Meilisearch (BM25) — alternativo Terrier
- Agente LLM: LangGraph (sobre LangChain) con tools
- Frontend: React (Vite) + MUI + Recharts

## Backend (FastAPI)

### Instalar deps
Notas:
- El entorno liviano evita dependencias pesadas (FAISS/`sentence-transformers`).
- Para un pipeline híbrido: indexación sparse con `Terrier`/`PISA` + re‑rank denso con `FAISS`.

```zsh
cd /home/gbenito/universidad/tp-final-ri-unlu/agente-inversiones/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Config rápida (recomendado): copiá los `.env.example` a `.env`.

### Lanzar API
```zsh
uvicorn app.main:app --reload --port 8000
```

Si tenés problemas de importación de `app`, probá:

```zsh
uvicorn --app-dir /home/gbenito/universidad/tp-final-ri-unlu/agente-inversiones/backend app.main:app --reload --port 8000
```

## Backend de búsqueda (Meilisearch o Terrier)

Por defecto se usa Terrier. Podés elegir el motor con `SEARCH_BACKEND`:

```zsh
export SEARCH_BACKEND=terrier
# o
export SEARCH_BACKEND=meilisearch
```

### Meilisearch

Descarga binario de Meilisearch y ejecútalo localmente (por defecto en `http://127.0.0.1:7700`).
Config opcional:
```zsh
export MEILI_HOST=http://127.0.0.1:7700
export MEILI_API_KEY=
export MEILI_INDEX=docs
```

### Terrier (opcional)
Requiere `python-terrier` y un índice offline ya construido.

```zsh
pip install python-terrier
export TERRIER_INDEX=/ruta/a/tu/index
export TERRIER_WMODEL=BM25
```

Si `pyterrier` no encuentra la JVM, definir:

```zsh
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export JVM_PATH=/usr/lib/jvm/java-17-openjdk-amd64/lib/server/libjvm.so
```

### Archivo .env
Backend: `agente-inversiones/backend/.env`
Frontend: `agente-inversiones/frontend/.env`

Variables principales (backend):
- `SEARCH_BACKEND`, `JAVA_HOME`, `JVM_PATH`
- `W_SENT`, `W_RECENCY`, `W_AUTH` (pesos de re‑ranking)
- `EXTRA_FEEDS`, `SEC_USER_AGENT`
- `GDELT_ENABLED`, `GDELT_DOC_API_URL`, `GDELT_MODE`, `GDELT_MAXRECORDS`

Construcción de índice desde SQLite (usa `backend/data/app.db` por defecto):

```zsh
cd /home/gbenito/universidad/tp-final-ri-unlu/agente-inversiones/backend
python -m app.terrier_index --overwrite
```

Notas:
- La indexación online desde el backend está deshabilitada para Terrier.
- La búsqueda funciona si el índice contiene metadatos como `title`, `text`, `url`, `source`, `timestamp`, `tickers`.

## Frontend (React)

### Instalar deps
```zsh
cd /home/gbenito/universidad/tp-final-ri-unlu/agente-inversiones/frontend
npm install
```

### Desarrollo
```zsh
npm run dev
# abrir http://127.0.0.1:5173
```

## Prueba rápida
1. Inicia backend y Meilisearch.
2. En frontend, agrega un ticker al portfolio.
3. Endpoints útiles:
	- `POST /ingest/news`: ingesta de noticias RSS + Yahoo Finance por ticker
	- `POST /ingest/prices?threshold=3.0`: genera alertas por caída de precio
	- `GET /alerts`: lista últimas alertas
	- `POST /signals/run/news?threshold=0.6&window_hours=72`: señales preventivas por noticias (sentimiento/autoridad/recencia)
	- `POST /signals/run/volume?avg_days=20&multiplier=2.0`: señales de volumen inusual
	- `GET /signals`: lista señales (filtro opcional por `ticker`)
	- `GET /search?q=...&ticker=...&w_sent=0.5&w_recency=0.3&w_auth=0.2`: búsqueda con re-ranking híbrido
	- `GET /recommendation/{ticker}?window_hours=72`: recomendación agregada (buy/sell/hold) con confianza
	- `POST /docs`: ingesta manual de documentos
4. Usa el campo de búsqueda en la UI para ver resultados.

## Notas
- `app/tools.py` contiene wrappers de herramientas para el agente.
- `app/clients/meilisearch_client.py` maneja indexación y búsqueda.
- Esquema SQLite en `app/db.py`.
- Próximos pasos: ingesta RSS/GDELT/Reddit, alertas de precio, generación de `digests` diarios, RAG y métricas RI.
 - Endpoints de ingesta y alertas disponibles para pruebas locales.

### Fuentes RSS actuales
- Reuters, CNBC, MarketWatch y SEC EDGAR (current filings).
- Yahoo Finance por ticker (endpoint dedicado).

GDELT (opcional):
```zsh
export GDELT_ENABLED=1
export GDELT_DOC_API_URL=https://api.gdeltproject.org/api/v2/doc/doc
export GDELT_MODE=ArtList
export GDELT_MAXRECORDS=50
```

Configuración opcional:
```zsh
export EXTRA_FEEDS="https://feeds.marketwatch.com/marketwatch/marketpulse/"
export SEC_USER_AGENT="tp-final-ri-unlu/1.0 tuemail@ejemplo.com"
```
