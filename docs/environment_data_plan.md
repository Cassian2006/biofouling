# 环境数据下载方案

## 结论

第一阶段不用把所有海洋变量都拉齐。先下载一套“能支撑 FPI/ECP 的最小环境数据”，再逐步扩展。

## 第一阶段最小必需变量

### 必需

- `sst`
  作用：高温暴露代理，是污损增长环境适宜性的核心变量。
- `chlorophyll_a`
  作用：生物活性代理，用来近似附着生物活跃程度。

### 推荐但可后补

- `salinity`
  作用：作为环境修正因子，第一阶段不是必须。
- `current_u`
- `current_v`
  作用：用于解释水动力环境和后续区域风险图层，第一阶段可选。

## 时间与空间建议

### 时间范围

- 先与 AIS 同步取 1 个月。
- 如果下载成本高，可以先按日尺度。
- 如果数据源支持更细时间分辨率，先不强求，日尺度足够完成第一阶段。

### 空间范围

- 研究区采用当前 bbox：
  `west=102.90, south=0.80, east=104.90, north=1.85`
- 实际下载时建议四周额外留一点缓冲，避免边界裁剪太死。

### 空间分辨率

- 第一阶段不追求最高精度。
- 能覆盖新加坡海峡主要梯度变化即可。
- 原则上只要不是粗到完全丢失港区与海峡差异，就足够先跑通。

## 推荐下载顺序

1. 先下载 `sst`
2. 再下载 `chlorophyll_a`
3. 如果下载和处理都顺利，再补 `salinity`
4. 最后再补 `current_u/current_v`

## 当前接入格式要求

当前项目首版统一要求转成 CSV，字段至少包括：

- `timestamp`
- `latitude`
- `longitude`
- `sst`

如果有更多变量，则继续附加：

- `salinity`
- `current_u`
- `current_v`
- `chlorophyll_a`

## 来源建议

- 优先使用 Copernicus Marine 一类的公开海洋产品。
- 第一阶段优先拿“物理环境”一套和“生物地球化学”一套，不要一开始就下载过多产品。
- 如果原始文件是 NetCDF，建议先只导出研究区与时间窗内的 CSV，再进入当前流水线。

## 到哪里下载

- Copernicus Marine Data Store:
  https://data.marine.copernicus.eu/
- Copernicus MyOcean Light Viewer:
  https://data.marine.copernicus.eu/

实际建议：

- 查产品、看变量、确认覆盖范围时，用 MyOcean Light / Data Store 页面；
- 真正下载研究区和时间窗数据时，用 Copernicus Marine Data Store 对应产品页面的下载方式；
- 如果后续批量化需要更强，可以再接 Copernicus 的 Python 工具链，但当前不是必需。

## 当前已验证可用的数据集

### 温度

- 数据集 ID：`cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m`
- 变量：`thetao`
- 用途：作为第一阶段 `sst` 代理

### 叶绿素

- 数据集 ID：`cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m`
- 变量：`chl`
- 用途：作为第一阶段 `chlorophyll_a` 变量

## 当前验证结果

- 时间窗 `2026-01-15T00:00:00Z` 到 `2026-01-18T00:00:00Z` 已通过 dry-run
- 以上两个数据集已成功完成真实下载
- 说明当前 2026 测试时间窗可以直接与 AIS 对齐，暂时不需要回退到 2025

## 和当前项目的关系

一旦环境数据转成上述 CSV，现有脚本就可以直接接入：

1. `scripts/process_env.py`
2. `scripts/build_features.py`
3. `scripts/generate_report.py`

## 2026-03-07 补充更新：新增已验证环境数据集

### 盐度
- 数据集 ID：`cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m`
- 变量：`so`
- 当前状态：已完成真实下载

### 海流
- 数据集 ID：`cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m`
- 变量：`uo`、`vo`
- 当前状态：已完成真实下载

## 当前处理链更新

当前环境处理脚本已支持：
- `thetao -> sst`
- `chl -> chlorophyll_a`
- `so -> salinity`
- `uo -> current_u`
- `vo -> current_v`

当前完整环境表已能携带：
- `sst`
- `chlorophyll_a`
- `salinity`
- `current_u`
- `current_v`
