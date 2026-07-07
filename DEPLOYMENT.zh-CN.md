# Plane MCP Server 部署文档（自托管 Plane CE 适配版）

> 本文档适用于 fork 仓库 [sakurayun/plane-mcp-server](https://github.com/sakurayun/plane-mcp-server)，
> 已针对自托管 Plane Community Edition（fork：[sakurayun/plane](https://github.com/sakurayun/plane)）做了兼容改造。
> 最后更新：2026-07-07

---

## 1. 架构总览

```
┌──────────────┐   stdio / HTTP    ┌───────────────────┐   REST /api/v1   ┌──────────────────────┐
│  MCP 客户端   │ ◄──────────────► │  plane-mcp-server │ ◄──────────────► │  自托管 Plane CE      │
│ (Claude Code │                   │  (Python/FastMCP) │   X-Api-Key 认证  │  192.168.1.52:8090   │
│  Cursor 等)  │                   │  139 个工具        │                  │  (Docker Compose)    │
└──────────────┘                   └───────────────────┘                  └──────────────────────┘
```

- MCP 服务器本身**无状态**，只是把 Plane 的 REST API（`/api/v1`，`X-Api-Key` 认证）封装成 MCP 工具
- 本 fork 相对上游的改动：
  1. **CE 兼容回退**（`plane_mcp/compat.py`）：`*-lite` 端点 404 时自动回退到完整端点
  2. **`create_page` 支持 `parent_id`**：可创建嵌套子页面
- 配套的 plane fork 在 CE 公开 API 中补齐了 pages（含嵌套）、lite 系列、dependencies、work-item-types、features 等端点（见第 6 节兼容性矩阵）

## 2. 前置条件

| 项目 | 要求 |
|---|---|
| Plane 实例 | 自托管 CE，镜像 `ghcr.io/sakurayun/plane-*:preview`（含 API 补全），或 Plane Cloud |
| Python | 3.10+（推荐用 [uv](https://docs.astral.sh/uv/) 管理） |
| API Token | Plane 个人 API Token（见 2.1） |
| Workspace slug | 如 `yun_er`（浏览器地址栏 `/<slug>/` 部分） |

### 2.1 获取 API Token

方式一（推荐）：Plane 网页 → 头像 → **Settings → API tokens → Add API token**。

方式二（服务器上直接生成）：

```bash
docker exec plane-api-1 python manage.py shell -c "
from plane.db.models import User, APIToken
u = User.objects.get(email='<你的邮箱>')
t, _ = APIToken.objects.get_or_create(user=u, label='mcp-server')
print(t.token)"
```

Token 形如 `plane_api_xxxxxxxxxxxx`，**注意保密，不要提交进任何仓库**。

## 3. 部署方式

### 方式 A：本地 venv + stdio（当前采用，最适合 Claude Code / Cursor）

```bash
git clone https://github.com/sakurayun/plane-mcp-server.git
cd plane-mcp-server
uv venv .venv
uv pip install -e .
```

冒烟测试（Windows 下 venv 的 python 在 `.venv/Scripts/python.exe`，Linux/macOS 在 `.venv/bin/python`）：

```bash
PLANE_API_KEY=plane_api_xxx \
PLANE_WORKSPACE_SLUG=yun_er \
PLANE_BASE_URL=http://192.168.1.52:8090 \
.venv/bin/python -m plane_mcp stdio
# 启动后打印 FastMCP banner 即为正常，Ctrl+C 退出
```

### 方式 B：uvx 免安装运行（跑上游 PyPI 版，无 fork 补丁）

```bash
uvx plane-mcp-server stdio
```

> ⚠️ 这是上游发布版：没有 CE lite 回退和 parent_id 补丁。对接自托管 CE 请用方式 A 或 C。

### 方式 C：Docker（GHCR 自建镜像，适合常驻 HTTP 服务）

fork 的 CI 会自动构建镜像 `ghcr.io/sakurayun/plane-mcp-server:latest`（push 到 main 触发）。

```bash
# 国内服务器建议走 NJU 镜像源
docker pull ghcr.nju.edu.cn/sakurayun/plane-mcp-server:latest

# HTTP 模式常驻（端口 8211，header 认证端点 /http/api-key/mcp）
docker run -d --name plane-mcp --restart unless-stopped \
  -p 8211:8211 \
  -e PLANE_BASE_URL=http://192.168.1.52:8090 \
  ghcr.nju.edu.cn/sakurayun/plane-mcp-server:latest http
```

HTTP 模式下客户端通过请求头传凭据（每个用户可以用自己的 token）：

```
URL: http://<主机>:8211/http/api-key/mcp
Headers:
  x-api-key: plane_api_xxx
  x-workspace-slug: yun_er
```

> CE 没有 OAuth Provider，**不要**用 `/oauth/mcp` 端点；SSE 模式同理跳过。

## 4. 客户端配置

### 4.1 Claude Code（当前机器已配置）

一条命令（用户级，所有项目生效）：

```bash
claude mcp add plane --scope user \
  -e PLANE_API_KEY=plane_api_xxx \
  -e PLANE_WORKSPACE_SLUG=yun_er \
  -e PLANE_BASE_URL=http://192.168.1.52:8090 \
  -- "D:\研发\网络调试\plane-mcp-server\.venv\Scripts\python.exe" -m plane_mcp stdio
```

验证：`claude mcp list` 显示 `plane: ... - ✔ Connected`。

### 4.2 Claude Desktop / Cursor（JSON 配置）

```json
{
  "mcpServers": {
    "plane": {
      "command": "D:\\研发\\网络调试\\plane-mcp-server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "plane_mcp", "stdio"],
      "env": {
        "PLANE_API_KEY": "plane_api_xxx",
        "PLANE_WORKSPACE_SLUG": "yun_er",
        "PLANE_BASE_URL": "http://192.168.1.52:8090"
      }
    }
  }
}
```

### 4.3 环境变量一览

| 变量 | 必填 | 说明 |
|---|---|---|
| `PLANE_API_KEY` | stdio 必填 | 个人 API Token |
| `PLANE_WORKSPACE_SLUG` | stdio 必填 | 目标 workspace |
| `PLANE_BASE_URL` | 是 | 自托管填实例地址（不带 `/api`），默认 `https://api.plane.so` |
| `PLANE_INTERNAL_BASE_URL` | 否 | HTTP 模式下服务器间调用的内网地址 |
| `REDIS_HOST` / `REDIS_PORT` | 否 | HTTP 模式 token 存储（缺省内存） |

## 5. 升级流程

**升级 MCP 服务器**：

```bash
cd plane-mcp-server
git pull origin main
uv pip install -e .        # 依赖有变化时
# Claude Code 无需重新配置，下次会话自动生效
```

**升级 Plane 后端**（改了 plane fork 的代码后）：

```bash
git push origin preview     # 触发 GHCR 自动构建（.github/workflows/build-ghcr.yml）
# 等 Actions 绿灯后，在服务器上：
ssh root@192.168.1.52 "cd /opt/plane && docker compose pull && docker compose up -d"
```

**回归测试**（仓库根目录，需先填好脚本里的连接参数）：

```bash
.venv/bin/python test_ce_contract.py   # SDK 契约测试（32 项，覆盖全部 CE 补全端点）
.venv/bin/python test_pages.py         # MCP 页面嵌套 e2e
.venv/bin/python test_selfhost.py      # 基础工具回归
```

## 6. CE 兼容性矩阵

### ✅ 完整可用（139 个工具中的绝大部分）

项目、工作项（CRUD/搜索/归档/按标识符查询）、**页面（含 parent_id 嵌套子页面）**、周期、模块、
标签、状态、评论、链接、附件、活动、成员、intake（含 status 更新）、estimates、
内置依赖关系（blocking/blocked_by/start_before 等 6 方向）、work-item-types、
project features（开关 cycles/modules/pages/intakes 等）、workspace 级工作项列表与计数。

### ⚠️ 优雅降级

- `get_features`（workspace 级）：CE 返回全 false 的桩数据，依赖它的工具会提示"功能未启用"而非报错
- PQL 过滤参数：CE 忽略（返回未过滤结果）

### ❌ 不可用（CE 数据库无对应模型，EE/Cloud 专属）

worklogs（工时）、milestones、initiatives、customers、teamspaces、releases、
templates、自定义 roles、自定义 properties/options/values、页面挂载到工作项
（attach_page_to_work_item）。调用会返回 404/错误提示。

## 7. 故障排查

| 现象 | 排查 |
|---|---|
| 客户端显示未连接 | 手动跑 `python -m plane_mcp stdio` 看报错；常见是 env 没传到子进程 |
| `PLANE_API_KEY is not set` | stdio 模式凭据必须写在 MCP 客户端配置的 `env` 里（子进程不继承 shell 环境） |
| 工具调用 401 | Token 失效/拼错；重新生成 API Token |
| 工具调用 404 | 该功能属于 EE（见第 6 节）；或 Plane 后端不是补全版镜像（确认 `ghcr.io/sakurayun/plane-backend:preview`） |
| 工具调用 502 | Plane API 容器在重启中，等约 1 分钟：`docker logs plane-api-1` |
| 拉取 GHCR 镜像失败 | 国内直连 ghcr.io 会被重置，改用 `ghcr.nju.edu.cn` 前缀 |

## 8. 相关仓库与位置备忘

| 内容 | 位置 |
|---|---|
| MCP 服务器 fork | `github.com/sakurayun/plane-mcp-server`（本地 `D:\研发\网络调试\plane-mcp-server`） |
| Plane CE fork（API 补全） | `github.com/sakurayun/plane` preview 分支（本地 `D:\研发\网络调试\plane`） |
| Plane 部署 | 192.168.1.52 `/opt/plane`（Docker Compose，Web 端口 8090） |
| 服务器源码副本 | 192.168.1.52 `/opt/plane/source` |
| GHCR 镜像 | `ghcr.io/sakurayun/plane-{frontend,space,admin,live,backend,proxy}` 与 `plane-mcp-server` |
