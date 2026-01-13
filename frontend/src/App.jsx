import React, { useEffect, useMemo, useRef, useState } from "react"
import { createChart } from "lightweight-charts"

const API = "https://market-vision-pro-real.onrender.com"

const isNum = (v) => Number.isFinite(Number(v))

const lineData = (overlays, key) =>
  overlays
    .filter(x => isNum(x[key]))
    .map(x => ({ time: x.time, value: Number(x[key]) }))

const histData = (overlays, key) =>
  overlays
    .filter(x => isNum(x[key]))
    .map(x => {
      const value = Number(x[key])
      return { time: x.time, value }
    })

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

  const baseOpts = (w, h, showTime) => ({
    width: w,
    height: h,
    layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" },
    grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } },
    rightPriceScale: { borderColor: "rgba(255,255,255,0.15)" },
    timeScale: { borderColor: "rgba(255,255,255,0.15)", visible: showTime },
    watermark: { visible: false }
  })

  function destroy() {
    Object.values(charts.current).forEach(c => { try { c.remove() } catch {} })
    charts.current = {}
  }

  function syncTime(chs) {
    const keys = Object.keys(chs)
    const lock = { v: false }
    keys.forEach(k => {
      chs[k].timeScale().subscribeVisibleTimeRangeChange(range => {
        if (lock.v || !range) return
        lock.v = true
        keys.forEach(k2 => { if (k2 !== k) chs[k2].timeScale().setVisibleRange(range) })
        lock.v = false
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

      const mainChart = createChart(mainRef.current, baseOpts(w, heights.main, false))
      const rsiChart  = createChart(rsiRef.current,  baseOpts(w, heights.rsi, false))
      const stochChart= createChart(stochRef.current,baseOpts(w, heights.stoch, false))
      const macdChart = createChart(macdRef.current, baseOpts(w, heights.macd, true))

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
      const t0 = data.overlays[0].time
      const t1 = data.overlays[data.overlays.length - 1].time
      rsiChart.addLineSeries({ lineWidth: 1 }).setData([{ time: t0, value: 70 }, { time: t1, value: 70 }])
      rsiChart.addLineSeries({ lineWidth: 1 }).setData([{ time: t0, value: 30 }, { time: t1, value: 30 }])

      const k = stochChart.addLineSeries({ lineWidth: 2 })
      const dline = stochChart.addLineSeries({ lineWidth: 2 })
      k.setData(lineData(data.overlays, "stoch_k"))
      dline.setData(lineData(data.overlays, "stoch_d"))
      stochChart.addLineSeries({ lineWidth: 1 }).setData([{ time: t0, value: 80 }, { time: t1, value: 80 }])
      stochChart.addLineSeries({ lineWidth: 1 }).setData([{ time: t0, value: 20 }, { time: t1, value: 20 }])

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

  useEffect(() => () => destroy(), [])

  useEffect(() => {
    const onResize = () => {
      const w = wrapRef.current?.clientWidth
      if (!w) return
      Object.values(charts.current).forEach(c => { try { c.applyOptions({ width: w }) } catch {} })
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
