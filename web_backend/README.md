# Web Backend

## 启动后端服务

```bash
# 激活环境
source ~/miniforge3/etc/profile.d/conda.sh
conda activate humanoid-retargeting

# 安装依赖 (如果需要)
pip install -r requirements.txt

# 启动服务
cd /path/to/humanoid-retargeting
python -m uvicorn web_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## API 文档

启动后访问: http://localhost:8000/docs

### 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/config/robots` | GET | 获取可用机器人列表 |
| `/api/config/{robot}/{gen}/configs` | GET | 获取配置列表 |
| `/api/config/{robot}/{gen}/{config}` | GET | 获取配置详情 |
| `/api/config/{robot}/{gen}/{config}` | POST | 保存配置 |
| `/api/model/mjcf/{robot}` | GET | 获取机器人 MJCF |
| `/api/model/retarget` | POST | 执行重定向 |
| `/api/model/motions/{gen}` | GET | 获取运动文件列表 |

---

# Web Frontend

## 前置要求

- Node.js 18+
- npm / yarn / pnpm

## 安装和运行

```bash
cd web_frontend
npm install
npm run dev
```

访问: http://localhost:5173

## 构建生产版本

```bash
npm run build
```

---

# 部署说明

## 开发模式

1. 后端: `python -m uvicorn web_backend.main:app --reload`
2. 前端: `npm run dev`

## 生产模式

1. 构建前端: `npm run build`
2. 配置 nginx 反向代理
