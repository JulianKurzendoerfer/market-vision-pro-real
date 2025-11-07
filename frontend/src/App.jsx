import {useEffect,useState} from "react"
const API=import.meta.env.VITE_API_BASE||""
export default function App(){
  const [status,setStatus]=useState("…")
  const [sym,setSym]=useState("")
  useEffect(()=>{
    fetch(`${API}/v1/resolve?q=Apple&preferUS=1`).then(r=>r.ok?r.json():Promise.reject(r.status)).then(j=>{
      if(j&&j.ok&&j.rows&&j.rows.length){ setSym(j.rows[0].code); setStatus("ok");}
      else setStatus("fail")
    }).catch(()=>setStatus("fail"))
  },[])
  const Card=({title,children})=>(<div style={{border:"1px solid #ddd",borderRadius:8,padding:12,minHeight:80}}><div style={{fontSize:12,color:"#666"}}>{title}</div><div style={{fontSize:18,marginTop:8}}>{children}</div></div>)
  return (<div style={{maxWidth:900,margin:"40px auto",fontFamily:"system-ui"}}>
    <h2>Market Vision Pro <span style={{fontSize:14,marginLeft:8,color:"#666"}}>{sym} {status}</span></h2>
    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
      <Card title="Preise">-</Card><Card title="Stoch K/D">-</Card>
      <Card title="MACD">-</Card><Card title="EMA20/50">-</Card>
    </div></div>)
}
