# 异常污损暴露检测模块

## 当前定位

这是 `1.5` 的第二条主线，目标不是预测下一时间窗，而是回答：

- 哪些船的当前暴露模式明显偏离同批船舶样本
- 这些异常主要来自哪些行为或环境信号

模块的产品作用是补强：

- 总览页的异常高风险对象筛查
- 单船页的“为什么值得优先看”解释层

## 当前输入

当前直接复用已产出的船舶特征表：

- `data/processed/vessel_features_*.csv`

首版输入特征包括：

- `ping_count`
- `low_speed_ratio`
- `mean_sst`
- `mean_chlorophyll_a`
- `mean_salinity`
- `current_speed`
- `track_duration_hours`
- `fpi_proxy`
- `ecp_proxy`

其中 `current_speed` 由 `mean_current_u / mean_current_v` 推导而来。

## 模型设计

首版采用轻量 `Autoencoder`，理由是：

- 能满足 `1.5` 的“轻量、可部署、可解释增强”目标
- 不需要标注异常标签
- 可直接对当前船舶特征向量做重建误差分析

当前结构：

- 输入层：`9` 维
- 编码器：`input -> hidden -> latent`
- 解码器：`latent -> hidden -> input`
- 激活函数：`ReLU`
- 训练目标：最小化重建 `MSE`

## 训练与评估流程

当前已补齐：

- 训练脚本：`scripts/train_exposure_autoencoder.py`
- 评估脚本：`scripts/evaluate_exposure_autoencoder.py`
- 特征与解释工具：`scripts/exposure_anomaly.py`

训练阶段会：

1. 读取最新船舶特征表
2. 构造异常检测输入特征
3. 按随机种子切分训练集和验证集
4. 训练轻量 `Autoencoder`
5. 保存模型与缩放参数

评估阶段会：

1. 读取模型与缩放参数
2. 对全部船舶做重建
3. 用重建误差生成 `anomaly_score`
4. 按分位数划分：
   - `normal`
   - `suspicious`
   - `highly_abnormal`
5. 输出每艘船的前三个异常驱动项

## 当前输出

评估产物会写到：

- `outputs/models/exposure_autoencoder_*/evaluation/`

包含：

- `vessel_anomaly_scores.csv`
- `evaluation.json`

其中每艘船会包含：

- `anomaly_score`
- `anomaly_level`
- `explanation_1`
- `explanation_2`
- `explanation_3`

## 当前意义

这一步的意义是把 1.5 的第二条线从“只有想法”推进到“已有真实训练与评分入口”。

下一步最自然的方向是：

1. 先在当前 15 天真实样本上训练首版 `Autoencoder`
2. 看高分异常对象是否具备解释性
3. 决定是否将异常榜单接入总览页与单船页
# 当前分级口径补充（2026-03-07）

为避免把轨迹过短、点数过少的对象误判为“高度异常”，当前分级规则已调整为两步：

1. 先判断观测是否充分
- `ping_count < 50` 或 `track_duration_hours < 12`
- 直接标记为 `observation_insufficient`

2. 对其余对象按固定分数阈值分级
- `anomaly_score >= 0.35` -> `highly_abnormal`
- `0.12 <= anomaly_score < 0.35` -> `suspicious`
- `anomaly_score < 0.12` -> `normal`

在当前 `637` 艘船的 15 天样本上，调整后的分布为：
- `highly_abnormal = 16`
- `suspicious = 70`
- `normal = 400`
- `observation_insufficient = 151`

这样做的目的，是让“高度异常”更接近真正的暴露模式偏离，而不是被观测稀疏样本挤占。
