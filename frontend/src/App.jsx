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


const ellLineData = (candles, deviation=0.06, minBars=8) => {
  if (!candles || candles.length < (minBars + 10)) return []
  const pct = (a,b) => b === 0 ? 0 : (a-b)/b
  const pivots = []
  let last = candles[0].close
  let trend = 0
  let exI = 0
  let exP = last

  for (let i=1;i<candles.length;i++){
    const hi = candles[i].high
    const lo = candles[i].low
    if (trend === 0){
      if (pct(hi,last) >= deviation){ trend = 1; exI=i; exP=hi }
      else if (pct(last,lo) >= deviation){ trend = -1; exI=i; exP=lo }
      continue
    }
    if (trend === 1){
      if (hi > exP){ exP = hi; exI = i }
      if (pct(exP, lo) >= deviation && (i-exI) >= minBars){
        pivots.push({ time: candles[exI].time, value: exP, t: "H" })
        trend = -1
        last = exP
        exI = i
        exP = lo
      }
    } else {
      if (lo < exP){ exP = lo; exI = i }
      if (pct(hi, exP) >= deviation && (i-exI) >= minBars){
        pivots.push({ time: candles[exI].time, value: exP, t: "L" })
        trend = 1
        last = exP
        exI = i
        exP = hi
      }
    }
  }
  pivots.push({ time: candles[exI].time, value: exP, t: trend===1 ? "H":"L" })
  const cleaned = []
  for (const pv of pivots){
    if (!cleaned.length){ cleaned.push(pv); continue }
    const prev = cleaned[cleaned.length-1]
    if (pv.t === prev.t){
      if (pv.t === "H"){
        if (pv.value >= prev.value) cleaned[cleaned.length-1]=pv
      } else {
        if (pv.value <= prev.value) cleaned[cleaned.length-1]=pv
      }
    } else cleaned.push(pv)
  }
  return cleaned.map(x=>({time:x.time,value:x.value}))
}

const ellMarkers = (pivots) => {
  if (!pivots || pivots.length < 5) return []
  const last = pivots.slice(-5)
  const labels = ["1","2","3","4","5"]
  return last.map((p,i)=>({
    time: p.time,
    position: "aboveBar",
    color: "rgba(255,255,255,0.85)",
    shape: "circle",
    text: labels[i]
  }))
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
  const elliottRef = useRef(null)
  const charts = useRef({})

  const heights = useMemo(() => ({ main: 420, rsi: 140, stoch: 170, macd: 170, elliott: 360 }), [])

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
      const elliottChart = createChart(elliottRef.current, baseOpts(w, heights.elliott, true))

      charts.current = { mainChart, rsiChart, stochChart, macdChart, elliottChart }

      const cs = mainChart.addCandlestickSeries({ priceLineVisible: false, lastValueVisible: false })

      const elliott = data.elliott || {}
      const ePivots = Array.isArray(elliott.pivots) ? elliott.pivots : []
      const eLabels = Array.isArray(elliott.labels) ? elliott.labels : []
      const mainSc = elliott.main_scenario || null
      const altSc = elliott.alt_scenario || null
      const eStructure = elliott.current_structure || ""
      const eConf = elliott.confidence || "none"
      const eDir = elliott.direction || ""

      const cs2 = elliottChart.addCandlestickSeries({ priceLineVisible: false, lastValueVisible: false })
      cs2.setData(candles)

      const allPivots = ePivots.filter(x => isTime(x.time) && isNum(x.price))
      const lastCandle = candles[candles.length - 1]
      const elliottLastClose = lastCandle?.close || 0
      const lastTime = lastCandle?.time

      const zzData = allPivots.map(x => ({ time: x.time, value: Number(x.price) }))
      if (lastTime && elliottLastClose && (zzData.length === 0 || zzData[zzData.length-1].time !== lastTime)) {
        zzData.push({ time: lastTime, value: elliottLastClose })
      }
      const zz2 = elliottChart.addLineSeries({ lineWidth: 2, color: "rgba(255,215,0,0.75)", priceLineVisible: false, lastValueVisible: false })
      if (zzData.length > 1) { try { zz2.setData(zzData) } catch {} }

      const markers2 = eLabels
        .filter(x => isTime(x.time) && isNum(x.price))
        .map(x => ({
          time: x.time,
          position: x.text === "2" || x.text === "4" || x.text === "B" ? "belowBar" : "aboveBar",
          color: x.text === "3" ? "rgba(52,199,89,1)" : x.text === "5" ? "rgba(255,200,0,1)" : x.text === "A" || x.text === "C" ? "rgba(255,100,100,1)" : "rgba(255,255,255,0.95)",
          shape: "circle",
          text: String(x.text || "")
        }))
      if (markers2.length > 0) { try { cs2.setMarkers(markers2) } catch {} }

      if (mainSc && mainSc.target_zone && mainSc.target_zone.length === 2) {
        const mLow = Math.min(...mainSc.target_zone)
        const mHigh = Math.max(...mainSc.target_zone)
        cs2.createPriceLine({ price: mHigh, color: "rgba(52,199,89,0.85)", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `▼ Ziel ${mainSc.probability||""}%  $${mHigh}` })
        cs2.createPriceLine({ price: mLow, color: "rgba(52,199,89,0.85)", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `$${mLow}` })
      }

      if (altSc && altSc.target_zone && altSc.target_zone.length === 2) {
        const aLow = Math.min(...altSc.target_zone)
        const aHigh = Math.max(...altSc.target_zone)
        cs2.createPriceLine({ price: aHigh, color: "rgba(255,160,50,0.85)", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `▲ Alt ${altSc.probability||""}%  $${aHigh}` })
        cs2.createPriceLine({ price: aLow, color: "rgba(255,160,50,0.85)", lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `$${aLow}` })
      }

      if (elliottRef.current && eStructure) {
        elliottRef.current.style.position = "relative"
        let box = elliottRef.current.querySelector(".elliott-info")
        if (!box) {
          box = document.createElement("div")
          box.className = "elliott-info"
          elliottRef.current.appendChild(box)
        }
        const confColor = eConf === "high" ? "#34c759" : eConf === "medium" ? "#fbbf24" : "#9ca3af"
        const dirIcon = eDir === "bullish" ? "▲" : eDir === "bearish" ? "▼" : ""
        box.style.cssText = "position:absolute;top:8px;left:12px;z-index:20;background:rgba(11,15,25,0.90);border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:8px 14px;font-size:12px;color:#e2e8f0;max-width:300px;pointer-events:none;line-height:1.6;"
        let html = `<div style="font-weight:700;font-size:13px;color:${confColor};margin-bottom:4px;">${dirIcon} ${eStructure}</div>`
        if (mainSc) {
          html += `<div style="color:rgba(52,199,89,1);margin-bottom:1px;">▼ ${mainSc.description} (${mainSc.probability||"?"}%)</div>`
          if (mainSc.target_zone) html += `<div style="color:rgba(52,199,89,0.7);font-size:11px;margin-bottom:5px;">&nbsp;&nbsp;Zone: $${mainSc.target_zone[0]} – $${mainSc.target_zone[1]}</div>`
        }
        if (altSc) {
          html += `<div style="color:rgba(255,160,50,1);margin-bottom:1px;">▲ ${altSc.description} (${altSc.probability||"?"}%)</div>`
          if (altSc.target_zone) html += `<div style="color:rgba(255,160,50,0.7);font-size:11px;">&nbsp;&nbsp;Zone: $${altSc.target_zone[0]} – $${altSc.target_zone[1]}</div>`
        }
        box.innerHTML = html
      }

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
      const lastClose = candles[candles.length - 1].close
      const chartMin = Math.min(...candles.map(x => x.low))
      const chartMax = Math.max(...candles.map(x => x.high))
      const priceSpan = chartMax - chartMin
      const nearThreshold = Math.max(lastClose * 0.04, priceSpan * 0.08)

      const normalizedLevels = levels
        .filter(lvl => lvl && isNum(lvl.value))
        .map(lvl => {
          const value = Number(lvl.value)
          const strength = Math.max(1, Number(lvl.strength || 1))
          const dist = Math.abs(value - lastClose)
          return { ...lvl, value, strength, dist }
        })
        .filter(lvl => lvl.value >= chartMin * 0.92 && lvl.value <= chartMax * 1.08)

      const scoreLevel = (lvl) => {
        const proximityScore = 1 / (1 + lvl.dist / (lastClose * 0.05))
        return lvl.strength * 0.5 + proximityScore * 3
      }

      const supports = normalizedLevels
        .filter(lvl => lvl.value <= lastClose)
        .sort((a, b) => scoreLevel(b) - scoreLevel(a))
        .slice(0, 10)

      const resistances = normalizedLevels
        .filter(lvl => lvl.value > lastClose)
        .sort((a, b) => scoreLevel(b) - scoreLevel(a))
        .slice(0, 10)

      let visibleLevels = [...supports, ...resistances]

      if (visibleLevels.length < 4) {
        visibleLevels = normalizedLevels
          .sort((a, b) => scoreLevel(b) - scoreLevel(a))
          .slice(0, 14)
      }

      const seen = new Set()
      visibleLevels = visibleLevels
        .filter(lvl => {
          const key = lvl.value.toFixed(3)
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
        .sort((a, b) => a.value - b.value)

      const nearestSupport = [...visibleLevels]
        .filter(lvl => lvl.value <= lastClose)
        .sort((a, b) => a.dist - b.dist)[0]

      const nearestResistance = [...visibleLevels]
        .filter(lvl => lvl.value > lastClose)
        .sort((a, b) => a.dist - b.dist)[0]

      for (const lvl of visibleLevels) {
        const isNearest =
          (nearestSupport && lvl.value === nearestSupport.value) ||
          (nearestResistance && lvl.value === nearestResistance.value)

        let color = "rgba(64,130,255,0.62)"
        let width = 1
        let showLabel = false

        if (lvl.strength >= 6) {
          color = isNearest ? "rgba(46,124,255,0.98)" : "rgba(46,124,255,0.86)"
          width = isNearest ? 3 : 2
          showLabel = true
        } else if (lvl.strength >= 4) {
          color = isNearest ? "rgba(70,144,255,0.94)" : "rgba(70,144,255,0.78)"
          width = isNearest ? 2 : 1
          showLabel = isNearest
        } else {
          color = isNearest ? "rgba(110,170,255,0.90)" : "rgba(110,170,255,0.68)"
          width = isNearest ? 2 : 1
          showLabel = isNearest
        }

        cs.createPriceLine({
          price: lvl.value,
          color,
          lineWidth: width,
          lineStyle: 0,
          axisLabelVisible: showLabel,
          title: ""
        })
      }

      cs.createPriceLine({
        price: Number(lastClose),
        color: "rgba(52,199,89,0.95)",
        lineWidth: 1,
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
      const macdBars = (overlays || [])
        .filter(x => isTime(x.time) && isNum(x.macd_hist))
        .map(x => {
          const v = Number(x.macd_hist)
          return { time: x.time, value: v, color: v >= 0 ? "rgba(38,166,154,0.9)" : "rgba(239,83,80,0.9)" }
        })
      try { hist.setData(macdBars) } catch {}
      macdChart.addLineSeries({ lineWidth: 1, color: "rgba(255,255,255,0.35)", ...noPriceLine }).setData([{ time: t0, value: 0 }, { time: t1, value: 0 }])
mainChart.timeScale().fitContent()
      const lr = { from: 0, to: Math.max(0, candles.length - 1) }
      mainChart.timeScale().setVisibleLogicalRange(lr)
      rsiChart.timeScale().setVisibleLogicalRange(lr)
      stochChart.timeScale().setVisibleLogicalRange(lr)
      macdChart.timeScale().setVisibleLogicalRange(lr)
      elliottChart.timeScale().setVisibleLogicalRange(lr)
      syncTimeScales(charts.current)
      removeTVAttribution(mainRef.current)
      removeTVAttribution(rsiRef.current)
      removeTVAttribution(stochRef.current)
      removeTVAttribution(macdRef.current)
      removeTVAttribution(elliottRef.current)
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
      removeTVAttribution(elliottRef.current)
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
            <div ref={elliottRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
