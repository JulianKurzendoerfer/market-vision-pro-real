import {useEffect,useState} from "react"
const API=(import.meta.env.VITE_API_BASE||"").replace(/\/$/,"")
export default function App(){
  const [q,setQ]=useState("Apple")
  const [sym,setSym]=useState("")
  const [bars,setBars]=useState([])
  const [ind,setInd]=useState(null)
  const [ok,setOk]=useState("…")
  async function j(u){const r=await fetch(u,{credentials:"include"});if(!r.ok)throw new Error();return r.json()}
  useEffect(()=>{(async()=>{try{const r=await j(API+"/health");setOk(r.ok?"ok":"fail")}catch(e){setOk("fail")}})()},[])
  useEffect(()=>{(async()=>{try{const r=await j(API+"/v1/resolve?q="+encodeURIComponent(q)+"&prefer=US");setSym(r?.[0]?.code||"")}catch(e){setSym("")}})()},[q])
  useEffect(()=>{(async()=>{if(!sym)return;try{const o=await j(API+"/v1/ohlcv?symbol="+encodeURIComponent(sym)+"&interval=60m");setBars(o.bars||[]);const ii=await j(API+"/v1/indicators?symbol="+encodeURIComponent(sym)+"&interval=60m");setInd(ii)}catch(e){setBars([]);setInd(null)}})()},[sym])
  return(<div style={{padding:16,fontFamily:"system-ui",maxWidth:1100,margin:"0 auto"}}>
    <h2>Market Vision Pro</h2>
    <div style={{display:"flex",gap:8,alignItems:"center"}}><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Suche"/><span>{ok}</span><span style={{marginLeft:"auto"}}>{sym}</span></div>
    <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:12,marginTop:16}}>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>Preise</div><div>{bars.length?("Close "+bars.at(-1).c):"-"}</div></div>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>Stoch K/D</div><div>{ind?(ind.stochK?.toFixed?.(2)??"-")+"/"+(ind.stochD?.toFixed?.(2)??"-"):"-"}</div></div>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>RSI</div><div>{ind?(ind.rsi14?.toFixed?.(2)??"-"):"-"}</div></div>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>MACD</div><div>{ind?((ind.macd?.toFixed?.(3)??"-")+" / "+(ind.macdSignal?.toFixed?.(3)??"-")):"-"}</div></div>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>EMA20/50</div><div>{ind?("E20 "+(ind.ema20?.toFixed?.(2)??"-")+" · E50 "+(ind.ema50?.toFixed?.(2)??"-")):"-"}</div></div>
      <div style={{border:"1px solid #ddd",padding:12,borderRadius:8}}><div>Optionen</div><div>später</div></div>
    </div></div>)}
