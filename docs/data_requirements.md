# 数据接入前置说明

## 目标

在真实数据尚未下载前，先把“需要什么数据、数据长什么样、数据到了以后怎么接”定义清楚，避免后续下载完成后再返工。

## 第一阶段必须准备的数据

### 1. AIS 原始轨迹数据

最低要求：

- 文件格式：CSV
- 时间范围：建议先取 1 个月
- 空间范围：新加坡研究区 bbox
- 最低字段：`mmsi`、`timestamp`、`latitude`、`longitude`

推荐补充字段：

- `sog`
- `cog`
- `heading`
- `nav_status`
- `ship_type`
- `imo`

### 2. 海洋环境数据

最低要求：

- 文件格式：CSV
- 时间范围：与 AIS 尽量重叠
- 空间范围：覆盖同一研究区
- 最低字段：`timestamp`、`latitude`、`longitude`、`sst`

推荐补充字段：

- `salinity`
- `current_u`
- `current_v`
- `chlorophyll_a`

## 当前约定

- 当前脚本首版统一按 CSV 接入
- 如果原始环境数据来自 NetCDF，建议先导出为研究区内的 CSV 再进入当前流水线
- 时间字段统一建议使用 UTC ISO 8601

## 文件与模板

- AIS 字段模板：[data/contracts/ais_columns_template.csv](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/ais_columns_template.csv)
- 环境字段模板：[data/contracts/env_columns_template.csv](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/env_columns_template.csv)
- 数据清单模板：[data/contracts/dataset_manifest.template.json](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/dataset_manifest.template.json)

## 接入顺序

1. 把真实 AIS 文件放到 `data/raw/`
2. 把真实环境文件放到 `data/external/`
3. 复制数据清单模板并改成真实路径
4. 先运行 AIS 清洗
5. 再运行环境处理
6. 再运行特征构建
7. 最后生成报告
