import os
from datetime import date, timedelta
import math
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

EODHD_BASE = "https://eodhd.com/api"

def _key() -> str:
    k = os.getenv("EODHD_API_KEY") or os.getenv("EODHD_TOKEN")
    if not k:
        raise HTTPException(status_code=500, detail="Missing EODHD_API_KEY env var")
    return k

def _get(path: str, params: dict):
    params = {**params, "api_token": _key(), "fmt": "json"}
    r = requests.get(f"{EODHD_BASE}/{path}", params=params, timeout=40)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"EODHD error {r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="EODHD returned non-JSON response")

def _get_fundamentals(symbol: str):
    return _get(f"fundamentals/{symbol}", {})

def _ipo_date(symbol: str):
    try:
        f = _get_fundamentals(symbol)
        d = None
        if isinstance(f, dict):
            g = f.get("General") if isinstance(f.get("General"), dict) else None
            if g:
                d = g.get("IPODate") or g.get("IPO_Date") or g.get("IPO")
        if isinstance(d, str) and len(d) >= 10:
            y,m,dd = d[:10].split("-")
            return date(int(y), int(m), int(dd))
    except Exception:
        pass
    return date(1970,1,1)

def _ema(values, span):
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out

def _sma(values, period):
    out = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        out.append(None if i + 1 < period else s / period)
    return out

def _std(values, period):
    out = []
    for i in range(len(values)):
        if i + 1 < period:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        out.append(math.sqrt(var))
    return out

def _bb(values, period=20, std_mul=2.0):
    mid = _sma(values, period)
    sd = _std(values, period)
    upper, lower = [], []
    for m, s in zip(mid, sd):
        if m is None or s is None:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(m + std_mul * s)
            lower.append(m - std_mul * s)
    return upper, mid, lower

def _rsi(values, period=14):
    if len(values) < period + 1:
        return [None] * len(values)
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = [None] * period
    rsi.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))
    return [None] + rsi

def _macd(values, fast=12, slow=26, signal=9):
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    n = len(values)

    macd_line = [None] * n
    for i in range(n):
        if i >= len(ema_fast) or i >= len(ema_slow):
            continue
        if ema_fast[i] is None or ema_slow[i] is None:
            continue
        macd_line[i] = ema_fast[i] - ema_slow[i]

    signal_line = [None] * n
    macd_vals = [x for x in macd_line if x is not None]

    if len(macd_vals) >= signal:
        signal_vals = _ema(macd_vals, signal)
        j = 0
        for i in range(n):
            if macd_line[i] is not None:
                signal_line[i] = signal_vals[j]
                j += 1

    hist = [None] * n
    for i in range(n):
        if macd_line[i] is None or signal_line[i] is None:
            continue
        hist[i] = macd_line[i] - signal_line[i]

    return macd_line, signal_line, hist

def _stoch(highs, lows, closes, period=14, smooth_d=3):
    k = [None] * len(closes)
    for i in range(len(closes)):
        if i + 1 < period:
            continue
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        denom = (hh - ll)
        k[i] = 0.0 if denom == 0 else 100.0 * (closes[i] - ll) / denom
    d = [None] * len(closes)
    for i in range(len(closes)):
        window = [x for x in k[max(0, i - smooth_d + 1): i + 1] if x is not None]
        d[i] = (sum(window) / len(window)) if window else None
    return k, d

def _sr_levels(candles, pivot_left=6, pivot_right=6, tol_pct=0.008, max_levels=30, current_price=None, price_range_pct=0.50):
    if not candles or len(candles) < (pivot_left + pivot_right + 10):
        return []
    pivots = []
    n = len(candles)
    for i in range(pivot_left, n - pivot_right):
        lo = candles[i]["low"]
        hi = candles[i]["high"]
        is_low = True
        is_high = True
        for j in range(i - pivot_left, i + pivot_right + 1):
            if candles[j]["low"] < lo:
                is_low = False
            if candles[j]["high"] > hi:
                is_high = False
            if not is_low and not is_high:
                break
        if is_low:
            pivots.append(("support", float(lo)))
        if is_high:
            pivots.append(("resistance", float(hi)))
    if not pivots:
        return []
    if current_price and current_price > 0:
        lo = current_price * (1.0 - price_range_pct)
        hi = current_price * (1.0 + price_range_pct)
        pivots = [(t, v) for t, v in pivots if lo <= v <= hi]
    if not pivots:
        return []
    supports = [p[1] for p in pivots if p[0] == "support"]
    resistances = [p[1] for p in pivots if p[0] == "resistance"]
    def cluster(values):
        values = sorted(values)
        clusters = []
        for v in values:
            placed = False
            for c in clusters:
                mid = c["sum"] / c["count"]
                if abs(v - mid) / mid <= tol_pct:
                    c["sum"] += v
                    c["count"] += 1
                    placed = True
                    break
            if not placed:
                clusters.append({"sum": v, "count": 1})
        out = [{"value": c["sum"] / c["count"], "strength": c["count"]} for c in clusters]
        out.sort(key=lambda x: (-x["strength"], -x["value"]))
        return out
    sup = cluster(supports)
    res = cluster(resistances)
    all_lvls = []
    for x in sup:
        all_lvls.append({"type": "support", "value": round(float(x["value"]), 6), "strength": int(x["strength"])})
    for x in res:
        all_lvls.append({"type": "resistance", "value": round(float(x["value"]), 6), "strength": int(x["strength"])})
    all_lvls.sort(key=lambda x: (-x["strength"], x["type"]))
    return all_lvls[:max_levels]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

def _zigzag_pivots(candles, deviation=0.06, min_bars=8):
    if not candles or len(candles) < (min_bars + 5):
        return []
    pivots = []
    last_idx = 0
    last_price = candles[0]["close"]
    trend = 0
    extreme_idx = 0
    extreme_price = last_price

    def pct(a, b):
        if b == 0:
            return 0.0
        return (a - b) / b

    for i in range(1, len(candles)):
        hi = candles[i]["high"]
        lo = candles[i]["low"]

        if trend == 0:
            up = pct(hi, last_price)
            dn = pct(last_price, lo)
            if up >= deviation:
                trend = 1
                extreme_idx = i
                extreme_price = hi
            elif dn >= deviation:
                trend = -1
                extreme_idx = i
                extreme_price = lo
            continue

        if trend == 1:
            if hi > extreme_price:
                extreme_price = hi
                extreme_idx = i
            rev = pct(extreme_price, lo)
            if rev >= deviation and (i - extreme_idx) >= min_bars:
                pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "H"})
                trend = -1
                last_idx = extreme_idx
                last_price = extreme_price
                extreme_idx = i
                extreme_price = lo

        else:
            if lo < extreme_price:
                extreme_price = lo
                extreme_idx = i
            rev = pct(hi, extreme_price)
            if rev >= deviation and (i - extreme_idx) >= min_bars:
                pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "L"})
                trend = 1
                last_idx = extreme_idx
                last_price = extreme_price
                extreme_idx = i
                extreme_price = hi

    if trend == 1:
        pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "H"})
    elif trend == -1:
        pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "L"})

    pivots = sorted(pivots, key=lambda x: x["idx"])
    cleaned = []
    for pv in pivots:
        if not cleaned:
            cleaned.append(pv)
            continue
        if pv["type"] == cleaned[-1]["type"]:
            if pv["type"] == "H":
                if pv["price"] >= cleaned[-1]["price"]:
                    cleaned[-1] = pv
            else:
                if pv["price"] <= cleaned[-1]["price"]:
                    cleaned[-1] = pv
        else:
            cleaned.append(pv)
    return cleaned

def _wave_len(a, b):
    return abs(float(b["price"]) - float(a["price"]))

def _between(v, lo, hi):
    return lo <= v <= hi

def _fib_score(ratio, targets):
    for t in targets:
        if abs(ratio - t) / t < 0.08:
            return 1.0
    for t in targets:
        if abs(ratio - t) / t < 0.15:
            return 0.5
    return 0.0

def _score_impulse(seq):
    if len(seq) != 6:
        return None
    p0, p1, p2, p3, p4, p5 = seq
    types = [p.get("type","") for p in seq]
    if types == ["L","H","L","H","L","H"]:
        direction = 1
    elif types == ["H","L","H","L","H","L"]:
        direction = -1
    else:
        return None
    if direction == 1:
        if p1["price"] <= p0["price"]: return None
        if p2["price"] >= p1["price"]: return None
        if p2["price"] <= p0["price"]: return None
        if p3["price"] <= p2["price"]: return None
        if p3["price"] <= p1["price"]: return None
        if p4["price"] >= p3["price"]: return None
        if p4["price"] <= p1["price"]: return None
        if p5["price"] <= p4["price"]: return None
    else:
        if p1["price"] >= p0["price"]: return None
        if p2["price"] <= p1["price"]: return None
        if p2["price"] >= p0["price"]: return None
        if p3["price"] >= p2["price"]: return None
        if p3["price"] >= p1["price"]: return None
        if p4["price"] <= p3["price"]: return None
        if p4["price"] >= p1["price"]: return None
        if p5["price"] >= p4["price"]: return None
    w1 = _wave_len(p0, p1)
    w2 = _wave_len(p1, p2)
    w3 = _wave_len(p2, p3)
    w4 = _wave_len(p3, p4)
    w5 = _wave_len(p4, p5)
    if min(w1, w2, w3, w4, w5) <= 0:
        return None
    score = 0.0
    rules = []
    rules.append("structure_valid"); score += 4.0
    if w3 == min(w1, w3, w5): return None
    rules.append("wave3_not_shortest"); score += 3.0
    r2 = w2 / w1
    score += _fib_score(r2, [0.382, 0.5, 0.618, 0.786]) * 2.0
    if _between(r2, 0.382, 0.786): rules.append("wave2_fib")
    r3 = w3 / w1
    score += _fib_score(r3, [1.618, 2.0, 2.618]) * 3.0
    if _between(r3, 1.382, 2.618): rules.append("wave3_fib")
    r4 = w4 / w3
    score += _fib_score(r4, [0.236, 0.382, 0.5]) * 2.0
    if _between(r4, 0.236, 0.618): rules.append("wave4_fib")
    r5 = w5 / w1
    score += _fib_score(r5, [0.618, 1.0, 1.618]) * 1.5
    if w3 > w1: score += 1.0
    if w3 > w5: score += 1.0
    return {
        "score": round(score, 3),
        "direction": "bullish" if direction == 1 else "bearish",
        "rules": rules,
        "points": [p0, p1, p2, p3, p4, p5],
        "w1": w1, "w2": w2, "w3": w3, "w4": w4, "w5": w5,
    }

def _score_abc(seq):
    if len(seq) != 3:
        return None
    a, b, c = seq
    da = b["price"] - a["price"]
    db = c["price"] - b["price"]
    if not (da != 0 and db != 0 and (da > 0) != (db > 0)):
        return None
    direction = 1 if da < 0 else -1
    wa = _wave_len(a, b)
    wb = _wave_len(b, c)
    wc = _wave_len(c if len(seq) > 2 else b, seq[-1])
    score = 2.0
    rc = wa / wa if wa == 0 else wb / wa
    if _between(rc, 0.5, 0.786): score += 1.5
    rc2 = wc / wa if wa else 1
    if _between(rc2, 0.618, 1.618): score += 1.5
    return {
        "score": round(score, 3),
        "direction": "bullish" if direction == 1 else "bearish",
        "type": "abc",
        "points": seq,
        "wa": wa, "wb": wb, "wc": wc,
    }

def _determine_current_wave(pivots, best):
    if not best or not best.get("points"):
        return "unknown", None
    pts = best["points"]
    last_pivot = pivots[-1] if pivots else None
    if not last_pivot:
        return "unknown", None
    last_pt = pts[-1]
    if last_pivot["time"] == last_pt["time"]:
        return "after_5", pts[-1]
    for i, pt in enumerate(pts):
        if pt["time"] == last_pivot["time"]:
            return f"in_wave_{i+1}", pt
    wave5 = pts[5] if len(pts) > 5 else pts[-1]
    wave5_idx = wave5.get("idx", 0)
    last_idx = last_pivot.get("idx", 999)
    if last_idx > wave5_idx:
        return "corrective_after_5", last_pivot
    p4 = pts[4] if len(pts) > 4 else pts[-1]
    if best["direction"] == "bullish" and last_pivot["price"] > wave5["price"]:
        return "extension_possible", last_pivot
    if best["direction"] == "bearish" and last_pivot["price"] < wave5["price"]:
        return "extension_possible", last_pivot
    return "corrective_after_5", last_pivot

def _fibonacci_targets(best, pivots):
    if not best:
        return []
    pts = best["points"]
    direction = best["direction"]
    w1 = best.get("w1", 0)
    w3 = best.get("w3", 0)
    targets = []
    wave5_pt = pts[5] if len(pts) > 5 else pts[-1]
    wave0_pt = pts[0]
    if direction == "bullish":
        top = wave5_pt["price"]
        bottom = wave0_pt["price"]
        wave_up = abs(top - bottom)
        targets.append({"label": "W5_ext_100", "price": round(top + w1, 2)})
        targets.append({"label": "W5_ext_162", "price": round(top + w1 * 1.618, 2)})
        targets.append({"label": "corr_382", "price": round(top - wave_up * 0.382, 2)})
        targets.append({"label": "corr_500", "price": round(top - wave_up * 0.500, 2)})
        targets.append({"label": "corr_618", "price": round(top - wave_up * 0.618, 2)})
    else:
        bottom = wave5_pt["price"]
        top = wave0_pt["price"]
        wave_down = abs(top - bottom)
        targets.append({"label": "W5_ext_100", "price": round(bottom - w1, 2)})
        targets.append({"label": "W5_ext_162", "price": round(bottom - w1 * 1.618, 2)})
        targets.append({"label": "corr_382", "price": round(bottom + wave_down * 0.382, 2)})
        targets.append({"label": "corr_500", "price": round(bottom + wave_down * 0.500, 2)})
        targets.append({"label": "corr_618", "price": round(bottom + wave_down * 0.618, 2)})
    return targets

def _best_impulse(pivots):
    if len(pivots) < 5:
        return None
    best = None
    n = len(pivots)
    for i in range(0, n - 5):
        seq = pivots[i:i+6]
        scored = _score_impulse(seq)
        if scored is None:
            continue
        if scored["score"] < 8.0:
            continue
        recency = i / max(n - 5, 1)
        scored["adjusted"] = scored["score"] + recency * 6.0
        if best is None or scored["adjusted"] > best["adjusted"]:
            best = scored
    return best

def _build_elliott_analysis(pivots):
    if not pivots or len(pivots) < 5:
        return _empty_elliott()

    best = _best_impulse(pivots)

    if not best:
        abc = None
        for i in range(len(pivots) - 2):
            r = _score_abc(pivots[i:i+3])
            if r and (abc is None or r["score"] > abc["score"]):
                abc = r
        if abc:
            return {
                "current_structure": "ABC-Korrektur",
                "confidence": "low",
                "main_scenario": _abc_scenario(abc, pivots),
                "alt_scenario": None,
                "labels": _abc_labels(abc),
                "pivots": pivots,
            }
        return _empty_elliott()

    current_wave, _ = _determine_current_wave(pivots, best)
    fib_targets = _fibonacci_targets(best, pivots)
    main_sc = _build_main_scenario(best, current_wave, fib_targets, pivots)
    alt_sc = _build_alt_scenario(best, current_wave, fib_targets, pivots)
    labels = []
    for i, name in enumerate(["1", "2", "3", "4", "5"], 1):
        pt = best["points"][i]
        labels.append({"time": pt["time"], "price": pt["price"], "text": name})
    confidence = "high" if best["score"] >= 14 else "medium" if best["score"] >= 10 else "low"
    structure = _describe_structure(current_wave, best)
    return {
        "current_structure": structure,
        "confidence": confidence,
        "score": best["score"],
        "direction": best["direction"],
        "main_scenario": main_sc,
        "alt_scenario": alt_sc,
        "labels": labels,
        "pivots": pivots,
        "rule_flags": best.get("rules", []),
    }

def _describe_structure(current_wave, best):
    d = "bullish" if best["direction"] == "bullish" else "bearish"
    wave_names = {
        "in_wave_1": "Welle 1 aktiv",
        "in_wave_2": "Welle 2 Korrektur",
        "in_wave_3": "Welle 3 aktiv (stärkste Welle)",
        "in_wave_4": "Welle 4 Korrektur",
        "in_wave_5": "Welle 5 aktiv",
        "after_5": "Impuls abgeschlossen - Korrektur erwartet",
        "corrective_after_5": "Korrektur nach Impuls",
        "extension_possible": "Mögliche Wellenverlängerung",
    }
    return wave_names.get(current_wave, f"Impulsstruktur ({d})")

def _build_main_scenario(best, current_wave, fib_targets, pivots):
    pts = best["points"]
    direction = best["direction"]
    last_price = pivots[-1]["price"] if pivots else pts[-1]["price"]
    targets_up = [t for t in fib_targets if t["price"] > last_price]
    targets_down = [t for t in fib_targets if t["price"] < last_price]
    if current_wave in ("after_5", "corrective_after_5"):
        zone = [targets_down[0]["price"], targets_down[1]["price"]] if len(targets_down) >= 2 else [round(last_price*0.90,2), round(last_price*0.95,2)]
        desc = "Korrektur nach abgeschlossenem Impuls"
        prob = 60
        future = _project_correction(pts, direction)
    elif "wave_3" in current_wave or "wave_5" in current_wave:
        zone = [targets_up[0]["price"], targets_up[1]["price"]] if len(targets_up) >= 2 else [round(last_price*1.05,2), round(last_price*1.10,2)]
        desc = "Impuls setzt sich fort"
        prob = 65
        future = _project_continuation(pts, direction, fib_targets)
    else:
        t_up = [t for t in fib_targets if t["price"] > last_price]
        t_dn = [t for t in fib_targets if t["price"] < last_price]
        if direction == "bullish" and len(t_up) >= 2:
            zone = [t_up[0]["price"], t_up[1]["price"]]
        elif direction == "bearish" and len(t_dn) >= 2:
            zone = [t_dn[0]["price"], t_dn[1]["price"]]
        elif len(t_up) >= 2:
            zone = [t_up[0]["price"], t_up[1]["price"]]
        else:
            zone = [round(last_price*1.05,2), round(last_price*1.12,2)]
        desc = "Impulsstruktur läuft weiter"
        prob = 58
        future = _project_continuation(pts, direction, fib_targets)
    if zone:
        zone = [round(min(zone), 2), round(max(zone), 2)]
    return {
        "description": desc,
        "probability": prob,
        "target_zone": zone,
        "future_path": future,
    }

def _build_alt_scenario(best, current_wave, fib_targets, pivots):
    pts = best["points"]
    direction = best["direction"]
    last_price = pivots[-1]["price"] if pivots else pts[-1]["price"]
    targets_down = [t for t in fib_targets if t["price"] < last_price]
    targets_up = [t for t in fib_targets if t["price"] > last_price]
    if current_wave in ("after_5", "corrective_after_5"):
        zone = [targets_up[0]["price"], targets_up[1]["price"]] if len(targets_up) >= 2 else [round(last_price*1.05,2), round(last_price*1.10,2)]
        desc = "Impuls setzt sich direkt fort (Welle 3 Extension)"
        prob = 40
        future = _project_continuation(pts, direction, fib_targets)
    else:
        zone = [targets_down[0]["price"], targets_down[1]["price"]] if len(targets_down) >= 2 else [round(last_price*0.88,2), round(last_price*0.93,2)]
        desc = "Impuls beendet, tiefere Korrektur"
        prob = 35
        future = _project_correction(pts, direction)
    if zone:
        zone = [round(min(zone), 2), round(max(zone), 2)]
    return {
        "description": desc,
        "probability": prob,
        "target_zone": zone,
        "future_path": future,
    }

def _project_continuation(pts, direction, fib_targets):
    if not pts or not fib_targets:
        return []
    last = pts[-1]
    targets_fwd = sorted(
        [t for t in fib_targets if (direction == "bullish" and t["price"] > last["price"]) or
                                    (direction == "bearish" and t["price"] < last["price"])],
        key=lambda x: abs(x["price"] - last["price"])
    )
    if not targets_fwd:
        return []
    return [
        {"time": last["time"], "price": last["price"], "projected": True},
        {"time": "projection", "price": targets_fwd[0]["price"], "projected": True},
    ]

def _project_correction(pts, direction):
    if len(pts) < 5:
        return []
    p0, p4 = pts[0], pts[4]
    total = abs(p4["price"] - p0["price"])
    corr_382 = p4["price"] - total * 0.382 if direction == "bullish" else p4["price"] + total * 0.382
    corr_618 = p4["price"] - total * 0.618 if direction == "bullish" else p4["price"] + total * 0.618
    return [
        {"time": p4["time"], "price": p4["price"], "projected": True},
        {"time": "projection_a", "price": round(corr_382, 2), "projected": True},
        {"time": "projection_b", "price": round(corr_618, 2), "projected": True},
    ]

def _abc_scenario(abc, pivots):
    last = pivots[-1]["price"] if pivots else 0
    return {
        "description": "ABC-Korrektur läuft",
        "probability": 55,
        "target_zone": None,
        "future_path": [],
    }

def _abc_labels(abc):
    names = ["A", "B", "C"]
    return [{"time": abc["points"][i]["time"], "price": abc["points"][i]["price"], "text": names[i]} for i in range(3)]

def _empty_elliott():
    return {
        "current_structure": "Keine klare Struktur erkannt",
        "confidence": "none",
        "main_scenario": None,
        "alt_scenario": None,
        "labels": [],
        "pivots": [],
        "rule_flags": [],
    }

def _elliott_labels(pivots):
    result = _build_elliott_analysis(pivots)
    return result

@app.get("/api/tv")
def tv(
    symbol: str = Query(..., min_length=1, max_length=32),
    period: str = Query("d", pattern="^(d|w|m)$"),
    full: int = Query(1, ge=0, le=1),
    days: int = Query(520, ge=120, le=80000),
):
    try:

            to_d = date.today()
            if int(full) == 1:
                start = _ipo_date(symbol)
                raw = _get(f"eod/{symbol}", {"from": start.isoformat(), "to": to_d.isoformat(), "period": period})
            else:
                from_d = to_d - timedelta(days=days)
                raw = _get(f"eod/{symbol}", {"from": from_d.isoformat(), "to": to_d.isoformat(), "period": period})
            if not isinstance(raw, list) or len(raw) == 0:
                raise HTTPException(status_code=502, detail="No candle data returned")
            raw_sorted = sorted(raw, key=lambda x: x.get("date", ""))
            candles = []
            closes, highs, lows = [], [], []
            for r in raw_sorted:
                d = r.get("date")
                o = r.get("open")
                h = r.get("high")
                l = r.get("low")
                c = r.get("close")
                if d is None or h is None or l is None or c is None:
                    continue
                try:
                    c = float(c)
                    h = float(h)
                    l = float(l)
                    o = float(o) if o is not None else c
                except Exception as e:
                    return {"ERROR": str(e), "raw": {"c": c, "h": h, "l": l, "o": o}}
                if c <= 0 or h <= 0 or l <= 0 or h < l:
                    continue
                candles.append({"time": d, "open": o, "high": h, "low": l, "close": c})
                closes.append(c)
                highs.append(h)
                lows.append(l)
            if len(candles) < 120:
                raise HTTPException(status_code=502, detail="Not enough candle data")
            bb_u, bb_m, bb_l = _bb(closes, 20, 2.0)
            ema20 = _ema(closes, 20)
            ema50 = _ema(closes, 50)
            ema100 = _ema(closes, 100)
            ema200 = _ema(closes, 200)
            rsi14 = _rsi(closes, 14)
            stoch_k, stoch_d = _stoch(highs, lows, closes, 14, 3)
            macd, macd_sig, macd_hist = _macd(closes, 12, 26, 9)
            overlays = []
            for i in range(len(candles)):
                overlays.append({
                    "time": candles[i]["time"],
                    "close": closes[i],
                    "bb_upper": bb_u[i],
                    "bb_middle": bb_m[i],
                    "bb_lower": bb_l[i],
                    "ema20": ema20[i] if i < len(ema20) else None,
                    "ema50": ema50[i] if i < len(ema50) else None,
                    "ema100": ema100[i] if i < len(ema100) else None,
                    "ema200": ema200[i] if i < len(ema200) else None,
                    "rsi14": rsi14[i] if i < len(rsi14) else None,
                    "stoch_k": stoch_k[i],
                    "stoch_d": stoch_d[i],
                    "macd": macd[i] if i < len(macd) else None,
                    "macd_signal": macd_sig[i] if i < len(macd_sig) else None,
                    "macd_hist": macd_hist[i] if i < len(macd_hist) else None,
                })
            last = overlays[-1]
            levels = _sr_levels(candles, current_price=closes[-1])
            ell_candles = candles[-250:] if len(candles) > 250 else candles
            pivots = _zigzag_pivots(ell_candles, deviation=0.06, min_bars=8)
            elliott = _elliott_labels(pivots)
            return {"symbol": symbol.upper(), "candles": candles, "overlays": overlays, "last": last, "levels": levels, "elliott": elliott}
    except Exception as e:
        import traceback
        return {"ERROR": str(e), "TRACE": traceback.format_exc()}
