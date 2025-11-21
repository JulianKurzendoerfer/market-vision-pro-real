import {useEffect,useRef,useState} from "react"
import {createChart,CrosshairMode} from "lightweight-charts"

const API=import.meta.env.VITE_API_BASE

function linechart(el,h){const c=createChart(el,{height:h,layout:{textColor:'#222',background:{type:'solid',color:'#fff'}},grid:{vertLines:{color:'#eee'},horzLines:{color:'#eee'}},crosshair:{mode:CrosshairMode.Normal},timeScale:{timeVisible:true,secondsVisible:false}});return c}
function candchart(el,h){const c=linechart(el,h);const s=c.addCandlestickSeries({upColor:"#26a69a",downColor:"#ef5350",borderVisible:false,wickUpColor:"#26a69a",wickDownColor:"#ef5350"});return {c,s}}

export default function App(){
  const [q,setQ]=useState("Apple")
  const [range,setRange]=useState("1Y")
  const [busy,setBusy]=useState(false)
  const roots=useRef({})
  const charts=useRef({})
  const [sym,setSym]=useState("")

  useEffect(()=>()=>Object.values(charts.current).forEach(x=>x?.remove?.()),[])

  async function load(){
    setBusy(true)
    const r1=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`)
    const pick=(await r1.json())[0]
    const symbol=pick?.code||q.toUpperCase()
    setSym(symbol)
    const r=await fetch(`${API}/v1/bundle?symbol=${encodeURIComponent(symbol)}&range=${range}`)
    const b=await r.json()
    draw(b)
    setBusy(false)
  }

  function draw(b){
    Object.values(charts.current).forEach(x=>x?.remove?.())
    charts.current={}
    const h=320
    const o=b?.ohlcv||[]
    const ohlc=o.map(d=>({time:d.t,open:d.o,high:d.h,low:d.l,close:d.c}))
    const t=o.map(d=>d.t)

    const r1=candchart(roots.current.c1,h); r1.s.setData(ohlc)
    if(b?.indicators?.ema20&&b?.indicators?.ema50){
      const ema20=r1.c.addLineSeries({lineWidth:2}); ema20.setData(b.indicators.ema20.map((v,i)=>({time:t[i],value:v})))
      const ema50=r1.c.addLineSeries({lineWidth:2}); ema50.setData(b.indicators.ema50.map((v,i)=>({time:t[i],value:v})))
    }
    charts.current.c1=r1.c

    const c2=linechart(roots.current.c2,h)
    if(b?.indicators?.stockK&&b?.indicators?.stockD){
      const k=c2.addLineSeries({lineWidth:2}); k.setData(b.indicators.stockK.map((v,i)=>({time:t[i],value:v})))
      const d=c2.addLineSeries({lineWidth:2}); d.setData(b.indicators.stockD.map((v,i)=>({time:t[i],value:v})))
      c2.priceScale("right").applyOptions({autoScale:true})
    }
    charts.current.c2=c2

    const c3=linechart(roots.current.c3,h)
    if(b?.indicators?.rsi){
      const r=c3.addLineSeries({lineWidth:2}); r.setData(b.indicators.rsi.map((v,i)=>({time:t[i],value:v})))
    }
    charts.current.c3=c3

    const c4=linechart(roots.current.c4,h)
    if(b?.indicators?.macdLine&&b?.indicators?.macdSignal&&b?.indicators?.macdHist){
      const l=c4.addLineSeries({lineWidth:2}); l.setData(b.indicators.macdLine.map((v,i)=>({time:t[i],value:v})))
      const s=c4.addLineSeries({lineWidth:2}); s.setData(b.indicators.macdSignal.map((v,i)=>({time:t[i],value:v})))
      const hst=c4.addHistogramSeries({base:0}); hst.setData(b.indicators.macdHist.map((v,i)=>({time:t[i],value:v})))
    }
    charts.current.c4=c4

    const c5=linechart(roots.current.c5,h)
    let pivH=b?.indicators?.pivotsH, pivL=b?.indicators?.pivotsL
    if(!pivH||!pivL){
      const ph=[],pl=[]
      for(let i=2;i<ohlc.length-2;i++){
        const a=ohlc[i]
        if(a.high>ohlc[i-1].high&&a.high>ohlc[i+1].high) ph.push({time:a.time,value:a.high})
        if(a.low<ohlc[i-1].low&&a.low<ohlc[i+1].low) pl.push({time:a.time,value:a.low})
      }
      pivH=ph; pivL=pl
    }
    const hs=c5.addScatterSeries?c5.addScatterSeries({}) : c5.addLineSeries({lineWidth:0})
    const ls=c5.addScatterSeries?c5.addScatterSeries({}) : c5.addLineSeries({lineWidth:0})
    hs.setData(pivH.slice(-100))
    ls.setData(pivL.slice(-100))
    const last2H=pivH.slice(-2), last2L=pivL.slice(-2)
    if(last2H.length===2){const tl=c5.addLineSeries({lineWidth:2}); tl.setData(last2H)}
    if(last2L.length===2){const tl2=c5.addLineSeries({lineWidth:2}); tl2.setData(last2L)}
    charts.current.c5=c5
  }

  return (
    <div style={{padding:16}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} style={{padding:"6px 8px",border:"1px solid #ddd",borderRadius:8,minWidth:200}}/>
        <button onClick={load} disabled={busy} style={{padding:"6px 12px",border:"1px solid #ddd",borderRadius:8}}>{busy?"...":"load"}</button>
        <span style={{marginLeft:8}}>{sym}</span>
        <div style={{marginLeft:"auto",display:"flex",gap:6}}>
          {["1M","3M","6M","1Y","5Y","MAX"].map(r=><button key={r} onClick={()=>setRange(r)} style={{padding:"4px 10px",border:"1px solid #ddd",borderRadius:8,background:range===r?"#f2f2f2":"#fff"}}>{r}</button>)}
        </div>
      </div>
      <div style={{display:"grid",gridTemplateRows:"repeat(5, 320px)",gap:16}}>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}><div style={{fontWeight:600,marginBottom:8}}>Main</div><div ref={el=>roots.current.c1=el} style={{width:"100%",height:"100%"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}><div style={{fontWeight:600,marginBottom:8}}>Stoch K/D</div><div ref={el=>roots.current.c2=el} style={{width:"100%",height:"100%"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}><div style={{fontWeight:600,marginBottom:8}}>RSI</div><div ref={el=>roots.current.c3=el} style={{width:"100%",height:"100%"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}><div style={{fontWeight:600,marginBottom:8}}>MACD</div><div ref={el=>roots.current.c4=el} style={{width:"100%",height:"100%"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}><div style={{fontWeight:600,marginBottom:8}}>Trend</div><div ref={el=>roots.current.c5=el} style={{width:"100%",height:"100%"}}/></div>
      </div>
    </div>
  )
}
