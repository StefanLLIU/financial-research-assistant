"""AI Financial Research Assistant — FastAPI + yfinance + SQLite"""

import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import yfinance as yf
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db

app = FastAPI(title="AI Financial Research Assistant", version="1.0.0")

# Serve PWA icons (and any other static assets)
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    db.init_db()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    ticker: str


class NewsItem(BaseModel):
    title: str
    publisher: str
    link: str
    published: str


class ResearchReport(BaseModel):
    id: int | None = None
    ticker: str
    company: str | None
    sector: str | None
    price: float | None
    currency: str | None
    market_cap: float | None
    pe_ratio: float | None
    week_52_high: float | None
    week_52_low: float | None
    news: list[NewsItem]
    ai_summary: str
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val) -> float | None:
    try:
        return float(val) if val not in (None, "N/A", float("inf"), float("-inf")) else None
    except (TypeError, ValueError):
        return None


_DEMO_DATA = {
    "ticker": "DEMO",
    "company": "Demo Corporation Inc.",
    "sector": "Technology",
    "price": 142.50,
    "currency": "USD",
    "market_cap": 85_000_000_000,
    "pe_ratio": 22.4,
    "week_52_high": 178.30,
    "week_52_low": 110.15,
    "target_mean_price": 168.00,
    "description": (
        "Demo Corporation Inc. is a fictional technology company used to showcase "
        "the Financial Research Assistant. It develops cloud software, AI tools, "
        "and enterprise SaaS products sold globally to Fortune 500 clients. "
        "The company has shown consistent revenue growth over the past five years "
        "and maintains a strong balance sheet with minimal long-term debt."
    ),
    "news": [
        NewsItem(title="Demo Corp beats Q2 earnings estimates", publisher="Financial Times", link="", published="2026-06-15 09:00 UTC"),
        NewsItem(title="Demo Corp expands into Asian markets", publisher="Reuters", link="", published="2026-06-10 14:30 UTC"),
        NewsItem(title="Demo Corp announces $2B share buyback", publisher="Bloomberg", link="", published="2026-06-05 11:00 UTC"),
    ],
}


def _safe_getattr(obj, attr):
    """Access a fast_info attribute without letting internal KeyErrors escape."""
    try:
        return getattr(obj, attr, None)
    except Exception:
        return None


def _yf_session():
    """A browser-impersonating session avoids Yahoo Finance 429 rate limits."""
    try:
        from curl_cffi import requests as creq
        return creq.Session(impersonate="chrome")
    except Exception:
        return None


FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "").strip()


def _finnhub_get(path: str, params: dict) -> dict | None:
    """Call a Finnhub REST endpoint; returns parsed JSON or None."""
    if not FINNHUB_KEY:
        return None
    query = urllib.parse.urlencode({**params, "token": FINNHUB_KEY})
    url = f"https://finnhub.io/api/v1{path}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_finnhub_meta(symbol: str) -> dict:
    """Company profile + key metrics from Finnhub.

    Used to fill the gaps Yahoo's heavier endpoints leave when its
    quoteSummary API is rate-limited on shared cloud IPs.
    """
    out: dict = {}

    prof = _finnhub_get("/stock/profile2", {"symbol": symbol})
    if prof:
        out["company"] = prof.get("name")
        out["sector"] = prof.get("finnhubIndustry")
        out["currency"] = prof.get("currency")
        mc = prof.get("marketCapitalization")  # reported in millions
        if mc:
            out["market_cap"] = float(mc) * 1e6

    metric = _finnhub_get("/stock/metric", {"symbol": symbol, "metric": "all"})
    if metric and isinstance(metric.get("metric"), dict):
        m = metric["metric"]
        out["pe_ratio"] = _safe_float(m.get("peTTM") or m.get("peBasicExclExtraTTM"))
        out["week_52_high"] = _safe_float(m.get("52WeekHigh"))
        out["week_52_low"] = _safe_float(m.get("52WeekLow"))

    quote = _finnhub_get("/quote", {"symbol": symbol})
    if quote and quote.get("c"):
        out["price"] = _safe_float(quote.get("c"))

    return out


def fetch_stock_data(ticker: str) -> dict:
    """Pull price, info and news from Yahoo Finance (Finnhub fills the gaps)."""
    symbol = ticker.upper()

    if symbol == "DEMO":
        return {**_DEMO_DATA}

    session = _yf_session()
    t = yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)

    # fast_info — wrap both the object retrieval AND every attribute access
    fi = None
    try:
        fi = t.fast_info
    except Exception:
        pass

    price = _safe_float(_safe_getattr(fi, "last_price"))
    fi_market_cap = _safe_float(_safe_getattr(fi, "market_cap"))
    fi_year_high = _safe_float(_safe_getattr(fi, "year_high"))
    fi_year_low = _safe_float(_safe_getattr(fi, "year_low"))
    fi_currency = _safe_getattr(fi, "currency")

    # Fall back to 1-day history for price
    if price is None:
        try:
            hist = t.history(period="1d")
            price = float(hist["Close"].iloc[-1]) if not hist.empty else None
        except Exception:
            pass

    # Full info for richer metadata
    info = {}
    try:
        info = t.info or {}
    except Exception:
        pass

    company = info.get("longName") or info.get("shortName")
    sector = info.get("sector")
    currency = info.get("currency") or fi_currency or "USD"
    market_cap = _safe_float(info.get("marketCap")) or fi_market_cap
    pe_ratio = _safe_float(info.get("trailingPE"))
    week_52_high = _safe_float(info.get("fiftyTwoWeekHigh")) or fi_year_high
    week_52_low = _safe_float(info.get("fiftyTwoWeekLow")) or fi_year_low
    target_mean_price = _safe_float(info.get("targetMeanPrice"))
    description = info.get("longBusinessSummary", "")

    raw_news = []
    try:
        raw_news = t.news or []
    except Exception:
        pass

    news_items = []
    for item in raw_news[:5]:
        content = item.get("content", {})
        pub_date = content.get("pubDate", "")
        if pub_date:
            try:
                pub_date = datetime.fromisoformat(
                    pub_date.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                pass
        news_items.append(
            NewsItem(
                title=content.get("title") or item.get("title", "No title"),
                publisher=content.get("provider", {}).get("displayName", "Unknown"),
                link=content.get("canonicalUrl", {}).get("url", ""),
                published=pub_date,
            )
        )

    # Fill any gaps Yahoo left (common when its quoteSummary API is rate-limited
    # on shared cloud IPs) using Finnhub, if an API key is configured.
    if FINNHUB_KEY and (company is None or pe_ratio is None or sector is None or price is None):
        fh = fetch_finnhub_meta(symbol)
        company = company or fh.get("company")
        sector = sector or fh.get("sector")
        currency = currency or fh.get("currency") or "USD"
        market_cap = market_cap or fh.get("market_cap")
        if pe_ratio is None:
            pe_ratio = fh.get("pe_ratio")
        week_52_high = week_52_high or fh.get("week_52_high")
        week_52_low = week_52_low or fh.get("week_52_low")
        if price is None:
            price = fh.get("price")

    return {
        "ticker": symbol,
        "company": company,
        "sector": sector,
        "price": price,
        "currency": currency,
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "week_52_high": week_52_high,
        "week_52_low": week_52_low,
        "target_mean_price": target_mean_price,
        "description": description,
        "news": news_items,
    }


_BULLISH_WORDS = (
    "beat", "beats", "surge", "soar", "record", "growth", "buyback", "upgrade",
    "expand", "expands", "rally", "gain", "gains", "profit", "strong", "raise",
    "raises", "wins", "win", "high", "jumps", "boost", "outperform",
)
_BEARISH_WORDS = (
    "miss", "misses", "plunge", "drop", "drops", "fall", "falls", "cut", "cuts",
    "downgrade", "loss", "losses", "lawsuit", "probe", "decline", "weak",
    "warning", "warn", "slump", "layoff", "layoffs", "recall", "fraud", "slowdown",
)


def compute_upside(price, target) -> float | None:
    """Percentage upside (or downside) from current price to analyst target."""
    if price and target and price > 0:
        return (target - price) / price * 100
    return None


def fmt_cap(v, lang: str = "zh") -> str:
    """Format a market cap into a readable unit (万亿/亿 or T/B/M)."""
    if v is None:
        return "N/A"
    if lang == "en":
        if v >= 1e12:
            return f"{v / 1e12:.2f}T"
        if v >= 1e9:
            return f"{v / 1e9:.1f}B"
        if v >= 1e6:
            return f"{v / 1e6:.1f}M"
        return f"{v:,.0f}"
    if v >= 1e12:
        return f"{v / 1e12:.2f} 万亿"
    if v >= 1e8:
        return f"{v / 1e8:.1f} 亿"
    return f"{v:,.0f}"


def news_sentiment(news: list) -> int:
    """Return -1 (bearish), 0 (neutral), or +1 (bullish) from headline keywords."""
    if not news:
        return 0
    score = 0
    for n in news:
        title = n.title.lower()
        score += sum(w in title for w in _BULLISH_WORDS)
        score -= sum(w in title for w in _BEARISH_WORDS)
    if score > 0:
        return 1
    if score < 0:
        return -1
    return 0


def compute_score(stock: dict, lang: str = "zh") -> dict:
    """Composite 1-10 score from price position, P/E, analyst upside, news.

    Each factor contributes points; the total is mapped to a 1-10 scale and a
    Bullish / Neutral / Bearish label. Missing factors are simply skipped.
    """
    en = lang == "en"
    price = stock["price"]
    high52 = stock["week_52_high"]
    low52 = stock["week_52_low"]
    pe = stock["pe_ratio"]
    upside = compute_upside(price, stock.get("target_mean_price"))
    sentiment = news_sentiment(stock.get("news", []))

    points = 0.0       # accumulated signal, roughly -1..+1 per factor
    factors = 0
    reasons: list[str] = []

    # 1. Price vs 52-week range — lower in range scores higher (more upside room)
    if price and high52 and low52 and high52 > low52:
        pos = (price - low52) / (high52 - low52)  # 0 = at low, 1 = at high
        contrib = 1 - 2 * pos                       # +1 at low, -1 at high
        points += contrib
        factors += 1
        if pos >= 0.8:
            reasons.append("near 52-week high (limited upside)" if en else "股价接近52周高点（上涨空间有限）")
        elif pos <= 0.3:
            reasons.append("near 52-week low (value potential)" if en else "股价接近52周低点（具备价值潜力）")
        else:
            reasons.append("mid-range price position" if en else "股价处于区间中段")

    # 2. P/E ratio — moderate P/E is good, very high or negative is bad
    if pe is not None:
        if pe < 0:
            contrib = -1.0
            reasons.append("currently unprofitable" if en else "公司目前亏损")
        elif pe < 15:
            contrib = 0.8
            reasons.append("attractive low P/E" if en else "市盈率偏低，估值吸引")
        elif pe < 25:
            contrib = 0.4
            reasons.append("reasonable P/E" if en else "市盈率合理")
        elif pe < 40:
            contrib = -0.2
            reasons.append("elevated P/E" if en else "市盈率偏高")
        else:
            contrib = -0.8
            reasons.append("very high P/E" if en else "市盈率非常高")
        points += contrib
        factors += 1

    # 3. Analyst target upside
    if upside is not None:
        contrib = max(-1.0, min(1.0, upside / 25))  # +/-25% => full +/-1
        points += contrib
        factors += 1
        if upside >= 10:
            reasons.append(f"analysts see {upside:.0f}% upside" if en else f"分析师预期上涨 {upside:.0f}%")
        elif upside <= -10:
            reasons.append(f"analysts see {abs(upside):.0f}% downside" if en else f"分析师预期下跌 {abs(upside):.0f}%")
        else:
            reasons.append("price near analyst target" if en else "股价接近分析师目标价")

    # 4. News sentiment
    if stock.get("news"):
        points += sentiment
        factors += 1
        if en:
            reasons.append({1: "positive news flow", 0: "neutral news", -1: "negative news flow"}[sentiment])
        else:
            reasons.append({1: "近期新闻偏正面", 0: "近期新闻中性", -1: "近期新闻偏负面"}[sentiment])

    # Map average signal (-1..+1) to a 1-10 scale (5.5 = neutral midpoint)
    avg = (points / factors) if factors else 0.0
    score = round(5.5 + avg * 4.5)
    score = max(1, min(10, score))

    if score >= 7:
        label, css = ("Bullish" if en else "看涨"), "bullish"
    elif score >= 4:
        label, css = ("Neutral" if en else "中性"), "neutral"
    else:
        label, css = ("Bearish" if en else "看跌"), "bearish"

    return {
        "score": score,
        "label": label,
        "css": css,
        "upside": upside,
        "reasons": reasons,
    }


_DEMO_EARNINGS = {
    "quarter": "2026-03-31",
    "eps_actual": 1.85,
    "eps_estimate": 1.70,
    "eps_beat_pct": 8.82,
    "revenue_actual": 6_120_000_000,
    "revenue_estimate": 5_800_000_000,
    "revenue_beat_pct": 5.52,
    "revenue_yoy": 24.5,
    "history": [
        {"quarter": "2025-06-30", "eps_actual": 1.42, "eps_estimate": 1.40, "beat_pct": 1.43},
        {"quarter": "2025-09-30", "eps_actual": 1.55, "eps_estimate": 1.58, "beat_pct": -1.90},
        {"quarter": "2025-12-31", "eps_actual": 1.78, "eps_estimate": 1.65, "beat_pct": 7.88},
        {"quarter": "2026-03-31", "eps_actual": 1.85, "eps_estimate": 1.70, "beat_pct": 8.82},
    ],
}


def _clean_num(val):
    """Convert pandas/NaN values to a float or None."""
    f = _safe_float(val)
    if f is None or (isinstance(f, float) and math.isnan(f)):
        return None
    return f


def _beat_pct(actual, estimate):
    """Percentage by which actual beat (or missed) the estimate."""
    if actual is None or estimate is None or estimate == 0:
        return None
    return (actual - estimate) / abs(estimate) * 100


def fetch_earnings(t) -> dict | None:
    """Pull latest quarterly EPS (actual vs estimate) and revenue from yfinance."""
    result = {
        "quarter": None,
        "eps_actual": None, "eps_estimate": None, "eps_beat_pct": None,
        "revenue_actual": None, "revenue_estimate": None, "revenue_beat_pct": None,
        "revenue_yoy": None,
        "history": [],
    }

    # --- EPS history (actual vs estimate) ---
    try:
        eh = t.earnings_history
        if eh is not None and not eh.empty:
            for idx, row in eh.iterrows():
                actual = _clean_num(row.get("epsActual"))
                est = _clean_num(row.get("epsEstimate"))
                if actual is None:
                    continue
                result["history"].append({
                    "quarter": str(idx)[:10],
                    "eps_actual": actual,
                    "eps_estimate": est,
                    "beat_pct": _beat_pct(actual, est),
                })
            result["history"] = result["history"][-4:]
            if result["history"]:
                last = result["history"][-1]
                result["quarter"] = last["quarter"]
                result["eps_actual"] = last["eps_actual"]
                result["eps_estimate"] = last["eps_estimate"]
                result["eps_beat_pct"] = last["beat_pct"]
    except Exception:
        pass

    # --- Revenue actual (latest reported quarter) + YoY ---
    try:
        qis = t.quarterly_income_stmt
        if qis is not None and "Total Revenue" in qis.index:
            rev = qis.loc["Total Revenue"].dropna()
            if len(rev) >= 1:
                result["revenue_actual"] = _clean_num(rev.iloc[0])
            if len(rev) >= 5:  # same quarter a year earlier
                prev = _clean_num(rev.iloc[4])
                cur = result["revenue_actual"]
                if prev and cur:
                    result["revenue_yoy"] = (cur - prev) / prev * 100
    except Exception:
        pass

    if result["eps_actual"] is None and result["revenue_actual"] is None:
        return None
    return result


def fetch_price_history(ticker: str) -> dict | None:
    """Up to 5 years of daily close prices for charting.

    DEMO uses a deterministic synthetic random walk so the chart always renders.
    """
    if ticker == "DEMO":
        import random
        from datetime import timedelta
        random.seed(42)
        dates, closes = [], []
        price = 80.0
        day = datetime.now() - timedelta(days=365 * 5)
        end = datetime.now()
        while day <= end:
            if day.weekday() < 5:  # weekdays only
                price *= 1 + random.uniform(-0.018, 0.020)
                price = max(10.0, price)
                dates.append(day.strftime("%Y-%m-%d"))
                closes.append(round(price, 2))
            day += timedelta(days=1)
        return {"dates": dates, "closes": closes}

    session = _yf_session()
    t = yf.Ticker(ticker, session=session) if session else yf.Ticker(ticker)
    try:
        hist = t.history(period="5y")
        if hist is None or hist.empty:
            return None
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        closes = [round(float(c), 2) for c in hist["Close"]]
        if not dates:
            return None
        return {"dates": dates, "closes": closes}
    except Exception:
        return None


# In-memory cache for the homepage mini-cards (ticker -> (timestamp, data)).
_MINI_CACHE: dict = {}
_MINI_TTL = 600  # seconds


def fetch_mini(symbol: str) -> dict:
    """Lightweight quote + ~1-month sparkline for a homepage mini card.

    Cached for 10 minutes so repeated homepage loads don't hammer the API.
    """
    symbol = symbol.upper()
    now = time.time()
    hit = _MINI_CACHE.get(symbol)
    if hit and now - hit[0] < _MINI_TTL:
        return hit[1]

    data = {"ticker": symbol, "price": None, "change_pct": None, "currency": "", "spark": []}

    if symbol == "DEMO":
        h = fetch_price_history("DEMO")
        closes = h["closes"][-22:] if h else []
        if closes:
            change = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0.0
            data = {"ticker": "DEMO", "price": closes[-1], "change_pct": round(change, 2),
                    "currency": "USD", "spark": closes}
        _MINI_CACHE[symbol] = (now, data)
        return data

    try:
        session = _yf_session()
        t = yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)
        hist = t.history(period="1mo")
        if hist is not None and not hist.empty:
            closes = [round(float(c), 2) for c in hist["Close"]]
            if closes:
                prev = closes[-2] if len(closes) >= 2 else closes[0]
                change = (closes[-1] - prev) / prev * 100 if prev else 0.0
                cur = _safe_getattr(getattr(t, "fast_info", None), "currency") or "USD"
                data = {"ticker": symbol, "price": closes[-1], "change_pct": round(change, 2),
                        "currency": cur, "spark": closes}
    except Exception:
        pass

    _MINI_CACHE[symbol] = (now, data)
    return data


FEATURED_TICKERS = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]


def featured_html(lang: str = "zh") -> str:
    """Placeholder mini cards for the home page; JS fills them via /api/mini."""
    t = T[lang]
    cards = "".join(
        f'<a class="mini" href="/research-page?ticker={tk}&lang={lang}" data-ticker="{tk}">'
        f'<div class="mini-top"><span class="mini-tk">{tk}</span><span class="mini-chg">·</span></div>'
        f'<div class="mini-price">…</div>'
        f'<div class="mini-spark"></div></a>'
        for tk in FEATURED_TICKERS
    )
    return f'<h3 class="featured-h">{t["featured"]}</h3><div class="mini-grid">{cards}</div>'


def generate_earnings_summary(e: dict, lang: str = "zh") -> str:
    """Rule-based bilingual earnings commentary."""
    en = lang == "en"
    parts: list[str] = []
    q = e.get("quarter") or ("latest quarter" if en else "最近一季")

    if e.get("eps_actual") is not None and e.get("eps_estimate") is not None:
        bp = e.get("eps_beat_pct")
        if bp is not None and bp >= 0:
            parts.append(
                f"In {q}, EPS was {e['eps_actual']:.2f}, beating the estimate of {e['eps_estimate']:.2f} by {bp:.1f}%."
                if en else
                f"{q} 每股收益 (EPS) 为 {e['eps_actual']:.2f}，超出市场预期 {e['eps_estimate']:.2f}，超预期 {bp:.1f}%。"
            )
        elif bp is not None:
            parts.append(
                f"In {q}, EPS was {e['eps_actual']:.2f}, missing the estimate of {e['eps_estimate']:.2f} by {abs(bp):.1f}%."
                if en else
                f"{q} 每股收益 (EPS) 为 {e['eps_actual']:.2f}，低于市场预期 {e['eps_estimate']:.2f}，差 {abs(bp):.1f}%。"
            )
    elif e.get("eps_actual") is not None:
        parts.append(
            f"In {q}, EPS was {e['eps_actual']:.2f} (no estimate available)."
            if en else
            f"{q} 每股收益 (EPS) 为 {e['eps_actual']:.2f}（暂无预期数据）。"
        )

    if e.get("revenue_actual") is not None:
        rev_txt = f"Revenue was {fmt_cap(e['revenue_actual'], lang)}" if en else f"营收为 {fmt_cap(e['revenue_actual'], lang)}"
        if e.get("revenue_estimate") is not None:
            rbp = e.get("revenue_beat_pct")
            if en:
                verb = "beating" if (rbp or 0) >= 0 else "missing"
                rev_txt += f", {verb} the estimate of {fmt_cap(e['revenue_estimate'], lang)} ({rbp:+.1f}%)"
            else:
                verb = "超出" if (rbp or 0) >= 0 else "低于"
                rev_txt += f"，{verb}预期 {fmt_cap(e['revenue_estimate'], lang)}（{rbp:+.1f}%）"
        if e.get("revenue_yoy") is not None:
            yoy = e["revenue_yoy"]
            if en:
                rev_txt += f", {'up' if yoy >= 0 else 'down'} {abs(yoy):.1f}% YoY"
            else:
                rev_txt += f"，同比{'增长' if yoy >= 0 else '下降'} {abs(yoy):.1f}%"
        parts.append(rev_txt + ("." if en else "。"))

    # Beat streak from history
    hist = e.get("history", [])
    beats = [h for h in hist if h.get("beat_pct") is not None and h["beat_pct"] >= 0]
    if hist:
        parts.append(
            f"EPS beat estimates in {len(beats)} of the last {len(hist)} quarters."
            if en else
            f"过去 {len(hist)} 个季度中有 {len(beats)} 个季度 EPS 超预期。"
        )

    if not parts:
        return "No earnings data available." if en else "暂无可用的财报数据。"
    parts.append(
        "Auto-generated from public earnings data; not investment advice."
        if en else "以上为基于公开财报数据的自动分析，不构成投资建议。"
    )
    return " ".join(parts)


def generate_summary(stock: dict, lang: str = "zh") -> str:
    """Rule-based bilingual investment summary derived from yfinance data."""
    en = lang == "en"
    ticker = stock["ticker"]
    company = stock["company"] or ticker
    sector = stock["sector"] or ("Unknown" if en else "未知")
    price = stock["price"]
    currency = stock["currency"] or "USD"
    market_cap = stock["market_cap"]
    pe = stock["pe_ratio"]
    high52 = stock["week_52_high"]
    low52 = stock["week_52_low"]
    description = stock.get("description", "")

    paragraphs: list[str] = []

    # --- Business overview ---
    if description:
        overview = description[:400].rstrip()
        if not overview.endswith("."):
            overview = overview.rsplit(" ", 1)[0] + "..."
        paragraphs.append((f"**Business Overview:** {overview}") if en else (f"**公司概况：** {overview}"))
    else:
        if en:
            paragraphs.append(f"**Business Overview:** {company} ({ticker}) operates in the {sector} sector. No detailed description is available.")
        else:
            paragraphs.append(f"**公司概况：** {company}（{ticker}）属于 {sector} 行业。数据提供方暂无更详细的公司描述。")

    # --- Valuation & size ---
    val_parts: list[str] = []
    if market_cap:
        if market_cap >= 200e9:
            cap_label = "mega-cap" if en else "超大盘股"
        elif market_cap >= 10e9:
            cap_label = "large-cap" if en else "大盘股"
        elif market_cap >= 2e9:
            cap_label = "mid-cap" if en else "中盘股"
        else:
            cap_label = "small-cap" if en else "小盘股"
        if en:
            val_parts.append(f"With a market cap of {currency} {fmt_cap(market_cap, lang)}, {company} is a {cap_label} company.")
        else:
            val_parts.append(f"市值约为 {currency} {fmt_cap(market_cap, lang)}，{company} 属于{cap_label}。")

    if pe is not None:
        if en:
            if pe < 0:
                pe_comment = "The P/E is negative, indicating the company is currently unprofitable."
            elif pe < 15:
                pe_comment = f"A P/E of {pe:.1f} is below market average — possibly undervalued or with muted growth expectations."
            elif pe < 25:
                pe_comment = f"A P/E of {pe:.1f} is roughly in line with the market average."
            elif pe < 50:
                pe_comment = f"A P/E of {pe:.1f} is above average; investors are paying a premium for expected growth."
            else:
                pe_comment = f"A P/E of {pe:.1f} is elevated; significant future growth is already priced in."
        else:
            if pe < 0:
                pe_comment = "市盈率为负，说明公司目前处于亏损状态。"
            elif pe < 15:
                pe_comment = f"市盈率为 {pe:.1f}，低于市场平均水平，可能被低估或市场对其增长预期较低。"
            elif pe < 25:
                pe_comment = f"市盈率为 {pe:.1f}，与市场平均水平大致相当。"
            elif pe < 50:
                pe_comment = f"市盈率为 {pe:.1f}，高于平均水平，投资者为预期增长支付了溢价。"
            else:
                pe_comment = f"市盈率为 {pe:.1f}，处于高位，市场已计入显著的未来增长预期。"
        val_parts.append(pe_comment)
    else:
        val_parts.append("P/E data is unavailable." if en else "暂无市盈率数据。")

    paragraphs.append(("**Valuation:** " if en else "**估值分析：** ") + " ".join(val_parts))

    # --- 52-week price position ---
    if price and high52 and low52 and high52 > low52:
        pct = (price - low52) / (high52 - low52) * 100
        if en:
            range_text = f"At {currency} {price:.2f}, the stock sits ~{pct:.0f}% of the way between its 52-week low ({currency} {low52:.2f}) and high ({currency} {high52:.2f}). "
            if pct >= 80:
                range_comment = "Trading near its annual high — strong momentum but limited near-term upside on range alone."
            elif pct <= 20:
                range_comment = "Trading near its annual low — recent weakness that may be a value opportunity or a sign of deteriorating fundamentals."
            else:
                range_comment = "Trading mid-range, indicating a balanced price trend over the past year."
            paragraphs.append(f"**Price Analysis:** {range_text}{range_comment}")
        else:
            range_text = f"当前价格 {currency} {price:.2f}，位于52周低点（{currency} {low52:.2f}）与高点（{currency} {high52:.2f}）之间约 {pct:.0f}% 的位置。"
            if pct >= 80:
                range_comment = "股价接近年内高点，近期势头强劲，但仅从历史区间看短期上行空间有限。"
            elif pct <= 20:
                range_comment = "股价接近年内低点，近期表现疲弱——这可能是价值机会，也可能反映基本面恶化。"
            else:
                range_comment = "股价处于年内区间中段，过去一年价格走势较为均衡。"
            paragraphs.append(f"**价格分析：** {range_text}{range_comment}")
    elif price:
        paragraphs.append(
            (f"**Price Analysis:** Current price is {currency} {price:.2f}; 52-week range unavailable.")
            if en else (f"**价格分析：** 当前价格 {currency} {price:.2f}，暂无52周区间数据。")
        )

    # --- Analyst target ---
    target = stock.get("target_mean_price")
    upside = compute_upside(price, target)
    if target and upside is not None:
        if en:
            direction = "upside" if upside >= 0 else "downside"
            paragraphs.append(f"**Analyst Target:** The mean target is {currency} {target:.2f}, implying {abs(upside):.1f}% {direction} from {currency} {price:.2f}.")
        else:
            direction = "上涨" if upside >= 0 else "下跌"
            paragraphs.append(f"**分析师目标价：** 分析师平均目标价为 {currency} {target:.2f}，相比当前价格 {currency} {price:.2f} 隐含 {abs(upside):.1f}% 的{direction}空间。")

    # --- Recent news ---
    news = stock.get("news", [])
    if news:
        if en:
            headlines = "; ".join(f'"{n.title}"' for n in news[:3])
            paragraphs.append(f"**Recent News ({len(news)}):** Recent coverage includes {headlines}. Consider these alongside company strategy and sector trends.")
        else:
            headlines = "；".join(f'「{n.title}」' for n in news[:3])
            paragraphs.append(f"**近期新闻（{len(news)} 条）：** 最近报道包括 {headlines}。投资者应结合公司战略与行业趋势综合判断这些动态。")
    else:
        paragraphs.append("**Recent News:** No recent headlines available." if en else "**近期新闻：** 数据提供方暂无最新新闻。")

    # --- Risks & opportunities ---
    risks: list[str] = []
    opportunities: list[str] = []
    if en:
        if pe and pe > 40:
            risks.append("high valuation multiples leave little room for earnings misses")
        if price and high52 and price >= 0.95 * high52:
            risks.append("price near 52-week high amplifies downside on any bad news")
        if market_cap and market_cap < 2e9:
            risks.append("small-caps carry higher liquidity and volatility risk")
        if pe and 0 < pe < 15:
            opportunities.append("a low P/E may offer a margin of safety")
        if price and low52 and price <= 1.1 * low52:
            opportunities.append("price near 52-week low may be a contrarian entry")
        if market_cap and market_cap >= 10e9:
            opportunities.append("large market cap implies mature operations and analyst coverage")
        risk_text = ("; ".join(risks) + ".") if risks else "No clear red flags from available metrics."
        opp_text = ("; ".join(opportunities) + ".") if opportunities else "No standout positives from available metrics."
        paragraphs.append(f"**Investment Considerations:** Risks: {risk_text} Opportunities: {opp_text} Auto-generated from public data; not investment advice.")
    else:
        if pe and pe > 40:
            risks.append("估值倍数偏高，业绩不及预期时回调风险较大")
        if price and high52 and price >= 0.95 * high52:
            risks.append("股价接近52周高点，任何利空都可能放大下行风险")
        if market_cap and market_cap < 2e9:
            risks.append("小盘股通常流动性和波动性风险较高")
        if pe and 0 < pe < 15:
            opportunities.append("较低的市盈率可能提供安全边际")
        if price and low52 and price <= 1.1 * low52:
            opportunities.append("股价接近52周低点，可能是逆向布局的入场点")
        if market_cap and market_cap >= 10e9:
            opportunities.append("较大市值意味着业务成熟、机构覆盖充分")
        risk_text = ("；".join(risks) + "。") if risks else "现有指标未发现明显风险信号。"
        opp_text = ("；".join(opportunities) + "。") if opportunities else "仅凭现有指标未发现突出亮点。"
        paragraphs.append(f"**投资考量：** 潜在风险：{risk_text} 潜在机会：{opp_text} 本摘要基于公开财务数据自动生成，不构成投资建议。")

    return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

PAGE_CSS = """
<style>
  :root{
    --bg:#f9fafb; --card:#ffffff; --tile:#f8fafc; --text:#111827; --muted:#64748b;
    --border:#eef2f7; --border2:#f1f5f9; --accent:#1e3a5f; --accent2:#2d5480;
    --chip-bg:#eff6ff; --chip-tx:#1e3a5f; --th-bg:#f1f5f9; --th-tx:#334155;
    --link:#2563eb; --input-bd:#d1d5db; --shadow:rgba(0,0,0,.08); --overlay:rgba(249,250,251,.9);
    --up:#166534; --down:#991b1b;
  }
  :root[data-theme="dark"]{
    --bg:#0f172a; --card:#1e293b; --tile:#243449; --text:#e2e8f0; --muted:#94a3b8;
    --border:#334155; --border2:#334155; --accent:#93c5fd; --accent2:#bfdbfe;
    --chip-bg:#334155; --chip-tx:#dbeafe; --th-bg:#273449; --th-tx:#cbd5e1;
    --link:#60a5fa; --input-bd:#475569; --shadow:rgba(0,0,0,.4); --overlay:rgba(15,23,42,.9);
    --up:#4ade80; --down:#f87171;
  }
  @media(prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#0f172a; --card:#1e293b; --tile:#243449; --text:#e2e8f0; --muted:#94a3b8;
      --border:#334155; --border2:#334155; --accent:#93c5fd; --accent2:#bfdbfe;
      --chip-bg:#334155; --chip-tx:#dbeafe; --th-bg:#273449; --th-tx:#cbd5e1;
      --link:#60a5fa; --input-bd:#475569; --shadow:rgba(0,0,0,.4); --overlay:rgba(15,23,42,.9);
      --up:#4ade80; --down:#f87171;
    }
  }
  body{font-family:system-ui,sans-serif;margin:0;padding:0;background:var(--bg);color:var(--text);}
  .layout{display:flex;gap:28px;max-width:1180px;margin:40px auto;padding:0 20px;align-items:flex-start;}
  .main{flex:1;min-width:0;}
  .sidebar{width:240px;flex-shrink:0;background:var(--card);border-radius:10px;padding:18px 16px;box-shadow:0 2px 8px var(--shadow);position:sticky;top:40px;}
  .sidebar h4{margin:0 0 10px;color:var(--accent);font-size:15px;border-bottom:1px solid var(--border);padding-bottom:6px;}
  .sidebar .cat{border-bottom:1px solid var(--border2);}
  .sidebar .cat>summary{cursor:pointer;list-style:none;padding:9px 4px;color:var(--accent);font-size:14px;font-weight:600;display:flex;align-items:center;justify-content:space-between;user-select:none;}
  .sidebar .cat>summary::-webkit-details-marker{display:none;}
  .sidebar .cat>summary::after{content:"▾";font-size:11px;color:var(--muted);transition:transform .15s;}
  .sidebar .cat[open]>summary::after{transform:rotate(180deg);}
  .sidebar .cat>summary:hover{color:var(--accent2);}
  .sidebar .cat-stocks{display:flex;flex-wrap:wrap;gap:6px;padding:2px 0 12px;}
  .sidebar a.tk{display:inline-block;background:var(--chip-bg);color:var(--chip-tx);text-decoration:none;padding:4px 10px;border-radius:6px;font-size:13px;font-weight:600;transition:background .15s;}
  .sidebar a.tk:hover{background:var(--accent);color:#fff;}
  @media(max-width:860px){.layout{flex-direction:column;}.sidebar{width:auto;position:static;}}
  h1{color:var(--accent);}
  input{padding:10px 14px;font-size:16px;border:1px solid var(--input-bd);border-radius:6px;width:200px;background:var(--card);color:var(--text);}
  button{padding:10px 20px;font-size:16px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;margin-left:8px;}
  .card{margin-top:30px;background:var(--card);border-radius:10px;padding:24px;box-shadow:0 2px 8px var(--shadow);}
  .metric{display:inline-block;background:var(--chip-bg);color:var(--chip-tx);border-radius:6px;padding:6px 12px;margin:4px;font-size:14px;}
  h2{color:var(--accent);border-bottom:2px solid var(--border);padding-bottom:8px;}
  h3{color:var(--text);}
  ul{padding-left:18px;}
  li{margin-bottom:6px;}
  a{color:var(--link);}
  .error{color:#dc2626;font-weight:bold;}
  table{width:100%;border-collapse:collapse;margin:8px 0 4px;}
  th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--border);font-size:15px;}
  th{background:var(--th-bg);color:var(--th-tx);font-weight:600;width:40%;}
  td.up{color:var(--up);font-weight:600;}
  td.down{color:var(--down);font-weight:600;}
  .score-table{width:100%;border-collapse:collapse;border-radius:10px;overflow:hidden;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
  .score-table td{border:none;padding:14px 18px;color:#fff;vertical-align:middle;}
  .score-table .score-num-cell{font-size:44px;font-weight:800;width:110px;text-align:center;}
  .score-table .score-label-cell{font-size:24px;font-weight:700;width:120px;}
  .score-table .score-reason-cell{font-size:14px;line-height:1.6;}
  .sc-bullish td{background:linear-gradient(135deg,#16a34a,#22c55e);}
  .sc-neutral td{background:linear-gradient(135deg,#64748b,#94a3b8);}
  .sc-bearish td{background:linear-gradient(135deg,#dc2626,#ef4444);}
  .score-den{font-size:18px;font-weight:500;opacity:.85;}
  .topbar{display:flex;justify-content:space-between;align-items:center;gap:8px;}
  .topbar-btns{display:flex;gap:8px;flex-shrink:0;}
  .lang-btn,.theme-btn{background:var(--card);border:1px solid var(--input-bd);border-radius:6px;padding:6px 12px;font-size:14px;text-decoration:none;color:var(--accent);white-space:nowrap;cursor:pointer;}
  .lang-btn:hover,.theme-btn:hover{background:var(--accent);color:#fff;}
  /* Dashboard stat tiles */
  .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0 6px;}
  .stat{background:var(--tile);border:1px solid var(--border);border-radius:12px;padding:14px 16px;}
  .stat .s-label{font-size:12px;color:var(--muted);margin-bottom:5px;}
  .stat .s-value{font-size:21px;font-weight:700;color:var(--accent);line-height:1.2;word-break:break-word;}
  .stat .s-value.up{color:var(--up);}
  .stat .s-value.down{color:var(--down);}
  .stat.hero{background:linear-gradient(135deg,#1e3a5f,#2d5480);border:none;}
  .stat.hero .s-label{color:#c7d6e8;}
  .stat.hero .s-value{color:#fff;font-size:24px;}
  /* Featured mini cards + sparklines */
  .featured-h{color:var(--accent);font-size:17px;margin:26px 0 10px;}
  .mini-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;}
  .mini{display:block;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:13px 15px;text-decoration:none;color:var(--text);box-shadow:0 1px 4px var(--shadow);transition:transform .12s,box-shadow .12s;}
  .mini:hover{transform:translateY(-2px);box-shadow:0 4px 12px var(--shadow);}
  .mini-top{display:flex;justify-content:space-between;align-items:baseline;}
  .mini-tk{font-weight:800;color:var(--accent);font-size:15px;}
  .mini-chg{font-size:13px;font-weight:700;}
  .mini-chg.up{color:var(--up);} .mini-chg.down{color:var(--down);}
  .mini-price{font-size:19px;font-weight:700;margin:4px 0 6px;}
  .mini-spark{height:34px;}
  .mini-spark svg{width:100%;height:34px;display:block;}
  /* Loading overlay */
  .loading-overlay{position:fixed;inset:0;background:var(--overlay);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;flex-direction:column;z-index:9999;}
  .loading-overlay.show{display:flex;}
  .spinner{width:46px;height:46px;border:4px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
  .loading-text{margin-top:16px;color:var(--accent);font-weight:600;font-size:15px;}
</style>
"""

STOCK_CATEGORIES = [
    ("🌟 七巨头", "🌟 Magnificent 7", ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]),
    ("💻 半导体", "💻 Semiconductors", ["NVDA", "AMD", "AVGO", "TSM", "INTC", "QCOM", "ASML", "MU"]),
    ("💾 存储/内存", "💾 Memory/Storage", ["MU", "WDC", "STX", "SNDK"]),
    ("🔦 CPO 光模块", "🔦 CPO/Optics", ["COHR", "LITE", "FN", "CRDO", "ALAB", "AAOI", "POET", "MRVL"]),
    ("☁️ 云与软件", "☁️ Cloud & Software", ["MSFT", "ORCL", "CRM", "ADBE", "NOW", "SNOW"]),
    ("🚗 电动车", "🚗 EV", ["TSLA", "RIVN", "LCID", "NIO", "XPEV"]),
    ("🏦 金融", "🏦 Finance", ["JPM", "BAC", "GS", "MS", "V", "MA"]),
    ("⚛️ 核电", "⚛️ Nuclear", ["CEG", "VST", "NRG", "SMR", "OKLO", "CCJ", "LEU"]),
    ("🚀 航天", "🚀 Space", ["RKLB", "LUNR", "ASTS", "RDW", "BA", "LMT", "NOC", "RTX"]),
    ("₿ 虚拟币相关", "₿ Crypto", ["COIN", "MSTR", "MARA", "RIOT", "HOOD", "CLSK"]),
    ("📊 大盘 ETF", "📊 Index ETFs", ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO"]),
    ("💊 医药生物", "💊 Healthcare", ["LLY", "JNJ", "UNH", "PFE", "MRK", "ABBV", "AMGN", "MRNA"]),
    ("🛢️ 能源石油", "🛢️ Energy", ["XOM", "CVX", "COP", "SLB", "OXY", "EOG", "PSX"]),
    ("🐉 中概股", "🐉 China ADRs", ["BABA", "PDD", "JD", "BIDU", "NIO", "LI", "TCEHY"]),
    ("🧪 演示", "🧪 Demo", ["DEMO"]),
]

# UI label translations
T = {
    "zh": {
        "title": "📈 股票研究助手",
        "app_name": "股票研究",
        "subtitle": "输入股票代码，或从右侧板块中选择，获取实时价格、财报分析、目标价与投资评分。",
        "placeholder": "例如 NVDA、AAPL、TSLA、DEMO",
        "analyze": "分析",
        "sectors": "📂 热门板块",
        "lang_switch": "English",
        "price": "当前价格", "target": "分析师目标价", "upside": "上涨/下跌空间",
        "mcap": "市值", "pe": "市盈率 (P/E)", "high52": "52周最高", "low52": "52周最低",
        "sector": "行业", "na_company": "未知公司",
        "chart": "📈 价格走势", "no_chart": "暂无价格走势数据。",
        "earnings": "💰 财报分析", "latest_q": "最新季度",
        "eps_actual": "每股收益 (EPS) 实际", "eps_est": "EPS 预期", "eps_beat": "EPS 超预期",
        "rev_actual": "营收实际", "rev_est": "营收预期", "rev_beat": "营收超预期", "rev_yoy": "营收同比 (YoY)",
        "q": "季度", "no_earnings": "暂无财报数据。",
        "news": "📰 最新新闻", "no_news": "暂无新闻。",
        "summary": "📋 投资摘要", "saved": "报告已保存 — 编号",
        "loading": "分析中，请稍候…",
        "featured": "🔥 热门股票", "theme_label": "深色/浅色",
        "err_empty": "请输入股票代码。",
        "err_fetch": "获取数据出错：",
        "err_noprice": "未找到「{t}」的价格数据，请检查代码是否正确。",
    },
    "en": {
        "title": "📈 Stock Research Assistant",
        "app_name": "StockResearch",
        "subtitle": "Enter a ticker, or pick from the sectors at right, for live price, earnings analysis, target price and an investment score.",
        "placeholder": "e.g. NVDA, AAPL, TSLA, DEMO",
        "analyze": "Analyze",
        "sectors": "📂 Sectors",
        "lang_switch": "中文",
        "price": "Current Price", "target": "Analyst Target", "upside": "Upside/Downside",
        "mcap": "Market Cap", "pe": "P/E Ratio", "high52": "52W High", "low52": "52W Low",
        "sector": "Sector", "na_company": "Unknown",
        "chart": "📈 Price Chart", "no_chart": "No price history available.",
        "earnings": "💰 Earnings Analysis", "latest_q": "latest quarter",
        "eps_actual": "EPS Actual", "eps_est": "EPS Estimate", "eps_beat": "EPS Surprise",
        "rev_actual": "Revenue Actual", "rev_est": "Revenue Estimate", "rev_beat": "Revenue Surprise", "rev_yoy": "Revenue YoY",
        "q": "Quarter", "no_earnings": "No earnings data available.",
        "news": "📰 Latest News", "no_news": "No recent news.",
        "summary": "📋 Investment Summary", "saved": "Report saved — ID",
        "loading": "Analyzing, please wait…",
        "featured": "🔥 Trending", "theme_label": "Dark/Light",
        "err_empty": "Please enter a ticker.",
        "err_fetch": "Error fetching data: ",
        "err_noprice": 'No price data found for "{t}". Check the symbol.',
    },
}


_CHART_TEMPLATE = """
<script>
(function(){
  var dates = __DATES__, closes = __CLOSES__, prefix = __PREFIX__;
  var gd = document.getElementById('priceChart');
  if(!gd || !window.Plotly || !dates.length) return;

  var up = closes[closes.length-1] >= closes[0];
  var color = up ? '#16a34a' : '#dc2626';
  var fill = up ? 'rgba(22,163,74,0.08)' : 'rgba(220,38,38,0.08)';

  var trace = {x:dates, y:closes, type:'scatter', mode:'lines',
    line:{color:color, width:2}, fill:'tozeroy', fillcolor:fill,
    hovertemplate:'%{x|%Y-%m-%d}<br>'+prefix+'%{y:,.2f}<extra></extra>'};

  // default to the most recent 1 year
  var last = dates[dates.length-1];
  var d = new Date(last); d.setFullYear(d.getFullYear()-1);
  var start1y = d.toISOString().slice(0,10);

  function yRange(lo, hi){
    var loD = new Date(lo), hiD = new Date(hi), ys = [];
    for(var i=0;i<dates.length;i++){var dd=new Date(dates[i]); if(dd>=loD&&dd<=hiD) ys.push(closes[i]);}
    if(!ys.length) return null;
    var mn=Math.min.apply(null,ys), mx=Math.max.apply(null,ys);
    var pad=(mx-mn)*0.08 || mx*0.05; return [Math.max(0,mn-pad), mx+pad];
  }

  var layout = {
    autosize:true,
    margin:{l:55,r:15,t:10,b:30},
    xaxis:{type:'date', range:[start1y,last], rangeslider:{visible:false},
      rangeselector:{x:0, y:1.12, buttons:[
        {count:1, label:'1M', step:'month', stepmode:'backward'},
        {count:3, label:'3M', step:'month', stepmode:'backward'},
        {count:1, label:'1Y', step:'year', stepmode:'backward'},
        {step:'all', label:'5Y'}
      ]}},
    yaxis:{tickprefix:prefix, fixedrange:true},
    plot_bgcolor:'#fff', paper_bgcolor:'#fff', showlegend:false
  };
  var yr = yRange(start1y, last); if(yr) layout.yaxis.range = yr;

  Plotly.newPlot(gd, [trace], layout, {responsive:true, displayModeBar:false}).then(function(){
    // re-measure once CSS layout has settled so the chart fits its card
    Plotly.Plots.resize(gd);
    setTimeout(function(){ Plotly.Plots.resize(gd); }, 100);
  });
  window.addEventListener('resize', function(){ Plotly.Plots.resize(gd); });

  gd.on('plotly_relayout', function(e){
    var lo, hi;
    if(e['xaxis.range[0]']){ lo=e['xaxis.range[0]']; hi=e['xaxis.range[1]']; }
    else if(e['xaxis.range']){ lo=e['xaxis.range'][0]; hi=e['xaxis.range'][1]; }
    else if(e['xaxis.autorange']){ lo=dates[0]; hi=last; }
    else return;
    var yr2 = yRange(lo, hi);
    if(yr2) Plotly.relayout(gd, {'yaxis.range': yr2});
  });
})();
</script>
"""


def sidebar_html(lang: str = "zh") -> str:
    sections = []
    for i, (zh_title, en_title, tickers) in enumerate(STOCK_CATEGORIES):
        title = en_title if lang == "en" else zh_title
        links = "".join(
            f'<a class="tk" href="/research-page?ticker={tk}&lang={lang}">{tk}</a>' for tk in tickers
        )
        # 第一个板块默认展开
        open_attr = " open" if i == 0 else ""
        sections.append(
            f'<details class="cat"{open_attr}><summary>{title}</summary>'
            f'<div class="cat-stocks">{links}</div></details>'
        )
    return f'<aside class="sidebar"><h4 style="font-size:15px">{T[lang]["sectors"]}</h4>{"".join(sections)}</aside>'


# Runs before paint to apply saved theme (avoids a light->dark flash).
_THEME_INIT = "try{var _t=localStorage.getItem('theme');if(_t)document.documentElement.setAttribute('data-theme',_t);}catch(e){}"

# Main client script: loading overlay, theme toggle, featured mini-card loader.
_APP_JS = """
(function(){
  var ov=document.getElementById('loadingOverlay');
  function showLoading(){if(ov)ov.classList.add('show');}
  document.querySelectorAll('form').forEach(function(f){f.addEventListener('submit',showLoading);});
  document.querySelectorAll('a.tk,a.lang-btn,a.mini').forEach(function(a){a.addEventListener('click',showLoading);});
  window.addEventListener('pageshow',function(){if(ov)ov.classList.remove('show');});

  // Theme toggle (light <-> dark, persisted in localStorage)
  var tb=document.getElementById('themeBtn');
  function curTheme(){
    var a=document.documentElement.getAttribute('data-theme');
    if(a)return a;
    return (window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light';
  }
  function setIcon(){if(tb)tb.textContent=curTheme()==='dark'?'☀️':'🌙';}
  setIcon();
  if(tb)tb.addEventListener('click',function(){
    var next=curTheme()==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',next);
    try{localStorage.setItem('theme',next);}catch(e){}
    setIcon();
  });

  // Featured mini cards: draw sparkline SVG from returned closes
  function spark(el,pts,up){
    if(!pts||pts.length<2){el.innerHTML='';return;}
    var w=100,h=34,mn=Math.min.apply(null,pts),mx=Math.max.apply(null,pts),rng=(mx-mn)||1;
    var d=pts.map(function(v,i){var x=i/(pts.length-1)*w;var y=h-((v-mn)/rng)*(h-4)-2;return (i?'L':'M')+x.toFixed(1)+' '+y.toFixed(1);}).join(' ');
    var col=up?'#22c55e':'#ef4444';
    el.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none"><path d="'+d+'" fill="none" stroke="'+col+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>';
  }
  document.querySelectorAll('.mini').forEach(function(c){
    var tk=c.getAttribute('data-ticker');
    fetch('/api/mini?ticker='+encodeURIComponent(tk)).then(function(r){return r.json();}).then(function(d){
      var pe=c.querySelector('.mini-price'),ce=c.querySelector('.mini-chg'),se=c.querySelector('.mini-spark');
      if(d.price==null){pe.textContent='N/A';return;}
      pe.textContent=(d.currency?d.currency+' ':'')+d.price.toFixed(2);
      var up=(d.change_pct||0)>=0;
      ce.textContent=(d.change_pct==null)?'':((up?'+':'')+d.change_pct.toFixed(2)+'%');
      ce.className='mini-chg '+(up?'up':'down');
      spark(se,d.spark,up);
    }).catch(function(){var pe=c.querySelector('.mini-price');if(pe)pe.textContent='N/A';});
  });

  if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){});});}
})();
"""


def page(body: str, ticker: str = "", lang: str = "zh") -> str:
    t = T[lang]
    other = "en" if lang == "zh" else "zh"
    tk_q = f"&ticker={ticker}" if ticker else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<script>{_THEME_INIT}</script>
<title>{t['title']}</title>
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#1e3a5f">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="{t['app_name']}">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<link rel="icon" type="image/png" href="/static/icon-192.png">
{PAGE_CSS}
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script></head>
<body>
<div class="layout">
  <div class="main">
    <div class="topbar">
      <h1>{t['title']}</h1>
      <div class="topbar-btns">
        <button type="button" id="themeBtn" class="theme-btn" title="{t['theme_label']}">🌙</button>
        <a href="/research-page?lang={other}{tk_q}" class="lang-btn">🌐 {t['lang_switch']}</a>
      </div>
    </div>
    <p>{t['subtitle']}</p>
    <form method="post" action="/research-page">
      <input type="hidden" name="lang" value="{lang}">
      <input name="ticker" type="text" placeholder="{t['placeholder']}" value="{ticker}" maxlength="10" autofocus>
      <button type="submit">{t['analyze']}</button>
    </form>
    {body}
  </div>
  {sidebar_html(lang)}
</div>
<div class="loading-overlay" id="loadingOverlay">
  <div class="spinner"></div>
  <div class="loading-text">{t['loading']}</div>
</div>
<script>{_APP_JS}</script>
</body>
</html>"""


def _norm_lang(lang: str) -> str:
    return "en" if (lang or "").lower().startswith("en") else "zh"


# --- PWA: manifest, service worker, offline ---
_MANIFEST = {
    "name": "股票研究助手 · Financial Research Assistant",
    "short_name": "股票研究",
    "description": "实时行情、财报分析、投资评分 · Live stock research & scoring",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#f9fafb",
    "theme_color": "#1e3a5f",
    "icons": [
        {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}

_SERVICE_WORKER = """
const CACHE = 'fra-v1';
const SHELL = ['/', '/static/icon-192.png', '/static/apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});

// Network-first for pages (fresh data); cache-first for static icons.
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match('/')))
  );
});
"""


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(_MANIFEST, media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # Served from root so its scope covers the whole site.
    return PlainTextResponse(
        _SERVICE_WORKER,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/api/mini")
def api_mini(ticker: str = ""):
    ticker = ticker.strip().upper()
    if not ticker:
        return JSONResponse({"error": "no ticker"}, status_code=400)
    return JSONResponse(fetch_mini(ticker))


@app.get("/", response_class=HTMLResponse)
def root(lang: str = "zh"):
    lang = _norm_lang(lang)
    return page(featured_html(lang), lang=lang)


@app.get("/research-page", response_class=HTMLResponse)
def research_page_get(ticker: str = "", lang: str = "zh"):
    return research_page(ticker, lang)

@app.post("/research-page", response_class=HTMLResponse)
def research_page(ticker: str = Form(""), lang: str = Form("zh")):
    lang = _norm_lang(lang)
    t = T[lang]
    ticker = ticker.strip().upper()
    if not ticker:
        return page(f'<p class="error">{t["err_empty"]}</p>', lang=lang)
    try:
        stock = fetch_stock_data(ticker)
    except Exception as exc:
        return page(f'<p class="error">{t["err_fetch"]}{exc}</p>', ticker, lang)
    if stock["price"] is None:
        return page(f'<p class="error">{t["err_noprice"].format(t=ticker)}</p>', ticker, lang)

    # --- Earnings (DEMO uses canned data; real tickers query yfinance) ---
    if ticker == "DEMO":
        earnings = {**_DEMO_EARNINGS}
    else:
        try:
            session = _yf_session()
            te = yf.Ticker(ticker, session=session) if session else yf.Ticker(ticker)
            earnings = fetch_earnings(te)
        except Exception:
            earnings = None

    # --- Price history for the chart ---
    history = fetch_price_history(ticker)

    summary = generate_summary(stock, lang)
    scoring = compute_score(stock, lang)
    news_json = json.dumps([n.model_dump() for n in stock["news"]])
    report_data = {**stock, "ai_summary": summary, "news_json": news_json}
    report_data.pop("news", None)
    report_data.pop("description", None)
    report_id = db.save_report(report_data)

    cur = stock["currency"] or "USD"
    num = lambda v: "N/A" if v is None else f"{v:,.2f}"
    news_html = "".join(
        f'<li><a href="{n.link}" target="_blank">{n.title}</a><br><small>{n.publisher} — {n.published}</small></li>'
        for n in stock["news"]
    ) or f"<li>{t['no_news']}</li>"

    summary_html = summary.replace("**", "<strong>", 1)
    while "**" in summary_html:
        summary_html = summary_html.replace("**", "</strong>", 1)
    summary_html = summary_html.replace("\n\n", "</p><p>").replace("\n", "<br>")

    # --- Score banner (table) ---
    score = scoring["score"]
    label = scoring["label"]
    css = scoring["css"]
    sep = "; " if lang == "en" else "；"
    reasons_html = sep.join(scoring["reasons"]) if scoring["reasons"] else ("limited data" if lang == "en" else "数据有限")
    score_table = f"""
  <table class="score-table sc-{css}">
    <tr>
      <td class="score-num-cell">{score}<span class="score-den">/10</span></td>
      <td class="score-label-cell">{label}</td>
      <td class="score-reason-cell">{reasons_html}</td>
    </tr>
  </table>"""

    # --- Dashboard stat tiles ---
    target = stock.get("target_mean_price")
    upside = scoring["upside"]

    def tile(label, value, cls="", hero=False):
        vc = f" {cls}" if cls else ""
        hc = " hero" if hero else ""
        return f'<div class="stat{hc}"><div class="s-label">{label}</div><div class="s-value{vc}">{value}</div></div>'

    tiles = [tile(t["price"], f"{cur} {num(stock['price'])}", hero=True)]
    if target and upside is not None:
        tiles.append(tile(t["target"], f"{cur} {num(target)}"))
        tiles.append(tile(t["upside"], f"{upside:+.1f}%", "up" if upside >= 0 else "down"))
    else:
        tiles.append(tile(t["target"], "N/A"))
    tiles.append(tile(t["mcap"], f"{cur} {fmt_cap(stock['market_cap'], lang)}"))
    tiles.append(tile(t["pe"], num(stock["pe_ratio"])))
    tiles.append(tile(t["high52"], f"{cur} {num(stock['week_52_high'])}"))
    tiles.append(tile(t["low52"], f"{cur} {num(stock['week_52_low'])}"))
    tiles.append(tile(t["sector"], stock["sector"] or "N/A"))
    stats_html = f'<div class="stats">{"".join(tiles)}</div>'

    # --- Earnings analysis ---
    earnings_html = ""
    if earnings:
        e_rows = []
        if earnings.get("eps_actual") is not None:
            ea = earnings["eps_actual"]
            ee = earnings.get("eps_estimate")
            ebp = earnings.get("eps_beat_pct")
            est_txt = num(ee) if ee is not None else "N/A"
            if ebp is not None:
                cls = "up" if ebp >= 0 else "down"
                beat_txt = f'<td class="{cls}">{ebp:+.1f}%</td>'
            else:
                beat_txt = "<td>N/A</td>"
            e_rows.append(f'<tr><th>{t["eps_actual"]}</th><td>{num(ea)}</td></tr>')
            e_rows.append(f'<tr><th>{t["eps_est"]}</th><td>{est_txt}</td></tr>')
            e_rows.append(f'<tr><th>{t["eps_beat"]}</th>{beat_txt}</tr>')

        if earnings.get("revenue_actual") is not None:
            ra = earnings["revenue_actual"]
            re_ = earnings.get("revenue_estimate")
            rbp = earnings.get("revenue_beat_pct")
            e_rows.append(f'<tr><th>{t["rev_actual"]}</th><td>{cur} {fmt_cap(ra, lang)}</td></tr>')
            if re_ is not None:
                e_rows.append(f'<tr><th>{t["rev_est"]}</th><td>{cur} {fmt_cap(re_, lang)}</td></tr>')
                if rbp is not None:
                    cls = "up" if rbp >= 0 else "down"
                    e_rows.append(f'<tr><th>{t["rev_beat"]}</th><td class="{cls}">{rbp:+.1f}%</td></tr>')
            if earnings.get("revenue_yoy") is not None:
                yoy = earnings["revenue_yoy"]
                cls = "up" if yoy >= 0 else "down"
                e_rows.append(f'<tr><th>{t["rev_yoy"]}</th><td class="{cls}">{yoy:+.1f}%</td></tr>')

        # Quarterly EPS history table
        hist_html = ""
        if earnings.get("history"):
            hrows = ""
            for h in earnings["history"]:
                bp = h.get("beat_pct")
                if bp is not None:
                    cls = "up" if bp >= 0 else "down"
                    bp_td = f'<td class="{cls}">{bp:+.1f}%</td>'
                else:
                    bp_td = "<td>N/A</td>"
                he = num(h["eps_estimate"]) if h.get("eps_estimate") is not None else "N/A"
                hrows += (
                    f'<tr><td>{h["quarter"]}</td><td>{num(h["eps_actual"])}</td>'
                    f'<td>{he}</td>{bp_td}</tr>'
                )
            hist_html = f"""
  <table>
    <tr><th>{t["q"]}</th><th>{t["eps_actual"]}</th><th>{t["eps_est"]}</th><th>{t["eps_beat"]}</th></tr>
    {hrows}
  </table>"""

        earnings_summary = generate_earnings_summary(earnings, lang)
        q = earnings.get("quarter") or ""
        q_label = (f" ({t['latest_q']} {q})" if lang == "en" else f"（{t['latest_q']} {q}）") if q else ""
        earnings_html = f"""
  <h3>{t['earnings']}{q_label}</h3>
  <table>
    {''.join(e_rows)}
  </table>
  {hist_html}
  <p>{earnings_summary}</p>"""
    else:
        earnings_html = f"<h3>{t['earnings']}</h3><p>{t['no_earnings']}</p>"

    # --- Interactive Plotly price chart (1M / 3M / 1Y / 5Y) ---
    if history and history.get("dates"):
        chart_js = _CHART_TEMPLATE
        chart_js = chart_js.replace("__DATES__", json.dumps(history["dates"]))
        chart_js = chart_js.replace("__CLOSES__", json.dumps(history["closes"]))
        chart_js = chart_js.replace("__PREFIX__", json.dumps(cur + " "))
        chart_html = f'<h3>{t["chart"]}</h3><div id="priceChart" style="width:100%;height:380px;"></div>{chart_js}'
    else:
        chart_html = f'<h3>{t["chart"]}</h3><p>{t["no_chart"]}</p>'

    body = f"""
<div class="card">
  {score_table}
  <h2>{stock['ticker']} — {stock['company'] or t['na_company']}</h2>
  {stats_html}
  {chart_html}
  {earnings_html}
  <h3>{t['news']}</h3>
  <ul>{news_html}</ul>
  <h3>{t['summary']}</h3>
  <p>{summary_html}</p>
  <p><small>{t['saved']} #{report_id}</small></p>
</div>"""
    return page(body, ticker, lang)


@app.post("/research", response_model=ResearchReport)
def research_ticker(req: ResearchRequest):
    """Fetch stock data, generate AI summary, persist to SQLite, return report."""
    ticker = req.ticker.strip().upper()
    if not ticker:
        raise HTTPException(400, "Ticker cannot be empty")

    # 1. Fetch market data
    try:
        stock = fetch_stock_data(ticker)
    except Exception as exc:
        raise HTTPException(502, f"Failed to fetch data for {ticker}: {exc}")

    if stock["price"] is None:
        raise HTTPException(404, f"No price data found for ticker '{ticker}'. Check the symbol.")

    # 2. Generate rule-based summary
    summary = generate_summary(stock)

    # 3. Save to SQLite
    news_json = json.dumps([n.model_dump() for n in stock["news"]])
    report_data = {**stock, "ai_summary": summary, "news_json": news_json}
    report_data.pop("news", None)
    report_data.pop("description", None)
    report_id = db.save_report(report_data)

    return ResearchReport(
        id=report_id,
        ticker=stock["ticker"],
        company=stock["company"],
        sector=stock["sector"],
        price=stock["price"],
        currency=stock["currency"],
        market_cap=stock["market_cap"],
        pe_ratio=stock["pe_ratio"],
        week_52_high=stock["week_52_high"],
        week_52_low=stock["week_52_low"],
        news=stock["news"],
        ai_summary=summary,
        created_at=datetime.utcnow().isoformat(),
    )


@app.get("/reports", summary="List saved research reports")
def list_reports(limit: int = 20):
    return db.get_reports(limit)


@app.get("/reports/{report_id}", summary="Get a single saved report")
def get_report(report_id: int):
    report = db.get_report(report_id)
    if not report:
        raise HTTPException(404, f"Report {report_id} not found")
    if report.get("news_json"):
        report["news"] = json.loads(report["news_json"])
    return report
