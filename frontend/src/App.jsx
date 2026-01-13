import React, { useState } from "react"

const API = "https://market-vision-pro-real.onrender.com"

export default function App() {
  const [symbol, setSymbol] = useState("AAPL.US")
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState("")
  const [quote, setQuote] = useState(null)
  const [ind, setInd] = useState(null)

  async function run() {
    setErr("")
    setLoading(true)
    try {
      const q = await fetch(`${API}/api/quote?symbol=${encodeURIComponent(symbol)}`)
      if (!q.ok) throw new Error(await q.text())
      setQuote(await q.json())

      const i = await fetch(`${API}/api/indicators?symbol=${encodeURIComponent(symbol)}`)
      if (!i.ok) throw new Error(await i.text())
      setInd(await i.json())
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ fontFamily: "system-ui", padding: 20, maxWidth: 900, margin: "0 auto" }}>
      <h2>Market Vision Pro</h2>
      <div style={{ opacity: 0.7 }}>API: {API}</div>

      <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          style={{ flex: 1, padding: 10 }}
        />
        <button onClick={run} disabled={loading}>
          {loading ? "Lade…" : "Analyse"}
        </button>
      </div>

      {err && <div style={{ color: "red", marginTop: 12 }}>{err}</div>}

      {quote && (
        <div style={{ marginTop: 12 }}>
          <strong>Preis:</strong> {quote.close ?? quote.price}
        </div>
      )}

      {ind?.last && (
        <div style={{ marginTop: 12 }}>
          <div>RSI: {Number(ind.last.rsi14).toFixed(2)}</div>
          <div>MACD: {Number(ind.last.macd).toFixed(4)}</div>
        </div>
      )}
    </div>
  )
}
