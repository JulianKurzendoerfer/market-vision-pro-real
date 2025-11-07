import { useState } from "react";

const API = import.meta.env.VITE_API_BASE; // z.B. https://market-vision-pro-real.onrender.com

function Card({ title, children }) {
  return (
    <div style={{border:"1px solid #ddd", borderRadius:10, padding:18, minHeight:110}}>
      <div style={{fontSize:13, color:"#666"}}>{title}</div>
      <div style={{fontSize:28, marginTop:10}}>{children}</div>
    </div>
  );
}

export default function App() {
  const [q, setQ] = useState("Apple");
  const [symbol, setSymbol] = useState(null);
  const [status, setStatus] = useState("ok");
  const [price, setPrice] = useState(null);
  const [rsi, setRsi] = useState(null);
  const [stoch, setStoch] = useState({ k: null, d: null });
  const [macd, setMacd] = useState({ line: null, signal: null });
  const [ema, setEma] = useState({ e20: null, e50: null });

  async function load() {
    try {
      setStatus("load");

      // 1) Symbol auflösen (bevorzugt US)
      const resResolve = await fetch(`${API}/v1/resolve?q=${encodeURIComponent(q)}&prefer=US`);
      const candidates = await resResolve.json();
      const sy = (Array.isArray(candidates) && candidates[0]?.code) ? candidates[0].code : "AAPL";
      setSymbol(sy);

      // 2) Daten holen (OHLCV + Indikatoren)
      const [ohlcv, ind] = await Promise.all([
        fetch(`${API}/v1/ohlcv?symbol=${sy}`).then(r => r.json()),
        fetch(`${API}/v1/indicators?symbol=${sy}`).then(r => r.json()),
      ]);

      // 3) Felder mappen
      const last = Array.isArray(ohlcv) && ohlcv.length ? ohlcv[ohlcv.length - 1] : null;
      setPrice(last?.close ?? null);

      setRsi(ind?.rsi ?? null);
      setStoch({ k: ind?.stochK ?? null, d: ind?.stochD ?? null });
      setMacd({ line: ind?.macdLine ?? null, signal: ind?.macdSignal ?? null });
      setEma({ e20: ind?.ema20 ?? null, e50: ind?.ema50 ?? null });

      setStatus("ok");
    } catch (e) {
      console.error(e);
      setStatus("fail");
    }
  }

  return (
    <div style={{maxWidth:1100, margin:"40px auto", fontFamily:"system-ui"}}>
      <h2>Market Vision Pro <span style={{fontSize:14, marginLeft:8, color:"#666"}}>{status}</span></h2>

      <div style={{display:"flex", gap:8, alignItems:"center"}}>
        <input
          style={{padding:"6px 10px"}}
          value={q}
          onChange={(e)=>setQ(e.target.value)}
          placeholder="Apple"
        />
        <button onClick={load}>ok</button>
        <button onClick={load}>load</button>
        {symbol && <span style={{marginLeft:12, color:"#666"}}>{symbol}</span>}
      </div>

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:18, marginTop:18}}>
        <Card title="Preise">
          {price!=null ? `${price.toFixed(2)} USD` : "- USD"}
        </Card>

        <Card title="Stoch K/D">
          {(stoch.k!=null && stoch.d!=null) ? `${stoch.k.toFixed(1)} / ${stoch.d.toFixed(1)}` : "- / -"}
        </Card>

        <Card title="RSI">
          {rsi!=null ? rsi.toFixed(1) : "-"}
        </Card>

        <Card title="MACD">
          {(macd.line!=null && macd.signal!=null) ? `${macd.line.toFixed(2)} / ${macd.signal.toFixed(2)}` : "- / -"}
        </Card>

        <Card title="EMA20/50">
          {(ema.e20!=null && ema.e50!=null) ? `${ema.e20.toFixed(2)} / ${ema.e50.toFixed(2)}` : "- / -"}
        </Card>
      </div>
    </div>
  );
}
