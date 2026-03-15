# 评分结构说明

## 升级目标

本轮科学升级的目标不是把平台改造成绝对真值模型，而是让评分结构更符合以下三条原则：

1. 行为暴露是主因。
2. 环境因子既可以增强，也可以削弱风险。
3. 维护状态应保留为轻修正项，而不是完全从污损倾向判断中消失。

## 总体结构

当前评分结构分为：

- 环境机制层
- 行为暴露层
- 维护轻修正层
- 代价放大层
- 区域综合风险层

## 环境机制层

### 生理适宜层

输入：

- `sst`
- `salinity`

回答的问题：

- 当前水体是否允许常见附着生物较稳定地存活、生长和繁殖。

输出：

- `T = sst_suitability`
- `S = salinity_suitability`

### 生产力/传播压力层

输入：

- `chlorophyll_a`

回答的问题：

- 该区域是否具有更高的食物供给、初级生产力和传播压力。

输出：

- `P = productivity_pressure_from_chl`

### 附着水动力层

输入：

- `current_speed = sqrt(current_u^2 + current_v^2)`

回答的问题：

- 当前流动条件更利于早期附着，还是更容易冲掉附着窗口。

输出：

- `H = hydrodynamic_attachment_score`

## 行为暴露层

行为暴露仍是主因，当前主要由以下代理项表达：

- `low_speed_hours`
- `anchor_hours`
- `dwell_hours`
- `port_proximity_hours`
- `port_visits`

它回答的是：

- 这艘船到底慢了多久、停了多久、靠港多久。

## 维护轻修正层

维护状态不再完全交给 ECP，而是重新回到 FPI 中，作为轻度修正项表达：

- `maintenance_score`
- `maintenance_multiplier`

它回答的是：

- 刚维护过的船和长期未维护的船，在同样暴露下是否应保持相同污损倾向。

## 响应函数设计

### SST

采用“暖水促进 + 极端高温软回落”的分段结构：

- `< 18°C`：明显不利
- `18–25°C`：快速上升
- `25–31°C`：高平台
- `31–33°C`：轻微回落
- `> 33°C`：继续回落但不归零

### Salinity

采用“门槛/闸门型”结构：

- `< 20 psu`：强惩罚
- `20–28 psu`：快速上升
- `28–35 psu`：宽平台
- `35–38 psu`：轻微软回落
- `> 38 psu`：继续下降

### Chlorophyll-a

采用“压力代理的饱和增益”结构：

- `< 0.5 μg/L`：低压力
- `0.5–2 μg/L`：中等
- `2–8 μg/L`：高压力
- `> 8 μg/L`：封顶，不再继续加分

### Current

不再分别给 `u / v` 打分，而是先合成为 `current_speed`，再按照“低流速更利于附着、高流速更不利于附着”的方向打分。当前切点使用研究区局地百分位，而非直接套用实验流速阈值。

## 正式公式

### 环境修正值

```text
EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H
```

权重逻辑：

- 温度仍是最强直接驱动。
- 盐度更像闸门，不是主导项。
- 叶绿素是重要代理，但不应高过温度。
- 海流是附着约束项，但受数据尺度限制，权重不宜过高。

### FPI

```text
EnvAdj = 0.85 + 0.30 × EnvModifier
MaintenanceAdj = 0.90 + 0.20 × MaintenanceScore

FPI = BehaviorExposure × EnvAdj × MaintenanceAdj
```

设计含义：

- 行为暴露仍是主因。
- 环境现在既可以增强，也可以削弱风险。
- 维护状态保留为轻修正，不再完全脱离 FPI。

### ECP

```text
CarbonPenaltyModifier = 1 + 0.18 × MaintenanceBurden + 0.12 × PersistentExposure

ECP = FPI × CarbonPenaltyModifier
```

设计含义：

- ECP 不再像“第二版 FPI”。
- 它表达的是：当污损倾向已经存在后，维护滞后与持续高暴露会进一步放大潜在能耗代价。

### RRI

```text
RRI = 0.40 × EnvModifier + 0.25 × Traffic + 0.20 × StayProb + 0.15 × PortAnchorageIntensity
```

设计含义：

- `Traffic`：交通疏密
- `StayProb`：低速/停泊概率
- `PortAnchorageIntensity`：港口/锚地参考层强度

该结构用于避免把同一个“停留事实”同时放进多个维度重复计分。

## 阈值策略

由于科学升级后的分数整体尺度下移，阈值已同步重标：

- `Prioritize cleaning assessment`
  - `FPI >= 0.25` 或 `ECP >= 0.30`
- `Monitor exposure trend`
  - `FPI >= 0.08` 或 `ECP >= 0.10`
- 其余为 `Low immediate concern`

## 当前工程策略

- 冻结的竞赛主版本样本保持不被覆盖。
- 新科学评分作为优先升级路线与对比层推进。
- 旧分数保留为 `legacy` 列，用于答辩和新旧对照。
