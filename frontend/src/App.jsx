import { useEffect, useRef, useState } from "react"

const API=(import.meta.env.VITE_API_BASE||"").replace(/\/$/,"")

function toDates(a){return a.map(v=>new Date(v))}
function xy(xs,ys){return xs.map((x,i)=>({x,y:ys[i]}))}
function ohlc(xs,o,h,l,c){return xs.map((x,i)=>({x,o:o[i],h:h[i],l:l[i],c:c[i]}))}

export default function App(){
  const [q,setQ]=useState("Apple")
  const [s,setS]=useState("")
  const [r,setR]=useState("1Y")
  const [busy,setBusy]=useState(false)
  const dataRef=useRef(null)

  const cRef={main:useRef(null),stoch:useRef(null),rsi:useRef(null),macd:useRef(null),trend:useRef(null)}
  const charts=useRef({})

  function kill(id){if(charts.current[id]){charts.current[id].destroy();charts.current[id]=null}}

  function render(id,cfg){
    const C=window.Chart
    kill(id)
    const ctx=cRef[id].current.getContext("2d")
    charts.current[id]=new C(ctx,cfg)
  }

  async function resolveOnce(name){
    const u=`${API}/v1/resolve?q=${encodeURIComponent(name)}&prefer=US`
    const j=await fetch(u).then(r=>r.json())
    if(Array.isArray(j)&&j.length>0)return j[0].code
    return name.toUpperCase()
  }

  async function load(){
    try{
      setBusy(true)
      const code=s||await resolveOnce(q)
      setS(code)
      const u=`${API}/v1/bundle?symbol=${encodeURIComponent(code)}&range=${encodeURIComponent(r)}`
      const j=await fetch(u).then(r=>r.json())
      dataRef.current=j
      draw(j)
    }finally{
      setBusy(false)
    }
  }

  function baseOptions(){
    return{
      animation:false,
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{
        x:{type:"time",ticks:{maxRotation:0,autoSkip:true},grid:{display:false}},
        y:{position:"right",grid:{color:"rgba(0,0,0,0.06)"}}
      }
    }
  }

  function draw(j){
    if(!j||!j.ohlcv)return
    const C=window.Chart
    const t=toDates(j.ohlcv.time)
    const open=j.ohlcv.open||[]
    const high=j.ohlcv.high||[]
    const low=j.ohlcv.low||[]
    const close=j.ohlcv.close||[]
    const ema20=(j.indicators&&j.indicators.ema20)||[]
    const ema50=(j.indicators&&j.indicators.ema50)||[]
    const rsi=(j.indicators&&j.indicators.rsi)||[]
    const stK=(j.indicators&&j.indicators.stochK)||[]
    const stD=(j.indicators&&j.indicators.stochD)||[]
    const macL=(j.indicators&&j.indicators.macdLine)||[]
    const macS=(j.indicators&&j.indicators.macdSignal)||[]
    const macH=(j.indicators&&j.indicators.macdHist)||[]

    let candleOK=false
    try{ C.registry.getController("candlestick"); candleOK=true }catch(_){}

    if(candleOK){
      render("main",{
        type:"candlestick",
        data:{datasets:[
          {label:"px",data:ohlc(t,open,high,low,close)},
          {type:"line",data:xy(t,ema20),borderWidth:1,pointRadius:0},
          {type:"line",data:xy(t,ema50),borderWidth:1,pointRadius:0}
        ]},
        options:baseOptions()
      })
    }else{
      render("main",{
        type:"line",
        data:{labels:t,datasets:[
          {data:close,borderWidth:1,pointRadius:0},
          {data:ema20,borderWidth:1,pointRadius:0},
          {data:ema50,borderWidth:1,pointRadius:0}
        ]},
        options:baseOptions()
      })
    }

    render("rsi",{
      type:"line",
      data:{labels:t,datasets:[{data:rsi,pointRadius:0,borderWidth:1}]},
      options:{...baseOptions(),scales:{...baseOptions().scales,y:{...baseOptions().scales.y,min:0,max:100}}}
    })

    render("stoch",{
      type:"line",
      data:{labels:t,datasets:[
        {data:stK,pointRadius:0,borderWidth:1},
        {data:stD,pointRadius:0,borderWidth:1}
      ]},
      options:{...baseOptions(),scales:{...baseOptions().scales,y:{...baseOptions().scales.y,min:0,max:100}}}
    })

    render("macd",{
      type:"bar",
      data:{labels:t,datasets:[
        {type:"line",data:macL,pointRadius:0,borderWidth:1},
        {type:"line",data:macS,pointRadius:0,borderWidth:1},
        {type:"bar",data:macH}
      ]},
      options:baseOptions()
    })

    const piv=calcPivots(high,low)
    const tlH=lineFromLastTwo(piv.high)
    const tlL=lineFromLastTwo(piv.low)
    const trendHigh=t.map((x,i)=>({x,y:tlH==null?null:tlH.m*i+tlH.b}))
    const trendLow=t.map((x,i)=>({x,y:tlL==null?null:tlL.m*i+tlL.b}))
    render("trend",{
      type:"line",
      data:{datasets:[
        {data:xy(t,close),pointRadius:0,borderWidth:1},
        {data:trendHigh,pointRadius:0,borderWidth:1,borderDash:[6,4]},
        {data:trendLow,pointRadius:0,borderWidth:1,borderDash:[6,4]}
      ]},
      options:baseOptions()
    })
  }

  function calcPivots(h,l){
    const n=h.length
    const left=3,right=3
    const ph=[],pl=[]
    for(let i=0;i<n;i++){
      let okH=true,okL=true
      for(let k=1;k<=left;k++){ if(i-k>=0){ if(h[i]<=h[i-k]) okH=false; if(l[i]>=l[i-k]) okL=false } }
      for(let k=1;k<=right;k++){ if(i+k<n){ if(h[i]<=h[i+k]) okH=false; if(l[i]>=l[i+k]) okL=false } }
      ph.push(okH?i:null)
      pl.push(okL?i:null)
    }
    return{high:ph,low:pl}
  }

  function lineFromLastTwo(idxArr){
    const idx=idxArr.filter(v=>v!=null)
    if(idx.length<2)return null
    const i2=idx[idx.length-1]
    const i1=idx[idx.length-2]
    const y2=dataRef.current.ohlcv.close[i2]
    const y1=dataRef.current.ohlcv.close[i1]
    const m=(y2-y1)/(i2-i1||1)
    const b=y2-m*i2
    return{m,b}
  }

  useEffect(()=>()=>{Object.keys(charts.current).forEach(k=>kill(k))},[])

  return(
    <div style={{padding:"8px"}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} style={{padding:"8px",flex:1}} />
        <button onClick={load} disabled={busy} style={{padding:"8px"}}>load</button>
        <span style={{marginLeft:8}}>{s}</span>
        {["1M","3M","6M","1Y","5Y","MAX"].map(x=><button key={x} onClick={()=>{setR(x); if(s) load()}} style={{padding:"6px"}}>{x}</button>)}
      </div>
      <div style={{display:"grid",gridTemplateRows:"repeat(5,320px)",gap:"8px"}}>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Main</div><canvas ref={cRef.main} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Stoch K/D</div><canvas ref={cRef.stoch} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>RSI</div><canvas ref={cRef.rsi} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>MACD</div><canvas ref={cRef.macd} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Trend</div><canvas ref={cRef.trend} style={{width:"100%",height:"260px"}}/></div>
      </div>
    </div>
  )
}
