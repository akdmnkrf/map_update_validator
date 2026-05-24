# Map Update Validator

OpenStreetMap (OSM) yol değişikliklerini izleyen, Overpass API ile veri çeken ve OSRM mesafe analiziyle ETA etkisini kabaca tahmin eden bir **Streamlit** uygulaması.

## Özellikler

- Türkiye’nin 81 ili ve çoklu yol türü (`highway`) filtresi
- Tarih aralığına göre değişen yolların listelenmesi
- OSRM ile uç noktalar arası sürüş mesafesi
- `maxspeed`, `oneway`, `access` etiketlerine göre tag kırılımı ve ETA etki oranları
- PyDeck ile interaktif harita
- Sonuçların CSV olarak indirilmesi

## Proje yapısı

```
.
├── app.py                      # Streamlit arayüzü (giriş noktası)
├── map_validator/
│   ├── config.py               # API URL’leri ve zaman aşımı ayarları
│   ├── constants.py            # İller, yol türleri, varsayılanlar
│   ├── models.py               # Veri modelleri
│   ├── analysis/
│   │   ├── analyzer.py         # Şehir bazlı analiz akışı
│   │   └── eta.py              # ETA etki heuristiği
│   └── services/
│       ├── overpass.py         # Overpass sorgu ve istemci
│       └── osrm.py             # OSRM mesafe (paralel istek desteği)
├── requirements.txt
└── README.md
```

## Kurulum

Python 3.10+ önerilir.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma

```bash
streamlit run app.py
```

Tarayıcıda tarih aralığı, iller ve yol türlerini seçip **Analyze** ile analizi başlatın.

## Dış servisler

| Servis | Kullanım |
|--------|----------|
| [Overpass API](https://overpass-api.de/) | OSM’de değişen yollar |
| [OSRM](https://router.project-osrm.org/) | Uç noktalar arası sürüş mesafesi |

Her ikisi de herkese açık uç noktalardır; yoğun kullanımda hız sınırı veya zaman aşımı oluşabilir. Üretim ortamında kendi Overpass/OSRM sunucunuzu kullanmanız önerilir.

## Metrikler (özet)

| Metrik | Açıklama |
|--------|----------|
| `changed_ways` | Değişiklik kaydı olan yol sayısı |
| `total_km` | OSRM mesafelerinin toplamı (km) |
| `Δdistance_km` | Ortalama mesafe farkı proxy’si (km) |
| `eta_positive_ratio (%)` | Pozitif etki potansiyeli (ör. hız artışı) |
| `eta_negative_ratio (%)` | Negatif etki potansiyeli (ör. tek yön, erişim) |
| `eta_net_impact_score (pp)` | Pozitif − negatif (yüzde puan) |

ETA etkisi **gerçek rota karşılaştırması değildir**; OSM etiketlerine dayalı bir heuristiktir. Mesafe, yol geometrisinin tamamı yerine ilk ve son nokta arasında ölçülür.

## Yapılandırma

`map_validator/config.py` içinde zaman aşımı süreleri ve OSRM paralel istek sayısı (`OSRM_MAX_WORKERS`) ayarlanabilir.

## Lisans

Bu depoda açık bir lisans dosyası yoktur; kullanım için depo sahibinin politikası geçerlidir.
