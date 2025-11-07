import {useEffect,useState} from "react"
const API=import.meta.env.VITE_API_BASE||""

function Card({title,children}){return(<div style={{border:"1px solid #ddd",borderRadius:8,padding:18,minHeight:110,display:"flex",flexDirection:"column",justifyContent:"space-between"}}><div style={{fontSize:14,color:"#666"}}>{title}</div><div style={{fontSize:28}}>{children}</div></div>)}

export default function App(){
  const [q,setQ]=useState("Apple")
  const [code,setCode]=useState("")
  const [price,setPrice]=useState(null)
  const [k,setK]=useState(null)
  const [d,setD]=useState(null)
  const [rsi,setRsi]=useState(null)
  const [m1,setM1]=useState(null)
  const [m2,setM2]=useState(null)
  const [e20,setE20]=useState(null)
  const [e50,setE50]=useState(null)

  async function load(symbol){
    const r=await fetch(`${API}/v1/indicators?symbol=${encodeURIComponent(symbol)}`)
    const j=await r.json()
    setPrice(j.price??null); setRsi(j.rsi??null); setK(j.stoch_k??null); setD(j.stoch_d??null); setM1(j.macd_line??null); setM2(j.macd_signal??null); setE20(j.ema20??null); setE50(j.ema50??null)
  }
  async function resolveAndLoad(){
    const r=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`)
    const j=await r.json()
    const c=(j&&j.length)?j[0].code:q
    setCode(c); await load(c)
  }
  useEffect(()=>{resolveAndLoad()},[])

  return (
    <div style={{maxWidth:1100,margin:"36px auto",fontFamily:"system-ui"}}>
      <h2>Market Vision Pro <span style={{fontSize:14,marginLeft:8,color:"#666"}}>ok</span></h2>
      <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:16}}>
        <input value={q} onChange={e=>setQ(e.target.value)} style={{padding:"6px 8px"}} />
        <button onClick={resolveAndLoad}>ok</button>
        <button onClick={()=>code&&load(code)}>load</button>
        <span style={{marginLeft:12}}>{code}</span>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18}}>
        <Card title="Preise">{price==null? "- USD": `${price.toFixed(2)} USD`}</Card>
        <Card title="Stoch K/D">{(k==null||d==null)?"- / -":`${k.toFixed(1)} / ${d.toFixed(1)}`}</Card>
        <Card title="RSI">{rsi==null?"-":rsi.toFixed(1)}</Card>
        <Card title="MACD">{(m1==null||m2==null)?"- / -":`${m1.toFixed(2)} / ${m2.toFixed(2)}`}</Card>
        <Card title="EMA20/50">{(e20==null||e50==null)?"- / -":`${e20.toFixed(2)} / ${e50.toFixed(2)}`}</Card>
      </div>
    </div>
  )
}
