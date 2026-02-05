"""Generación de señales (price/news/volume) y recomendaciones preventivas.
Combina sentimiento (VADER), autoridad de fuente y recencia para señales de noticias.
"""
from typing import List, Dict, Tuple
from datetime import datetime, timezone, timedelta
import math
import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .db import get_conn
from .ingestion import _get_portfolio_tickers
from .alerts import create_alert
from .ingestion import fetch_prices


analyzer = SentimentIntensityAnalyzer()


AUTHORITY_WEIGHTS = {
    "reuters.com": 1.0,
    "sec.gov": 1.0,
    "marketwatch.com": 0.8,
    "finance.yahoo.com": 0.7,
    "cnbc.com": 0.8,
}

EVENT_KEYWORDS = {
    # negativos
    "downgrade": -1.0,
    "lawsuit": -1.0,
    "guidance cut": -0.8,
    "miss earnings": -1.0,
    "layoff": -0.6,
    "recall": -0.6,
    "investigation": -0.7,
    "negative outlook": -0.8,
    # positivos
    "upgrade": 1.0,
    "beat earnings": 1.0,
    "buyback": 0.8,
    "dividend increase": 0.8,
    "guidance raise": 0.9,
    "approval": 0.9,
    "partnership": 0.6,
}


def _extract_source(host_or_url: str) -> str:
    try:
        host = re.sub(r"^https?://", "", host_or_url).split("/")[0]
        return host
    except Exception:
        return host_or_url


def _iso_to_datetime(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def _recency_decay(ts_iso: str, half_life_hours: float = 48.0) -> float:
    now = datetime.now(timezone.utc)
    ts = _iso_to_datetime(ts_iso)
    age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
    lam = math.log(2) / half_life_hours
    return math.exp(-lam * age_hours)


def create_signal(ticker: str, sig_type: str, score: float, direction: str, doc_url: str | None = None, details: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO signals (ticker, type, score, direction, doc_url, details, created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
        (ticker.upper(), sig_type, float(score), direction, doc_url or None, details or None),
    )
    conn.commit()
    conn.close()


def recommendation_from_score(score: float) -> str:
    if score >= 0.6:
        return "buy"
    if score <= -0.6:
        return "sell"
    return "hold"


def aggregate_recommendation_for_ticker(ticker: str, window_hours: float = 72.0) -> dict:
    """Agrega señales recientes (precio/noticias/volumen) para un ticker y devuelve recomendación con confianza.
    Estrategia simple: promedio ponderado de scores normalizados.
    """
    from datetime import datetime, timezone, timedelta

    t = ticker.upper()
    conn = get_conn()
    cur = conn.cursor()
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    cutoff_iso = cutoff_dt.isoformat()
    cur.execute(
        "SELECT type, score, direction, created_at FROM signals WHERE ticker=? AND created_at >= ? ORDER BY created_at DESC",
        (t, cutoff_iso),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {"ticker": t, "window_hours": window_hours, "recommendation": "hold", "confidence": 0.0, "signals": []}

    signals = []
    agg = 0.0
    weight_sum = 0.0
    for sig_type, score, direction, created_at in rows:
        w = 1.0
        # pesos por tipo: noticias y precio más altos, volumen medio
        if sig_type == "news_sentiment":
            w = 1.0
        elif sig_type == "price_change":
            w = 0.9
        elif sig_type == "volume_spike":
            w = 0.6
        s = float(score)
        agg += w * s
        weight_sum += w
        signals.append({"type": sig_type, "score": s, "direction": direction, "created_at": created_at})

    avg = agg / weight_sum if weight_sum > 0 else 0.0
    rec = recommendation_from_score(avg)
    confidence = min(1.0, abs(avg))
    return {"ticker": t, "window_hours": window_hours, "recommendation": rec, "confidence": confidence, "signals": signals}


def run_news_signals(sentiment_threshold: float = 0.6, window_hours: float = 72.0) -> dict:
    """Analiza documentos recientes por ticker del portfolio y genera señales preventivas.
    Señales: news_sentiment y news_event, con recomendación asociada.
    """
    tickers = _get_portfolio_tickers()
    conn = get_conn()
    cur = conn.cursor()
    # recuperar docs en ventana (filtrado básico por timestamp ISO)
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    cutoff_iso = cutoff_dt.isoformat()
    cur.execute("SELECT id, source, url, title, text, timestamp, tickers FROM docs WHERE timestamp >= ? ORDER BY timestamp DESC", (cutoff_iso,))
    rows = cur.fetchall()
    conn.close()

    created = 0
    for (doc_id, source, url, title, text, ts, doc_tickers_csv) in rows:
        doc_tickers = [t.strip().upper() for t in (doc_tickers_csv or "").split(",") if t.strip()]
        common = [t for t in doc_tickers if t in tickers]
        if not common:
            continue
        # sentimiento
        comp = analyzer.polarity_scores((text or "") + " " + (title or "")).get("compound", 0.0)
        # autoridad
        host = _extract_source(source or url or "")
        auth = AUTHORITY_WEIGHTS.get(host, 0.5)
        # recencia
        decay = _recency_decay(ts)
        # evento por keywords
        event_boost = 0.0
        lower = ((title or "") + " " + (text or "")).lower()
        for k, pol in EVENT_KEYWORDS.items():
            if k in lower:
                event_boost = pol * 0.3
                break

        # score híbrido preventivo: comp * auth * decay + event_boost
        score = comp * auth * decay + event_boost
        direction = "positive" if score > 0 else ("negative" if score < 0 else "neutral")
        # generar señales y alertas si supera umbral
        if abs(score) >= sentiment_threshold:
            for t in common:
                create_signal(t, "news_sentiment", score, direction, doc_url=url, details=host)
                created += 1
                rec = recommendation_from_score(score)
                # alerta preventiva con recomendación embebida en type
                create_alert(t, f"news_preventive_{rec}", score)
    return {"docs_checked": len(rows), "signals_created": created}


def run_price_signals(threshold_pct: float = 3.0) -> dict:
    tickers = _get_portfolio_tickers()
    price_data = fetch_prices(tickers)
    created = 0
    for t, prev, last in price_data:
        if prev <= 0:
            continue
        change_pct = ((last - prev) / prev) * 100.0
        direction = "positive" if change_pct > 0 else ("negative" if change_pct < 0 else "neutral")
        if abs(change_pct) >= abs(threshold_pct):
            create_signal(t, "price_change", change_pct, direction, details=f"prev={prev}, last={last}")
            created += 1
    return {"checked": len(price_data), "signals_created": created}


def run_volume_signals(avg_days: int = 20, multiplier: float = 2.0) -> dict:
    """Genera señal si el volumen del último día >= multiplier * promedio de `avg_days`.
    Usa history diario de 6 meses.
    """
    import yfinance as yf

    tickers = _get_portfolio_tickers()
    created = 0
    for t in tickers:
        try:
            daily = yf.Ticker(t).history(period="6mo", interval="1d")
            if daily is None or daily.empty or len(daily) < avg_days + 1:
                continue
            avg20 = float(daily["Volume"].tail(avg_days + 1).iloc[:-1].mean())
            today_vol = float(daily["Volume"].iloc[-1])
            prev_close = float(daily["Close"].iloc[-2])
            last_close = float(daily["Close"].iloc[-1])
            direction = "positive" if last_close > prev_close else ("negative" if last_close < prev_close else "neutral")
            ratio = today_vol / avg20 if avg20 > 0 else 0.0
            if ratio >= multiplier:
                create_signal(t, "volume_spike", ratio, direction, details=f"avg{avg_days}={avg20}, today={today_vol}")
                created += 1
        except Exception:
            continue
    return {"checked": len(tickers), "signals_created": created}
