# 参数来源表

| 项目 | 当前取值 / 结构 | 来源类型 | 说明 |
| --- | --- | --- | --- |
| SST 响应 | `<18 / 18-25 / 25-31 / 31-33 / >33` | 机理 + 热带港区工程先验 | 方向由温度影响繁殖与附着的海洋附着生物文献支持，切点按新加坡港区场景设定 |
| Salinity 响应 | `<20 / 20-28 / 28-35 / 35-38 / >38` | 机理 + 工程先验 | 低盐应激有明确机制基础；正常海水区间设为宽平台 |
| Chlorophyll-a 响应 | `<0.5 / 0.5-2 / 2-8 / >8` | 生产力代理 + 工程先验 | 作为食物供给和传播压力代理，不当作直接生理最优变量 |
| Current 响应方向 | 低流速有利，高流速不利 | 机理文献 | 依据 cyprid 临时附着与流动条件关系 |
| Current 切点 | `P25 / P50 / P75 / P90` | 局地百分位 | 当前使用冻结 15 天窗口的研究区局地分布，不直接硬套实验阈值 |
| EnvModifier 权重 | `0.40T + 0.20S + 0.25P + 0.15H` | 工程综合权重 | 基于机理相对重要性设定，不是直接文献系数 |
| FPI 结构 | `Behavior × (0.7 + 0.3×Env)` | IMO 逻辑 + 工程实现 | 表达行为主因、环境修正，避免环境单独主导 |
| ECP 放大项 | `maintenance + productivity + temperature + low-speed pressure` | 工程启发式 | 当前仍属于代理惩罚，不应解释为绝对燃油代价 |
| RRI 结构 | `0.40 Env + 0.25 Traffic + 0.20 Anchorage + 0.15 Behavior` | 区域风险表达设计 | 用于热点识别，不用于绝对生态量估计 |
| 异常检测主引擎 | Dense Autoencoder | 无监督学习常规做法 | 识别偏离常规模式对象，不等于真实污损已经发生 |
| 时序预测主引擎 | 单层 LSTM | 工程成熟方法 | 当前预测下一时间窗 FPI proxy，属于短期趋势模型 |

## 外部参考集

- [IMO Biofouling 页面](https://www.imo.org/en/OurWork/Environment/Pages/Biofouling.aspx)
- [Journal of Experimental Biology: Temporary adhesion of barnacle cyprids](https://journals.biologists.com/jeb/article/211/13/2178/18261/Temporary-adhesion-of-barnacle-cyprids-effects-of/18261)

## 当前口径

- 表中“机理文献”指方向和结构受文献支持
- 表中“工程先验”指当前项目按热带港区场景做的第一版落地
- 表中“局地百分位”指当前直接从冻结 15 天样本中提取的本地尺度
