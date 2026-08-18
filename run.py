"""run.py — GitHub Actions her gün bunu çağırır."""
import logging, sys, datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('run.log', encoding='utf-8'),
    ]
)
log = logging.getLogger(__name__)

EXCEL_FILE = 'US_Momentum_Screener.xlsx'
OUTPUT_DIR = 'docs'

def main():
    excel = Path(EXCEL_FILE)
    if not excel.exists():
        log.error(f"Excel bulunamadı: {excel}")
        sys.exit(1)

    from engine_us import load_raw_data
    raw       = load_raw_data(excel)
    last_date = raw['last_date']
    log.info(f"Excel son veri: {last_date}")

    # Per-ticker last_date hesapla
    from fetch import fetch_missing_days
    tickers = list(raw['daily'].keys())
    per_ticker_last = {
        t: max(raw['daily'][t].keys())
        for t in tickers if raw['daily'].get(t)
    }

    fetched = fetch_missing_days(tickers, last_date, per_ticker_last)

    if fetched:
        from update_excel import write_new_data
        write_new_data(excel, fetched)
        log.info("Excel güncellendi — yeniden yükleniyor...")
        raw = load_raw_data(excel)

    # Cuma günü strateji listesini güncelle
    from build_site import build, build_strategies
    is_friday = datetime.date.today().weekday() == 4
    force     = '--force-strategy' in sys.argv

    stocks, meta = build(excel, Path(OUTPUT_DIR))

    if is_friday or force:
        build_strategies(stocks, Path(OUTPUT_DIR))
        log.info("Strateji listesi güncellendi.")

    log.info("=" * 50)
    log.info(f"  Son veri     : {meta['last_updated']}")
    log.info(f"  Toplam hisse : {meta['total']}")
    log.info(f"  Pozitif mom  : {meta['pos_mom']}")
    log.info(f"  Negatif FIP  : {meta['neg_fip']} (kaliteli)")
    log.info("=" * 50)

if __name__ == '__main__':
    main()
