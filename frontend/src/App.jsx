import React,{useEffect,useState} from 'react'
const API = import.meta.env.VITE_API_BASE || ""
export default function App(){
  const [q,setQ]=useState("Apple")
  const [status,setStatus]=useState("-")
  const [rows,setRows]=useState([])
  const go=async()=>{
    setStatus("…")
    try{
      const r=await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}`)
      const data=await r.json()
      setRows(Array.isArray(data)?data:[])
      setStatus("ok")
    }catch{ setStatus("fail") }
  }
  useEffect(()=>{go()},[])
  return(
    <div style={{maxWidth:900,margin:"40px auto",fontFamily:"system-ui"}}>
      <h2>Market Vision Pro <span style={{fontSize:14,marginLeft:8,color:"#666"}}>{status}</span></h2>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16}}>
        <div>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Suche…"/>
          <button onClick={go} style={{marginLeft:8}}>ok</button>
          <pre style={{marginTop:12,whiteSpace:"pre-wrap"}}>{rows.slice(0,5).map(r=>r.name||r.Code||JSON.stringify(r)).join("\n")||"-"}</pre>
        </div>
        <div><div style={{border:"1px solid #ddd",padding:16,minHeight:120}}>-</div></div>
      </div>
    </div>
  )
}
