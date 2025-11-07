import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE || "";

function Card({ title, children }) {
  return (
    <div style={{border:"1px solid #ddd", borderRadius:8, padding:16, minHeight:80, margin:8}}>
      <div style={{fontSize:14, color:"#666"}}>{title}</div>
      <div style={{fontSize:18, marginTop:8}}>{children ?? "-"}</div>
    </div>
  );
}

export default function App() {
  const [q, setQ] = useState("Apple");
  const [suggest, setSuggest] = useState([]);
  const [symbol, setSymbol] = useState(null);
  const [status, setStatus] = useState("ok");

  const [price, setPrice] = useState(null);
  const [rsi, setRsi] = useState(null);
  const [ema20, setEma20] = useState(null);
  const [ema50, setEma50] = useState(null);
  const [macdL, setMacdL] = useState(null);
  const [macdS, setMacdS] = useState(null);
  const [stochK, setStochK] = useState(null);
  const [stochD, setStochD] = useState(null);

  async function loadSuggest(qq) {
    try {
      const r = await fetch(`${API}/v1/resolve?q=${encodeURIComponent(qq)}&prefer=US`);
      const j = await r.json();
      setSuggest(Array.isArray(j) ? j : []);
    } catch {
      setSuggest([]);
    }
  }

  async function loadData(code) {
    setStatus("…");
    try {
      const [r1, r2] = await Promise.all([
        fetch(`${API}/v1/ohlcv?symbol=${encodeURIComponent(code)}`),
        fetch(`${API}/v1/indicators?symbol=${encodeURIComponent(code)}`)
      ]);
      const ohlcv = await r1.json();
      const ind = await r2.json();

      const rows = Array.isArray(ohlcv?.rows) ? ohlcv.rows : [];
      const last = rows.length ? rows[rows.length - 1] : null;

      setPrice(last?.close ?? null);
      setRsi(ind?.rsi ?? null);
      setEma20(ind?.ema20 ?? null);
      setEma50(ind?.ema50 ?? null);
      setMacdL(ind?.macdLine ?? null);
      setMacdS(ind?.macdSignal ?? null);
      setStochK(ind?.stochK ?? ind?.stock ?? null);
      setStochD(ind?.stochD ?? null);

      setStatus("ok");
    } catch {
      setStatus("fail");
    }
  }

  useEffect(() => { loadSuggest(q); }, []);

  function onOK() {
    const code = suggest?.[0]?.code || suggest?.[0]?.symbol || q.trim();
    setSymbol(code);
    if (code) loadData(code);
  }

  return (
    <div style={{maxWidth:980, margin:"48px auto", fontFamily:"system-ui"}}>
      <h2>Market Vision Pro <span style={{fontSize:14, marginLeft:8, color:"#666"}}>{status}</span></h2>

      <div>
        <input value={q} onChange={e=>setQ(e.target.value)} style={{padding:"6px 8px"}} />
        <button onClick={onOK} style={{marginLeft:8, padding:"6px 10px"}}>ok</button>
        <span style={{marginLeft:12}}>{symbol || ""}</span>
      </div>

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginTop:16}}>
        <div>
          {suggest.slice(0,8).map((s,i)=>(
            <div key={i} style={{cursor:"pointer"}} onClick={()=>{setSymbol(s.code||s.symbol); loadData(s.code||s.symbol);}}>
              {(s.name||"").slice(0,48)}
            </div>
          ))}
        </div>

        <div>
          <Card title="Preise">{price!=null ? `${price.toFixed(2)} USD` : "-"}</Card>
          <Card title="Stoch K/D">
            {(stochK!=null && stochD!=null) ? `K ${stochK.toFixed(1)} / D ${stochD.toFixed(1)}` : "-"}
          </Card>
          <Card title="RSI">{rsi!=null ? rsi.toFixed(1) : "-"}</Card>
          <Card title="MACD">{(macdL!=null && macdS!=null) ? `${macdL.toFixed(2)} / ${macdS.toFixed(2)}` : "-"}</Card>
          <Card title="EMA20/50">
            {(ema20!=null && ema50!=null) ? `${ema20.toFixed(2)} / ${ema50.toFixed(2)}` : "-"}
          </Card>
          <Card title="Optionen später">-</Card>
        </div>
      </div>
    </div>
  );
}
