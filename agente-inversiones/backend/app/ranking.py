"""Funciones de ranking híbrido para documentos de noticias.
Combina sentimiento (VADER), autoridad de fuente, recencia y eventos.
"""
from datetime import datetime, timezone
import math
import re
from typing import Tuple

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Reusar el mismo diccionario de autoridad/eventos definido en signals
AUTHORITY_WEIGHTS = {
    "reuters.com": 1.0,
    "sec.gov": 1.0,
    "marketwatch.com": 0.8,
    "finance.yahoo.com": 0.7,
    "cnbc.com": 0.8,
}

EVENT_KEYWORDS = {
    "downgrade": -1.0,
    "lawsuit": -1.0,
    "guidance cut": -0.8,
    "miss earnings": -1.0,
    "layoff": -0.6,
    "recall": -0.6,
    "investigation": -0.7,
    "negative outlook": -0.8,
    "upgrade": 1.0,
    "beat earnings": 1.0,
    "buyback": 0.8,
    "dividend increase": 0.8,
    "guidance raise": 0.9,
    "approval": 0.9,
    "partnership": 0.6,
}

_analyzer = SentimentIntensityAnalyzer()


def _extract_host(source_or_url: str) -> str:
    try:
        host = re.sub(r"^https?://", "", source_or_url or "").split("/")[0]
        # strip www.
        host = re.sub(r"^www\.", "", host)
        return host
    except Exception:
        return ""


def _iso_to_datetime(s: str) -> datetime:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def recency_decay(ts_iso: str, half_life_hours: float = 48.0) -> float:
    now = datetime.now(timezone.utc)
    ts = _iso_to_datetime(ts_iso)
    age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
    lam = math.log(2) / half_life_hours
    return math.exp(-lam * age_hours)


def sentiment_score(title: str, text: str) -> float:
    comp = _analyzer.polarity_scores(f"{title or ''} {text or ''}").get("compound", 0.0)
    return comp


def event_boost(title: str, text: str) -> float:
    lower = f"{title or ''} {text or ''}".lower()
    for k, pol in EVENT_KEYWORDS.items():
        if k in lower:
            return pol * 0.3
    return 0.0


def authority_weight(source: str, url: str) -> float:
    host = _extract_host(source or url or "")
    # fallback para subdominios: usar dominio base
    parts = host.split(".")
    base = host
    if len(parts) > 2:
        base = ".".join(parts[-2:])
    return AUTHORITY_WEIGHTS.get(base, 0.5)


def hybrid_score(
    title: str,
    text: str,
    source: str,
    url: str,
    timestamp: str,
    bm25_pos_weight: float = 1.0,
    w_sent: float = 0.5,
    w_recency: float = 0.3,
    w_auth: float = 0.2,
) -> Tuple[float, dict]:
    sent = sentiment_score(title, text)
    rec = recency_decay(timestamp)
    auth = authority_weight(source, url)
    evt = event_boost(title, text)
    score = bm25_pos_weight + w_sent * sent + w_recency * rec + w_auth * auth + evt
    details = {
        "sentiment": sent,
        "recency": rec,
        "authority": auth,
        "event_boost": evt,
        "bm25_pos_weight": bm25_pos_weight,
    }
    return score, details
