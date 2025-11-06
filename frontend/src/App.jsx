import {useEffect,useState} from "react"
const API=import.meta.env.VITE_API_BASE||""
export default function App(){
  const [asof,setAsof]=useState("...")
  useEffect(()=>{fetch(API+"/health").then(r=>r.json()).then(j=>setAsof(j.asof)).catch(()=>setAsof("fail"))},[])
  return <div style={{minHeight:"100vh",display:"grid",placeItems:"center",background:"#0b0c10",color:"#eaecef"}}>OK {asof}</div>
}
