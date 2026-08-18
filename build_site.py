"""build_site.py — JSON ve HTML sayfalarını üretir."""
import json, datetime, logging, shutil
from pathlib import Path
from engine_us import load_raw_data, compute_all

log = logging.getLogger(__name__)

def build(excel_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'data' / 'detail').mkdir(parents=True, exist_ok=True)

    raw    = load_raw_data(excel_path)
    stocks = compute_all(raw)

    # Her hisse için JSON
    for s in stocks:
        p = out_dir / 'data' / 'detail' / f"{s['ticker']}.json"
        p.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')

    # Ana stocks.json
    summary = [{
        'ticker':  s['ticker'],
        'name':    s['name'],
        'sector':  s['sector'],
        'type':    s['type'],
        'mom':     s['mom'],
        'fip':     s['fip'],
        'last_month': s['monthly'][-1] if s['monthly'] else None,
        'prev_month': s['monthly'][-2] if len(s['monthly']) >= 2 else None,
    } for s in stocks]

    (out_dir / 'data' / 'stocks.json').write_text(
        json.dumps(summary, ensure_ascii=False), encoding='utf-8')

    meta = {
        'last_updated': str(raw['last_date']),
        'total':        len(stocks),
        'pos_mom':      sum(1 for s in stocks if s['mom'] and s['mom'] > 0),
        'neg_fip':      sum(1 for s in stocks if s['fip'] and s['fip'] < 0),
        'generated_at': datetime.datetime.utcnow().isoformat(),
    }
    (out_dir / 'data' / 'meta.json').write_text(
        json.dumps(meta, ensure_ascii=False), encoding='utf-8')

    # HTML
    template = Path('template_us.html').read_text(encoding='utf-8')
    (out_dir / 'index.html').write_text(template, encoding='utf-8')

    log.info(f"Site derlendi: {len(stocks)} hisse → {out_dir}")
    return stocks, meta


def build_strategies(stocks, out_dir: Path):
    """Long / Short strateji listelerini üretir."""
    from strategies_us import compute_strategies
    strategies = compute_strategies(stocks)
    (out_dir / 'data' / 'strategies.json').write_text(
        json.dumps(strategies, ensure_ascii=False), encoding='utf-8')

    template = Path('strategies_us.html').read_text(encoding='utf-8')
    (out_dir / 'strategies.html').write_text(template, encoding='utf-8')
    log.info("Strateji sayfası güncellendi.")
