import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pyproj import Transformer
import chardet

# CSV 로딩 및 좌표 변환
@st.cache_data
def load_data(file_path):
    with open(file_path, 'rb') as f:
        encoding = chardet.detect(f.read())['encoding']
    df = pd.read_csv(file_path, encoding=encoding)
    df.columns = df.columns.str.strip()

    df = df[[
        "사업장명", "소재지전체주소", "소재지전화", "의료기관종별명",
        "진료과목내용명", "좌표정보x(epsg5174)", "좌표정보y(epsg5174)", "영업상태명"
    ]].dropna(subset=["좌표정보x(epsg5174)", "좌표정보y(epsg5174)"])

    df = df[df["영업상태명"] == "영업/정상"]

    transformer = Transformer.from_crs("epsg:5174", "epsg:4326", always_xy=True)

    def transform_coords(row):
        try:
            lon, lat = transformer.transform(row["좌표정보x(epsg5174)"], row["좌표정보y(epsg5174)"])
            return pd.Series([lat, lon])
        except:
            return pd.Series([None, None])

    df[["위도", "경도"]] = df.apply(transform_coords, axis=1)
    df["시"] = df["소재지전체주소"].apply(lambda x: x.split()[0] if isinstance(x, str) else "")
    df["구"] = df["소재지전체주소"].apply(lambda x: x.split()[1] if isinstance(x, str) and len(x.split()) > 1 else "")
    return df.dropna(subset=["위도", "경도"])

# Streamlit UI
st.set_page_config(layout="wide")
st.title("🏥 시/구 기반 병원 지도 및 상세 정보")

# CSV 경로
csv_path = "전국병원정보.csv"
df = load_data(csv_path)

cities = sorted(df["시"].dropna().unique())
selected_city = st.selectbox("시를 선택하세요", cities)

gus = sorted(df[df["시"] == selected_city]["구"].dropna().unique())
selected_gu = st.selectbox(f"{selected_city}의 구를 선택하세요", gus)

filtered = df[(df["시"] == selected_city) & (df["구"] == selected_gu)]

hospital_names = filtered["사업장명"].tolist()
selected_hospital = st.selectbox("병원을 선택하세요", hospital_names)

hospital_info = filtered[filtered["사업장명"] == selected_hospital].iloc[0]

# 지도 및 정보 시각화
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ 병원 위치 지도")
    m = folium.Map(location=[hospital_info["위도"], hospital_info["경도"]], zoom_start=14)

    for _, row in filtered.iterrows():
        popup_text = f"""
        <b>{row['사업장명']}</b><br>
        주소: {row['소재지전체주소']}<br>
        전화: {row['소재지전화']}<br>
        종별: {row.get('의료기관종별명', '-')},<br>
        진료과: {row.get('진료과목내용명', '-')}
        """
        folium.Marker(
            location=[row["위도"], row["경도"]],
            tooltip=row["사업장명"],  # ✅ 마우스 올렸을 때 병원명만 표시
            popup=popup_text         # ✅ 클릭하면 상세 정보
        ).add_to(m)

    st_folium(m, width=800, height=500)

with col2:
    st.subheader("📋 선택한 병원 정보")
    st.markdown(f"""
    **🏥 병원명:** {hospital_info['사업장명']}  
    **📍 주소:** {hospital_info['소재지전체주소']}  
    **📞 전화번호:** {hospital_info['소재지전화']}  
    **🏷️ 종별:** {hospital_info.get('의료기관종별명', '-')}  
    **💉 진료과목:** {hospital_info.get('진료과목내용명', '-')}
    """)

st.subheader("📊 병원 리스트")
st.dataframe(filtered[["사업장명", "소재지전체주소", "소재지전화", "의료기관종별명", "진료과목내용명"]], use_container_width=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; font-size: 16px;'>
    👉 <a href='https://pharmacyfind-39mmx2wu5khtp9hkeyjeaw.streamlit.app/' target='_blank'>
    💊 약국 위치 확인 페이지로 이동하기
    </a>
</div>
""", unsafe_allow_html=True)
