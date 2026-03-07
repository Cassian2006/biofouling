# 部署运行手册

## 1. 当前推荐部署方式

当前项目已经整理成适合 Render 的两服务结构：

- `biofouling-api`
  运行 FastAPI，负责提供 `/api/...` 接口与评分逻辑。
- `biofouling-web`
  运行 Vue 3 + Vite 构建后的静态站点，负责展示总览页、单船页、区域页。

仓库根目录中的 `render.yaml` 已经描述了这两项服务。

## 2. Render 部署前需要准备的环境变量

### 后端服务

- `FRONTEND_ORIGIN`
  填前端站点的公开地址，例如 `https://biofouling-web.onrender.com`

### 前端服务

- `VITE_API_BASE_URL`
  填后端服务的公开地址，例如 `https://biofouling-api.onrender.com`

## 3. Render 部署顺序建议

1. 先部署后端服务 `biofouling-api`
2. 拿到后端公开地址
3. 把这个地址填入前端服务的 `VITE_API_BASE_URL`
4. 再部署前端服务 `biofouling-web`
5. 把前端公开地址回填到后端的 `FRONTEND_ORIGIN`
6. 重新触发一次后端部署，使跨域白名单生效

## 4. 本地开发方式

### 后端

```powershell
uvicorn backend.main:app --reload
```

默认地址：

- `http://127.0.0.1:8000`

### 前端

```powershell
cd frontend
npm install
npm run dev
```

默认地址：

- `http://127.0.0.1:5173`

本地开发时，前端会通过 Vite 代理把 `/api` 请求转发到本地 FastAPI。

## 5. 单体部署备用方案

如果后续希望简化部署，也可以只保留后端服务，把前端先在本地构建出 `frontend/dist`，然后让 FastAPI 直接托管构建产物。

当前代码已经支持：

- 如果 `frontend/dist` 存在，访问根路径会返回前端首页
- `/assets` 与 `/demo` 静态资源可由后端直接提供
- 前端路由刷新后会回退到 `index.html`

这个方案更适合想先快速合并成一个服务演示时使用，但当前默认建议仍然是前后端分开部署，后续维护更清晰。
