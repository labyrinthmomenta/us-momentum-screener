"""update_excel.py — Yeni günlük verileri Excel'e yazar."""
import datetime, logging, openpyxl
from pathlib import Path

log = logging.getLogger(__name__)

SHEET      = 'US D Return Data'
DATE_ROW   = 3
DATA_START = 4
TICKER_COL = 1
DATE_COL_START = 5

def write_new_data(excel_path: Path, fetched: dict):
    """fetched = {date: {ticker: ret_decimal}}"""
    if not fetched:
        return

    wb = openpyxl.load_workbook(excel_path)
    ws = wb[SHEET]

    # Tarih → sütun haritası
    date_row    = list(ws.iter_rows(min_row=DATE_ROW, max_row=DATE_ROW, values_only=True))[0]
    date_to_col = {}
    for i, v in enumerate(date_row[DATE_COL_START-1:], start=DATE_COL_START):
        if isinstance(v, datetime.datetime):
            date_to_col[v.date()] = i

    # Ticker → satır haritası
    ticker_to_row = {}
    for ri, row in enumerate(ws.iter_rows(min_row=DATA_START, max_row=2000, values_only=True)):
        t = row[TICKER_COL-1]
        if t:
            ticker_to_row[str(t).strip()] = ri + DATA_START

    # Yeni tarihler için sütun ekle
    existing_dates = set(date_to_col.keys())
    new_dates      = sorted(set(fetched.keys()) - existing_dates)
    if new_dates:
        max_col = max(date_to_col.values()) if date_to_col else DATE_COL_START - 1
        for nd in new_dates:
            max_col += 1
            cell = ws.cell(DATE_ROW, max_col)
            cell.value = datetime.datetime(nd.year, nd.month, nd.day)
            cell.number_format = 'YYYY-MM-DD'
            date_to_col[nd] = max_col
        log.info(f"{len(new_dates)} yeni tarih sütunu eklendi.")

    written = 0
    for date, day_data in fetched.items():
        col = date_to_col.get(date)
        if col is None:
            continue
        for ticker, ret in day_data.items():
            row = ticker_to_row.get(ticker)
            if row is None:
                continue
            ws.cell(row, col).value = round(ret * 100, 8)
            written += 1

    wb.save(excel_path)
    wb.close()
    log.info(f"Excel güncellendi: {written} hücre yazıldı.")
