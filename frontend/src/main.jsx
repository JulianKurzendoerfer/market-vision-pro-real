import React, { useState } from "react"
import { createRoot } from "react-dom/client"
import App from "./App.jsx"

const U = "Julian08527"
const P = "Ju08527"

function Root() {
  const [ok, setOk] = useState(() => sessionStorage.getItem("auth") === "1")
  const [u, setU] = useState("")
  const [p, setP] = useState("")
  const [err, setErr] = useState(false)

  if (ok) return <App />

  const login = () => {
    if (u === U && p === P) { sessionStorage.setItem("auth","1"); setOk(true) }
    else { setErr(true); setTimeout(() => setErr(false), 2000) }
  }

  return (
    <div style={{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#0b0f19"}}>
      <div style={{background:"#111827",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"12px",padding:"40px",width:"320px"}}>
        <h2 style={{color:"#e2e8f0",textAlign:"center",marginBottom:"8px",fontSize:"22px",fontWeight:"700"}}>Market Vision Pro</h2>
        <p style={{color:"#64748b",textAlign:"center",marginBottom:"28px",fontSize:"13px"}}>Bitte anmelden</p>
        <input type="text" placeholder="Benutzername" value={u} onChange={e=>setU(e.target.value)} onKeyDown={e=>e.key==="Enter"&&login()} style={{width:"100%",padding:"10px 14px",marginBottom:"12px",background:"#1e293b",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",color:"#e2e8f0",fontSize:"14px",boxSizing:"border-box",outline:"none"}} />
        <input type="password" placeholder="Passwort" value={p} onChange={e=>setP(e.target.value)} onKeyDown={e=>e.key==="Enter"&&login()} style={{width:"100%",padding:"10px 14px",marginBottom:"16px",background:"#1e293b",border:"1px solid rgba(255,255,255,0.1)",borderRadius:"8px",color:"#e2e8f0",fontSize:"14px",boxSizing:"border-box",outline:"none"}} />
        {err && <p style={{color:"#ef4444",textAlign:"center",fontSize:"13px",marginBottom:"12px"}}>Falsche Zugangsdaten</p>}
        <button onClick={login} style={{width:"100%",padding:"11px",background:"#1d4ed8",border:"none",borderRadius:"8px",color:"white",fontSize:"15px",fontWeight:"600",cursor:"pointer"}}>Anmelden</button>
      </div>
    </div>
  )
}

createRoot(document.getElementById("root")).render(<Root />)
