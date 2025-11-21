import {useEffect,useRef,useState} from "react"
import Chart from "chart.js/auto"

const API=location.origin.replace("-front","")

function Box({title,children}){return(<div style={{border:"1px solid #ddd",borderRadius:8,padding:8,marginBottom:8}}><div style={{fontWeight:600,marginBottom:6}}>{title}</div>{children}</div>)}

function App(){
  const [q,setQ]=useState("Apple")
  const [r,setR]=useState("1Y")
  const [busy,setBusy]=useState(false)
  const c1=useRef(null),c2=useRef(null),c3=useRef(null),c4=useRef(null),c5=useRef(null)
  const charts=useRef({})
  function kill(k){if(charts.current[k]){charts.current[k].destroy();delete charts.current[k]}}
  function mk(k,cfg){kill(k);const ctx=(k==="c1"?c1:c2,c3,c4,c5);const map={c1,c2,c3,c4,c5};charts.current[k]=new Chart(map[k].current.getContext("2d"),cfg)}
  function clean(a){return (a||[]).map(v=>Number.isFinite(v)?v:null)}
  function sl(a,n){return (a||[]).slice(-n)}
  async function load(){
    setBusy(true)
    try{
      const hit=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`).then(r=>r.json())
      const symbol=(hit.hits&&hit.hits[0]&&hit.hits[0].code)||q.toUpperCase()
      const d=await fetch(`${API}/v1/bundle?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(r)}`).then(r=>r.json())
      const t=d.ohlcv.time||[]
      const close=clean(d.ohlcv.close)
      const high=clean(d.ohlcv.high)
      const low=clean(d.ohlcv.low)
      const ema20=clean(d.indicators?.ema20)
      const ema50=clean(d.indicators?.ema50)
      const rsi=clean(d.indicators?.rsi)
      const k=clean(d.indicators?.stochK)
      const dline=clean(d.indicators?.stochD)
      const macdL=clean(d.indicators?.macdLine)
      const macdS=clean(d.indicators?.macdSignal)
      const macdH=clean(d.indicators?.macdHist)
      const trH=clean(d.indicators?.trendH)
      const trL=clean(d.indicators?.trendL)
      const n=Math.min(t.length,close.length||0)
      const L=sl(t,n).map(x=>x)
      const mainCfg={type:"line",data:{labels:L,datasets:[
        {label:"Close",data:sl(close,n),borderWidth:1,pointRadius:0},
        {label:"EMA20",data:sl(ema20,n),borderWidth:1,pointRadius:0},
        {label:"EMA50",data:sl(ema50,n),borderWidth:1,pointRadius:0}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}}
      const stochCfg={type:"line",data:{labels:L,datasets:[
        {label:"K",data:sl(k,n),borderWidth:1,pointRadius:0},
        {label:"D",data:sl(dline,n),borderWidth:1,pointRadius:0},
        {label:"80",data:new Array(n).fill(80),borderWidth:1,pointRadius:0,borderDash:[6,6]},
        {label:"20",data:new Array(n).fill(20),borderWidth:1,pointRadius:0,borderDash:[6,6]}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{min:0,max:100}}}}
      const rsiCfg={type:"line",data:{labels:L,datasets:[
        {label:"RSI",data:sl(rsi,n),borderWidth:1,pointRadius:0},
        {label:"70",data:new Array(n).fill(70),borderWidth:1,pointRadius:0,borderDash:[6,6]},
        {label:"30",data:new Array(n).fill(30),borderWidth:1,pointRadius:0,borderDash:[6,6]}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{min:0,max:100}}}}
      const macdCfg={type:"bar",data:{labels:L,datasets:[
        {type:"bar",label:"H",data:sl(macdH,n),borderWidth:0},
        {type:"line",label:"MACD",data:sl(macdL,n),borderWidth:1,pointRadius:0},
        {type:"line",label:"Signal",data:sl(macdS,n),borderWidth:1,pointRadius:0}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}}
      const trendCfg={type:"line",data:{labels:L,datasets:[
        {label:"H",data:sl(trH,n),borderWidth:1,pointRadius:0},
        {label:"L",data:sl(trL,n),borderWidth:1,pointRadius:0}
      ]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}}
      mk("c1",mainCfg)
      mk("c2",stochCfg)
      mk("c3",rsiCfg)
      mk("c4",macdCfg)
      mk("c5",trendCfg)
    }finally{setBusy(false)}
  }
  useEffect(()=>()=>Object.keys(charts.current).forEach(k=>kill(k)),[])
  return(
    <div style={{padding:"8px"}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} style={{padding:"8px",width:220}}/>
        <button onClick={load} disabled={busy} style={{padding:"8px"}}>load</button>
        <span style={{marginLeft:8}}></span>
        {["1M","3M","6M","1Y","5Y","MAX"].map(x=><button key={x} onClick={()=>{setR(x);load()}} style={{padding:"6px 8px"}}>{x}</button>)}
      </div>
      <div style={{display:"grid",gridTemplateRows:"repeat(5,320px)",gap:8}}>
        <Box title="Main"><canvas ref={c1} style={{width:"100%",height:"300px"}}/></Box>
        <Box title="Stoch K/D"><canvas ref={c2} style={{width:"100%",height:"300px"}}/></Box>
        <Box title="RSI"><canvas ref={c3} style={{width:"100%",height:"300px"}}/></Box>
        <Box title="MACD"><canvas ref={c4} style={{width:"100%",height:"300px"}}/></Box>
        <Box title="Trend"><canvas ref={c5} style={{width:"100%",height:"300px"}}/></Box>
      </div>
    </div>
  )
}
export default App
