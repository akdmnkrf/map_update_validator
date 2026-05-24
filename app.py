"""Streamlit entry point for Map Update Validator."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from map_validator import __version__
from map_validator.analysis.analyzer import CityAnalyzer
from map_validator.constants import DEFAULT_CITIES, DEFAULT_HIGHWAYS, HIGHWAY_TYPES, TURKISH_CITIES
from map_validator.services.overpass import OverpassClient, build_overpass_query

METRIC_HELP = """
- **changed_ways** — Seçilen aralıkta değişiklik kaydı olan yol sayısı
- **total_km** — Değişen yolların OSRM sürüş mesafesi toplamı (km)
- **Δdistance_km** — Ortalama mesafe farkı (km); ETA için yönsel bir proxy
- **maxspeed_changes** — Hız etiketi güncellemeleri (potansiyel pozitif etki)
- **oneway_changes / access_changes** — Yön ve erişim kısıtları (potansiyel negatif etki)
- **eta_positive_ratio (%)** — Pozitif etki potansiyeli olan yolların oranı
- **eta_negative_ratio (%)** — Negatif etki potansiyeli olan yolların oranı
- **eta_net_impact_score (pp)** — Pozitif oran − negatif oran (yüzde puan)
- **critical_ratio (%)** — (maxspeed + oneway + access) / changed_ways × 100
"""


def _render_sidebar_inputs() -> tuple[dt.date, dt.date, list[str], list[str], bool, bool]:
    today = dt.date.today()
    c1, c2 = st.columns(2)
    start_date = c1.date_input("Başlangıç tarihi", value=today - dt.timedelta(days=30))
    end_date = c2.date_input("Bitiş tarihi", value=today)
    if end_date > today:
        end_date = today
    if start_date > end_date:
        st.warning("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        st.stop()

    selected_highways = st.multiselect(
        "Yol türleri",
        HIGHWAY_TYPES,
        default=DEFAULT_HIGHWAYS,
        help="Analize dahil edilecek highway türleri. Arter yolları seçmek sorguyu hızlandırır.",
    )
    if not selected_highways:
        st.warning("En az bir yol türü seçmelisiniz.")
        st.stop()

    selected_cities = st.multiselect("İller", TURKISH_CITIES, default=DEFAULT_CITIES)
    if st.checkbox("Tüm illeri seç", value=False):
        selected_cities = TURKISH_CITIES.copy()
    if not selected_cities:
        st.warning("En az bir il seçmelisiniz.")
        st.stop()

    show_raw_json = st.checkbox("Overpass JSON çıktısını göster", value=False)
    run = st.button("Analyze", type="primary")
    return start_date, end_date, selected_highways, selected_cities, show_raw_json, run


def _render_map(points: list[tuple[float, float]]) -> None:
    if not points:
        st.info("Haritada gösterilecek veri bulunamadı.")
        return

    df_points = pd.DataFrame(points, columns=["lat", "lon"])
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_points,
        get_position="[lon, lat]",
        get_radius=60,
        get_color=[255, 100, 50],
        pickable=True,
    )
    view = pdk.ViewState(
        latitude=df_points["lat"].mean(),
        longitude=df_points["lon"].mean(),
        zoom=5.5,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view))


def main() -> None:
    st.set_page_config(
        page_title=f"Map Update Validator v{__version__}",
        page_icon="🗺️",
        layout="wide",
    )
    st.title(f"🗺️ Map Update Validator v{__version__} — ETA Etki Oranı + Tag Kırılımı")
    st.caption(
        "Overpass değişimleri · OSRM mesafe ölçümü · ETA etki oranı · tag kırılımı · harita"
    )

    start_date, end_date, selected_highways, selected_cities, show_raw_json, run = _render_sidebar_inputs()

    if not run:
        st.info("Tarih aralığı, il(ler) ve yol türlerini seçip **Analyze** butonuna basın.")
        return

    analyzer = CityAnalyzer()
    overpass = OverpassClient()
    results = []
    all_points: list[tuple[float, float]] = []

    with st.spinner("Overpass ve OSRM sorguları çalışıyor..."):
        for city in selected_cities:
            try:
                query = build_overpass_query(city, start_date, selected_highways)
                overpass_data = overpass.fetch(query)
                if show_raw_json:
                    st.subheader(f"Overpass JSON ({city})")
                    st.json(overpass_data)
                result = analyzer.analyze(
                    city,
                    start_date,
                    end_date,
                    selected_highways,
                    overpass_data=overpass_data,
                )
            except requests.RequestException as exc:
                st.error(f"Analiz hatası ({city}): {exc}")
                continue

            if result is None:
                continue

            results.append(result)
            all_points.extend((point.lat, point.lon) for point in result.map_points)

    if not results:
        st.error("Veri alınamadı. Tarih aralığını, illeri veya yol türlerini değiştirin.")
        return

    df = pd.DataFrame([row.to_row() for row in results]).sort_values(
        "eta_net_impact_score (pp)",
        ascending=False,
    )

    st.subheader("Metrik açıklamaları")
    st.markdown(METRIC_HELP)

    st.subheader("İl bazlı özet")
    st.dataframe(df, use_container_width=True)

    cA, cB, cC, cD = st.columns(4)
    cA.metric("Toplam değişen yol", f"{df['changed_ways'].sum():,}")
    cB.metric("Toplam değişim", f"{df['total_km'].sum():,.1f} km")
    cC.metric("ETA etki oranı (pozitif)", f"{df['eta_positive_ratio (%)'].mean():.1f}%")
    cD.metric("ETA etki oranı (negatif)", f"{df['eta_negative_ratio (%)'].mean():.1f}%")

    st.caption(
        "`eta_net_impact_score (pp)` = pozitif oran − negatif oran. "
        "Pozitif değer, ETA açısından iyileştirici olma ihtimalinin daha yüksek olduğunu gösterir."
    )

    st.subheader("Değişen yolların konumu")
    _render_map(all_points)

    st.download_button(
        "CSV olarak indir",
        data=df.to_csv(index=False),
        file_name=f"map_update_eta_impact_{start_date}_{end_date}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
