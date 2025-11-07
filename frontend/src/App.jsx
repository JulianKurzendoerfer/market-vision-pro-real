import { useEffect, useState } from "react"
const API=import.meta.env.VITE_API_BASE||""
function ema(a,n){let k=2/(n+1),e=[];let p=a[0];for(let i=0;i<a.length;i++){let v=i===0?p:(a[i]-p)*k+p;e.push(v);p=v}return e}
function rsi(a,n=14){let g=0,l=0;for(let i=1;i<=n;i++){let d=a[i]-a[i-1];g+=d>0?d:0;l+=d<0?-d:0}g/=n;l/=n;let rs=g/(l||1e-9);let r=[100-100/(1+rs)];for(let i=n+1;i<a.length;i++){let d=a[i]-a[i-1];g=(g*(n-1)+(d>0?d:0))/n;l=(l*(n-1)+(d<0?-d:0))/n;rs=g/(l||1e-9);r.push(100-100/(1+rs))}return Array(a.length-n).fill(0).concat(r)}
function sma(a,n){let r=[];let s=0;for(let i=0;i<a.length;i++){s+=a[i];if(i>=n)s-=a[i-n];r.push(i>=n-1?s/n:0)}return r}
function stoch(h,l,c,n=14,k=3){let K=[];for(let i=0;i<c.length;i++){let hs=-1e9,ls=1e9;for(let j=Math.max(0,i-n+1);j<=i;j++){hs=Math.max(hs,h[j]);ls=Math.min(ls,l[j])}K.push(hs>ls?100*(c[i]-ls)/(hs-ls):0)}let D=sma(K,k);return {K,D}}
function macd(a,f=12,s=26,st=9){let e12=ema(a,f),e26=ema(a,s);let m=a.map((_,i)=>e12[i]-e26[i]);let sig=ema(m,st);let h=m.map((v,i)=>v-sig[i]);return {m,sig,h}}
function Card({title,children}){return <div style={{border:"1px solid #ddd",borderRadius:8,padding:16,minHeight:80}}><div style={{fontSize:14,color:"#666"}}>{title}</div><div style={{fontSize:18,marginTop:8}}>{children}</div></div>}
export default function App(){
  const [q,setQ]=useState("Apple"); const [s,setS]=useState(""); const [rows,setRows]=useState([])
  async function go(){
    try{
      const r=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`).then(r=>r.json())
      const best=r&&r.length?r[0].code||r[0].Code||r[0].symbol||"AAPL":"AAPL"
      setS(best)
      const o=await fetch(`${API}/v1/ohlcv?symbol=${encodeURIComponent(best)}`).then(r=>r.json())
      setRows(o.rows||[])
    }catch(e){setRows([])}
  }
  useEffect(()=>{go()},[])
  const o=rows.length?rows:[]; const c=o.map(x=>x.c); const h=o.map(x=>x.h); const l=o.map(x=>x.l)
  const p=c.length?c[c.length-1]:null
  const e20=c.length?ema(c,20).at(-1):null
  const e50=c.length?ema(c,50).at(-1):null
  const r=rsi(c); const r14=r.length?r[r.length-1]:null
  const st=stoch(h,l,c); const kVal=st.K.length?st.K.at(-1):null; const dVal=st.D.length?st.D.at(-1):null
  const m=macd(c); const macdLine=m.m.length?m.m.at(-1):null; const macdSig=m.sig.length?m.sig.at(-1):null; const macdHist=m.h.length?m.h.at(-1):null
  return (
    <div style={{maxWidth:1000,margin:"24px auto",padding:"0 16px"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        <input value={q} onChange={e=>setQ(e.target.value)} style={{padding:"6px 8px"}}/>
        <button onClick={go}>ok</button>
        <div style={{marginLeft:"auto"}}>{s||""}</div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16,marginTop:16}}>
        <Card title="Preise">{p!=null?`${p.toFixed(2)} USD`:"-"}</Card>
        <Card title="Stoch K/D">{kVal!=null&&dVal!=null?`${kVal.toFixed(1)} / ${dVal.toFixed(1)}`:"-"}</Card>
        <Card title="RSI">{r14!=null?r14.toFixed(1):"-"}</Card>
        <Card title="MACD">{macdLine!=null&&macdSig!=null?`${macdLine.toFixed(2)} / ${macdSig.toFixed(2)} (${macdHist.toFixed(2)})`:"-"}</Card>
        <Card title="EMA20/50">{e20!=null&&e50!=null?`${e20.toFixed(2)} / ${e50.toFixed(2)}`:"-"}</Card>
        <Card title="Optionen später">-</Card>
      </div>
    </div>
  )
}
