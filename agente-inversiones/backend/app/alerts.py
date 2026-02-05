"""Generación y persistencia de alertas simples basadas en precios."""
from typing import List
from datetime import datetime

from .db import get_conn
from .ingestion import _get_portfolio_tickers, fetch_prices


def create_alert(ticker: str, alert_type: str, score: float):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO alerts (ticker, type, score, created_at) VALUES (?,?,?,?)",
        (ticker.upper(), alert_type, float(score), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def run_price_drop_alerts(threshold_pct: float = 3.0) -> dict:
    """Crea alertas si la caída porcentual entre últimos cierres >= threshold."""
    tickers = _get_portfolio_tickers()
    price_data = fetch_prices(tickers)
    created = 0
    for t, prev, last in price_data:
        if prev <= 0:
            continue
        change_pct = ((last - prev) / prev) * 100.0
        if change_pct <= -abs(threshold_pct):
            create_alert(t, "price_drop", change_pct)
            created += 1
    return {"checked": len(price_data), "alerts_created": created}
