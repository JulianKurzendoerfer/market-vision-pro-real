import {useRef,useState} from "react"
const API=import.meta.env.VITE_API_BASE
function loadScript(u){return new Promise(r=>{const s=document.createElement("script");s.src=u;s.onload=r;document.head.appendChild(s)})}
async function needChart(){if(!window.Chart){await loadScript("https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js")}}

export default function App(){
  const charts=useRef({})
  const [q,setQ]=useState("Apple")
  const [r,setR]=useState("1Y")
  const [busy,setBusy]=useState(false)
  function kill(k){if(charts.current[k]){charts.current[k].destroy();delete charts.current[k]}}
  function mk(id,cfg){kill(id);const ctx=document.getElementById(id).getContext("2d");charts.current[id]=new window.Chart(ctx,cfg)}
  function line(y,label){return {type:"line",data:y,borderWidth:1,pointRadius:0,tension:0,label}}
  function bar(y,label){return {type:"bar",data:y,label,borderWidth:0}}
  function band(v,len){return Array(len).fill(v)}

  async function load(){
    setBusy(true)
    await needChart()
    const sym=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`).then(r=>r.json()).then(a=>a[0]?.code||"AAPL")
    const b=await fetch(`${API}/v1/bundle?symbol=${sym}&range=${r}`).then(r=>r.json())
    const t=b.ohlcv.time
    const close=b.ohlcv.close
    const high=b.ohlcv.high
    const low=b.ohlcv.low
    const ema20=b.indicators.ema20||[]
    const ema50=b.indicators.ema50||[]
    const rsi=b.indicators.rsi||[]
    const k=b.indicators.stochK||[]
    const d=b.indicators.stochD||[]
    const macdL=b.indicators.macdLine||[]
    const macdS=b.indicators.macdSignal||[]
    const macdH=macdL.map((v,i)=>v-(macdS[i]??0))

    const labels=t
    const mainCfg={data:{labels,datasets:[line(close,"Close"),line(ema20,"EMA20"),line(ema50,"EMA50")]},options:{plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}}}}}
    const stochCfg={data:{labels,datasets:[line(k,"K"),line(d,"D"),line(band(80,t.length),""),line(band(20,t.length),"")]},options:{plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}}}}}
    const rsiCfg={data:{labels,datasets:[line(rsi,"RSI"),line(band(70,t.length),""),line(band(30,t.length),"")]},options:{plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}}}}}
    const macdCfg={data:{labels,datasets:[bar(macdH,"H"),line(macdL,"L"),line(macdS,"S")]},options:{plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}}}}}
    const trendCfg={data:{labels,datasets:[line(high,"H"),line(low,"L")]},options:{plugins:{legend:{display:false}},responsive:true,maintainAspectRatio:false,scales:{x:{ticks:{maxTicksLimit:8}}}}}

    mk("c1",mainCfg)
    mk("c2",stochCfg)
    mk("c3",rsiCfg)
    mk("c4",macdCfg)
    mk("c5",trendCfg)
    setBusy(false)
  }

  return (
    <div style={{padding:"8px"}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={load} disabled={busy}>load</button>
        <span style={{marginLeft:8}}></span>
        {["1M","3M","6M","1Y","5Y","MAX"].map(x=><button key={x} onClick={()=>{setR(x)}} style={{marginRight:6}}>{x}</button>)}
      </div>
      <div style={{display:"grid",gridTemplateRows:"repeat(5,320px)",gap:8}}>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Main</div><canvas id="c1" style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Stoch K/D</div><canvas id="c2" style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>RSI</div><canvas id="c3" style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>MACD</div><canvas id="c4" style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Trend</div><canvas id="c5" style={{width:"100%",height:"260px"}}/></div>
      </div>
    </div>
  )
}
