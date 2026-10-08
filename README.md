# WMS 仓储物流管理系统

前后端分离的仓储管理系统（WMS），多仓集中管理，RBAC 权限，AI 扩展预留。

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 · JWT |
| 前端 | Vue 3 · TypeScript · Vite · Element Plus · Pinia · ECharts |
| 数据 | PostgreSQL 16 · Redis 7（可选，缺失时自动降级） |
| 部署 | 本地直跑 / Docker Compose |

## 功能模块

- **看板**：库存总量、今日出入库、7 天趋势图、库存预警
- **基础数据**：仓库 / 库区 / 库位（支持批量生成、编码扫码）/ 商品分类 / 商品（自动编码 SKU****）/ 供应商 / 客户
- **入库管理**：采购入库 / 退货入库 / 其他入库，草稿→执行（库存增加），一步执行模式
- **出库管理**：销售出库 / 领用出库 / 其他出库，行锁防超扣
- **库存管理**：库存查询、库位间移库、跨仓调拨（Redis 分布式锁）、不可变库存流水、上下限预警、Excel 导出
- **盘点管理**：按仓库/库区创建盘点单，快照账面数量 → 录入实盘 → 完成后自动调整差异
- **系统管理**：用户 / 角色 / 菜单（完整 RBAC），按钮级权限指令，按仓库的数据权限，操作日志
- **AI 预留**：`app/ai/` 模块含 LLMService 抽象接口与 `/api/v1/ai/chat` 骨架，库存流水数据完整规范，为后续 ChatBI / 需求预测打基础

## 本地开发启动

前置：Python 3.12+、Node 18+、PostgreSQL 16（Redis 可选）

```bash
# 1. 数据库：创建角色和库（一次性）
psql -U postgres -c "CREATE ROLE wms LOGIN PASSWORD 'wms123456';"
psql -U postgres -c "CREATE DATABASE wms OWNER wms;"

# 2. 后端（端口 8000）
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env        # 按需修改连接配置
python -m app.seed            # 建表 + 种子数据（admin/admin123、示例仓库 WH01）
python -m uvicorn app.main:app --port 8000 --reload

# 3. 前端（端口 5173，/api 代理到 8000）
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 ，默认账号 `admin / admin123`（超级管理员）。

## Docker 一键部署（轻量云服务器）

```bash
docker compose up -d --build
```

启动后访问 http://服务器IP （前端 80 端口，自动代理 API）。首次启动自动建表和种子数据。

## 关键设计

- **并发安全**：库存变动唯一入口 `services/inventory.apply_stock_change`，`SELECT ... FOR UPDATE` 行锁 + 条件更新防超扣；跨仓调拨加 Redis 锁（无 Redis 降级为事务保护）
- **流水不可变**：`inventory_transaction` 只插入不更新，记录变动前后数量，全程可追溯
- **单号规则**：`IN/OUT/TR/MV/ST + 日期 + 序号`，Redis INCR 保证唯一，降级时时间戳兜底
- **扫码支持**：扫枪即键盘输入，库位编码输入框回车即可定位，零驱动
- **数据权限**：用户可分配多个仓库，所有业务查询自动按授权仓库过滤；超管不受限

## 测试

```bash
cd backend
python scripts/smoke_test.py   # 全链路冒烟：登录→商品→入库→出库→超扣拦截→移库→盘点→看板
```

## 目录结构

```
warehouse/
├── backend/
│   ├── app/
│   │   ├── core/        # 配置/数据库/安全/依赖/缓存
│   │   ├── models/      # SQLAlchemy 模型（约 20 张表）
│   │   ├── schemas/     # Pydantic
│   │   ├── api/v1/      # auth/system/basic/order/inventory/transfer/stocktake/dashboard/export
│   │   ├── services/    # 库存核心逻辑
│   │   └── ai/          # AI 扩展预留（LLMService 抽象 + ChatBI 骨架）
│   ├── scripts/smoke_test.py
│   └── Dockerfile
├── frontend/
│   └── src/{api,stores,router,directives,layouts,views}
├── docker-compose.yml
└── README.md
```
