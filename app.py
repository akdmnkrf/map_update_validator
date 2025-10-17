import datetime as dt
import requests
import pandas as pd
import streamlit as st
import pydeck as pdk

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

st.set_page_config(page_title="Map Update Validator v2.1", page_icon="🗺️", layout="wide")
st.title("🗺️ Map Update Validator v2.1 — ETA Etki Oranı + Tag Kırılımı")
st.caption("Overpass değişimleri + OSRM mesafe ölçümü + ETA etki oranı (pozitif/negatif) + tag kırılımı + harita")

# --------------------- Inputs ---------------------
today = dt.date.today()
c1, c2 = st.columns(2)
start_date = c1.date_input("Başlangıç tarihi", value=today - dt.timedelta(days=30))
end_date   = c2.date_input("Bitiş tarihi", value=today)
if end_date > today:
    end_date = today

# Yol türü filtresi
all_highway_types = [
    "motorway","trunk","primary","secondary","tertiary",
    "residential","service","unclassified","track","path","living_street","road"
]
selected_highways = st.multiselect(
    "Yol türleri (multi-select)",
    all_highway_types,
    default=["motorway","trunk","primary","secondary","tertiary"],
    help="Analize dahil edilecek highway türleri. Sadece arterleri (motorway, trunk, primary...) seçmek sorguyu hızlandırır."
)

# Şehir filtresi
all_cities = [
    "Adana","Adıyaman","Afyonkarahisar","Ağrı","Aksaray","Amasya","Ankara","Antalya","Ardahan","Artvin","Aydın",
    "Balıkesir","Bartın","Batman","Bayburt","Bilecik","Bingöl","Bitlis","Bolu","Burdur","Bursa","Çanakkale",
    "Çankırı","Çorum","Denizli","Diyarbakır","Düzce","Edirne","Elazığ","Erzincan","Erzurum","Eskişehir","Gaziantep",
    "Giresun","Gümüşhane","Hakkari","Hatay","Iğdır","Isparta","İstanbul","İzmir","Kahramanmaraş","Karabük",
    "Karaman","Kars","Kastamonu","Kayseri","Kilis","Kırıkkale","Kırklareli","Kırşehir","Kocaeli","Konya","Kütahya",
    "Malatya","Manisa","Mardin","Mersin","Muğla","Muş","Nevşehir","Niğde","Ordu","Osmaniye","Rize","Sakarya","Samsun",
    "Siirt","Sinop","Sivas","Şanlıurfa","Şırnak","Tekirdağ","Tokat","Trabzon","Tunceli","Uşak","Van","Yalova","Yozgat","Zonguldak"
]
selected_cities = st.multiselect("İller (multi-select)", all_cities, default=["Ankara"])
if st.checkbox("Tüm illeri seç", value=False):
    selected_cities = all_cities.copy()

show_raw_json = st.checkbox("Overpass JSON çıktısını göster", value=False)
run = st.button("Analyze")

# --------------------- Helpers ---------------------
def overpass_fetch(query: str):
    try:
        r = requests.post(OVERPASS_URL, data=query, timeout=180)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Overpass hatası: {e}")
        return None

def osrm_distance(lat1, lon1, lat2, lon2):
    try:
        url = f"{OSRM_URL}/{lon1},{lat1};{lon2},{lat2}?overview=false"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data["routes"][0]["distance"] if data["routes"] else 0
    except Exception:
        return 0

def build_overpass_query(city_name, start_dt, highway_types):
    hw_regex = "|".join(highway_types)
    return f"""
[out:json][timeout:180];
area["name"="{city_name}"]->.a;
(
  way["highway"~"{hw_regex}"](newer:"{start_dt}")(area.a);
  way["highway"~"{hw_regex}"]["oneway"](newer:"{start_dt}")(area.a);
  way["highway"~"{hw_regex}"]["maxspeed"](newer:"{start_dt}")(area.a);
  way["highway"~"{hw_regex}"]["access"](newer:"{start_dt}")(area.a);
);
out geom;
""".strip()

# ETA proxy: yönsel etkiyi pozitif/negatif olarak işaretle, katsayıları dengeli tut
def eta_proxy_change(tags, d_new_m):
    """
    tags: OSM tag'leri
    d_new_m: OSRM'in mevcut mesafesi (metre)
    dönüş: (delta_km, impact_label)
      impact_label ∈ {"positive", "negative", "neutral"}
    yorum:
      - maxspeed değişimi genelde ETA'yı iyileştirir (pozitif etki)
      - oneway / access kısıtları genelde ETA'yı kötü etkiler (negatif etki)
    """
    # kalibre katsayılar (daha dengeli)
    if "maxspeed" in tags:
        d_old = d_new_m * 1.10  # hız artışı → eski durumda rota daha uzundu → şimdi daha kısa
        impact = "positive"
    elif "oneway" in tags:
        d_old = d_new_m * 0.95  # yön kısıtı → yeni durumda rota biraz uzadı say
        impact = "negative"
    elif "access" in tags:
        d_old = d_new_m * 0.90  # erişim kısıtı → yeni durumda rota biraz daha uzadı say
        impact = "negative"
    else:
        d_old = d_new_m
        impact = "neutral"
    delta_km = (d_new_m - d_old) / 1000.0
    return round(delta_km, 3), impact

# --------------------- Run ---------------------
if run:
    results = []
    all_points = []

    with st.spinner("Overpass & OSRM sorguları çalışıyor..."):
        for city in selected_cities:
            q = build_overpass_query(city, start_date.strftime("%Y-%m-%dT00:00:00Z"), selected_highways)
            data = overpass_fetch(q)
            if show_raw_json and data:
                st.subheader(f"🧩 Overpass JSON (örnek: {city})")
                st.json(data)

            if not data or "elements" not in data:
                continue

            ways = [el for el in data["elements"] if el["type"] == "way" and "geometry" in el]
            total_ways = len(ways)

            # Tag kırılımı (adet)
            tag_counts = {
                "maxspeed": 0,  # potansiyel POZİTİF etki
                "oneway":   0,  # potansiyel NEGATİF etki
                "access":   0   # potansiyel NEGATİF etki
            }

            distances_m = []
            deltas_km = []
            impacts = []
            coords = []

            for w in ways:
                tags = w.get("tags", {})
                geom = w["geometry"]
                # tag sayaçları
                for k in tag_counts.keys():
                    if k in tags:
                        tag_counts[k] += 1

                if len(geom) >= 2:
                    lat1, lon1 = geom[0]["lat"], geom[0]["lon"]
                    lat2, lon2 = geom[-1]["lat"], geom[-1]["lon"]
                    d_new = osrm_distance(lat1, lon1, lat2, lon2)
                    delta_km, impact = eta_proxy_change(tags, d_new)
                    distances_m.append(d_new)
                    deltas_km.append(delta_km)
                    impacts.append(impact)
                    coords.append((lat1, lon1))

            total_km = sum(distances_m) / 1000.0
            avg_delta_km = sum(deltas_km) / len(deltas_km) if deltas_km else 0.0

            # Pozitif/Negatif etki oranları (adet bazlı)
            pos_cnt = impacts.count("positive")
            neg_cnt = impacts.count("negative")
            # oranları % olarak
            pos_ratio = (pos_cnt / total_ways * 100.0) if total_ways else 0.0
            neg_ratio = (neg_cnt / total_ways * 100.0) if total_ways else 0.0
            # net etki skoru = pozitif - negatif (yüzde puan)
            net_impact_score = pos_ratio - neg_ratio

            # kritik değişim sayısı: (oneway + access + maxspeed)
            critical_changes = tag_counts["oneway"] + tag_counts["access"] + tag_counts["maxspeed"]
            critical_ratio = (critical_changes / total_ways * 100.0) if total_ways else 0.0

            results.append({
                "city": city,
                "changed_ways": total_ways,           # adet
                "total_km": round(total_km, 2),       # km
                "Δdistance_km": round(avg_delta_km, 3),  # km
                # tag kırılımı
                "maxspeed_changes": tag_counts["maxspeed"],
                "oneway_changes": tag_counts["oneway"],
                "access_changes": tag_counts["access"],
                # etki oranları
                "eta_positive_ratio (%)": round(pos_ratio, 2),
                "eta_negative_ratio (%)": round(neg_ratio, 2),
                "eta_net_impact_score (pp)": round(net_impact_score, 2),
                # genel kritik oran
                "critical_changes": critical_changes,
                "critical_ratio (%)": round(critical_ratio, 2),
            })
            all_points.extend(coords)

    if not results:
        st.error("Hiç veri alınamadı. Tarihleri, şehirleri veya yol türlerini değiştir.")
        st.stop()

    df = pd.DataFrame(results).sort_values("eta_net_impact_score (pp)", ascending=False)

    # --------------------- Explanations ---------------------
    st.subheader("📘 Metrik Açıklamaları")
    st.markdown(
        "- `changed_ways` : Seçilen aralıkta değişiklik kaydı olan yol sayısı (adet)\n"
        "- `total_km` : Değişen yolların toplam uzunluğu (OSRM sürüş mesafesi, km)\n"
        "- `Δdistance_km` : OSRM mesafesine göre ortalama fark (km) — ETA için yönsel bir **proxy** (negatif = kısalma, pozitif = uzama)\n"
        "- `maxspeed_changes` : Hız etiketi güncellemeleri (**potansiyel pozitif** etki)\n"
        "- `oneway_changes` / `access_changes` : Yön ve erişim kısıtları (**potansiyel negatif** etki)\n"
        "- `eta_positive_ratio (%)` : Pozitif etki potansiyeli olan yolların oranı (%, adet bazlı)\n"
        "- `eta_negative_ratio (%)` : Negatif etki potansiyeli olan yolların oranı (%, adet bazlı)\n"
        "- `eta_net_impact_score (pp)` : Net etki skoru = pozitif - negatif (yüzde puan cinsinden)\n"
        "- `critical_ratio (%)` : (maxspeed + oneway + access) / changed_ways × 100"
    )

    # --------------------- Table ---------------------
    st.subheader("📊 İl Bazlı Özet (Tag Kırılımı + ETA Etki Oranları)")
    st.dataframe(df, use_container_width=True)

    # --------------------- Top-level metrics ---------------------
    cA, cB, cC, cD = st.columns(4)
    with cA:
        st.metric("Toplam Değişen Yol", f"{df['changed_ways'].sum():,}")
        st.caption("🛣️ Değişiklik kaydı olan yollar (adet).")
    with cB:
        st.metric("Toplam Değişim", f"{df['total_km'].sum():,.1f} km")
        st.caption("📏 OSRM sürüş mesafesi toplamı.")
    with cC:
        st.metric("ETA’ya Etki Oranı (Pozitif)", f"{df['eta_positive_ratio (%)'].mean():.1f}%")
        st.caption("🟢 Hız artışı vb. pozitif sinyallerin oranı (adet bazlı).")
    with cD:
        st.metric("ETA’ya Etki Oranı (Negatif)", f"{df['eta_negative_ratio (%)'].mean():.1f}%")
        st.caption("🔴 Yön/erişim kısıtları vb. negatif sinyallerin oranı (adet bazlı).")

    st.subheader("🧩 Not")
    st.caption("`eta_net_impact_score (pp)` = Pozitif oran − Negatif oran. Pozitif çıkarsa güncellemenin ETA açısından iyileştirici olma ihtimali daha yüksektir.")

    # --------------------- Map ---------------------
    st.subheader("🗺️ Değişen Yolların Konumu (Harita)")
    if all_points:
        df_points = pd.DataFrame(all_points, columns=["lat", "lon"])
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_points,
            get_position='[lon, lat]',
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
    else:
        st.info("Haritada gösterilecek veri bulunamadı.")

    # --------------------- Download ---------------------
    st.download_button(
        "📥 CSV olarak indir",
        data=df.to_csv(index=False),
        file_name=f"map_update_eta_impact_{start_date}_{end_date}.csv",
        mime="text/csv",
    )

else:
    st.info("Tarih aralığı, şehir(ler) ve yol türlerini seçip **Analyze** butonuna bas.")
