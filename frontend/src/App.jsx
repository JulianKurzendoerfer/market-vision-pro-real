import React, { useEffect, useMemo, useRef, useState } from "react"
import { createChart } from "lightweight-charts"

const API = "https://market-vision-pro-real.onrender.com"

function lineData(overlays, key) {
  return overlays
    .filter(x => x[key] !== null && x[key] !== undefined)
    .map(x => ({ time: x.time, value: Number(x[key]) }))
}

function histData(overlays, key) {
  return overlays
    .filter(x => x[key] !== null && x[key] !== undefined)
    .map(x => ({ time: x.time, value: Number(x[key]) }))
}

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

  const heights = useMemo(() => ({
    main: 420,
    rsi: 140,
    stoch: 170,
    macd: 170
  }), [])

  function destroy() {
    Object.values(charts.current).forEach(c => {
      try { c.remove() } catch {}
    })
    charts.current = {}
  }

  function syncTime(chs) {
    const keys = Object.keys(chs)
    keys.forEach(k => {
      chs[k].timeScale().subscribeVisibleTimeRangeChange(range => {
        keys.forEach(k2 => {
          if (k2 !== k) chs[k2].timeScale().setVisibleRange(range)
        })
      })
    })
  }

  async function run() {
    setErr("")
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/tv?symbol=${encodeURIComponent(symbol)}&days=520&period=d`)
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()
      setLast(data.last || null)

      destroy()

      const w = wrapRef.current?.clientWidth || 1000

      const mainChart = createChart(mainRef.current, { width: w, height: heights.main, layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" }, grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } }, rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" }, timeScale: { borderColor: "rgba(255,255,255,0.15)" } })
      const rsiChart  = createChart(rsiRef.current,  { width: w, height: heights.rsi,  layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" }, grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } }, rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" }, timeScale: { borderColor: "rgba(255,255,255,0.15)" } })
      const stochChart= createChart(stochRef.current,{ width: w, height: heights.stoch,layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" }, grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } }, rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" }, timeScale: { borderColor: "rgba(255,255,255,0.15)" } })
      const macdChart = createChart(macdRef.current, { width: w, height: heights.macd, layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" }, grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } }, rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" }, timeScale: { borderColor: "rgba(255,255,255,0.15)" } })

      charts.current = { mainChart, rsiChart, stochChart, macdChart }
      syncTime(charts.current)

      const candles = mainChart.addCandlestickSeries()
      candles.setData(data.candles)

      const bbU = mainChart.addLineSeries({ lineWidth: 1 })
      const bbM = mainChart.addLineSeries({ lineWidth: 1 })
      const bbL = mainChart.addLineSeries({ lineWidth: 1 })
      bbU.setData(lineData(data.overlays, "bb_upper"))
      bbM.setData(lineData(data.overlays, "bb_middle"))
      bbL.setData(lineData(data.overlays, "bb_lower"))

      const e20 = mainChart.addLineSeries({ lineWidth: 1 })
      const e50 = mainChart.addLineSeries({ lineWidth: 1 })
      const e100 = mainChart.addLineSeries({ lineWidth: 1 })
      const e200 = mainChart.addLineSeries({ lineWidth: 1 })
      e20.setData(lineData(data.overlays, "ema20"))
      e50.setData(lineData(data.overlays, "ema50"))
      e100.setData(lineData(data.overlays, "ema100"))
      e200.setData(lineData(data.overlays, "ema200"))

      const rsi = rsiChart.addLineSeries({ lineWidth: 2 })
      rsi.setData(lineData(data.overlays, "rsi14"))
      rsiChart.addLineSeries({ lineWidth: 1 }).setData([{ time: data.overlays[0].time, value: 70 }, { time: data.overlays[data.overlays.length-1].time, value: 70 }])
      rsiChart.addLineSeries({ lineWidth: 1 }).setData([{ time: data.overlays[0].time, value: 30 }, { time: data.overlays[data.overlays.length-1].time, value: 30 }])

      const k = stochChart.addLineSeries({ lineWidth: 2 })
      const dline = stochChart.addLineSeries({ lineWidth: 2 })
      k.setData(lineData(data.overlays, "stoch_k"))
      dline.setData(lineData(data.overlays, "stoch_d"))
      stochChart.addLineSeries({ lineWidth: 1 }).setData([{ time: data.overlays[0].time, value: 80 }, { time: data.overlays[data.overlays.length-1].time, value: 80 }])
      stochChart.addLineSeries({ lineWidth: 1 }).setData([{ time: data.overlays[0].time, value: 20 }, { time: data.overlays[data.overlays.length-1].time, value: 20 }])

      const hist = macdChart.addHistogramSeries()
      const macd = macdChart.addLineSeries({ lineWidth: 2 })
      const sig = macdChart.addLineSeries({ lineWidth: 2 })
      hist.setData(histData(data.overlays, "macd_hist"))
      macd.setData(lineData(data.overlays, "macd"))
      sig.setData(lineData(data.overlays, "macd_signal"))

      mainChart.timeScale().fitContent()
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    return () => destroy()
  }, [])

  useEffect(() => {
    const onResize = () => {
      if (!wrapRef.current) return
      const w = wrapRef.current.clientWidth
      Object.values(charts.current).forEach(c => {
        try { c.applyOptions({ width: w }) } catch {}
      })
    }
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [])

  return (
    <div style={{ fontFamily: "system-ui", padding: 16, maxWidth: 1200, margin: "0 auto" }} ref={wrapRef}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <div style={{ fontSize: 22, fontWeight: 700 }}>Market Vision Pro</div>
        <div style={{ opacity: 0.7 }}>API: {API}</div>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
        <input value={symbol} onChange={e => setSymbol(e.target.value)} style={{ flex: 1, padding: 10, fontSize: 16 }} />
        <button onClick={run} disabled={loading} style={{ padding: "10px 14px", fontSize: 16 }}>
          {loading ? "Lade..." : "Analyse"}
        </button>
      </div>

      {err ? <div style={{ color: "#ff6b6b", marginBottom: 12 }}>{err}</div> : null}

      {last ? (
        <div style={{ color: "#d6d6d6", marginBottom: 10 }}>
          <div>Preis: {last?.bb_middle ?? "-"}</div>
          <div>RSI: {last?.rsi14 != null ? Number(last.rsi14).toFixed(2) : "-"}</div>
          <div>Stoch K/D: {last?.stoch_k != null ? Number(last.stoch_k).toFixed(2) : "-"} / {last?.stoch_d != null ? Number(last.stoch_d).toFixed(2) : "-"}</div>
          <div>MACD: {last?.macd != null ? Number(last.macd).toFixed(4) : "-"} | Signal: {last?.macd_signal != null ? Number(last.macd_signal).toFixed(4) : "-"}</div>
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
