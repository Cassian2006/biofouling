# 竞赛主版本冻结说明

## 目的

将当前已经稳定跑通的 `15 天` 数据链路固定为竞赛评审主版本，确保后续 2.x 升级不会改变评审展示所使用的样本、截图口径和核心结论。

## 冻结窗口

- 时间窗：`20260115 to 20260130`
- 状态：`frozen`
- 版本标识：`competition_main_v1`

## 冻结清单

以 [competition_baseline.json](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/config/competition_baseline.json) 为唯一清单，固定以下产物：

- 研究区清洗 AIS：`data/processed/ais_20260115_20260130_cleaned.csv`
- 环境特征表：`data/processed/env_20260115_20260130.csv`
- 船舶特征表：`data/processed/vessel_features_20260115_20260130.csv`
- 区域风险结果：`outputs/maps/regional_risk_20260115_20260130.csv`
- 航次报告：`outputs/reports/voyage_report_20260115_20260130.md`
- 参考站点：`data/reference/singapore_reference_sites.csv`
- 前端静态回退数据：
  - `frontend/public/demo/summary.json`
  - `frontend/public/demo/vessels.json`
  - `frontend/public/demo/risk_cells.json`

## 基线口径

冻结后的标准摘要如下：

- `vessels_summarized = 637`
- `grid_cells = 1143`
- `high_risk_cells = 1`
- `medium_risk_cells = 78`
- recommendation 分布：
  - `Prioritize cleaning assessment = 284`
  - `Monitor exposure trend = 340`
  - `Low immediate concern = 13`
- anomaly 分布：
  - `highly_abnormal = 16`
  - `suspicious = 70`
  - `normal = 400`
  - `observation_insufficient = 151`

## 使用规则

- 后端 demo 接口优先读取冻结清单，而不是自动选择“最新文件”。
- 新时间窗、新模型或新分析结果不得覆盖这套基线文件。
- 若后续需要替换竞赛主版本，应新建新的 baseline 清单，而不是直接修改旧清单对应的数据。
- 所有评审截图、录屏、汇报数字优先以这套冻结基线为准。
