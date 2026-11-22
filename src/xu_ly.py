"""Đọc và làm sạch dữ liệu COVID-19 World Vaccination Progress (Kaggle, CC0) – dùng pandas, numpy.

Quy tắc làm sạch giống TH4 – Yêu cầu 5.1 để số liệu giữa các bài thống nhất.
"""
from pathlib import Path

import numpy as np
import pandas as pd

PCT_COLS = ["total_vaccinations_per_hundred", "people_vaccinated_per_hundred",
            "people_fully_vaccinated_per_hundred"]
CUM_COLS = ["total_vaccinations", "people_vaccinated", "people_fully_vaccinated"] + PCT_COLS
NGUONG_NGUOI_TIEM = 100_000          # chỉ phân tích quốc gia có ít nhất 100.000 người đã tiêm
NGUONG_DAT = 70                      # nhãn phân loại: đạt >= 70% dân số tiêm đủ liều

TEN_BIEN = {
    "do_tre_bat_dau": "Độ trễ bắt đầu tiêm (ngày)",
    "so_loai_vaccine": "Số loại vaccine sử dụng",
    "toc_do_tb_trieu": "Tốc độ tiêm TB (liều/1 triệu dân/ngày)",
    "log_toc_do": "log10(Tốc độ tiêm TB)",
    "ty_le_tiem_du": "Tỉ lệ tiêm đủ liều (% dân số)",
    "ty_le_tiem_1": "Tỉ lệ tiêm ít nhất 1 mũi (% dân số)",
    "tong_lieu_100": "Tổng liều / 100 dân",
}


def load_clean(path):
    """Trả về (df_sạch, nhật_ký_làm_sạch)."""
    log = []
    df = pd.read_csv(path)
    log.append(f"Đọc {len(df):,} dòng, {df.shape[1]} cột, {df['country'].nunique()} quốc gia/vùng lãnh thổ.")

    n = len(df)
    df = df[~df["iso_code"].astype(str).str.startswith("OWID")].copy()
    log.append(f"Loại {n - len(df):,} dòng của các vùng thuộc quốc gia khác (mã OWID_*: England, Scotland…) "
               "để tránh đếm trùng.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    n = len(df)
    df = df.dropna(subset=["date"]).drop_duplicates(subset=["country", "date"]).sort_values(["country", "date"])
    log.append(f"Chuẩn hóa cột ngày; loại {n - len(df)} dòng lỗi hoặc trùng (quốc gia, ngày).")

    before = df[CUM_COLS].isna().mean().mean()
    df[CUM_COLS] = df.groupby("country")[CUM_COLS].ffill()
    log.append(f"Điền tiếp (forward-fill) chỉ số tích lũy theo quốc gia: tỉ lệ ô thiếu giảm từ "
               f"{before:.0%} xuống {df[CUM_COLS].isna().mean().mean():.0%}.")

    for c in PCT_COLS:                                   # giá trị phi lý
        df.loc[(df[c] < 0) | (df[c] > 400), c] = np.nan
    return df.reset_index(drop=True), log


def country_summary(df, log=None):
    """Mỗi quốc gia một dòng đặc trưng để thống kê, hồi quy và phân loại."""
    first_global = df.loc[df["total_vaccinations"] > 0, "date"].min()
    rows = []
    for country, g in df.groupby("country"):
        started = g.loc[g["total_vaccinations"] > 0, "date"]
        last = g.iloc[-1]
        rows.append({
            "country": country, "iso_code": last["iso_code"],
            "nguoi_da_tiem": last["people_vaccinated"],
            "do_tre_bat_dau": (started.min() - first_global).days if len(started) else np.nan,
            "so_loai_vaccine": len(str(last["vaccines"]).split(",")),
            "toc_do_tb_trieu": g["daily_vaccinations_per_million"].mean(),
            "ty_le_tiem_du": last["people_fully_vaccinated_per_hundred"],
            "ty_le_tiem_1": last["people_vaccinated_per_hundred"],
            "tong_lieu_100": last["total_vaccinations_per_hundred"],
        })
    sm = pd.DataFrame(rows).dropna()
    n = len(sm)
    sm = sm[(sm["ty_le_tiem_du"] <= 100) & (sm["nguoi_da_tiem"] >= NGUONG_NGUOI_TIEM)].copy()
    if log is not None:
        log.append(f"Giữ {len(sm)}/{n} quốc gia có tỉ lệ tiêm đủ liều hợp lệ (0–100%) và ít nhất "
                   f"{NGUONG_NGUOI_TIEM:,}".replace(",", ".") +
                   " người đã tiêm (loại vùng lãnh thổ rất nhỏ như Pitcairn, Gibraltar).")
        log.append("Lấy log10 cho tốc độ tiêm vì phân phối lệch phải; tạo nhãn phân loại "
                   f"'Đạt' khi tỉ lệ tiêm đủ liều ≥ {NGUONG_DAT}%.")
    sm["log_toc_do"] = np.log10(sm["toc_do_tb_trieu"].clip(lower=1))
    sm["dat_muc_tieu"] = (sm["ty_le_tiem_du"] >= NGUONG_DAT).astype(int)
    return sm.reset_index(drop=True)


if __name__ == "__main__":
    import sys
    d, lg = load_clean(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parents[1] / "data/country_vaccinations.csv")
    s = country_summary(d, lg)
    print("\n".join(lg)); print(s.describe().round(1))
