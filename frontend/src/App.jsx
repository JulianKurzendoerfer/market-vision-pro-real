import { useEffect, useState } from "react"
export default function App(){
  const [status,setStatus]=useState("loading...")
  const [sample,setSample]=useState([])
  const api=import.meta.env.VITE_API_BASE
  useEffect(()=>{
    fetch(`${api}/health`).then(r=>r.json()).then(()=>setStatus("ok")).catch(()=>setStatus("down"))
    fetch(`${api}/v1/bundle?symbol=AAPL&range=1y&interval=1d`).then(r=>r.json()).then(j=>setSample(j.ohlc?.slice(0,3)||[])).catch(()=>setSample([]))
  },[])
  return (<div style={{fontFamily:"Inter,system-ui",padding:24}}>
    <h1>Market Vision Pro</h1>
    <p>Backend: {status}</p>
    <pre>{JSON.stringify(sample,null,2)}</pre>
    <button onClick={async()=>{
      const r=await fetch(`${api}/v1/compute`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({symbol:"AAPL",range:"1y",interval:"1d"})})
      const j=await r.json(); alert(j.ok?`RSI: ${j.indicators.at(-1).RSI.toFixed(2)}`:"compute failed")
    }}>Compute</button>
  </div>)
}
