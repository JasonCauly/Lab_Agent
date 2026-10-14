# Lab_Agent — 实验室智能预约管理系统

基于 FastAPI、Vue 3、MySQL 的实验室管理系统，包含用户注册登录、JWT 身份认证、用户信息管理、实验室相关数据模型、文件上传等功能，为后续 Agent 智能预约功能提供基础。

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
│   │   ├── schemas/        # Pydantic 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库连接
│   │   └── main.py         # FastAPI 入口
│   ├── .env                # 本地创建，不提交
│   ├── .venv/              # Python 虚拟环境
│   ├── uploads/            # 用户上传文件
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
└── README.md
```

说明：`.env`、`.venv`、`node_modules` 等文件或目录不会包含在 GitHub 仓库中，需要在下载代码后自行配置或安装。具体目录以仓库当前版本为准。

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
- `lab`：实验室信息表

注意：

1. 必须先创建 MySQL 数据库。
2. MySQL 服务必须正常运行。
3. 后端使用的数据库账号必须具有建表权限。
4. `create_all()` 可以创建缺失的表，但不负责后续数据库结构迁移，也不会自动生成测试用户或业务数据。

后续如果修改数据库表结构，建议使用 Alembic 管理迁移。

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

当前仓库的依赖清单主要包含 FastAPI、Uvicorn、SQLAlchemy、PyMySQL、Pydantic Settings、bcrypt 和 PyJWT。

此外，当前文件上传接口使用 `UploadFile`，还需要安装：

```powershell
python -m pip install python-multipart
```

仓库维护者应将 `python-multipart` 加入 `requirements.txt` 并固定经测试的版本，之后新环境就可以仅通过 `requirements.txt` 安装所有依赖。

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
```

参数说明：

| 参数 | 含义 | 是否必需 |
|---|---|---|
| DATABASE_URL | SQLAlchemy 数据库连接字符串 | 是 |
| JWT_SECRET_KEY | JWT 签名密钥 | 是 |
| JWT_EXPIRE_HOURS | Token 有效时间，单位小时 | 否，默认 24 |
| JWT_ALGORITHM | JWT 签名算法 | 否，默认 HS256 |

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

当前前端入口文件使用了 `@element-plus/icons-vue`，但它尚未在当前 `package.json` 中显式声明。

首次配置时建议执行：

```powershell
npm install @element-plus/icons-vue
```

这会更新 `package.json` 和 `package-lock.json`，仓库维护者应将更新后的依赖清单提交到 GitHub。

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
| `/api/files/upload` | POST | 文件上传 |

部分用户管理接口仅允许管理员调用。

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

### 9.5 缺少 DATABASE_URL 或 JWT_SECRET_KEY

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
- 当前用户没有访问相应接口的权限。

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
```

### frontend/.env.example

```dotenv
VITE_API_BASE_URL=
```

这两个示例文件可以上传到 GitHub。

下载项目后，Windows 用户可以执行：

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
python -m pip install python-multipart

# 配置好 backend/.env，确保 MySQL 已启动

python -m uvicorn app.main:app --reload
```

**前端终端：**

```powershell
cd Lab_Agent\frontend
npm ci
npm install @element-plus/icons-vue

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

项目持续开发中，后续将根据实际功能进展完善实验室预约和 Agent 智能交互模块。
