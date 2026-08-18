"""fetch.py — Günlük eksik veri çekme (per-ticker)"""
import math, datetime, time, logging
from pathlib import Path

log = logging.getLogger(__name__)
BATCH_SIZE  = 50
RETRY_WAIT  = 5
MAX_RETRIES = 3
BATCH_DELAY = 1.0

def fetch_missing_days(tickers, last_filled, per_ticker_last=None):
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance kurulu değil"); return {}

    today = datetime.date.today()
    ticker_missing = {}
    all_missing    = set()

    for t in tickers:
        t_last = per_ticker_last.get(t, last_filled) if per_ticker_last else last_filled
        missing = [d for d in _business_days(t_last + datetime.timedelta(days=1), today)]
        if missing:
            ticker_missing[t] = missing
            all_missing.update(missing)

    if not all_missing:
        log.info("Güncel — çekilecek gün yok."); return {}

    all_sorted  = sorted(all_missing)
    fetch_start = (all_sorted[0]  - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    fetch_end   = (all_sorted[-1] + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    log.info(f"{len(ticker_missing)} hissede eksik veri: {all_sorted[0]} → {all_sorted[-1]}")

    result = {}
    total  = (len(tickers)-1)//BATCH_SIZE + 1

    for bi in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[bi:bi+BATCH_SIZE]
        log.info(f"Batch {bi//BATCH_SIZE+1}/{total}...")
        for attempt in range(MAX_RETRIES):
            try:
                raw = yf.download(batch, start=fetch_start, end=fetch_end,
                                  progress=False, auto_adjust=True, actions=False)
                if raw is None or raw.empty: break
                close = raw[['Close']].copy() if len(batch)==1 else raw['Close'].copy()
                if len(batch)==1: close.columns = [batch[0]]
                pct = close.pct_change()
                for t in batch:
                    if t not in pct.columns: continue
                    t_miss = set(ticker_missing.get(t, []))
                    for dt_idx in pct.index:
                        d = dt_idx.date() if hasattr(dt_idx,'date') else dt_idx
                        if d not in t_miss: continue
                        try:
                            v = float(pct[t].loc[dt_idx])
                            if not (math.isnan(v) or math.isinf(v)):
                                result.setdefault(d, {})[t] = v
                        except: pass
                break
            except Exception as e:
                log.warning(f"  Deneme {attempt+1}: {e}")
                if attempt < MAX_RETRIES-1: time.sleep(RETRY_WAIT)
        if bi+BATCH_SIZE < len(tickers): time.sleep(BATCH_DELAY)

    log.info(f"Çekilen: {len(result)} gün")
    return result

def _business_days(start, end):
    from engine_us import NYSE_HOLIDAYS
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in NYSE_HOLIDAYS:
            yield d
        d += datetime.timedelta(days=1)
