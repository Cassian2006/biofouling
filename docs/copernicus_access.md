# Copernicus 账号接入说明

## 当前状态

本机已安装官方 `copernicusmarine` Python 包，当前项目已新增脚本：

- [scripts/download_env_copernicus.py](/c:/Users/cai%20yuan%20qi/Desktop/biofouling/scripts/download_env_copernicus.py)

该脚本通过 Copernicus Marine 官方 API 下载研究区时间窗子集数据。

## 账号提供方式

不建议把账号密码直接写进仓库文件。

建议通过本地环境变量提供：

- `COPERNICUSMARINE_SERVICE_USERNAME`
- `COPERNICUSMARINE_SERVICE_PASSWORD`

PowerShell 示例：

```powershell
$env:COPERNICUSMARINE_SERVICE_USERNAME="your_username"
$env:COPERNICUSMARINE_SERVICE_PASSWORD="your_password"
```

设置后即可运行环境下载脚本。

## 运行方式

```powershell
python scripts/download_env_copernicus.py --job data/contracts/copernicus_env_job.template.json
```

## 时间对齐建议

当前 AIS 冒烟时间窗是：

- `2026-01-15T00:00:00Z`
- `2026-01-18T00:00:00Z`

如果后续发现环境产品对 2026 时间窗覆盖不理想，建议按下面顺序向前调整，而不是随意改：

1. 先整体平移到 `2025-12-15` 到 `2025-12-18`
2. 如果仍不理想，再平移到 `2025-01` 同长度窗口
3. 始终保持 AIS 与环境时间窗一致

## 原则

- 同一轮测试中，AIS 与环境数据必须使用同一时间窗
- 如果时间窗调整，优先整体平移，不要只改单边
- 第一阶段先以“能稳定下载并对齐”为优先，不追求特定季节
