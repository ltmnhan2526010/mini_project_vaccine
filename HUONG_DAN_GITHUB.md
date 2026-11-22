# Đưa mini-project lên GitHub

1. Tạo repo trống trên github.com (ví dụ `mini-project-tiem-chung`), **không** tick thêm README/LICENSE (repo đã có sẵn).
2. Trong thư mục dự án chạy lần lượt:

```bash
git init
git add .
git commit -m "Mini-project: AI + Python sinh báo cáo từ dữ liệu tiêm chủng COVID-19"
git branch -M main
git remote add origin https://github.com/<tai-khoan>/mini-project-tiem-chung.git
git push -u origin main
```

3. Trên GitHub kiểm tra: README hiển thị, nhãn giấy phép **MIT** xuất hiện ở cột phải, `results/bao_cao_tiem_chung.pdf` và `results/slide_tiem_chung.pptx` mở được.
4. (Tùy chọn) Triển khai dashboard miễn phí trên Streamlit Community Cloud: chọn repo, file chính `app.py`.

Nếu sửa thông tin tác giả (`README.md`, biến `AUTHORS` trong `src/bao_cao.py`), chạy lại `python src/bao_cao.py data/country_vaccinations.csv` và `python src/tao_slide.py`.
