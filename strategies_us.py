"""strategies_us.py — US Momentum strateji listeleri."""
import datetime

def compute_strategies(stocks: list) -> dict:
    today = datetime.date.today().isoformat()

    def last_mom(s):
        return s['monthly'][-1]['momentum'] if s['monthly'] else None
    def last_fip(s):
        return s['monthly'][-1]['fip'] if s['monthly'] else None
    def prev_mom(s):
        return s['monthly'][-2]['momentum'] if len(s['monthly']) >= 2 else None
    def prev_fip(s):
        return s['monthly'][-2]['fip'] if len(s['monthly']) >= 2 else None

    # ── Momentum Long ─────────────────────────────────────────────────────
    # 12-1M > 0, aylık mom pozitif, FIP negatif (kaliteli trend)
    long_list = []
    for s in stocks:
        if s['mom'] is None or s['mom'] <= 0:
            continue
        lm = last_mom(s)
        lf = last_fip(s)
        if lm is None or lm <= 0:
            continue
        dm = (lm - prev_mom(s)) if prev_mom(s) is not None else None
        df = (lf - prev_fip(s)) if (lf is not None and prev_fip(s) is not None) else None
        score = (s['mom'] or 0) * 100
        if lf is not None and lf < 0:
            score += 10  # kaliteli momentum bonusu
        long_list.append({
            'ticker': s['ticker'], 'name': s['name'], 'sector': s['sector'],
            'mom_12_1': s['mom'], 'fip_annual': s['fip'],
            'last_month_mom': lm, 'last_month_fip': lf,
            'delta_mom': dm, 'delta_fip': df,
            'score': round(score, 2),
        })

    long_list.sort(key=lambda x: x['score'], reverse=True)

    # ── Momentum Short ────────────────────────────────────────────────────
    # 12-1M < 0, aylık mom negatif ve düşüyor
    short_list = []
    for s in stocks:
        if s['mom'] is None or s['mom'] >= 0:
            continue
        lm = last_mom(s)
        if lm is None or lm >= 0:
            continue
        dm = (lm - prev_mom(s)) if prev_mom(s) is not None else None
        df_val = last_fip(s)
        score  = abs(s['mom']) * 100
        short_list.append({
            'ticker': s['ticker'], 'name': s['name'], 'sector': s['sector'],
            'mom_12_1': s['mom'], 'fip_annual': s['fip'],
            'last_month_mom': lm, 'last_month_fip': df_val,
            'delta_mom': dm, 'score': round(score, 2),
        })

    short_list.sort(key=lambda x: x['score'], reverse=True)

    return {
        'updated':    today,
        'long_count': len(long_list),
        'short_count':len(short_list),
        'long':       long_list[:50],   # Top 50
        'short':      short_list[:50],
    }
