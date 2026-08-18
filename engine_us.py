"""
engine_us.py — US Momentum Screener hesap motoru
Wesley Gray 12-1M momentum + FIP metodolojisi
NYSE tatil takvimi dahil
"""
import datetime, math, logging
from pathlib import Path

log = logging.getLogger(__name__)

# ── NYSE Tatil Takvimi ─────────────────────────────────────────────────────
NYSE_HOLIDAYS = {
    # 2024
    datetime.date(2024,  1,  1), datetime.date(2024,  1, 15),
    datetime.date(2024,  2, 19), datetime.date(2024,  3, 29),
    datetime.date(2024,  5, 27), datetime.date(2024,  6, 19),
    datetime.date(2024,  7,  4), datetime.date(2024,  9,  2),
    datetime.date(2024, 11, 28), datetime.date(2024, 12, 25),
    # 2025
    datetime.date(2025,  1,  1), datetime.date(2025,  1,  9),  # Carter mourning
    datetime.date(2025,  1, 20), datetime.date(2025,  2, 17),
    datetime.date(2025,  4, 18), datetime.date(2025,  5, 26),
    datetime.date(2025,  6, 19), datetime.date(2025,  7,  4),
    datetime.date(2025,  9,  1), datetime.date(2025, 11, 27),
    datetime.date(2025, 12, 25),
    # 2026
    datetime.date(2026,  1,  1), datetime.date(2026,  1, 19),
    datetime.date(2026,  2, 16), datetime.date(2026,  4,  3),
    datetime.date(2026,  5, 25), datetime.date(2026,  6, 19),
    datetime.date(2026,  7,  3), datetime.date(2026,  9,  7),
    datetime.date(2026, 11, 26), datetime.date(2026, 12, 25),
}

def _trading_days(start: datetime.date, end: datetime.date):
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in NYSE_HOLIDAYS:
            yield d
        d += datetime.timedelta(days=1)

def _prev_month(y, m):
    return (y, m-1) if m > 1 else (y-1, 12)

def load_raw_data(excel_path: Path) -> dict:
    """Excel'den günlük return verilerini yükler."""
    import openpyxl
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb['US D Return Data']

    TICKER_COL    = 1
    NAME_COL      = 2
    SECTOR_COL    = 3
    TYPE_COL      = 4
    DATE_COL_START= 5
    DATE_ROW      = 3
    DATA_ROW_START= 4

    # Tarih satırını oku
    date_row = list(ws.iter_rows(min_row=DATE_ROW, max_row=DATE_ROW, values_only=True))[0]
    col_to_date = {}
    for i, v in enumerate(date_row[DATE_COL_START-1:], start=DATE_COL_START):
        if isinstance(v, datetime.datetime):
            col_to_date[i] = v.date()

    # Hisse verilerini oku
    daily  = {}
    info   = {}
    last_date = None

    for row in ws.iter_rows(min_row=DATA_ROW_START, max_row=2000, values_only=True):
        t = row[TICKER_COL-1]
        if not t:
            continue
        t = str(t).strip()
        info[t] = {
            'name':   str(row[NAME_COL-1]   or ''),
            'sector': str(row[SECTOR_COL-1] or ''),
            'type':   str(row[TYPE_COL-1]   or 'Stock'),
        }
        daily[t] = {}
        for col, d in col_to_date.items():
            v = row[col-1]
            if v is not None and v != '':
                try:
                    ret = float(v) / 100.0
                    daily[t][d] = ret
                    if last_date is None or d > last_date:
                        last_date = d
                except:
                    pass

    wb.close()
    log.info(f"Yüklendi: {len(daily)} hisse, son tarih: {last_date}")
    return {'daily': daily, 'info': info, 'last_date': last_date}


def calc_momentum_monthly(daily: dict, year: int, month: int) -> float | None:
    """Aylık momentum: (son kapanış - ilk kapanış) / ilk kapanış"""
    import calendar
    first = datetime.date(year, month, 1)
    last  = datetime.date(year, month, calendar.monthrange(year, month)[1])
    days_in_month = sorted(d for d in daily if first <= d <= last)
    if len(days_in_month) < 1:
        return None
    # Kümülatif çarpım
    cum = 1.0
    for d in days_in_month:
        cum *= (1 + daily[d])
    return cum - 1.0


def calc_fip_monthly(daily: dict, year: int, month: int, min_days: int = 1):
    """FIP = momentum × (neg/N - pos/N)"""
    import calendar
    first = datetime.date(year, month, 1)
    last  = datetime.date(year, month, calendar.monthrange(year, month)[1])
    days_in_month = {d: daily[d] for d in daily if first <= d <= last}
    N = len(days_in_month)
    if N < min_days:
        return None, {'neg_count':0,'pos_count':0,'flat_count':0,'total_days':0,'days':[]}
    neg = sum(1 for v in days_in_month.values() if v < 0)
    pos = sum(1 for v in days_in_month.values() if v > 0)
    flt = N - neg - pos
    mom = calc_momentum_monthly(daily, year, month)
    fip = mom * (neg/N - pos/N) if mom is not None else None
    detail = {
        'neg_count': neg, 'pos_count': pos, 'flat_count': flt,
        'total_days': N,
        'days': [{'date': str(d), 'ret': round(v, 8)}
                 for d, v in sorted(days_in_month.items())]
    }
    return fip, detail


def compute_all(raw: dict) -> list:
    """Tüm hisseler için momentum, FIP ve aylık detay hesaplar."""
    last_date = raw['last_date']
    if last_date is None:
        return []
    y, m = last_date.year, last_date.month

    # Son 13 ay listesi
    months = []
    yy, mm = y, m
    for _ in range(13):
        months.append((yy, mm))
        yy, mm = _prev_month(yy, mm)
    months.reverse()

    results = []
    for ticker, daily in raw['daily'].items():
        if not daily:
            continue

        info = raw['info'].get(ticker, {})

        # 12-1M momentum: 12 ay önceki ayın sonu → 1 ay önceki ayın sonu
        y_start, m_start = _prev_month(*_prev_month(y, m))
        # 13 ay öncesi
        yy2, mm2 = y, m
        for _ in range(13):
            yy2, mm2 = _prev_month(yy2, mm2)
        y13, m13 = yy2, mm2

        # 1 ay öncesinin kümülatif getirisi (skip son ay)
        y1, m1 = _prev_month(y, m)

        mom_12_1 = None
        try:
            import calendar
            # 13 ay önce son günü
            d_start_last = datetime.date(y13, m13, calendar.monthrange(y13, m13)[1])
            d_start_avail = [d for d in sorted(daily.keys()) if d <= d_start_last]
            # 1 ay önce son günü
            d_end_last = datetime.date(y1, m1, calendar.monthrange(y1, m1)[1])
            d_end_avail = [d for d in sorted(daily.keys()) if d <= d_end_last]

            if d_start_avail and d_end_avail:
                # Kümülatif çarpım
                cum = 1.0
                for d in sorted(daily.keys()):
                    if d_start_avail[-1] < d <= d_end_avail[-1]:
                        cum *= (1 + daily[d])
                mom_12_1 = cum - 1.0
        except:
            pass

        # Yıllık FIP (son 12 tamamlanmış ay)
        fip_annual = None
        try:
            fip_sum, fip_n = 0.0, 0
            for my, mm2 in months[:-1]:  # son ay hariç
                f, _ = calc_fip_monthly(daily, my, mm2)
                if f is not None:
                    fip_sum += f
                    fip_n   += 1
            if fip_n > 0:
                fip_annual = fip_sum / fip_n
        except:
            pass

        # Aylık detay
        monthly = []
        for my, mm2 in months:
            mom_m, _ = None, None
            fip_m, detail = calc_fip_monthly(daily, my, mm2)
            mom_m = calc_momentum_monthly(daily, my, mm2)

            is_current = (my == last_date.year and mm2 == last_date.month)
            is_partial  = is_current and detail['total_days'] < 15

            if detail['total_days'] == 0:
                continue

            monthly.append({
                'month':      f"{my}-{mm2:02d}",
                'momentum':   round(mom_m,  6) if mom_m  is not None else None,
                'fip':        round(fip_m,  6) if fip_m  is not None else None,
                'neg_count':  detail['neg_count'],
                'pos_count':  detail['pos_count'],
                'flat_count': detail['flat_count'],
                'total_days': detail['total_days'],
                'is_partial': is_partial,
                'days':       detail['days'],
            })

        results.append({
            'ticker':  ticker,
            'name':    info.get('name', ''),
            'sector':  info.get('sector', ''),
            'type':    info.get('type', 'Stock'),
            'mom':     round(mom_12_1,  6) if mom_12_1  is not None else None,
            'fip':     round(fip_annual, 6) if fip_annual is not None else None,
            'monthly': monthly,
        })

    results.sort(key=lambda x: x['mom'] if x['mom'] is not None else -999, reverse=True)
    log.info(f"Hesaplandı: {len(results)} hisse")
    return results
