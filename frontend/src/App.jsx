import React, { useEffect, useMemo, useRef, useState } from "react"
import { createChart } from "lightweight-charts"

const API = "https://market-vision-pro-real.onrender.com"

const isNum = (v) => Number.isFinite(Number(v))
const isTime = (t) => typeof t === "string" && t.length >= 8

const cleanCandles = (candles) =>
  (candles || [])
    .filter(b => isTime(b.time) && isNum(b.open) && isNum(b.high) && isNum(b.low) && isNum(b.close) && Number(b.high) > 0 && Number(b.low) > 0 && Number(b.close) > 0 && Number(b.high) >= Number(b.low))
    .map(b => ({ time: b.time, open: +b.open, high: +b.high, low: +b.low, close: +b.close }))

const lineData = (overlays, key) =>
  (overlays || [])
    .filter(x => isTime(x.time) && isNum(x[key]))
    .map(x => ({ time: x.time, value: Number(x[key]) }))

const histData = (overlays, key) =>
  (overlays || [])
    .filter(x => isTime(x.time) && isNum(x[key]))
    .map(x => ({ time: x.time, value: Number(x[key]) }))

const removeTVAttribution = (el) => {
  if (!el) return
  const kill = (node) => { try { node.remove() } catch {} }
  el.querySelectorAll("a,img,svg,div,span").forEach(n => {
    const href = (n.getAttribute?.("href") || n.href || "").toString().toLowerCase()
    const title = (n.getAttribute?.("title") || "").toString().toLowerCase()
    const aria = (n.getAttribute?.("aria-label") || "").toString().toLowerCase()
    const cls = (n.getAttribute?.("class") || "").toString().toLowerCase()
    const txt = (n.textContent || "").toString().toLowerCase()
    if (href.includes("tradingview") || title.includes("tradingview") || aria.includes("tradingview") || cls.includes("attribution") || txt === "tv") {
      kill(n)
    }
  })
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

  const heights = useMemo(() => ({ main: 420, rsi: 140, stoch: 170, macd: 170 }), [])

  const baseOpts = (w, h, timeVisible) => ({
    width: w,
    height: h,
    layout: { background: { type: "solid", color: "#0b0f19" }, textColor: "#d6d6d6" },
    grid: { vertLines: { color: "rgba(255,255,255,0.06)" }, horzLines: { color: "rgba(255,255,255,0.06)" } },
    rightPriceScale: {  borderColor: "rgba(255,255,255,0.10)", minimumWidth: 90, scaleMargins: { top: 0.10, bottom: 0.10 , mode: 1 }, textColor: "rgba(255,255,255,0.72)" },
    timeScale: { borderColor: "rgba(255,255,255,0.15)", visible: timeVisible, rightOffset: 6, barSpacing: 6, lockVisibleTimeRangeOnResize: true },
    watermark: { visible: true, text: "MVP", fontSize: 18, color: "rgba(255,255,255,0.08)" },
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
      const r = await fetch(`${API}/api/tv?symbol=${encodeURIComponent(symbol)}&period=d&full=1`)
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()

      const candles = cleanCandles(data.candles)
      const overlays = (data.overlays || []).filter(x => isTime(x.time))
      if (candles.length < 60) throw new Error("Zu wenig gültige Candle-Daten.")

      setLast(data.last || null)
      destroy()

      const wrapW = wrapRef.current?.clientWidth || 1200
      const w = Math.max(720, wrapW - 24)

      const mainChart  = createChart(mainRef.current,  baseOpts(w, heights.main, true))
      const rsiChart   = createChart(rsiRef.current,   baseOpts(w, heights.rsi, false))
      const stochChart = createChart(stochRef.current, baseOpts(w, heights.stoch, false))
      const macdChart  = createChart(macdRef.current,  baseOpts(w, heights.macd, false))

      charts.current = { mainChart, rsiChart, stochChart, macdChart }

      const cs = mainChart.addCandlestickSeries({ priceLineVisible: false, lastValueVisible: false })
      cs.setData(candles)

      const bbColor = "#22d3ee"
      const bbMidColor = "#67e8f9"
      const bbU = mainChart.addLineSeries({ lineWidth: 2, color: bbColor, ...noPriceLine })
      const bbM = mainChart.addLineSeries({ lineWidth: 1, color: bbMidColor, ...noPriceLine })
      const bbL = mainChart.addLineSeries({ lineWidth: 2, color: bbColor, ...noPriceLine })
      safeSet(bbU, lineData(overlays, "bb_upper"))
      safeSet(bbM, lineData(overlays, "bb_middle"))
      safeSet(bbL, lineData(overlays, "bb_lower"))

      const e20  = mainChart.addLineSeries({ lineWidth: 2, color: "#fbbf24", ...noPriceLine })
      const e50  = mainChart.addLineSeries({ lineWidth: 2, color: "#fb7185", ...noPriceLine })
      const e100 = mainChart.addLineSeries({ lineWidth: 2, color: "#a78bfa", ...noPriceLine })
      const e200 = mainChart.addLineSeries({ lineWidth: 2, color: "#60a5fa", ...noPriceLine })
      safeSet(e20,  lineData(overlays, "ema20"))
      safeSet(e50,  lineData(overlays, "ema50"))
      safeSet(e100, lineData(overlays, "ema100"))
      safeSet(e200, lineData(overlays, "ema200"))

      const levels = Array.isArray(data.levels) ? data.levels : []
      const SR_COLOR = "rgba(255,255,255,0.24)"
      const fmt = (v) => Number(v).toFixed(2)
      for (const lvl of levels) {
        if (!lvl || !isNum(lvl.value)) continue
        const strength = Math.max(1, Number(lvl.strength || 1))
        const width = strength >= 6 ? 4 : strength >= 4 ? 3 : 2
        cs.createPriceLine({
          price: Number(lvl.value),
          color: SR_COLOR,
          lineWidth: width,
          lineStyle: 0,
          axisLabelVisible: true,
          title: ""
        })
      }

      const lastClose = candles[candles.length - 1].close
      cs.createPriceLine({
        price: Number(lastClose),
        color: "rgba(52,199,89,0.95)",
        lineWidth: 0,
        lineStyle: 0,
        axisLabelVisible: true,
        title: ""
      })

      const t0 = candles[0].time
      const t1 = candles[candles.length - 1].time

      const rsi = rsiChart.addLineSeries({ lineWidth: 2, color: "#c084fc", ...noPriceLine })
      safeSet(rsi, lineData(overlays, "rsi14"))
      rsiChart.addLineSeries({ lineWidth: 1, color: "#ff3b30", ...noPriceLine }).setData([{ time: t0, value: 70 }, { time: t1, value: 70 }])
      rsiChart.addLineSeries({ lineWidth: 1, color: "#34c759", ...noPriceLine }).setData([{ time: t0, value: 30 }, { time: t1, value: 30 }])

      const k = stochChart.addLineSeries({ lineWidth: 2, color: "#38bdf8", ...noPriceLine })
      const dline = stochChart.addLineSeries({ lineWidth: 2, color: "#22c55e", ...noPriceLine })
      safeSet(k, lineData(overlays, "stoch_k"))
      safeSet(dline, lineData(overlays, "stoch_d"))
      stochChart.addLineSeries({ lineWidth: 1, color: "#ff3b30", ...noPriceLine }).setData([{ time: t0, value: 80 }, { time: t1, value: 80 }])
      stochChart.addLineSeries({ lineWidth: 1, color: "#34c759", ...noPriceLine }).setData([{ time: t0, value: 20 }, { time: t1, value: 20 }])

      const hist = macdChart.addHistogramSeries({ ...noPriceLine })
      const macd = macdChart.addLineSeries({ lineWidth: 2, color: "#38bdf8", ...noPriceLine })
      const sig  = macdChart.addLineSeries({ lineWidth: 2, color: "#fb7185", ...noPriceLine })
      safeSet(hist, histData(overlays, "macd_hist"))
      safeSet(macd, lineData(overlays, "macd"))
      safeSet(sig,  lineData(overlays, "macd_signal"))
      macdChart.addLineSeries({ lineWidth: 1, color: "rgba(255,255,255,0.55)", ...noPriceLine }).setData([{ time: t0, value: 0 }, { time: t1, value: 0 }])

      mainChart.timeScale().fitContent()
      const lr = { from: 0, to: Math.max(0, candles.length - 1) }
      mainChart.timeScale().setVisibleLogicalRange(lr)
      rsiChart.timeScale().setVisibleLogicalRange(lr)
      stochChart.timeScale().setVisibleLogicalRange(lr)
      macdChart.timeScale().setVisibleLogicalRange(lr)
      syncTimeScales(charts.current)
removeTVAttribution(mainRef.current)
      removeTVAttribution(rsiRef.current)
      removeTVAttribution(stochRef.current)
      removeTVAttribution(macdRef.current)
    } catch (e) {
      setErr(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => () => destroy(), [])

  useEffect(() => {
    const onResize = () => {
      const wrapW = wrapRef.current?.clientWidth
      if (!wrapW) return
      const w = Math.max(720, wrapW - 24)
      Object.values(charts.current).forEach(c => { try { c.applyOptions({ width: w }) } catch {} })
      applySameRangeFromMain(charts.current)
      removeTVAttribution(mainRef.current)
      removeTVAttribution(rsiRef.current)
      removeTVAttribution(stochRef.current)
      removeTVAttribution(macdRef.current)
    }
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [])

  const page = {
    minHeight: "100vh",
    background: "#ffffff",
    padding: "28px 16px 40px"
  }

  const container = {
    maxWidth: 1100,
    margin: "0 auto"
  }

  const title = {
    textAlign: "center",
    fontSize: 40,
    fontWeight: 800,
    letterSpacing: "-0.6px",
    color: "#0b2a5b",
    margin: "6px 0 18px"
  }

  const formWrap = {
    display: "flex",
    justifyContent: "center",
    marginBottom: 14
  }

  const form = {
    width: "100%",
    maxWidth: 760,
    display: "flex",
    gap: 12,
    alignItems: "center",
    padding: 10,
    borderRadius: 14,
    border: "1px solid rgba(11,42,91,0.12)",
    background: "linear-gradient(180deg, #ffffff 0%, #fbfcff 100%)",
    boxShadow: "0 10px 30px rgba(11,42,91,0.08)"
  }

  const input = {
    flex: 1,
    height: 46,
    padding: "0 14px",
    borderRadius: 12,
    border: "1px solid rgba(11,42,91,0.16)",
    outline: "none",
    fontSize: 16
  }

  const button = {
    height: 46,
    padding: "0 18px",
    borderRadius: 12,
    border: "1px solid rgba(11,42,91,0.15)",
    background: "linear-gradient(180deg, #0b2a5b 0%, #0a244d 100%)",
    color: "white",
    fontSize: 16,
    fontWeight: 700,
    cursor: "pointer",
    opacity: loading ? 0.7 : 1
  }

  const info = {
    maxWidth: 760,
    margin: "0 auto 12px",
    color: "rgba(11,42,91,0.55)",
    fontSize: 13,
    textAlign: "center"
  }

  const card = {
    maxWidth: 1100,
    margin: "0 auto",
    borderRadius: 16,
    border: "1px solid rgba(11,42,91,0.10)",
    background: "#ffffff",
    boxShadow: "0 16px 50px rgba(11,42,91,0.08)",
    padding: 14
  }

  return (
    <div style={page}>
      <div style={container}>
        <div style={title}>Market Vision Pro</div>

        <div style={formWrap}>
          <div style={form}>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="Ticker eingeben (z.B. AAPL.US)"
              style={input}
            />
            <button onClick={run} disabled={loading} style={button}>
              {loading ? "Lädt..." : "Analyse"}
            </button>
          </div>
        </div>

        <div style={info}>
          Eingabe: US = .US (z.B. TSLA.US) · Deutschland z.B. BMW.DE
        </div>

        {err ? <div style={{ maxWidth: 760, margin: "0 auto 12px", color: "#b42318", fontWeight: 600, textAlign: "center" }}>{err}</div> : null}

        <div style={card} ref={wrapRef}>
          <div style={{ borderRadius: 12, overflow: "hidden" }}>
            <div ref={mainRef} />
            <div ref={rsiRef} />
            <div ref={stochRef} />
            <div ref={macdRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
