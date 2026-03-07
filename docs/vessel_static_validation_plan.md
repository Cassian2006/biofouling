# 船舶静态资料与外部校验数据接入计划

本文档面向 1.0 的第二类数据补齐工作：船舶静态资料与外部校验数据。

## 目标

这条线解决三个问题：

1. 单船页不再只展示“行为结果”，还要展示“船舶画像”
2. 后续可以按船型、尺度、载重能力做分层分析
3. 给未来的案例核验和到离港对照预留正式接入口

## 当前接入策略

### 船舶静态资料

当前分两层接：

- 第一层：没有外部静态表时，从 AIS 中派生基础船舶画像
- 第二层：有外部静态表时，用外部字段覆盖和补全

当前建议字段模板：

- [vessel_static_columns_template.csv](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/vessel_static_columns_template.csv)

建议字段：

- `mmsi`
- `vessel_name`
- `imo`
- `ship_type`
- `flag`
- `build_year`
- `length_m`
- `beam_m`
- `design_draught_m`
- `dwt`
- `grt`
- `teu`
- `source`

### 外部校验数据

当前先接“事件型校验表”，不急着一开始就做复杂港口事件知识图谱。

当前建议字段模板：

- [external_validation_events_template.csv](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/data/contracts/external_validation_events_template.csv)

建议字段：

- `validation_id`
- `mmsi`
- `event_type`
- `event_start`
- `event_end`
- `port_name`
- `latitude`
- `longitude`
- `source`
- `notes`

## 当前脚本链

### 船舶画像生成

- [build_vessel_catalog.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/build_vessel_catalog.py)

作用：

- 从 AIS 生成基础船舶画像
- 合并外部静态资料
- 输出可供后端和前端使用的船舶目录

### 校验事件汇总

- [summarize_validation_events.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/summarize_validation_events.py)

作用：

- 把事件级外部校验数据汇总成单船级摘要
- 输出单船最近事件、事件数量、来源数量等信息

## 1.0 阶段建议

1. 先让单船页能稳定展示船舶画像
2. 再让单船页能显示“是否已有外部校验事件”
3. 后续再把这些资料进一步用于模型修正和案例核验
