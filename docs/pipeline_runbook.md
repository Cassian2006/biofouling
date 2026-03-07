# Pipeline Runbook

## 当前阶段

项目已推进到“数据接入前一刻”。也就是说，流程、目录、模板和执行顺序已经准备好，下一步只差真实数据文件。

## 推荐执行顺序

### 1. 清洗 AIS

```bash
python scripts/ingest_ais.py --input data/raw/your_ais.csv --output data/processed/ais_cleaned.csv
```

### 2. 处理环境数据

```bash
python scripts/process_env.py --input data/external/your_env.csv --output data/processed/env_processed.csv
```

或使用 Copernicus 下载后的 NetCDF：

```bash
python scripts/process_env.py --thetao-netcdf data/external/copernicus/thetao.nc --chl-netcdf data/external/copernicus/chl.nc --output data/processed/env_processed.csv
```

### 3. 构建特征

```bash
python scripts/build_features.py --ais data/processed/ais_cleaned.csv --env data/processed/env_processed.csv --output data/processed/vessel_features.csv
```

### 4. 生成报告

```bash
python scripts/generate_report.py --input data/processed/vessel_features.csv --output outputs/reports/voyage_report.md
```

## 当前脚本能力

- `ingest_ais.py`：可做 CSV 读取、核心字段校验、时间标准化、研究区裁剪、去重
- `convert_ais_tracks_json.py`：可将切片 AIS 轨迹 JSON 扁平化为标准 CSV
- `process_env.py`：可做环境 CSV 校验、字段标准化、研究区裁剪
- `build_features.py`：可生成首版船舶级特征表
- `generate_report.py`：可根据特征表生成面向演示的 Markdown 报告

## 当前边界

- 尚未接入真实 AIS API
- 尚未处理 NetCDF 原生环境数据
- 尚未实现地图图层输出
- 尚未实现前端展示
