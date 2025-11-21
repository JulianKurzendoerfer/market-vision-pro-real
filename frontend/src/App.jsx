import {useRef,useState} from "react"

const API=import.meta.env.VITE_API_BASE||""
const Btn=({onClick,children,disabled})=><button onClick={onClick} disabled={disabled} style={{padding:"8px 12px",borderRadius:8,border:"1px solid #ddd"}}>{children}</button>
const Box=({title,children})=><div style={{border:"1px solid #ddd",borderRadius:8,padding:8,marginBottom:8}}><div style={{fontWeight:600,marginBottom:8}}>{title}</div>{children}</div>

export default function App(){
  const [q,setQ]=useState("Apple")
  const [busy,setBusy]=useState(false)
  const [rng,setRng]=useState("1Y")
  const charts=useRef({})

  function kill(id){
    if(charts.current[id]){ charts.current[id].destroy(); delete charts.current[id] }
  }
  function mk(id,cfg){
    const ctx=document.getElementById(id).getContext("2d")
    const c=new window.Chart(ctx,cfg)
    charts.current[id]=c
  }
  function lineCfg(x,ys){
    return {
      type:"line",
      data:{labels:x,datasets:ys},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{enabled:false}},
        scales:{x:{display:false},y:{display:false}}
      }
    }
  }
  function barLineCfg(x,bar,line1,line2){
    return {
      data:{labels:x,datasets:[bar,line1,line2]},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{display:false},tooltip:{enabled:false}},
        scales:{x:{display:false},y:{display:false}}
      }
    }
  }

  async function load(){
    setBusy(true)
    try{
      const r1=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}`).then(r=>r.json())
      const sym=(r1.hits&&r1.hits[0]&&r1.hits[0].code)||q
      const r=await fetch(`${API}/v1/bundle?symbol=${sym}&range=${rng}`).then(r=>r.json())
      const t=r.ohlcv.time
      const o=r.ohlcv.open,h=r.ohlcv.high,l=r.ohlcv.low,c=r.ohlcv.close
      const k=r.indicators.stochK,d=r.indicators.stochD
      const rsi=r.indicators.rsi
      const mL=r.indicators.macdLine,mS=r.indicators.macdSignal,mH=r.indicators.macdHist
      const e20=r.indicators.ema20,e50=r.indicators.ema50
      const th=r.indicators.th, tl=r.indicators.tl

      kill("c1"); kill("c2"); kill("c3"); kill("c4"); kill("c5")

      mk("c1", lineCfg(t,[
        {type:"line",data:c,borderWidth:1,pointRadius:0},
        {type:"line",data:e20,borderWidth:1,pointRadius:0},
        {type:"line",data:e50,borderWidth:1,pointRadius:0},
      ]))

      mk("c2", lineCfg(t,[
        {type:"line",data:k,borderWidth:1,pointRadius:0},
        {type:"line",data:d,borderWidth:1,pointRadius:0},
        {type:"line",data:new Array(t.length).fill(80),borderWidth:1,pointRadius:0,borderDash:[4,4]},
        {type:"line",data:new Array(t.length).fill(20),borderWidth:1,pointRadius:0,borderDash:[4,4]},
      ]))

      mk("c3", lineCfg(t,[
        {type:"line",data:rsi,borderWidth:1,pointRadius:0},
        {type:"line",data:new Array(t.length).fill(70),borderWidth:1,pointRadius:0,borderDash:[4,4]},
        {type:"line",data:new Array(t.length).fill(30),borderWidth:1,pointRadius:0,borderDash:[4,4]},
      ]))

      mk("c4", Object.assign({type:"bar"},
        barLineCfg(t,
          {type:"bar",data:mH,borderWidth:0},
          {type:"line",data:mL,borderWidth:1,pointRadius:0},
          {type:"line",data:mS,borderWidth:1,pointRadius:0}
        )
      ))

      mk("c5", lineCfg(t,[
        {type:"line",data:c,borderWidth:1,pointRadius:0},
        {type:"line",data:th,borderWidth:1,pointRadius:0},
        {type:"line",data:tl,borderWidth:1,pointRadius:0},
      ]))

    } finally { setBusy(false) }
  }

  return (
    <div style={{padding:"8px"}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} />
        <Btn onClick={load} disabled={busy}>load</Btn>
        <span style={{marginLeft:8}}></span>
        {["1M","3M","6M","1Y","5Y","MAX"].map(r=><button key={r} onClick={()=>{setRng(r)}} style={{padding:"6px 8px",border:"1px solid #ddd",borderRadius:8,background:rng===r?"#eee":"#fff"}}>{r}</button>)}
      </div>

      <div style={{display:"grid",gridTemplateRows:"repeat(5,320px)",gap:8}}>
        <Box title="Main"><canvas id="c1" style={{width:"100%",height:"260px"}}/></Box>
        <Box title="Stoch K/D"><canvas id="c2" style={{width:"100%",height:"260px"}}/></Box>
        <Box title="RSI"><canvas id="c3" style={{width:"100%",height:"260px"}}/></Box>
        <Box title="MACD"><canvas id="c4" style={{width:"100%",height:"260px"}}/></Box>
        <Box title="Trend"><canvas id="c5" style={{width:"100%",height:"260px"}}/></Box>
      </div>
    </div>
  )
}
