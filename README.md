# US Momentum Screener

Wesley Gray'in Quantitative Momentum metodolojisi — 1680 ABD hissesi.

## Metodoloji
- **12-1M Momentum**: Son 13 aylık dönemde son ayı atlayarak hesaplanan kümülatif getiri
- **FIP (Frog-in-the-Pan)**: Trendin kalitesini ölçer — negatif FIP = smooth (güvenilir) momentum

## Kurulum (İlk Kez)

1. Bu repoyu GitHub'a yükle
2. GitHub Pages'i `docs/` klasörü için aktif et
3. Actions → "US Momentum — İlk Veri Yükleme" → çalıştır (~90 dk)
4. Tamamlandığında site yayında olur

## Günlük Güncelleme
GitHub Actions her hafta içi NYSE kapanışı sonrası (18:30 UTC) otomatik çalışır.

## Dosya Yapısı
```
├── engine_us.py        # Hesap motoru (NYSE takvimi dahil)
├── fetch.py            # yfinance veri çekme
├── fetch_initial.py    # İlk 24 aylık veri yükleme
├── update_excel.py     # Excel güncelleme
├── build_site.py       # JSON + HTML üretimi
├── strategies_us.py    # Long/Short strateji listeleri
├── run.py              # Ana çalıştırıcı
├── template_us.html    # Screener sayfası
├── strategies_us.html  # Strateji sayfası
├── tickers.json        # 1680 hisse listesi
├── .github/workflows/
│   ├── update.yml          # Günlük güncelleme
│   └── initial_fetch.yml   # İlk kurulum
└── docs/               # GitHub Pages çıktısı
```
