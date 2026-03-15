import argparse
import html
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


DESKTOP_DIR = Path.home() / "Desktop"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a plain-language science upgrade briefing on the desktop."
    )
    parser.add_argument(
        "--comparison-csv",
        default="outputs/science/scoring_comparison_20260115_20260130.csv",
        help="Path to the legacy-vs-scientific comparison CSV.",
    )
    parser.add_argument(
        "--summary-json",
        default="outputs/science/scoring_comparison_summary.json",
        help="Path to the comparison summary JSON.",
    )
    parser.add_argument(
        "--base-chart",
        default="outputs/science/scoring_v1_vs_v2.png",
        help="Path to the existing legacy-vs-scientific comparison chart.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DESKTOP_DIR / "biofouling_science_upgrade"),
        help="Directory for the generated briefing package.",
    )
    return parser.parse_args()


def configure_matplotlib() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def classify_priority(score: float) -> str:
    if score >= 0.25:
        return "优先评估"
    if score >= 0.08:
        return "持续监测"
    return "当前较低"


def recommendation_counts(scores: pd.Series) -> dict[str, int]:
    counts = {"优先评估": 0, "持续监测": 0, "当前较低": 0}
    for score in scores.fillna(0):
        counts[classify_priority(float(score))] += 1
    return counts


def plain_language_takeaways(summary: dict[str, float]) -> list[str]:
    return [
        "旧算法更像把海温、叶绿素等环境变量当成几个独立加分按钮，只要值偏高，风险就容易被整体抬高。",
        "新算法先判断这片水是否适合附着生物存活、这里的生产力压力是否偏高、水流会不会冲掉附着窗口，最后再看这艘船自己到底暴露了多久。",
        "这一版和上一版最大的区别是：环境现在既可以增强，也可以削弱风险，不再是“只能降分不能增强”。",
        "维护状态也重新回到了 FPI 中，但只作为轻修正项，不再完全交给 ECP 去兜底。",
        (
            f"在当前 15 天竞赛样本里，FPI 平均值从 {summary['legacy_fpi_mean']:.4f} "
            f"变为 {summary['scientific_fpi_mean']:.4f}，说明新算法确实把旧版环境单独抬分的部分压回去了。"
        ),
        (
            f"ECP 平均值从 {summary['legacy_ecp_mean']:.4f} 变为 {summary['scientific_ecp_mean']:.4f}，"
            "说明 ECP 现在更像污损代价放大器，而不是另一套重复算一遍的 FPI。"
        ),
    ]


def build_distribution_chart(dataframe: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    sns.histplot(
        dataframe["fpi_proxy_legacy"],
        bins=24,
        color="#94a3b8",
        alpha=0.55,
        ax=axes[0],
        label="旧 FPI",
    )
    sns.histplot(
        dataframe["fpi_proxy_scientific"],
        bins=24,
        color="#2563eb",
        alpha=0.55,
        ax=axes[0],
        label="新 FPI",
    )
    axes[0].set_title("FPI 分布变化")
    axes[0].set_xlabel("分数")
    axes[0].set_ylabel("船舶数量")
    axes[0].legend()

    sns.histplot(
        dataframe["ecp_proxy_legacy"],
        bins=24,
        color="#cbd5e1",
        alpha=0.55,
        ax=axes[1],
        label="旧 ECP",
    )
    sns.histplot(
        dataframe["ecp_proxy_scientific"],
        bins=24,
        color="#0f766e",
        alpha=0.55,
        ax=axes[1],
        label="新 ECP",
    )
    axes[1].set_title("ECP 分布变化")
    axes[1].set_xlabel("分数")
    axes[1].set_ylabel("船舶数量")
    axes[1].legend()

    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build_priority_shift_chart(
    dataframe: pd.DataFrame, output_path: Path
) -> dict[str, dict[str, int]]:
    legacy_counts = recommendation_counts(dataframe["fpi_proxy_legacy"])
    scientific_counts = recommendation_counts(dataframe["fpi_proxy_scientific"])

    plot_frame = pd.DataFrame(
        [
            {"version": "旧算法", "bucket": key, "count": value}
            for key, value in legacy_counts.items()
        ]
        + [
            {"version": "新算法", "bucket": key, "count": value}
            for key, value in scientific_counts.items()
        ]
    )

    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    sns.barplot(
        data=plot_frame,
        x="bucket",
        y="count",
        hue="version",
        ax=ax,
        palette=["#94a3b8", "#2563eb"],
    )
    ax.set_title("维护优先级变化")
    ax.set_xlabel("")
    ax.set_ylabel("船舶数量")
    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)

    return {"legacy": legacy_counts, "scientific": scientific_counts}


def build_top_drop_chart(dataframe: pd.DataFrame, output_path: Path) -> pd.DataFrame:
    top_drop = dataframe.sort_values("fpi_delta").head(12).copy()
    top_drop["label"] = top_drop["mmsi"].astype(str)

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    sns.barplot(data=top_drop, x="fpi_delta", y="label", color="#dc2626", ax=ax)
    ax.set_title("FPI 降幅最大的船舶")
    ax.set_xlabel("新旧 FPI 差值（新 - 旧）")
    ax.set_ylabel("MMSI")
    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)

    return top_drop[
        [
            "mmsi",
            "fpi_proxy_legacy",
            "fpi_proxy_scientific",
            "fpi_delta",
            "behavior_score",
            "environment_score",
        ]
    ]


def build_component_chart(dataframe: pd.DataFrame, output_path: Path) -> None:
    component_frame = pd.DataFrame(
        {
            "component": [
                "行为暴露",
                "海温适宜",
                "盐度适宜",
                "叶绿素压力",
                "水动力附着",
            ],
            "mean_score": [
                dataframe["behavior_score"].mean(),
                dataframe["temperature_score"].mean(),
                dataframe["salinity_score"].mean(),
                dataframe["productivity_score"].mean(),
                dataframe["hydrodynamic_score"].mean(),
            ],
        }
    )

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    sns.barplot(data=component_frame, x="component", y="mean_score", ax=ax, color="#0f766e")
    ax.set_title("新算法的平均机制分量")
    ax.set_xlabel("")
    ax.set_ylabel("平均分值")
    ax.set_ylim(0, 1)
    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def build_scatter_chart(dataframe: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    sns.scatterplot(
        data=dataframe,
        x="fpi_proxy_legacy",
        y="fpi_proxy_scientific",
        s=40,
        alpha=0.65,
        color="#2563eb",
        ax=ax,
    )
    diagonal_max = max(
        dataframe["fpi_proxy_legacy"].max(),
        dataframe["fpi_proxy_scientific"].max(),
    )
    ax.plot([0, diagonal_max], [0, diagonal_max], linestyle="--", color="#94a3b8", linewidth=1)
    ax.set_title("旧 FPI 与新 FPI 的逐船对比")
    ax.set_xlabel("旧 FPI")
    ax.set_ylabel("新 FPI")
    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def render_html_report(
    output_dir: Path,
    summary: dict[str, float],
    takeaways: list[str],
    priority_counts: dict[str, dict[str, int]],
    top_drop: pd.DataFrame,
) -> None:
    top_rows = "".join(
        f"""
        <tr>
          <td>{html.escape(str(row.mmsi))}</td>
          <td>{row.fpi_proxy_legacy:.3f}</td>
          <td>{row.fpi_proxy_scientific:.3f}</td>
          <td>{row.fpi_delta:.3f}</td>
          <td>{row.behavior_score:.3f}</td>
          <td>{row.environment_score:.3f}</td>
        </tr>
        """
        for row in top_drop.itertuples(index=False)
    )

    takeaway_html = "".join(f"<li>{html.escape(item)}</li>" for item in takeaways)

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>科学升级简报</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      background: #f5f7fb;
      color: #162033;
    }}
    .page {{
      width: min(1120px, calc(100% - 40px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    .hero, .panel {{
      background: white;
      border: 1px solid #d8e0ee;
      border-radius: 18px;
      box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
    }}
    .hero {{
      padding: 26px 28px;
      margin-bottom: 20px;
    }}
    .kicker {{
      margin: 0 0 8px;
      font-size: 12px;
      letter-spacing: 0.12em;
      color: #2563eb;
      text-transform: uppercase;
      font-weight: 700;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 34px;
      line-height: 1.15;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 24px;
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    p, li {{
      line-height: 1.75;
      color: #30425e;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .metric {{
      border: 1px solid #d8e0ee;
      border-radius: 14px;
      padding: 14px;
      background: #f8fbff;
    }}
    .metric span {{
      display: block;
      color: #4c5d7a;
      font-size: 13px;
    }}
    .metric strong {{
      display: block;
      margin-top: 8px;
      font-size: 26px;
    }}
    .panel {{
      padding: 22px;
      margin-top: 18px;
    }}
    .grid, .two-col, .formula-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .formula-card {{
      border: 1px solid #d8e0ee;
      border-radius: 14px;
      padding: 16px;
      background: #f8fbff;
    }}
    .formula {{
      margin: 10px 0;
      padding: 12px 14px;
      border-radius: 12px;
      background: #eef4ff;
      color: #1d4ed8;
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
      line-height: 1.6;
      white-space: pre-wrap;
    }}
    .tag {{
      display: inline-block;
      margin: 0 8px 8px 0;
      padding: 6px 10px;
      border-radius: 999px;
      background: #e2ecff;
      color: #1d4ed8;
      font-size: 13px;
      font-weight: 600;
    }}
    img {{
      width: 100%;
      border-radius: 14px;
      border: 1px solid #d8e0ee;
      background: white;
    }}
    .figure-note {{
      margin: 10px 0 0;
      font-size: 14px;
      color: #51627d;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e3eaf5;
      text-align: left;
    }}
    th {{
      color: #4c5d7a;
      background: #f8fbff;
    }}
    @media (max-width: 900px) {{
      .summary-grid, .grid, .two-col, .formula-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <p class="kicker">Science Upgrade Brief</p>
      <h1>新旧科学算法机制对比</h1>
      <p>这份简报用通俗语言说明：旧算法为什么容易把风险整体抬高，新算法为什么更接近“行为是主因、环境做修正、维护轻度参与”的逻辑。数据来自冻结的 15 天竞赛样本窗口。</p>
      <div class="summary-grid">
        <div class="metric"><span>旧 FPI 平均值</span><strong>{summary['legacy_fpi_mean']:.4f}</strong></div>
        <div class="metric"><span>新 FPI 平均值</span><strong>{summary['scientific_fpi_mean']:.4f}</strong></div>
        <div class="metric"><span>旧 ECP 平均值</span><strong>{summary['legacy_ecp_mean']:.4f}</strong></div>
        <div class="metric"><span>新 ECP 平均值</span><strong>{summary['scientific_ecp_mean']:.4f}</strong></div>
      </div>
    </section>

    <section class="panel">
      <h2>一句话先讲明白</h2>
      <ul>{takeaway_html}</ul>
    </section>

    <section class="panel">
      <h2>新算法具体怎么计算</h2>
      <p>新算法不再把海温、盐度、叶绿素和海流当成四个独立加分按钮，而是先拆成几个机制层，再合成环境修正值，最后与行为暴露和维护状态共同形成 FPI。</p>
      <div>
        <span class="tag">海温适宜度 T</span>
        <span class="tag">盐度适宜度 S</span>
        <span class="tag">叶绿素压力 P</span>
        <span class="tag">水动力附着 H</span>
        <span class="tag">行为暴露 BehaviorExposure</span>
        <span class="tag">维护修正 MaintenanceAdj</span>
      </div>
      <div class="formula-grid">
        <div class="formula-card">
          <h3>第一步：环境先拆机制</h3>
          <p>环境部分先回答四个问题：这里的海温和盐度适不适合附着生物稳定存活？这里的叶绿素压力高不高？这里的流动条件会不会把附着窗口冲掉？</p>
          <div class="formula">T = sst_suitability
S = salinity_suitability
P = productivity_pressure_from_chl
H = hydrodynamic_attachment_score_from_current_speed</div>
          <p class="figure-note">关键变化是：海流不再分别看 u 和 v，而是先合成为 current_speed，再判断附着会不会被冲掉。</p>
        </div>
        <div class="formula-card">
          <h3>第二步：先合成环境修正值</h3>
          <p>温度仍然最重要，盐度像一个闸门，叶绿素是生产力压力代理，海流是附着约束项。</p>
          <div class="formula">EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H
EnvAdj = 0.85 + 0.30 × EnvModifier</div>
          <p class="figure-note">这一版的重点是：环境乘子以 1 为中心，所以环境现在既可以增强，也可以削弱风险。</p>
        </div>
        <div class="formula-card">
          <h3>第三步：FPI 由行为主导</h3>
          <p>最终的 FPI 先看这艘船自己慢了多久、停了多久、靠港多久，再由环境和维护做轻修正。</p>
          <div class="formula">MaintenanceAdj = 0.90 + 0.20 × MaintenanceScore
FPI = BehaviorExposure × EnvAdj × MaintenanceAdj</div>
          <p class="figure-note">这一步解决了两个问题：环境不再只能降分，维护也不再完全被移出 FPI。</p>
        </div>
        <div class="formula-card">
          <h3>第四步：ECP 和 RRI</h3>
          <p>ECP 现在更像“污损代价放大器”，RRI 则继续服务于区域热点识别。</p>
          <div class="formula">CarbonPenaltyModifier = 1 + 0.18 × MaintenanceBurden + 0.12 × PersistentExposure
ECP = FPI × CarbonPenaltyModifier

RRI = 0.40 × EnvModifier + 0.25 × Traffic + 0.20 × StayProb + 0.15 × PortAnchorageIntensity</div>
          <p class="figure-note">所以 ECP 不再是第二版 FPI，RRI 也把“停留概率”和“港口/锚地强度”拆开了，减少重复计分。</p>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>旧算法怎么想</h2>
        <p>旧算法更像把环境变量当成几个独立的加分按钮。海温高一点、叶绿素高一点，分数就跟着往上走。它的方向不算完全错，但容易把“环境看起来不错”直接翻译成“这艘船一定很危险”。</p>
      </div>
      <div class="panel">
        <h2>新算法怎么想</h2>
        <p>新算法先问四件事：这片水是否适合附着生物存活，这里的生产力压力是否偏高，这里的水流是否会冲掉附着窗口，这艘船自己到底慢了多久、停了多久、靠港多久。只有当行为暴露足够高时，环境才会真正把风险放大。</p>
      </div>
    </section>

    <section class="panel">
      <h2>已有旧新评分总对比</h2>
      <img src="scoring_v1_vs_v2.png" alt="旧新评分总对比">
      <p class="figure-note">这张图是总览图。可以先看出一个大方向：新算法下，大部分船的评分都明显低于旧算法，说明旧算法确实更容易把整体风险抬高。</p>
    </section>

    <section class="two-col">
      <div class="panel">
        <h2>分布变化</h2>
        <img src="fpi_ecp_distribution_shift.png" alt="FPI 与 ECP 分布变化">
        <p class="figure-note">这张图看的是整体分布。旧算法的分数整体更靠右，也就是更容易给出偏高分；新算法把分布往中低区间拉回来了。</p>
      </div>
      <div class="panel">
        <h2>维护优先级变化</h2>
        <p>旧算法分级：优先评估 {priority_counts['legacy']['优先评估']}，持续监测 {priority_counts['legacy']['持续监测']}，当前较低 {priority_counts['legacy']['当前较低']}。</p>
        <p>新算法分级：优先评估 {priority_counts['scientific']['优先评估']}，持续监测 {priority_counts['scientific']['持续监测']}，当前较低 {priority_counts['scientific']['当前较低']}。</p>
        <img src="priority_shift.png" alt="维护优先级变化">
        <p class="figure-note">这张图看的是结论层面的变化。新算法仍然保留了一批需要优先评估的船，但不再像旧算法那样几乎把所有对象都推到高等级。</p>
      </div>
    </section>

    <section class="two-col">
      <div class="panel">
        <h2>新算法内部看什么</h2>
        <img src="mechanism_component_means.png" alt="新算法机制分量均值">
        <p class="figure-note">这张图是在拆新算法内部。它告诉你新算法不是只看一个总分，而是同时看行为暴露、海温适宜、盐度适宜、叶绿素压力和水动力附着几个机制分量。</p>
      </div>
      <div class="panel">
        <h2>逐船对比</h2>
        <img src="fpi_scatter_shift.png" alt="逐船 FPI 旧新对比">
        <p class="figure-note">这张图看单船层面的变化。虚线表示“新旧分数一样高”，大多数点落在虚线下方，说明同一艘船在新算法里的 FPI 往往低于旧算法。</p>
      </div>
    </section>

    <section class="panel">
      <h2>降幅最大的船舶</h2>
      <img src="top_fpi_drop.png" alt="FPI 降幅最大的船舶">
      <p>这些船在新算法里被压分最明显。通常不是因为它们完全没风险，而是旧算法把环境因素抬得过高；新算法要求“环境适宜 + 行为暴露也高”同时成立。</p>
      <p class="figure-note">这张图适合讲案例。它列出从旧算法切到新算法后降幅最大的对象，方便你解释“哪些船以前被环境项抬分抬得太厉害”。</p>
    </section>

    <section class="panel">
      <h2>案例表</h2>
      <table>
        <thead>
          <tr>
            <th>MMSI</th>
            <th>旧 FPI</th>
            <th>新 FPI</th>
            <th>差值</th>
            <th>行为暴露</th>
            <th>环境修正</th>
          </tr>
        </thead>
        <tbody>
          {top_rows}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""
    (output_dir / "science_upgrade_brief.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    comparison_path = Path(args.comparison_csv)
    summary_path = Path(args.summary_json)
    base_chart_path = Path(args.base_chart)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    configure_matplotlib()

    dataframe = pd.read_csv(comparison_path)
    dataframe["mmsi"] = dataframe["mmsi"].astype(str)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    distribution_chart = output_dir / "fpi_ecp_distribution_shift.png"
    priority_chart = output_dir / "priority_shift.png"
    top_drop_chart = output_dir / "top_fpi_drop.png"
    mechanism_chart = output_dir / "mechanism_component_means.png"
    scatter_chart = output_dir / "fpi_scatter_shift.png"

    build_distribution_chart(dataframe, distribution_chart)
    priority_counts = build_priority_shift_chart(dataframe, priority_chart)
    top_drop = build_top_drop_chart(dataframe, top_drop_chart)
    build_component_chart(dataframe, mechanism_chart)
    build_scatter_chart(dataframe, scatter_chart)
    shutil.copy2(base_chart_path, output_dir / "scoring_v1_vs_v2.png")

    takeaways = plain_language_takeaways(summary)
    render_html_report(output_dir, summary, takeaways, priority_counts, top_drop)

    print(f"Science briefing written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
