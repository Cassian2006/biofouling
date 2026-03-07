# 数据字典草案

## AIS 原始数据

| 字段名 | 类型 | 是否必需 | 含义 | 备注 |
| --- | --- | --- | --- | --- |
| mmsi | string | 是 | 船舶唯一识别号 | 主键之一 |
| imo | string | 否 | IMO 编号 | 若源数据提供 |
| timestamp | datetime | 是 | 轨迹时间戳 | 建议统一为 UTC |
| latitude | float | 是 | 纬度 | WGS84 |
| longitude | float | 是 | 经度 | WGS84 |
| sog | float | 否 | 对地航速 | 单位需统一 |
| cog | float | 否 | 对地航向 | 0-360 |
| heading | float | 否 | 船首向 | 可缺失 |
| nav_status | string | 否 | 航行状态 | 用于识别停泊等行为 |
| ship_type | string | 否 | 船型 | 首批样本建议聚焦一种主船型 |

## 环境数据

| 字段名 | 类型 | 是否必需 | 含义 | 备注 |
| --- | --- | --- | --- | --- |
| timestamp | datetime | 是 | 环境时间戳 | 与 AIS 对齐 |
| latitude | float | 是 | 纬度 | 网格中心或观测点 |
| longitude | float | 是 | 经度 | 网格中心或观测点 |
| sst | float | 是 | 海表温度 | 可作为高温暴露代理 |
| salinity | float | 否 | 盐度 | 后续可用于修正 |
| current_u | float | 否 | 海流 u 分量 | 可选 |
| current_v | float | 否 | 海流 v 分量 | 可选 |
| chlorophyll_a | float | 否 | 叶绿素浓度 | 生物活性代理 |

## 后续补充

- 港口与锚地辅助数据
- 航次级特征表
- 区域级栅格或分区统计表
