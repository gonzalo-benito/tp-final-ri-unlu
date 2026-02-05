from pydantic import BaseModel, Field
from typing import List

class PortfolioItem(BaseModel):
    ticker: str = Field(..., min_length=1)
    quantity: float
    entry_price: float
    entry_date: str  # ISO date string

class Digest(BaseModel):
    ticker: str
    date: str
    content: str

class DocItem(BaseModel):
    source: str
    url: str
    title: str
    text: str
    timestamp: str
    tickers: List[str] = []
