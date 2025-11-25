import {useEffect,useState} from "react"
export default function App(){
  const [msg,setMsg]=useState("loading...")
  useEffect(()=>{fetch(`${import.meta.env.VITE_API_BASE}/health`).then(r=>r.json()).then(j=>setMsg(JSON.stringify(j))).catch(e=>setMsg(String(e)))},[])
  return <div style={{fontFamily:"Inter,system-ui",padding:24}}>
    <h1>Market Vision Pro</h1>
    <p>Backend: {msg}</p>
    <button onClick={()=>{fetch(`${import.meta.env.VITE_API_BASE}/v1/bundle?symbol=AAPL&range=1Y`).then(r=>r.json()).then(j=>alert(j.ok?"OK":"ERR"))}}>Test /v1/bundle</button>
  </div>
}
