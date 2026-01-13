import { useEffect, useMemo, useState } from "react"

export default function App() {
  const apiBase = useMemo(() => {
    const v = import.meta.env.VITE_API_BASE
    return (v && v.trim()) ? v.trim().replace(/\/+$/, "") : ""
  }, [])

  const [health, setHealth] = useState(null)
  const [ping, setPing] = useState(null)
  const [err, setErr] = useState("")

  useEffect(() => {
    const run = async () => {
      setErr("")
      try {
        const h = await fetch(`${apiBase}/health`)
        const hj = await h.json()
        setHealth(hj)
      } catch (e) {
        setErr(String(e))
      }
      try {
        const p = await fetch(`${apiBase}/api/ping`)
        const pj = await p.json()
        setPing(pj)
      } catch (e) {
        setErr(prev => (prev ? prev : String(e)))
      }
    }
    run()
  }, [apiBase])

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Arial", padding: 24 }}>
      <h1>MVP Frontend</h1>
      <div style={{ marginTop: 12 }}>
        <div><b>API_BASE</b>: {apiBase}</div>
        <div style={{ marginTop: 12 }}><b>/health</b>: {health ? JSON.stringify(health) : "-"}</div>
        <div style={{ marginTop: 12 }}><b>/api/ping</b>: {ping ? JSON.stringify(ping) : "-"}</div>
        {err ? <div style={{ marginTop: 12, color: "crimson" }}><b>Fehler</b>: {err}</div> : null}
      </div>
    </div>
  )
}
