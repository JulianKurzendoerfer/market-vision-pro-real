import React, { useEffect, useMemo, useRef, useState } from "react"
import { createChart } from "lightweight-charts"

const API = "https://market-vision-pro-real.onrender.com"

const isNum = (v) => Number.isFinite(Number(v))
const isTime = (t) => typeof t === "string" && t.length >= 8

const cleanCandles = (candles) =>
  (candles || [])
    .filter(b => isTime(b.time) && isNum(b.open) && isNum(b.high) && isNum(b.low) && isNum(b.close))
    .map(b => ({ time: b.time, open: +b.open, high: +b.high, low: +b.low, close: +b.close }))

const lineData = (overlays, key) =>
  (overlays || [])
    .filter(x => isTime(x.time) && isNum(x[key]))
    .map(x => ({ time: x.time, value: Number(x[key]) }))

const histData = (overlays, key) =>
  (overlays || [])
    .filter(x => isTime(x.time) && isNum(x[key]))
    .map(x => ({ time: x.time, value: Number(x[key]) }))

export default function App() {
  const [symbol, setSymbol] = useState("AAPL.US")
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState("")
  const [last, setLast] = useState(null)

  const wrapRef = useRef(null)
  const mainRef = useRef(null)
  const rsiRef = useRef(null)
  const stochRef = useRef(null)
  const macdRef = useRef(null)
  const charts = useRef({})

  const heights = useMemo(() => ({ main: 420, rsi: 140, stoch: 170, macd: 170 }), [])

  const baseOpts = (w, h, timeVisible) => ({
    width: w,
    height: h,
    layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" },
    grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } },
    rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" },
    timeScale: { borderColor: "rgba(255,255,255,0.15)", visible: timeVisible, rightOffset: 5, barSpacing: 8, lockVisibleTimeRangeOnResize: true },
    watermark: { visible: false },
    attributionLogo: false,
    crosshair: { mode: 1 }
  })

  const noPriceLine = { priceLineVisible: false, lastValueVisible: false }

  function destroy() {
    Object.values(charts.current).forEach(c => { try { c.remove() } catch {} })
    charts.current = {}
  }

  function safeSet(series, data) {
    try { series.setData(data) } catch {}
  }

  function syncTimeScales(all) {
    const keys = Object.keys(all)
    const lock = { v: false }
    keys.forEach(k => {
      const ts = all[k].timeScale()
      ts.subscribeVisibleLogicalRangeChange((range) => {
        if (lock.v || !range) return
        lock.v = true
        keys.forEach(k2 => {
          if (k2 === k) return
          try { all[k2].timeScale().setVisibleLogicalRange(range) } catch {}
        })
        lock.v = false
      })
    })
  }

  function applySameRangeFromMain(all) {
    const main = all.mainChart
    if (!main) return
    const r = main.timeScale().getVisibleLogicalRange()
    if (!r) return
    Object.entries(all).forEach(([name, c]) => {
      if (name === "mainChart") return
      try { c.timeScale().setVisibleLogicalRange(r) } catch {}
    })
  }

  async function run() {
    setErr("")
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/tv?symbol=${encodeURIComponent(symbol)}&days=520&period=d`)
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()

      const candles = cleanCandles(data.candles)
      const overlays = (data.overlays || []).filter(x => isTime(x.time))

      if (candles.length < 60) throw new Error("Zu wenig gültige Candle-Daten.")

      setLast(data.last || null)
      destroy()

      const w = wrapRef.current?.clientWidth || 1000

      const mainChart  = createChart(mainRef.current,  baseOpts(w, heights.main, true))
      const rsiChart   = createChart(rsiRef.current,   baseOpts(w, heights.rsi, false))
      const stochChart = createChart(stochRef.current, baseOpts(w, heights.stoch, false))
      const macdChart  = createChart(macdRef.current,  baseOpts(w, heights.macd, false))

      charts.current = { mainChart, rsiChart, stochChart, macdChart }

      const cs = mainChart.addCandlestickSeries({ ...noPriceLine })
      cs.setData(candles)

      const bbU = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      const bbM = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      const bbL = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      safeSet(bbU, lineData(overlays, "bb_upper"))
      safeSet(bbM, lineData(overlays, "bb_middle"))
      safeSet(bbL, lineData(overlays, "bb_lower"))

      const e20  = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      const e50  = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      const e100 = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      const e200 = mainChart.addLineSeries({ lineWidth: 1, ...noPriceLine })
      safeSet(e20,  lineData(overlays, "ema20"))
      safeSet(e50,  lineData(overlays, "ema50"))
      safeSet(e100, lineData(overlays, "ema100"))
      safeSet(e200, lineData(overlays, "ema200"))

      const rsi = rsiChart.addLineSeries({ lineWidth: 2, ...noPriceLine })
      safeSet(rsi, lineData(overlays, "rsi14"))

      const k = stochChart.addLineSeries({ lineWidth: 2, ...noPriceLine })
      const dline = stochChart.addLineSeries({ lineWidth: 2, ...noPriceLine })
      safeSet(k, lineData(overlays, "stoch_k"))
      safeSet(dline, lineData(overlays, "stoch_d"))

      const hist = macdChart.addHistogramSeries({ ...noPriceLine })
      const macd = macdChart.addLineSeries({ lineWidth: 2, ...noPriceLine })
      const sig  = macdChart.addLineSeries({ lineWidth: 2, ...noPriceLine })
      safeSet(hist, histData(overlays, "macd_hist"))
      safeSet(macd, lineData(overlays, "macd"))
      safeSet(sig,  lineData(overlays, "macd_signal"))

      mainChart.timeScale().fitContent()
      applySameRangeFromMain(charts.current)
      syncTimeScales(charts.current)
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => () => destroy(), [])

  useEffect(() => {
    const onResize = () => {
      const w = wrapRef.current?.clientWidth
      if (!w) return
      Object.values(charts.current).forEach(c => { try { c.applyOptions({ width: w }) } catch {} })
      applySameRangeFromMain(charts.current)
    }
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [])

  return (
    <div style={{ fontFamily: "system-ui", padding: 16, maxWidth: 1200, margin: "0 auto" }} ref={wrapRef}>
      <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 6 }}>Market Vision Pro</div>

      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        <input value={symbol} onChange={e => setSymbol(e.target.value)} style={{ flex: 1, padding: 10, fontSize: 16 }} />
        <button onClick={run} disabled={loading} style={{ padding: "10px 14px", fontSize: 16 }}>
          {loading ? "Lade..." : "Analyse"}
        </button>
      </div>

      {err ? <div style={{ color: "#ff6b6b", marginBottom: 10 }}>{err}</div> : null}

      {last ? (
        <div style={{ color: "#d6d6d6", marginBottom: 10 }}>
          <div>Preis: {isNum(last.close) ? Number(last.close).toFixed(2) : "-"}</div>
          <div>RSI: {isNum(last.rsi14) ? Number(last.rsi14).toFixed(2) : "-"}</div>
          <div>Stoch K/D: {isNum(last.stoch_k) ? Number(last.stoch_k).toFixed(2) : "-"} / {isNum(last.stoch_d) ? Number(last.stoch_d).toFixed(2) : "-"}</div>
          <div>MACD: {isNum(last.macd) ? Number(last.macd).toFixed(4) : "-"} | Signal: {isNum(last.macd_signal) ? Number(last.macd_signal).toFixed(4) : "-"}</div>
        </div>
      ) : null}

      <div style={{ borderRadius: 10, overflow: "hidden" }}>
        <div ref={mainRef} />
        <div ref={rsiRef} />
        <div ref={stochRef} />
        <div ref={macdRef} />
      </div>
    </div>
  )
}
