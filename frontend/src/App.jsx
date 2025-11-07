import { useEffect, useState } from "react"

const API = import.meta.env.VITE_API_BASE || ""

function num(v, d=2){ return v==null || Number.isNaN(v) ? "-" : (+v).toFixed(d) }

export default function App(){
  const [q,setQ] = useState("Apple")
  const [status,setStatus] = useState("ok")
  const [suggest,setSuggest] = useState([])
  const [symbol,setSymbol] = useState("")
  const [price,setPrice] = useState(null)
  const [stoch,setStoch] = useState({k:null,d:null})
  const [rsi,setRsi] = useState(null)
  const [macd,setMacd] = useState({line:null,signal:null})
  const [ema,setEma] = useState({e20:null,e50:null})

  async function fetchResolve(){
    setStatus("…")
    const r = await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`)
    const arr = await r.json()
    setSuggest(arr || [])
    const best = (arr && arr[0]?.code) || ""
    setSymbol(best)
    setStatus("ok")
  }

  async function fetchData(){
    if(!symbol) return
    setStatus("load")
    const [ohlcvRes, indRes] = await Promise.all([
      fetch(`${API}/v1/ohlcv?symbol=${encodeURIComponent(symbol)}`),
      fetch(`${API}/v1/indicators?symbol=${encodeURIComponent(symbol)}`)
    ])
    const ohlcv = await ohlcvRes.json()
    const ind = await indRes.json()
    const last = Array.isArray(ohlcv) && ohlcv.length ? ohlcv[ohlcv.length-1] : null
    setPrice(last?.close ?? null)
    setStoch({k: ind?.stochK ?? null, d: ind?.stochD ?? null})
    setRsi(ind?.rsi ?? null)
    setMacd({line: ind?.macdLine ?? null, signal: ind?.macdSignal ?? null})
    setEma({e20: ind?.ema20 ?? null, e50: ind?.ema50 ?? null})
    setStatus("ok")
  }

  useEffect(()=>{ /* no auto */ },[])

  function Card({title,children}){ 
    return <div style={{border:"1px solid #ddd", borderRadius:8, padding:16, minHeight:120}}>
      <div style={{fontSize:14, color:"#666"}}>{title}</div>
      <div style={{fontSize:28, marginTop:8}}>{children}</div>
    </div>
  }

  return (
    <div style={{maxWidth:1200,margin:"40px auto",fontFamily:"system-ui"}}>
      <h2>Market Vision Pro <span style={{fontSize:14,marginLeft:8,color:"#666"}}>{status}</span></h2>

      <div style={{display:"flex", gap:12, alignItems:"center"}}>
        <input value={q} onChange={e=>setQ(e.target.value)} style={{padding:6}} />
        <button onClick={fetchResolve} style={{padding:"6px 10px"}}>ok</button>
        <div style={{marginLeft:12, color:"#666"}}>{symbol}</div>
        <button onClick={fetchData} style={{padding:"6px 10px"}}>load</button>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16,marginTop:16}}>
        <div style={{whiteSpace:"pre",fontFamily:"ui-monospace, SFMono-Regular, Menlo, monospace"}}>{
          (suggest||[]).map(s=>s.name || s.code).join("\n")
        }</div>
        <div style={{gridColumn:"span 2"}}>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
            <Card title="Preise">{num(price,2)} USD</Card>
            <Card title="Stoch K/D">{num(stoch.k,1)} / {num(stoch.d,1)}</Card>
            <Card title="RSI">{num(rsi,1)}</Card>
            <Card title="MACD">{num(macd.line,2)} / {num(macd.signal,2)}</Card>
            <Card title="EMA20/50">{num(ema.e20,2)} / {num(ema.e50,2)}</Card>
          </div>
        </div>
      </div>
    </div>
  )
}
