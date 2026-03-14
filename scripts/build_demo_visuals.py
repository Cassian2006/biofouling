import argparse
from pathlib import Path

import folium
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from branca.colormap import LinearColormap
from folium.plugins import HeatMap

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a localized visualization demo from current processed outputs."
    )
    parser.add_argument("--ais", required=True, help="Path to cleaned AIS CSV.")
    parser.add_argument("--features", required=True, help="Path to vessel features CSV.")
    parser.add_argument("--risk", required=True, help="Path to regional risk CSV.")
    parser.add_argument(
        "--output-dir",
        default="outputs/demo",
        help="Directory for generated demo visuals.",
    )
    return parser.parse_args()


def load_csv(path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(path)
    dataframe.columns = [column.strip().lower() for column in dataframe.columns]
    return dataframe


def window_label_from_features_path(path: Path) -> str:
    stem = path.stem.replace("vessel_features_", "")
    parts = stem.split("_")
    if len(parts) >= 2:
        return f"{parts[0]} 至 {parts[1]}"
    return stem


def build_map(ais: pd.DataFrame, features: pd.DataFrame, risk: pd.DataFrame, output_dir: Path) -> Path:
    center = [1.28, 103.85]
    fmap = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")

    lat_values = sorted(risk["grid_lat"].dropna().unique())
    lon_values = sorted(risk["grid_lon"].dropna().unique())
    lat_step = min(
        (lat_values[index + 1] - lat_values[index] for index in range(len(lat_values) - 1) if lat_values[index + 1] > lat_values[index]),
        default=0.05,
    )
    lon_step = min(
        (lon_values[index + 1] - lon_values[index] for index in range(len(lon_values) - 1) if lon_values[index + 1] > lon_values[index]),
        default=0.05,
    )
    lat_half = lat_step / 2
    lon_half = lon_step / 2

    color_scale = LinearColormap(
        colors=["#dbeafe", "#7dd3fc", "#34d399", "#fbbf24", "#dc2626"],
        vmin=0,
        vmax=max(float(risk["rri_score"].max()), 1e-6),
    )
    color_scale.caption = "RRI score"

    grid_layer = folium.FeatureGroup(name="RRI Grid", show=True)
    for row in risk.itertuples(index=False):
        bounds = [
            [row.grid_lat - lat_half, row.grid_lon - lon_half],
            [row.grid_lat + lat_half, row.grid_lon + lon_half],
        ]
        folium.Rectangle(
            bounds=bounds,
            color=color_scale(row.rri_score),
            weight=1,
            fill=True,
            fill_color=color_scale(row.rri_score),
            fill_opacity=0.55,
            popup=(
                f"RRI: {row.rri_score:.3f}<br>"
                f"Risk level: {row.risk_level}<br>"
                f"Traffic points: {int(row.traffic_points)}<br>"
                f"Low-speed ratio: {row.low_speed_ratio:.2f}"
            ),
        ).add_to(grid_layer)
    grid_layer.add_to(fmap)

    heat_points = risk[["grid_lat", "grid_lon", "rri_score"]].dropna().values.tolist()
    HeatMap(
        heat_points,
        name="Heat Overlay",
        radius=32,
        blur=26,
        min_opacity=0.2,
        max_zoom=11,
        show=False,
    ).add_to(fmap)
    color_scale.add_to(fmap)

    top_cells = risk.sort_values("rri_score", ascending=False).head(20)
    for row in top_cells.itertuples(index=False):
        color = "#d7301f" if row.risk_level == "high" else "#fc8d59" if row.risk_level == "medium" else "#91bfdb"
        folium.CircleMarker(
            location=[row.grid_lat, row.grid_lon],
            radius=5 + row.rri_score * 8,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=(
                f"RRI: {row.rri_score:.3f}<br>"
                f"Traffic points: {int(row.traffic_points)}<br>"
                f"Low-speed ratio: {row.low_speed_ratio:.2f}"
            ),
        ).add_to(fmap)

    top_vessels = features.sort_values("fpi_proxy", ascending=False).head(3)["mmsi"].astype(str).tolist()
    color_cycle = ["#08306b", "#2171b5", "#41ab5d"]
    ais = ais.copy()
    ais["mmsi"] = ais["mmsi"].astype(str)
    for index, vessel_id in enumerate(top_vessels):
        vessel_track = ais[ais["mmsi"] == vessel_id].sort_values("timestamp")
        if vessel_track.empty:
            continue
        coords = vessel_track[["latitude", "longitude"]].values.tolist()
        folium.PolyLine(
            coords,
            color=color_cycle[index % len(color_cycle)],
            weight=3,
            opacity=0.9,
            tooltip=f"高风险船舶 {vessel_id}",
        ).add_to(fmap)

    folium.LayerControl().add_to(fmap)
    output_path = output_dir / "regional_demo_map.html"
    fmap.save(str(output_path))
    return output_path


def build_recommendation_chart(features: pd.DataFrame, output_dir: Path) -> Path:
    plt.figure(figsize=(8, 4.5))
    order = features["recommendation"].value_counts().index.tolist()
    sns.countplot(data=features, y="recommendation", order=order, color="#4daf4a")
    plt.title("Vessel Recommendation Breakdown")
    plt.xlabel("Vessel Count")
    plt.ylabel("")
    plt.tight_layout()
    output_path = output_dir / "recommendation_breakdown.png"
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def build_top_vessel_chart(features: pd.DataFrame, output_dir: Path) -> Path:
    top = features.sort_values("fpi_proxy", ascending=False).head(10).copy()
    top["mmsi"] = top["mmsi"].astype(str)
    plt.figure(figsize=(10, 5.5))
    sns.barplot(data=top, x="fpi_proxy", y="mmsi", color="#2b8cbe")
    plt.title("Top 10 Vessels by FPI Proxy")
    plt.xlabel("FPI Proxy")
    plt.ylabel("MMSI")
    plt.xlim(0, 1)
    plt.tight_layout()
    output_path = output_dir / "top_vessels_fpi.png"
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def build_dashboard(
    features: pd.DataFrame,
    risk: pd.DataFrame,
    map_path: Path,
    rec_chart_path: Path,
    top_chart_path: Path,
    output_dir: Path,
    window_label: str,
) -> Path:
    top_vessel = features.sort_values("fpi_proxy", ascending=False).iloc[0]
    top_vessels = features.sort_values("fpi_proxy", ascending=False).head(5)
    top_cells = risk.sort_values("rri_score", ascending=False).head(5)
    high_cells = int((risk["risk_level"] == "high").sum())
    medium_cells = int((risk["risk_level"] == "medium").sum())
    recommendation_counts = features["recommendation"].value_counts().to_dict()

    vessel_rows = "".join(
        f"""
        <div class="rank-row">
          <div>
            <strong>{row.mmsi}</strong>
            <span>{row.recommendation}</span>
          </div>
          <div class="rank-metrics">
            <span>FPI {row.fpi_proxy:.3f}</span>
            <span>ECP {row.ecp_proxy:.3f}</span>
          </div>
        </div>
        """
        for row in top_vessels.itertuples(index=False)
    )
    cell_rows = "".join(
        f"""
        <div class="rank-row">
          <div>
            <strong>{row.grid_lat:.4f}, {row.grid_lon:.4f}</strong>
            <span>{row.risk_level}</span>
          </div>
          <div class="rank-metrics">
            <span>RRI {row.rri_score:.3f}</span>
            <span>点数 {int(row.traffic_points)}</span>
          </div>
        </div>
        """
        for row in top_cells.itertuples(index=False)
    )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>生物污损演示面板</title>
  <style>
    :root {{
      --bg: #f4efe8;
      --panel: rgba(255, 255, 255, 0.88);
      --ink: #1d1a16;
      --muted: #6a6259;
      --accent: #0f766e;
      --line: rgba(29, 26, 22, 0.08);
      --shadow: 0 20px 60px rgba(35, 28, 20, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.15), transparent 32%),
        radial-gradient(circle at top right, rgba(194, 65, 12, 0.12), transparent 28%),
        linear-gradient(180deg, #faf5ef 0%, var(--bg) 100%);
    }}
    .page {{ width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 56px; }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero {{ display: grid; grid-template-columns: 1.45fr 0.95fr; gap: 16px; }}
    .hero-copy {{ padding: 28px; }}
    .hero-copy h1 {{ margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: 54px; line-height: 0.98; max-width: 10ch; }}
    .eyebrow {{ margin: 0 0 10px; color: var(--accent); font-size: 12px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; }}
    .muted {{ color: var(--muted); font-size: 15px; line-height: 1.7; }}
    .hero-panel {{ padding: 22px; display: grid; gap: 12px; }}
    .hero-metric {{ padding: 14px 16px; background: #fff; border-radius: 16px; border: 1px solid var(--line); }}
    .hero-metric span, .label {{ display: block; color: var(--muted); font-size: 13px; }}
    .hero-metric strong, .value {{ display: block; margin-top: 6px; font-size: 26px; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 18px 0 0; }}
    .card, .section-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .section {{ margin-top: 24px; }}
    h2 {{ margin: 0; font-size: 34px; line-height: 1.08; }}
    h3 {{ margin: 0 0 10px; font-size: 18px; }}
    .module-grid, .feature-grid, .table-grid, .image-row {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
    .module-top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
    .pill {{ padding: 6px 10px; border-radius: 999px; background: #dff4ee; color: var(--accent); font-size: 12px; font-weight: 700; }}
    .insight-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }}
    .big {{ font-size: 28px; font-weight: 700; margin: 0 0 8px; }}
    img {{ width: 100%; border-radius: 14px; border: 1px solid #ddd; background: white; }}
    iframe {{ width: 100%; height: 680px; border: 1px solid #ddd; border-radius: 16px; background: white; }}
    .rank-row {{ display: flex; justify-content: space-between; gap: 12px; padding: 12px 0; border-top: 1px solid var(--line); }}
    .rank-row:first-child {{ border-top: 0; padding-top: 0; }}
    .rank-row strong {{ display: block; }}
    .rank-row span {{ display: block; color: var(--muted); font-size: 13px; margin-top: 4px; }}
    .rank-metrics {{ text-align: right; }}
    .summary-box p {{ margin: 0 0 10px; line-height: 1.7; }}
    .summary-box p:last-child {{ margin-bottom: 0; }}
    @media (max-width: 980px) {{
      .hero, .cards, .module-grid, .feature-grid, .table-grid, .image-row, .insight-grid {{ grid-template-columns: 1fr; }}
      .hero-copy h1 {{ font-size: 40px; }}
      iframe {{ height: 520px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="panel hero-copy">
        <p class="eyebrow">基于 AIS 与海洋环境的演示面板</p>
        <h1>先看见风险，再决定何时清洗、如何维护、哪里最值得关注。</h1>
        <p class="muted">
          这个页面用当前真实测试窗做演示，同时补上正式平台后续要展示的主要功能区。
          你现在看到的是一个说明性很强的 demo，它的目标是让用户快速理解系统会展示什么。
        </p>
      </div>
      <div class="panel hero-panel">
        <div class="hero-metric"><span>当前测试时间窗</span><strong>{window_label}</strong></div>
        <div class="hero-metric"><span>已汇总船舶</span><strong>{len(features)}</strong></div>
        <div class="hero-metric"><span>区域格网单元</span><strong>{len(risk)}</strong></div>
        <div class="hero-metric"><span>当前最高风险船舶</span><strong>{top_vessel.mmsi}</strong></div>
      </div>
    </section>

    <section class="cards">
      <div class="card"><span class="label">高风险格网</span><div class="value">{high_cells}</div><div class="muted">表示当前时间窗下最值得优先关注的热点海域。</div></div>
      <div class="card"><span class="label">中风险格网</span><div class="value">{medium_cells}</div><div class="muted">表示可能存在持续暴露积累，需要继续观察。</div></div>
      <div class="card"><span class="label">优先评估清洗</span><div class="value">{int(recommendation_counts.get("Prioritize cleaning assessment", 0))}</div><div class="muted">规则系统当前建议优先检查维护窗口的船舶数量。</div></div>
      <div class="card"><span class="label">低即时关注</span><div class="value">{int(recommendation_counts.get("Low immediate concern", 0))}</div><div class="muted">当前暴露水平相对较低的船舶数量。</div></div>
    </section>

    <section class="section">
      <p class="eyebrow">本页展示什么</p>
      <h2>四个核心区块，对应后续正式平台的主要功能</h2>
      <div class="module-grid">
        <div class="section-card">
          <div class="module-top"><h3>单船诊断</h3><span class="pill">已演示</span></div>
          <div class="muted">展示单船的污损倾向、隐性碳排惩罚、维护建议和优先级。正式版会进入单船详情页。</div>
        </div>
        <div class="section-card">
          <div class="module-top"><h3>区域风险地图</h3><span class="pill">已演示</span></div>
          <div class="muted">展示研究区内哪些海域更可能促进污损积累。后续会加入图层切换和时间窗筛选。</div>
        </div>
        <div class="section-card">
          <div class="module-top"><h3>情景模拟</h3><span class="pill">规划中</span></div>
          <div class="muted">用于比较“不清洗 / 延后清洗 / 近期清洗”等方案带来的风险变化和维护差异。</div>
        </div>
        <div class="section-card">
          <div class="module-top"><h3>维护建议</h3><span class="pill">已演示</span></div>
          <div class="muted">当前已能输出首版规则建议，后续会继续补经验参数和更细的推荐逻辑。</div>
        </div>
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">如何理解当前结果</p>
      <h2>这是一次真实测试窗的快照，不是完整年度结论</h2>
      <div class="insight-grid">
        <div class="section-card">
          <h3>单船风险信号</h3>
          <p class="big">MMSI {top_vessel.mmsi}</p>
          <div class="muted">FPI {top_vessel.fpi_proxy:.3f}，ECP {top_vessel.ecp_proxy:.3f}</div>
          <div class="muted">{top_vessel.recommendation}</div>
        </div>
        <div class="section-card">
          <h3>区域热点位置</h3>
          <p class="big">{top_cells.iloc[0].grid_lat:.4f}, {top_cells.iloc[0].grid_lon:.4f}</p>
          <div class="muted">RRI {top_cells.iloc[0].rri_score:.3f}，等级 {top_cells.iloc[0].risk_level}</div>
        </div>
        <div class="section-card">
          <h3>当前页面定位</h3>
          <div class="muted">这个 demo 的重点是告诉用户系统会展示什么，而不是一次性实现所有交互能力。</div>
        </div>
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">区域风险视图</p>
      <h2>研究区地图上显示哪些海域更可能促进污损积累</h2>
      <div class="muted">颜色越热，表示该位置在当前时间窗下越可能具备高温、生物活性、交通密度或低速暴露等风险条件。</div>
      <div class="section-card" style="margin-top:14px; padding:10px;">
        <iframe src="{map_path.name}" title="区域风险地图"></iframe>
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">单船与区域榜单</p>
      <h2>先看最值得关注的船和区域</h2>
      <div class="table-grid">
        <div class="section-card">
          <h3>高风险船舶 Top 5</h3>
          {vessel_rows}
        </div>
        <div class="section-card">
          <h3>高风险格网 Top 5</h3>
          {cell_rows}
        </div>
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">证据图表</p>
      <h2>当前规则系统输出了什么分层结果</h2>
      <div class="muted">左图展示当前船舶建议分布，右图展示 FPI 最高的船舶。这两张图主要用于帮助用户快速理解当前数据状态。</div>
      <div class="image-row">
        <img src="{rec_chart_path.name}" alt="建议分布图">
        <img src="{top_chart_path.name}" alt="高风险船舶图">
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">后续将展示的功能</p>
      <h2>这些模块当前先说明，后续再逐步做实</h2>
      <div class="feature-grid">
        <div class="section-card">
          <h3>情景模拟器</h3>
          <div class="muted">用户可切换“当前清洗 / 延后清洗 / 不清洗”等方案，对比风险变化和建议差异。</div>
        </div>
        <div class="section-card">
          <h3>单船报告页</h3>
          <div class="muted">后续会把当前 Markdown 报告改成可视化报告页，包含轨迹、暴露因子分解和建议说明。</div>
        </div>
        <div class="section-card">
          <h3>区域图层切换</h3>
          <div class="muted">后续将支持环境暴露层、行为暴露层、综合风险层之间切换，并允许按时间窗或船型筛选。</div>
        </div>
        <div class="section-card">
          <h3>维护窗口建议</h3>
          <div class="muted">后续会把建议扩展到“何时看、何时洗、为什么洗”三个层次，提升决策可读性。</div>
        </div>
      </div>
    </section>

    <section class="section">
      <p class="eyebrow">当前测试窗摘要</p>
      <h2>把现阶段的演示条件说清楚</h2>
      <div class="section-card summary-box">
        <p>时间窗：{window_label}</p>
        <p>空间范围：新加坡海峡及周边固定 bbox</p>
        <p>当前环境变量：海温（thetao）与叶绿素（chl）</p>
        <p>当前页面的目标：说明系统未来要展示什么，而不是一次性做完所有交互功能。</p>
      </div>
    </section>
  </div>
</body>
</html>
"""
    output_path = output_dir / "demo_dashboard.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme(style="whitegrid")
    ais = load_csv(Path(args.ais))
    features_path = Path(args.features)
    features = load_csv(features_path)
    risk = load_csv(Path(args.risk))
    window_label = window_label_from_features_path(features_path)

    map_path = build_map(ais, features, risk, output_dir)
    rec_chart_path = build_recommendation_chart(features, output_dir)
    top_chart_path = build_top_vessel_chart(features, output_dir)
    dashboard_path = build_dashboard(
        features, risk, map_path, rec_chart_path, top_chart_path, output_dir, window_label
    )

    print(f"Demo dashboard written to: {dashboard_path.resolve()}")
    print(f"Map written to: {map_path.resolve()}")
    print(f"Charts written to: {rec_chart_path.resolve()} and {top_chart_path.resolve()}")


if __name__ == "__main__":
    main()
