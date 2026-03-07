# 数据资源总表

本文档汇总本项目第一阶段与后续扩展所需的数据资源，按“必须 / 推荐 / 可选”分层整理。

## A. 必须数据

### 1. AIS 轨迹数据

来源：

- 你现有的 AIS API 下载脚本
- 或任何能导出同类 AIS 字段的合法数据源

最少字段：

- `mmsi`
- `timestamp`
- `latitude`
- `longitude`

推荐字段：

- `sog`
- `cog`
- `heading`
- `nav_status`
- `ship_type`
- `imo`

作用：

- 重建船舶轨迹
- 识别低速、停泊、锚泊等行为
- 计算行为暴露特征
- 生成单船报告

### 2. 海表温度 `sst`

推荐来源：

- Copernicus Marine Data Store

当前首选数据集：

- `cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m`

当前变量：

- `thetao`

作用：

- 作为温度暴露核心变量
- 支撑 FPI 中的环境适宜性部分
- 支撑 ECP 中的高温修正项

### 3. 叶绿素 `chlorophyll_a`

推荐来源：

- Copernicus Marine Data Store

当前首选数据集：

- `cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m`

当前变量：

- `chl`

作用：

- 作为生物活性代理变量
- 支撑 FPI 中的生物活跃暴露
- 支撑 ECP 中的环境放大项

## B. 推荐数据

### 4. 盐度 `salinity`

推荐来源：

- Copernicus Marine Data Store

作用：

- 作为环境修正项
- 后续可提高环境暴露解释力

### 5. 海流 `current_u / current_v`

推荐来源：

- Copernicus Marine Data Store

作用：

- 支撑区域风险图层
- 用于解释不同海区水动力环境差异
- 可用于后续更精细的暴露建模

### 6. 港口与锚地辅助数据

推荐来源：

- World Port Index
- 新加坡 MPA Oceans X / Maritime Data Hub

作用：

- 标记港口位置
- 辅助识别港口访问与近港暴露
- 帮助解释高风险区域与停泊行为

## C. 可选增强数据

### 7. 新加坡港到港 / 离港 / 船舶动态数据

推荐来源：

- MPA Oceans X

作用：

- 做案例校验
- 对照 AIS 轨迹的进出港行为
- 辅助构建港口访问事件链

### 8. 文献经验参数

来源：

- 船体污损与能耗惩罚相关论文、技术报告

作用：

- 给 ECP 提供首版经验参数
- 支持清洗建议阈值的初步设定

### 9. 船舶静态资料

来源：

- AIS 附带字段
- 或独立船舶资料源

字段示例：

- 船长
- 船宽
- 吃水
- 船型
- DWT / GRT / TEU

作用：

- 后续做船型分层分析
- 修正不同船型的暴露与惩罚差异

## 当前第一阶段最小闭环实际需要

如果只想尽快跑通第一阶段，实际只需要这四类：

1. AIS 轨迹数据
2. `sst`
3. `chlorophyll_a`
4. 基础港口/锚地参考信息

## 下载入口建议

### 环境数据

- Copernicus Marine Data Store: https://data.marine.copernicus.eu/
- Copernicus MyOcean Light Viewer: https://data.marine.copernicus.eu/

说明：

- 如果只是查产品、试看片区、确认变量，可先用 MyOcean Light。
- 如果要做研究区时间窗下载，优先使用 Data Store 中的产品页面和下载服务。

### 港口与船舶辅助数据

- MPA Oceans X: https://oceans-x.mpa.gov.sg/
- NGA World Port Index 相关资料入口: https://msi.nga.mil/

## 下载优先级

1. 先下载 AIS
2. 再下载 `sst`
3. 再下载 `chlorophyll_a`
4. 如果流程稳定，再补 `salinity`
5. 最后再补海流和更多辅助数据
