"""
fetch_initial.py — 1680 US hissesi için 24 aylık geçmiş veriyi çeker
ve Excel'e yazar. Sadece ilk kurulumda çalıştırılır.

Kullanım: python fetch_initial.py
"""
import json, math, datetime, time, logging, sys
from pathlib import Path

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler('fetch_initial.log', encoding='utf-8')])
log = logging.getLogger(__name__)

EXCEL_FILE  = 'US_Momentum_Screener.xlsx'
TICKER_FILE = 'tickers.json'
BATCH_SIZE  = 50
BATCH_DELAY = 2.0
MAX_RETRIES = 3

def main():
    import yfinance as yf
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    # Ticker listesini yükle
    data = json.loads(Path(TICKER_FILE).read_text())
    tickers = data['tickers']
    meta    = data['meta']
    log.info(f"{len(tickers)} hisse yüklenди.")

    # Tarih aralığı: 26 ay geriye (12-1M için 13 ay + buffer)
    today      = datetime.date.today()
    start_date = (today - datetime.timedelta(days=26*31)).strftime('%Y-%m-%d')
    end_date   = today.strftime('%Y-%m-%d')
    log.info(f"Veri aralığı: {start_date} → {end_date}")

    # NYSE iş günlerini oluştur
    from engine_us import NYSE_HOLIDAYS
    def trading_days(start, end):
        d, days = start, []
        while d <= end:
            if d.weekday() < 5 and d not in NYSE_HOLIDAYS:
                days.append(d)
            d += datetime.timedelta(days=1)
        return days

    start_d = datetime.date.fromisoformat(start_date)
    all_days = trading_days(start_d, today)
    log.info(f"Toplam işlem günü: {len(all_days)}")

    # Excel oluştur
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'US D Return Data'

    # Başlık satırları
    ws.cell(1, 1, 'US Momentum Screener')
    ws.cell(2, 1, f'Oluşturulma: {today}')
    ws.cell(3, 1, 'Ticker')
    ws.cell(3, 2, 'Name')
    ws.cell(3, 3, 'Sector')
    ws.cell(3, 4, 'Type')

    # Tarih başlıkları (5. sütundan itibaren)
    DATE_COL_START = 5
    for ci, d in enumerate(all_days):
        col = DATE_COL_START + ci
        cell = ws.cell(3, col)
        cell.value = datetime.datetime(d.year, d.month, d.day)
        cell.number_format = 'YYYY-MM-DD'

    # Hisse satırları
    DATA_ROW_START = 4
    ticker_to_row = {}
    for ri, t in enumerate(tickers):
        row = DATA_ROW_START + ri
        m = meta.get(t, {})
        ws.cell(row, 1, t)
        ws.cell(row, 2, m.get('name', ''))
        ws.cell(row, 3, m.get('sector', ''))
        ws.cell(row, 4, 'Stock')
        ticker_to_row[t] = row

    date_to_col = {d: DATE_COL_START + i for i, d in enumerate(all_days)}

    # yfinance'ten veri çek ve Excel'e yaz
    total_batches = (len(tickers) - 1) // BATCH_SIZE + 1
    total_written = 0

    for bi in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[bi:bi+BATCH_SIZE]
        bn    = bi // BATCH_SIZE + 1
        log.info(f"Batch {bn}/{total_batches} ({len(batch)} hisse)...")

        for attempt in range(MAX_RETRIES):
            try:
                raw = yf.download(batch, start=start_date, end=end_date,
                                  progress=False, auto_adjust=True, actions=False)
                if raw is None or raw.empty:
                    log.warning(f"  Batch {bn}: boş veri")
                    break

                if len(batch) == 1:
                    close = raw[['Close']].copy()
                    close.columns = [batch[0]]
                else:
                    close = raw['Close'].copy()

                pct = close.pct_change()

                for t in batch:
                    if t not in pct.columns:
                        continue
                    row = ticker_to_row[t]
                    for dt_idx in pct.index:
                        d = dt_idx.date() if hasattr(dt_idx, 'date') else dt_idx
                        col = date_to_col.get(d)
                        if col is None:
                            continue
                        try:
                            v = float(pct[t].loc[dt_idx])
                            if not (math.isnan(v) or math.isinf(v)):
                                ws.cell(row, col).value = round(v * 100, 8)
                                total_written += 1
                        except:
                            pass
                break
            except Exception as e:
                log.warning(f"  Deneme {attempt+1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)

        if bi + BATCH_SIZE < len(tickers):
            time.sleep(BATCH_DELAY)

    log.info(f"Toplam yazılan: {total_written} hücre")
    wb.save(EXCEL_FILE)
    log.info(f"✅ Excel kaydedildi: {EXCEL_FILE}")

if __name__ == '__main__':
    main()
