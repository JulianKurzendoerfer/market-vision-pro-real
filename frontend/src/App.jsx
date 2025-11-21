import {useEffect,useRef,useState} from "react"

const API=import.meta.env.VITE_API_BASE
function toTs(s){return new Date(s).getTime()}
function ema(arr,p){let k=2/(p+1),out=new Array(arr.length).fill(null);let s=0,c=0;for(let i=0;i<arr.length;i++){let v=arr[i];if(v==null)continue;if(c<p){s+=v;c++;if(c===p){out[i]=s/p}}else{out[i]=v*k+out[i-1]*(1-k)}}return out}
function rsi(arr,p=14){let out=new Array(arr.length).fill(null);let gain=0,loss=0,prev=null;let up=0,down=0;for(let i=0;i<arr.length;i++){let v=arr[i];if(prev==null){prev=v}else{let ch=v-prev;prev=v;if(i<=p){if(ch>0){gain+=ch}else{loss-=Math.min(ch,0)}if(i===p){up=gain/p;down=loss/p;out[i]=down===0?100:100-100/(1+up/down)}}else{up=(up*(p-1)+(ch>0?ch:0))/p;down=(down*(p-1)+(ch<0?-ch:0))/p;out[i]=down===0?100:100-100/(1+up/down)}}}return out}
function stoch(h,l,c,kp=14,dp=3){let k=new Array(c.length).fill(null),d=new Array(c.length).fill(null);for(let i=0;i<c.length;i++){if(i<kp-1)continue;let hh=-1e99,ll=1e99;for(let j=i-kp+1;j<=i;j++){if(h[j]>hh)hh=h[j];if(l[j]<ll)ll=l[j]}k[i]=((c[i]-ll)/(hh-ll))*100}for(let i=0;i<c.length;i++){if(i<kp-1+dp-1)continue;let s=0;for(let j=i-dp+1;j<=i;j++){s+=k[j]}d[i]=s/dp}return {k,d}}
function macd(arr,fast=12,slow=26,signal=9){let f=ema(arr,fast),s=ema(arr,slow);let line=arr.map((_,i)=>f[i]==null||s[i]==null?null:f[i]-s[i]);let sig=ema(line.filter(v=>v!=null),signal);let sigSeries=new Array(arr.length).fill(null);let idx=0;for(let i=0;i<arr.length;i++){if(line[i]!=null){sigSeries[i]=sig[idx++]} }let hist=line.map((_,i)=>line[i]==null||sigSeries[i]==null?null:line[i]-sigSeries[i]);return {line,sig:sigSeries,hist}}
function pivots(close,w=5){let n=close.length;let ph=new Array(n).fill(null),pl=new Array(n).fill(null);for(let i=w;i<n-w;i++){let v=close[i];let hi=true,lo=true;for(let j=i-w;j<=i+w;j++){if(close[j]>v)lo=false;if(close[j]<v)hi=false}if(hi)ph[i]=v;if(lo)pl[i]=v}let trend=new Array(n).fill(null);let last=null;for(let i=0;i<n;i++){if(ph[i]!=null||pl[i]!=null){if(last==null){last=i}else{trend[last]= (ph[last]!=null?ph[last]:pl[last]);trend[i]= (ph[i]!=null?ph[i]:pl[i]);last=i}}}return {ph,pl,trend}}
function useChart(ref,config){const inst=useRef(null);useEffect(()=>{if(!ref.current)return;if(inst.current){inst.current.destroy()}inst.current=new Chart(ref.current.getContext("2d"),config());return ()=>{if(inst.current){inst.current.destroy();inst.current=null}}},[ref,config]);return inst}

export default function App(){
  const [q,setQ]=useState("Apple")
  const [busy,setBusy]=useState(false)
  const [range,setRange]=useState("1Y")
  const cMain=useRef(null),cRSI=useRef(null),cStoch=useRef(null),cMACD=useRef(null),cTrend=useRef(null)
  const dataRef=useRef(null)

  async function load(){
    if(busy)return
    setBusy(true)
    try{
      const r=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`)
      const picks=await r.json()
      const symbol=(picks[0]?.code)||q
      const b=await fetch(`${API}/v1/bundle?symbol=${encodeURIComponent(symbol)}&range=${encodeURIComponent(range)}`)
      const j=await b.json()
      const t=j.ohlcv.time.map(toTs)
      const open=j.ohlcv.open,high=j.ohlcv.high,low=j.ohlcv.low,close=j.ohlcv.close,vol=j.ohlcv.volume
      let rsiSeries=j.indicators?.rsi, kSeries=j.indicators?.stochK, dSeries=j.indicators?.stochD, macdLine=j.indicators?.macdLine, macdSig=j.indicators?.macdSignal, e20=j.indicators?.ema20, e50=j.indicators?.ema50
      if(!e20||e20.every(v=>v==null)) e20=ema(close,20)
      if(!e50||e50.every(v=>v==null)) e50=ema(close,50)
      if(!rsiSeries||rsiSeries.every(v=>v==null)) rsiSeries=rsi(close,14)
      if(!kSeries||!dSeries||kSeries.every(v=>v==null)||dSeries.every(v=>v==null)){let sd=stoch(high,low,close,14,3);kSeries=sd.k;dSeries=sd.d}
      if(!macdLine||!macdSig||macdLine.every(v=>v==null)||macdSig.every(v=>v==null)){let m=macd(close,12,26,9);macdLine=m.line;macdSig=m.sig}
      const macdHist=macdLine.map((v,i)=>v==null||macdSig[i]==null?null:v-macdSig[i])
      const pv=pivots(close,5)
      dataRef.current={t,open,high,low,close,vol,e20,e50,rsi:rsiSeries,stochK:kSeries,stochD:dSeries,macdLine,macdSig,macdHist,trend:pv.trend,ph:pv.ph,pl:pv.pl}
      renderAll()
    }catch(e){
      console.error(e)
    }finally{
      setBusy(false)
    }
  }

  function renderAll(){
    const d=dataRef.current
    if(!d)return

    const mainCfg=()=>({
      type:"line",
      data:{labels:d.t,datasets:[
        {type:"candlestick",label:"C",data:d.open.map((_,i)=>({x:d.t[i],o:d.open[i],h:d.high[i],l:d.low[i],c:d.close[i]})),yAxisID:"y1"},
        {type:"line",label:"EMA20",data:d.e20.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0,yAxisID:"y1"},
        {type:"line",label:"EMA50",data:d.e50.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0,yAxisID:"y1"},
      ]},
      options:{responsive:true,plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{type:"time",time:{unit:"day"}},y1:{position:"right"}},elements:{point:{radius:0}}}
    })
    const rsiCfg=()=>({
      type:"line",
      data:{labels:d.t,datasets:[
        {data:d.rsi.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
        {data:d.t.map(x=>({x,y:70})),borderWidth:1,pointRadius:0,borderDash:[4,4]},
        {data:d.t.map(x=>({x,y:30})),borderWidth:1,pointRadius:0,borderDash:[4,4]},
      ]},
      options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{type:"time"},y:{min:0,max:100}},elements:{point:{radius:0}}}
    })
    const stochCfg=()=>({
      type:"line",
      data:{labels:d.t,datasets:[
        {data:d.stochK.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
        {data:d.stochD.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
        {data:d.t.map(x=>({x,y:80})),borderWidth:1,pointRadius:0,borderDash:[4,4]},
        {data:d.t.map(x=>({x,y:20})),borderWidth:1,pointRadius:0,borderDash:[4,4]},
      ]},
      options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{type:"time"},y:{min:0,max:100}},elements:{point:{radius:0}}}
    })
    const macdCfg=()=>({
      data:{labels:d.t,datasets:[
        {type:"bar",data:d.macdHist.map((v,i)=>v==null?null:{x:d.t[i],y:v}),barPercentage:1,categoryPercentage:1},
        {type:"line",data:d.macdLine.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
        {type:"line",data:d.macdSig.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
      ]},
      options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{type:"time"},y:{}},elements:{point:{radius:0}}}
    })
    const trendCfg=()=>({
      type:"line",
      data:{labels:d.t,datasets:[
        {data:d.close.map((v,i)=>({x:d.t[i],y:v})),borderWidth:1,pointRadius:0},
        {data:d.trend.map((v,i)=>v==null?null:{x:d.t[i],y:v}),borderWidth:1,pointRadius:0},
      ]},
      options:{plugins:{legend:{display:false},tooltip:{enabled:false}},scales:{x:{type:"time"},y:{}},elements:{point:{radius:0}},spanGaps:true}
    })

    useChart(cMain,mainCfg)
    useChart(cRSI,rsiCfg)
    useChart(cStoch,stochCfg)
    useChart(cMACD,macdCfg)
    useChart(cTrend,trendCfg)
  }

  useEffect(()=>{},[])
  return (
    <div style={{padding:"8px"}}>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}>
        <input placeholder="Apple" value={q} onChange={e=>setQ(e.target.value)} style={{padding:"8px"}}/>
        <button onClick={load} disabled={busy} style={{padding:"8px"}}>{busy?"...":"load"}</button>
        <span style={{marginLeft:8}}>↔</span>
        {["1M","3M","6M","1Y","5Y","MAX"].map(r=>(
          <button key={r} onClick={()=>{setRange(r);load()}} style={{padding:"6px"}}>{r}</button>
        ))}
      </div>
      <div style={{display:"grid",gridTemplateRows:"repeat(5, 320px)",gap:"12px"}}>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Main</div><canvas ref={cMain} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Stoch K/D</div><canvas ref={cStoch} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>RSI</div><canvas ref={cRSI} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>MACD</div><canvas ref={cMACD} style={{width:"100%",height:"260px"}}/></div>
        <div style={{border:"1px solid #ddd",borderRadius:8,padding:8}}><div>Trend</div><canvas ref={cTrend} style={{width:"100%",height:"260px"}}/></div>
      </div>
    </div>
  )
}
