"""Dashboard tương tác (Streamlit) cho mini-project tiêm chủng COVID-19.

Chạy:  streamlit run app.py
"""
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))
from bao_cao import build_report                                   # noqa: E402
from tao_slide import build as build_pptx, tao_md                  # noqa: E402
from phan_tich import (FEATURES, TARGET, chart_confusion, chart_heatmap, chart_scatter,  # noqa: E402
                       classification, regression)
from xu_ly import NGUONG_DAT, PCT_COLS, TEN_BIEN, country_summary, load_clean  # noqa: E402

DEFAULT_CSV = ROOT / "data" / "country_vaccinations.csv"
st.set_page_config(page_title="Tiêm chủng COVID-19", page_icon="💉", layout="wide")


@st.cache_data
def get_data(path):
    df, log = load_clean(path)
    return df, country_summary(df, log), log


st.sidebar.title("⚙️ Tùy chọn")
up = st.sidebar.file_uploader("Tải file CSV khác (cùng cấu trúc)", type="csv")
csv_path = DEFAULT_CSV
if up is not None:
    csv_path = Path(tempfile.mkdtemp()) / "upload.csv"
    csv_path.write_bytes(up.getvalue())
if not Path(csv_path).exists():
    st.error(f"Không tìm thấy {DEFAULT_CSV}. Hãy tải dữ liệu từ Kaggle (xem README) hoặc upload file CSV.")
    st.stop()

df, sm, log = get_data(str(csv_path))

st.title("💉 Tiến độ tiêm chủng COVID-19 toàn cầu")
st.caption("Dữ liệu: Kaggle – COVID-19 World Vaccination Progress (Gabriel Preda, giấy phép CC0; nguồn gốc Our World in Data).")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Quốc gia", len(sm))
c2.metric("Số dòng dữ liệu", f"{len(df):,}")
c3.metric("Trung vị % tiêm đủ liều", f"{sm[TARGET].median():.1f}%")
c4.metric("Giai đoạn", f"{df['date'].min():%m/%Y} – {df['date'].max():%m/%Y}")

tab1, tab2, tab3, tab5, tab4 = st.tabs(["📈 Theo quốc gia", "🔍 Mối liên hệ", "🤖 Hồi quy", "🌳 Phân loại", "📄 Báo cáo"])

with tab1:
    countries = sorted(df["country"].unique())
    default = [c for c in ["Vietnam", "Thailand", "Singapore", "United States", "India"] if c in countries]
    chon = st.multiselect("Chọn quốc gia", countries, default=default)
    metric = st.selectbox("Chọn chỉ số", PCT_COLS + ["daily_vaccinations_per_million"],
                          format_func=lambda c: c.replace("_", " "))
    if chon:
        piv = df[df["country"].isin(chon)].pivot_table(index="date", columns="country", values=metric)
        st.line_chart(piv)
        st.dataframe(sm[sm["country"].isin(chon)].rename(columns=TEN_BIEN).set_index("country").round(1))

with tab2:
    x = st.selectbox("Biến giải thích (trục X)", FEATURES, format_func=TEN_BIEN.get)
    left, right = st.columns(2)
    left.pyplot(chart_scatter(sm, x))
    right.pyplot(chart_heatmap(sm))
    plt.close("all")

with tab3:
    feats = st.multiselect("Chọn biến đưa vào mô hình", FEATURES, default=FEATURES, format_func=TEN_BIEN.get)
    seed = st.slider("random_state (chia train/test)", 0, 100, 42)
    if feats:
        r = regression(sm, feats, seed=seed)
        a, b, c = st.columns(3)
        a.metric("R² train", f"{r['r2_train']:.2f}")
        b.metric("R² test", f"{r['r2_test']:.2f}")
        c.metric("MAE test", f"{r['mae_test']:.1f} điểm %")
        st.bar_chart(r["coef"].rename(index=TEN_BIEN))
        st.caption("Hệ số dương: biến tăng thì tỉ lệ tiêm đủ liều có xu hướng tăng (giữ các biến khác cố định).")

with tab5:
    st.write(f"Cây quyết định dự đoán quốc gia **đạt** (≥ {NGUONG_DAT}% dân số tiêm đủ liều) hay **chưa đạt**.")
    feats_c = st.multiselect("Chọn biến", FEATURES, default=FEATURES, format_func=TEN_BIEN.get, key="fc")
    depth = st.slider("Độ sâu tối đa của cây", 1, 6, 3)
    seed_c = st.slider("random_state", 0, 100, 42, key="sc")
    if feats_c:
        k = classification(sm, feats_c, max_depth=depth, seed=seed_c)
        a, b, c = st.columns(3)
        a.metric("Accuracy test", f"{k['acc_test']:.2f}")
        b.metric("F1 (lớp Đạt)", f"{k['f1_test']:.2f}")
        c.metric("Tỉ lệ quốc gia Đạt", f"{k['ty_le_dat']:.0%}")
        left, right = st.columns(2)
        left.pyplot(chart_confusion(k)); plt.close("all")
        right.bar_chart(k["importance"].rename(index=TEN_BIEN))
        st.code(k["rules"], language="text")

with tab4:
    st.write("Các bước làm sạch dữ liệu:")
    for line in log:
        st.markdown(f"- {line}")
    if st.button("Tạo báo cáo PDF và slide"):
        with st.spinner("Đang sinh báo cáo và slide…"):
            tmp = Path(tempfile.mkdtemp())
            pdf = build_report(csv_path, tmp / "bao_cao_tiem_chung.pdf", tmp / "figures")
            md = tao_md(tmp / "thong_ke.json", tmp / "noi_dung_slide.md")
            pptx = tmp / "slide_tiem_chung.pptx"
            build_pptx(md, pptx, ROOT / "templates" / "10-CTU_PowerPoint_Template.pptx")
        a, b = st.columns(2)
        a.download_button("⬇️ Tải báo cáo PDF", pdf.read_bytes(), "bao_cao_tiem_chung.pdf", "application/pdf")
        b.download_button("⬇️ Tải slide PowerPoint", pptx.read_bytes(), "slide_tiem_chung.pptx",
                          "application/vnd.openxmlformats-officedocument.presentationml.presentation")
