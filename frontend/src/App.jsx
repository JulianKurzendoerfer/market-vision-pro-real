import React, { useMemo, useState } from "react"

import { API_URL } from "./config.js"

const API = API_URL.replace(/\/$/, "")

export default function App() {
  const [symbol, setSymbol] = useState("AAPL.US")
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState("")
  const [quote, setQuote] = useState(null)
  const [ind, setInd] = useState(null)

  const canCall = useMemo(() => API.length > 0, [])

  async function run() {
    setErr("")
    setLoading(true)
    try {
      const q = await fetch(`${API}/api/quote?symbol=${encodeURIComponent(symbol)}`)
      if (!q.ok) throw new Error(await q.text())
      setQuote(await q.json())

      const i = await fetch(`${API}/api/indicators?symbol=${encodeURIComponent(symbol)}&days=320&period=d`)
      if (!i.ok) throw new Error(await i.text())
      setInd(await i.json())
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ fontFamily: "system-ui", padding: 18, maxWidth: 980, margin: "0 auto" }}>
      <h2 style={{ margin: 0 }}>Market Vision Pro</h2>
      <div style={{ opacity: 0.8, marginTop: 6 }}>
        API: {canCall ? API : "VITE_API_URL fehlt (Render EnvVar)"}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="z.B. AAPL.US"
          style={{ flex: 1, padding: 10, fontSize: 16 }}
        />
        <button onClick={run} disabled={!canCall || loading} style={{ padding: "10px 14px", fontSize: 16 }}>
          {loading ? "Lade..." : "Analyse"}
        </button>
      </div>

      {err ? (
        <div style={{ marginTop: 14, padding: 12, background: "#ffe9e9" }}>
          {err}
        </div>
      ) : null}

      {quote ? (
        <div style={{ marginTop: 14, padding: 12, background: "#f4f6ff" }}>
          <div style={{ fontWeight: 700 }}>{quote.code || quote.ticker || symbol}</div>
          <div>Preis: {quote.close ?? quote.price ?? quote.last ?? quote.previousClose ?? "-"}</div>
          <div>Währung: {quote.currency ?? "-"}</div>
        </div>
      ) : null}

      {ind?.last ? (
        <div style={{ marginTop: 14, padding: 12, background: "#f6fff4" }}>
          <div style={{ fontWeight: 700 }}>Letzte Indikatoren</div>
          <div>Datum: {ind.last.date}</div>
          <div>RSI(14): {Number(ind.last.rsi14).toFixed(2)}</div>
          <div>MACD: {Number(ind.last.macd).toFixed(4)} | Signal: {Number(ind.last.macd_signal).toFixed(4)}</div>
          <div>Bollinger: U {Number(ind.last.bb_upper).toFixed(2)} | M {Number(ind.last.bb_middle).toFixed(2)} | L {Number(ind.last.bb_lower).toFixed(2)}</div>
        </div>
      ) : null}
    </div>
  )
}
