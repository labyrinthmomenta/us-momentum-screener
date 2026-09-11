"""strategies_us.py — US Momentum strateji listeleri (S/A-Tier + sinyal skorları)"""
import datetime

def compute_strategies(stocks: list) -> dict:
    today = datetime.date.today().isoformat()

    def lm(s):   return s['monthly'][-1]  if s['monthly']              else {}
    def pm(s):   return s['monthly'][-2]  if len(s['monthly']) >= 2    else {}
    def lmom(s): return lm(s).get('momentum')
    def lfip(s): return lm(s).get('fip')
    def pmom(s): return pm(s).get('momentum')
    def pfip(s): return pm(s).get('fip')

    def pos_months(s):
        """Son 3 ayda kaç ay pozitif momentum"""
        return sum(1 for m in s['monthly'][-3:] if (m.get('momentum') or 0) > 0)

    def tier(s):
        mom = s.get('mom') or 0
        fip = s.get('fip') or 0
        pm3 = pos_months(s)
        if mom > 0.50 and fip < -0.10 and pm3 >= 3: return 'S'
        if mom > 0.20 and fip < -0.05 and pm3 >= 2: return 'A'
        return ''

    # ── LONG ─────────────────────────────────────────────────────────────
    long_list = []
    for s in stocks:
        if not (s.get('mom') and s['mom'] > 0): continue
        lm_val = lmom(s)
        if not (lm_val and lm_val > 0): continue

        lf    = lfip(s)
        dm    = (lm_val - pmom(s)) if pmom(s) is not None else None
        df    = (lf - pfip(s))     if (lf is not None and pfip(s) is not None) else None

        # Skor: 12-1M ağırlıklı + kalite bonusu
        score = (s['mom'] or 0) * 100
        if lf is not None and lf < 0:   score += 15   # kaliteli FIP
        if dm is not None and dm > 0:   score += 10   # ivme artıyor
        t = tier(s)
        if t == 'S': score += 20
        elif t == 'A': score += 10

        long_list.append({
            'ticker': s['ticker'], 'name': s['name'], 'sector': s['sector'],
            'mom_12_1': s['mom'], 'fip_annual': s['fip'], 'tier': t,
            'last_month_mom': lm_val, 'last_month_fip': lf,
            'delta_mom': round(dm, 6) if dm is not None else None,
            'delta_fip': round(df, 6) if df is not None else None,
            'pos_months': pos_months(s),
            'score': round(score, 2),
        })

    long_list.sort(key=lambda x: x['score'], reverse=True)

    # ── SHORT ─────────────────────────────────────────────────────────────
    short_list = []
    for s in stocks:
        if not (s.get('mom') and s['mom'] < 0): continue
        lm_val = lmom(s)
        if not (lm_val and lm_val < 0): continue

        lf = lfip(s)
        dm = (lm_val - pmom(s)) if pmom(s) is not None else None
        df = (lf - pfip(s))     if (lf is not None and pfip(s) is not None) else None

        score = abs(s['mom']) * 100
        if dm is not None and dm < 0: score += 10
        if lf is not None and lf > 0: score += 5

        short_list.append({
            'ticker': s['ticker'], 'name': s['name'], 'sector': s['sector'],
            'mom_12_1': s['mom'], 'fip_annual': s['fip'],
            'last_month_mom': lm_val, 'last_month_fip': lf,
            'delta_mom': round(dm, 6) if dm is not None else None,
            'delta_fip': round(df, 6) if df is not None else None,
            'score': round(score, 2),
        })

    short_list.sort(key=lambda x: x['score'], reverse=True)

    return {
        'updated':    today,
        'long_count': len(long_list),
        'short_count':len(short_list),
        'long':       long_list[:50],
        'short':      short_list[:50],
    }
