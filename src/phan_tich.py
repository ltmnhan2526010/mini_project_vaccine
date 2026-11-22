"""Phân tích thống kê, hồi quy tuyến tính, phân loại (cây quyết định) và vẽ biểu đồ (matplotlib, seaborn)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

from xu_ly import NGUONG_DAT, TEN_BIEN

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
NAVY, SKY, ORANGE = "#1F5CAA", "#00B0F0", "#F39C12"      # màu CTU, đồng bộ bài 5.1
FEATURES = ["do_tre_bat_dau", "so_loai_vaccine", "log_toc_do"]
TARGET = "ty_le_tiem_du"


def regression(summary, features=FEATURES, target=TARGET, seed=42):
    """Hồi quy tuyến tính đa biến; trả về dict kết quả."""
    X, y = summary[features], summary[target]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=seed)
    m = LinearRegression().fit(Xtr, ytr)
    pred = m.predict(Xte)
    return {
        "model": m, "n_train": len(Xtr), "n_test": len(Xte),
        "r2_test": r2_score(yte, pred), "mae_test": mean_absolute_error(yte, pred),
        "r2_train": m.score(Xtr, ytr),
        "coef": pd.Series(m.coef_, index=features), "intercept": m.intercept_,
        "y_test": yte, "pred": pred,
    }


def classification(summary, features=FEATURES, max_depth=3, seed=42):
    """Cây quyết định phân loại quốc gia 'Đạt' (>= NGUONG_DAT% tiêm đủ liều) hay 'Chưa đạt'."""
    X, y = summary[features], summary["dat_muc_tieu"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    m = DecisionTreeClassifier(max_depth=max_depth, min_samples_leaf=5, random_state=seed).fit(Xtr, ytr)
    pred = m.predict(Xte)
    return {
        "model": m, "n_train": len(Xtr), "n_test": len(Xte), "ty_le_dat": float(y.mean()),
        "acc_test": accuracy_score(yte, pred), "f1_test": f1_score(yte, pred),
        "acc_train": m.score(Xtr, ytr), "cm": confusion_matrix(yte, pred),
        "importance": pd.Series(m.feature_importances_, index=features).sort_values(ascending=False),
        "rules": export_text(m, feature_names=[TEN_BIEN[f] for f in features], decimals=1),
    }


def chart_heatmap(summary):
    cols = FEATURES + [TARGET]
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    sns.heatmap(summary[cols].corr().rename(index=TEN_BIEN, columns=TEN_BIEN), annot=True, fmt=".2f",
                cmap="Blues", vmin=-1, vmax=1, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_title("Ma trận tương quan Pearson giữa các biến")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    return fig


# ---- Thống kê mô tả dùng lại từ TH4 – Yêu cầu 5.1 (bảng ASEAN, loại vaccine) ----
ASEAN = ["Vietnam", "Thailand", "Indonesia", "Philippines", "Malaysia", "Singapore",
         "Cambodia", "Laos", "Myanmar", "Brunei"]
PCT = ["people_vaccinated_per_hundred", "people_fully_vaccinated_per_hundred", "total_vaccinations_per_hundred"]


def asean_table(df):
    last = df.groupby("country").tail(1).set_index("country")
    return last.loc[[c for c in ASEAN if c in last.index], PCT].sort_values(PCT[1], ascending=False)


def vaccine_counts(df):
    last = df.groupby("country").tail(1)
    return last["vaccines"].dropna().str.split(r",\s*").explode().str.strip().value_counts()


def chart_asean(df):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for c in asean_table(df).index:
        g = df[df["country"] == c]
        ax.plot(g["date"], g[PCT[1]], lw=3 if c == "Vietnam" else 1.2,
                color=ORANGE if c == "Vietnam" else None, label=c)
    ax.set_ylabel("% dân số tiêm đủ liều"); ax.set_title("Tiến độ tiêm đủ liều các nước ASEAN (cam: Việt Nam)")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False)
    return fig


def chart_vaccine(df, n=8):
    v = vaccine_counts(df).head(n).sort_values()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.barh(v.index, v.values, color=SKY)
    for y, x in enumerate(v.values):
        ax.text(x + 1, y, str(x), va="center", fontsize=8)
    ax.set_xlabel("Số quốc gia sử dụng"); ax.set_title("Các loại vaccine được nhiều quốc gia sử dụng nhất")
    return fig


def chart_confusion(cls):
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    sns.heatmap(cls["cm"], annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                xticklabels=["Chưa đạt", "Đạt"], yticklabels=["Chưa đạt", "Đạt"])
    ax.set_xlabel("Dự đoán"); ax.set_ylabel("Thực tế")
    ax.set_title(f"Ma trận nhầm lẫn (Accuracy = {cls['acc_test']:.2f})")
    return fig


def chart_global_trend(df, ax=None):
    s = df.groupby("date")["daily_vaccinations"].sum() / 1e6
    fig = None
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(s.index, s.values, color=NAVY)
    ax.fill_between(s.index, s.values, color=SKY, alpha=0.25)
    ax.set_ylabel("Triệu liều / ngày")
    ax.set_title("Số liều vaccine tiêm mỗi ngày trên toàn cầu (trung bình trượt 7 ngày)")
    return fig or ax.figure


def chart_top(summary, n=15, highlight="Vietnam"):
    top = summary.nlargest(n, TARGET).sort_values(TARGET)
    if highlight in summary["country"].values and highlight not in top["country"].values:
        top = pd.concat([summary[summary["country"] == highlight], top])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    colors = [ORANGE if c == highlight else SKY for c in top["country"]]
    ax.barh(top["country"], top[TARGET], color=colors)
    ax.set_xlabel("% dân số tiêm đủ liều (cuối kỳ dữ liệu)")
    ax.set_title(f"Top {n} quốc gia theo tỉ lệ tiêm đủ liều (cam: {highlight})")
    return fig


def chart_scatter(summary, x="do_tre_bat_dau"):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.scatter(summary[x], summary[TARGET], s=18, alpha=0.6, color=SKY)
    m = LinearRegression().fit(summary[[x]], summary[TARGET])
    xs = pd.DataFrame({x: sorted(summary[x])})
    ax.plot(xs[x], m.predict(xs), color=ORANGE, lw=2, label=f"Hồi quy đơn: hệ số = {m.coef_[0]:.3f}")
    ax.set_xlabel(TEN_BIEN.get(x, x))
    ax.set_ylabel(TEN_BIEN[TARGET])
    ax.legend(frameon=False)
    ax.set_title("Quốc gia bắt đầu tiêm muộn hơn có tỉ lệ tiêm đủ liều thấp hơn?")
    return fig


def chart_pred(res):
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(res["y_test"], res["pred"], color=NAVY, s=20)
    lim = [0, max(res["y_test"].max(), res["pred"].max()) * 1.05]
    ax.plot(lim, lim, "--", color=ORANGE, label="Dự đoán hoàn hảo")
    ax.set_xlabel("Thực tế (%)"); ax.set_ylabel("Dự đoán (%)")
    ax.set_title(f"Tập kiểm tra: R² = {res['r2_test']:.2f}")
    ax.legend(frameon=False)
    return fig


def save_all(df, summary, res, out, cls=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    paths = {}
    figs = [("xu_huong_toan_cau", chart_global_trend(df)), ("top_quoc_gia", chart_top(summary)),
            ("tuong_quan", chart_heatmap(summary)), ("tre_vs_ty_le", chart_scatter(summary)),
            ("du_doan", chart_pred(res)), ("asean", chart_asean(df)), ("loai_vaccine", chart_vaccine(df))]
    if cls is not None:
        figs.append(("ma_tran_nham_lan", chart_confusion(cls)))
    for name, fig in figs:
        fig.tight_layout()
        p = out / f"{name}.png"
        fig.savefig(p, dpi=200); plt.close(fig)
        paths[name] = p
    return paths
