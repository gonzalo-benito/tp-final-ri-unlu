import { useEffect, useState } from 'react'
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Stack,
  Grid,
  Card,
  CardContent,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Alert,
  Tooltip
} from '@mui/material'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const getAuthority = (source?: string) => {
  const s = (source || '').toLowerCase()
  if (s.includes('reuters.com') || s.includes('sec.gov')) return 'Alta'
  if (s.includes('marketwatch.com') || s.includes('finance.yahoo.com') || s.includes('cnbc.com')) return 'Media'
  return 'Baja'
}

function App() {
  const [portfolio, setPortfolio] = useState<any[]>([])
  const [ticker, setTicker] = useState('')
  const [qty, setQty] = useState('0')
  const [price, setPrice] = useState('0')
  const [date, setDate] = useState('2025-01-01')
  const [searchQ, setSearchQ] = useState('')
  const [searchRes, setSearchRes] = useState<any[]>([])
  const [ingestStatus, setIngestStatus] = useState<string>('')
  const [signalsStatus, setSignalsStatus] = useState<string>('')
  const [recommendation, setRecommendation] = useState<any | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [signals, setSignals] = useState<any[]>([])
  const [topTicker, setTopTicker] = useState('')
  const [topK, setTopK] = useState('5')
  const [topResults, setTopResults] = useState<any[]>([])

  const loadPortfolio = async () => {
    const res = await fetch(`${API_BASE}/portfolio`)
    const data = await res.json()
    setPortfolio(data)
  }

  const addPortfolio = async () => {
    await fetch(`${API_BASE}/portfolio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker, quantity: parseFloat(qty), entry_price: parseFloat(price), entry_date: date })
    })
    setTicker(''); setQty('0'); setPrice('0')
    await loadPortfolio()
  }

  const doSearch = async () => {
    const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(searchQ)}&limit=10`)
    const data = await res.json()
    setSearchRes(data.results || [])
  }

  const runIngest = async () => {
    setIngestStatus('Ejecutando ingesta...')
    const res = await fetch(`${API_BASE}/ingest/news`, { method: 'POST' })
    const data = await res.json()
    setIngestStatus(`RSS: ${data?.rss?.docs_indexed ?? 0} docs | Yahoo: ${data?.yahoo?.docs_indexed ?? 0} docs`)
  }

  const runSignals = async () => {
    setSignalsStatus('Calculando señales...')
    const res = await fetch(`${API_BASE}/signals/run/news?threshold=0.6&window_hours=72`, { method: 'POST' })
    const data = await res.json()
    setSignalsStatus(`Señales creadas: ${data?.signals_created ?? 0}`)
  }

  const getRecommendation = async () => {
    if (!ticker) return
    const res = await fetch(`${API_BASE}/recommendation/${encodeURIComponent(ticker)}?window_hours=72`)
    const data = await res.json()
    setRecommendation(data)
  }

  const loadAlerts = async () => {
    const res = await fetch(`${API_BASE}/alerts`)
    const data = await res.json()
    setAlerts(data || [])
  }

  const loadSignals = async () => {
    const url = ticker ? `${API_BASE}/signals?ticker=${encodeURIComponent(ticker)}&limit=100` : `${API_BASE}/signals?limit=100`
    const res = await fetch(url)
    const data = await res.json()
    setSignals(data || [])
  }

  const loadTopK = async () => {
    if (!topTicker) return
    const limit = Math.max(1, parseInt(topK || '5', 10))
    const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(topTicker)}&ticker=${encodeURIComponent(topTicker)}&limit=${limit}`)
    const data = await res.json()
    setTopResults(data.results || [])
  }

  useEffect(() => { loadPortfolio() }, [])

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>Agente de Inversiones</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Panel de monitoreo: portfolio, ingesta, señales preventivas y alertas.
      </Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={8}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>Portfolio</Typography>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ my: 1 }}>
                <TextField label="Ticker" value={ticker} onChange={e => setTicker(e.target.value)} />
                <TextField label="Cantidad" value={qty} onChange={e => setQty(e.target.value)} />
                <TextField label="Precio de compra" value={price} onChange={e => setPrice(e.target.value)} />
                <TextField label="Fecha de compra" value={date} onChange={e => setDate(e.target.value)} />
                <Button variant="contained" onClick={addPortfolio}>Agregar</Button>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Ejemplo: TSLA — 10 @ 300 (2025-01-01) = 10 acciones compradas a 300 el 01/01/2025.
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ticker</TableCell>
                    <TableCell align="right">Cantidad</TableCell>
                    <TableCell align="right">Precio compra</TableCell>
                    <TableCell>Fecha compra</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {portfolio.map(p => (
                    <TableRow key={p.id}>
                      <TableCell>{p.ticker}</TableCell>
                      <TableCell align="right">{p.quantity}</TableCell>
                      <TableCell align="right">{p.entry_price}</TableCell>
                      <TableCell>{p.entry_date}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>Acciones rápidas</Typography>
              <Stack spacing={1}>
                <Button variant="outlined" onClick={runIngest}>Ingestar noticias</Button>
                <Button variant="outlined" onClick={runSignals}>Generar señales</Button>
                <Button variant="outlined" onClick={getRecommendation}>Recomendación (ticker)</Button>
              </Stack>
              <Divider sx={{ my: 2 }} />
              {ingestStatus && <Alert severity="info">{ingestStatus}</Alert>}
              {signalsStatus && <Alert severity="success" sx={{ mt: 1 }}>{signalsStatus}</Alert>}
              {recommendation && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  Recomendación: {recommendation.recommendation} — Confianza: {recommendation.confidence}
                </Alert>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                RSS/Yahoo indica cuántos documentos se indexaron en la última ingesta.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Búsqueda de noticias</Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ my: 1 }}>
            <TextField fullWidth label="Consulta" value={searchQ} onChange={e => setSearchQ(e.target.value)} />
            <Button variant="outlined" onClick={doSearch}>Buscar</Button>
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Título</TableCell>
                <TableCell>Fuente</TableCell>
                <TableCell>Autoridad</TableCell>
                <TableCell>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
                {searchRes.map((d: any) => (
                <TableRow key={d.id}>
                    <TableCell>
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noreferrer">{d.title}</a>
                      ) : (
                        d.title
                      )}
                    </TableCell>
                  <TableCell>{d.source}</TableCell>
                  <TableCell>{getAuthority(d.source)}</TableCell>
                  <TableCell>{d.timestamp}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Top‑K noticias por ticker</Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ my: 1 }}>
            <TextField label="Ticker" value={topTicker} onChange={e => setTopTicker(e.target.value)} />
            <TextField label="Top‑K" value={topK} onChange={e => setTopK(e.target.value)} />
            <Button variant="outlined" onClick={loadTopK}>Ver top‑K</Button>
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Rank</TableCell>
                <TableCell>Título</TableCell>
                <TableCell>Fuente</TableCell>
                <TableCell>Autoridad</TableCell>
                <TableCell align="right">Score</TableCell>
                <TableCell>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {topResults
                .slice()
                .sort((a: any, b: any) => (b.score ?? 0) - (a.score ?? 0))
                .map((d: any, idx: number) => (
                <TableRow key={d.id}>
                  <TableCell>{idx + 1}</TableCell>
                    <TableCell>
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noreferrer">{d.title}</a>
                      ) : (
                        d.title
                      )}
                    </TableCell>
                  <TableCell>{d.source}</TableCell>
                  <TableCell>{getAuthority(d.source)}</TableCell>
                  <TableCell align="right">
                    {d.score_details ? (
                      <Tooltip title={JSON.stringify(d.score_details)}>
                        <span>{typeof d.score === 'number' ? d.score.toFixed(3) : d.score}</span>
                      </Tooltip>
                    ) : (
                      typeof d.score === 'number' ? d.score.toFixed(3) : d.score
                    )}
                  </TableCell>
                  <TableCell>{d.timestamp}</TableCell>
                </TableRow>
                ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="h6">Alertas</Typography>
                <Button variant="outlined" onClick={loadAlerts}>Refrescar</Button>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                news_preventive_buy = alerta preventiva basada en noticias con señal positiva.
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ticker</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell>Fecha</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {alerts.map((a: any) => (
                    <TableRow key={a.id}>
                      <TableCell>{a.ticker}</TableCell>
                      <TableCell>
                        <Chip size="small" label={a.type} />
                      </TableCell>
                      <TableCell align="right">{Number(a.score).toFixed(3)}</TableCell>
                      <TableCell>{a.created_at}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="h6">Señales</Typography>
                <Button variant="outlined" onClick={loadSignals}>Refrescar</Button>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                news_sentiment = score preventivo por sentimiento/autoridad/recencia.
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ticker</TableCell>
                    <TableCell>Tipo</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell>Fecha</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {signals.map((s: any) => (
                    <TableRow key={s.id}>
                      <TableCell>{s.ticker}</TableCell>
                      <TableCell>
                        <Chip size="small" label={s.type} />
                      </TableCell>
                      <TableCell align="right">{Number(s.score).toFixed(3)}</TableCell>
                      <TableCell>{s.created_at}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  )
}

export default App
