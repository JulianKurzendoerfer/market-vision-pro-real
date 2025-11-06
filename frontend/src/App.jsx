import { useEffect, useMemo, useRef, useState } from "react"
import { createChart } from "lightweight-charts"

const API = import.meta.env.VITE_API_BASE || ""

function useFetch(url, deps) {
  const [data,setData]=useState(null)
  const [err,setErr]=useState(null)
  const [loading,setLoading]=useState(false)
  useEffect(()=>{
    if(!url) return
    let abort=false
    setLoading(true); setErr(null)
    fetch(url,{credentials:"omit"}).then(async r=>{
      if(!r.ok) throw new Error("HTTP "+r.status)
      const j=await r.json()
      if(!abort) setData(j)
    }).catch(e=>!abort&&setErr(String(e))).finally(()=>!abort&&setLoading(false))
    return ()=>{abort=true}
  },deps)
  return {data,err,loading}
}

function Pane({title,series,gridRows=3}) {
  const ref=useRef(null)
  const chartRef=useRef(null)
  useEffect(()=>{
    if(!ref.current) return
    if(chartRef.current){ chartRef.current.remove(); chartRef.current=null }
    const c=createChart(ref.current,{height:220,layout:{background:{type:"solid",color:"#0b0c10"},textColor:"#eaecef"},rightPriceScale:{borderVisible:false},timeScale:{borderVisible:false},grid:{vertLines:{color:"#1f232a"},horzLines:{color:"#1f232a"}}})
    series.forEach(s=>{
      let h
      if(s.type==="candlestick"){ h=c.addCandlestickSeries({upColor:"#22c55e",downColor:"#ef4444",borderVisible:false,wicksVisible:true}); h.setData(s.data) }
      else if(s.type==="line"){ h=c.addLineSeries({lineWidth:2}); h.setData(s.data) }
      else if(s.type==="hist"){ h=c.addHistogramSeries({priceFormat:{type:"volume"}}); h.setData(s.data) }
      else if(s.type==="area"){ h=c.addAreaSeries({lineWidth:2}); h.setData(s.data) }
    })
    chartRef.current=c
    const ro=new ResizeObserver(()=>c.applyOptions({width:ref.current.clientWidth}))
    ro.observe(ref.current)
    return ()=>{ro.disconnect(); c.remove()}
  },[JSON.stringify(series)])
  return (
    <div style={{background:"#0d1117",border:"1px solid #1f232a",borderRadius:14,padding:12}}>
      <div style={{fontSize:14,opacity:.8,marginBottom:8}}>{title}</div>
      <div ref={ref} style={{width:"100%"}} />
    </div>
  )
}

function Ladder({rows}) {
  if(!rows?.length) return null
  const items=rows.slice(0,30)
  return (
    <div style={{background:"#0d1117",border:"1px solid #1f232a",borderRadius:14,padding:12}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <div style={{fontSize:14,opacity:.8}}>Options-Ladder (7–14 Tage)</div>
      </div>
      <div style={{overflowX:"auto",marginTop:8}}>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
          <thead>
            <tr style={{background:"#0b0c10"}}>
              <th style={{textAlign:"left",padding:"8px"}}>Side</th>
              <th style={{textAlign:"right",padding:"8px"}}>Strike</th>
              <th style={{textAlign:"right",padding:"8px"}}>Spot</th>
              <th style={{textAlign:"right",padding:"8px"}}>Expiry</th>
              <th style={{textAlign:"right",padding:"8px"}}>Premium</th>
              <th style={{textAlign:"right",padding:"8px"}}>Yield/wk %</th>
              <th style={{textAlign:"right",padding:"8px"}}>OTM %</th>
              <th style={{textAlign:"left",padding:"8px"}}>Risk</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r,i)=>(
              <tr key={i} style={{borderTop:"1px solid #1f232a"}}>
                <td style={{padding:"8px",color:r.side==="put"?"#22c55e":"#ef4444"}}>{String(r.side||"").toUpperCase()}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{Number(r.strike).toFixed(2)}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{Number(r.spot).toFixed(2)}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{String(r.expiry).slice(0,10)}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{Number(r.premium||r.mid||0).toFixed(2)}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{Number(r.yield_weekly_pct||0).toFixed(2)}</td>
                <td style={{padding:"8px",textAlign:"right"}}>{Number(r.otm_pct||0).toFixed(2)}</td>
                <td style={{padding:"8px"}}>{r.risk||""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function App(){
  const [q,setQ]=useState("Apple")
  const [symbol,setSymbol]=useState("AAPL.US")
  const [interval,setInterval]=useState("1d")
  const [limit,setLimit]=useState(200)
  const [optOpen,setOptOpen]=useState(false)

  const {data:res}=useFetch(q?`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`:"",[q])
  useEffect(()=>{ if(res?.code) setSymbol(`${res.code}.US`) },[res])

  const {data:bars}=useFetch(symbol?`${API}/v1/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`:"",[symbol,interval,limit])
  const {data:ind}=useFetch(symbol?`${API}/v1/indicators?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=${limit}`:"",[symbol,interval,limit])
  const {data:lad}=useFetch(symbol?`${API}/v1/options/ladder?symbol=${encodeURIComponent(symbol)}&side=both`:"",[symbol])

  const priceSeries=useMemo(()=>{
    const c=(bars?.bars||bars)||[]
    const cs=c.map(d=>({time:Math.floor((d.t||d.time)/1000),open:+d.o,high:+d.h,low:+d.l,close:+d.c})).filter(x=>x.time&&isFinite(x.close))
    const u=(ind?.bb_upper||ind?.bbUpper||[]).map(d=>({time:Math.floor((d.t||d.time)/1000),value:+(d.u||d.value||d.bb_u||d.bbUpper)})).filter(x=>x.time&&isFinite(x.value))
    const l=(ind?.bb_lower||ind?.bbLower||[]).map(d=>({time:Math.floor((d.t||d.time)/1000),value:+(d.l||d.value||d.bb_l||d.bbLower)})).filter(x=>x.time&&isFinite(x.value))
    return [
      {type:"candlestick",data:cs},
      {type:"line",data:u},
      {type:"line",data:l},
    ]
  },[bars,ind])

  const stochSeries=useMemo(()=>{
    const k=(ind?.stoch_k||ind?.stochK||[]).map(d=>({time:Math.floor((d.t||d.time)/1000),value:+(d.k||d.value)}))
    const d=(ind?.stoch_d||ind?.stochD||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+(x.d||x.value)}))
    return [
      {type:"line",data:k},
      {type:"line",data:d},
      {type:"line",data:k.map(p=>({time:p.time,value:80}))},
      {type:"line",data:k.map(p=>({time:p.time,value:20}))},
    ]
  },[ind])

  const rsiSeries=useMemo(()=>{
    const r=(ind?.rsi||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+(x.rsi||x.value)}))
    return [
      {type:"line",data:r},
      {type:"line",data:r.map(p=>({time:p.time,value:70}))},
      {type:"line",data:r.map(p=>({time:p.time,value:30}))},
    ]
  },[ind])

  const macdSeries=useMemo(()=>{
    const ml=(ind?.macd||ind?.macd_line||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+(x.macd||x.value)}))
    const sig=(ind?.macd_signal||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+(x.signal||x.value)}))
    const hist=(ind?.macd_hist||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+(x.hist||x.value)}))
    return [
      {type:"line",data:ml},
      {type:"line",data:sig},
      {type:"hist",data:hist.map(h=>({time:h.time,value:h.value,color:h.value>=0?"#22c55e":"#ef4444"}))},
    ]
  },[ind])

  const trendSeries=useMemo(()=>{
    const hi=(ind?.swing_highs||ind?.highs||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+x.price}))
    const lo=(ind?.swing_lows||ind?.lows||[]).map(x=>({time:Math.floor((x.t||x.time)/1000),value:+x.price}))
    return [
      {type:"line",data:hi},
      {type:"line",data:lo},
    ]
  },[ind])

  return (
    <div style={{minHeight:"100vh",background:"#0b0c10",color:"#eaecef"}}>
      <div style={{maxWidth:1300,margin:"0 auto",padding:16}}>
        <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:12}}>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Name/Ticker" style={{background:"#0d1117",color:"#eaecef",border:"1px solid #1f232a",borderRadius:10,padding:"10px 12px",width:260}}/>
          <select value={interval} onChange={e=>setInterval(e.target.value)} style={{background:"#0d1117",color:"#eaecef",border:"1px solid #1f232a",borderRadius:10,padding:"10px 12px"}}>
            <option value="1d">1d</option>
            <option value="60m">60m</option>
            <option value="5m">5m</option>
          </select>
          <button onClick={()=>setLimit(l=>l)} style={{background:"#2563eb",border:"none",color:"#fff",borderRadius:10,padding:"10px 14px"}}>Analysieren</button>
          <div style={{marginLeft:8,opacity:.7}}>{symbol}</div>
          <div style={{flex:1}}/>
          <button onClick={()=>setOptOpen(v=>!v)} style={{background:"#111827",border:"1px solid #1f232a",color:"#eaecef",borderRadius:10,padding:"10px 14px"}}>{optOpen?"Optionen ausblenden":"Optionen anzeigen"}</button>
        </div>

        <div style={{display:"grid",gridTemplateColumns:"1fr",gap:12}}>
          <Pane title="Preis + Bollinger" series={priceSeries}/>
          <Pane title="Stochastik (K/D, 80/20)" series={stochSeries}/>
          <Pane title="RSI (70/30)" series={rsiSeries}/>
          <Pane title="MACD" series={macdSeries}/>
          <Pane title="Trendpanel (Highs/Lows)" series={trendSeries}/>
          {optOpen && <Ladder rows={lad?.rows}/>}
        </div>
      </div>
    </div>
  )
}
