"""Tự động tạo slide thuyết trình (.pptx, template CTU) từ kết quả mini-project.

Tái sử dụng bộ chuyển Markdown -> PowerPoint của TH4 – Yêu cầu 5.2 (2b_md_sang_pptx.py):
    bước 1  tao_md()  : results/thong_ke.json (do bao_cao.py tạo)  ->  results/noi_dung_slide.md (sửa tay được)
    bước 2  build()   : file .md  ->  results/slide_tiem_chung.pptx

Chạy (sau khi đã chạy bao_cao.py):
    python src/tao_slide.py                       # tạo cả .md và .pptx
    python src/tao_slide.py --chi-pptx            # chỉ chuyển lại .md đã sửa tay thành .pptx
Quy ước .md: # tiêu đề · ## slide mới · - ý · ![](hinh.png) chèn hình · ## CÁM ƠN slide kết
"""
import argparse
import json
import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).parents[1]
CTU, WHITE, DARK = RGBColor(0x1F, 0x5C, 0xAA), RGBColor(255, 255, 255), RGBColor(0x28, 0x32, 0x41)
IMG = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')


def parse(text):
    title, sub, slides = None, [], []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith('## '):
            slides.append({'head': s[3:].strip(), 'items': [], 'imgs': []})
        elif s.startswith('# '):
            title = s[2:].strip()
        elif (m := IMG.search(s)):
            if slides: slides[-1]['imgs'].append(m.group(1))
        else:
            t = re.sub(r'^[-*+]\s+', '', s)
            (slides[-1]['items'] if slides else sub).append(t)
    return title, sub, slides


def runs(tf, size, color=None, bold=None):
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size)
            if color is not None: r.font.color.rgb = color
            if bold is not None: r.font.bold = bold


def fill(tf, items, size):
    tf.clear(); tf.word_wrap = True
    for i, t in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if ':' in t and t.index(':') < 40:                     # "Nhãn: nội dung" -> nhãn in đậm
            a, b = t.split(':', 1)
            r = p.add_run(); r.text = a + ':'; r.font.bold = True; r.font.color.rgb = CTU
            r = p.add_run(); r.text = b
        else:
            r = p.add_run(); r.text = t
        p.space_after = Pt(12); p.alignment = PP_ALIGN.LEFT   # căn trái, tránh giãn chữ
    runs(tf, size)


def build(md_path, out, template):
    md_path = Path(md_path)
    title, sub, slides = parse(md_path.read_text(encoding='utf-8'))
    prs = Presentation(template)
    lst = prs.slides._sldIdLst                                  # bỏ các slide mẫu, giữ master + layout
    for s in list(lst):
        prs.part.drop_rel(s.rId); lst.remove(s)
    L = {l.name: l for l in prs.slide_layouts}

    # 1. Slide tiêu đề (nền xanh có logo)
    s = prs.slides.add_slide(L['Title Slide'])
    ph = {p.placeholder_format.idx: p for p in s.placeholders}
    ph[0].text = (title or md_path.stem).upper(); runs(ph[0].text_frame, 36, WHITE, True)
    ph[1].text = sub[0] if sub else ''; runs(ph[1].text_frame, 22, WHITE)
    ph[12].text = ' · '.join(sub[1:]); runs(ph[12].text_frame, 16, WHITE)

    for sd in slides:
        if sd['head'].upper().startswith('CÁM ƠN'):            # 2. Slide kết theo mẫu template
            s = prs.slides.add_slide(L['Title Blue Background'])
            ph = {p.placeholder_format.idx: p for p in s.placeholders}
            ph[0].text = 'CÁM ƠN'; ph[1].text = sd['items'][0] if sd['items'] else 'Thank you'
            continue
        s = prs.slides.add_slide(L['Title and Content with logo'])   # 3. Slide nội dung
        ph = {p.placeholder_format.idx: p for p in s.placeholders}
        ph[0].text = sd['head']; runs(ph[0].text_frame, 32, CTU, True)
        body = ph[1]
        imgs = [md_path.parent / p for p in sd['imgs'] if (md_path.parent / p).exists()]
        if imgs:                                               # hình trái, ý phải
            top, left, maxw, maxh = Inches(1.75), Inches(0.6), Inches(8.0), Inches(4.85)
            pic = s.shapes.add_picture(str(imgs[0]), left, top, width=maxw)
            if pic.height > maxh:
                pic.width = int(pic.width * maxh / pic.height); pic.height = maxh
            pic.top = top + (maxh - pic.height) // 2
            body.left, body.top, body.width, body.height = Inches(8.85), Inches(1.9), Inches(4.0), Inches(4.6)
            fill(body.text_frame, sd['items'], 18)
        else:
            fill(body.text_frame, sd['items'], 22 if len(sd['items']) <= 4 else 20)
    prs.save(out)
    return len(prs.slides)


def tao_md(stats_path, md_path):
    k = json.loads(Path(stats_path).read_text(encoding="utf-8"))
    H, hq, pl, vn = k["hinh"], k["hoi_quy"], k["phan_loai"], k["viet_nam"]
    top3 = ", ".join(f"{c} {v}%" for c, v in k["top3"])
    vac = ", ".join(f"{n} ({c} quốc gia)" for n, c in k["vaccine_top3"])
    tq = "\n".join(f"- {n}: r = {v}" for n, v in k["tuong_quan"].items())
    md = f"""# Tiến độ tiêm chủng COVID-19 và các yếu tố liên quan
Mini-project AI + Python: phân tích dữ liệu và sinh báo cáo tự động
{k['tac_gia']}

## Dữ liệu và cách làm
- Nguồn: {k['nguon']}
- {k['so_dong']:_} dòng sau làm sạch, {k['tu_ngay']} – {k['den_ngay']}; {k['so_quoc_gia']} quốc gia có từ 100.000 người đã tiêm
- Làm sạch: pandas, numpy · Biểu đồ: matplotlib, seaborn · Mô hình: scikit-learn
- Tự động sinh báo cáo PDF (fpdf2), slide (python-pptx) và dashboard (Streamlit)

## Xu hướng tiêm toàn cầu
![]({H['xu_huong_toan_cau']})
- Đỉnh {k['dinh_trieu_lieu']} triệu liều/ngày vào {k['dinh_ngay']}
- Sau đỉnh, tốc độ tiêm giảm dần

## Các quốc gia dẫn đầu
![]({H['top_quoc_gia']})
- Cao nhất: {top3}
- Trung vị {k['so_quoc_gia']} quốc gia: {k['trung_vi']}%
- {k['ty_le_dat']}% quốc gia đạt mốc {k['nguong_dat']}%

## Việt Nam trong ASEAN
![]({H['asean']})
""" + (f"- Việt Nam: {vn['tiem_du']}%, thứ {vn['hang_asean']}/{len(k['asean'])} ASEAN\n"
       f"- Bắt đầu trễ {vn['tre']} ngày so với quốc gia đầu tiên\n" if vn else "") + f"""- Vaccine phổ biến: {vac}

## Tương quan giữa các biến
![]({H['tuong_quan']})
{tq}
- Kết luận: tốc độ tiêm liên hệ mạnh nhất

## Mô hình hồi quy tuyến tính
![]({H['du_doan']})
- R² kiểm tra: {hq['r2_test']} · MAE: {hq['mae']} điểm %
- Tốc độ tiêm tăng 10 lần: tỉ lệ tiêm đủ liều cao hơn {hq['he_so_log_toc_do']} điểm %
- Mỗi ngày bắt đầu muộn: {hq['he_so_do_tre']} điểm %

## Mô hình phân loại (cây quyết định)
![]({H['ma_tran_nham_lan']})
- Dự đoán quốc gia đạt mốc {k['nguong_dat']}% tiêm đủ liều
- Accuracy: {pl['accuracy']} · F1: {pl['f1']}
- Biến quan trọng nhất: {next(iter(pl['quan_trong']))}

## Kết luận và đề xuất
- Năng lực tiêm hằng ngày là yếu tố gắn chặt nhất với tỉ lệ tiêm đủ liều
- Bắt đầu sớm giúp tỉ lệ cao hơn; Việt Nam bắt đầu muộn nhưng vượt trung vị
- Hạn chế: ít biến, tập kiểm tra nhỏ; kết quả là tương quan, không phải nhân quả
- Đề xuất: bổ sung biến kinh tế – xã hội, dùng kiểm định chéo

## CÁM ƠN
- Thank you
"""
    md = re.sub(r"(\d)_(\d)", r"\1.\2", md)            # 84_056 -> 84.056
    Path(md_path).write_text(md, encoding="utf-8")
    return md_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "results" / "thong_ke.json"))
    ap.add_argument("--md", default=str(ROOT / "results" / "noi_dung_slide.md"))
    ap.add_argument("-o", "--output", default=str(ROOT / "results" / "slide_tiem_chung.pptx"))
    ap.add_argument("--template", default=str(ROOT / "templates" / "10-CTU_PowerPoint_Template.pptx"))
    ap.add_argument("--chi-pptx", action="store_true", help="không viết lại file .md (giữ phần đã sửa tay)")
    a = ap.parse_args()
    if not a.chi_pptx:
        tao_md(a.json, a.md)
    n = build(a.md, a.output, a.template)
    print(f"Đã tạo {Path(a.output).name} – {n} slide (nội dung: {Path(a.md).name})")
