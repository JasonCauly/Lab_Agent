# Lab_Agent — 实验室智能预约管理系统

基于 FastAPI、Vue 3、MySQL 的实验室管理与预约项目。当前 AI 模块采用 LangChain + LangGraph，通过 SSE 逐步显示状态、工具过程和正文，支持知识库检索、实验室/设备资料查询、服务器日期与创建预约五个工具。预约工具复用登录身份和原业务校验，写入待审核申请；确认目前由提示词引导，服务端强制确认、幂等与完整联调仍待完善。

文档更新：2026-10-26。

**项目已基本结题。** 首页现整合欢迎信息、身份展示、系统功能介绍和角色快捷入口，与预约业务、知识问答及 SSE Agent 组成完整展示主线。两个首页统计数字仍为占位值；后续完善和真实环境验收见[结题说明](demo_1代码学习_复习笔记.md#project-closeout)。

[AI 与知识库入门教程](demo_1代码学习_复习笔记.md#20-ai-rag) · [预约自动过期与扫描](demo_1代码学习_复习笔记.md#reservation-expiry) · [AI 配置与验收](#ai-rag-setup)

[LangChain / LangGraph 与 SSE 教程](demo_1代码学习_复习笔记.md#agent-sse) · [工具执行路线图](#ai-tool-flow)

[学习与复习笔记](demo_1代码学习_复习笔记.md) · [预约事务与并发教程](demo_1代码学习_复习笔记.md#reservation-concurrency) · [预约查询、取消与审核教程](demo_1代码学习_复习笔记.md#18-reservation-workflow)

[项目运行与功能路线图](#runtime-flow) · [逐文件、逐函数执行讲解](demo_1代码学习_复习笔记.md#19-code-flow)

## 当前功能与进度

| 模块 | 当前实现 |
| --- | --- |
| 系统首页 | 欢迎与身份、三张功能介绍卡、AI 按钮；学生 3 个快捷入口，管理分支 4 个；统计数字尚未接入 |
| 用户与登录 | 注册、JWT 登录、个人信息与头像、修改密码、管理员用户增删改查 |
| 实验室与设备 | 资料管理、分页搜索、按实验室筛选设备、学生端卡片和详情浏览 |
| 预约提交 | 共用预约弹窗、日期和时段填写、实验室/设备状态检查、设备归属检查、同资源时段冲突检查 |
| 我的预约 | 查询本人预约、按状态筛选、分页、取消本人待审核预约 |
| 预约审核管理 | 管理员查询全部用户预约、查看预约人、通过或拒绝待审核预约；默认显示待审核 |
| 数据一致性 | 创建预约的事务锁与死锁重试、用户名数据库唯一约束及升级脚本、有预约历史的资源和用户禁止删除 |
| 表单和登录修补 | 设备新增重置、正整数容量、删除确认异常处理、JWT UTC 有效期、旧请求 401 防止误清新登录状态 |
| AI 智能助手 | POST /api/ai/chat/stream → LangChain / LangGraph → SSE；逐步显示状态、工具过程和正文；fetch 目前未配置超时/取消 |
| AI 资源查询 | list_open_labs 查询启用实验室；list_lab_equipments 查询指定实验室设备；复用既有 service，结果回传模型 |
| AI 预约与日期 | get_today 获取服务器日期；create_lab_reservation 使用当前登录用户创建待审核预约，提示词要求复述并确认 |
| 本地知识库 | search_lab_docs 调用 BGE/Chroma；只加载本地模型缓存，源码默认启动预热，最多检索 5 条并筛选前 2 条 |
| 过期扫描 | asyncio.to_thread 执行同步扫描，每轮完成后等待 60 秒；按结束时间将过期待审核记录转为 3，循环处理取消 |

**预约主要流程已接通。** 新记录为待审核（status=0）；本人可取消为 3，管理员可通过为 1 或拒绝为 2；后台扫描也会把已过期的待审核记录转为 3。当前仅允许操作待审核记录，取消会保留历史记录，已通过的预约不能再取消。状态 0、1 占用同资源时段，2、3 不占用；整间实验室与其设备仍分别检查冲突，设备 quantity 尚未用于按数量预约。

学习笔记现按 6 个部分、20 章组织：预约提交与并发见第 12 章，查询、取消、审核与自动过期见第 13 章，AI/RAG 与工具调用见第 14、15 章；各功能修补已归入所属章节。日期有效性、零时长、部分基础数据约束、旧会话失效和上传认证等仍需完善；审核与取消的并发状态更新也尚未保护。功能已写出不代表真实 MySQL 并发和浏览器完整验收已完成。

## 1. 技术栈

### 后端

| 技术 | 版本 / 说明 |
|---|---|
| Python | 3.10+，建议 3.11 |
| FastAPI | 0.115.13 |
| Uvicorn | 0.34.0 |
| SQLAlchemy | 2.0.41 |
| PyMySQL | 1.1.1 |
| Pydantic Settings | 2.7.1 |
| bcrypt | 5.0.0 |
| PyJWT | 2.13.0 |
| python-multipart | 0.0.32，文件上传表单解析 |
| cryptography | 50.0.1 |
| langchain-openai | 1.6.2，ChatOpenAI 模型调用与工具绑定 |
| langchain-core | 1.6.3，消息类型与 @tool |
| langgraph | 1.2.11，StateGraph、MessagesState 与 ToolNode |
| openai | 3.14.1，兼容模型接口的 SDK 依赖 |
| chromadb | 1.5.9，本地持久化向量库 |
| sentence-transformers | 6.0.1，加载 BAAI/bge-small-zh-v1.5 |
| MySQL | 建议 MySQL 8.x |

### 前端

| 技术 | 版本 / 说明 |
|---|---|
| Node.js | ^22.18.0 或 >=24.12.0 |
| npm | 与 Node.js 对应的版本 |
| Vue | 3.x |
| Vite | 8.x |
| Vue Router | 5.x |
| Element Plus | 2.x |
| Axios | 1.x |
| marked / DOMPurify | Markdown 转 HTML，再清理 HTML；版本以 package-lock.json 为准 |

建议使用项目提供的 `requirements.txt` 和 `package-lock.json` 安装依赖，以尽量保持运行环境一致。

## 2. 项目结构

```text
Lab_Agent/
├── .gitignore
│
├── backend/
│   ├── app/
│   │   ├── api/            # API 接口
│   │   ├── common/         # 公共响应与异常处理
│   │   ├── dependencies/   # 依赖注入、身份认证
│   │   ├── models/         # 数据库模型
│   │   ├── migrations/     # 现有库升级：用户名唯一索引
│   │   ├── schemas/        # Pydantic 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # FastAPI 入口
│   ├── .env                # 本地创建，不提交
│   ├── .venv/              # Python 虚拟环境
│   ├── uploads/            # 用户上传文件
│   ├── data/
│   │   ├── kb/            # 知识库 Markdown 原文
│   │   ├── config_global/ # agent_config.py：当前 Agent 提示词与五个工具，属于源码
│   │   └── chroma/        # 运行时生成的向量库与索引
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/            # API 请求封装
│   │   ├── assets/         # 静态资源
│   │   ├── components/     # 公共组件
│   │   ├── router/         # 路由配置
│   │   ├── utils/          # 工具函数
│   │   ├── views/          # 页面
│   │   ├── App.vue
│   │   └── main.js
│   ├── .env.development    # 本地开发环境配置
│   ├── node_modules/       # Node.js 依赖
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── demo_1代码学习_复习笔记.md
└── README.md
```

说明：`.env`、`.venv`、`node_modules` 等文件或目录不会包含在 GitHub 仓库中，需要在下载代码后自行配置或安装。具体目录以仓库当前版本为准。

当前工作区未包含早期 docs、原后端/登录回归及 frontend/tests/ai.test.js。教学文档保留此前的测试结果与 SSE 用例快照，恢复文件后才能重跑；它们不替代真实端到端验收。

## 3. 环境准备

项目支持在 Windows、Linux 等系统中运行。以下主要使用 Windows PowerShell 演示。

### 3.1 安装 Git

下载地址：

https://git-scm.com/downloads

安装完成后检查：

```powershell
git --version
```

### 3.2 安装 Python

推荐使用 Python 3.11。

下载地址：

https://www.python.org/downloads/

安装完成后检查：

```powershell
python --version
python -m pip --version
```

Windows 用户安装 Python 时，建议勾选 Add Python to PATH。

### 3.3 安装 Node.js

下载地址：

https://nodejs.org/

根据 `frontend/package.json`，需要 Node.js：

```text
^22.18.0 || >=24.12.0
```

安装完成后检查：

```powershell
node -v
npm -v
```

注意：Node.js 版本过低可能导致 Vite 无法运行。

### 3.4 安装 MySQL

建议安装 MySQL 8.x。

下载地址：

https://dev.mysql.com/downloads/mysql/

安装时记录以下信息：

- MySQL 用户名
- MySQL 密码
- MySQL 服务端口，默认 `3306`

安装完成后确认 MySQL 服务已启动。

可以使用 MySQL Workbench、命令行等工具管理数据库。

## 4. 下载项目

执行：

```powershell
git clone https://github.com/JasonCauly/Lab_Agent.git
```

进入项目目录：

```powershell
cd Lab_Agent
```

如果仓库是 Private，需要使用具有访问权限的 GitHub 账号完成身份验证。

如果已配置 GitHub SSH，也可以使用：

```bash
git clone git@github.com:JasonCauly/Lab_Agent.git
```

## 5. 配置 MySQL 数据库

### 5.1 创建数据库

打开 MySQL Workbench 或 MySQL 命令行，使用具有数据库管理权限的账号执行：

```sql
CREATE DATABASE IF NOT EXISTS lab_agent
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

查看数据库：

```sql
SHOW DATABASES;
```

### 5.2 创建项目专用数据库账号

建议不要长期使用 MySQL 的 root 账号运行项目。

以下仅为本地开发示例：

```sql
CREATE USER IF NOT EXISTS 'lab_agent'@'localhost'
IDENTIFIED BY 'ChangeMe123';

GRANT ALL PRIVILEGES ON lab_agent.*
TO 'lab_agent'@'localhost';
```

请将 `ChangeMe123` 替换为自己的密码。

确保 `DATABASE_URL` 中填写的用户名、密码、主机、端口和数据库名称与 MySQL 的实际配置一致。

如果使用 `127.0.0.1` 连接，需要确保 MySQL 用户具有该连接来源对应的访问权限。

### 5.3 数据库表初始化

当前后端代码中使用：

```python
Base.metadata.create_all(bind=engine)
```

因此，首次启动 FastAPI 时，SQLAlchemy 会尝试自动创建已经注册的数据库模型所对应的表。

目前包括：

- `users`：用户信息表
- `labs`：实验室信息表（旧版本名为 `lab`）
- `equipments`：设备表，通过 lab_id 关联实验室
- `reservation`：预约表，关联用户、实验室和可选设备

注意：

1. 必须先创建 MySQL 数据库。
2. MySQL 服务必须正常运行。
3. 后端使用的数据库账号必须具有建表权限。
4. `create_all()` 可以创建缺失的表，但不负责后续数据库结构迁移，也不会自动生成测试用户或业务数据。

新库的 users.username 会按当前模型创建唯一约束。MySQL 预约锁逻辑要求相关表使用 InnoDB。旧库请先阅读下一节，不能把 create_all() 当作升级工具。

### 5.4 已有数据库升级

升级前备份学习数据库，并暂停相关写入。当前有两项独立的结构变化：

1. **实验室表由 lab 改名为 labs。** 设备和预约的实验室外键现指向 labs.id。当前没有自动改名、搬迁旧数据和调整外键的脚本；需先核对实际表结构，在保留实验室 ID 和关联关系的前提下制定迁移。直接启动可能创建空 labs 表，但不会把旧 lab 数据搬过来，也不会改写已有 equipments 外键。下面的用户名脚本不处理这项迁移。
2. **users.username 增加唯一约束。** 旧 users 表需要执行专用升级脚本；已有重复用户名时脚本会停止，不会自动删除或合并用户。

先检查重复用户名：

```sql
SELECT username, COUNT(*) AS account_count
FROM users
GROUP BY username
HAVING COUNT(*) > 1;
```

确认目标数据库配置及数据后，在 backend 目录执行：

```powershell
.\.venv\Scripts\python.exe -m app.migrations.add_username_unique
```

脚本添加 uq_users_username 唯一索引；已存在用户名唯一约束时会跳过。若发现重复数据，先人工核实账号身份和历史预约归属，再处理数据并重试。完整说明见 [学习笔记第 3.6 节：用户名唯一索引升级](demo_1代码学习_复习笔记.md#username-migration)。本轮预约查询、取消和审核复用现有 reservation 表，无新增表字段；本轮文档验证没有对现有 MySQL 执行升级。

## 6. 配置 FastAPI 后端

### 6.1 进入 backend

在项目根目录执行：

```powershell
cd backend
```

### 6.2 创建 Python 虚拟环境

```powershell
python -m venv .venv
```

激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

激活成功后，终端会显示类似：

```text
(.venv) PS ...\Lab_Agent\backend>
```

如果 PowerShell 禁止运行激活脚本，可以直接使用：

```powershell
.\.venv\Scripts\python.exe -m pip --version
```

或者根据本机安全策略调整执行策略。

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 6.3 安装 Python 依赖

先升级 pip：

```powershell
python -m pip install --upgrade pip
```

安装项目依赖：

```powershell
python -m pip install -r requirements.txt
```

当前 requirements.txt 已包含 python-multipart 和 cryptography；按清单安装即可，无需再单独安装文件上传依赖。

检查依赖：

```powershell
python -m pip check
```

### 6.4 配置 backend/.env

由于环境变量可能包含数据库密码和 JWT 密钥，因此 `.env` 不会上传到 GitHub。

在 `backend` 文件夹中创建 `.env`：

```text
backend/.env
```

参考内容：

```dotenv
# MySQL 数据库连接
DATABASE_URL=mysql+pymysql://lab_agent:ChangeMe123@localhost:3306/lab_agent?charset=utf8mb4

# JWT 配置
JWT_SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET_KEY
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256

# 大模型接口：请替换为所用服务的实际值
LLM_API_KEY=YOUR_LLM_API_KEY
LLM_MODEL=YOUR_CHAT_MODEL_ID
LLM_BASE_URL=https://YOUR_PROVIDER_HOST/v1

# 可选：源码默认 true；false 表示跳过启动预热
KB_WARMUP_ON_STARTUP=true
```

参数说明：

| 参数 | 含义 | 是否必需 |
|---|---|---|
| DATABASE_URL | SQLAlchemy 数据库连接字符串 | 是 |
| JWT_SECRET_KEY | JWT 签名密钥 | 是 |
| JWT_EXPIRE_HOURS | Token 有效时间，单位小时 | 否，默认 24 |
| JWT_ALGORITHM | JWT 签名算法 | 否，默认 HS256 |
| LLM_API_KEY | 大模型接口密钥，仅保存在后端 | 是 |
| LLM_MODEL | 服务端支持的聊天模型标识 | 是 |
| LLM_BASE_URL | 兼容 Chat Completions 的服务基础地址 | 是 |
| KB_WARMUP_ON_STARTUP | 是否等待知识库预热后再启动；仅加载本地缓存 | 否，源码默认 true，可通过环境配置覆盖 |

当前 Settings 在导入时校验配置，这三个 LLM 字段没有默认值，即使暂时不打开 AI 页面也必须配置。示例域名及模型 ID 是占位符，不能直接用于请求。向量模型名称在 kb_service.py 中设置，与 LLM_MODEL 是两个独立配置。

其中数据库连接字符串格式为：

```text
mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
```

请根据本机 MySQL 配置修改。

如果密码包含 `@`、`#`、`/`、`:` 等 URL 特殊字符，需要对连接字符串中的密码部分进行 URL 编码。

JWT 密钥不要使用公开的示例值。可以使用 Python 生成随机密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

将生成的随机字符串填入 `JWT_SECRET_KEY`。

### 6.5 启动后端

确保当前目录为：

```text
Lab_Agent/backend
```

执行：

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

正常情况下会看到：

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete.
```

访问后端根路径：

http://127.0.0.1:8000/

预期返回：

```json
{
  "message": "Hello, World!"
}
```

FastAPI 自动生成的接口文档：

http://127.0.0.1:8000/docs

OpenAPI 文档：

http://127.0.0.1:8000/openapi.json

注意：`--reload` 适用于本地开发环境，不建议直接用于生产环境。

## 7. 配置 Vue 前端

前端需要在新的终端窗口中启动。后端服务应保持运行。

### 7.1 进入 frontend

从项目根目录执行：

```powershell
cd frontend
```

### 7.2 安装 Node.js 依赖

项目已经包含 `package-lock.json`，建议使用：

```powershell
npm ci
```

如果 `package.json` 和锁文件不一致，或者 `npm ci` 无法正常执行，可以使用：

```powershell
npm install
```

注意，`npm install` 可能更新 `package-lock.json`。

当前锁文件通过 Element Plus 的依赖包含 @element-plus/icons-vue，先按锁文件执行 npm ci。源码直接引用了该包，但 package.json 尚未把它列为直接依赖；这是后续依赖整理项，不需要每次启动都额外安装。

PowerShell 若限制 npm.ps1，可使用 npm.cmd ci、npm.cmd run dev 等对应命令。

### 7.3 配置前端环境变量

在 `frontend` 文件夹中创建：

```text
frontend/.env.development
```

建议内容：

```dotenv
VITE_API_BASE_URL=
```

这里特意留空，是因为当前项目的 API 请求使用 `/api/...`，并且 Vite 已经配置代理：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true
    },
    '/uploads': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true
    }
  }
}
```

因此浏览器访问：

```text
http://localhost:5173/api/auth/login
```

在开发环境中会通过 Vite 代理转发到：

```text
http://127.0.0.1:8000/api/auth/login
```

无需额外编写代理服务器。

如果不使用 Vite 代理，也可以根据实际部署方式配置完整后端 URL，并正确配置跨域。

注意：`VITE_` 前缀的变量会暴露给前端代码，不能在里面保存 JWT 私钥、数据库密码或其他服务端机密信息。

### 7.4 启动前端

```powershell
npm run dev
```

正常情况下会出现类似：

```text
VITE ready

Local: http://localhost:5173/
```

在浏览器中打开：

http://localhost:5173/

如果端口 `5173` 被占用，Vite 可能尝试其他端口。此时需要同时检查后端 CORS 配置是否允许新的前端地址。

## 8. 首次运行与功能验证

建议按以下顺序完成：

1. 启动 MySQL 服务。
2. 确认 `lab_agent` 数据库已经创建。
3. 配置 `backend/.env`。
4. 启动 FastAPI 后端。
5. 打开 `/docs`，确认 API 文档正常。
6. 配置 `frontend/.env.development`。
7. 安装前端依赖并启动 Vite。
8. 在浏览器中打开前端页面。
9. 注册测试用户并进行登录验证。

### 8.1 验证用户注册

当前后端提供：

```http
POST /api/auth/register
```

请求体示例：

```json
{
  "username": "test_user",
  "password": "ReplaceWithAStrongPassword",
  "name": "测试用户",
  "email": "test@example.com"
}
```

可以在：

http://127.0.0.1:8000/docs

中使用 Swagger UI 发送测试请求。

注册成功后，数据库应产生新的用户记录。

当前注册逻辑默认创建 `student` 角色。

### 8.2 验证用户登录

当前后端提供：

```http
POST /api/auth/login
```

请求体：

```json
{
  "username": "test_user",
  "password": "ReplaceWithAStrongPassword"
}
```

使用刚刚注册的账号密码登录。

验证成功后，后端会生成 JWT Token。

前端后续受保护的请求通过：

```http
Authorization: Bearer <token>
```

进行身份认证。

### 8.3 其他主要接口

| 接口 | 方法 | 作用 |
|---|---|---|
| `/api/auth/register` | POST | 用户注册 |
| `/api/auth/login` | POST | 用户登录 |
| `/api/user/me` | GET | 获取当前用户信息 |
| `/api/user/me` | PUT | 更新个人信息 |
| `/api/user/password` | PUT | 修改密码 |
| `/api/user/list` | GET | 查询用户列表 |
| `/api/user` | POST | 创建用户 |
| `/api/user/{user_id}` | PUT | 更新指定用户 |
| `/api/user/{user_id}` | DELETE | 删除指定用户 |
| `/api/lab/list` | GET | 分页查询实验室 |
| `/api/lab/{lab_id}` | GET | 查询实验室详情 |
| `/api/lab` | POST | 新增实验室 |
| `/api/lab/{lab_id}` | PUT / DELETE | 修改 / 删除实验室 |
| `/api/equipment/list` | GET | 查询设备，可按 lab_id 筛选 |
| `/api/equipment` | POST | 新增设备 |
| `/api/equipment/{equipment_id}` | PUT / DELETE | 修改 / 删除设备 |
| `/api/reservation` | POST | 提交实验室或设备预约 |
| `/api/reservation/list` | GET | 分页查询；普通用户仅本人，管理员全部；支持 status 筛选 |
| `/api/reservation/{reservation_id}/cancel` | PUT | 取消本人待审核预约，不需要请求体 |
| `/api/reservation/{reservation_id}/audit` | PUT | 管理员审核待审核预约；请求体 status=1 通过、2 拒绝 |
| `/api/files/upload` | POST | 文件上传 |

用户管理和资源写入接口要求管理员；资源查询和预约提交要求有效登录。当前文件上传接口尚未增加登录依赖，不能视为已有统一认证保护。

预约审核由后端 `get_current_admin` 检查管理员身份；取消接口同时检查记录归属和待审核状态，管理员也不能通过取消接口取消他人的记录。前端隐藏菜单和按钮不替代这些检查。

具体参数和响应模型请以 FastAPI 的 `/docs` 为准。

### 8.4 文件上传目录

当前项目默认将文件保存至：

```text
backend/uploads/
```

并通过：

```text
http://127.0.0.1:8000/uploads/文件名
```

访问已上传文件。

配置模块会在目录不存在时尝试创建它。

默认单文件大小限制为 100MB，允许的文件扩展名在 `backend/app/config.py` 中定义。

该目录不应直接提交到 GitHub。

### 8.5 申请、查询、取消与审核预约

学生在“实验室列表”的卡片上预约实验室，或进入设备列表预约指定设备。三个入口共用 ReserveDialog.vue，提交到 POST /api/reservation。

请求示例（ID 需替换为实际资源，日期和时段需符合实验室开放安排）：

```json
{
  "lab_id": 8,
  "equipment_id": null,
  "date": "2099-10-20",
  "start_time": "09:00",
  "end_time": "10:00",
  "remark": "课程实验"
}
```

equipment_id 为 null 表示预约整间实验室；填写设备 ID 表示预约该设备，设备必须属于所选实验室。预约人由后端从 token 对应的当前用户取得，请求体不提供 user_id。

成功返回 code=200、data=null，并保存 status=0 的待审核记录；此处不返回预约详情。状态 0、1 参与冲突判断，状态 2、3 不占用时段；相邻且不重叠的时段可以提交。

两个新增页面：

| 角色菜单 | 页面路径 | 默认查询 | 可以执行的操作 |
| --- | --- | --- | --- |
| 普通用户：我的预约 | `/manager/myreservation` | 本人全部状态 | 筛选、翻页、取消本人待审核预约 |
| 管理员：预约审核管理 | `/manager/auditreservation` | 全部用户的待审核预约 | 筛选、翻页、通过或拒绝待审核预约 |

两个页面共用列表接口，例如：

```http
GET /api/reservation/list?page=1&page_size=10&status=0
```

省略 status 表示不按状态筛选，传 0 表示只查待审核。后端按当前登录用户决定数据范围，不接收前端指定的 user_id。列表成功返回 `data: { list: [...], total: 数量 }`；每行含实验室名、可选设备名、预约人名、日期、时段、备注和状态。查询到的名称来自当前关联资料。

取消预约（把 42 换成实际 ID）：

```http
PUT /api/reservation/42/cancel
```

管理员审核：

```http
PUT /api/reservation/42/audit
Content-Type: application/json

{"status": 1}
```

将 status 改为 2 表示拒绝。取消和审核成功均返回 code=200、data=null，页面随后重新查询列表。管理员默认筛选待审核，因此审核成功的行会从当前列表消失，切换状态可再查看；记录没有被删除。

建议准备学生 A、学生 B、管理员三个学习账号，依次检查：

1. A 提交实验室及设备预约，在“我的预约”看到待审核记录；B 的列表看不到 A 的记录。
2. A 在确认框关闭时不发出取消请求；确认取消后状态变为已取消，同一资源同一时段可重新申请。
3. 管理员通过一条待审核记录；A 刷新后看到已通过，取消按钮消失，同资源重叠时段仍被阻止。
4. 管理员拒绝另一条记录；A 刷新后看到已拒绝，原时段可以重新申请。
5. 直接调用接口验证：普通用户不能审核，不能取消别人的记录；非待审核记录不能再次审核或取消。
6. 验证状态 0 筛选、清空筛选、超过一页的数据，以及审核、取消同时发生的情况。

以上是待执行的浏览器与联调清单，不是本轮已经全部通过的验收结果。当前两个页面的 pageSize 尚未映射为后端 page_size，默认都为 10 时不易发现；loading 未设为 true，Search 图标变量也未导入。具体原因和建议改法见学习笔记第 13 章。

冲突和部分删除限制使用业务 code=409。当前统一业务异常响应仍为 HTTP 200，客户端需要读取 JSON 中的 code；参数校验错误使用 HTTP 422。

### 8.6 准备学习环境的管理员

项目没有内置默认管理员账号或密码，普通注册创建 student。可先注册一个专用于学习管理的账号，由数据库维护者确认账号后执行：

```sql
UPDATE users
SET role = 'admin'
WHERE username = 'YOUR_ADMIN_USERNAME';
```

把占位符替换为自己刚注册的唯一账号，再重新登录，让前端用户信息和菜单更新。随后创建实验室（容量必须大于 0）和设备，再用学生账号验证预约。

### 8.7 回归检查与当前验证范围

后端在 backend 目录可先检查 Python 语法（不等于业务测试）：

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
```

前端在 frontend 目录运行：

```powershell
npm.cmd run build
```

2026-10-21 本轮检查：后端 Python 语法检查通过；提取实际模型和业务函数，在内存 SQLite 上完成查询范围、分页、状态转换、取消/拒绝后重新预约等检查，并静态核对接口身份依赖，共 33 个断言通过。前端提取两个实际页面的函数，模拟 API 与确认框，完成 18 组场景检查；其中也确认了 pageSize、loading 和 Search 的现状。前端构建通过，仍有包体积提示。

这些是本轮临时隔离检查，没有新增为仓库内的测试文件；未连接现有 MySQL。早期的 19 项后端与 6 项登录测试是历史结果，当前工作区缺少对应测试文件。虽然 package.json 仍有 test 脚本，也不能把发现零个测试当成这 6 项重新通过。

真实 MySQL/InnoDB 并发、旧库迁移及浏览器完整流程仍待验收。创建预约的事务保护没有自动扩展到新加的取消与审核函数；同时处理同一条待审核记录时仍可能覆盖状态。完整解释与验收表见 [第 13 章](demo_1代码学习_复习笔记.md#18-reservation-workflow)。

## 9. 常见问题

### 9.1 npm run dev 提示找不到 vite

错误示例：

```text
'vite' 不是内部或外部命令
```

通常是因为下载 GitHub 代码后，`node_modules` 尚未安装。

解决方法：

```powershell
cd frontend
npm ci
npm run dev
```

如果仍然失败，请检查 Node.js 版本以及 `npm ls vite` 的输出。

### 9.2 找不到 @element-plus/icons-vue

错误示例：

```text
Failed to resolve import "@element-plus/icons-vue"
```

执行：

```powershell
npm install @element-plus/icons-vue
```

并确认依赖已经写入 `package.json`。

### 9.3 Python 提示 ModuleNotFoundError

首先确认已经进入正确的 Python 虚拟环境：

```powershell
python -c "import sys; print(sys.executable)"
```

然后安装依赖：

```powershell
python -m pip install -r requirements.txt
```

如果提示缺少 `multipart`：

```powershell
python -m pip install python-multipart
```

### 9.4 数据库连接失败

常见错误：

```text
pymysql.err.OperationalError
```

检查：

- MySQL 是否已经启动。
- `DATABASE_URL` 中的用户名和密码是否正确。
- 数据库是否已经创建。
- MySQL 端口是否为 `3306`。
- 用户是否具有访问数据库和建表的权限。
- 数据库密码中的特殊字符是否正确编码。

Windows 可以检查端口：

```powershell
Test-NetConnection 127.0.0.1 -Port 3306
```

### 9.5 缺少 DATABASE_URL、JWT_SECRET_KEY 或 LLM 配置

2026-10-23 更新：当前还必须提供 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL，完整示例见第 6.4 节。缺失字段会在 Settings() 初始化时阻止应用启动。

如果 FastAPI 启动时出现 Pydantic 配置验证错误，请检查：

```text
backend/.env
```

确认：

```dotenv
DATABASE_URL=...
JWT_SECRET_KEY=...
```

都已填写。

注意：环境变量名称必须与 `backend/app/config.py` 中定义的一致。

### 9.6 前端出现 Network Error

检查后端是否已启动：

http://127.0.0.1:8000/

检查前端开发服务器是否运行，以及 `VITE_API_BASE_URL` 与 Vite 代理配置是否正确。

如果修改了 `.env.development` 或 Vite 配置，请重新启动前端：

```powershell
npm run dev
```

### 9.7 接口返回 401

可能原因：

- 用户尚未登录。
- JWT Token 已过期或无效。
- 请求没有携带 Authorization 头。
- 修改了 `JWT_SECRET_KEY`，导致旧 Token 失效。

当前用户没有管理员权限通常对应业务 code=403；账号禁用等情况也可能返回 HTTP 403，应结合响应内容区分。

可以重新登录并检查浏览器开发者工具中的 Network 请求。

### 9.8 PowerShell 无法激活 .venv

可以使用虚拟环境的 Python 解释器直接执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

这样无需先激活虚拟环境。

## 10. GitHub 更新与维护

开发者修改代码后，在项目根目录执行：

```bash
git status
git add .
git diff --cached --stat
git commit -m "Update project"
git push
```

推荐提交的文件：

- Python 源代码
- Vue 前端源代码
- `requirements.txt`
- `package.json`
- `package-lock.json`
- `.gitignore`
- `README.md`
- 不包含真实密钥的环境配置示例

不应提交：

- `.env`
- `.env.development`
- `.venv/`
- `node_modules/`
- 日志文件
- 上传文件
- 本地数据库文件
- API Key、密码和其他敏感数据

如果增加新的 Python 依赖，请同步维护 `requirements.txt`。

如果安装新的前端依赖，请提交修改后的 `package.json` 和 `package-lock.json`。

## 11. 推荐增加环境变量模板文件

为方便其他开发者复现，建议仓库维护者额外创建两个不包含真实凭证的模板文件。

### backend/.env.example

```dotenv
DATABASE_URL=mysql+pymysql://lab_agent:YOUR_PASSWORD@localhost:3306/lab_agent?charset=utf8mb4
JWT_SECRET_KEY=REPLACE_WITH_YOUR_RANDOM_SECRET
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256
LLM_API_KEY=YOUR_LLM_API_KEY
LLM_MODEL=YOUR_CHAT_MODEL_ID
LLM_BASE_URL=https://YOUR_PROVIDER_HOST/v1

# 可选：源码默认 true；false 表示跳过启动预热
KB_WARMUP_ON_STARTUP=true
```

### frontend/.env.example

```dotenv
VITE_API_BASE_URL=
```

这两个示例文件可以上传到 GitHub。

当前仓库尚未提供这两个模板。维护者添加模板后，Windows 用户才可以执行以下复制命令；目前请按第 6.4、7.3 节手动创建配置：

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.development
```

然后填写本地数据库密码、随机 JWT 密钥等配置。

真实 `.env` 文件仍然需要通过 `.gitignore` 排除。

## 12. Windows 快速启动参考

初次下载项目后：

**后端终端：**

```powershell
cd Lab_Agent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# 配置好 backend/.env，确保 MySQL 已启动

python -m uvicorn app.main:app --reload
```

**前端终端：**

```powershell
cd Lab_Agent\frontend
npm ci

# 配置好 frontend/.env.development

npm run dev
```

安装和配置完成后，以后正常启动项目只需要：

**后端：**

```powershell
cd Lab_Agent\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

**前端：**

```powershell
cd Lab_Agent\frontend
npm run dev
```

确保 MySQL 服务保持运行。

## 13. 安全与部署说明

本项目当前以本地开发与功能验证为主。

正式部署前建议：

- 使用独立、低权限的 MySQL 数据库账号。
- 使用足够随机的 JWT 密钥，并妥善管理。
- 禁止将真实 `.env` 文件提交到 GitHub。
- 配置 HTTPS 和合适的反向代理。
- 为生产环境配置明确的 CORS 来源。
- 对文件上传增加完善的安全校验。
- 使用正式的数据库迁移机制。
- 对数据库和上传目录进行定期备份。
- 生产环境不要直接使用 Vite 开发服务器或 Uvicorn 的 `--reload` 模式。

如果真实密码或密钥曾经被提交到 Git 历史，仅删除当前文件并不代表历史中的凭证已经失效，应及时更换。

## 14. 项目地址

GitHub：

https://github.com/JasonCauly/Lab_Agent

预约主要业务与 LangChain / LangGraph 五工具 Agent 已写出，包括真实创建待审核预约。后续重点是强制确认、幂等与结果追踪、预约状态并发保护、知识规则校准及真实模型/浏览器验收。当前讲解见[框架 Agent 教程](demo_1代码学习_复习笔记.md#langchain-langgraph-agent)。

<a id="runtime-flow"></a>

## 15. 项目运行与功能路线图

下面按当前源码说明实际调用关系。图中前端 `views/`、`api/`、`utils/` 等路径相对 `frontend/src/`；后端路径相对 `backend/app/`。文件之间的箭头表示函数调用、数据传递或请求，不表示每一步都会切换网页。详细代码与传参解释见 [教学笔记第 16 章](demo_1代码学习_复习笔记.md#19-code-flow)。

### 15.1 启动与一次请求的总路线

```mermaid
flowchart TD
    subgraph Frontend[前端启动与页面]
        F0["npm run dev → Vite"] --> F1["index.html → src/main.js"]
        F1 --> F2["注册 router、Element Plus；挂载 App.vue"]
        F2 --> F3["router/index.js 匹配地址与登录守卫"]
        F3 --> F4["Layout.vue / router-view → 具体页面"]
    end
    subgraph Backend[后端启动与路由准备]
        B0["uvicorn app.main:app → main.py"] --> B1["导入配置、数据库、模型、路由"]
        B1 --> B2["config.py → settings；database.py → engine / SessionLocal"]
        B1 --> B3["模型注册 → create_all；include_router；异常处理与静态目录"]
        B3 --> BW["lifespan：按开关等待本地知识库预热，再启动扫描"]
    end
    F4 --> E["页面事件或 onMounted → 页面函数"]
    E --> A["前端 api/*.js：构造 method、url、params/data"]
    A --> R["utils/request.js：添加 token，发送 HTTP"]
    R --> P["开发环境 vite.config.js：/api 代理"]
    P --> B4["FastAPI 按 method + path 匹配已注册接口"]
    B3 -.准备路由.-> B4
    B4 --> B5["参数模型校验；按接口声明解析身份和数据库依赖"]
    B5 --> B6["api/*.py → services/*_service.py"]
    B6 --> DB[(MySQL)]
    DB --> OUT["返回数据 → Response.success；失败由异常处理器生成响应"]
    OUT --> RI["request.js 响应拦截器 → 返回正文或拒绝 Promise"]
    RI --> UI["页面更新 ref / reactive → Vue 更新界面"]
```

登录、注册不要求先登录；上传目前直接在 `api/files.py` 写磁盘；获取本人信息直接返回认证依赖取得的用户，并非所有接口都经过 service。main.py 中的初始化也不是每次请求重新执行。

### 15.2 管理员点击“通过”：精确调用路线

逐步代码解释见[审核通过的十二步](demo_1代码学习_复习笔记.md#19-audit-flow)。

```mermaid
sequenceDiagram
    actor Admin as 管理员
    participant View as views/AuditReservation.vue
    participant API as 前端 api/reservation.js
    participant Req as utils/request.js
    participant Route as 后端 api/reservation.py
    participant Service as services/reservation_service.py
    participant DB as MySQL reservation 表
    Admin->>View: 点击 @click="handleAudit(row, 1)"
    View->>View: handleAudit：等待确认框确认
    View->>API: auditReservationApi(row.id, 1)
    API->>Req: request：PUT，URL 中的 ID，data={status:1}
    Req->>Route: 经开发代理发送 PUT /api/reservation/{id}/audit
    Note over Route: AuditReservationRequest；get_current_admin；get_db
    Route->>Service: audit_reservation(db, reservation_id, status=1)
    Service->>DB: 查记录 → 要求原 status=0 → 更新 status=1 → commit
    Service-->>Route: 正常返回
    Route-->>Req: Response.success() → code=200, data=null
    Req-->>View: 拦截器返回响应正文，await 继续执行
    View->>View: 提示成功 → await load()
    View->>API: getReservationPageList(params)
    API->>Req: GET /api/reservation/list
    Req->>Route: 再次查询，默认 status=0
    Route->>Service: get_reservation_page_list(...)
    Service->>DB: 按角色、状态和分页查询，组装名称
    DB-->>Service: 查询结果
    Service-->>Route: PageResponse(list, total)
    Route-->>Req: Response.success(data=分页结果)
    Req-->>View: res.data.list / res.data.total
    View->>View: 更新 tableData、total；已通过行退出待审核列表
```

定位顺序：[按钮与 handleAudit](frontend/src/views/AuditReservation.vue) → [auditReservationApi](frontend/src/api/reservation.js) → [请求与响应拦截器](frontend/src/utils/request.js) → [后端 audit 接口](backend/app/api/reservation.py) → [管理员依赖](backend/app/dependencies/auth.py) → [audit_reservation 业务函数](backend/app/services/reservation_service.py)。通过传 1，拒绝传 2；均不切换页面，成功后会另发一次 GET 刷新列表。取消与审核的并发边界见第 8.7 节和教学笔记第 13.22 节。

### 15.3 账号与个人资料路线

```mermaid
flowchart LR
    R["Register.vue：register"] --> R1["api/auth.js：registerApi<br/>POST /api/auth/register"]
    R1 --> R2["api/auth.py：register<br/>auth_service.register → hash_password → users"]
    R2 --> R3["成功返回 → router.push('/login')"]
    L["Login.vue：login"] --> L1["api/auth.js：loginApi<br/>POST /api/auth/login"]
    L1 --> L2["api/auth.py：login<br/>auth_service.login → 校验密码 → 生成 JWT"]
    L2 --> L3["saveLoginData → token / 用户信息<br/>router.replace('/manager/home')"]
    P["Profile.vue：loadUserInfo / handleSubmit"] --> P1["api/user.js：getUserInfo / updateUserInfo<br/>GET / PUT /api/user/me"]
    P1 --> P2["api/user.py：get_user_info / update_user_info<br/>查询用认证用户；修改调用 user_service.update_user_info"]
    P2 --> P3["查询填 form；保存后 updateUser<br/>Layout / Home 读取共享 userInfo"]
    W["Password.vue：handleSubmit"] --> W1["api/user.js：updatePassword<br/>PUT /api/user/password"]
    W1 --> W2["api/user.py → user_service.update_password<br/>验证旧密码、保存新哈希"]
    W2 --> W3["成功 → 前端 logout → 登录页"]
```

普通退出登录：`Layout.vue.handleCommand('logout') → utils/auth.js.logout → 清理 localStorage → router.push('/login')`，当前没有后端登出接口。修改密码后的前端退出也不代表已建立服务端旧 token 撤销机制。

### 15.4 用户、实验室与设备管理路线

三个管理页面都采用“列表 → 打开表单 → 保存或删除 → 成功后重新查询”的方式：

```mermaid
flowchart TD
    ENTER["User.vue / Lab.vue / Equipment.vue"] --> Q["onMounted / handleSearch / 翻页 → load"]
    Q --> QAPI["getUserPageList / getLabPageList / getEquipmentPageList"]
    ENTER --> OPEN["handleCreate 重置表单；handleEdit(row) 回填表单"]
    OPEN --> SAVE["表单提交 → handleSave → 按 form.id 判断新增或修改"]
    SAVE --> WRITE["create*Api：POST；update*Api：PUT"]
    ENTER --> DEL["handleDelete(row) → 确认框 → delete*Api：DELETE"]
    QAPI --> HTTP["前端 api/user.js、lab.js、equipment.js → request.js"]
    WRITE --> HTTP
    DEL --> HTTP
    HTTP --> ROUTE["后端 api/user.py、lab.py、equipment.py：对应路由函数"]
    ROUTE --> SERVICE["对应 *_service.py：查询 / 创建 / 修改 / 关联检查后删除"]
    SERVICE --> DB[(users / labs / equipments)]
    DB --> BACK["Response → request.js → 页面"]
    BACK --> DONE["查询：填 tableData / total<br/>写入成功：关闭表单或提示 → load 再查询"]
```

| 模块 | 前端 API 文件 / 后端 API 文件 | service 的主要函数 |
| --- | --- | --- |
| 用户 | `frontend/src/api/user.js` / `backend/app/api/user.py` | `user_service.py`：get_user_page_list、create_user、update_user、delete_user |
| 实验室 | `frontend/src/api/lab.js` / `backend/app/api/lab.py` | `lab_service.py`：get_lab_page_list、create_lab、update_lab、delete_lab |
| 设备 | `frontend/src/api/equipment.js` / `backend/app/api/equipment.py` | `equipment_service.py`：get_equipment_page_list、create_equipment、update_equipment、delete_equipment |

点击“编辑”先回填当前行，不另发详情请求；点击表单“保存”才写后端。用户管理接口要求管理员，实验室/设备查询只要求登录，写入要求管理员。

### 15.5 学生浏览、申请、查询与取消路线

```mermaid
flowchart TD
    LAB["LabList.vue：onMounted → load<br/>getLabPageList → GET /api/lab/list"] --> CARDS["lab_service.get_lab_page_list → 卡片列表"]
    CARDS --> DETAIL["handelViewEquipment(item)<br/>router.push：/manager/labequipment?lab_id=..."]
    DETAIL --> PAGE["LabEquipment.vue：读取 route.query.lab_id"]
    PAGE --> INFO["loadLab → api/lab.js.getLab<br/>GET /api/lab/{id} → lab_service.get_lab"]
    PAGE --> EQUIP["loadEquipment → getEquipmentPageList<br/>GET /api/equipment/list → 按 lab_id 查询"]
    CARDS --> OPEN["handelReserve；或详情页 hanldeReserveLab / hanldeReserveEquipment"]
    INFO --> OPEN
    EQUIP --> OPEN
    OPEN --> DIALOG["props / v-model → ReserveDialog.vue<br/>handleOpen 重置；handleSubmit 提交"]
    DIALOG --> CREATE["createReservationApi → POST /api/reservation<br/>api.create_reservation → service.create_reservation → _create_reservation"]
    CREATE --> PENDING["校验与冲突检查 → reservation 新增 status=0<br/>成功提示 → emit 关闭弹窗"]
    PENDING -.用户另行进入.-> MINE["MyReservation.vue：load → getReservationPageList<br/>GET /api/reservation/list → 本人记录"]
    MINE --> CANCEL["handleCancel(row) → 确认<br/>cancelReservationApi → PUT /api/reservation/{id}/cancel"]
    CANCEL --> UPDATE["api.cancel_reservation → service.cancel_reservation<br/>检查本人及 status=0 → 改为 3 → commit"]
    UPDATE --> RELOAD["成功返回 → load → 重新显示列表"]
```

图中 `handelViewEquipment`、`handelReserve`、`hanldeReserveLab`、`hanldeReserveEquipment` 保留源码的实际拼写，便于搜索。预约成功当前只关闭弹窗，不自动跳到“我的预约”。

### 15.6 图片上传与读取路线

```mermaid
flowchart TD
    PICK["Profile.vue / Lab.vue / Equipment.vue<br/>选择图片 → beforeAvatarUpload → handleFileUpload"]
    PICK --> FORM["api/files.js：uploadFileApi<br/>FormData 的 file 字段"]
    FORM --> UP["request.js → POST /api/files/upload"]
    UP --> DISK["api/files.py：upload<br/>检查文件 → 写入 backend/uploads"]
    DISK --> URL["FileResponse.url → /uploads/文件名"]
    URL --> LOCAL["页面写 form.avatar 或 form.img → 显示预览"]
    LOCAL --> SAVE["另点保存 → 用户 / 实验室 / 设备更新接口<br/>数据库保存图片 URL"]
    LOCAL --> IMG["浏览器 img 请求 /uploads/文件名<br/>Vite 代理 → main.py 的 StaticFiles → 图片内容"]
```

图片上传、业务资料保存、图片读取是不同请求；读取图片不经过 Axios 响应拦截器，上传文件本身也不直接更新用户或资源记录。


### 15.7 首页展示与角色快捷入口

首页位于 /manager/home，由 Layout.vue 的 router-view 承载。Home.vue 读取 useUser 的共享用户信息，显示昵称与身份；本地 features 数组生成“业务预约、知识库问答、智能 Agent”三张介绍卡，卡片本身不绑定跳转。

| 入口 | 当前目标 |
| --- | --- |
| 顶部“打开AI助手” | /manager/aichat，对两种角色均显示 |
| 学生快捷入口 | AI 智能助手、实验室列表、我的预约 |
| 管理分支快捷入口 | 预约审核管理、实验室管理、设备管理、用户管理 |

快捷入口由 computed 根据角色生成，router-link 导航到已有页面。当前实现判断 student，其余角色值进入管理分支；页面链接不是后端授权。Layout 的 AI 侧栏项仍只向学生显示，首页顶部按钮则没有该限制。

“开放的实验室”和“与我相关的预约”目前均初始化为 ref(0)，未接入查询；首页也不主动重新获取用户资料。固定三列介绍卡尚未配置移动端断点。具体代码与语法见[首页教程](demo_1代码学习_复习笔记.md#home-overview)。

本次首页收尾已在 frontend 执行 `npm.cmd run build`，构建通过，仍有超过 500 kB 的包体积提示。未执行真实浏览器、模型和数据库联调；结题演示可按“首页 → 学生预约 → 管理员审核 → AI 查询与预约”的顺序，详见[结题展示与后续完善](demo_1代码学习_复习笔记.md#project-closeout)。

<a id="ai-rag-setup"></a>

## 16. LangChain / LangGraph Agent、知识库与预约工具

### 16.1 当前 SSE 能力与入口

页面位于 /manager/aichat，当前入口是 POST /api/ai/chat/stream。API 使用 get_current_user 验证登录，没有额外限定 student 角色；返回 text/event-stream，不返回完整的 Response.success JSON。前端 chatStreamApi 使用带 Bearer 头的 POST fetch 读取流，页面显示状态、工具步骤和增量 Markdown。

```mermaid
flowchart TD
    V["AIChat.vue：reactive 空助手 + 历史"] --> F["chatStreamApi：POST fetch + Authorization"]
    F --> A["/api/ai/chat/stream：StreamingResponse"]
    A --> S["stream_agent：astream_events v2"]
    S --> G["LangGraph：模型 ainvoke / ToolNode"]
    G --> E["status / tool_start / tool_end / token / done / error"]
    E --> W["data: JSON + 空行"]
    W --> D["reader → TextDecoder → buffer 分帧"]
    D --> C["onEvent → status、steps、content"]
    C --> V
```

五个工具继续复用知识库、资源与预约服务；图的 recursion_limit=10 是执行步数上限。当前异步调用未传 max_concurrency，同批工具可能并发，共享 Session 的隔离仍需完善。知识检索由 search_lab_docs 触发，不是每次提问固定执行。

### 16.2 依赖、配置与首次启动

1. 使用后端虚拟环境安装 requirements.txt；其中固定 langgraph 1.2.11、langchain-openai 1.6.2、langchain-core 1.6.3。前端按 package-lock.json 安装依赖。
2. 按第 6.4 节设置数据库、JWT 和 LLM_API_KEY/LLM_MODEL/LLM_BASE_URL；所选模型服务必须支持结构化工具调用。
3. 保留 `backend/data/config_global/agent_config.py`，从 backend 目录启动；它是工具与提示词源码。确认 `backend/data/kb` 中的 Markdown 资料。
4. 提前准备 `BAAI/bge-small-zh-v1.5` 完整本地缓存。加载时指定 `local_files_only=True`，应用不会自动从 Hugging Face 下载缺失文件。

在可访问 Hugging Face 的网络下，从 backend 使用虚拟环境准备缓存：

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5')"
```

当前 Settings 源码中 `KB_WARMUP_ON_STARTUP: bool = True`。未覆盖配置时，lifespan 会先 `await asyncio.to_thread(kb_service.warmup)`，等待本地模型/集合准备和一次预热查询，再创建预约扫描任务。预热异常记录日志后继续启动，不代表知识检索已经可用。

在 backend/.env 设置 `KB_WARMUP_ON_STARTUP=false` 可跳过启动预热，此时首次真正调用 search_lab_docs 才加载模型、初始化集合。环境配置可覆盖源码默认值。只导入 kb_service 不会立即加载模型；预热和首次检索会触发实际加载。[本地模型加载参数](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)

### 16.3 源码、知识原文与运行数据

| 位置 | 作用 |
| --- | --- |
| backend/app/services/agent_service.py | 构建异步消息图、观察事件并生成页面 SSE 数据 |
| backend/data/config_global/agent_config.py | 提示词、五个工具定义与 TOOL_LABELS 中文进度名称 |
| backend/app/services/kb_service.py | BGE 本地加载、Chroma 集合、预热和检索筛选 |
| backend/data/kb | 人工维护的 Markdown 原文，每篇非空文件整体作为一条文档 |
| backend/data/chroma | 持久化向量集合及索引；与模型文件缓存不同 |
| 模型缓存 | 预先下载的 BGE 文件，由模型加载库管理 |

get_collection 仅在空集合时读取 Markdown 入库；修改、增加或删除原文，不会自动同步已有集合，重启和 warmup 也不会覆盖旧文档。切换嵌入模型时应重新建立匹配的索引。当前没有自动重建命令。

检索最多取 5 条候选，按 `1 / (1 + distance)` 筛掉低于 0.5 的结果，再取前 2 条拼接。此分数不是回答正确率，需用实际中文问题校准；与 LangGraph 的图步数限制无关。

### 16.4 请求、事件与前端历史

登录后 POST /api/ai/chat/stream 的请求体：

```json
{"messages":[{"role":"user","content":"实验室安全规范"}]}
```

SSE 响应示意，每帧以空行分隔：

```text
data: {"type":"status","message":"正在思考..."}

data: {"type":"tool_start","name":"search_lab_docs","label":"检索实验室知识库"}

data: {"type":"tool_end","name":"search_lab_docs","label":"检索实验室知识库","preview":"检索资料片段…"}

data: {"type":"token","content":"根据资料"}

data: {"type":"done"}

```

执行异常通过 type=error/message 返回，正常结束发送 done。tool_end 仅表示工具返回，done 仅表示事件迭代结束，二者均不保证预约写入成功。当前 token 可能包含工具前的模型说明或空字符串，未另行确认只转发最终答案。

前端用 TextDecoder 的流模式保留跨块 UTF-8 字节，用 buffer 保留半帧，完整事件立即分发。history 只重传 role/content，不包含 status/steps，也排除本轮空助手；正文仍经 marked 与 DOMPurify。没有服务端会话持久化，刷新后历史重置。

fetch 未配置应用级超时、AbortController、重连或心跳；releaseLock 只释放读取器锁，不取消请求。401 由页面提示，未接入 Axios 的自动登出与跳转。未收到 done 就 EOF 的检测以及部分失败内容的历史过滤仍待完善。

### 16.5 当前故障定位与生命周期

| 现象 | 当前应核对的路径 |
| --- | --- |
| 连接结束才出现全部文字 | 检查模型是否有增量事件、前端是否立即分发完整帧、代理是否缓冲；X-Accel-Buffering:no 仍需部署验证 |
| 中文乱码、JSON 被截断 | 区分 UTF-8 字节边界与 SSE 帧边界；分别检查 TextDecoder 和 buffer |
| 字节到达而 UI 不更新 | 回调应修改 reactive 助手代理，token 追加而非覆盖 |
| 状态显示工具完成但预约失败 | tool_end 可能携带 ok=false 的工具返回；核对 preview、错误和真实记录 |
| 无正文或出现伪工具标签 | 当前流分支尚未复用最终 AIMessage/invalid_tool_calls/伪标签校验，需要补齐 |
| DeepSeek 工具调用兼容问题 | hostname=api.deepseek.com 时设置 thinking.type="disabled"；当前仅回传正文，未实现 reasoning_content 流程 |
| 401 或响应并非 SSE | 核对 token、实际 /chat/stream 路由和响应头；前端目前多为通用错误文案 |
| 知识库不可用 | 核对本地 BGE 缓存、预热日志与已有向量集合，原文修改不会自动同步 |
| 多工具或断流时数据库异常 | 核对异步工具共用 Session 和 yield 依赖的清理时机 |

当前 FastAPI 0.115.13 的 yield 依赖清理发生在发送 StreamingResponse 之前；get_db 会先 close，后续生成器却仍引用该 db。SQLAlchemy 的默认会话可能重置后再使用而不立即报错，但后续连接释放与 ORM 状态仍需处理。不能直接按“依赖保持到流结束”推断安全，详见[流式会话说明](demo_1代码学习_复习笔记.md#sse-session-lifecycle)。

预约扫描现使用 to_thread，并捕获取消后结束循环；取消协程不会强制停止已经运行的线程内数据库操作。main.py 仍负责取消并等待扫描任务。Windows 重载日志可结合新进程启动与接口响应判断；可去掉 --reload 手动重启，区分退出日志与运行故障。

流开始前的 HTTP/JSON 错误与流内 type=error 分别处理；收到 HTTP 200 不代表本轮业务成功。当前尚未建立流断开后撤销工具写入的机制。

### 16.6 预约确认、知识与业务边界

提示词要求先查询真实资源、复述资源 ID/名称和日期时段，得到用户明确确认后才调用创建工具；相对日期先用 get_today 获取服务器日期。当前确认依靠提示词和前端重传历史，没有服务端强制确认节点、确认凭据或写入前 confirmed 校验。

创建工具复用登录身份、ReservationCreateRequest 和原预约 service 的资源/冲突/事务规则。提交成功为 status=0，仍需管理员审核；没有 AI 取消、审核、本人预约查询或单独的时段空闲查询工具。启用实验室不等于某时段可用，设备 quantity 不是剩余库存。

当前知识文件仍需校准：预约规则写已通过也可本人取消，但服务只允许取消待审核；设备使用写预约设备同时占用实验室，而当前冲突按设备和整间实验室分别检查。Markdown 开放时间与数据库字段也没有自动同步。应以实际业务规则核验结果，并同步原文与向量索引。

图执行没有包裹成一笔数据库事务。创建预约已提交后，模型失败、图步数耗尽或前端断流不会撤销记录；当前没有请求级幂等键。审核、取消与扫描的并发状态更新也仍需完善。

### 16.7 实际验收清单

- 验证未登录与不同用户身份，连接未关闭前即可逐段显示状态、工具过程和正文。
- 覆盖长回答、中文跨块、空片段、Markdown 代码块、多个工具和重复工具调用。
- 覆盖空历史、非 SSE 响应、模型失败、解析失败、无 done 的提前 EOF 和长时间无数据。
- 核对代理缓冲、跨域认证、断网/关页后的 loading、连接和数据库清理。
- 在学习库验收预约确认、冲突、工具失败、写入后断流和重复确认，不能只看“工具完成”文案。
- 检查 FastAPI 版本相关的依赖 Session 生命周期，以及异步工具并发使用同一 Session 的问题。
- 继续验收强制确认、幂等、最终文本校验、停止按钮/超时/心跳策略及后台扫描退出。

<a id="ai-tool-flow"></a>

### 16.8 五个工具与预约执行路线

| 工具 | 输入 | 实际调用与返回 |
| --- | --- | --- |
| search_lab_docs | query | kb_service.search，返回资料或未检索到的提示 |
| list_open_labs | 可选 keywords | 启用实验室第 1 页、最多 10 条，返回 total 与资料 |
| list_lab_equipments | lab_id、可选 keywords | 指定实验室设备第 1 页、最多 10 条，不自动筛掉维修设备 |
| create_lab_reservation | 资源 ID、日期、起止时间；可选设备与备注 | 原预约 service 写入，返回 ok、资源与规范化时段，未返回新预约 ID |
| get_today | 无 | 服务器 datetime.now() 的日期，供模型换算相对日期 |

```mermaid
sequenceDiagram
    actor U as 用户
    participant V as AIChat.vue
    participant A as stream_agent / StateGraph
    participant L as ChatOpenAI 绑定的模型
    participant T as ToolNode
    participant S as 业务 service / MySQL
    U->>V: 描述预约资源和明天的时段
    V->>A: 第一次 POST，包含文本历史
    A->>L: 消息与五个工具定义
    L-->>A: 结构化日期/资源查询调用
    A->>T: 执行 get_today 和所需资源查询
    T-->>A: ToolMessage
    A->>L: 查询结果与历史
    L-->>A: 复述资源、日期时段，询问确认
    A-->>V: SSE token 输出确认问题，再 done
    U->>V: 确认预约
    V->>A: 第二次 POST，重传历史与确认文字
    A->>L: 新图读取对话上下文
    L-->>A: create_lab_reservation 工具调用
    A->>T: 执行创建工具
    T->>S: create_reservation(db, current_user, data)
    S-->>T: 校验通过后提交 status=0
    T-->>A: 工具成功 JSON
    A->>L: 工具结果
    L-->>A: 已提交，等待管理员审核
    A-->>V: SSE 工具过程与增量正文，再 done
```

这是符合提示词的示意流程；工具顺序由模型决定，确认并非后端硬性中断节点。工具直接调用 Python service，不经过浏览器再次请求资源 API。详细讲解见[当前 SSE Agent 教程](demo_1代码学习_复习笔记.md#agent-sse)。

### 16.9 SSE 历史测试与本次核对范围

此前在 2026-10-26 的 SSE 文档更新中，于 frontend 执行 `node --test tests/ai.test.js`，7 项通过、0 失败。用例加载实际 chatStreamApi，模拟 fetch/ReadableStream，覆盖未关闭连接时分发、中文跨字节块与 CRLF、无尾空行、401、响应类型、非法 JSON 和回调错误。本次首页收尾时该文件已不在工作区，未重跑此测试。

此前 SSE 更新同时核对了源码、相关依赖实现与文档快照，未调用真实模型、访问业务数据库或重建索引；这些测试不挂载真实页面，也不验证代理、后端会话和工具写入。本次新增的是首页说明与前端构建记录，完整流式验收仍见[教学文档清单](demo_1代码学习_复习笔记.md#sse-validation)。
