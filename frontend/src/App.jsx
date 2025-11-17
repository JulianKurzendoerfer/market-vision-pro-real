import React,{useEffect,useRef,useState}from"react"
import{createChart}from"lightweight-charts"
const fmt=(x)=>x==null?"-":(Math.round(x*100)/100).toString()
function useBundle(range,symbolText){
  const[query,setQuery]=useState(symbolText||"Apple")
  const[symbol,setSymbol]=useState(null)
  const[data,setData]=useState(null)
  const[loading,setLoading]=useState(false)
  const load=async()=>{
    setLoading(true)
    let sym=query.trim()
    try{
      const r=await fetch("/v1/resolve?q="+encodeURIComponent(query))
      const j=await r.json()
      if(Array.isArray(j)&&j.length>0&&j[0].code){sym=j[0].code}
    }catch(e){}
    setSymbol(sym)
    const b=await fetch("/v1/bundle?symbol="+encodeURIComponent(sym))
    const bj=await b.json()
    setData(bj)
    setLoading(false)
  }
  return{query,setQuery,symbol,data,load,loading}
}
function toSec(s){return Math.floor(new Date(s).getTime()/1000)}
function sliceIdx(times,days){
  if(!times||times.length===0)return 0
  if(days==="MAX")return 0
  const end=toSec(times[times.length-1])
  const delta=days*24*3600
  const from=end-delta
  let i=0
  for(let k=0;k<times.length;k++){if(toSec(times[k])>=from){i=k;break}}
  return i
}
function CandleChart({rootId,ohlcv,ema20,ema50,range}){
  const ref=useRef(null)
  useEffect(()=>{
    const el=document.getElementById(rootId)
    if(!el||!ohlcv||ohlcv.time.length===0)return
    el.innerHTML=""
    const chart=createChart(el,{width:el.clientWidth,height:el.clientHeight,rightPriceScale:{visible:true},leftPriceScale:{visible:false},timeScale:{timeVisible:true,secondsVisible:false}})
    const cs=chart.addCandlestickSeries()
    const i0=sliceIdx(ohlcv.time,range)
    const t=ohlcv.time.slice(i0).map(toSec)
    cs.setData(ohlcv.time.slice(i0).map((d,ix)=>({time:t[ix],open:ohlcv.open[i0+ix],high:ohlcv.high[i0+ix],low:ohlcv.low[i0+ix],close:ohlcv.close[i0+ix]})))
    if(ema20){
      const s=chart.addLineSeries({lineWidth:1})
      s.setData(ohlcv.time.slice(i0).map((d,ix)=>({time:t[ix],value:ema20[i0+ix]})))
    }
    if(ema50){
      const s=chart.addLineSeries({lineWidth:1})
      s.setData(ohlcv.time.slice(i0).map((d,ix)=>({time:t[ix],value:ema50[i0+ix]})))
    }
    chart.timeScale().setVisibleRange({from:t[0],to:t[t.length-1]})
    const ro=new ResizeObserver(()=>{chart.applyOptions({width:el.clientWidth,height:el.clientHeight})})
    ro.observe(el)
    return()=>{ro.disconnect();chart.remove()}
  },[rootId,ohlcv,ema20,ema50,range])
  return null
}
function LineChart({rootId,times,vals,bands,range}){
  const ref=useRef(null)
  useEffect(()=>{
    const el=document.getElementById(rootId)
    if(!el||!times||times.length===0)return
    el.innerHTML=""
    const chart=createChart(el,{width:el.clientWidth,height:el.clientHeight,leftPriceScale:{visible:false},rightPriceScale:{visible:true},timeScale:{timeVisible:true,secondsVisible:false}})
    const i0=sliceIdx(times,range)
    const t=times.slice(i0).map(toSec)
    const ls=chart.addLineSeries({lineWidth:1})
    ls.setData(t.map((tt,ix)=>({time:tt,value:vals[i0+ix]})))
    if(bands&&bands.length){
      for(const b of bands){
        const s=chart.addLineSeries({lineWidth:1})
        s.setData(t.map(tt=>({time:tt,value:b})))
      }
    }
    chart.timeScale().setVisibleRange({from:t[0],to:t[t.length-1]})
    const ro=new ResizeObserver(()=>{chart.applyOptions({width:el.clientWidth,height:el.clientHeight})})
    ro.observe(el)
    return()=>{ro.disconnect();chart.remove()}
  },[rootId,times,vals,bands,range])
  return null
}
function MacdChart({rootId,times,macd,signal,hist,range}){
  useEffect(()=>{
    const el=document.getElementById(rootId)
    if(!el||!times||times.length===0)return
    el.innerHTML=""
    const chart=createChart(el,{width:el.clientWidth,height:el.clientHeight,leftPriceScale:{visible:false},rightPriceScale:{visible:true},timeScale:{timeVisible:true,secondsVisible:false}})
    const i0=sliceIdx(times,range)
    const t=times.slice(i0).map(toSec)
    const hs=chart.addHistogramSeries({priceFormat:{type:"price",precision:2,minMove:0.01}})
    hs.setData(t.map((tt,ix)=>({time:tt,value:hist[i0+ix]})))
    const m=chart.addLineSeries({lineWidth:1})
    const s=chart.addLineSeries({lineWidth:1})
    m.setData(t.map((tt,ix)=>({time:tt,value:macd[i0+ix]})))
    s.setData(t.map((tt,ix)=>({time:tt,value:signal[i0+ix]})))
    chart.timeScale().setVisibleRange({from:t[0],to:t[t.length-1]})
    const ro=new ResizeObserver(()=>{chart.applyOptions({width:el.clientWidth,height:el.clientHeight})})
    ro.observe(el)
    return()=>{ro.disconnect();chart.remove()}
  },[rootId,times,macd,signal,hist,range])
  return null
}
function TrendChart({rootId,ohlcv,trend,range}){
  useEffect(()=>{
    const el=document.getElementById(rootId)
    if(!el||!ohlcv||ohlcv.time.length===0)return
    el.innerHTML=""
    const chart=createChart(el,{width:el.clientWidth,height:el.clientHeight,leftPriceScale:{visible:false},rightPriceScale:{visible:true},timeScale:{timeVisible:true,secondsVisible:false}})
    const i0=sliceIdx(ohlcv.time,range)
    const t=ohlcv.time.slice(i0).map(toSec)
    const ls=chart.addLineSeries({lineWidth:1})
    ls.setData(t.map((tt,ix)=>({time:tt,value:ohlcv.close[i0+ix]})))
    if(trend&&trend.pivots&&trend.pivots.length){
      const ms=chart.addLineSeries({lineWidth:0})
      ms.setData(trend.pivots.map(p=>({time:toSec(ohlcv.time[p.i]),value:p.p})))
    }
    if(trend&&trend.lines){
      for(const ln of trend.lines){
        const s=chart.addLineSeries({lineWidth:1})
        s.setData([{time:toSec(ohlcv.time[ln.from.i]),value:ln.from.p},{time:toSec(ohlcv.time[ln.to.i]),value:ln.to.p}])
      }
    }
    chart.timeScale().setVisibleRange({from:t[0],to:t[t.length-1]})
    const ro=new ResizeObserver(()=>{chart.applyOptions({width:el.clientWidth,height:el.clientHeight})})
    ro.observe(el)
    return()=>{ro.disconnect();chart.remove()}
  },[rootId,ohlcv,trend,range])
  return null
}
export default function App(){
  const[r,setR]=useState("1Y")
  const{query,setQuery,symbol,data,load,loading}=useBundle(r,"Apple")
  const t=data?.ohlcv?.time||[]
  const c=data?.ohlcv?.close||[]
  const e20=data?.indicators?.ema20||null
  const e50=data?.indicators?.ema50||null
  const rsi=data?.indicators?.rsi14||null
  const k=data?.indicators?.stochK||null
  const d=data?.indicators?.stochD||null
  const mL=data?.indicators?.macdLine||null
  const mS=data?.indicators?.macdSignal||null
  const mH=data?.indicators?.macdHist||null
  return(
    <div style={{padding:"20px",fontFamily:"system-ui"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        <h2 style={{margin:"0 12px 0 0"}}>Market Vision Pro</h2>
        <input value={query} onChange={e=>setQuery(e.target.value)} style={{padding:"6px 8px"}}/>
        <button onClick={load} disabled={loading} style={{padding:"6px 10px"}}>load</button>
        <span style={{marginLeft:12}}>{symbol||""}</span>
        <div style={{marginLeft:"auto",display:"flex",gap:8}}>
          {["1M","3M","6M","1Y","5Y","MAX"].map(x=>(
            <button key={x} onClick={()=>setR(x==="1M"?30:x==="3M"?90:x==="6M"?180:x==="1Y"?365:x==="5Y"?365*5:"MAX")} style={{padding:"4px 8px"}}>{x}</button>
          ))}
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginTop:16}}>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}>
          <div style={{marginBottom:8}}>Main</div>
          <div id="c1" style={{width:"100%",height:280}}/>
          {data&&<CandleChart rootId="c1" ohlcv={data.ohlcv} ema20={e20} ema50={e50} range={r}/>}
        </div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}>
          <div style={{marginBottom:8}}>Stoch K/D</div>
          <div id="c2" style={{width:"100%",height:280}}/>
          {data&&k&&d&&<LineChart rootId="c2" times={t} vals={k} bands={[80,20]} range={r}/>}
          {data&&k&&d&&<LineChart rootId="c2" times={t} vals={d} bands={[]} range={r}/>}
        </div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}>
          <div style={{marginBottom:8}}>RSI</div>
          <div id="c3" style={{width:"100%",height:260}}/>
          {data&&rsi&&<LineChart rootId="c3" times={t} vals={rsi} bands={[70,30]} range={r}/>}
        </div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}>
          <div style={{marginBottom:8}}>MACD</div>
          <div id="c4" style={{width:"100%",height:260}}/>
          {data&&mL&&mS&&mH&&<MacdChart rootId="c4" times={t} macd={mL} signal={mS} hist={mH} range={r}/>}
        </div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:12}}>
          <div style={{marginBottom:8}}>Trend</div>
          <div id="c5" style={{width:"100%",height:260}}/>
          {data&&<TrendChart rootId="c5" ohlcv={data.ohlcv} trend={data.trend} range={r}/>}
        </div>
      </div>
    </div>
  )
}
