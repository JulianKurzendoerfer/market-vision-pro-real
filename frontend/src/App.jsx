import { useEffect, useState } from "react"

const API = import.meta.env.VITE_API_BASE?.replace(/\/+$/,"")

export default function App(){
  const [symbol,setSymbol] = useState("AAPL")
  const [range,setRange] = useState("1Y")
  const [data,setData] = useState(null)
  const [err,setErr] = useState(null)
  const load = async () => {
    setErr(null); setData(null)
    const url = `${API}/v1/bundle?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(range)}`
    try{
      const r = await fetch(url)
      const j = await r.json()
      if(!j.ok) throw new Error(j.error || "error")
      setData(j)
    }catch(e){ setErr(String(e.message||e)) }
  }
  useEffect(()=>{ if(API) load() },[])
  return (
    <div style={{fontFamily:"Inter, system-ui, Arial", padding:16, maxWidth:900, margin:"0 auto"}}>
      <h2>Market Vision Pro — Front</h2>
      <div style={{display:"flex", gap:8, marginBottom:12}}>
        <input value={symbol} onChange={e=>setSymbol(e.target.value)} placeholder="Ticker" />
        <select value={range} onChange={e=>setRange(e.target.value)}>
          <option>1D</option><option>5D</option><option>1W</option><option>1MO</option>
          <option>3MO</option><option>6MO</option><option>1Y</option><option>2Y</option>
          <option>5Y</option><option>10Y</option><option>YTD</option><option>MAX</option>
        </select>
        <button onClick={load}>Load</button>
      </div>
      {!API && <div style={{color:"#c00"}}>VITE_API_BASE fehlt</div>}
      {err && <div style={{color:"#c00"}}>{err}</div>}
      {data && (
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:8}}>
          <div><b>Symbol:</b> {data.meta?.symbol}</div>
          <div><b>Rows:</b> {data.meta?.rows}</div>
          <div><b>Period/Interval:</b> {data.meta?.period} / {data.meta?.interval}</div>
          <div><b>Indicators:</b> {(data.meta?.indicators||[]).join(", ")}</div>
          <div style={{gridColumn:"1 / -1", marginTop:8}}>
            <b>Preview Close (last 10):</b>
            <div style={{fontFamily:"mono"}}>{(data.c||[]).slice(-10).map(v=>v.toFixed(2)).join(", ")}</div>
          </div>
        </div>
      )}
    </div>
  )
}
