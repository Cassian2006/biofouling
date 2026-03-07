# 1.0 数据补齐计划

本文档只回答三个问题：

1. 1.0 还缺哪些数据类别
2. 这些数据应该按什么顺序补
3. 补齐后当前流水线怎么接

## 当前结论

当前项目的最小闭环已经有：

- AIS 轨迹
- `sst` 代理数据
- `chlorophyll_a` 代理数据

当前项目的 1.0 展示与解释体验要进一步做实，还建议补齐：

- `salinity`
- `current_u`
- `current_v`
- 基础港口 / 锚地参考数据

其中，前 3 项可以直接通过 Copernicus API 补齐；港口 / 锚地参考数据建议先做轻量参考层，不需要一开始就追求完整港口知识库。

## 建议优先级

### 第一优先级：环境变量补齐

目标：

- 让环境表不再只包含 `sst` 和 `chlorophyll_a`
- 把 `salinity`、`current_u`、`current_v` 一并纳入处理链

当前已准备好的任务文件：

- [copernicus_so_20260115_20260118.json](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/copernicus_so_20260115_20260118.json)
- [copernicus_currents_20260115_20260118.json](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/copernicus_currents_20260115_20260118.json)

官方产品依据：

- Copernicus Marine `GLOBAL_ANALYSISFORECAST_PHY_001_024`
- 当前确认可用数据集：
  - `cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m`
  - `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m`

### 第二优先级：港口 / 锚地参考层

目标：

- 让区域页和单船页不只看“轨迹在哪里”，还开始看“是否靠近港口、航道、锚地”

建议来源：

- 新加坡 MPA Oceans X / Maritime Data Hub
- NGA World Port Index

建议做法：

- 先做一个轻量参考层
- 先保证能标出港口和主要近港区域
- 后续再增加更细的港区事件与到离港校验

### 第三优先级：静态船舶资料与外部校验数据

目标：

- 为 1.5 的更深层分析做准备
- 让后续船型分层、惩罚修正和案例核验更稳

建议内容：

- 船长 / 船宽 / 吃水
- 船型
- DWT / GRT / TEU
- 到港 / 离港或其他案例参考数据

## 当前流水线接法

环境变量补齐后，当前脚本链路可继续沿用：

1. [download_env_copernicus.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/download_env_copernicus.py)
2. [process_env.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/process_env.py)
3. [build_features.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/build_features.py)
4. [generate_report.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/generate_report.py)

其中 [process_env.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/process_env.py) 现已支持：

- `thetao -> sst`
- `chl -> chlorophyll_a`
- `so -> salinity`
- `uo -> current_u`
- `vo -> current_v`

## 建议的下一步动作

1. 直接下载 `salinity`
2. 直接下载 `current_u/current_v`
3. 重新生成完整环境表
4. 重新跑一次特征构建
5. 再决定港口 / 锚地参考层怎么接进前端
