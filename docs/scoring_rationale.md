# 评分结构说明

## 目标

本轮科学升级的目标不是把平台改成一个“绝对真值模型”，而是让评分结构更符合三个原则：

- 行为暴露是主因
- 环境因子既可以增强，也可以削弱风险
- 维护状态不应完全从污损积累倾向中消失

因此，当前评分结构不再采用“环境变量各自单调加分”的旧逻辑，而是采用：

- `3 个环境机制层`
- `1 个行为主导层`
- `1 个维护轻修正层`

## 新结构

### 1. 环境机制层

#### 生理适宜层
输入：
- `sst`
- `salinity`

含义：
- 这片水体是否允许常见附着生物较稳定地存活、生长、繁殖

输出：
- `T = sst_suitability`
- `S = salinity_suitability`

#### 生产力 / 传播压力层
输入：
- `chlorophyll_a`

含义：
- 这里是否更容易形成较高的食物供给、初级生产力和传播压力

输出：
- `P = productivity_pressure_from_chl`

#### 附着水动力层
输入：
- `current_speed = sqrt(current_u^2 + current_v^2)`

含义：
- 流动条件是更利于早期附着，还是更容易把附着窗口冲掉

输出：
- `H = hydrodynamic_attachment_score`

### 2. 行为暴露主层

行为暴露当前由以下代理项组成：

- `low_speed_hours`
- `anchor_hours`
- `dwell_hours`
- `port_proximity_hours`
- `port_visits`

含义：
- 这艘船到底慢了多久、停了多久、靠港多久

### 3. 维护轻修正层

维护状态不再完全交给 ECP 去处理，而是保留为 FPI 的轻度修正项：

- `maintenance_score`
- `maintenance_multiplier`

含义：
- 刚维护过的船应比长期未维护的船更不容易积累相同程度的污损倾向

## 变量响应函数

### SST

采用“暖水促进 + 极端高温软回落”的分段结构：

- `< 18°C`：明显不利
- `18–25°C`：快速上升
- `25–31°C`：高平台
- `31–33°C`：轻微回落
- `> 33°C`：继续回落，但不直接归零

### Salinity

采用“门槛 / 闸门型”结构：

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

不再分别给 `u / v` 打分，而是先合成为 `current_speed`，再按“低流速更利于附着、高流速更不利于附着”的方向建模。

当前具体切点不直接套实验室绝对阈值，而是采用研究区局地百分位：

- `P25 = 0.3303`
- `P50 = 0.3685`
- `P75 = 0.4189`
- `P90 = 0.4610`

## 正式评分结构

### 1. 环境修正值

```text
EnvModifier = 0.40T + 0.20S + 0.25P + 0.15H
```

权重逻辑：

- 温度仍是最强直接驱动
- 盐度更像闸门，不是主导项
- 叶绿素是重要代理，但不高过温度
- 海流是附着约束项，但受数据尺度限制，不宜给太高

### 2. FPI

```text
EnvAdj = 0.85 + 0.30 × EnvModifier
MaintenanceAdj = 0.90 + 0.20 × MaintenanceScore

FPI = BehaviorExposure × EnvAdj × MaintenanceAdj
```

含义：

- 行为暴露仍是主因
- 环境现在既可以增强，也可以削弱风险
- 维护状态作为轻修正保留在 FPI 中

这一步比上一版更合理，因为环境乘子不再“只能降分”，而是以 `1` 为中心：

- 环境差：削弱行为风险
- 环境好：增强行为风险

### 3. ECP

```text
CarbonPenaltyModifier = 1 + 0.18 × MaintenanceBurden + 0.12 × PersistentExposure

ECP = FPI × CarbonPenaltyModifier
```

含义：

- ECP 不再像“第二版 FPI”
- 它表示的是：当污损倾向已经存在后，长期未维护与持续性暴露会把潜在能耗代价进一步放大

这里的 `PersistentExposure` 更强调持续时间结构，而不是把温度、叶绿素再完整重算一遍。

### 4. RRI

```text
RRI = 0.40 × EnvModifier + 0.25 × Traffic + 0.20 × StayProb + 0.15 × PortAnchorageIntensity
```

其中：

- `Traffic`：交通疏密
- `StayProb`：低速 / 停泊概率
- `PortAnchorageIntensity`：港口 / 锚地参考层强度

这样可以避免把“同一个停留事实”同时放进 `Anchorage` 和 `Behavior` 两个桶里重复计分。

## 当前阈值策略

由于科学升级后的分数尺度整体下降，建议分级阈值也已重标：

- `Prioritize cleaning assessment`
  - `FPI >= 0.25` 或 `ECP >= 0.30`
- `Monitor exposure trend`
  - `FPI >= 0.08` 或 `ECP >= 0.10`
- 其余为 `Low immediate concern`

这一步的目的不是“强行恢复旧分布”，而是避免在新尺度下出现大量对象被机械地打回“安全”。

## 当前工程策略

- 冻结的竞赛主版本样本保持不被覆盖
- 新科学评分作为优先升级路线与对比层推进
- 旧分数保留为 `legacy` 列，用于对照与答辩说明
