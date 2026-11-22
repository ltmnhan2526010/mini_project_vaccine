"""Sinh báo cáo khoa học PDF tự động từ dữ liệu tiêm chủng (fpdf2).

Cách dùng (từ thư mục gốc dự án):
    python src/bao_cao.py data/country_vaccinations.csv -o results/bao_cao_tiem_chung.pdf
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib
from fpdf import FPDF
from fpdf.fonts import FontFace
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from phan_tich import (FEATURES, TARGET, asean_table, classification, regression, save_all,  # noqa: E402
                       vaccine_counts)
from xu_ly import NGUONG_DAT, TEN_BIEN, country_summary, load_clean            # noqa: E402

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
NAVY = (31, 92, 170)                     # xanh CTU #1F5CAA
TITLE = "Phân tích tiến độ tiêm chủng COVID-19 toàn cầu và các yếu tố liên quan đến tỉ lệ tiêm đủ liều"
AUTHORS = "Lê Thị Mỹ Nhân (MSHV: M2526010) – Học phần Công nghệ số nâng cao (CT999), Đại học Cần Thơ"


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", FONT_DIR / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", FONT_DIR / "DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
        self.set_auto_page_break(True, 15)

    def footer(self):
        self.set_y(-12); self.set_font("DejaVu", "", 8); self.set_text_color(120)
        self.cell(0, 6, f"Mini-project AI + Python – Dữ liệu tiêm chủng COVID-19  •  Trang {self.page_no()}/{{nb}}",
                  align="C")

    def need(self, height):
        """Sang trang mới nếu không đủ chỗ (tránh tiêu đề/hình bị tách khỏi chú thích)."""
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def h1(self, t):
        self.need(30); self.ln(2); self.set_font("DejaVu", "B", 13); self.set_text_color(*NAVY)
        self.cell(0, 8, t, new_x="LMARGIN", new_y="NEXT"); self.set_text_color(0)

    def h2(self, t):
        self.need(25); self.set_font("DejaVu", "B", 10.5); self.set_text_color(*NAVY)
        self.cell(0, 7, t, new_x="LMARGIN", new_y="NEXT"); self.set_text_color(0)

    def p(self, t, style=""):
        self.set_font("DejaVu", style, 10); self.multi_cell(0, 5.5, t, new_x="LMARGIN", new_y="NEXT"); self.ln(1)

    def bullets(self, items):
        for it in items:
            self.p("•  " + it)

    def table(self, header, rows, widths=None):
        self.need(6 * (len(rows) + 1) + 4)
        self.set_font("DejaVu", "", 9)
        with super().table(col_widths=widths, headings_style=FontFace(emphasis="BOLD", color=255, fill_color=NAVY),
                           line_height=5.5, width=self.epw, text_align="LEFT") as t:
            t.row(header)
            for r in rows:
                t.row([str(x) for x in r])
        self.ln(2)

    def fig(self, path, caption, w=None):
        w = w or self.epw
        iw, ih = Image.open(path).size
        self.need(w * ih / iw + 9)
        self.image(str(path), w=w, x=(self.w - w) / 2)
        self.set_font("DejaVu", "I", 8.5); self.set_text_color(90)
        self.multi_cell(0, 5, caption, align="C", new_x="LMARGIN", new_y="NEXT"); self.set_text_color(0); self.ln(2)


def build_report(csv, out_pdf, fig_dir, authors=AUTHORS):
    df, log = load_clean(csv)
    sm = country_summary(df, log)
    res = regression(sm)
    cls = classification(sm)
    figs = save_all(df, sm, res, fig_dir, cls)
    vn = sm[sm["country"] == "Vietnam"]
    n = len(sm)

    pdf = PDF(); pdf.add_page()
    pdf.set_font("DejaVu", "B", 16); pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 8, TITLE, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9); pdf.set_text_color(90)
    pdf.multi_cell(0, 5, f"{authors}\nBáo cáo sinh tự động ngày {date.today():%d/%m/%Y}", align="C",
                   new_x="LMARGIN", new_y="NEXT"); pdf.set_text_color(0)

    # 1 ------------------------------------------------------------------
    pdf.h1("1. Giới thiệu đề tài")
    pdf.p("Tiêm chủng là biện pháp then chốt trong ứng phó đại dịch COVID-19, nhưng tiến độ giữa các quốc gia "
          "rất khác nhau. Báo cáo này phân tích dữ liệu tiêm chủng toàn cầu nhằm: (i) mô tả xu hướng tiêm chủng; "
          "(ii) so sánh tỉ lệ tiêm đủ liều giữa các quốc gia; (iii) xây dựng mô hình hồi quy tuyến tính để xem "
          "thời điểm bắt đầu, số loại vaccine và tốc độ tiêm liên quan thế nào đến tỉ lệ tiêm đủ liều; "
          f"(iv) xây dựng mô hình phân loại (cây quyết định) dự đoán quốc gia có đạt mốc {NGUONG_DAT}% dân số "
          "tiêm đủ liều hay không. Toàn bộ quy trình – đọc dữ liệu, làm sạch, phân tích, vẽ biểu đồ và viết báo "
          "cáo này – được thực hiện tự động bằng Python (pandas, numpy, matplotlib, seaborn, scikit-learn, fpdf2).")

    # 2 ------------------------------------------------------------------
    pdf.h1("2. Mô tả dữ liệu")
    pdf.p(f"Nguồn: bộ dữ liệu \"COVID-19 World Vaccination Progress\" trên Kaggle (tác giả Gabriel Preda), tổng hợp "
          f"từ Our World in Data. Giấy phép: CC0 – Public Domain. Dữ liệu ở mức quốc gia, không chứa thông tin cá "
          f"nhân. Quy mô: {len(df):_} dòng sau khi loại vùng trùng lặp, 15 cột; giai đoạn "
          f"{df['date'].min():%d/%m/%Y} – {df['date'].max():%d/%m/%Y}.".replace("_", "."))
    pdf.p("Các bước làm sạch (pandas, numpy):", "B")
    pdf.bullets(log)
    pdf.p(f"Sau khi tổng hợp, mỗi quốc gia còn một dòng gồm các biến ở Bảng 1 ({n} quốc gia). "
          "Độ trễ bắt đầu tính từ ngày quốc gia đầu tiên tiêm liều đầu (02/12/2020); số liệu của mỗi quốc gia là "
          "giá trị cuối cùng có trong bộ dữ liệu.")
    d = sm[FEATURES + ["toc_do_tb_trieu", TARGET]].describe().T
    pdf.table(["Biến", "TB", "ĐLC", "Min", "Max"],
              [[TEN_BIEN[i], f"{r['mean']:.1f}", f"{r['std']:.1f}", f"{r['min']:.1f}", f"{r['max']:.1f}"]
               for i, r in d.iterrows()], widths=(78, 14, 14, 14, 14))
    pdf.set_font("DejaVu", "I", 8.5); pdf.cell(0, 5, f"Bảng 1. Thống kê mô tả các biến ({n} quốc gia).", align="C",
                                              new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)

    # 3 ------------------------------------------------------------------
    pdf.h1("3. Kết quả phân tích")
    pdf.h2("3.1. Thống kê mô tả")
    peak = df.groupby("date")["daily_vaccinations"].sum()
    pdf.p(f"Toàn cầu đạt đỉnh {peak.max() / 1e6:.1f} triệu liều/ngày vào {peak.idxmax():%d/%m/%Y} (Hình 1). "
          f"Trung vị tỉ lệ tiêm đủ liều của {n} quốc gia là {sm[TARGET].median():.1f}%; "
          f"{cls['ty_le_dat']:.0%} quốc gia đạt mốc {NGUONG_DAT}% (Hình 2).")
    pdf.fig(figs["xu_huong_toan_cau"], "Hình 1. Số liều vaccine tiêm mỗi ngày trên toàn cầu.")
    pdf.fig(figs["top_quoc_gia"], "Hình 2. Các quốc gia có tỉ lệ tiêm đủ liều cao nhất (Việt Nam tô màu cam).",
            w=pdf.epw * 0.9)
    asean, vac = asean_table(df), vaccine_counts(df)
    rank = list(asean.index).index("Vietnam") + 1 if "Vietnam" in asean.index else None
    pdf.p(f"Trong ASEAN, dẫn đầu là {asean.index[0]} ({asean.iloc[0, 1]:.1f}%)" +
          (f"; Việt Nam xếp thứ {rank}/{len(asean)}" if rank else "") + " (Bảng 2, Hình 3). "
          f"{vac.index[0]} là vaccine được nhiều quốc gia dùng nhất ({vac.iloc[0]} quốc gia, Hình 4).")
    pdf.table(["Quốc gia", "% tiêm ít nhất 1 mũi", "% tiêm đủ liều", "Tổng liều / 100 dân"],
              [[c, f"{r.iloc[0]:.1f}", f"{r.iloc[1]:.1f}", f"{r.iloc[2]:.1f}"] for c, r in asean.iterrows()],
              widths=(54, 40, 40, 40))
    pdf.set_font("DejaVu", "I", 8.5); pdf.cell(0, 5, "Bảng 2. Các nước ASEAN, sắp theo tỉ lệ tiêm đủ liều.",
                                              align="C", new_x="LMARGIN", new_y="NEXT"); pdf.ln(2)
    pdf.fig(figs["asean"], "Hình 3. Tiến độ tiêm đủ liều các nước ASEAN theo thời gian.")
    pdf.fig(figs["loai_vaccine"], "Hình 4. Các loại vaccine được nhiều quốc gia sử dụng nhất.", w=pdf.epw * 0.85)

    pdf.h2("3.2. Tương quan giữa các biến")
    corr = sm[FEATURES + [TARGET]].corr()[TARGET].drop(TARGET)
    pdf.p("Hệ số tương quan Pearson với tỉ lệ tiêm đủ liều: " +
          "; ".join(f"{TEN_BIEN[k]}: r = {v:.2f}" for k, v in corr.items()) +
          ". Tốc độ tiêm là biến có liên hệ mạnh nhất; quốc gia bắt đầu càng muộn thường có tỉ lệ càng thấp (Hình 5, 6).")
    pdf.fig(figs["tuong_quan"], "Hình 5. Ma trận tương quan Pearson (seaborn).", w=pdf.epw * 0.62)
    pdf.fig(figs["tre_vs_ty_le"], "Hình 6. Độ trễ bắt đầu tiêm và tỉ lệ tiêm đủ liều.", w=pdf.epw * 0.8)

    pdf.h2("3.3. Mô hình hồi quy tuyến tính")
    pdf.p(f"Hồi quy tuyến tính đa biến (scikit-learn), chia 75% huấn luyện ({res['n_train']} quốc gia) / "
          f"25% kiểm tra ({res['n_test']} quốc gia), random_state = 42:")
    pdf.table(["Thành phần", "Giá trị"],
              [["Hệ số chặn", f"{res['intercept']:.3f}"]] +
              [[f"Hệ số – {TEN_BIEN[k]}", f"{v:.3f}"] for k, v in res["coef"].items()] +
              [["R² (huấn luyện / kiểm tra)", f"{res['r2_train']:.2f} / {res['r2_test']:.2f}"],
               ["MAE tập kiểm tra (điểm %)", f"{res['mae_test']:.1f}"]], widths=(120, 54))
    pdf.fig(figs["du_doan"], "Hình 7. Giá trị thực tế và dự đoán trên tập kiểm tra.", w=pdf.epw * 0.4)

    pdf.h2("3.4. Mô hình phân loại (cây quyết định)")
    cm = cls["cm"]
    pdf.p(f"Nhãn 'Đạt' = tỉ lệ tiêm đủ liều ≥ {NGUONG_DAT}%. Cây quyết định độ sâu tối đa 3, chia 75/25 có phân "
          f"tầng theo nhãn. Trên {cls['n_test']} quốc gia kiểm tra: Accuracy = {cls['acc_test']:.2f}, "
          f"F1 (lớp 'Đạt') = {cls['f1_test']:.2f}; dự đoán đúng {cm[1, 1]}/{cm[1].sum()} quốc gia 'Đạt' và "
          f"{cm[0, 0]}/{cm[0].sum()} quốc gia 'Chưa đạt' (Hình 8). Mức độ quan trọng của biến: " +
          "; ".join(f"{TEN_BIEN[k]} {v:.2f}" for k, v in cls["importance"].items()) + ".")
    pdf.fig(figs["ma_tran_nham_lan"], "Hình 8. Ma trận nhầm lẫn của cây quyết định trên tập kiểm tra.",
            w=pdf.epw * 0.34)

    # 4 ------------------------------------------------------------------
    pdf.h1("4. Kết luận & đề xuất")
    c = res["coef"]
    items = [
        f"Tốc độ tiêm toàn cầu tăng nhanh trong năm 2021 rồi giảm dần; tỉ lệ tiêm đủ liều giữa các quốc gia "
        f"chênh lệch lớn (từ {sm[TARGET].min():.1f}% đến {sm[TARGET].max():.1f}%).",
        f"Hồi quy: tốc độ tiêm trung bình tăng 10 lần gắn với tỉ lệ tiêm đủ liều cao hơn {c['log_toc_do']:.1f} "
        f"điểm %; mỗi ngày bắt đầu muộn hơn gắn với {c['do_tre_bat_dau']:+.3f} điểm % (giữ các biến khác không "
        f"đổi). Mô hình giải thích khoảng {res['r2_test']:.0%} biến thiên trên tập kiểm tra.",
        f"Phân loại: cây quyết định dự đoán khá chính xác quốc gia đạt mốc {NGUONG_DAT}% (Accuracy "
        f"{cls['acc_test']:.2f}) và gần như chỉ dựa vào tốc độ tiêm – năng lực tiêm hằng ngày là yếu tố quyết định.",
    ]
    if len(vn):
        v = vn.iloc[0]
        items.append(f"Việt Nam: bắt đầu trễ {v['do_tre_bat_dau']:.0f} ngày so với quốc gia đầu tiên nhưng đạt "
                     f"{v[TARGET]:.1f}% tiêm đủ liều, cao hơn trung vị {n} quốc gia ({sm[TARGET].median():.1f}%).")
    items += [
        "Hạn chế: chỉ có 3 biến giải thích, tập kiểm tra nhỏ nên kết quả thay đổi theo cách chia dữ liệu; tốc độ "
        "tiêm và tỉ lệ tiêm đủ liều cùng phản ánh năng lực tiêm chủng. Kết quả là tương quan, không khẳng định "
        "nhân quả.",
        "Đề xuất: bổ sung biến kinh tế – xã hội (GDP bình quân, dân số, chi tiêu y tế), dùng kiểm định chéo "
        "(cross-validation); về chính sách, chuẩn bị nguồn vaccine sớm và nâng năng lực tiêm hằng ngày là đòn bẩy "
        "quan trọng cho các chiến dịch tiêm chủng tương lai.",
    ]
    pdf.bullets(items)
    pdf.output(str(out_pdf))

    # Lưu số liệu + đường dẫn hình để bước tạo slide (tao_slide.py) dùng lại – giống YC5.1 -> YC5.2
    stats = {
        "nguon": "Kaggle – COVID-19 World Vaccination Progress (Gabriel Preda), CC0; dữ liệu gốc Our World in Data",
        "tac_gia": authors, "so_dong": int(len(df)), "so_quoc_gia": n,
        "tu_ngay": f"{df['date'].min():%d/%m/%Y}", "den_ngay": f"{df['date'].max():%d/%m/%Y}",
        "dinh_trieu_lieu": round(peak.max() / 1e6, 1), "dinh_ngay": f"{peak.idxmax():%d/%m/%Y}",
        "trung_vi": round(float(sm[TARGET].median()), 1), "ty_le_dat": round(cls["ty_le_dat"] * 100),
        "nguong_dat": NGUONG_DAT,
        "top3": [[r.country, round(r.ty_le_tiem_du, 1)] for r in sm.nlargest(3, TARGET).itertuples()],
        "asean": [[c, round(float(v), 1)] for c, v in asean.iloc[:, 1].items()],
        "vaccine_top3": [[k, int(v)] for k, v in vac.head(3).items()],
        "tuong_quan": {TEN_BIEN[k]: round(float(v), 2) for k, v in corr.items()},
        "hoi_quy": {"r2_train": round(res["r2_train"], 2), "r2_test": round(res["r2_test"], 2),
                    "mae": round(res["mae_test"], 1), "he_so_log_toc_do": round(float(c["log_toc_do"]), 1),
                    "he_so_do_tre": round(float(c["do_tre_bat_dau"]), 3)},
        "phan_loai": {"accuracy": round(cls["acc_test"], 2), "f1": round(cls["f1_test"], 2),
                      "quan_trong": {TEN_BIEN[k]: round(float(v), 2) for k, v in cls["importance"].items()}},
        "viet_nam": {"tiem_du": round(float(vn.iloc[0][TARGET]), 1), "tre": int(vn.iloc[0]["do_tre_bat_dau"]),
                     "hang_asean": rank} if len(vn) else None,
        "ket_luan": items,
        "hinh": {k: Path(v).resolve().relative_to(Path(out_pdf).resolve().parent).as_posix() for k, v in figs.items()},
    }
    Path(out_pdf).with_name("thong_ke.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
    return out_pdf


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("-o", "--output", default="results/bao_cao_tiem_chung.pdf")
    a = ap.parse_args()
    out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    build_report(a.csv, out, out.parent / "figures")
    print("Đã tạo", out)
