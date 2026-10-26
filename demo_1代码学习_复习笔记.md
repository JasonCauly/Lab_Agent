# demo_1 代码学习：从基础搭建到预约与 AI

整理日期：2026-10-26。

> **学习目标**：理解 lab-agent 的设计与代码，并能从空目录创建、配置、运行和检查项目。
>
> **阅读方法**：按功能顺序学习“职责与文件 → 调用链 → 实现与语法 → 边界与修补 → 验证与复习”。相关修补直接放在功能旁；阶段代码快照集中在所属章节，并保留记录日期。
>
> **版本与验证**：基础章节含 learning-demo 教学整合示例，后续章节含原项目的阶段快照。不要混合不同日期的完整文件。“已实现”“已讲解”“历史检查通过”“待验收”分别记录；历史测试数量不能当作本次重新运行的结果。

当前项目已包括用户与资源管理、学生浏览、预约主要流程与自动过期，以及框架 Agent 的五个工具。聊天现使用 POST SSE，逐步显示状态、工具过程和正文；自定义方案与框架 JSON 方案继续保留用于对照。强制确认、幂等、流式会话清理与工具并发、时段空闲查询及真实环境完整验收仍需完善。

本笔记不保存数据库密码、JWT 密钥或真实 token。示例占位值需替换为学习环境配置。早期 docs 与原后端/前端回归文件未恢复，旧结果见[历史验证记录](#historical-regression)；当前已有 frontend/tests/ai.test.js，7 项 SSE 解析测试的本次结果见[流式验收](#sse-validation)，不要与旧测试数量合并。

## 目录

**第一部分 · 项目与基础搭建**

1. [项目是什么，以及如何从零设计](#01-overview)
2. [目录、环境与第一个前后端请求](#02-start)
3. [配置、数据库与用户模型](#03-database)
4. [统一响应与异常处理](#04-response)

**第二部分 · 身份、用户与资源功能**

5. [注册与登录的后端代码](#05-auth-backend)
6. [身份认证、路由整合与应用生命周期](#06-current-user)
7. [前端请求、登录状态与页面代码](#07-frontend)
8. [个人资料、头像上传与开发代理](#12-profile)
9. [密码修改与管理员用户管理](#13-user-management)
10. [实验室与设备管理](#14-lab-equipment)
11. [学生端实验室与设备浏览](#15-lab-browse)

**第三部分 · 预约完整流程**

12. [预约提交、资源校验与事务并发](#16-reservation)
13. [预约查询、取消、审核与自动过期](#18-reservation-workflow)

**第四部分 · AI 与工具调用**

14. [AI 对话、向量知识库与 RAG](#20-ai-rag)
15. [Agent 两种实现与 SSE：自定义工具循环、LangChain / LangGraph](#22-tool-calling)

**第五部分 · 整体联调与最终验收**

16. [整项目执行路线：从页面操作到数据库再返回](#19-code-flow)
17. [启动、联调、排错与验证记录](#09-check)
18. [功能待办、遗留问题与最终验收](#10-pending)

**第六部分 · 语法与参考**

19. [语法与框架机制速查](#08-questions)
20. [官方参考资料](#11-references)

**按文件定位核心讲解**

| 文件或功能                                          | 阅读位置                                                                           |
| --------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 用户名唯一索引与旧库升级                            | [配置与数据库](#username-migration)、[并发注册](#username-uniqueness)              |
| main.py、lifespan 与后台任务关闭                    | [身份认证与应用入口](#app-lifespan)                                                |
| request.js、Login.vue 与路由实例                    | [前端登录与导航](#17-login-navigation)                                             |
| 用户和资源的关联删除                                | [用户删除](#user-deletion)、[实验室与设备删除](#resource-deletion)                 |
| reservation_service.py 的创建与事务                 | [预约提交与并发](#reservation-concurrency)                                         |
| reservation_service.py 的查询、取消、审核与过期扫描 | [预约完整流程](#18-reservation-workflow)、[过期扫描代码](#reservation-expiry-code) |
| kb_service.py、AIChat.vue 与 RAG                    | [AI 与知识库](#20-ai-rag)                                                          |
| ai_config.py、ai_service.run_tool 与旧自定义循环 | [保留的自定义方案](#22-tool-calling) |
| agent_service.py、agent_config.py 与框架基础 | [框架 JSON 阶段](#langchain-langgraph-agent)、[逐项对照](#agent-framework-comparison) |
| chat_stream、stream_agent、chatStreamApi 与 AIChat.vue | [当前 SSE 输出](#agent-sse)、[流式验收](#sse-validation) |

首次搭建从第一部分开始；追踪一次实际操作可先看[整项目执行路线](#19-code-flow)；核对剩余工作可直接看[遗留问题与最终验收](#10-pending)。

<a id="01-overview"></a>

## 1. 项目是什么，以及如何从零设计

按业务功能学习，每章先理解职责与调用链，再阅读代码、边界和验证要求。首次学习可顺序阅读；复习时使用目录与文件定位表。

### 1.1 四个主要角色

| 部分   | 负责什么                                 | 例子                       |
| ------ | ---------------------------------------- | -------------------------- |
| 前端   | 显示页面、接收操作、发出请求             | 登录页、注册页、菜单       |
| 后端   | 校验输入、处理业务、检查身份、访问数据库 | 判断密码是否正确、创建用户 |
| 数据库 | 持久保存数据                             | 用户账号、密码哈希、昵称   |
| HTTP   | 让浏览器与后端交换信息                   | POST 登录、GET 用户信息    |

浏览器不能因为某个页面上显示了“管理员”就获得管理员权限。后端需要独立检查身份和权限。

### 1.2 一次登录的整体过程

```mermaid
sequenceDiagram
    participant U as 用户
    participant V as Login.vue
    participant A as 前端 API 与 request.js
    participant B as FastAPI 后端
    participant D as MySQL
    U->>V: 输入账号密码，点击登录
    V->>V: 表单校验
    V->>A: loginApi(form)
    A->>B: POST /api/auth/login
    B->>D: 按账号查询用户
    D-->>B: 用户记录
    B->>B: 检查密码和账号状态，生成 token
    B-->>A: code、message、data
    A-->>V: 响应拦截器返回 response.data
    V->>V: 保存 token 和用户信息
    V->>V: 跳转首页
```

再进入首页时：

```text
Home.vue
  → getUserInfoApi()
  → request.js 添加 Authorization
  → GET /api/user/info
  → get_current_user 验证 token、查询数据库
  → 返回当前用户
  → updateUser 更新缓存和界面
```

### 1.3 从零开发时的设计顺序

1. 明确要完成的操作：注册、登录、进入首页、查看用户信息、上传文件。
2. 确定数据：用户有哪些字段，哪些必填，哪些需要唯一。
3. 约定接口：请求地址、HTTP 方法、请求内容、返回内容。
4. 搭建最小前后端，先让一次请求跑通。
5. 实现数据库模型、业务逻辑和接口。
6. 实现页面、请求封装和登录状态。
7. 检查正常流程、输入错误、身份失效等情况。
8. 整理依赖、配置和启动方式，验证能否重新创建项目。

这是一条逐步扩展的路线。初学阶段先完成一个完整的小功能，再扩展其余功能。

### 1.4 原项目与学习副本

| 项目          | 后端端口 | 前端端口 | 用途         |
| ------------- | -------- | -------- | ------------ |
| 原 lab-agent  | 8000     | 5173     | 对照原代码   |
| learning-demo | 8001     | 5174     | 练习从零编写 |

基础学习副本最初只覆盖注册、登录、当前用户和上传。原项目现已包含用户与资源管理、学生浏览、完整预约主要流程、自动过期与框架 Agent。Agent 已提供真实创建预约工具；提示词要求确认，服务端强制确认与完整验收仍待完善。旧自定义只读工具版本保留在第 15 章用于对照，请区分学习副本、历史阶段和当前入口。

本笔记的整合代码用于 **learning-demo**，不需要覆盖原项目。为方便复习，下面把前面分次添加的代码合并在一起，JWT 工具文件统一命名为 `app/utils/token.py`。它不是原仓库所有文件的逐字副本，页面样式只保留学习所需内容。

<a id="02-start"></a>

## 2. 目录、环境与第一个前后端请求

### 2.1 最终达到本节进度的目录

```text
learning-demo/
├─ backend/
│  ├─ .env
│  ├─ .venv/                       # 本机创建，不手写
│  ├─ requirements.txt
│  ├─ seed_user.py
│  └─ app/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ config.py
│     ├─ database.py
│     ├─ api/
│     │  ├─ __init__.py
│     │  ├─ auth.py
│     │  └─ user.py
│     ├─ common/
│     │  ├─ __init__.py
│     │  ├─ response.py
│     │  └─ exceptions.py
│     ├─ dependencies/
│     │  ├─ __init__.py
│     │  └─ auth.py
│     ├─ models/
│     │  ├─ __init__.py
│     │  └─ user.py
│     ├─ schemas/
│     │  ├─ __init__.py
│     │  ├─ auth.py
│     │  └─ user.py
│     ├─ services/
│     │  ├─ __init__.py
│     │  └─ auth_service.py
│     └─ utils/
│        ├─ __init__.py
│        ├─ password.py
│        └─ token.py
└─ frontend/
   ├─ .env.development
   ├─ index.html
   ├─ package.json
   ├─ package-lock.json             # npm 生成，保留以固定依赖
   ├─ vite.config.js
   └─ src/
      ├─ main.js
      ├─ App.vue
      ├─ api/
      │  ├─ auth.js
      │  └─ user.js
      ├─ utils/
      │  ├─ auth.js
      │  ├─ user.js
      │  └─ request.js
      ├─ router/
      │  └─ index.js
      ├─ layouts/
      │  └─ Layout.vue
      └─ views/
         ├─ Register.vue
         ├─ Login.vue
         └─ Home.vue
```

除另有代码的 `api/__init__.py` 外，上述 `__init__.py` 文件可以为空。

### 2.2 开发工具与依赖

之前检查到的本机环境为 Python 3.13.9、Node.js 24.21.0、npm 11.19.0。这些记录用于说明学习时的环境，不代表所有版本组合都已经验证。

- Python 运行后端。
- Node.js 和 npm 用于前端依赖安装、开发服务器与构建。
- MySQL 是数据库服务；安装 PyMySQL 不会安装 MySQL 服务。
- VS Code 是编辑器，本身不代替以上运行环境。

在 PowerShell 中，若 `npm` 被脚本执行策略阻止，可以使用 `npm.cmd`。

在学习副本的 `backend` 目录创建虚拟环境：

```powershell
python -m venv .venv
```

虚拟环境保存本项目自己的 Python 包。教程直接调用其中的 Python，不要求先激活：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

学习副本 `backend/requirements.txt` 的整合内容：

```text
fastapi==0.115.13
uvicorn==0.34.0
sqlalchemy==2.0.41
pymysql[rsa]==1.1.1
pydantic-settings==2.7.1
bcrypt==5.0.0
PyJWT==2.13.0
```

`pymysql[rsa]` 会带上某些 MySQL 认证方式需要的附加依赖。文件上传所需依赖在后续章节补充。

当前 requirements.txt 已包含 python-multipart 与 cryptography。直接使用的 @element-plus/icons-vue 目前仍由 Element Plus 间接提供，显式声明依赖仍是整理项。

### 2.3 第一个后端程序

刚开始练习时，`backend/app/main.py` 可以只有：

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/hello")
def hello(name: str = "student"):
    return {"message": f"你好，{name}"}
```

在 `backend` 目录启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

- `app.main`：导入 `app/main.py` 这个模块。
- 冒号后的 `app`：该模块内创建的 FastAPI 应用对象。
- `--reload`：代码变化时重新加载，适合开发。
- `/hello?name=张三`：通过查询参数传入名字。
- `name: str`：类型标注。
- `= "student"`：未传入时使用默认值。

访问：

```text
http://127.0.0.1:8001/
http://127.0.0.1:8001/hello?name=张三
http://127.0.0.1:8001/docs
```

`/docs` 是 FastAPI 生成的接口文档。路径不匹配通常是 404，方法不匹配通常是 405。

### 2.4 第一个前端请求

在 `learning-demo` 目录初始化 Vue 项目：

```powershell
npm.cmd create vite@latest frontend -- --template vue --no-interactive
```

进入 `frontend` 后：

```powershell
npm.cmd install
npm.cmd install axios@1.20.0 --save-exact
```

脚手架的模板和依赖可能随版本变化。保留生成的 `package.json`、`package-lock.json`，后续复现使用锁文件安装；不能仅靠一条 `@latest` 命令保证不同时间的环境完全相同。

创建 `frontend/.env.development`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

最初用于测试连通性的 `App.vue` 可以写成：

```vue
<template>
  <div>
    <input v-model="name" placeholder="请输入名字" />
    <button @click="sayHello">请求后端</button>
    <p>{{ message }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";

const name = ref("student");
const message = ref("");

async function sayHello() {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_API_BASE_URL}/hello`,
      {
        params: { name: name.value },
        timeout: 5000,
      },
    );

    message.value = response.data.message;
  } catch {
    message.value = "请求失败，请检查后端是否启动";
  }
}
</script>
```

- `<template>`：页面结构。
- `<script setup>`：组件逻辑。
- `v-model`：把输入框内容与变量关联。
- `@click`：点击时调用函数。
- `ref`：创建响应式数据；脚本通过 `.value` 访问。
- `await`：等待 Promise 的结果；通常写在 `async` 函数中。
- 原生 Axios 返回的 `response` 包含状态、响应头和 `data`，后面封装的 `request.js` 会改变页面得到的结果。

启动前端：

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

`--strictPort` 用于端口被占用时直接报告错误，避免自动换端口后与 CORS 配置不一致。

### 2.5 跨域 CORS

前端 5174 与后端 8001 属于不同来源。浏览器需要后端允许这个来源。

在创建 `app` 后添加：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

CORS 是浏览器的跨来源访问机制；它不代替身份认证或权限检查。

<a id="03-database"></a>

## 3. 配置、数据库与用户模型

### 3.1 创建学习数据库

在已经连接 MySQL 的数据库客户端执行：

```sql
CREATE DATABASE learning_lab_agent
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

这一步创建数据库。SQLAlchemy 的 `create_all()` 后面负责创建表，不能代替创建数据库。

### 3.2 环境配置

2026-10-23 更新：本节保留基础阶段配置。当前 Settings 还要求 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL；从零启动当前版本请使用 README 第 6.4 节完整配置，新增字段解释见第 14.3 节。

学习副本 `backend/.env`：

```env
DATABASE_URL=mysql+pymysql://YOUR_USER:YOUR_PASSWORD@127.0.0.1:3306/learning_lab_agent
JWT_SECRET_KEY=REPLACE_WITH_YOUR_GENERATED_SECRET
JWT_EXPIRE_HOURS=24
JWT_ALGORITHM=HS256
```

将数据库用户、密码和密钥占位符替换成自己的值。数据库密码中若有 `@`、`:` 等 URL 特殊字符，需要正确进行 URL 编码。

生成本机学习密钥：

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

将输出写入后端 `.env` 的 `JWT_SECRET_KEY`。不要把后端密钥放到前端环境变量中。

学习副本 `backend/app/config.py`：

```python
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
```

初次数据库课程只要求 `DATABASE_URL`；这里是加入登录后的最终配置，所以启动前也必须准备 JWT 密钥。

读取关系：

```text
settings = Settings()
  → BaseSettings 读取 model_config
  → 根据 env_file 找到 backend/.env
  → 按声明的字段名查找 DATABASE_URL 等配置
  → 转换类型并校验
  → 创建 settings 对象
  → database.py 使用 settings.DATABASE_URL
```

- `__file__`：当前 Python 文件路径。
- `resolve()`：获得解析后的绝对路径。
- 第一个 `.parent` 是 `app`，第二个是 `backend`。
- `env_file` 给出文件位置，字段名决定取哪项配置；字段不会自己调用 `env_file`。
- `model_config` 是 Pydantic 规定的配置属性名，不是 Python 关键字，不能随意改名后期待相同功能。
- `env_file`、`env_file_encoding` 是库规定的配置键。
- `settings` 是自己定义的变量名，可以改，但引用处也必须改。
- 在本教程的默认配置中，同名进程环境变量优先于 `.env`。
- `settings` 在模块加载时创建，修改 `.env` 后要重启后端，不会每次请求自动重新读取。

### 3.3 数据库连接与公共基类

`backend/app/database.py`：

```python
from datetime import datetime

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

from app.config import settings


engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
```

| 名称         | 理解方式                             |
| ------------ | ------------------------------------ |
| engine       | 管理数据库连接与连接池               |
| SessionLocal | 创建数据库会话的工厂                 |
| db           | 某次使用的数据库会话                 |
| Base         | 所有数据库模型共用的父类             |
| get_db       | 给接口提供数据库会话，并在结束后关闭 |

`create_engine()` 通常不会立即执行 SQL；真正查询或建表时才需要连接。

`yield db` 将会话交给请求使用；`finally` 用于执行关闭操作，即使中途出现异常也会进入。

`default=datetime.now` 传的是函数，插入记录时再调用。写成 `datetime.now()` 会在定义代码时先计算一次时间。

### 3.4 用户表模型

`backend/app/models/user.py`：

```python
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    email: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(50))
    avatar: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[bool] = mapped_column(Boolean, default=True)
```

- ORM：用 Python 类和对象表示数据库表与记录。
- `__tablename__`：实际数据库表名。
- `Mapped[str]`：SQLAlchemy 映射属性的类型声明。
- `mapped_column(...)`：声明列及长度、是否可空等规则。
- `nullable=False`：不能存 SQL NULL，不等于禁止空字符串。
- `str | None`：字符串或空值。
- `User` 继承 `Base`，因此拥有 ID 和时间字段。

学习代码沿用原项目模型，没有在用户名列上增加唯一约束。注册前查询可以识别一般重复操作，但并发请求下仍需要数据库唯一约束；这一改进尚未实施。

### 3.5 建表与初始化用户

建表前要先导入模型，使 SQLAlchemy 知道有哪些表：

```python
from app.models.user import User
from app.database import Base, engine

Base.metadata.create_all(bind=engine)
```

`create_all()` 可以创建尚不存在的表，不能自动完成现有表结构迁移。修改模型不代表旧表会同步改变。

可选的 `backend/seed_user.py`：

```python
import bcrypt

from app.database import Base, SessionLocal, engine
from app.models.user import User


Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    existing = db.query(User).filter(
        User.username == "demo_student"
    ).first()

    if existing:
        print("示例用户已经存在")
    else:
        password_hash = bcrypt.hashpw(
            "Learn123!".encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        user = User(
            username="demo_student",
            password=password_hash,
            name="示例学生",
            role="student",
            status=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"创建成功，用户 ID：{user.id}")
except Exception:
    db.rollback()
    raise
finally:
    db.close()
```

在 `backend` 目录运行：

```powershell
.\.venv\Scripts\python.exe seed_user.py
```

这个密码仅是学习示例。重复执行脚本不会因为正常的重复运行再创建同名示例用户。

数据库操作含义：

```text
db.add(user)      把对象加入会话，准备保存
db.commit()      提交事务，持久保存
db.refresh(user) 重新从数据库读取，包括生成的 ID
db.rollback()    发生错误时回滚当前事务
db.close()       释放会话使用的资源
```

可以在数据库客户端检查：

```sql
USE learning_lab_agent;
SHOW TABLES;
DESCRIBE users;
SELECT id, username, name, role, status FROM users;
```

<a id="username-migration"></a>

### 3.6 已有用户表的唯一索引升级与幂等

模型声明只会影响新表创建；已有 users 表不会被 create_all() 自动追加唯一约束。

backend/app/migrations/add_username_unique.py 的 upgrade(connection) 依次执行：

1. inspect(connection) 读取数据库实际已有的唯一约束和索引。
2. 如果已存在仅针对 username 的唯一约束或唯一索引，返回 False，表示无需修改。
3. 用反射加载已有 users 表结构。
4. GROUP BY username、HAVING COUNT(\*) > 1 查找重复用户名。
5. 发现重复则抛错，保留账号和预约数据，由维护者先核实处理。
6. 没有重复则创建 uq_users_username 唯一索引，返回 True。

脚本可以重复执行，而不会每次再建一个相同约束，这种性质叫幂等。它不是“执行多少次都会新增一条相同数据”，而是重复执行不会再次改变已达到目标的状态。

操作命令必须在 backend 目录运行：

```powershell
.\.venv\Scripts\python.exe -m app.migrations.add_username_unique
```

-m 后面是 Python 模块路径，用点分隔，不能写成文件系统中的反斜杠路径。

脚本读取实际项目数据库配置，会修改目标库结构。运行前应备份、确认配置目标并暂停账号创建等相关写入；若两个检查与建索引之间仍有人写入重复账号，升级也可能失败。

本次只运行测试中的临时 SQLite 版本，没有对你的 MySQL 执行这个命令。该脚本也不处理第 12.4 节的 lab → labs 迁移。

**复习自测**

| 问题                                           | 核对要点                 |
| ---------------------------------------------- | ------------------------ |
| 用户名模型加了唯一约束，旧数据库是否立即生效？ | 不会，需要实际升级数据库 |

### 3.7 本章修补代码快照（2026-10-20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/models/user.py</code></summary>

```python
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, UniqueConstraint


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        {"comment": "用户信息表"},
    )

    username: Mapped[str] = mapped_column(String(50), comment="账号")
    password: Mapped[str] = mapped_column(String(255), comment="密码")
    name: Mapped[str] = mapped_column(String(50), comment="名称")
    role: Mapped[str] = mapped_column(
        String(50), comment="角色: student-学生, admin-管理员"
    )
    email: Mapped[str | None] = mapped_column(String(50), comment="邮箱", nullable=True)
    phone: Mapped[str | None] = mapped_column(
        String(50), comment="手机号", nullable=True
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), comment="头像", nullable=True
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态: True-启用, False-禁用"
    )
```

</details>

<details>
<summary><code>backend/app/migrations/add_username_unique.py</code></summary>

```python
"""运行方式：在 backend 目录执行 python -m app.migrations.add_username_unique。"""

from sqlalchemy import Index, MetaData, Table, func, inspect, select
from sqlalchemy.engine import Connection

from app.database import engine


def upgrade(connection: Connection) -> bool:
    """为已有 users 表添加唯一索引；有重复账号时停止，不改动账号数据。"""
    inspector = inspect(connection)
    unique_keys = inspector.get_unique_constraints("users") + inspector.get_indexes(
        "users"
    )
    if any(
        key.get("column_names") == ["username"] and key.get("unique", True)
        for key in unique_keys
    ):
        return False

    users = Table("users", MetaData(), autoload_with=connection)
    duplicate = connection.execute(
        select(users.c.username)
        .group_by(users.c.username)
        .having(func.count() > 1)
        .limit(1)
    ).first()
    if duplicate:
        raise RuntimeError(
            "users 表存在重复账号，请先核实账号及其预约归属，处理重复数据后重试；"
            "本脚本不会自动删除或合并账号。"
        )

    Index("uq_users_username", users.c.username, unique=True).create(connection)
    return True


if __name__ == "__main__":
    with engine.begin() as connection:
        changed = upgrade(connection)
    print("用户名唯一索引已创建" if changed else "用户名唯一约束已存在，无需修改")
```

</details>

<a id="04-response"></a>

## 4. 统一响应与异常处理

### 4.1 为什么要统一格式

前端可以用相同的方式读取所有接口的结果：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": null
}
```

HTTP 状态码与 JSON 中的 `code` 是不同位置的两个值。例如，原项目的业务异常处理器返回 HTTP 200，但 JSON 中可能是 `code: 500`。

### 4.2 Response 模型

`backend/app/common/response.py`：

```python
from typing import Any

from pydantic import BaseModel


class Response(BaseModel):
    code: int
    message: str
    data: Any = None

    @classmethod
    def success(
        cls,
        message: str = "请求成功",
        data: Any = None,
    ):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(
        cls,
        code: int = 500,
        message: str = "请求失败",
    ):
        return cls(code=code, message=message)
```

`Response.success(...)` 创建一个响应数据对象，不会自己发出 HTTP 请求。`cls` 和 `@classmethod` 的具体解释见第 19 节。

### 4.3 异常类型与处理器

下面整合了讲过的业务异常、参数校验异常和 HTTP 异常，也列出原项目中的全局异常处理写法。全局异常的日志与排错策略仍需要后续系统讲解。

`backend/app/common/exceptions.py`：

```python
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.response import Response


class BusinessException(Exception):
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)


async def business_exception_handler(
    request: Request,
    exc: BusinessException,
):
    return JSONResponse(
        status_code=200,
        content=Response.error(
            code=exc.code,
            message=exc.message,
        ).model_dump(),
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content=Response.error(
            code=exc.status_code,
            message=str(exc.detail),
        ).model_dump(),
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content=Response.error(
            code=422,
            message="请求参数校验错误",
        ).model_dump(),
    )


async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content=Response.error(
            code=500,
            message="服务器内部错误",
        ).model_dump(),
    )
```

| 情况                           | 异常                   | 学习副本的 HTTP 状态 | JSON code |
| ------------------------------ | ---------------------- | -------------------- | --------- |
| 账号已存在                     | BusinessException      | 200                  | 409       |
| 账号或密码错误                 | BusinessException      | 200                  | 400       |
| 登录凭证无效                   | HTTPException          | 401                  | 401       |
| 当前账号被禁用                 | HTTPException          | 403                  | 403       |
| 请求字段不符合规则             | RequestValidationError | 422                  | 422       |
| 未被以上处理器处理的服务器错误 | Exception              | 500                  | 500       |

这些业务 code 是学习副本显式设置的。原项目未传 code 的 `BusinessException` 使用默认 500。

### 4.4 raise、try、except、finally

```python
try:
    # 尝试执行
    ...
except SomeException:
    # 捕获指定异常后执行
    ...
finally:
    # 无论正常还是异常，执行清理
    ...
```

- `return`：正常结束函数，返回值。
- `raise`：抛出异常，中断当前正常流程，寻找异常处理逻辑。
- `except`：捕获匹配的异常。
- `finally`：执行关闭数据库会话、恢复页面加载状态等清理操作。

业务异常的流程：

```text
服务函数发现账号重复
  → raise BusinessException(...)
  → 接口函数后续代码停止
  → FastAPI 调用已注册的处理器
  → JSONResponse 返回约定的格式
```

普通接口返回 Pydantic 模型时，FastAPI 可以处理序列化。自己构造 `JSONResponse` 时，需要先准备可编码的内容；`.model_dump()` 的详细解释见第 19 节。

<a id="05-auth-backend"></a>

## 5. 注册与登录的后端代码

### 5.1 输入模型和输出模型

模型分成两类：

- 数据库模型 `User`：描述数据库表，包含密码哈希等字段。
- Pydantic 模型：描述接口输入和输出，进行校验或控制返回字段。

`backend/app/schemas/user.py`：

```python
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)
```

`from_attributes=True` 允许从对象属性读取字段，所以可以转换 SQLAlchemy 用户对象：

```python
UserResponse.model_validate(user)
```

没有在输出模型中声明密码，接口返回的这份用户资料就不包含密码。

`backend/app/schemas/auth.py`：

```python
from pydantic import BaseModel, Field, field_validator

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    name: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=50)

    @field_validator("password")
    @classmethod
    def check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码不能超过 72 个 UTF-8 字节")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def check_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("密码不能超过 72 个 UTF-8 字节")
        return value


class LoginResponse(BaseModel):
    token: str
    user: UserResponse
```

学习副本增加了长度校验，原项目的输入模型较简单。bcrypt 5 对超过 72 字节的密码会报错，字节数与字符数不是同一个概念。

原注册页面会发送 `confirmPassword`；此处模型没有这个字段，Pydantic 默认会忽略额外字段。确认密码用于前端检查，后端校验真正用于注册的 `password`。

### 5.2 密码哈希

`backend/app/utils/password.py`：

```python
import bcrypt


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt)
    return password_hash.decode("utf-8")


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
```

- 哈希是密码验证所需的单向计算结果。
- 盐值用于让相同密码的不同记录也能产生不同哈希。
- 注册：计算哈希后保存。
- 登录：使用 `checkpw` 验证输入密码与保存的哈希是否匹配。
- 不通过“解密哈希”找回原始密码。

### 5.3 生成 JWT

`backend/app/utils/token.py`：

```python
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        hours=settings.JWT_EXPIRE_HOURS
    )

    payload = {
        "user_id": user_id,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
```

JWT 是一种 token 格式。本教程使用签名验证内容是否可信：

- `user_id`：这个 token 对应哪个用户。
- `exp`：有效期截止时间。
- 签名：帮助后端发现 token 被修改。

JWT 的载荷通常可以被读取，签名不等于加密，所以不能在载荷中保存密码。

原项目 JWT 工具在 `app/utils/jwt.py`。学习副本使用 `token.py`，并采用带 UTC 时区的时间；原项目之前读取的写法使用 `datetime.now()`。

### 5.4 JWT 有效期：用 UTC 时间修正时区偏差

原来：

```python
expire = datetime.now() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
```

得到的是没有时区信息的本地时间。PyJWT 对 exp 的编码和比较使用 UTC 时间语义，因而把本地钟面值当作 UTC 会产生偏差。原审查在 UTC+8 环境中测到配置 24 小时、实际约 32 小时的结果。

现在：

```python
expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
```

timezone.utc 使 datetime 明确携带 UTC 时区；timedelta 表示一个持续时长。PyJWT 再把它编码成 exp 时间戳。参见 [PyJWT 过期时间说明](https://pyjwt.readthedocs.io/en/stable/usage.html#expiration-time-claim-exp)。

测试检查实际 token 的有效时长，并模拟不同本地时区，确认都接近配置小时数乘以 3600。

这只修正时间计算，没有增加“修改密码立即注销所有旧 token”的服务端机制。旧令牌的撤销问题仍待处理。

### 5.5 注册与登录的业务逻辑

`backend/app/services/auth_service.py`：

```python
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.utils.password import hash_password, verify_password
from app.utils.token import create_access_token


def register(db: Session, data: RegisterRequest) -> None:
    existing = db.query(User).filter(
        User.username == data.username
    ).first()

    if existing:
        raise BusinessException(
            message="账号已存在",
            code=409,
        )

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name or data.username,
        email=data.email,
        role="student",
        status=True,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise


def login(db: Session, data: LoginRequest) -> LoginResponse:
    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user or not verify_password(
        data.password,
        user.password,
    ):
        raise BusinessException(
            message="账号或密码错误",
            code=400,
        )

    if not user.status:
        raise BusinessException(
            message="账号已被禁用",
            code=403,
        )

    token = create_access_token(user.id)

    return LoginResponse(
        token=token,
        user=UserResponse.model_validate(user),
    )
```

`data.name or data.username` 表示昵称没有有效值时，使用账号作为昵称。

`if not user or ...` 使用短路求值：没有用户时，右侧密码检查不会执行，因此不会去访问不存在的 `user.password`。

后端决定新账号的角色，前端不能仅通过提交 `role: "admin"` 就获得管理员权限。

<a id="username-uniqueness"></a>

### 5.6 并发注册：用户名唯一约束与失败回滚

用户模型增加：

```python
__table_args__ = (
    UniqueConstraint("username", name="uq_users_username"),
    {"comment": "用户信息表"},
)
```

原来只传一个表配置字典，现在是包含约束和配置字典的元组。UniqueConstraint 告诉数据库：users.username 不允许重复。

服务仍保留“查询账号已存在”的检查，用来尽早给出友好提示。但两个请求可能同时通过，所以注册和管理员创建用户都增加了提交时的处理：

```python
try:
    db.commit()
except IntegrityError as exc:
    db.rollback()
    if db.query(User.id).filter(User.username == data.username).first():
        raise BusinessException(message="账号已存在", code=409) from exc
    raise
```

IntegrityError 表示数据库完整性约束失败，例如唯一约束或外键冲突。先 rollback，再查询是否确有同名账号，确认后才转换成账号已存在；其他完整性错误继续抛出。

如果数据库没有真正安装唯一约束，这个异常分支不会凭空阻止同名写入。因此已有库必须执行[已有用户表的唯一索引升级](#username-migration)。

注册服务还修正了原来的 db.rollback：

```python
db.rollback()
```

不带括号只是取得方法对象；带括号才执行回滚。这与前面 JavaScript 中“函数本身”和“调用函数”是同一类基础区别。

### 5.7 注册与登录接口

`backend/app/api/auth.py`：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["权限验证"])


@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    auth_service.register(db, data)
    return Response.success(message="注册成功")


@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    result = auth_service.login(db, data)
    return Response.success(
        message="登录成功",
        data=result,
    )
```

接口层接收请求并组织返回，服务层处理业务。小程序可以暂时放在一起，分层是为了后续更容易修改、复用与阅读。

### 5.8 本章修补代码快照（2026-10-20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/services/auth_service.py</code></summary>

```python
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.schemas.user import UserResponse
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token


def login(db: Session, data: LoginRequest):
    # 根据用户名查询用户信息
    user = db.query(User).filter(User.username == data.username).first()

    # 判断账号和密码是否正确
    if not user or not verify_password(data.password, user.password):
        raise BusinessException(message="账号或密码错误")
    # 判断账号是否被禁用
    if user.status != 1:
        raise BusinessException(message="账号已被禁用")
    # 生成访问令牌
    access_token = create_access_token(user.id)
    return LoginResponse(token=access_token, user=UserResponse.model_validate(user))


def register(db: Session, data: RegisterRequest):
    # 根据用户账号查询数据库
    user = db.query(User).filter(User.username == data.username).first()

    if user:
        raise BusinessException(message="账号已存在", code=409)

    user_model = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name or data.username,
        email=data.email,
        role="student",
        status=1,
    )
    db.add(user_model)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if db.query(User.id).filter(User.username == data.username).first():
            raise BusinessException(message="账号已存在", code=409) from exc
        raise
    except Exception:
        db.rollback()
        raise
    db.refresh(user_model)
```

</details>

<details>
<summary><code>backend/app/utils/jwt.py</code></summary>

```python
from datetime import datetime, timedelta, timezone
import jwt
from app.config import settings


def create_access_token(user_id: int) -> str:
    """
    Create a JWT access token.

    :param data: The data to encode in the token (usually user information).
    :param secret_key: The secret key used to sign the token.
    :param algorithm: The algorithm used for encoding (default is HS256).
    :return: A JWT access token as a string.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    payload = {"user_id": user_id, "exp": expire}

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode a JWT access token.

    :param token: The JWT access token to decode.
    :param secret_key: The secret key used to sign the token.
    :param algorithms: A list of algorithms to use for decoding (default is HS256).
    :return: The decoded payload as a dictionary.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
```

</details>

<a id="06-current-user"></a>

## 6. 身份认证、路由整合与应用生命周期

先用当前用户依赖与总路由完成最小后端，再阅读 main.py 的完整生命周期。过期扫描的业务规则在预约流程章讲解；本章只负责应用如何启动、注册功能和关闭后台任务。

### 6.1 当前用户依赖

`backend/app/dependencies/auth.py`：

```python
import jwt

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    auth_error = HTTPException(
        status_code=401,
        detail="登录信息无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise auth_error

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "user_id"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise auth_error

    user_id = payload.get("user_id")

    if type(user_id) is not int or user_id <= 0:
        raise auth_error

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise auth_error

    if not user.status:
        raise HTTPException(
            status_code=403,
            detail="账号已被禁用",
        )

    return user
```

主要顺序：

```text
提取 token
  → 确认存在
  → 验证签名与 exp
  → 确认必要字段
  → 读取用户 ID
  → 查询数据库
  → 检查用户存在且可用
  → 返回 User 对象
```

`OAuth2PasswordBearer` 从 `Authorization: Bearer ...` 请求头中提取 token。它不会自动验证 JWT，也不会自动调用登录接口。`tokenUrl` 描述获取 token 的地址。

`auto_error=False` 让缺少 token 的情况由我们显式返回 401，减少不同版本默认行为带来的差异。

此处与原项目有几处教学上的调整：

- 解码直接放在依赖函数中，方便看清完整顺序。
- 区分过期与其他无效 token，而不是捕获所有异常。
- 要求有 `exp` 和 `user_id`，并检查用户 ID 类型。
- 用户不存在时返回 401；原项目之前读取的代码返回 404。
- HTTP 异常处理器保留 `WWW-Authenticate` 响应头。

这些是学习副本的实现，不意味着已经修改了原项目。

### 6.2 获取用户信息接口

`backend/app/api/user.py`：

```python
from fastapi import APIRouter, Depends

from app.common.response import Response
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse


router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/info")
def get_user_info(
    current_user: User = Depends(get_current_user),
):
    user_data = UserResponse.model_validate(current_user)
    return Response.success(data=user_data)
```

`Depends(get_current_user)` 的含义：先执行这个依赖，成功后将其返回值填入 `current_user`。

如果依赖抛出异常，接口函数体不会执行。前端不需要提交用户 ID，后端根据经过验证的 token 确定身份。

这里给接口函数取名 `get_user_info`，避免与导入的依赖函数同名。

### 6.3 合并路由

`backend/app/api/__init__.py`：

```python
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.user import router as user_router


api = APIRouter(prefix="/api")

api.include_router(auth_router)
api.include_router(user_router)
```

完整地址：

| 前缀与路径               | 最终地址           | 方法 |
| ------------------------ | ------------------ | ---- |
| /api + /auth + /register | /api/auth/register | POST |
| /api + /auth + /login    | /api/auth/login    | POST |
| /api + /user + /info     | /api/user/info     | GET  |

### 6.4 基础学习阶段的后端入口整合版

阶段说明：下面是早期入口。第 6.5 节讲扫描的启动与关闭；2026-10-25 入口还增加了知识库预热，当前完整 main.py 与配置见第 6.8 节。

`backend/app/main.py`：

```python
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.database import Base, engine, get_db
from app.models.user import User


# 导入 User 后，元数据才能知道需要创建 users 表。
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    BusinessException,
    business_exception_handler,
)
app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
app.add_exception_handler(
    Exception,
    global_exception_handler,
)

app.include_router(api)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/hello")
def hello(name: str = "student"):
    return {"message": f"你好，{name}"}


@app.get("/users/count")
def count_users(db: Session = Depends(get_db)):
    return {"count": db.query(User).count()}
```

`/hello` 和 `/users/count` 是前面用于验证连通性、数据库访问的学习接口。本进度还没有加入文件上传、静态文件挂载或完整的管理菜单。

原项目登录接口接收 JSON；Swagger 的 OAuth2 Authorize 按钮默认走标准表单流程，不能仅凭 `tokenUrl` 就认为两者已经适配。本笔记用前端登录和 Network 面板检查请求，不使用该按钮作为登录验证方式。

<a id="app-lifespan"></a>

### 6.5 应用生命周期：启动扫描、取消任务并等待关闭

本节保留扫描生命周期的讲解。当前入口在创建扫描任务前先按配置等待知识库预热，完整顺序见第 6.8 节。

main.py 的关键部分：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(reservation_service.run_expire_scan())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
```

yield 之前安排启动任务，yield 之后对应退出清理。cancel 发出取消请求，await 等待协程真正结束；suppress 只处理预期的 CancelledError，其他异常不会因此消失。

曾经的 changed 异常会令任务退出；如果没有及时取回任务异常，就可能看到 Task exception was never retrieved。生命周期清理解决取消收尾，不能代替扫描循环的异常恢复。Ctrl+C、重载时也可能出现服务主任务的取消堆栈，要结合前后日志判断，不能把所有 CancelledError 都当成业务失败或全部忽略。

多进程部署时每个应用进程都可能启动自己的扫描任务。扫描也会与管理员审核或本人取消竞争：读到 status=0 后直接修改对象并提交，未使用带原状态条件的原子更新。后续可统一状态转换、异常日志和任务调度策略。

过期判定、独立 Session 和扫描函数见[预约自动过期](#reservation-expiry)。业务层负责改变状态，入口层负责安排任务和退出清理。

**错误复盘（2026-10-23）**

| 故障               | 原因           | 已保存的修补或定位方式                     |
| ------------------ | -------------- | ------------------------------------------ |
| 关闭时只发取消请求 | 未等待任务退出 | finally 中 cancel 后 await，并处理预期取消 |

<a id="main-current-snapshot"></a>

### 6.6 backend/app/main.py：含生命周期的入口快照（2026-10-23）

```python
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.database import engine, Base
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)
from app.services import reservation_service

Base.metadata.create_all(bind=engine)  # 自动创建数据库表结构


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(
        reservation_service.run_expire_scan()
    )  # 启动项目 开启异步的扫描任务
    try:
        yield
    finally:
        task.cancel()  # 关闭项目 同时取消异步任务
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)

app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底, 必须放在最后注册!!!
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录 http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Hello, World!"}
```

<a id="entry-history"></a>

### 6.7 总路由与应用入口的早期阶段快照

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/api/__init__.py</code>（2026-10-15）</summary>

```python
from fastapi import APIRouter, Depends
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.files import router as files_router
from app.api.lab import router as lab_router
from app.api.equipment import router as equipment_router

api = APIRouter(prefix="/api", tags=["用户信息"])

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(files_router)
api.include_router(lab_router)
api.include_router(equipment_router)
```

</details>

<details>
<summary><code>backend/app/main.py</code>（2026-10-15）</summary>

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR
from app.models.user import User
from app.models.lab import Lab
from app.database import engine, Base
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

Base.metadata.create_all(bind=engine)  # 自动创建数据库表结构

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)

app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底, 必须放在最后注册!!!
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录 http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Hello, World!"}
```

</details>

<details>
<summary><code>backend/app/api/__init__.py</code>（2026-10-20）</summary>

```python
from fastapi import APIRouter, Depends
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.files import router as files_router
from app.api.lab import router as lab_router
from app.api.equipment import router as equipment_router
from app.api.reservation import router as reservation_router

api = APIRouter(prefix="/api", tags=["用户信息"])

api.include_router(auth_router)
api.include_router(user_router)
api.include_router(files_router)
api.include_router(lab_router)
api.include_router(equipment_router)
api.include_router(reservation_router)
```

</details>

<details>
<summary><code>backend/app/main.py</code>（2026-10-20）</summary>

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR
from app.models.equipment import Equipment
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.database import engine, Base
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

Base.metadata.create_all(bind=engine)  # 自动创建数据库表结构

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)

app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底, 必须放在最后注册!!!
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录 http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Hello, World!"}
```

</details>

<a id="kb-startup-lifecycle"></a>

### 6.8 当前入口：知识库预热与扫描任务的先后顺序（2026-10-25）

2026-10-26 补充：本节 main.py 的预热与创建任务顺序仍适用；被调用的 run_expire_scan 已线程化并处理取消，具体变化归入[预约扫描](#expiry-thread-scan)。流式接口的依赖 Session 清理是另一问题，见[流式会话生命周期](#sse-session-lifecycle)。

第 6.5～6.7 节保留扫描生命周期与早期入口。当前 main.py 在创建扫描任务之前增加知识库预热，Settings 的 `KB_WARMUP_ON_STARTUP` 源码默认值为 True，环境配置可覆盖它。

```text
导入配置、数据库、模型与路由 → 创建 FastAPI 应用
  → lifespan 启动
  → 开关为 true：await asyncio.to_thread(kb_service.warmup)
      → 准备本地向量模型与 Chroma 集合；非空集合执行一次预热查询
      → 失败记录 logger.exception，然后继续启动
  → 开关为 false：跳过预热
  → create_task(run_expire_scan())
  → yield：服务接收请求
  → finally：取消扫描任务并等待它结束
```

to_thread 将同步预热工作交给线程执行；await 仍会等待它完成，因此这不是启动后放任执行的后台预热任务。默认预热完成或失败被捕获后，才安排预约扫描。预热失败不阻止其他后端接口启动，也不说明知识工具已可用。

kb_service 的模块级 `_embedding_fn` 现在初始为 None，不再一导入就加载模型。设置 false 时，模型和集合延迟到首次实际检索；设置 true 时，warmup 会提前触发加载与空集合入库。当前只读取本地模型缓存，具体配置与检索实现见第 14.19～14.20 节。

以下快照来自当前源码。配置文件只声明字段，不包含 `.env` 中的真实连接、密钥或令牌；保留前面的历史入口便于比较新增生命周期步骤。

<details>
<summary><code>backend/app/main.py</code>（2026-10-25）</summary>

```python
import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR, settings
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.database import engine, Base
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)
from app.services import kb_service, reservation_service

Base.metadata.create_all(bind=engine)  # 自动创建数据库表结构

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.KB_WARMUP_ON_STARTUP:
        try:
            await asyncio.to_thread(kb_service.warmup)
        except Exception:
            logger.exception("知识库预热失败，后端继续启动；请检查本地向量模型缓存")
    task = asyncio.create_task(
        reservation_service.run_expire_scan()
    )  # 启动项目 开启异步的扫描任务
    try:
        yield
    finally:
        task.cancel()  # 关闭项目 同时取消异步任务
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许的前端源，不要直接写 ["*"]
    allow_credentials=True,  # ✅ 关键：允许前端携带 Authorization token
    allow_methods=["*"],  # 允许所有请求方法 GET POST PUT DELETE OPTIONS
    allow_headers=["*"],  # 允许所有请求头（包含Authorization）
)

app.include_router(api)

# 注册异常处理器
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 全局的异常兜底, 必须放在最后注册!!!
app.add_exception_handler(Exception, global_exception_handler)

# 挂载静态的文件目录 http://127.0.0.1:8000/uploads/xxx.jpg
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "Hello, World!"}
```

</details>

<details>
<summary><code>backend/app/config.py</code>（2026-10-25）</summary>

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # 后端项目的根路径


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str

    # JWT settings
    JWT_SECRET_KEY: str
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"

    # LLM setting
    LLM_API_KEY: str
    LLM_MODEL: str
    LLM_BASE_URL: str

    # Knowledge-base models are loaded lazily from the local cache by default.
    KB_WARMUP_ON_STARTUP: bool = True

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8"
    )


settings = Settings()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
}
```

</details>

<a id="07-frontend"></a>

## 7. 前端请求、登录状态与页面代码

先搭建登录闭环所需的最小前端，再说明会话版本、登录跳转与菜单同步。个人资料章继续展示完整布局与头像；各功能章说明自己新增的页面与路由。

### 7.1 安装依赖与设置路径别名

在学习副本 `frontend` 目录运行：

```powershell
npm.cmd install axios@1.20.0 element-plus@2.14.6 vue-router@5.3.1 @element-plus/icons-vue --save-exact
```

前面安装过 Axios 的话，可以按实际情况只安装缺少的包。保留 npm 更新的锁文件。

`frontend/vite.config.js`：

```js
import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
```

因此：

```js
import request from "@/utils/request";
```

指向 `src/utils/request.js`。`@` 不是 JavaScript 自动认识的路径，是在这里配置的别名。

### 7.2 应用入口

`frontend/index.html` 的关键结构：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>代码学习示例</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

`frontend/src/main.js`：

```js
import { createApp } from "vue";
import ElementPlus from "element-plus";
import zhCn from "element-plus/es/locale/lang/zh-cn";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router";

createApp(App).use(router).use(ElementPlus, { locale: zhCn }).mount("#app");
```

`frontend/src/App.vue`：

```vue
<template>
  <router-view />
</template>
```

整体关系：

```text
浏览器加载 index.html
  → 加载 main.js
  → 创建 Vue 应用，安装路由和组件库
  → App.vue 挂载到 #app
  → router-view 根据路径显示对应页面
```

### 7.3 浏览器存储工具

`frontend/src/utils/auth.js`：

```js
const TOKEN_KEY = "token";
const USER_KEY = "userInfo";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getUserInfo() {
  const raw = localStorage.getItem(USER_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setUserInfo(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY);
}

export function logout() {
  removeToken();
  removeUserInfo();
}
```

`localStorage` 只能保存字符串，所以用户对象需要：

```text
保存：对象 → JSON.stringify → 字符串
读取：字符串 → JSON.parse → 对象
```

浏览器存储按来源区分。用 `localhost` 登录后再打开 `127.0.0.1`，不一定能读到同一份登录信息。

### 7.4 共享的响应式用户信息

`frontend/src/utils/user.js`：

```js
import { ref } from "vue";
import { getUserInfo, setToken, setUserInfo, logout } from "./auth";

const userInfo = ref(getUserInfo());

export function useUser() {
  function saveLoginData(data) {
    setToken(data.token);
    setUserInfo(data.user);
    userInfo.value = data.user;
  }

  function updateUser(user) {
    setUserInfo(user);
    userInfo.value = user;
  }

  function reloadUser() {
    userInfo.value = getUserInfo();
  }

  return {
    userInfo,
    saveLoginData,
    updateUser,
    reloadUser,
  };
}

export function clearLoginData() {
  logout();
  userInfo.value = null;
}
```

`userInfo` 在函数外定义，因此同一前端应用中，多个组件调用 `useUser()` 得到的是同一个 ref。

`clearLoginData` 是上一节为学习副本添加的函数，确保退出登录时也清空内存中的用户信息。原项目之前读取的 `user.js` 没有这个函数。

只修改 localStorage 不会自动触发 Vue 界面更新；只修改 ref 又不会自动持久保存。以上函数同时完成两项工作。

### 7.5 Axios 请求封装

`frontend/src/utils/request.js`：

```js
import axios from "axios";
import { ElMessage } from "element-plus";

import router from "@/router";
import { getToken } from "@/utils/auth";
import { clearLoginData } from "@/utils/user";

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

function handleUnauthorized(message) {
  ElMessage.error(message || "登录已过期，请重新登录");
  clearLoginData();
  router.replace("/login");
}

service.interceptors.request.use(
  (config) => {
    const token = getToken();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

service.interceptors.response.use(
  (response) => {
    const data = response.data;

    if (data.code === 401) {
      handleUnauthorized(data.message);
      return Promise.reject(data);
    }

    if (data.code !== 200) {
      ElMessage.error(data.message || "请求失败");
    }

    return data;
  },
  (error) => {
    if (error.response) {
      const status = error.response.status;
      const message = error.response.data?.message;

      if (status === 401) {
        handleUnauthorized(message);
      } else {
        ElMessage.error(message || "请求失败");
      }
    } else {
      ElMessage.error("网络异常，请检查后端服务");
    }

    return Promise.reject(error);
  },
);

export default service;
```

`import.meta.env.VITE_API_BASE_URL` 来自前端环境配置，不是后端的 `.env`。Vite 的 `VITE_` 配置会进入前端代码，不能用于存放后端密钥。

请求地址组合：

```text
baseURL：http://127.0.0.1:8001
url：/api/auth/login
最终地址：http://127.0.0.1:8001/api/auth/login
```

页面发请求时的公共流程：

```text
API 函数
  → Axios 实例
  → 请求拦截器
  → HTTP 请求
  → 响应拦截器
  → 页面 await 得到结果，或进入 catch
```

在当前写法中：

- HTTP 200 且 code 200：返回 JSON 内容。
- HTTP 200 且业务 code 非 200、非 401：显示错误，但 Promise 仍然成功，因此页面必须检查 `res.code`。
- HTTP 401 或业务 code 401：清理登录信息、跳转登录、返回拒绝状态的 Promise。
- 其他 HTTP 错误或网络错误：显示错误、返回拒绝状态的 Promise。

### 7.6 请求拦截器：防止旧请求的 401 清除新登录

本次 auth.js 增加了模块内变量 authVersion；setToken、removeToken 每调用一次，就把它加 1。

请求发出时，拦截器记录：

```js
config._authVersion = getAuthVersion();
```

它是客户端这次请求的元信息，保留在 Axios 配置对象中；没有作为认证字段交给后端。Authorization 中的 token 才用于后端认证。

这个机制处理以下时序：

```text
旧会话发起请求 A，记录版本 1
    → 用户重新登录，版本变成 2
    → A 很晚才返回 401
    → 如果直接 logout，就会清掉版本 2 的新登录
```

handleUnauthorized 先比较请求版本与当前版本：

```js
if (config?._authVersion !== getAuthVersion()) return;
const token = getToken();
if (token && config.headers?.Authorization !== `Bearer ${token}`) return;
```

只有错误属于当前这次登录状态，才提示并执行 logout、router.replace('/login')。token 文本相同但已经重新登录时，版本号仍能区分先后两次会话操作。

一次有效注销会增加版本，所以其他同批旧请求的 401 再回来时，不会重复清理和提示。

这里提前 return 只是跳过全局注销处理；响应拦截器仍会 Promise.reject，让原请求表达失败。没有把未授权请求变成业务成功。

authVersion 只存在当前页面的 JavaScript 模块内，刷新会重建，也不是跨标签页共享状态，更不是后端 token 撤销列表。因此它解决的是当前页面异步请求的先后问题。

**复习自测**

| 问题                                              | 核对要点                           |
| ------------------------------------------------- | ---------------------------------- |
| authVersion 能不能让另一台设备上的旧 token 失效？ | 不能，它是当前页面内的请求先后标识 |

### 7.7 前端 API 文件

`frontend/src/api/auth.js`：

```js
import request from "@/utils/request";

export function registerApi(data) {
  return request({
    url: "/api/auth/register",
    method: "post",
    data,
  });
}

export function loginApi(data) {
  return request({
    url: "/api/auth/login",
    method: "post",
    data,
  });
}
```

`frontend/src/api/user.js`：

```js
import request from "@/utils/request";

export function getUserInfoApi() {
  return request({
    url: "/api/user/info",
    method: "get",
  });
}
```

`data` 是对象属性简写，相当于 `data: data`。这个包装函数的 `return` 返回 Promise，具体解释见第 19 节。

### 7.8 注册页

`frontend/src/views/Register.vue`：

```vue
<template>
  <div>
    <h2>注册</h2>

    <el-form ref="formRef" :model="form" :rules="rules">
      <el-form-item prop="username">
        <el-input
          v-model="form.username"
          placeholder="账号"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="密码"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-form-item prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          show-password
          placeholder="确认密码"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-button type="primary" :loading="loadingValue" @click="register">
        注册
      </el-button>
    </el-form>

    <router-link to="/login">已有账号，去登录</router-link>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";

import { registerApi } from "@/api/auth";

const router = useRouter();
const formRef = ref();
const loadingValue = ref(false);

const form = reactive({
  username: "",
  password: "",
  confirmPassword: "",
});

function validateConfirmPassword(rule, value, callback) {
  if (!value) {
    callback(new Error("请再次输入密码"));
  } else if (value !== form.password) {
    callback(new Error("两次密码不一致"));
  } else {
    callback();
  }
}

const rules = {
  username: [
    { required: true, message: "请输入账号", trigger: "blur" },
    { min: 3, max: 50, message: "账号长度为 3～50 个字符", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 6, message: "密码至少 6 个字符", trigger: "blur" },
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: "blur" }],
};

async function register() {
  const valid = await formRef.value.validate().catch(() => false);

  if (!valid) {
    return;
  }

  loadingValue.value = true;

  try {
    const res = await registerApi(form);

    if (res.code === 200) {
      ElMessage.success("注册成功");
      await router.push("/login");
    }
  } catch {
    // request.js 已显示请求错误。
  } finally {
    loadingValue.value = false;
  }
}
</script>
```

重要对应关系：

```text
form.username
  ↔ el-form-item 的 prop="username"
  ↔ rules.username
```

`ref="formRef"` 将表单组件实例放进 ref。`formRef.value.validate()` 调用组件提供的校验方法，校验失败后 `.catch(() => false)` 将结果转为 false。

`trigger: 'blur'` 表示输入框失去焦点时触发相应校验。提交时调用 `validate()` 也会校验整个表单。

前端校验帮助用户及时发现输入问题；后端还必须独立校验，因为请求可以绕过页面发出。

### 7.9 登录页

`frontend/src/views/Login.vue`：

```vue
<template>
  <div>
    <h2>登录</h2>

    <el-form ref="formRef" :model="form" :rules="rules">
      <el-form-item prop="username">
        <el-input
          v-model="form.username"
          placeholder="账号"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="密码"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-button type="primary" :loading="loadingValue" @click="login">
        登录
      </el-button>
    </el-form>

    <router-link to="/register">没有账号，去注册</router-link>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";

import { loginApi } from "@/api/auth";
import { useUser } from "@/utils/user";

const router = useRouter();
const formRef = ref();
const loadingValue = ref(false);
const { saveLoginData } = useUser();

const form = reactive({
  username: "",
  password: "",
});

const rules = {
  username: [{ required: true, message: "请输入账号", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function login() {
  const valid = await formRef.value.validate().catch(() => false);

  if (!valid) {
    return;
  }

  loadingValue.value = true;

  try {
    const res = await loginApi(form);

    if (res.code === 200) {
      saveLoginData(res.data);
      ElMessage.success("登录成功");
      await router.push("/manager/home");
    }
  } catch {
    // request.js 已显示请求错误。
  } finally {
    loadingValue.value = false;
  }
}
</script>
```

`saveLoginData` 接收的是 `res.data`，其中包含 `token` 和 `user`，不是整个 `res`。

### 7.10 首页

`frontend/src/views/Home.vue`：

```vue
<template>
  <div>
    <p v-if="loading">正在获取用户信息……</p>

    <div v-else-if="loadError">
      <p>{{ loadError }}</p>
      <el-button @click="loadUser">重新获取</el-button>
    </div>

    <div v-else-if="userInfo">
      <h3>欢迎你：{{ userInfo.name }}</h3>
      <p>账号：{{ userInfo.username }}</p>
      <p>角色：{{ userInfo.role }}</p>
    </div>

    <el-button :disabled="loading" @click="handleLogout"> 退出登录 </el-button>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { getUserInfoApi } from "@/api/user";
import { useUser, clearLoginData } from "@/utils/user";

const router = useRouter();
const { userInfo, updateUser } = useUser();

const loading = ref(true);
const loadError = ref("");

async function loadUser() {
  loading.value = true;
  loadError.value = "";

  try {
    const res = await getUserInfoApi();

    if (res.code === 200) {
      updateUser(res.data);
    } else {
      loadError.value = res.message || "用户信息获取失败";
    }
  } catch {
    loadError.value = "用户信息获取失败，请重试";
  } finally {
    loading.value = false;
  }
}

async function handleLogout() {
  clearLoginData();
  await router.replace("/login");
}

onMounted(loadUser);
</script>
```

`onMounted(loadUser)` 是注册回调，在组件挂载后调用函数。`onMounted(loadUser())` 会先调用函数，再把它的返回值传进去，含义不同。

首页获取数据期间显示加载状态，成功后才显示用户资料。

### 7.11 最小布局与路由守卫

`frontend/src/layouts/Layout.vue`：

```vue
<template>
  <div>
    <h2>实验室管理系统</h2>
    <router-view />
  </div>
</template>
```

`frontend/src/router/index.js`：

```js
import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "@/utils/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/manager/home",
    },
    {
      path: "/login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      component: () => import("@/views/Register.vue"),
    },
    {
      path: "/manager",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          component: () => import("@/views/Home.vue"),
        },
      ],
    },
  ],
});

router.beforeEach((to) => {
  if (to.path === "/login" || to.path === "/register") {
    return true;
  }

  return getToken() ? true : "/login";
});

export default router;
```

- 外层 App 的 `router-view` 显示 Layout。
- Layout 的 `router-view` 显示子页面 Home。
- 子路径 `home` 与父路径 `/manager` 合成 `/manager/home`。
- `beforeEach` 在导航前执行，返回 true 放行，返回路径进行重定向。
- 这个守卫只检查 token 是否存在；后端验证其真实性和有效期。
- `push` 通常增加历史记录，`replace` 替换当前历史记录。

完整布局与侧栏菜单见第 8.15 节；登录导航、路由实例与当前菜单选中项见本章后面的导航说明。

<a id="17-login-navigation"></a>

### 7.12 登录后地址已改变，页面为什么仍停留在登录页

本次遇到的现象是：提交正确的登录信息后，浏览器地址栏已经变成 `/manager/home`，页面仍显示登录界面；手动刷新后才显示首页。这里要分别检查登录请求、保存登录信息、路由导航和页面渲染，不能仅凭地址栏变化判断首页已经显示。

#### 先理解跳转对象与页面显示的关系

在 `frontend/src/main.js` 中，应用通过 `app.use(router)` 注册路由实例。`<router-view>` 根据这个实例提供的当前路由决定显示哪个组件。

登录页原来这样取得路由：

```js
import router from "@/router";
```

正常情况下，导入的单例与应用注册的是同一个对象，这种写法可以工作。如果模块重新加载或其他初始化方式造成实例不一致，登录处理函数可能操作另一个路由对象，而页面继续使用应用原先注册的实例。此时检查被操作对象的 `currentRoute` 也可能得到首页路径，却不能证明当前应用已经显示首页。

本次隔离测试主动构造了“应用注册一个实例、登录页导入另一个实例”的条件，旧代码中能复现登录处理完成、应用仍显示登录页的情况。**这证明实例不一致能导致这类现象；尚未直接确认真实浏览器中的实例是否确实因热更新而分离。** 如果实际问题仍然存在，应继续查看组件加载和渲染错误。

#### 修改一：Login.vue 使用当前应用注入的路由

在 `frontend/src/views/Login.vue` 的 `<script setup>` 中，移除原来的路由对象导入，改成：

```js
import { useRouter } from "vue-router";

const router = useRouter();
```

`useRouter()` 获取当前应用注入的路由实例。放在页面的 `<script setup>` 顶层调用后，登录函数就使用这个实例进行导航，与页面中的 `<router-view>` 保持一致。这里的“顶层”是组件 setup 的作用域，不是任意普通 JavaScript 模块的顶层。相关用法见 [Vue Router 组合式 API](https://router.vuejs.org/guide/advanced/composition-api.html)。

登录成功后的执行顺序仍是：

```text
loginApi 返回业务 code=200
    → saveLoginData 保存 token、用户信息并更新共享状态
    → 使用当前应用的 router 执行 replace('/manager/home')
    → 当前应用的 router-view 显示 Layout 和 Home
    → 登录函数确认目标路径并显示成功提示
```

`await router.replace(...)` 用于等待导航；真实页面是否成功显示，还需结合渲染结果确认。回归测试因此同时检查路由路径和实际渲染的首页内容。

#### 保留原来的导航结果检查

Login.vue 在保存登录数据后，改成等待 router.replace('/manager/home')。

replace 替换当前浏览历史记录，避免成功登录后浏览器后退马上回到刚才的登录页。随后代码检查实际路径是不是 /manager/home，再显示“登录成功”。

导航 Promise 可能结束但返回导航失败信息，加载路由组件也可能抛错。因此现在分别处理“没有到达首页”和“首页加载失败”。导航失败的行为可查 [Vue Router Navigation Failures](https://router.vuejs.org/guide/advanced/navigation-failures.html)。

保存 token 与导航成功是两个步骤。当前保存先发生，导航失败不会自动回滚已经保存的 token；页面提示用户重试或刷新。

这个变化与本章请求拦截器的会话版本处理配合：旧请求的 401 不再清除新 token；登录函数等待导航并检查目标路径后再提示成功。路径检查仍需结合页面渲染验证。

#### 修改二：Layout.vue 统一导航实例与菜单状态

布局中的个人信息、修改密码和退出登录也需要导航，因此在 `frontend/src/layouts/Layout.vue` 的 `<script setup>` 中使用：

```js
import { useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();
```

二者的职责不同：

| API           | 返回什么             | 本次用途                          |
| ------------- | -------------------- | --------------------------------- |
| `useRouter()` | 当前应用的路由器实例 | 调用 `push`、`replace` 等导航方法 |
| `useRoute()`  | 响应式的当前路由信息 | 读取 `route.path`，设置菜单选中项 |

模板中只保留一个 `default-active` 配置：

```html
<el-menu router :default-active="route.path" style="height: 100%">
  <!-- 保留已有菜单项 -->
</el-menu>
```

原来同时存在动态 `:default-active="router.currentRoute.value.path"` 和固定 `default-active="/manager/home"`。现在移除重复配置，直接让菜单读取当前路径。`route` 是路由对象，读取 `route.path` 即可；原来的 `router.currentRoute` 是 ref，在脚本表达式中需要通过 `.value` 读取。

这项修改负责同步菜单状态，主页面的组件切换由 `<router-view>` 完成。设备浏览页与实验室列表页的菜单路径映射仍是第 11.18 节所述的独立界面需求。

#### 如何验证这次修改

当时新增测试文件为 frontend/tests/login-navigation.test.mjs（2026-10-21 当前工作区无此文件）。它编译真实 Login.vue 的脚本，使用实际 Vue 渲染器和 Vue Router 的内存历史，模拟接口、表单校验、保存登录信息等外部依赖；不访问现有数据库。下面是当时的执行方式，恢复文件后才能复跑这些用例。

`frontend/package.json` 增加了 `"test": "node --test"`。在 `frontend` 目录执行：

```powershell
npm.cmd test
npm.cmd run build
```

6 项测试覆盖：正常登录后显示首页；导入路由与应用实例不一致；表单校验失败不发请求；凭证被拒绝时停留登录页；网络失败后恢复提交状态；连续提交只发送一次请求。修复前，实例不一致的用例失败；修复后 6 项全部通过，前端构建也通过。

真实浏览器验收仍待完成：

- [ ] 从登录页提交正确凭证，确认地址和首页内容一起切换，无需手动刷新。
- [ ] 切换侧栏菜单，确认页面和菜单选中项一致。
- [ ] 退出后重新登录，确认仍能直接显示首页。
- [ ] 输入错误密码，确认停留登录页且可以再次提交。
- [ ] 开发时修改组件触发热更新后再登录，查看是否仍需刷新，并记录控制台错误。

这些隔离测试未运行真实 Vite 热更新，也未访问真实后端，不能据此把浏览器中的具体根因和完整登录流程标记为已验收。

### 7.13 本章修补代码快照（2026-10-20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>frontend/src/utils/auth.js</code></summary>

```js
// 存储token、用户信息, 获取token、用户信息, 删除token、用户信息
const TOKEN_KEY = "token";
const USER_KEY = "userInfo";
let authVersion = 0;

export function getAuthVersion() {
  return authVersion;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
  authVersion++;
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY);
  authVersion++;
}

export function getUserInfo() {
  const str = localStorage.getItem(USER_KEY);
  if (!str) return null;

  try {
    return JSON.parse(str);
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setUserInfo(userInfo) {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo));
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY);
}

// 登出
export function logout() {
  removeToken();
  removeUserInfo();
}
```

</details>

<details>
<summary><code>frontend/src/utils/request.js</code></summary>

```js
import axios from "axios";
import { getAuthVersion, getToken, logout } from "./auth";
import router from "@/router";
import { ElMessage } from "element-plus";

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000, // 30s
});

const handleUnauthorized = (config, message) => {
  // 旧会话的请求失败，不能使重新登录后的会话失效。
  if (config?._authVersion !== getAuthVersion()) return;
  const token = getToken();
  if (token && config.headers?.Authorization !== `Bearer ${token}`) return;
  ElMessage.error(message);
  if (token) {
    logout();
    router.replace("/login");
  }
};

// 请求的拦截器的配置
service.interceptors.request.use(
  (config) => {
    const token = getToken();
    config._authVersion = getAuthVersion();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (err) => Promise.reject(err),
);

// 返回的拦截器配置
service.interceptors.response.use(
  (res) => {
    const data = res.data;
    console.log("response:", res);
    if (data.code === 401) {
      handleUnauthorized(res.config, data.message || "登录已过期，请重新登录");
      return Promise.reject(data);
    }
    if (data.code !== 200) {
      ElMessage.error(data.message || "请求失败");
    }
    return data;
  },
  (err) => {
    if (err.response) {
      const httpStatusCode = err.response.status;
      if (httpStatusCode === 401) {
        handleUnauthorized(
          err.config,
          err.response.data?.message || "登录已过期，请重新登录",
        );
      } else {
        ElMessage.error(err.response.data?.message || "请求失败");
      }
    } else {
      ElMessage.error("网络异常，请检查后端服务");
    }
    return Promise.reject(err);
  },
);

export default service;
```

</details>

<details>
<summary><code>frontend/src/views/Login.vue</code></summary>

```vue
<template>
  <div class="login-container">
    <div class="login-box">
      <h1 style="font-size: 28px">实验室预约系统</h1>
      <div style="margin-top: 5px; margin-bottom: 30px">
        基于Agent智能预约系统
      </div>
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-width="0px"
        style="width: 100%"
        @submit.prevent="login"
      >
        <el-form-item prop="username">
          <el-input
            size="large"
            v-model="form.username"
            placeholder="请输入账号"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            type="password"
            size="large"
            v-model="form.password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <div>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            native-type="submit"
            :loading="loadingValue"
            >登 录</el-button
          >
          <div style="text-align: right; margin-top: 20px; padding-right: 15px">
            还没有账号？请<router-link
              style="color: var(--el-color-primary)"
              to="/register"
              >注册</router-link
            >
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { User, Lock } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { loginApi } from "@/api/auth";
import { useUser } from "@/utils/user";
const router = useRouter();
const { saveLoginData } = useUser();

const formRef = ref();

const rules = {
  username: [
    { required: true, message: "请输入账号", trigger: "blur" },
    // { min: 3, max: 20, message: '账号长度在3到20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    // { min: 6, max: 20, message: '密码长度在6到20个字符之间', trigger: 'blur' }
  ],
};

const form = reactive({
  username: "",
  password: "",
});

const loadingValue = ref(false);

const login = async () => {
  if (loadingValue.value) return;
  loadingValue.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const res = await loginApi(form);
    if (res.code === 200) {
      saveLoginData(res.data);
      try {
        const failure = await router.replace("/manager/home");
        if (router.currentRoute.value.path === "/manager/home") {
          ElMessage.success("登录成功");
        } else {
          console.error("登录后跳转首页未完成:", failure);
          ElMessage.error("首页跳转未完成，请重试");
        }
      } catch (error) {
        console.error("登录后加载首页失败:", error);
        ElMessage.error("首页加载失败，请刷新页面后重试");
      }
    }
  } catch {
    // 登录请求失败时由请求拦截器提示错误。
  } finally {
    loadingValue.value = false;
  }
};
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.login-box {
  width: 380px;
  border-radius: 8px;
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  text-align: center;
}
</style>
```

</details>

<a id="12-profile"></a>

## 8. 个人资料、头像上传与开发代理

阶段起点：2026-10-12。先讲个人资料从查询、填表到保存的完整过程，再讲头像上传、静态访问和代理。早期快照用于学习演进；用户管理章说明后续接口与字段权限调整。

### 8.1 个人资料与头像功能的整体设计

本次功能包含三个动作：

1. **查询资料**：进入 Profile 页面，后端根据 token 找到当前用户，把信息填入表单。
2. **上传头像**：浏览器上传图片，后端保存文件，返回图片访问地址，表单显示预览。
3. **保存资料**：把名称、邮箱、手机号和头像地址提交给后端，更新用户记录，再同步前端共享状态。

头像处理分两步：

```text
上传图片：图片内容 → backend/uploads 中的文件
保存资料：图片 URL → 数据库 users.avatar 字段
```

头像字段保存的是地址字符串，不是图片二进制。上传成功后如果没有保存资料，数据库中的头像仍是旧值。

### 8.2 文件职责与调用关系

| 文件                                 | 本次职责                                              |
| ------------------------------------ | ----------------------------------------------------- |
| backend/app/services/user_service.py | 把输入模型转换成字段和值，修改用户对象并提交数据库    |
| backend/app/schemas/user.py          | 定义用户返回结构和允许修改的字段，返回结构加入 avatar |
| backend/app/schemas/files.py         | 定义上传文件返回的名称、大小和访问地址                |
| backend/app/api/user.py              | 注册 GET 查询和 PUT 修改接口，取得当前登录用户        |
| backend/app/api/files.py             | 检查文件并保存到磁盘，返回 FileResponse               |
| frontend/src/api/user.js             | 封装查询和修改个人资料的 HTTP 请求                    |
| frontend/src/api/files.js            | 使用 FormData 封装文件上传请求                        |
| frontend/src/views/Profile.vue       | 显示资料、校验输入、上传头像、保存修改                |
| frontend/src/layouts/Layout.vue      | 显示共享的昵称与头像，提供个人信息入口                |
| frontend/src/router/index.js         | 将 /manager/profile 映射到 Profile.vue                |
| frontend/.env.development            | API baseURL 改为留空，使用相对地址                    |
| frontend/vite.config.js              | 开发时将 /api 和 /uploads 转发到后端                  |

还需要联动理解已有的 `request.js`、`utils/user.js`、`utils/auth.js`、`dependencies/auth.py`、`models/user.py`、`main.py` 和 `config.py`。

本次涉及的地址：

| 操作         | 地址                  | 方法 | 内容                       |
| ------------ | --------------------- | ---- | -------------------------- |
| 查询本人资料 | /api/user/info        | GET  | 请求头携带 token           |
| 修改本人资料 | /api/user/update      | PUT  | JSON 对象                  |
| 上传文件     | /api/files/upload     | POST | multipart/form-data        |
| 读取头像图片 | /uploads/生成的文件名 | GET  | 浏览器根据 img 的 src 请求 |

### 8.3 查询资料：从导航到填充表单

#### 第一步：点击个人信息

Layout 中：

```js
const goPerson = () => {
  router.push("/manager/profile");
};
```

这里发生的是前端页面导航，尚未调用查询用户接口。

路由中：

```js
{
  path: 'profile',
  name: 'Profile',
  component: () => import('@/views/Profile.vue')
}
```

父路径是 `/manager`，因此完整路径是 `/manager/profile`。`name` 是路由的名字，不是请求方法或后端接口名称。

`component: () => import(...)` 是按需加载组件。外层 App 的 router-view 显示 Layout，Layout 内部的 router-view 显示 Profile。

#### 第二步：组件挂载时查询

Profile 中：

```js
onMounted(() => {
  loadUserInfo();
});
```

组件挂载后，回调调用 `loadUserInfo`。函数设置：

```js
loading.value = true;
```

表单上的 `v-loading="loading"` 使用 Element Plus 的加载指令显示遮罩。finally 把 loading 恢复为 false，成功失败都会结束加载状态。

#### 第三步：前端 API 发请求

当前 `frontend/src/api/user.js` 的查询函数名是 `getUserInfo`：

```js
export function getUserInfo() {
  return request({
    url: "/api/user/info",
    method: "get",
  });
}
```

它与 `utils/auth.js` 中同名函数的职责不同：

| 函数来源                    | 实际动作                                      |
| --------------------------- | --------------------------------------------- |
| @/api/user 的 getUserInfo   | 发 HTTP 请求，得到 Promise                    |
| @/utils/auth 的 getUserInfo | 从 localStorage 读取缓存，直接返回对象或 null |

看调用时要看 import 的路径，不能只看函数名字。同一个文件需要使用两者时，可以通过 `as` 给其中一个导入起别名。

`request.js` 会添加 Authorization，并将 Axios 原始响应中的 data 返回给页面。所以：

```js
const res = await getUserInfo();
```

这里的 res 是包含 code、message、data 的后端 JSON 内容。

#### 第四步：后端通过 token 查出用户

当前接口：

```python
@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    return Response.success(
        data=UserResponse.model_validate(current_user)
    )
```

数据库查询发生在已有的 `get_current_user` 依赖中。接口不需要再从前端接收用户 ID。

注意当前调用关系：`user_service.py` 虽然定义了 `get_user_info(user)`，但是这个 GET 接口直接调用 `UserResponse.model_validate`，没有调用该服务函数。这是代码中目前存在的两种组织方式，不能把“定义了函数”理解成“接口必定使用它”。

#### 第五步：Object.assign 填入响应式表单

```js
if (res.code === 200) {
  Object.assign(form, res.data);
}
```

例如原表单为：

```js
{
  username: '',
  name: '',
  role: '',
  email: '',
  phone: '',
  avatar: ''
}
```

响应里的同名字段会覆盖这些值。Object.assign 是把源对象的属性复制到目标对象，也会加入目标原本没有的字段。

这里的目标是已经通过 reactive 创建的 form。修改其属性会更新表单显示，并保留原来的响应式对象。

后端响应还包含 id 和 status；Object.assign 也会把它们加到 form。它们不一定显示在输入框中，但之后直接提交整个 form 时会一起进入请求体。

### 8.4 UserResponse：让接口返回头像

当前返回模型新增：

```python
avatar: str | None = None
```

含义：

- 可以是头像地址字符串。
- 可以是 None，表示没有头像。
- 没有提供该字段时，默认使用 None。

`model_config = ConfigDict(from_attributes=True)` 允许从数据库 User 对象的属性中提取头像等字段。

因此：

```python
UserResponse.model_validate(current_user)
```

可以得到带 avatar 的用户返回对象。

登录服务也使用这个 UserResponse 模型，所以该模型变化还会影响登录接口中的 user 返回结构。

数据库 User 模型已经声明了 `avatar: String(255)`。schema 加入字段与修改数据库表结构是不同的事：是否需要迁移，要看真实表里是否已有该列，不能认为修改 Pydantic schema 会自动修改表。

### 8.5 UserUpdateRequest：定义允许修改的范围

> 历史版本提示：下面是 2026-10-12 的字段范围。2026-10-14 的共享模型加入 role/status 后曾引入权限问题；2026-10-15 本人服务已排除这两个字段。问题与实际修正见第 9.2 节和第 9.3 节。

你新增的请求模型：

```python
class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
```

它只声明名称、邮箱、手机号和头像。这些字段都有默认值，因此请求可以不提供某个字段。

当前没有声明：

```text
id、username、role、status、password
```

Pydantic BaseModel 的默认行为是忽略未声明的额外字段。前端虽然提交整个 form，后端不会把其中的 role、username、id 等加入这个请求模型的输出字典。

这是更新字段的范围控制。前端 disabled 输入框只是交互限制，后端输入模型才决定当前服务函数会处理哪些字段。

模型目前只检查“字符串或 None”等基本类型，没有设置邮箱格式、手机号模式或数据库字段长度限制。前端校验并不等于已经具备这些后端校验。

### 8.6 PUT 修改接口与 Depends

当前 API：

```python
@router.put("/update")
def update_user_info(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = user_service.update_user_info(db, current_user, data)
    return Response.success(data=res)
```

三个参数分别来自：

| 参数         | 来源                                   |
| ------------ | -------------------------------------- |
| data         | JSON 请求体，经 UserUpdateRequest 校验 |
| current_user | 身份依赖验证 token 后查询到的用户      |
| db           | 数据库会话依赖                         |

前端不能通过提交其他用户 ID 指定要修改谁。当前修改对象由身份依赖确定。

get_current_user 内部也依赖 get_db。FastAPI 在同一次请求中默认缓存依赖结果，因此这里两处使用同一个 get_db 时通常得到同一个会话。当前用户是该会话已经查询并管理的对象，可以直接修改其属性后提交。[FastAPI 子依赖与缓存](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)

本接口使用 PUT，但实现方式是“只修改部分提供了非 None 值的字段”。从行为上看属于部分更新；HTTP 方法本身不会自动产生数据库修改。

### 8.7 核心：model_dump、items、setattr、commit

你的业务函数：

```python
def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(exclude_none=True)
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
```

#### 1. model_dump(exclude_none=True)

model_dump 把 Pydantic 模型转换成字典。exclude_none=True 表示排除值为 None 的字段。

例如请求只给出：

```json
{
  "name": "学习用户",
  "email": null
}
```

转换结果是：

```python
{"name": "学习用户"}
```

email 是 None 被排除；没有提供的 phone、avatar 使用默认 None，也被排除。

具体行为：

| 请求内容           | 更新字典       | 对邮箱的影响 |
| ------------------ | -------------- | ------------ |
| 没有 email         | 不包含 email   | 保持原值     |
| email 为 null      | 不包含 email   | 保持原值     |
| email 为 ""        | 包含 email: "" | 保存空字符串 |
| email 为有效字符串 | 包含该字符串   | 保存新值     |

**因此，当前代码不能通过 email: null 把已有邮箱清空为 SQL NULL。**

空字符串不是 None，exclude_none 不会排除它。

如果将来需要区分“不提供”和“明确清空”，可以考虑 exclude_unset=True，并为 name 等不可为空的字段设置独立规则。这是后续设计调整，不是本次已实施行为。[Pydantic 字段排除规则](https://docs.pydantic.dev/latest/concepts/serialization/)

#### 2. user_dict.items()

字典的 items() 提供键和值组成的配对：

```python
{
    "name": "学习用户",
    "phone": "13912345678",
}
```

循环中会依次取到：

```text
field = "name"，value = "学习用户"
field = "phone"，value = "13912345678"
```

`for field, value in ...` 使用解包，将每一组的两个元素分别赋给两个变量。

#### 3. setattr(user, field, value)

setattr 是 Python 内置函数，根据属性名字符串设置对象属性。

```python
setattr(user, "name", "学习用户")
```

相当于：

```python
user.name = "学习用户"
```

这样不必给每个可编辑字段都写一个单独赋值语句。当前字典来自限定字段的 UserUpdateRequest；不要把任意未经限制的原始请求字典直接用于修改用户对象。

#### 4. 为什么这里没有 db.add(user)

current_user 是数据库会话已经查询出来的 ORM 对象。SQLAlchemy 会跟踪它的属性变化，commit 时可以保存这些改动。

db.add 常用于把新建对象交给会话。这里操作的是已经由会话管理的记录。

#### 5. commit、refresh、model_validate

```text
setattr：修改内存对象
  → db.commit：提交数据库事务
  → db.refresh：重新读取数据库中的字段
  → model_validate：整理成用户返回模型
```

refresh 可读到更新后的时间等数据库记录值。它不是“提交”；把两个步骤分开理解。

当前服务函数没有显式的 try/rollback。如果提交失败会走异常处理，get_db 最后会关闭会话；若要在同一会话中捕获失败并继续使用它，需要明确处理回滚。这里没有自动为你改写事务逻辑。

### 8.8 前端保存资料与同步页头

提交函数先校验：

```js
const valid = await formRef.value.validate().catch(() => false);
if (!valid) return;
```

校验规则：

- 名称必填。
- 邮箱使用组件库的 email 类型规则。
- 手机号使用手机号格式的正则表达式。

正则 `/^1[3-9]\d{9}$/` 中：

| 片段  | 含义                     |
| ----- | ------------------------ |
| ^     | 从字符串开头匹配         |
| 1     | 第一个字符为 1           |
| [3-9] | 第二个字符为 3～9 的数字 |
| \d{9} | 后面跟 9 个数字          |
| $     | 匹配到字符串末尾         |

它是格式校验，不是号码存在性验证。

通过校验后：

```js
submitting.value = true;

try {
  const res = await updateUserInfo(form);

  if (res.code === 200) {
    updateUser(res.data);
    ElMessage.success("更新成功");
  }
} finally {
  submitting.value = false;
}
```

当前实际函数还有 catch，错误提示由 request.js 统一显示。

API 包装中的 method 是 put，data 是 form：

```js
return request({
  url: "/api/user/update",
  method: "put",
  data,
});
```

成功后为什么需要 updateUser(res.data)？

```text
数据库已更新
  → 后端返回保存后的资料
  → updateUser 写入 localStorage
  → 修改共享 ref：userInfo.value
  → Layout 昵称和头像更新
```

只更新数据库不会自动修改浏览器已经显示的状态。返回保存后的资料，再更新前端共享状态，完成两边同步。

注意命名：

| 名称             | 所在位置     | 作用                   |
| ---------------- | ------------ | ---------------------- |
| updateUserInfo   | @/api/user   | 发请求，保存到后端     |
| update_user_info | 后端服务     | 修改 ORM 对象并提交    |
| updateUser       | @/utils/user | 更新前端缓存和共享状态 |

当前 loadUserInfo 只执行 Object.assign(form, res.data)，不会同步共享 userInfo。因此，查询到新资料会更新 Profile 表单；页头共享资料在当前写法中主要通过登录和保存成功后更新。

### 8.9 ref、reactive、computed 与页面状态

| 变量       | 类型     | 用途                              |
| ---------- | -------- | --------------------------------- |
| loading    | ref      | 控制查询过程的加载遮罩            |
| submitting | ref      | 控制保存按钮的加载状态            |
| formRef    | ref      | 存放表单组件实例，以调用 validate |
| form       | reactive | 保存当前编辑的资料                |
| roleLabel  | computed | 把角色代码映射成显示文字          |
| userInfo   | 共享 ref | 保存布局等组件使用的用户状态      |

form 和共享 userInfo 是两份不同用途的数据：form 保存未提交的编辑内容，userInfo 保存共享的用户资料。修改表单不会立即改变页头；保存成功调用 updateUser 后再同步。

你的计算属性：

```js
const roleLabel = computed(() => {
  return form.role === "admin"
    ? "管理员"
    : form.role === "student"
      ? "学生"
      : "未知角色";
});
```

computed 根据依赖计算结果，form.role 改变时它会更新。三元表达式的形式是：

```text
条件 ? 条件成立时的值 : 条件不成立时的值
```

这里只定义了 getter，所以 roleLabel 是只读计算属性。账号和角色输入框被 disabled，用户无法在页面中编辑。只用于显示时，可以用 :model-value="roleLabel" 表达这一意图，避免使用需要写回的 v-model。[Vue 计算属性](https://vuejs.org/guide/essentials/computed.html)

### 8.10 Profile 的头像上传组件

主要配置：

```html
<el-upload
  :http-request="handleFileUpload"
  :show-file-list="false"
  accept="image/jpeg,image/png,image/gif,image/webp"
  :on-success="handleAvatarSuccess"
  :before-upload="beforeAvatarUpload"
>
  <!-- 当前头像或加号图标 -->
</el-upload>
```

这里的冒号是 v-bind 的简写，传入变量、函数或布尔值。

| 配置                 | 当前含义                             |
| -------------------- | ------------------------------------ |
| http-request         | 使用自定义函数发上传请求             |
| show-file-list=false | 不显示默认文件列表                   |
| accept               | 文件选择器的类型提示                 |
| before-upload        | 上传前检查文件                       |
| on-success           | 上传成功时的回调，目前绑定名称未定义 |

http-request 是组件的一个函数属性，不是后端路由，也不是 Vue 的路由导航。[Element Plus 上传组件](https://element-plus.org/en-US/component/upload.html)

Profile 模板中的 Plus 没有在该页面单独 import，但 main.js 通过遍历 ElementPlusIconsVue 全局注册图标，因此当前项目可以使用它。若迁移到前面没有全局注册的学习副本，则需要显式导入 Plus 或采用同样的注册方式。

#### 上传前检查

```js
const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
```

file.type 是浏览器提供的 MIME 类型，file.size 是字节数。

```js
if (!imageTypes.includes(file.type)) {
  return false;
}

if (file.size / 1024 / 1024 > 2) {
  return false;
}

return true;
```

includes 判断数组是否包含某值。两次除以 1024 把字节换算成此处采用的 MB 量级。

before-upload 返回 false 会阻止这次上传。当前限制是图片且不超过 2 × 1024 × 1024 字节。

accept 是选择提示，before-upload 是前端检查；它们不会自动把同样的规则传给后端。

#### 自定义上传函数的参数

当前写法：

```js
const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);

    if (res.code === 200) {
      form.avatar = res.data?.url;
    }
  } catch {}
};
```

`({ file })` 是对参数对象的解构。组件传入的是一个包含 file 等属性的对象，函数直接取出 file。

它相当于：

```js
const handleFileUpload = async (options) => {
  const file = options.file;
  // 使用 file 上传
};
```

上传完成后 form.avatar 变为后端地址，v-if 和 img 的 :src 随着响应式属性变化而更新。此时只是更新表单预览，尚未保存用户记录。

### 8.11 files.js：FormData 上传二进制文件

当前函数：

```js
export function uploadFileApi(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request({
    url: "/api/files/upload",
    method: "post",
    data: formData,
    headers: { "Content-Type": "multipart/form-data" },
  });
}
```

JSON 适合传递名称、邮箱等普通字段；FormData 可以携带文件内容和普通表单项。

append 的第一个参数 `'file'` 是表单字段名，它与后端接收参数名 file 对应：

```text
formData.append('file', 浏览器文件对象)
  ↔ 后端 file: UploadFile = File(...)
```

它不等于文件的原始名字。即使原文件叫“头像.png”，表单字段名仍然是 file。

multipart/form-data 用分隔边界 boundary 组织不同表单项。浏览器发送 FormData 时应生成带 boundary 的 Content-Type；不要自行拼接不完整的 boundary。

本次检查到的 Axios 浏览器实现会在 FormData 场景中把 Content-Type 留给浏览器处理，所以不能仅凭这里手写了 multipart/form-data 就断言当前上传一定失败。通常可以交由 Axios/浏览器生成该请求头。[MDN FormData 说明](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest_API/Using_FormData_Objects)

request.js 的 token 与响应拦截器也会作用于这次请求，组件不需要再建立一套独立的 Axios 实例。

### 8.12 后端 files.py：接收并保存文件

#### 接收参数

```python
@router.post("/upload")
def upload(file: UploadFile = File(...)):
    ...
```

- UploadFile 表示 FastAPI 接收的上传文件。
- File(...) 告诉框架这个参数来自文件表单。
- 此处的 ... 表示参数必需，由 FastAPI/Pydantic 识别；不是“后端函数尚未写完”的意思。
- file.filename 是上传时提供的文件名。
- file.file 是框架准备的文件对象，可供读取。
- 常规 multipart 解析会统计 file.size。

文件请求需要 python-multipart。本次检查发现当前虚拟环境已安装 0.0.32，但 backend/requirements.txt 尚未列出它，因此新建环境不能只凭现有依赖清单保证上传可用。[FastAPI 文件请求](https://fastapi.tiangolo.com/tutorial/request-files/)

#### 文件名与扩展名

```python
original_name = os.path.basename(file.filename)
ext = Path(original_name).suffix.lower()
```

basename 取最后的文件名部分，suffix 取扩展名，lower 转为小写。

例如：

```text
原始名称：头像.PNG
扩展名：.png
```

之后与 ALLOWED_EXTENSIONS 比较。

#### 后端大小规则

```python
if file.size and file.size > MAX_FILE_SIZE:
    ...
```

当前 MAX_FILE_SIZE 为 100 × 1024 × 1024 字节。

file.size 为 None 或 0 时，and 左侧为假，不会继续比较。正常上传有统计出的大小。当前代码也没有单独拒绝空文件。

当前规则分属不同用途：

| 位置             | 类型规则                                 | 大小规则 |
| ---------------- | ---------------------------------------- | -------- |
| Profile 头像组件 | JPEG、PNG、GIF、WebP 的 MIME 类型        | 2 MB     |
| 通用后端上传接口 | 配置的扩展名，包括图片、PDF、Office、ZIP | 100 MB   |

后端没有自动继承前端“头像必须为图片且小于 2 MB”的规则。是否另设头像专用约束，需要按功能需求进一步决定。

#### 生成磁盘名字

```python
disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"
```

组成部分：

- time.time()：当前时间戳，乘 1000 后取整数得到毫秒量级。
- uuid.uuid4().hex[:8]：取随机 UUID 的前 8 个十六进制字符。
- ext：保留文件后缀。

这样的名字用于降低重名概率。original_name 保存供展示的名字，disk_name 是实际落盘的名字，两者可以不同。

#### 保存到目录

```python
save_path = UPLOAD_DIR / disk_name

with open(save_path, "wb") as f:
    shutil.copyfileobj(file.file, f)
```

- 对 Path 对象使用 /，表示路径拼接。
- wb 表示写入二进制文件。
- with 在代码块结束时关闭目标文件。
- copyfileobj 从源文件对象逐块复制内容。

这是从框架提供的临时文件向目标文件复制，不是把图片内容作为 JSON 保存，也不等于应用自己直接处理网络字节流。

### 8.13 FileResponse 与头像访问地址

新模型：

```python
class FileResponse(BaseModel):
    original_name: str
    disk_name: str
    size: int
    url: str
```

上传接口返回：

```python
Response.success(
    data=FileResponse(
        original_name=original_name,
        disk_name=disk_name,
        size=file.size,
        url=f"/uploads/{disk_name}",
    )
)
```

例如：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "original_name": "头像.png",
    "disk_name": "示例时间戳_随机串.png",
    "size": 10240,
    "url": "/uploads/示例时间戳_随机串.png"
  }
}
```

size 的模型类型为 int，接口依赖常规上传解析提供数值大小；若将来使用其他来源可能得到 None，需要明确处理，不能认为 int 会自动补出实际文件大小。

区分三个位置：

| 内容     | 例子                               | 谁使用       |
| -------- | ---------------------------------- | ------------ |
| 磁盘路径 | backend/uploads/生成的文件名.png   | 后端文件系统 |
| URL 路径 | /uploads/生成的文件名.png          | 浏览器       |
| 用户字段 | users.avatar 中保存上述 URL 字符串 | 用户信息接口 |

已有 main.py 的挂载：

```python
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads",
)
```

使浏览器能够通过 /uploads 路径读取目录里的文件。name 是挂载的名字，不是磁盘子目录名。

浏览器看到 img 的 src 后会独立发起图片 GET 请求，这个请求不经过 request.js 的 Axios 拦截器。

### 8.14 .env 留空与 Vite 代理为什么配合使用

以前学习副本的配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

这次原项目变为：

```env
VITE_API_BASE_URL=
```

它表示 Axios 的 baseURL 为留空的字符串。以 / 开头的 API 路径会向当前页面的来源发请求，并不是“没有后端”或“请求地址为空”。

以当前前端运行在 http://localhost:5173 为例：

```text
浏览器访问：http://localhost:5173/api/user/info
                    ↓ Vite /api 代理
后端接收：http://127.0.0.1:8000/api/user/info
```

头像同理：

```text
img src="/uploads/xxx.png"
  → 浏览器访问 http://localhost:5173/uploads/xxx.png
  → Vite /uploads 代理
  → 后端 http://127.0.0.1:8000/uploads/xxx.png
  → StaticFiles 返回图片
```

你的代理配置没有 rewrite，所以路径前缀 /api 和 /uploads 会保留，不会被删除。

changeOrigin 主要调整代理发往目标服务的 Host 请求头，不改变浏览器地址栏，也不会把用户浏览器直接切换到后端。

这样，浏览器侧向自己的前端来源发送请求，开发服务器再转发到后端；这条代理请求链不会触发浏览器直接跨来源访问后端的同一套 CORS 检查。[Vite 开发代理](https://vite.dev/config/server-options.html#server-proxy)

重要区别：

- /api 代理解决 API 请求转发。
- /uploads 代理解决相对图片地址的访问。
- 只代理 /api，头像相对地址可能仍无法访问。
- 如果使用绝对后端 baseURL，API 会直接请求后端，开发代理可能不再参与。
- server.proxy 属于开发服务器配置；发布构建后的静态站点时，需要相应的服务器代理或地址配置。
- import.meta.env.BASE_URL 是 Vite 应用的基础路径，与自定义 VITE_API_BASE_URL 不是同一个变量。

迁移到前面的学习副本时，如果后端继续使用 8001，代理 target 也应相应改为 8001。原项目当前配置是 8000，不要混用。

### 8.15 Layout、菜单、插槽与头像显示

Layout 结构：

```text
el-container
  ├─ el-header：标志、名称、用户头像、下拉菜单
  └─ el-container
      ├─ el-aside：导航菜单
      └─ el-main：router-view 显示子页面
```

#### 为什么保存后页头会更新

```js
const { userInfo } = useUser();
```

Layout 与 Profile 保存成功后调用的 updateUser 使用同一模块中的共享 ref。

模板：

```html
<img :src="userInfo?.avatar" />
<div>{{ userInfo?.name || userInfo?.username || '用户' }}</div>
```

可选链防止尚无用户信息时直接访问属性报错。|| 从左到右选择第一个真值；昵称为空时尝试账号，再显示“用户”。

头像没有配置占位图片逻辑，avatar 缺失时的视觉表现仍需要在实际页面检查。

#### el-menu 的 router 属性

```html
<el-menu router default-active="/manager/home">
  <el-menu-item index="/manager/home">系统首页</el-menu-item>
</el-menu>
```

router 开启菜单的路由导航行为。index 对应要访问的路由路径，不是后台接口地址。

当前 default-active 固定为首页，不是与当前路径实时绑定的值；通过下拉入口进入 profile 时，菜单高亮是否符合期望需要另行检查或调整。

Lab.vue、Equ.vue、User.vue 在本次读取时仍只有相应的占位文字；它们出现在菜单里，不等于完整管理功能已经实现。Profile 是独立的个人资料页面。

#### #header 和 #dropdown

```html
<template #header>
  <!-- el-card 的标题区域 -->
</template>

<template #dropdown>
  <!-- el-dropdown 的下拉菜单区域 -->
</template>
```

`#` 是 `v-slot` 的简写。这些是组件提供的具名插槽，允许你把内容放到指定区域；与 URL 的 `#` 锚点无关。

#### scoped 与普通样式

Profile 中第一个 style 使用 scoped，主要约束本组件样式。第二个普通 style 可以匹配组件库生成的内部 .el-upload 等元素，同时也可能影响其他使用相同类名的区域。

这里不是两个独立页面的样式文件，而是同一个 Vue 单文件组件中的两组样式规则。

### 8.16 当前代码中需要单独注意的点

本节讲解与检查只修改笔记，没有自动修复下面的业务源码。

| 当前事实                                                            | 影响或下一步                                                                     |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Profile 绑定 handleAvatarSuccess，但脚本没有定义                    | 可能产生运行时警告；当前预览由 handleFileUpload 更新，应删除多余绑定或补齐回调   |
| 自定义上传函数 catch 为空，成功时也没有 return res                  | 组件得到的 Promise 可能以 undefined 成功完成；失败被吞掉后，组件也可能按成功处理 |
| request.js 对一般业务 code 非 200 仍返回成功 Promise                | 上传组件不能只依赖 Promise 是否成功，还需明确处理业务 code                       |
| 上传过程中没有单独的 uploading 状态                                 | 可能在文件上传未完成时保存，提交旧头像地址                                       |
| UserUpdateRequest 没有格式和长度规则                                | 邮箱、手机号和最大长度不能仅靠页面校验保证                                       |
| exclude_none=True 排除显式 null                                     | 当前不能通过 null 清空已有可空字段，需要确认是否符合交互设计                     |
| Profile 查询只更新 form                                             | 不会把重新查询到的资料同步到页头共享状态                                         |
| 当前 Layout 退出只调用存储 logout                                   | shared userInfo 没有直接清空；此前学习副本的 clearLoginData 尚未加入当前原项目   |
| 通用上传接口没有身份依赖                                            | 当前可以不经登录验证调用，是否加登录限制需要按需求决定                           |
| 服务中 get_user_info 定义后未被 GET API 调用                        | 可统一分层写法，但当前查询路径仍可以工作                                         |
| requirements 未列 python-multipart，package.json 未直接列 icons-vue | 当前环境已装不代表新环境能按清单稳定复现，需要补齐依赖声明                       |

#### 上传 Promise 为什么需要关注

本次检查了本地 Element Plus 上传组件实现：自定义请求返回 Promise 时，组件会把成功分支交给 onSuccess，把拒绝分支交给 onError。

```text
async 上传函数返回 Promise
  → 成功 resolve：组件标记成功
  → 失败 reject：组件标记失败
```

空 catch 捕获错误后，async 函数正常结束，相当于返回一个以 undefined 成功完成的 Promise。

这与“页面请求函数吞掉异常以避免重复提示”不是同一种调用场景：上传组件需要根据 Promise 状态管理文件状态。

以下只是参考调整，尚未写入源码：

```js
const handleFileUpload = async ({ file }) => {
  const res = await uploadFileApi(file);

  if (res.code !== 200 || !res.data?.url) {
    throw new Error(res.message || "上传失败");
  }

  form.avatar = res.data.url;
  return res;
};
```

让请求失败继续拒绝，并明确拒绝业务失败；成功时给组件返回响应内容。预览已经在该函数中更新时，可以移除不存在的 on-success 绑定。

如果选择保留 on-success 回调，应定义对应函数，并明确由哪个位置负责更新预览，避免重复处理。

### 8.17 本次验证记录与实际运行检查

#### 已经完成的检查

- 5 个相关后端 Python 文件通过编译语法检查。
- Profile.vue 和 Layout.vue 通过 Vue 脚本与模板编译。
- files.js、user.js、router/index.js、vite.config.js 通过 Node.js 语法检查。
- 使用内存 SQLite 和原服务函数的实际代码验证提交、刷新和返回结构。
- 确认不传字段与显式 None 被跳过，空字符串被保存。
- 确认额外 role、username、id 不进入更新字典，角色没有改变。
- 确认 avatar 出现在用户响应中，password 不出现在该响应中。
- 确认 handleAvatarSuccess 当前没有定义。
- 确认 main.js 全局注册图标，因此 Plus 的使用有对应来源。

隔离数据库验证没有导入真实数据库配置，也没有修改真实用户记录。Vue 编译通过不表示没有运行时绑定或交互问题，未定义回调就是需要额外阅读发现的例子。

本次读取到的环境：

| 依赖                    | 当前安装版本 |
| ----------------------- | ------------ |
| FastAPI                 | 0.115.13     |
| Pydantic                | 2.13.5       |
| SQLAlchemy              | 2.0.41       |
| python-multipart        | 0.0.32       |
| @element-plus/icons-vue | 2.3.2        |

这些是本机记录，不是已经更新的依赖清单。

#### 浏览器检查清单

- [ ] 登录后从下拉菜单进入 /manager/profile。
- [ ] 页面自动发出 GET /api/user/info 并填充资料。
- [ ] 账号和角色不可在页面输入修改。
- [ ] 修改名称、邮箱、手机号后，检查 PUT 请求的 JSON。
- [ ] 保存成功后，数据库记录和页头名称一致。
- [ ] 重新进入或刷新页面，已保存资料仍然存在。
- [ ] 图片上传请求的表单字段名为 file。
- [ ] 图片上传后表单显示预览，/uploads 请求返回图片。
- [ ] 上传图片后不保存，重新进入页面仍使用旧头像。
- [ ] 上传并保存后，重新进入页面显示新头像。
- [ ] 检查超过 2 MB、类型不允许、网络失败等上传场景。
- [ ] 检查上传失败时组件状态是否仍错误显示成功。
- [ ] 验证空字符串和 null 的清空行为符合需求。
- [ ] 检查保存过程中按钮状态，上传过程中提前保存的行为。
- [ ] 退出后，浏览器存储与共享资料都处于预期状态。
- [ ] 在没有 token 时检查资料接口被拒绝，并确认通用上传接口的访问要求。

Network 面板中的 API Request URL 可能显示前端 5173，这是使用开发代理的正常表现；不要仅凭端口认为请求没有到后端。

### 8.18 从前面学习副本继续复现这一功能

按依赖关系逐步加入：

1. UserResponse 增加 avatar，增加 UserUpdateRequest。
2. 新增 user_service.py 的更新逻辑。
3. 用户 API 增加 PUT /update，并保留 GET /info。
4. 增加 FileResponse 和上传 API，挂入 api 路由。
5. 在 config 中准备上传目录和规则，在 main 中挂载 /uploads。
6. 补齐 multipart 上传依赖；图标依赖直接写入前端依赖清单。
7. 增加前端 api/user.js 的更新函数与 api/files.js。
8. 增加 Profile.vue 和 /manager/profile 子路由。
9. Layout 引用共享 userInfo，加入个人信息入口。
10. 根据运行端口配置 baseURL 或开发代理，并核对 /uploads。
11. 处理第 8.16 节中的已知问题，再完成第 8.17 节的交互检查。

迁移时注意：

- 前面笔记使用 getUserInfoApi，本次原项目使用 getUserInfo，导入和调用要一致。
- 前面笔记使用 clearLoginData，本次原项目的 utils/user.js 尚未导出它。
- 前面学习副本端口为 8001/5174，本次原项目代理目标为 8000。
- schemas 的字段增加不会自动迁移旧数据库表。
- 保存旧头像替换记录，不会自动删除以前上传的磁盘文件；旧文件处理尚未实现。

不要把不同阶段的文件片段直接拼接后就认为已经完成复现，最后仍需检查实际调用名称和依赖。

### 8.19 本节复习练习

1. 不看代码，说明“上传头像”和“保存头像地址”的区别。
2. 解释为什么数据库没有变化时，表单也能先显示新头像。
3. 写出 setattr(user, "phone", value) 等价的直接赋值。
4. 对比不传 email、email 为 null、email 为 "" 三种结果。
5. 说明 form 为什么会包含模板中没有输入框的 id 和 status。
6. 解释直接提交 form 时，role 为什么不会被更新服务处理。
7. 描述保存成功后，Layout 如何得到新的名称和头像。
8. 说明 /uploads 为什么也需要代理，而不能只代理 /api。
9. 解释 async 上传函数的空 catch 如何改变组件看到的结果。
10. 指出当前哪些检查已经完成，哪些必须通过浏览器运行确认。

### 8.20 补充参考

- [Pydantic 字段排除：exclude_none、exclude_unset](https://docs.pydantic.dev/latest/concepts/serialization/)
- [FastAPI 同请求的子依赖缓存](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)
- [FastAPI 文件上传](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Vue 计算属性](https://vuejs.org/guide/essentials/computed.html)
- [Element Plus Upload 参数与回调](https://element-plus.org/en-US/component/upload.html)
- [Vite 开发代理](https://vite.dev/config/server-options.html#server-proxy)
- [MDN FormData](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest_API/Using_FormData_Objects)
- [Python setattr](https://docs.python.org/3.13/library/functions.html#setattr)

### 8.21 本章阶段代码快照（2026-10-12）

下面保留本次读取的 12 个指定文件，供日后修改代码时对照。快照是当时的实际写法，包含第 8.16 节已说明的待处理问题，不是自动修正后的版本。

<details>
<summary><code>backend/app/services/user_service.py</code></summary>

```python
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from sqlalchemy.orm import Session


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(exclude_none=True)  # pydantic对象转换成字典
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
```

</details>

<details>
<summary><code>backend/app/schemas/files.py</code></summary>

```python
from pydantic import BaseModel


class FileResponse(BaseModel):
    original_name: str
    disk_name: str
    size: int
    url: str
```

</details>

<details>
<summary><code>backend/app/schemas/user.py</code></summary>

```python
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
```

</details>

<details>
<summary><code>backend/app/api/files.py</code></summary>

```python
import os
import time
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR


from app.schemas.files import FileResponse

router = APIRouter(prefix="/files", tags={"文件管理"})


@router.post("/upload")
def upload(file: UploadFile = File(...)):
    """文件上传的接口"""

    if not file.filename:
        raise BusinessException(message="文件名不能为空")

    # 原始的文件名，例如：用户头像.jpg
    original_name = os.path.basename(file.filename)

    # 文件后缀，例如：.jpg
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(message=f"不支持的文件后缀：{ext}")

    # 文件大小校验
    if file.size and file.size > MAX_FILE_SIZE:
        raise BusinessException(
            message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 设置唯一的文件名称
    disk_name = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}"

    # 文件存储的实际路径
    save_path = UPLOAD_DIR / disk_name

    # 流式写文件
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return Response.success(
        data=FileResponse(
            original_name=original_name,
            disk_name=disk_name,
            size=file.size,
            url=f"/uploads/{disk_name}",
        )
    )
```

</details>

<details>
<summary><code>backend/app/api/user.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services import user_service

router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/info")
def get_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录的用户信息
    """
    return Response.success(data=UserResponse.model_validate(current_user))


@router.put("/update")
def update_user_info(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息"""
    res = user_service.update_user_info(db, current_user, data)
    return Response.success(data=res)
```

</details>

<details>
<summary><code>frontend/src/api/files.js</code></summary>

```js
import request from "@/utils/request";

export function uploadFileApi(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request({
    url: "/api/files/upload",
    method: "post",
    data: formData,
    headers: { "Content-Type": "multipart/form-data" },
  });
}
```

</details>

<details>
<summary><code>frontend/src/api/user.js</code></summary>

```js
import request from "@/utils/request";

// 获取个人信息
export function getUserInfo() {
  return request({
    url: "/api/user/info",
    method: "get",
  });
}

// 更新个人信息
export function updateUserInfo(data) {
  return request({
    url: "/api/user/update",
    method: "put",
    data,
  });
}
```

</details>

<details>
<summary><code>frontend/src/layouts/Layout.vue</code></summary>

```vue
<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown>
            <div
              style="display: flex; align-items: center; margin-right: 20px; cursor: pointer"
            >
              <img
                :src="userInfo?.avatar"
                alt=""
                style="width: 30px; border-radius: 50%"
              />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || "用户" }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goPerson">个人信息</el-dropdown-item>
                <el-dropdown-item @click="handleLogout"
                  >退出登录</el-dropdown-item
                >
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu router style="height: 100%" default-active="/manager/home">
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>
            <el-menu-item index="/manager/lab">
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/equ">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/user">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu as IconMenu,
  House,
  Setting,
  User,
} from "@element-plus/icons-vue";
import router from "@/router";
import { logout } from "@/utils/auth";
import { useUser } from "@/utils/user";
const { userInfo } = useUser();

const handleLogout = () => {
  logout();
  router.push("/login");
};

const goPerson = () => {
  router.push("/manager/profile");
};
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from "@/utils/auth";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: "/manager/home" },
    {
      path: "/manager",
      name: "Layout",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          name: "Home",
          component: () => import("@/views/Home.vue"),
        },
        {
          path: "lab",
          name: "Lab",
          component: () => import("@/views/Lab.vue"),
        },
        {
          path: "profile",
          name: "Profile",
          component: () => import("@/views/Profile.vue"),
        },
        {
          path: "equ",
          name: "Equ",
          component: () => import("@/views/Equ.vue"),
        },
        {
          path: "user",
          name: "User",
          component: () => import("@/views/User.vue"),
        },
      ],
    },
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
    },
  ],
});

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken();
  if (to.path === "/login" || to.path === "/register") {
    return true;
  } else {
    return token ? true : "/login";
  }
});

export default router;
```

</details>

<details>
<summary><code>frontend/src/views/Profile.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>个人信息</span>
        </div>
      </template>
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-width="80px"
        style="width: 100%; padding-right: 50px"
        v-loading="loading"
      >
        <el-form-item>
          <el-upload
            class="avatar-uploader"
            :http-request="handleFileUpload"
            :show-file-list="false"
            accept="image/jpeg,image/png,image/gif,image/webp"
            :on-success="handleAvatarSuccess"
            :before-upload="beforeAvatarUpload"
          >
            <img v-if="form.avatar" :src="form.avatar" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-form-item label="账号">
          <el-input disabled v-model="form.username" placeholder="请输入账号" />
        </el-form-item>

        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入名称" />
        </el-form-item>

        <el-form-item label="角色">
          <el-input disabled v-model="roleLabel" />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            保存修改
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { getUserInfo, updateUserInfo } from "@/api/user";
import { uploadFileApi } from "@/api/files";
import { useUser } from "@/utils/user";
const { updateUser } = useUser();

const loading = ref(false);
const submitting = ref(false);
const formRef = ref();
const form = reactive({
  username: "",
  name: "",
  role: "",
  email: "",
  phone: "",
  avatar: "",
});

const roleLabel = computed(() => {
  return form.role === "admin"
    ? "管理员"
    : form.role === "student"
      ? "学生"
      : "未知角色";
});

const rules = {
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  email: [{ type: "email", message: "邮箱格式错误", trigger: "blur" }],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: "手机号格式错误", trigger: "blur" },
  ],
};

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.avatar = res.data?.url;
    }
  } catch {}
};

//  发送请求查询用户信息
const loadUserInfo = async () => {
  loading.value = true;
  try {
    const res = await getUserInfo();
    if (res.code === 200) {
      Object.assign(form, res.data);
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return;
  } finally {
    loading.value = false;
  }
};

//  发送请求更新用户信息
const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  submitting.value = true;
  try {
    const res = await updateUserInfo(form);
    if (res.code === 200) {
      updateUser(res.data);
      ElMessage.success("更新成功");
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return;
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  loadUserInfo();
});
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<details>
<summary><code>frontend/.env.development</code></summary>

```env
VITE_API_BASE_URL=
```

</details>

<details>
<summary><code>frontend/vite.config.js</code></summary>

```js
import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000", //  /api -> http://127.0.0.1:8000/api
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8000", //  /api -> http://127.0.0.1:8000/uploads
        changeOrigin: true,
      },
    },
  },
});
```

</details>

<a id="13-user-management"></a>

## 9. 密码修改与管理员用户管理

阶段起点：2026-10-14。密码修改、用户分页、管理员增删改属于本章；本人 role/status 过滤和有预约用户禁止删除的后续修补也放在对应功能旁。历史权限问题只代表当时版本，当前行为以修正说明为准。

### 9.1 密码与用户管理在项目中的位置

本次从“本人查看、修改资料”扩展为：

- 已登录用户修改自己的密码。
- 管理员查询全体用户，支持关键词和分页。
- 管理员新增、编辑、删除用户。

CRUD 是四个英文操作的缩写：

| 字母      | 操作 | 本项目例子         |
| --------- | ---- | ------------------ |
| C：Create | 创建 | 新增用户           |
| R：Read   | 读取 | 用户列表、个人资料 |
| U：Update | 更新 | 编辑用户、修改密码 |
| D：Delete | 删除 | 删除用户记录       |

页面、接口和服务不是三套不同功能，而是同一功能的不同层：

```text
页面收集输入
  → 前端 API 包装函数发请求
  → 后端依赖检查身份和权限
  → Pydantic 校验请求字段
  → 服务函数查询或修改数据库
  → 响应模型整理输出
  → 页面刷新显示
```

### 9.2 本人资料权限：历史问题与字段边界

> 2026-10-15 修正说明：当前本人资料服务已在 model_dump 中明确 exclude={"role", "status"}，隔离验证确认这两个字段不再写入。下文保留 2026-10-14 的问题分析；模型拆分仍是整理方案，当前修正详见第 9.3 节。

2026-10-14 的 UserUpdateRequest 增加了：

```python
role: str | None = None
status: bool | None = None
```

管理员修改用户确实需要这些字段，但本人修改接口 PUT /api/user/me 也继续使用同一个模型，并调用同一个“遍历所有非 None 字段赋值”的服务逻辑。

因此，当时的本人接口不仅能修改名称和联系方式，也会接受并保存 role、status。普通用户可能改变自己的角色，随后通过管理员校验。

这个问题已在隔离数据库中确认：原来的学生对象经本人更新服务修改角色后，能通过 get_current_admin。未在真实数据库中执行该操作。

**需要优先拆分本人修改模型与管理员修改模型，并在 API 参数类型上使用各自的模型。**只把前端角色输入框 disabled，不会限制其他客户端提交角色字段。

具体参考设计见第 9.20 节。这个问题不影响我们理解原代码如何执行，但要区分历史漏洞、已落地的字段过滤与进一步拆分模型的建议。

### 9.3 本人资料权限：排除 role/status 的实际修正

当前 user_service.update_user_info 改为：

```python
user_dict = data.model_dump(
    exclude_none=True,
    exclude={"role", "status"},
)
```

exclude 明确把两个字段从赋值字典中移除，即使请求提供它们也不会在这个服务中保存。

本次隔离验证同时提供了名称、角色和状态，结果名称更新，角色与状态保持原值，说明该修改路径已修正。

第 9 节保留的是发现问题时的旧代码。当前可以继续使用字段排除控制写入范围；再拆分请求模型是让接口声明更清楚的整理方向，不是说当前过滤修正没有作用。

该结论只覆盖已检查的本人资料修改路径，不等于已经审计或验证整个项目的所有权限功能。

### 9.4 当前文件与接口对照

| 文件                                 | 本次变化                                               |
| ------------------------------------ | ------------------------------------------------------ |
| backend/app/schemas/user.py          | 新增创建用户、修改密码模型；用户更新模型加入角色和状态 |
| backend/app/common/response.py       | 新增 PageResponse                                      |
| backend/app/dependencies/auth.py     | 新增 get_current_admin                                 |
| backend/app/services/user_service.py | 新增改密、分页、创建、按 ID 更新和删除函数             |
| backend/app/api/user.py              | 注册本人、密码、列表和管理员 CRUD 接口                 |
| frontend/src/api/user.js             | 对应各接口的请求包装                                   |
| frontend/src/views/Password.vue      | 本人修改密码页面                                       |
| frontend/src/views/User.vue          | 列表、搜索、分页与新增编辑弹窗                         |
| frontend/src/layouts/Layout.vue      | command 下拉菜单、修改密码入口、管理员菜单显示         |
| frontend/src/router/index.js         | 增加 /manager/password 子路由                          |

当前接口：

| 方法   | 路径                | 当前权限依赖      | 动作                         |
| ------ | ------------------- | ----------------- | ---------------------------- |
| GET    | /api/user/me        | get_current_user  | 查询本人                     |
| PUT    | /api/user/me        | get_current_user  | 修改本人，当前字段范围有问题 |
| PUT    | /api/user/password  | get_current_user  | 修改本人密码                 |
| GET    | /api/user/list      | get_current_admin | 搜索和分页查询用户           |
| POST   | /api/user           | get_current_admin | 新增用户                     |
| PUT    | /api/user/{user_id} | get_current_admin | 修改指定用户                 |
| DELETE | /api/user/{user_id} | get_current_admin | 删除指定用户                 |

旧地址 /api/user/info 和 /api/user/update 已改成同一个资源地址 /api/user/me，通过 GET 与 PUT 区分查询和修改。前端 api/user.js 已同步；复现时其他调用也要检查是否仍使用旧地址。

### 9.5 下拉 command 与页面路由

Layout 从分别绑定 click 改为：

```html
<el-dropdown @command="handleCommand">
  <el-dropdown-item command="profile">个人信息</el-dropdown-item>
  <el-dropdown-item command="password">修改密码</el-dropdown-item>
  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
</el-dropdown>
```

command 是每个菜单项携带的标识值。点击后，组件发出 command 事件，把对应字符串交给 handleCommand。

```js
const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/manager/profile");
  } else if (command === "password") {
    router.push("/manager/password");
  } else if (command === "logout") {
    logout();
    router.push("/login");
  }
};
```

router 的 password 子路由加载 Password.vue。这里是前端导航，随后页面提交时才访问后端接口。

用户管理菜单：

```html
<el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
  用户管理
</el-menu-item>
```

v-if 控制菜单是否显示。当前路由守卫仍只检查 token，未独立检查管理员角色；普通用户直接访问用户管理页面时，后端列表接口才会拒绝其操作。

前端使用缓存中的角色决定显示，后端使用数据库中的角色决定权限，二者职责不同。

### 9.6 get_current_admin：依赖还可以依赖其他依赖

当前函数：

```python
def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise BusinessException(message="无权限访问", code=403)
    return current_user
```

执行顺序：

```text
管理员接口请求
  → get_current_user 提取和验证 token
  → 根据 user_id 查询数据库用户
  → 检查账号状态
  → get_current_admin 检查 role
  → 通过后调用管理员接口函数
```

API 中的参数名仍叫 current_user，但它的权限范围由 Depends(get_current_admin) 决定，名字本身不会自动产生管理员限制。

函数注释写的是“JWT token 内角色”，实际代码检查的是数据库用户的 role。当前 JWT 载荷只有 user_id 与 exp，没有 role；应以代码实际读取的位置理解。

拒绝使用 BusinessException(code=403)，现有处理器返回 HTTP 200、JSON code 403。不要把它等同于 HTTP 403。request.js 会显示错误，但对这个业务 code 通常仍返回成功完成的 Promise，因此页面需要判断 res.code。

### 9.7 密码修改：页面字段与接口字段

Password.vue 中：

```js
const form = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});
```

这些是页面变量名。后端字段是：

```python
class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str
```

提交时显式映射：

```js
const res = await updatePassword({
  old_password: form.oldPassword,
  new_password: form.newPassword,
});
```

confirmPassword 只用于页面比较两次输入，没有发送给后端。camelCase 与 snake_case 不会自动对应，当前转换由这个对象构造完成。

前端校验包括：

- 原密码必填。
- 新密码必填。
- 确认密码不能为空，且与新密码一致。

当前三个 el-input 都没有设置 type="password"，按默认文本方式显示输入内容。type="password" 控制显示遮盖，不等于传输加密。

### 9.8 密码修改：服务函数的顺序

当前逻辑：

```python
def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误!")
    if data.old_password == data.new_password:
        raise BusinessException(message="新密码不能跟原密码相同!")
    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)
```

可以分成四步：

1. 用 bcrypt 验证输入原密码与已保存哈希是否匹配。
2. 原密码验证通过后，拒绝新旧密码相同。
3. 对新密码计算哈希，替换数据库对象的 password。
4. 提交事务并刷新对象。

不能直接拿原密码字符串与 user.password 比较，因为数据库字段保存的是哈希。

函数没有返回用户资料，接口返回 Response.success()，所以成功内容中的 data 为 null。

失败的 BusinessException 没显式传 code，当前默认业务 code 为 500；HTTP 仍为 200。这是现有约定，不代表每个“原密码错误”都是真正的服务器故障。

#### 成功后为什么退出登录

Password.vue 在 code 200 时：

```js
ElMessage.success("修改密码成功");
logout();
await router.push("/login");
```

这是前端选择的交互：清理当前浏览器存储，让用户用新密码重新登录。

当前 JWT 没有密码版本或撤销机制，改密服务也没有让旧 token 失效。清理这个浏览器的 token 不等于其他浏览器或已经复制的 token 被后端撤销。

本次隔离验证确认：旧密码不再匹配，新密码匹配，数据库保存的是新哈希。

#### 当前缺少的密码规则

PasswordUpdateRequest 只声明 str，没有最小长度、最大字节数等规则。当前服务可以给空字符串计算哈希并保存；超过 bcrypt 限制的新密码会到达库中产生 ValueError，而不是请求校验阶段的 422。

前端必填校验不能代替后端校验。密码规则应在所有创建和修改入口保持一致。

### 9.9 分页查询：GET params 与后端查询参数

前端列表调用：

```js
const res = await getUserPageList({
  page: params.page,
  page_size: params.pageSize,
  keywords: params.keywords,
});
```

API 包装：

```js
export function getUserPageList(params) {
  return request({
    url: "/api/user/list",
    method: "get",
    params,
  });
}
```

params 会进入 URL 查询部分，例如：

```text
/api/user/list?page=2&page_size=10&keywords=demo
```

与 data 的区别：

| Axios 配置 | 这里的用途                    |
| ---------- | ----------------------------- |
| params     | 查询参数，出现在 URL 中       |
| data       | 请求内容，例如创建用户的 JSON |

前端变量 pageSize 转成后端字段 page_size，是 load 函数显式映射的结果。

后端参数：

```python
page: int = 1
page_size: int = 10
keywords: str | None = None
```

这些参数不是路径占位变量，也不是 Pydantic 请求体，因此 FastAPI 将它们作为查询参数读取。int 会解析类型，但当前没有限制正数或最大页大小。

### 9.10 查询构造、模糊搜索与 OR

服务先构造查询：

```python
query = db.query(User)

if keywords:
    query = query.filter(
        or_(
            User.username.ilike(f"%{keywords}%"),
            User.name.ilike(f"%{keywords}%"),
        )
    )
```

含义：关键词非空时，账号或名称中有匹配内容的用户都符合条件。

% 是 LIKE 的任意长度通配符，前后都有 % 表示包含匹配。ilike 表示不区分大小写的匹配语义；MySQL 等方言通常通过 lower 与 LIKE 组织表达式。实际效果也与数据库字符串规则有关。

这里构造的是 SQLAlchemy 查询表达式，匹配值会作为参数处理，不是把完整 SQL 直接拼接出来。输入中的 % 和 \_ 仍有 LIKE 通配含义，当前没有做“纯字面关键词”的转义。

#### 为什么 from operator import or\_ 当前也能运行

你的导入是：

```python
from operator import or_
```

operator.or\_(a, b) 等价于 a | b。SQLAlchemy 对这里的 SQL 条件表达式重载了 |，所以这两个条件仍然形成 SQL OR。本次隔离验证也确认查询能按账号或名称匹配。

通常从 sqlalchemy 导入 or\_ 能更清楚地表达数据库条件，也支持不同的调用组织；不能简单把当前写法判定为必然报错。

也不能直接换成 Python 普通 or，因为普通 or 会做 Python 真值判断，而这里需要组合 SQL 条件。[SQLAlchemy 运算符说明](https://docs.sqlalchemy.org/en/20/core/operators.html)

### 9.11 count、offset、limit、all 与排序

当前代码：

```python
total = query.count()

items = (
    query.order_by(User.id.desc())
    .offset((page - 1) * page_size)
    .limit(page_size)
    .all()
)
```

| 操作                     | 含义                              |
| ------------------------ | --------------------------------- |
| count()                  | 统计所有符合筛选条件的记录数      |
| order_by(User.id.desc()) | ID 从大到小排序，新记录通常在前面 |
| offset(...)              | 跳过前面的记录                    |
| limit(page_size)         | 最多取这一页的数量                |
| all()                    | 执行查询，得到用户对象列表        |

页大小为 10 时：

| 页码 | offset | 读取范围               |
| ---- | ------ | ---------------------- |
| 1    | 0      | 前 10 条               |
| 2    | 10     | 跳过 10 条，再取 10 条 |
| 3    | 20     | 跳过 20 条，再取 10 条 |

total 在分页截取前统计。它是符合关键词的总数量，不是当前页的行数。

db.query、filter、order_by 等主要构造查询；count 与 all 会执行查询。这个函数通常会有一次计数查询和一次分页查询。

### 9.12 PageResponse 与列表推导式

当前新增模型：

```python
class PageResponse(BaseModel):
    list: Any = []
    total: int = 0
```

它只描述返回数据，不会自动执行分页。

服务中的：

```python
[UserResponse.model_validate(item) for item in items]
```

是列表推导式，相当于：

```python
result = []
for item in items:
    result.append(UserResponse.model_validate(item))
```

每个数据库对象转换成用户响应，避免把密码字段返回给表格。

最终内容类似：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "list": [
      {
        "id": 7,
        "username": "demo_user",
        "name": "示例用户",
        "role": "student",
        "email": null,
        "phone": null,
        "avatar": null,
        "status": true
      }
    ],
    "total": 21
  }
}
```

Any 表示宽泛类型，不会在 PageResponse 的 list 字段中强制检查每一项类型。当前服务显式构造 UserResponse，所以返回元素仍有响应模型校验。后续可用更明确的列表类型和默认工厂提升可读性。

### 9.13 el-table、作用域插槽与分页组件

前端接收：

```js
tableData.value = res.data?.list;
total.value = res.data?.total;
```

el-table 的 data 是行数组。普通列的 prop 指向行对象的属性：

```html
<el-table-column prop="username" label="账号" />
```

自定义列：

```html
<template #default="{ row }">
  <el-tag :type="row.status ? 'success' : 'danger'">
    {{ row.status ? '正常' : '禁用' }}
  </el-tag>
</template>
```

组件把当前行作为插槽参数传入，{ row } 是解构取出当前用户对象。同一个插槽模板会为每行使用不同的 row。[Element Plus 表格](https://element-plus.org/en-US/component/table.html)

编辑按钮传入整行：

```html
<el-button @click="handleEdit(row)">编辑</el-button>
```

分页组件使用两个具名 v-model：

```html
<el-pagination
  v-model:current-page="params.page"
  v-model:page-size="params.pageSize"
  :total="total"
  layout="total, prev, pager, next"
  @current-change="load"
/>
```

具名 v-model 绑定组件指定的属性与更新事件。翻页会更新 params.page，并触发 load 重新获取数据。[Element Plus 分页](https://element-plus.org/en-US/component/pagination.html)

当前 layout 没有 sizes，所以没有显示页大小选择器；pageSize 当前主要保持为 10。

### 9.14 搜索为什么先重置到第一页

```js
const handleSearch = async () => {
  params.page = 1;
  load();
};
```

原来可能在第 5 页，新的关键词只有 1 页结果。先回到第一页，可以避免用旧页码请求新筛选结果。

输入框的 @keyup.enter 是 Enter 键事件修饰符，@clear 处理清空操作，查询按钮也调用同一个函数。

当前虽然把 handleSearch 声明为 async，但没有 await load，函数自身不会等列表加载完才结束。列表 loading 仍由 load 管理；若调用方需要等待或接收失败，应明确返回或 await 这个 Promise。

### 9.15 一个弹窗同时完成新增与编辑

弹窗是否打开：

```js
const dialogVisible = ref(false);
```

模式判断使用 form.id：

| 状态 | form.id | 行为                            |
| ---- | ------- | ------------------------------- |
| 新增 | null    | 显示密码，账号可编辑，调用 POST |
| 编辑 | 已有 ID | 隐藏密码，账号禁用，调用 PUT    |

`!!form.id` 先取反再取反，得到布尔值。因此 `:disabled="!!form.id"` 表示有 ID 时禁用账号输入。

标题的 `form.id ? '编辑' : '新增'` 使用同一判断。这里依赖数据库 ID 是正整数。

#### resetForm 不是清空数据库

resetForm 用 Object.assign 把编辑表单恢复为初始值，包括：

```js
{
  id: null,
  username: '',
  password: '',
  name: '',
  role: 'student',
  email: '',
  phone: '',
  avatar: '',
  status: 1
}
```

它只改浏览器里的编辑数据，不会发请求。每次打开新模式前重置，避免把上一个用户的字段带进下一个用户。

handleEdit 再把 row 的指定字段复制进 form。当前没有把 row 直接作为表单对象，因此编辑普通字符串字段不会直接修改原表格行的显示数据。

### 9.16 nextTick、动态校验与原生提交

打开新增或编辑窗口后：

```js
dialogVisible.value = true;
await nextTick();
formRef.value?.clearValidate();
```

Vue 的页面更新不是每次赋值就同步完成。nextTick 等待这一轮 DOM 更新，随后更适合操作新显示的表单组件。clearValidate 清除旧的校验错误，不会清空字段值。[Vue nextTick](https://vuejs.org/api/general.html#nexttick)

问号表示表单实例暂时没有时，不继续调用方法，避免直接访问不存在的对象。

校验规则是计算属性：

```js
const rules = computed(() => ({
  username: [{ required: true, message: "请输入账号", trigger: "blur" }],
  password: form.id
    ? []
    : [
        { required: true, message: "请输入密码", trigger: "blur" },
        { min: 3, max: 10, message: "密码是3-10位", trigger: "blur" },
      ],
}));
```

实际代码还包含名称、邮箱、手机号规则。form.id 改变时，密码规则跟着变化：编辑时不要求填写新增密码。

#### 为什么弹窗外侧的确定按钮也能提交

表单：

```html
<el-form id="user-form" @submit.prevent="handleSave">
  <!-- 输入项 -->
</el-form>
```

按钮位于 footer 插槽：

```html
<el-button native-type="submit" form="user-form" :loading="formLoading">
  确定
</el-button>
```

native-type 设置原生按钮的 type。form 属性通过 ID 将按钮关联到对应的 HTML 表单，即使按钮不在 form 标签内部。

@submit.prevent 监听表单提交，并阻止默认的浏览器提交和页面刷新，转而调用异步 handleSave。用户按 Enter 和点击确定可以走同一条提交逻辑。

el-form-item 的 for 与输入框 id 用于标签关联；prop 与 rules/model 的字段关系仍是另一套用途。

### 9.17 handleSave 的解构、剩余属性与模式分支

核心：

```js
const { id, username, password, ...userData } = form;

const res = id
  ? await updateUserApi(id, userData)
  : await createUserApi({ username, password, ...userData });
```

对象解构取出三个字段，...userData 收集其余属性。

例如 form 包含：

```text
id、username、password、name、role、email、phone、avatar、status
```

userData 就包含：

```text
name、role、email、phone、avatar、status
```

两个分支：

- 编辑：ID 放在 URL 中，请求体不包含 username 和 password。
- 新增：把 username、password 加回请求体，发送创建用户请求。

所以编辑弹窗不会修改密码，也不会修改账号名。本人密码修改属于独立的 /password 功能，当前没有管理员重置他人密码接口。

成功后关闭弹窗、显示提示，并 await load 重新查询列表。编辑接口保存到数据库并不会自动更新原来的 tableData，需要重查或主动替换行。

formLoading 在进入提交时设为 true，防止重复提交并控制按钮状态。校验失败的 return 也会经过 finally，恢复加载状态。

当前 catch 捕获请求失败并保留表单；request.js 已经显示提示，避免重复提示。

### 9.18 后端创建、按 ID 更新与删除

#### 创建：UserCreateRequest 与默认值

当前模型：

```python
class UserCreateRequest(BaseModel):
    username: str
    password: str = "123456"
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role: str = "student"
    status: bool = 1
```

username 没有默认值，是必需字段。password 的默认值只在请求没有提供它时使用，不会自动替换显式提供的空字符串。

role 默认 student。status 的声明是 bool，用 True 作为默认值更明确；当前 1 的默认写法不等于页面中的所有状态类型已经统一。

服务流程：

```text
按账号查重
  → 重复时抛业务异常
  → 计算密码哈希
  → 创建 User 对象
  → add、commit、refresh
  → 返回不含密码的 UserResponse
```

与公开注册接口不同，管理员创建模型允许指定角色和状态，且由 get_current_admin 限制调用者。

模型的 name 可以不提供，但数据库 name 列不允许 NULL，而创建服务直接写入 data.name。当前“只给账号不提供名称”的请求能通过模型，却会在数据库阶段失败。本次隔离验证确认该冲突。

参考方向：请求模型要求名称，或像注册服务一样明确使用账号作为默认名称。两种行为需要统一决定，不应依赖前端必填来弥补接口契约。

#### 更新：路径 ID 与业务请求体

前端地址：

```js
url: `/api/user/${userId}`;
```

对应后端：

```python
@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.update_user(db, user_id, data)
    return Response.success(data=res)
```

user_id 来自 URL，data 来自 JSON，管理员身份来自依赖，数据库会话来自 get_db。

服务先查目标是否存在，再使用 model_dump(exclude_none=True) 和 setattr 修改允许的字段，最后提交。

exclude_none 不会排除 False。因此 status 为 false 时仍可保存禁用状态；它只跳过 None，而不是跳过所有假值。

管理员当前可以修改自己的角色或状态。服务没有禁止自我禁用或自我降级，也没有在编辑成功后同步当前用户的共享缓存，相关行为需要单独检查。

#### 删除：确认框与后端约束

前端：

```js
ElMessageBox.confirm(`确认删除用户【${row.username}】？`, "确认删除", {
  type: "warning",
}).then(async () => {
  const res = await deleteUserApi(row.id);

  if (res.code === 200) {
    ElMessage.success("删除用户成功");
    load();
  }
});
```

确认框的 Promise 在确认后进入 then，取消时会拒绝。当前没有 catch，取消或删除请求失败可能产生未处理的 Promise 拒绝；并不意味着取消后一定删除了用户。[Element Plus 确认框](https://element-plus.org/en-US/component/message-box.html)

后端先检查：

```python
if user_id == currut_user.id:
    raise BusinessException(message="不能删除当前登录的账号")
```

比较的是目标 ID 与已经认证的当前用户 ID。这项限制在后端，不依赖前端隐藏按钮。

目标不存在也抛业务异常。存在时：

```python
db.delete(user)
db.commit()
```

这里真正删除数据库记录。把 status 改为 False 只是禁用，记录仍在，是另一种操作。

当前形参 currut_user 的拼写不标准，但函数内使用一致，因此不是运行错误。建议维护时统一命名为 current_user。

<a id="user-deletion"></a>

### 9.19 用户删除：历史预约、外键约束与确认框

当前用户删除策略如下；实验室与设备的关联删除见[资源删除规则](#resource-deletion)。

| 删除对象 | 服务先检查什么                         | 存在关联时的结果                 |
| -------- | -------------------------------------- | -------------------------------- |
| 用户     | 是否为当前登录用户；是否有任意预约记录 | 拒绝删除本人；有预约时提示可禁用 |

这里的“任意预约”没有排除拒绝、取消或过去的记录。保留历史归属和“是否占用未来时段”是两种不同判断。

为什么先查过，提交时还要捕获 IntegrityError？因为关联检查结束后、实际删除提交前，另一个请求仍可能新建关联记录。数据库外键是最后一道约束；提交失败时回滚并返回业务 code=409，避免直接把约束错误暴露成模糊的 500。

前端 User.vue、Lab.vue、Equipment.vue 都把确认和请求放在同一个 try 中：

```js
try {
  await ElMessageBox.confirm("确认删除？", "确认删除", { type: "warning" });
  const res = await deleteUserApi(row.id);
  if (res.code === 200) {
    ElMessage.success("删除用户成功");
    await load();
  }
} catch {
  // 取消、关闭和请求失败都在这里结束这次操作。
}
```

这是简化的用户删除片段，完整写法见快照。

确认框的取消和关闭也会让等待的 Promise 拒绝，catch 可以接住这种正常操作。请求失败的提示由拦截器处理。业务 code=409 通常仍返回对象，因此不会进入成功刷新分支。

### 9.20 本人修改模型与管理员模型的参考拆分

这是参考调整，未写入业务源码：

```python
from typing import Literal

from pydantic import BaseModel


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None


class AdminUserUpdateRequest(ProfileUpdateRequest):
    role: Literal["student", "admin"] | None = None
    status: bool | None = None
```

用途：

| 接口           | 建议请求模型           |
| -------------- | ---------------------- |
| PUT /me        | ProfileUpdateRequest   |
| PUT /{user_id} | AdminUserUpdateRequest |

Literal 限定角色只能是给出的值，避免任意角色字符串。

需要同时修改 API 的请求参数类型和对应服务的类型声明。只新增模型但接口继续使用旧模型，字段范围不会自动改变。

格式、长度和清空语义仍需独立设计。此示例只展示权限字段拆分，不是全部校验的最终实现。

### 9.21 静态路由与动态路由的注册顺序

当前 PUT 路由中，/me 和 /password 定义在 /{user_id} 前。

FastAPI 按注册顺序匹配路由。/{user_id} 可以先在路径层面接收 me 这样的字符串，再发生 int 校验错误；不能依赖 user_id: int 就认为静态路径永远不会被匹配。

把固定路径放在宽泛的动态路径前，能避免被遮住。当前代码的顺序符合这一安排。[FastAPI 路由顺序](https://fastapi.tiangolo.com/tutorial/path-params/#order-matters)

POST 的装饰器使用空路径 `@router.post("")`。

它表示使用当前 router 的根路径。与 /api 和 /user 前缀组合后，创建地址就是 /api/user，不是“没有注册路径”。

### 9.22 布尔状态与数字单选框的类型不一致

后端 UserResponse 返回：

```json
{ "status": true }
```

编辑时复制：

```js
status: row.status;
```

但单选框使用：

```html
<el-radio :value="1">正常</el-radio> <el-radio :value="0">禁用</el-radio>
```

这是数字 1、0，与布尔 true、false 不是相同的值：

```js
true === 1; // false
false === 0; // false
```

本次检查到的 Element Plus Radio 使用严格比较判断选中状态，所以编辑回填可能无法显示预期的单选项。

可以统一为布尔值：

```html
<el-radio :value="true">正常</el-radio> <el-radio :value="false">禁用</el-radio>
```

同时将 form 初始和重置的 status 改为 true。或者保留数字控件，在回填时显式转换；不要在不同环节混用后期待组件自动匹配。

Pydantic 会处理请求中的 bool 输入，不代表 Vue 控件已经在显示层做了同样转换。[Element Plus Radio](https://element-plus.org/en-US/component/radio.html)

### 9.23 本次检查记录与问题清单

#### 已完成的隔离检查

使用实际 schema、服务函数和管理员依赖的代码，在内存 SQLite 中完成 20 项检查，包括：

- 创建用户与默认密码哈希，响应不含密码。
- 管理员依赖放行管理员，拒绝学生。
- 重复账号被拒绝。
- 原密码错误、新旧相同被拒绝。
- 改密后新密码匹配、旧密码不匹配。
- 模糊搜索匹配账号和名称，空结果处理。
- 分页 total、倒序和 offset/limit。
- operator.or\_ 对当前表达式构造 SQL OR。
- 更新名称及 False 状态、目标不存在时拒绝。
- 删除他人、拒绝删除本人、拒绝不存在目标。
- 确认当前本人更新模型接受角色，并使学生变为管理员。
- 确认新密码为空目前可保存，超过字节限制到达 bcrypt 错误。
- 确认新建名称缺失与数据库 NOT NULL 冲突。

另外：

- User.vue、Password.vue、Profile.vue、Layout.vue 通过脚本和模板编译。
- 前端用户 API 与路由通过 JavaScript 语法检查。
- 检查本地 Radio 比较实现，确认类型差异。

这些检查没有验证完整 HTTP 登录流程、真实 MySQL 方言行为或浏览器弹窗交互，不能替代下面的实际验收。

#### 当时的问题清单与后续处理

| 优先项       | 当前事实                                  | 需要处理                       |
| ------------ | ----------------------------------------- | ------------------------------ |
| 权限边界     | /me 与管理员更新共用含 role/status 的模型 | 拆分模型并绑定到不同接口       |
| 密码校验     | 新密码只声明 str，后端允许空值            | 统一必填、长度、UTF-8 字节限制 |
| 密码显示     | Password.vue 输入框默认文本               | 使用密码输入框                 |
| 状态类型     | 接口返回 bool，单选框使用数字             | 统一或显式转换                 |
| 新建用户契约 | name 可不传，数据库不允许 NULL            | 要求名称或提供明确默认         |
| 分页范围     | page/page_size 只校验 int                 | 限制页码、页大小与合理上限     |
| 删除 Promise | confirm().then 没有 catch                 | 分别处理取消与请求失败         |
| 角色输入     | 请求模型接受任意 role 字符串              | 使用限定值或规则               |
| 事务错误     | 修改服务未显式处理回滚                    | 明确失败后的会话处理           |
| 当前用户状态 | 管理员编辑本人不更新共享 userInfo         | 确定自我修改限制和缓存同步     |
| 改密失效     | 清理本地 token，不撤销其他有效 token      | 根据需求设计服务端失效机制     |
| 管理员初始化 | 注册默认学生，管理 API 又要求管理员       | 从零复现需准备受控的初始管理员 |

这些是分析结果和待办，不代表本次已修改源码。

阶段核对只把实际业务逻辑变化记为修复；user_service 的空行整理不改变权限、删除或密码行为。

### 9.24 浏览器实际验收清单

#### 密码修改

- [ ] 菜单进入 /manager/password。
- [ ] 检查两次新密码不一致时不会提交。
- [ ] 原密码错误时显示业务错误。
- [ ] 新旧密码相同时被拒绝。
- [ ] 修改成功后回到登录页，新密码可登录，旧密码不可登录。
- [ ] 检查输入内容是否按预期遮盖。
- [ ] 修正后验证后端直接请求也不能提交空密码或超长密码。

#### 列表与权限

- [ ] 管理员进入用户管理页，表格和 total 正确。
- [ ] 账号和名称关键词能找到目标。
- [ ] 搜索会重置到第一页。
- [ ] 翻页读取不同数据，ID 按倒序显示。
- [ ] 空结果显示正常。
- [ ] 学生不能调用管理员列表和 CRUD 接口。
- [ ] 修正模型后，本人资料接口不能改变角色或状态。

#### 创建、编辑、删除

- [ ] 新增弹窗重置字段并显示密码。
- [ ] 编辑弹窗复制指定行，隐藏密码并禁用账号。
- [ ] 新增与编辑规则跟随模式切换，旧错误提示清除。
- [ ] 点击确定与 Enter 只提交一次。
- [ ] 正常与禁用单选项回填正确。
- [ ] 创建、编辑成功后列表刷新。
- [ ] 重复账号、缺失字段、目标不存在等错误可理解。
- [ ] 取消删除不会请求 DELETE。
- [ ] 删除他人成功，删除自己被后端拒绝。
- [ ] 删除最后一页最后一项后，页码和列表状态正确。
- [ ] 网络失败时加载状态恢复，表单可重试。
- [ ] 编辑当前管理员的角色或状态时，行为符合约定。

只在自己的学习环境使用专门的测试账户检查，验收结果不要由“语法编译通过”代替。

### 9.25 从零复现时的新增顺序

1. 保留已完成的用户模型、认证和密码哈希工具。
2. 更新个人资料地址为 GET/PUT /me，并同步前端调用。
3. 将本人更新与管理员更新字段分开，避免权限漏洞。
4. 增加 PasswordUpdateRequest、UserCreateRequest 和管理更新模型。
5. 增加 PageResponse 与 get_current_admin。
6. 实现密码修改、分页、创建、指定 ID 更新和删除服务。
7. 按静态优先顺序注册后端接口。
8. 增加前端 API 请求函数。
9. 增加 Password.vue 和 User.vue，设置路由与菜单。
10. 统一状态值、密码规则、名称要求与分页范围。
11. 在学习数据库的初始化流程中创建初始管理员。
12. 完成第 9.24 节的功能检查。

第一位管理员不能依靠允许学生自行修改角色来产生。最终复现章节需要给出明确的学习数据库初始化方式；本次没有向真实数据库创建管理员。

### 9.26 复习问题

1. 用户身份验证与管理员权限验证分别发生在哪里？
2. 为什么缓存中显示 admin 不代表后端一定放行？
3. 当前本人更新模型扩展 role 后，旧的字段限制结论为何失效？
4. Password.vue 的 camelCase 怎样转换成后端 snake_case？
5. 为什么不用原密码字符串直接与数据库 password 比较？
6. GET 的 params 与 POST/PUT 的 data 有什么区别？
7. total 为什么在 offset/limit 前统计？
8. 第 4 页、页大小 10 的 offset 是多少？
9. #default="{ row }" 从哪里得到 row？
10. nextTick 与 clearValidate 分别解决什么问题？
11. ...userData 在解构和构造对象时分别有什么作用？
12. 编辑用户为什么没有修改密码？
13. status: false 为什么不会被 exclude_none 排除？
14. “禁止删除自己”为什么还需要后端实现？
15. 页面退出登录与服务端撤销 token 有何区别？

**复习自测**

| 问题                                         | 核对要点                                       |
| -------------------------------------------- | ---------------------------------------------- |
| 一个预约已取消，为什么当前用户删除仍被阻止？ | 删除检查保护任意历史归属，不按占用时段规则筛选 |

### 9.27 本节官方参考

- [FastAPI 路径参数与路由顺序](https://fastapi.tiangolo.com/tutorial/path-params/)
- [FastAPI 查询参数校验](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/)
- [SQLAlchemy 条件运算符](https://docs.sqlalchemy.org/en/20/core/operators.html)
- [SQLAlchemy Session 与事务](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [Vue nextTick](https://vuejs.org/api/general.html#nexttick)
- [Vue 计算属性](https://vuejs.org/guide/essentials/computed.html)
- [Element Plus Table](https://element-plus.org/en-US/component/table.html)
- [Element Plus Pagination](https://element-plus.org/en-US/component/pagination.html)
- [Element Plus Radio](https://element-plus.org/en-US/component/radio.html)
- [Element Plus MessageBox](https://element-plus.org/en-US/component/message-box.html)
- [bcrypt 说明](https://github.com/pyca/bcrypt)

### 9.28 本章阶段代码快照（2026-10-14）

以下保存本次核心文件的实际内容，供复习和比较。保留原写法及已经指出的问题；第 8 节快照不被覆盖，便于观察项目怎样逐步演变。

<details>
<summary><code>backend/app/schemas/user.py</code></summary>

```python
from xmlrpc.client import boolean

from pydantic import BaseModel, ConfigDict

from app.utils import password


class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreateRequest(BaseModel):
    username: str
    password: str = "123456"
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role: str = "student"
    status: bool = 1


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role: str | None = None
    status: bool | None = None


class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str
```

</details>

<details>
<summary><code>backend/app/common/response.py</code></summary>

```python
from typing import Any
from pydantic import BaseModel


class Response(BaseModel):
    code: int
    message: str
    data: Any = None

    @classmethod
    def success(cls, message: str = "请求成功", data: Any = None):
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "请求失败"):
        return cls(code=code, message=message)


class PageResponse(BaseModel):
    """分页的返回结果"""

    list: Any = []
    total: int = 0
```

</details>

<details>
<summary><code>backend/app/dependencies/auth.py</code></summary>

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录的用户信息
    """
    try:
        payload = decode_access_token(token=token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的访问令牌")
    except Exception:
        raise HTTPException(status_code=401, detail="无效的访问令牌")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    elif user.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """判断JWT token内角色是否为admin"""
    if current_user.role != "admin":
        raise BusinessException(message="无权限访问", code=403)
    return current_user
```

</details>

<details>
<summary><code>backend/app/services/user_service.py</code></summary>

```python
from operator import or_

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.user import User
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(exclude_none=True)  # pydantic对象转换成字典
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误!")
    if data.old_password == data.new_password:
        raise BusinessException(message="新密码不能跟原密码相同!")
    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    # select * from user where username like '%张%' or name like '%张%';
    query = db.query(User)

    if keywords:
        query = query.filter(
            or_(User.username.ilike(f"%{keywords}%"), User.name.ilike(f"%{keywords}%"))
        )
    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items], total=total
    )


def create_user(db: Session, data: UserCreateRequest):
    """新增用户"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="账号已存在")

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """更新用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    user_dict = data.model_dump(exclude_none=True)
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int, currut_user: User):
    """删除用户"""
    if user_id == currut_user.id:
        raise BusinessException(message="不能删除当前登录的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")

    db.delete(user)
    db.commit()
```

</details>

<details>
<summary><code>backend/app/api/user.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services import user_service

router = APIRouter(prefix="/user", tags=["用户信息"])


@router.get("/me")
def get_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录的用户信息
    """
    return Response.success(data=UserResponse.model_validate(current_user))


@router.put("/me")
def update_user_info(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户信息"""
    res = user_service.update_user_info(db, current_user, data)
    return Response.success(data=res)


@router.put("/password")
def update_password(
    data: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户密码"""
    user_service.update_password(db, current_user, data)
    return Response.success()


@router.get("/list")
def get_user_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.get_user_page_list(db, page, page_size, keywords)
    return Response.success(data=res)


@router.post("")
def create_user(
    data: UserCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.create_user(db, data)
    return Response.success(data=res)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.update_user(db, user_id, data)
    return Response.success(data=res)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user_service.delete_user(db, user_id, current_user)
    return Response.success()
```

</details>

<details>
<summary><code>frontend/src/api/user.js</code></summary>

```js
import request from "@/utils/request";

// 获取个人信息
export function getUserInfo() {
  return request({
    url: "/api/user/me",
    method: "get",
  });
}

// 更新个人信息
export function updateUserInfo(data) {
  return request({
    url: "/api/user/me",
    method: "put",
    data,
  });
}

// 更新用户密码
export function updatePassword(data) {
  return request({
    url: "/api/user/password",
    method: "put",
    data,
  });
}

// 分页模糊查询用户列表
export function getUserPageList(params) {
  return request({
    url: "/api/user/list",
    method: "get",
    params,
  });
}

// 新增用户
export function createUserApi(data) {
  return request({
    url: "/api/user",
    method: "post",
    data,
  });
}

// 修改用户
export function updateUserApi(userId, data) {
  return request({
    url: `/api/user/${userId}`,
    method: "put",
    data,
  });
}

// 删除用户
export function deleteUserApi(userId) {
  return request({
    url: `/api/user/${userId}`,
    method: "delete",
  });
}
```

</details>

<details>
<summary><code>frontend/src/views/Password.vue</code></summary>

```vue
<template>
  <div
    style="width: 420px; max-width: 100%; margin-left: 60px; margin-top: 40px"
  >
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>修改密码</span>
        </div>
      </template>
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-width="100px"
        style="width: 300px; max-width: 100%"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="form.oldPassword" placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="form.newPassword" placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" placeholder="请确认新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="submitting">
            保存修改
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { updatePassword } from "@/api/user";
import router from "@/router";
import { ElMessage } from "element-plus";
import { logout } from "@/utils/auth";

const submitting = ref(false);
const formRef = ref();
const form = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const validatePass = (rule, value, callback) => {
  if (value === "") {
    callback(new Error("请确认密码"));
  } else {
    if (value !== form.newPassword) {
      callback(new Error("两次输入密码不一致!"));
    } else {
      callback();
    }
  }
};

const rules = {
  oldPassword: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  newPassword: [{ required: true, message: "请输入新密码", trigger: "blur" }],
  confirmPassword: [{ validator: validatePass, trigger: "blur" }],
};

const handleSubmit = async () => {
  if (submitting.value) return;
  submitting.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const res = await updatePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword,
    });
    if (res.code === 200) {
      ElMessage.success("修改密码成功");
      logout();
      await router.push("/login");
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return;
  } finally {
    submitting.value = false;
  }
};
</script>
```

</details>

<details>
<summary><code>frontend/src/views/User.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>用户管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入账号或名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="primary" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="avatar" label="头像" width="100">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.avatar"
                style="display: block; width: 50px; height: 50px; border-radius: 50%"
                :src="row.avatar"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="phone" label="手机号" width="160" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            {{ row.role === "admin" ? "管理员" : "学生" }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "正常" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="账号" prop="username" for="user-form-username">
            <el-input
              id="user-form-username"
              :disabled="!!form.id"
              v-model="form.username"
              placeholder="请输入账号"
            />
          </el-form-item>

          <el-form-item
            v-if="!form.id"
            label="密码"
            prop="password"
            for="user-form-password"
          >
            <el-input
              id="user-form-password"
              type="password"
              show-password
              v-model="form.password"
              placeholder="请输入密码"
            />
          </el-form-item>

          <el-form-item label="名称" prop="name" for="user-form-name">
            <el-input
              id="user-form-name"
              v-model="form.name"
              placeholder="请输入名称"
            />
          </el-form-item>

          <el-form-item label="角色" prop="role" for="user-form-role">
            <el-select id="user-form-role" v-model="form.role">
              <el-option label="学生" value="student"></el-option>
              <el-option label="管理员" value="admin"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="邮箱" prop="email" for="user-form-email">
            <el-input
              id="user-form-email"
              v-model="form.email"
              placeholder="请输入邮箱"
            />
          </el-form-item>

          <el-form-item label="手机号" prop="phone" for="user-form-phone">
            <el-input
              id="user-form-phone"
              v-model="form.phone"
              placeholder="请输入手机号"
            />
          </el-form-item>
          <!-- 状态是控件组，使用组件的 aria-labelledby 关联组标签。 -->
          <el-form-item label="状态" prop="status" for="">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">禁用</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getUserPageList,
  createUserApi,
  updateUserApi,
  deleteUserApi,
} from "@/api/user";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: "",
});

// 加载分页数据
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  username: "",
  password: "",
  name: "",
  role: "",
  email: "",
  phone: "",
  avatar: "",
  status: 1,
});

const load = async () => {
  loading.value = true;
  try {
    const res = await getUserPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords,
    });
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = computed(() => ({
  username: [{ required: true, message: "请输入账号", trigger: "blur" }],
  password: form.id
    ? []
    : [
        { required: true, message: "请输入密码", trigger: "blur" },
        { min: 3, max: 10, message: "密码是3-10位", trigger: "blur" },
      ],
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  email: [{ type: "email", message: "邮箱格式错误", trigger: "blur" }],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: "手机号格式错误", trigger: "blur" },
  ],
}));

const resetForm = () => {
  Object.assign(form, {
    id: null,
    username: "",
    password: "",
    name: "",
    role: "student",
    email: "",
    phone: "",
    avatar: "",
    status: 1,
  });
};

const handleSearch = async () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑用户信息
const handleEdit = async (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.role,
    email: row.email,
    phone: row.phone,
    avatar: row.avatar,
    status: row.status,
  });
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 删除用户信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除用户【${row.username}】？`, "确认删除", {
    type: "warning",
  }).then(async () => {
    const res = await deleteUserApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除用户成功");
      load();
    }
  });
};

// 保存用户信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, username, password, ...userData } = form;
    const res = id
      ? await updateUserApi(id, userData)
      : await createUserApi({ username, password, ...userData });
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

onMounted(() => {
  load();
});
</script>
```

</details>

<details>
<summary><code>frontend/src/layouts/Layout.vue</code></summary>

```vue
<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div
              style="display: flex; align-items: center; margin-right: 20px; cursor: pointer"
            >
              <img
                :src="userInfo?.avatar"
                alt=""
                style="width: 30px; border-radius: 50%"
              />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || "用户" }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu router style="height: 100%" default-active="/manager/home">
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>
            <el-menu-item index="/manager/lab">
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/equ">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/user"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu as IconMenu,
  House,
  Setting,
  User,
} from "@element-plus/icons-vue";
import router from "@/router";
import { logout } from "@/utils/auth";
import { useUser } from "@/utils/user";
const { userInfo } = useUser();

const handleLogout = () => {
  logout();
  router.push("/login");
};

const goPerson = () => {
  router.push("/manager/profile");
};

const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/manager/profile");
  } else if (command === "password") {
    router.push("/manager/password");
  } else if (command === "logout") {
    logout();
    router.push("/login");
  }
};
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from "@/utils/auth";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: "/manager/home" },
    {
      path: "/manager",
      name: "Layout",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          name: "Home",
          component: () => import("@/views/Home.vue"),
        },
        {
          path: "lab",
          name: "Lab",
          component: () => import("@/views/Lab.vue"),
        },
        {
          path: "equ",
          name: "Equ",
          component: () => import("@/views/Equ.vue"),
        },
        {
          path: "user",
          name: "User",
          component: () => import("@/views/User.vue"),
        },
        {
          path: "profile",
          name: "Profile",
          component: () => import("@/views/Profile.vue"),
        },
        {
          path: "password",
          name: "Password",
          component: () => import("@/views/Password.vue"),
        },
      ],
    },
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
    },
  ],
});

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken();
  if (to.path === "/login" || to.path === "/register") {
    return true;
  } else {
    return token ? true : "/login";
  }
});

export default router;
```

</details>

### 9.29 本人字段过滤的服务快照（2026-10-15）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/services/user_service.py</code></summary>

```python
from operator import or_

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.user import User
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误!")
    if data.old_password == data.new_password:
        raise BusinessException(message="新密码不能跟原密码相同!")
    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    # select * from user where username like '%张%' or name like '%张%';
    query = db.query(User)

    if keywords:
        query = query.filter(
            or_(User.username.ilike(f"%{keywords}%"), User.name.ilike(f"%{keywords}%"))
        )
    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items], total=total
    )


def create_user(db: Session, data: UserCreateRequest):
    """新增用户"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="账号已存在")

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """更新用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    user_dict = data.model_dump(exclude_none=True)
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int, currut_user: User):
    """删除用户"""
    if user_id == currut_user.id:
        raise BusinessException(message="不能删除当前登录的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")

    db.delete(user)
    db.commit()
```

</details>

### 9.30 本章修补代码快照（2026-10-20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/services/user_service.py</code></summary>

```python
from operator import or_

from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.user import User
from app.models.reservation import Reservation
from app.schemas.user import (
    PasswordUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误!")
    if data.old_password == data.new_password:
        raise BusinessException(message="新密码不能跟原密码相同!")
    user.password = hash_password(data.new_password)
    db.commit()
    db.refresh(user)


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    # select * from user where username like '%张%' or name like '%张%';
    query = db.query(User)

    if keywords:
        query = query.filter(
            or_(User.username.ilike(f"%{keywords}%"), User.name.ilike(f"%{keywords}%"))
        )
    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items], total=total
    )


def create_user(db: Session, data: UserCreateRequest):
    """新增用户"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="账号已存在", code=409)

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if db.query(User.id).filter(User.username == data.username).first():
            raise BusinessException(message="账号已存在", code=409) from exc
        raise
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """更新用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    user_dict = data.model_dump(exclude_none=True)
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(db: Session, user_id: int, currut_user: User):
    """删除用户"""
    if user_id == currut_user.id:
        raise BusinessException(message="不能删除当前登录的账号")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")

    if db.query(Reservation.id).filter(Reservation.user_id == user_id).first():
        raise BusinessException(
            message="该用户存在预约记录，不能删除，可将用户设为禁用状态", code=409
        )

    try:
        db.delete(user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise BusinessException(
            message="该用户存在关联数据，无法删除，可将用户设为禁用状态", code=409
        ) from exc
```

</details>

<details>
<summary><code>frontend/src/views/User.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>用户管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入账号或名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="primary" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="avatar" label="头像" width="100">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.avatar"
                style="display: block; width: 50px; height: 50px; border-radius: 50%"
                :src="row.avatar"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="账号" width="140" />
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="phone" label="手机号" width="160" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            {{ row.role === "admin" ? "管理员" : "学生" }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "正常" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="账号" prop="username" for="user-form-username">
            <el-input
              id="user-form-username"
              :disabled="!!form.id"
              v-model="form.username"
              placeholder="请输入账号"
            />
          </el-form-item>

          <el-form-item
            v-if="!form.id"
            label="密码"
            prop="password"
            for="user-form-password"
          >
            <el-input
              id="user-form-password"
              type="password"
              show-password
              v-model="form.password"
              placeholder="请输入密码"
            />
          </el-form-item>

          <el-form-item label="名称" prop="name" for="user-form-name">
            <el-input
              id="user-form-name"
              v-model="form.name"
              placeholder="请输入名称"
            />
          </el-form-item>

          <el-form-item label="角色" prop="role" for="user-form-role">
            <el-select id="user-form-role" v-model="form.role">
              <el-option label="学生" value="student"></el-option>
              <el-option label="管理员" value="admin"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="邮箱" prop="email" for="user-form-email">
            <el-input
              id="user-form-email"
              v-model="form.email"
              placeholder="请输入邮箱"
            />
          </el-form-item>

          <el-form-item label="手机号" prop="phone" for="user-form-phone">
            <el-input
              id="user-form-phone"
              v-model="form.phone"
              placeholder="请输入手机号"
            />
          </el-form-item>
          <!-- 状态是控件组，使用组件的 aria-labelledby 关联组标签。 -->
          <el-form-item label="状态" prop="status" for="">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">禁用</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getUserPageList,
  createUserApi,
  updateUserApi,
  deleteUserApi,
} from "@/api/user";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: "",
});

// 加载分页数据
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  username: "",
  password: "",
  name: "",
  role: "",
  email: "",
  phone: "",
  avatar: "",
  status: 1,
});

const load = async () => {
  loading.value = true;
  try {
    const res = await getUserPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords,
    });
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = computed(() => ({
  username: [{ required: true, message: "请输入账号", trigger: "blur" }],
  password: form.id
    ? []
    : [
        { required: true, message: "请输入密码", trigger: "blur" },
        { min: 3, max: 10, message: "密码是3-10位", trigger: "blur" },
      ],
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  email: [{ type: "email", message: "邮箱格式错误", trigger: "blur" }],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: "手机号格式错误", trigger: "blur" },
  ],
}));

const resetForm = () => {
  Object.assign(form, {
    id: null,
    username: "",
    password: "",
    name: "",
    role: "student",
    email: "",
    phone: "",
    avatar: "",
    status: 1,
  });
};

const handleSearch = async () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑用户信息
const handleEdit = async (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.role,
    email: row.email,
    phone: row.phone,
    avatar: row.avatar,
    status: row.status,
  });
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 删除用户信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认删除用户【${row.username}】？`,
      "确认删除",
      { type: "warning" },
    );
    const res = await deleteUserApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除用户成功");
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};

// 保存用户信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, username, password, ...userData } = form;
    const res = id
      ? await updateUserApi(id, userData)
      : await createUserApi({ username, password, ...userData });
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

onMounted(() => {
  load();
});
</script>
```

</details>

<a id="14-lab-equipment"></a>

## 10. 实验室与设备管理

阶段起点：2026-10-15。按数据模型、接口、管理页面、校验与关联删除的顺序学习。后续设备分页/重置、容量约束与 labs 表名快照已归入本章。早期“所有查询都要管理员”的版本后来已调整：查询允许登录用户，写入仍校验管理员；学生浏览章说明查询权限扩展。

### 10.1 实验室与设备管理的能力范围

实验室模块维护：

- 实验室名称、简介、封面、位置。
- 容量、每日开始与结束时间。
- 开启或关闭状态。
- 名称搜索、分页、新增、编辑、删除。

设备模块维护：

- 所属实验室、设备名称、说明、图片。
- 型号规格、数量、正常或维修状态。
- 按实验室筛选、设备名称搜索、分页及 CRUD。

当前代码实现的是资源资料管理。不能仅凭系统名称推断已经实现预约时段、预约冲突或 Agent 功能。

Lab.vue 和 Equipment.vue 现在已有真实页面逻辑，早期章节中的占位页面描述属于当时版本。

### 10.2 文件地图

| 层             | 实验室模块                  | 设备模块                          |
| -------------- | --------------------------- | --------------------------------- |
| 数据库模型     | app/models/lab.py           | app/models/equipment.py           |
| 输入与输出模型 | app/schemas/lab.py          | app/schemas/equipment.py          |
| 业务逻辑       | app/services/lab_service.py | app/services/equipment_service.py |
| 后端接口       | app/api/lab.py              | app/api/equipment.py              |
| 前端请求       | src/api/lab.js              | src/api/equipment.js              |
| 页面           | src/views/Lab.vue           | src/views/Equipment.vue           |

还需要理解这些连接位置：

- app/api/**init**.py：把两个后端 router 加入总路由。
- app/main.py：导入模块、创建缺失表、注册应用路由。
- src/router/index.js：把页面组件映射到前端路径。
- src/layouts/Layout.vue：显示管理员菜单。
- 原有文件上传工具：封面或图片上传后，把 URL 存入 img。

这里的 backend/app 和 frontend 前缀在表格中省略，完整快照位于第 10.29 节。

### 10.3 数据设计：一个实验室可以有多条设备记录

```mermaid
erDiagram
    lab ||--o{ equipments : "包含"
    lab {
        int id PK
        string name
        int capacity
        boolean status
    }
    equipments {
        int id PK
        int lab_id FK
        string name
        string spec
        int quantity
        int status
    }
```

图表示数据库关系。当前 ORM 只定义了设备到实验室的属性 Equipment.lab，没有定义 Lab.equipments 集合。

示例：

| lab.id | 实验室       |
| ------ | ------------ |
| 1      | 计算机实验室 |
| 2      | 电子实验室   |

| equipments.id | lab_id | 设备名称 | quantity |
| ------------- | ------ | -------- | -------- |
| 10            | 1      | 工作站   | 20       |
| 11            | 1      | 投影仪   | 1        |
| 12            | 2      | 示波器   | 8        |

设备通过实验室 ID 建立关联。实验室更名后，不需要把所有设备中的名字都重写一次。

一条设备记录可以代表某类设备及其数量；当前没有给每一件物理设备单独分配资产编号。

### 10.4 Lab 数据库模型

当前表名是单数 lab。继承 Base 后，也拥有 id、create_time、update_time。

主要字段：

| 字段                   | 类型与含义                       |
| ---------------------- | -------------------------------- |
| name                   | String(50)，名称                 |
| description            | String(500)，简介，可为 NULL     |
| img                    | String(100)，封面 URL，可为 NULL |
| location               | String(100)，位置，可为 NULL     |
| capacity               | Integer，容量，ORM 默认 0        |
| open_time / close_time | String(20)，开始和结束时间       |
| status                 | Boolean，默认 True               |

Mapped 描述映射属性，mapped_column 声明列。数据库字段有长度不等于 Pydantic 请求模型已经设置同样的长度限制。

当前 description、img 等使用 Mapped[str]，同时明确 nullable=True，数据库仍允许 NULL；注解若写成 str | None，会与可空含义更一致。

status 的 True/False 在页面中显示为开启/关闭，编辑单选框也使用 :value="true" 与 :value="false"，类型是对应的。

表名演进：本节早期快照使用 lab；预约阶段已改为 labs。旧库需核对迁移、ID 与外键，不能混用两种表名的模型；变化原因见第 12.4 节。

### 10.5 Equipment 的 ForeignKey 与 relationship

当前定义：

```python
lab_id: Mapped[int] = mapped_column(
    ForeignKey("lab.id"),
    comment="所属实验室",
    nullable=False,
)

lab: Mapped[Lab] = relationship()
```

两部分作用不同：

| 定义                 | 作用                             |
| -------------------- | -------------------------------- |
| lab_id 列            | 存储所属实验室 ID                |
| ForeignKey("lab.id") | 声明数据库外键，指向表 lab 的 id |
| lab 属性             | 通过 ORM 访问对应的 Lab 对象     |

ForeignKey 字符串中的 lab 是数据库表名，不是 Python 类名 Lab。Mapped[Lab] 中的 Lab 则是 Python 模型类。

因此可以这样理解：

```python
equipment.lab_id
equipment.lab
equipment.lab.name
```

分别取得实验室 ID、实验室对象、实验室名称。relationship 本身不是“额外存一份实验室”的数据库列。[SQLAlchemy 多对一关系](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#many-to-one)

Equipment 的表名为 equipments，其他字段包括 name、description、img、spec、quantity、status。

当前 status: Mapped[int] 没显式写 Integer，SQLAlchemy 可以根据映射注解推断整数类型。1 表示正常，0 表示维修。

### 10.6 两种 status 与数字字段不能混淆

| 字段               | 当前类型 | 页面含义             |
| ------------------ | -------- | -------------------- |
| Lab.status         | bool     | 开启/关闭或正常/禁用 |
| Equipment.status   | int      | 1 正常，0 维修       |
| Lab.capacity       | int      | 容量                 |
| Equipment.quantity | int      | 数量                 |

实验室状态与设备状态表达不同业务事实。实验室关闭并不自动把所有设备改成维修。

当前新增设备服务只确认实验室存在，没有要求它必须开启。所以管理员目前可以维护关闭实验室中的设备。

数量和状态的 0 也不同：quantity=0 表示数量为零，status=0 表示维修。当前后端模型没有范围限制，quantity 为零甚至负数都需要额外规则才能拒绝。

### 10.7 Create、Update、Response 三种模型

两个模块各有三类 Pydantic 模型：

| 模型          | 用途                             |
| ------------- | -------------------------------- |
| CreateRequest | 新建一条记录需要的字段与默认值   |
| UpdateRequest | 更新允许修改的字段，通常允许省略 |
| Response      | 返回给前端的字段结构             |

实验室创建要求 name，默认 capacity=0、status=True。设备创建要求 lab_id 和 name，默认 quantity=1、status=1。

更新模型中的字段使用默认 None，配合 exclude_none=True，表示当前写法跳过值为 None 的字段。

两个响应模型都用 from_attributes=True 从 ORM 属性读取。EquipmentResponse 还增加了 lab_name，用于页面展示实验室名称。

img 保存图片 URL，不保存图片二进制。LabResponse 的 capacity 虽然返回了，当前实验室表格没有单独显示容量列；表单和数据库中仍可以有这个值。

### 10.8 新语法：字典的 \*\* 解包

实验室创建：

```python
lab = Lab(**data.model_dump(exclude_none=True))
```

例如：

```python
payload = {
    "name": "计算机实验室",
    "capacity": 20,
    "status": True,
}

lab = Lab(**payload)
```

相当于：

```python
lab = Lab(
    name="计算机实验室",
    capacity=20,
    status=True,
)
```

这里的 \*\* 把字典拆成关键字参数，不是进行乘法或幂运算。键名需要对应构造对象可以接收的属性。

设备创建使用 Equipment(\*\*data.model_dump())，没有排除 None。其可空说明、图片和规格字段可以接收 None。

### 10.9 当前后端接口与权限

| 模块   | 方法   | 地址                          | 操作                       |
| ------ | ------ | ----------------------------- | -------------------------- |
| 实验室 | GET    | /api/lab/list                 | 搜索分页                   |
| 实验室 | POST   | /api/lab                      | 创建                       |
| 实验室 | PUT    | /api/lab/{lab_id}             | 修改                       |
| 实验室 | DELETE | /api/lab/{lab_id}             | 删除                       |
| 设备   | GET    | /api/equipment/list           | 搜索分页，可按 lab_id 筛选 |
| 设备   | POST   | /api/equipment                | 创建                       |
| 设备   | PUT    | /api/equipment/{equipment_id} | 修改                       |
| 设备   | DELETE | /api/equipment/{equipment_id} | 删除                       |

8 个接口都声明 Depends(get_current_admin)。本次检查确认它们都接入该依赖，不只是前端隐藏按钮。

依赖会先完成用户认证和管理员校验。服务函数通常假设调用者已经经过 API 层权限检查，服务函数本身没有重复检查管理员。

### 10.10 为什么新增 Equipment 表不要求 main 显式导入它

main 中直接导入了 User 和 Lab，同时还在 create_all 前导入总 API。当前导入链包括：

```text
main
  → app.api
  → app.api.equipment
  → app.services.equipment_service
  → app.models.equipment
  → Equipment 加入 Base.metadata
```

因此，不能因为 main 没有写 from app.models.equipment import Equipment，就认定设备表一定不会创建。

关键是调用 Base.metadata.create_all 时，模型类是否已经加载到同一个 Base 的元数据中。

ForeignKey 定义了表依赖，SQLAlchemy 可据此安排新表的创建顺序。create_all 仍不会自动迁移旧表，尤其不能假定旧设备表会自动补上新外键。

### 10.11 实验室列表与增删改的调用过程

```text
Lab.vue 的 load
  → getLabPageList({page, page_size, keywords})
  → GET /api/lab/list
  → 管理员依赖
  → lab_service.get_lab_page_list
  → 查询、计数、倒序和分页
  → PageResponse
  → tableData 与 total
```

搜索当前只匹配 Lab.name。页面输入提示仍写“账号或名称”，属于从用户模块复用后尚未调整的文案。

新建先按名称查询重名，再创建对象、add、commit、refresh。删除和修改会先查询目标，不存在时抛 BusinessException。

当前创建会查重，但 update_lab 没有检查“改名后与其他实验室重名”，模型也没有数据库唯一约束。本次隔离验证确认可以把两个实验室改成同名。

这说明“创建时有一次查重”不等于“所有入口和并发请求都有唯一性保证”。

### 10.12 每次打开表单的默认值

Lab.vue 的初始 form.capacity 为 1，但 resetForm 中设为 20：

```js
{
  id: null,
  name: '',
  description: '',
  img: '',
  location: '',
  capacity: 20,
  open_time: '08:30',
  close_time: '20:30',
  status: true
}
```

点击新增时先调用 resetForm，所以新建窗口实际显示的是重置后的默认值。

编辑时也先重置，再用 row 覆盖。Object.assign 修改现有响应式对象的属性，新增/编辑仍通过 form.id 选择不同 API。

模板中的 form="user-form" 仍沿用原用户页面的 ID 名字。只要它与本页 form 的 id 一致，当前提交可以工作；命名可以整理为更符合模块的值。若未来在同一文档同时挂载多个相同 ID 的表单，则需要避免冲突。

### 10.13 容量输入与整数校验

当前模板：

```html
<el-input :min="1" v-model="form.capacity" />
```

校验规则要求 integer。普通 el-input 作为文本输入，编辑后通常产生字符串，例如 "30"。:min 不会自动把字符串转换成数字，也不等于整数输入控件。

本次按本地 Element Plus 的规则处理方式验证：

| 值          | 整数规则结果 |
| ----------- | ------------ |
| 数字 30     | 通过         |
| 字符串 "30" | 不通过       |

因此，未修改的数字回填可能正常，但用户编辑容量后可能无法提交。

参考调整是使用数值组件：

```html
<el-input-number v-model="form.capacity" :min="1" />
```

这只是笔记中的建议，没有写入源码。后端也应按业务决定容量是否允许 0，并在输入模型中保持一致的范围要求。

<a id="lab-capacity"></a>

### 10.14 实验室容量：数字控件与后端正数约束

实验室容量控件改为：

```html
<el-input-number
  v-model="form.capacity"
  :min="1"
  :precision="0"
  placeholder="请输入容量"
/>
```

数值控件使表单接收数值，避免原先 el-input 输入得到 "30" 字符串，却拿去做整数表单校验的冲突。

后端也增加约束：

```python
# 创建模型
capacity: int = Field(gt=0)

# 更新模型
capacity: int | None = Field(default=None, gt=0)
```

gt 是 greater than 的缩写。创建时没有默认值，表示容量必填且必须大于 0；更新时可以不传，提供时也必须大于 0。当前服务排除 None，所以不传容量不会把已有值清空。

这属于请求模型的类型和数值限制，不是已经给数据库新增 CHECK 约束，也没有修复其他设备数量、状态、开放时间规则。已有库中的负容量记录不会因为改了请求模型就自动更正。

### 10.15 时间选择器：显示格式与绑定格式

当前组件同时设置：

```html
<el-time-picker v-model="form.open_time" format="HH:mm" value-format="HH:mm" />
```

- format 控制输入框显示什么格式。
- value-format 控制绑定到 form 的值采用什么格式。

因此当前可以把 "08:30" 这样的字符串交给后端，而不是必须传一个 JavaScript Date 对象。[Element Plus TimePicker](https://element-plus.org/en-US/component/time-picker)

后端当前用 String(20) 和 str 保存时间，没有验证真实时间格式、开始结束顺序或跨夜规则。本次隔离检查确认 "25:99" 等字符串仍能通过当前模型并保存。

如果控件清空后提交 null，更新服务会用 exclude_none 跳过它，旧时间可能保留。需明确清空与跨夜的业务含义，再统一前后端规则。

### 10.16 设备页为什么先加载实验室选项

设备页面需要一份实验室列表：

```js
const labOptions = ref([]);

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });

  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};
```

它同时供两个下拉框使用：

- 查询区：选择实验室，筛选设备。
- 编辑表单：决定设备归属于哪个实验室。

选项：

```html
<el-option
  v-for="item in labOptions"
  :key="item.id"
  :label="item.name"
  :value="item.id"
/>
```

label 是用户看到的名称，value 是选中后保存的 ID，key 帮助 Vue 识别重复渲染中的各选项。三个属性的职责不同。

因此选择“计算机实验室”后，form.lab_id 中保存的是数字 ID，不是名称字符串。

onMounted 中分别调用 loadLabs 和 load，没有等待前一个完成。两次请求可以各自进行，因为设备列表的 lab_name 已由后端提供，不依赖前端选项列表拼接名称。

当前选项请求只取前 100 条。如果实验室超过 100 个，下拉框并不包含全部实验室；后续可选择分页加载或远程搜索。

### 10.17 按实验室和关键词组合筛选

设备查询：

```python
query = db.query(Equipment)

if lab_id is not None:
    query = query.filter(Equipment.lab_id == lab_id)

if keywords:
    query = query.filter(
        Equipment.name.ilike(f"%{keywords}%")
    )
```

连续 filter 的条件组合为 AND：

```text
属于指定实验室
并且
设备名称匹配关键词
```

is not None 表示明确判断是否提供值。即使 lab_id=0，也会执行这个筛选，而不是因为 0 为假就返回所有实验室设备。本次验证确认 ID 0 得到空结果。

前端下拉 change 调用 handleSearch，把页码重置到 1，再读取筛选结果。清空筛选时需要检查实际发出的参数；null 或 undefined 通常由 Axios 略过，不应把空字符串作为整数 ID 发送。

当前页面提示“请输入设备名称或型号”，但服务只搜索 Equipment.name，没有搜索 spec。隔离验证中，只出现在 spec 的关键词查不到设备。

可以选择把提示改为设备名称，或在后端明确加入 name 与 spec 的 OR 搜索。本次未修改这一行为。

### 10.18 创建设备：先查实验室，再查同名记录

服务顺序：

```text
根据 lab_id 查实验室
  → 不存在则拒绝
  → 查询同一实验室内是否有同名设备
  → 重复则拒绝
  → 创建 Equipment
  → 提交、刷新
  → 返回设备和实验室名称
```

重复判断：

```python
db.query(Equipment).filter(
    Equipment.lab_id == data.lab_id,
    Equipment.name == data.name,
).first()
```

filter 的多个参数也是 AND 关系。

当前规则：

| 情况                                  | 结果         |
| ------------------------------------- | ------------ |
| A 实验室已有“工作站”，再在 A 新建同名 | 拒绝         |
| A 实验室已有“工作站”，在 B 新建同名   | 允许         |
| A 的设备名称相同，但规格不同          | 仍按同名拒绝 |

规格不是当前查重条件的一部分，设备也不是全局名称唯一。

这项规则目前通过服务查询实现，模型没有 (lab_id, name) 组合唯一约束。若要在并发创建时仍保证唯一，需要数据库约束和相应的异常处理。

### 10.19 更新设备：先确定修改后的实验室与名称

当前核心代码：

```python
payload = data.model_dump(exclude_none=True)

lab_id = payload.get("lab_id", equipment.lab_id)
name = payload.get("name", equipment.name)
```

字典 get 的第二个参数是“键不存在时使用的默认值”。

- 本次传了 lab_id：使用目标实验室。
- 没传 lab_id：使用设备原来的实验室。
- name 同理。

因为前面排除了 None，传入 None 的字段也不会出现在 payload 中。

接着先确认目标实验室存在，再检查新的“实验室 ID + 名称”是否与其他设备冲突：

```python
exist = (
    db.query(Equipment)
    .filter(
        Equipment.lab_id == lab_id,
        Equipment.name == name,
        Equipment.id != equipment.id,
    )
    .first()
)
```

最后一个条件排除设备自己。否则只是保存原名称，也可能把自己误认为重复记录。

这里先检查修改后的组合，再执行 setattr，能够处理：

- 只改名称。
- 只改所属实验室。
- 同时改名称和所属实验室。

本次验证确认：移动到存在同名设备的实验室会被拒绝；移动并改成不冲突名称后成功，返回的新 lab_name 也正确。

quantity=0、status=0 不会被 exclude_none 排除，当前服务仍会保存。这是字段范围需要另行校验的地方，不是 exclude_none 自动过滤所有假值。

### 10.20 lab_name 为什么要手动补充

列表服务中：

```python
result = []

for item in items:
    data = EquipmentResponse.model_validate(item)
    data.lab_name = item.lab.name if item.lab else None
    result.append(data)
```

Equipment 模型没有 lab_name 列，而响应模型希望提供这个展示字段。

from_attributes=True 按字段名读取属性，不会自动把 lab_name 理解为 lab.name。所以服务先生成设备响应，再通过关联对象补上名称。

`item.lab.name if item.lab else None` 是 Python 条件表达式：

```text
关联实验室存在时取名称，否则使用 None
```

创建与更新服务也做了相同补充，因此返回结构保持一致。

#### relationship 可能额外查询数据库

默认关系加载通常是按需加载：第一次访问 item.lab 时，可能再发 SQL 查询。

本次在一个新的会话中查询 3 条设备，属于 2 个实验室，共观察到 4 次 SELECT：

1. 统计设备总数。
2. 查询分页设备记录。
3. 读取第一个实验室。
4. 读取第二个实验室。

同一个会话的缓存会影响次数，所以不是每条设备都必然多查一次。

数据量增大时，可以考虑提前加载关联，例如：

```python
from sqlalchemy.orm import selectinload

query = db.query(Equipment).options(
    selectinload(Equipment.lab)
)
```

这是优化方向，未改入当前服务。[SQLAlchemy 关系加载](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#select-in-loading)

### 10.21 删除实验室与外键约束

当前删除实验室服务只做：

```text
查实验室
  → 不存在则抛业务异常
  → db.delete
  → db.commit
```

没有先检查是否还有设备，也没有定义级联删除。

在当前模型首次正确建表、数据库启用外键约束时，仍有设备引用的实验室通常不能直接删除。本次打开 SQLite 外键检查后，确认该删除产生 IntegrityError。

ForeignKey 不代表自动删除所有关联设备。当前关系没有配置删除级联；删除设备也不会因为它有 lab 属性就自动删除实验室。[SQLAlchemy 外键删除规则](https://docs.sqlalchemy.org/en/20/core/constraints.html#on-update-on-delete)

需要按业务决定：

- 有设备时明确拒绝，并返回可理解的业务提示。
- 先把设备迁移或处理完，再删除实验室。
- 如果确实需要级联删除，单独设计和验证其范围。

本次没有替你选择或实施级联行为。真实 MySQL 表是否已经拥有外键，需要单独核对；create_all 不会替旧表补齐缺失约束。

<a id="resource-deletion"></a>

### 10.22 实验室与设备删除：保留历史归属并处理关联竞争

当前服务在删除前检查关联记录：

| 删除对象 | 服务先检查什么           | 存在关联时的结果                 |
| -------- | ------------------------ | -------------------------------- |
| 实验室   | 是否有预约；是否仍有设备 | 拒绝，提示关闭实验室或先处理设备 |
| 设备     | 是否有任意预约记录       | 拒绝删除                         |

“任意预约”包含已取消、已拒绝和过去的记录；保护历史归属与判断未来时段是否被占用是两件事。检查结束到提交之间仍可能出现新关联，服务还会捕获 IntegrityError、回滚并返回业务提示。前端 Lab.vue、Equipment.vue 将确认框和删除请求放在同一个 try/catch 中，取消、关闭及请求失败都结束本次操作；完整 Promise 示例见[用户删除](#user-deletion)。

Equipment.vue 的删除按钮在 2026-10-20 已恢复，早期快照中“只有编辑入口”只描述当时阶段。

### 10.23 设备重置与分页绑定的历史问题

#### 1. resetForm 仍包含实验室字段

当前设备页重置包含：

```text
location、capacity、open_time、close_time、status: true
```

却没有重置设备需要的：

```text
lab_id、spec、quantity
```

Object.assign 只覆盖列出的键，不删除其他键。因此从编辑设备再切到新增时，可能继承上一个设备的实验室、规格和数量。

本次执行实际 resetForm 代码后确认这些旧值会保留，并会向对象加入实验室专有字段。

status 也被改成布尔 true，而设备单选框使用数字 1/0，导致选中显示的类型不一致。

参考重置内容如下，未写入源码：

```js
const resetForm = () => {
  Object.assign(form, {
    id: null,
    lab_id: null,
    name: "",
    description: "",
    img: "",
    spec: "",
    quantity: 1,
    status: 1,
  });
};
```

应与设备 form 的初始结构一致。Object.assign 不会删除早先已经加进去的多余属性；修正后也应在干净页面状态中检查，必要时清理多余键。

额外实验室字段通常会被 Pydantic 忽略，所以“不立即报接口错误”不代表重置逻辑正确。

#### 2. pageSize 与 page_size 不是同一个属性

设备 params 声明：

```js
{
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
}
```

但分页组件绑定 params.pageSize。JavaScript 属性名区分这些写法，不会自动对应。

实际列表请求直接传整个 params，读取的是 page_size。给 params.pageSize 赋值不会改变 page_size；本次函数检查确认这一点。

参考绑定：

```html
v-model:page-size="params.page_size"
```

当前默认页大小都是 10，可能掩盖问题。如果以后显示 sizes 选择器，还应处理页大小改变后的重新查询。

设备 resetForm、分页和删除入口的后续调整已放在本节之后；下面的旧问题用于解释触发原因，最终实现以带日期的后续说明与当前代码为准。

### 10.24 设备管理：分页字段与删除入口的阶段调整

第一项改动是前面指出的分页绑定已经修正：

```html
v-model:page-size="params.page_size"
```

现在模板绑定和请求对象使用同一个属性。本次读取与静态检查已经确认，因此第 18.6 节对应任务改为完成。

当前 layout 没有 sizes 项，也就没有页大小选择器。如果以后加上，仍需要处理页大小变化后的页码和重新加载。

第二项改动是模板删除了“删除”按钮，现在行操作只显示“编辑”。但是：

- Equipment.vue 中的 handleDelete 逻辑还保留着。
- frontend/src/api/equipment.js 仍有删除请求函数。
- 后端 DELETE /api/equipment/{equipment_id} 仍保留管理员依赖及删除逻辑。

所以这是界面入口的变化，不能写成“后端删除功能已经移除”。之后可以根据产品需求恢复入口，或清理不再使用的代码。

第三项是 handleSearch 不再声明 async。它内部只是设置页码并调用 load，没有 await；去掉 async 符合当前写法，也不会因此停止请求。当前调用方仍没有等待 load 完成。

当时 Equipment.vue.resetForm 复制实验室字段的问题仍存在：lab_id、spec、quantity 没有正确重置，status 被写成布尔 true。这里没有因为分页修复就一并解决，当时仍保留待办；2026-10-20 的实际重置修补见紧接着的下一节。

### 10.25 设备表单：按实际字段重置新增状态

设备 resetForm 现在覆盖：

```js
Object.assign(form, {
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});
```

这样从编辑切到新增时，实验室、型号、数量都恢复默认，status 保持与设备单选项一致的数字 1。早期重置函数残留的 location、capacity、开放时间等实验室字段不再由这个重置函数添加。

Object.assign 只覆盖列出的键；修补后应在重新加载的干净页面状态检查，不能指望它删除旧运行状态里曾经存在的额外属性。

### 10.26 图片上传与复用结构时的核对项

两页都复用 uploadFileApi，流程与头像一致：

```text
选文件
  → 前端类型与大小检查
  → FormData 上传
  → 后端返回 /uploads/... URL
  → form.img 显示预览
  → 保存实验室或设备时写入 img
```

上传成功不等于资源记录已经保存，取消弹窗也不会自动删除已上传文件。

两页上传函数仍有空 catch，成功后没有明确 return 响应；上传组件的 Promise 状态问题与第 8.16 节相同。上传未完成时提前保存，也需要检查是否会提交旧图片地址。

当前其他核对项：

| 当前事实                                             | 需要处理或确认                           |
| ---------------------------------------------------- | ---------------------------------------- |
| 实验室搜索提示仍写账号                               | 与实际只按名称查询的行为一致             |
| 设备搜索提示包含型号                                 | 决定加入 spec 搜索还是更正文案           |
| 编辑设备未等待 nextTick 清理校验                     | 检查上次错误是否残留                     |
| 实验室下拉只取前 100 条                              | 规模增大后需要完整选项加载策略           |
| 两页确认删除没有 catch                               | 处理取消与网络失败的 Promise             |
| 后端未限制容量、数量、状态取值、时间格式和字符串长度 | 根据业务统一前后端校验                   |
| 页码与页大小未设范围                                 | 避免无效分页参数                         |
| 实验室改名不查重                                     | 补齐更新路径及数据库唯一性策略           |
| 所有页面 form ID 仍叫 user-form                      | 核对当前匹配关系和未来同时挂载时的唯一性 |

lab_service 中还保留 get_lab_info、update_Lab_info 等未被当前 API 调用的函数，以及密码工具等未使用导入。这些可整理，但它们不会因为定义在文件里就自动执行。

特别是 update_Lab_info 中排除 status，不代表当前实验室更新无法改状态。API 调用的是 update_lab，后者会保存 status。应沿实际调用链分析。

### 10.27 本次验证记录与实际验收

#### 已完成

- 23 组隔离检查，使用实际模型、schema 和服务函数。
- 实验室创建、重复名称拒绝、搜索分页、零值与 False 更新、空记录删除。
- 设备所属实验室、同名规则、名称搜索与实验室组合筛选。
- 设备更新排除自己、移动实验室冲突检查、新 lab_name 返回。
- 设备删除、目标不存在、仍有设备的实验室删除失败。
- 确认当前实验室改名允许重名，范围和时间约束不足。
- 确认只出现在 spec 的关键词不会匹配当前设备查询。
- 确认默认懒加载下 3 条设备、2 个实验室产生 4 次 SELECT。
- 检查 8 个新 API 都引用管理员依赖。
- Lab.vue、Equipment.vue、Layout.vue 通过脚本与模板编译。
- 两个前端 API 文件和路由通过 JavaScript 语法检查。
- 执行实际设备 resetForm，确认旧字段残留和混入实验室字段。
- 按本地 Element Plus 的规则过滤方式，确认数字容量通过、数字字符串不通过整数校验。
- 确认分页属性名不一致。
- 确认本人资料服务已过滤角色和状态。

隔离数据库启用了外键检查，没有导入真实数据库配置。语法检查不等于浏览器完整交互，静态权限依赖检查也不等于完整 HTTP 认证验收。

#### 实验室页面

- [ ] 管理员能进入实验室页面，普通用户被后端拒绝。
- [ ] 名称搜索、清空搜索、翻页和总数正确。
- [ ] 新增默认容量和时间符合预期。
- [ ] 容量编辑后保持数字并能提交。
- [ ] 时间显示、请求字符串、清空与跨夜规则一致。
- [ ] 封面上传、预览、保存和重新进入页面正确。
- [ ] 修改状态后再次查询显示正确。
- [ ] 重复创建、重复改名按约定处理。
- [ ] 空实验室可删除，有设备时返回符合约定的提示。

#### 设备页面

- [ ] 实验室下拉显示名称，提交值为对应 ID。
- [ ] 实验室筛选与关键词同时生效，清空筛选不产生错误整数参数。
- [ ] 设备名称与规格搜索行为和提示一致。
- [ ] 打开新增前不保留上个设备的 lab_id、spec、quantity。
- [ ] 新增和编辑的状态单选值与类型一致。
- [ ] 同一实验室同名被拒绝，不同实验室同名按当前规则允许。
- [ ] 只改数量、只改名称和迁移实验室都正确。
- [ ] 编辑同一记录不被误判为重复。
- [ ] 表格中的 lab_name 跟随所属实验室变化。
- [ ] 图片、数量、维修状态可以保存并回填。
- [ ] 分页字段和发送参数一致。
- [ ] 超过 100 个实验室时选项仍满足使用需求。
- [ ] 取消删除不请求 DELETE，失败后加载状态恢复。

### 10.28 继续复现的顺序与参考资料

建议按数据依赖顺序：

1. 添加 Lab 模型和实验室输入、输出模型。
2. 添加 Equipment 模型，外键指向 lab.id，定义 lab 关系。
3. 实现实验室 CRUD 与分页服务。
4. 实现设备筛选、创建、更新查重、删除和 lab_name。
5. 添加两个 API router，接入管理员依赖和总 API。
6. 确认模型在 create_all 前加载；旧表单独处理迁移。
7. 添加前端 lab.js、equipment.js。
8. 实现 Lab.vue，复用分页和弹窗结构并核对字段。
9. 实现 Equipment.vue，加载实验室选项并处理设备专有字段。
10. 更新路由为 /manager/lab 与 /manager/equipment，匹配菜单。
11. 处理当前重置、容量、分页、搜索和删除规则问题。
12. 先创建学习实验室，再使用真实返回的 lab.id 创建设备。
13. 完成第 10.27 节的实际功能检查。

旧设备路径 /manager/equ 已改成 /manager/equipment，组件也变成 Equipment.vue。当前没有给旧路径配置别名或重定向，不会自动映射过去。

从包中导入 lab_service、equipment_service，会加载相应子模块；不要求把所有服务代码写进 services/**init**.py。

复习时尝试回答：

- 外键与 relationship 分别解决什么问题？
- 为什么下拉框显示名称却提交 ID？
- 为什么 model_validate 不会自动生成 lab_name？
- 更新时为什么检查修改后的实验室与名称，并排除自己？
- Object.assign 为什么没有清空旧的设备字段？
- 为什么 numeric string 不一定能通过整数校验？
- 为什么 ForeignKey 不等于自动级联删除？
- 为什么查询设备时可能额外查询实验室？
- 为什么定义了未使用的函数不等于 API 会调用它？

官方资料：

- [SQLAlchemy 多对一关系](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#many-to-one)
- [SQLAlchemy 外键与约束](https://docs.sqlalchemy.org/en/20/core/constraints.html)
- [SQLAlchemy 关系加载](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
- [Element Plus TimePicker](https://element-plus.org/en-US/component/time-picker)
- [Element Plus Input Number](https://element-plus.org/en-US/component/input-number)
- [Vue 表单绑定](https://vuejs.org/guide/essentials/forms.html)
- [Pydantic 序列化与字段排除](https://docs.pydantic.dev/latest/concepts/serialization/)

### 10.29 本章阶段代码快照（2026-10-15）

以下保存本次实验室、设备模块及其连接文件，也保留本人资料字段过滤修正。它们是实际源码，包含已说明的待处理问题，没有自动改成参考方案。

<details>
<summary><code>backend/app/models/lab.py</code></summary>

```python
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Integer, String


class Lab(Base):
    __tablename__ = "lab"
    __table_args__ = {"comment": "实验室信息"}

    name: Mapped[str] = mapped_column(String(50), comment="名称")
    description: Mapped[str] = mapped_column(String(500), comment="简介", nullable=True)
    img: Mapped[str] = mapped_column(String(100), comment="封面", nullable=True)
    location: Mapped[str] = mapped_column(String(100), comment="位置", nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, comment="容量", default=0)
    open_time: Mapped[str] = mapped_column(
        String(20), comment="开放的开始时间", nullable=True
    )
    close_time: Mapped[str] = mapped_column(
        String(20), comment="开放的结束时间", nullable=True
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态: True-启用, False-禁用"
    )
```

</details>

<details>
<summary><code>backend/app/models/equipment.py</code></summary>

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Integer, String
from app.database import Base
from app.models.lab import Lab


class Equipment(Base):
    __tablename__ = "equipments"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(
        ForeignKey("lab.id"), comment="所属实验室", nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), comment="设备名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(500), comment="说明", nullable=True
    )
    img: Mapped[str | None] = mapped_column(String(200), comment="图片", nullable=True)
    spec: Mapped[str | None] = mapped_column(
        String(100), comment="型号规格", nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, comment="数量", default=1)
    status: Mapped[int] = mapped_column(default=1, comment="状态(0-维修,1-正常)")

    lab: Mapped[Lab] = relationship()
```

</details>

<details>
<summary><code>backend/app/schemas/lab.py</code></summary>

```python
from pydantic import BaseModel, ConfigDict


class LabResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int
    open_time: str | None = None
    close_time: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)


class LabCreateRequest(BaseModel):
    name: str
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int = 0
    open_time: str | None = None
    close_time: str | None = None
    status: bool = True


class LabUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int | None = None
    open_time: str | None = None
    close_time: str | None = None
    status: bool | None = None
```

</details>

<details>
<summary><code>backend/app/schemas/equipment.py</code></summary>

```python
from pydantic import BaseModel, ConfigDict


class EquipmentResponse(BaseModel):
    id: int
    lab_id: int
    lab_name: str | None = None
    name: str
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int
    status: int

    model_config = ConfigDict(from_attributes=True)


class EquipmentCreateRequest(BaseModel):
    lab_id: int
    name: str
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int = 1
    status: int = 1


class EquipmentUpdateRequest(BaseModel):
    lab_id: int | None = None
    name: str | None = None
    description: str | None = None
    img: str | None = None
    spec: str | None = None
    quantity: int | None = None
    status: int | None = None
```

</details>

<details>
<summary><code>backend/app/services/lab_service.py</code></summary>

```python
from operator import or_
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.lab import Lab
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_lab_info(Lab: Lab) -> LabResponse:
    return LabResponse.model_validate(Lab)


def update_Lab_info(db: Session, Lab: Lab, data: LabUpdateRequest):
    Lab_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in Lab_dict.items():
        setattr(Lab, field, value)
    db.commit()
    db.refresh(Lab)
    return LabResponse.model_validate(Lab)


def get_lab_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    # select * from Lab where name like '%计算机实验室%'
    query = db.query(Lab)

    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items], total=total
    )


def create_lab(db: Session, data: LabCreateRequest):
    """新增"""

    exist = db.query(Lab).filter(Lab.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室已存在")

    lab = Lab(
        **data.model_dump(exclude_none=True)
    )  # {"key1": "value1", "key2": "value2"} -> key1=value1, key2=value2
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, Lab_id: int, data: LabUpdateRequest):
    """更新"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    Lab_dict = data.model_dump(exclude_none=True)
    for field, value in Lab_dict.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, Lab_id: int):
    """删除"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    db.delete(lab)
    db.commit()
```

</details>

<details>
<summary><code>backend/app/services/equipment_service.py</code></summary>

```python
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.schemas.equipment import (
    EquipmentResponse,
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
)
from sqlalchemy.orm import Session


def get_equipment_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    lab_id: int | None = None,
):
    """分页模糊查询列表"""

    # select * from equipment where name like '%计算机%';
    query = db.query(Equipment)
    if lab_id is not None:
        query = query.filter(Equipment.lab_id == lab_id)
    if keywords:
        query = query.filter(Equipment.name.ilike(f"%{keywords}%"))
    total = query.count()
    items = (
        query.order_by(Equipment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        data = EquipmentResponse.model_validate(item)
        data.lab_name = item.lab.name if item.lab else None
        result.append(data)
    return PageResponse(list=result, total=total)


def create_equipment(db: Session, data: EquipmentCreateRequest):
    """新增"""
    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(Equipment.lab_id == data.lab_id, Equipment.name == data.name)
        .first()
    )
    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdateRequest):
    """更新"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")

    payload = data.model_dump(exclude_none=True)
    lab_id = payload.get("lab_id", equipment.lab_id)
    name = payload.get("name", equipment.name)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(
            Equipment.lab_id == lab_id,
            Equipment.name == name,
            Equipment.id != equipment.id,
        )
        .first()
    )

    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")

    for field, value in payload.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def delete_equipment(db: Session, equipment_id: int):
    """删除"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")
    db.delete(equipment)
    db.commit()
```

</details>

<details>
<summary><code>backend/app/api/lab.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.lab import Lab
from app.models.user import User
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from app.services import lab_service

router = APIRouter(prefix="/lab", tags=["实验室信息"])


@router.get("/list")
def get_lab_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab_page_list(db, page, page_size, keywords)
    return Response.success(data=res)


@router.post("")
def create_lab(
    data: LabCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.create_lab(db, data)
    return Response.success(data=res)


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.update_lab(db, lab_id, data)
    return Response.success(data=res)


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab_service.delete_lab(db, lab_id)
    return Response.success()
```

</details>

<details>
<summary><code>backend/app/api/equipment.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.models.user import User
from app.dependencies.auth import get_current_admin
from app.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
)
from app.services import equipment_service
from app.database import get_db

router = APIRouter(prefix="/equipment", tags=["实验室设备接口"])


@router.get("/list")
def get_equipment_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    lab_id: int | None = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = equipment_service.get_equipment_page_list(
        db, page, page_size, keywords, lab_id
    )
    return Response.success(data=res)


@router.post("")
def create_equipment(
    data: EquipmentCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = equipment_service.create_equipment(db, data)
    return Response.success(data=res)


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = equipment_service.update_equipment(db, equipment_id, data)
    return Response.success(data=res)


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment_service.delete_equipment(db, equipment_id)
    return Response.success()
```

</details>

<details>
<summary><code>frontend/src/api/lab.js</code></summary>

```js
import request from "@/utils/request";

// 分页模糊查询实验室列表
export function getLabPageList(params) {
  return request({
    url: "/api/lab/list",
    method: "get",
    params,
  });
}

// 新增实验室
export function createLabApi(data) {
  return request({
    url: "/api/lab",
    method: "post",
    data,
  });
}

// 修改实验室
export function updateLabApi(labId, data) {
  return request({
    url: `/api/lab/${labId}`,
    method: "put",
    data,
  });
}

// 删除实验室
export function deleteLabApi(labId) {
  return request({
    url: `/api/lab/${labId}`,
    method: "delete",
  });
}
```

</details>

<details>
<summary><code>frontend/src/api/equipment.js</code></summary>

```js
import request from "@/utils/request";

// 分页模糊查询列表
export function getEquipmentPageList(params) {
  return request({
    url: "/api/equipment/list",
    method: "get",
    params,
  });
}

// 新增
export function createEquipmentApi(data) {
  return request({
    url: "/api/equipment",
    method: "post",
    data,
  });
}

// 修改
export function updateEquipmentApi(equipmentId, data) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: "put",
    data,
  });
}

// 删除
export function deleteEquipmentApi(equipmentId) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: "delete",
  });
}
```

</details>

<details>
<summary><code>frontend/src/views/Lab.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入账号或名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="primary" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="封面" width="100">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 50%"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="description" label="简介" width="140" />
        <el-table-column prop="location" label="位置" width="200" />
        <el-table-column label="开放时间">
          <template #default="{ row }"
            >{{ row.open_time }} - {{ row.close_time }}</template
          >
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "开启" : "关闭" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入名称" />
          </el-form-item>

          <el-form-item label="简介">
            <el-input
              type="textarea"
              v-model="form.description"
              placeholder="请输入简介"
            />
          </el-form-item>

          <el-form-item label="封面">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>
          <el-form-item label="位置">
            <el-input
              type="textarea"
              v-model="form.location"
              placeholder="请输入位置"
            />
          </el-form-item>
          <el-form-item label="容量" prop="capacity">
            <el-input
              :min="1"
              v-model="form.capacity"
              placeholder="请输入容量"
            />
          </el-form-item>
          <el-form-item label="开放时间">
            <el-time-picker
              v-model="form.open_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="开始时间"
              style="width: 140px; margin-right: 8px"
            />
            <el-time-picker
              v-model="form.close_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="结束时间"
              style="width: 140px"
            />
          </el-form-item>
          <el-form-item label="状态" prop="status" for="">
            <el-radio-group v-model="form.status">
              <el-radio :value="true">正常</el-radio>
              <el-radio :value="false">禁用</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getLabPageList,
  createLabApi,
  updateLabApi,
  deleteLabApi,
} from "@/api/lab";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { uploadFileApi } from "@/api/files";

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: "",
});

// 加载分页数据
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  name: "",
  description: "",
  img: "",
  location: "",
  capacity: 1,
  open_time: "",
  close_time: "",
  status: true,
});

const load = async () => {
  loading.value = true;
  try {
    const res = await getLabPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords,
    });
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = computed(() => ({
  name: [{ required: true, message: "请输入实验室名称", trigger: "blur" }],
  capacity: [
    { required: true, message: "请输入容量", trigger: "blur" },
    { type: "integer", min: 1, message: "容量必须为正整数", trigger: "change" },
  ],
}));

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = async () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑信息
const handleEdit = async (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    img: row.img,
    location: row.location,
    capacity: row.capacity,
    open_time: row.open_time,
    close_time: row.close_time,
    status: row.status,
  });
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, "确认删除", {
    type: "warning",
  }).then(async () => {
    const res = await deleteLabApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除成功");
      load();
    }
  });
};

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, ...labData } = form;
    const res = id
      ? await updateLabApi(id, labData)
      : await createLabApi(labData);
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

onMounted(() => {
  load();
});

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.img = res.data?.url;
    }
  } catch {}
};
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<details>
<summary><code>frontend/src/views/Equipment.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>设备管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.lab_id"
          placeholder="所属实验室"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
        >
          <el-option
            v-for="item in labOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-input
          placeholder="请输入设备名称或型号"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="success" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? "正常" : "维修" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="所属实验室" prop="lab_id">
            <el-select
              v-model="form.lab_id"
              placeholder="请选择实验室"
              style="width: 100%"
            >
              <el-option
                v-for="item in labOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="设备名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入设备名称" />
          </el-form-item>

          <el-form-item label="说明">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入说明"
            />
          </el-form-item>

          <el-form-item label="图片">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>

          <el-form-item label="型号规格">
            <el-input v-model="form.spec" placeholder="例如 RTX4090 24G" />
          </el-form-item>

          <el-form-item label="数量" prop="quantity">
            <el-input-number v-model="form.quantity" :min="1" :max="999" />
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">维修</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi,
} from "@/api/equipment";
import { getLabPageList } from "@/api/lab";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { uploadFileApi } from "@/api/files";

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});

const loading = ref(false);
const tableData = ref([]);
const labOptions = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});

// 加载分页数据
const load = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = {
  lab_id: [{ required: true, message: "请选择实验室", trigger: "change" }],
  name: [{ required: true, message: "请输入设备名称", trigger: "blur" }],
  quantity: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = async () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑信息
const handleEdit = (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status,
  });
  dialogVisible.value = true;
};

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, "确认删除", {
    type: "warning",
  }).then(async () => {
    const res = await deleteEquipmentApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除成功");
      load();
    }
  });
};

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, ...equipmentData } = form;
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData);
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.img = res.data?.url;
    }
  } catch {}
};

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });
  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};

onMounted(() => {
  loadLabs();
  load();
});
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<details>
<summary><code>frontend/src/layouts/Layout.vue</code></summary>

```vue
<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div
              style="display: flex; align-items: center; margin-right: 20px; cursor: pointer"
            >
              <img
                :src="userInfo?.avatar"
                alt=""
                style="width: 30px; border-radius: 50%"
              />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || "用户" }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu router style="height: 100%" default-active="/manager/home">
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/lab"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/equipment"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/user"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu as IconMenu,
  House,
  Setting,
  User,
} from "@element-plus/icons-vue";
import router from "@/router";
import { logout } from "@/utils/auth";
import { useUser } from "@/utils/user";
const { userInfo } = useUser();

const handleLogout = () => {
  logout();
  router.push("/login");
};

const goPerson = () => {
  router.push("/manager/profile");
};

const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/manager/profile");
  } else if (command === "password") {
    router.push("/manager/password");
  } else if (command === "logout") {
    logout();
    router.push("/login");
  }
};
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from "@/utils/auth";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: "/manager/home" },
    {
      path: "/manager",
      name: "Layout",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          name: "Home",
          component: () => import("@/views/Home.vue"),
        },
        {
          path: "lab",
          name: "Lab",
          component: () => import("@/views/Lab.vue"),
        },
        {
          path: "equipment",
          name: "Equipment",
          component: () => import("@/views/Equipment.vue"),
        },
        {
          path: "user",
          name: "User",
          component: () => import("@/views/User.vue"),
        },
        {
          path: "profile",
          name: "Profile",
          component: () => import("@/views/Profile.vue"),
        },
        {
          path: "password",
          name: "Password",
          component: () => import("@/views/Password.vue"),
        },
      ],
    },
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
    },
  ],
});

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken();
  if (to.path === "/login" || to.path === "/register") {
    return true;
  } else {
    return token ? true : "/login";
  }
});

export default router;
```

</details>

总路由与 main.py 的同阶段快照见[应用入口阶段快照](#entry-history)。

<a id="resource-evolution-snapshots"></a>

### 10.30 设备分页与 labs 表名的阶段快照（2026-10-19～20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>frontend/src/views/Equipment.vue</code>（2026-10-19）</summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>设备管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.lab_id"
          placeholder="所属实验室"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
        >
          <el-option
            v-for="item in labOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-input
          placeholder="请输入设备名称或型号"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="success" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? "正常" : "维修" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="所属实验室" prop="lab_id">
            <el-select
              v-model="form.lab_id"
              placeholder="请选择实验室"
              style="width: 100%"
            >
              <el-option
                v-for="item in labOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="设备名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入设备名称" />
          </el-form-item>

          <el-form-item label="说明">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入说明"
            />
          </el-form-item>

          <el-form-item label="图片">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>

          <el-form-item label="型号规格">
            <el-input v-model="form.spec" placeholder="例如 RTX4090 24G" />
          </el-form-item>

          <el-form-item label="数量" prop="quantity">
            <el-input-number v-model="form.quantity" :min="1" :max="999" />
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">维修</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi,
} from "@/api/equipment";
import { getLabPageList } from "@/api/lab";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { uploadFileApi } from "@/api/files";

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});

const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const labOptions = ref([]);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});

// 加载分页数据
const load = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = {
  lab_id: [{ required: true, message: "请选择实验室", trigger: "change" }],
  name: [{ required: true, message: "请输入设备名称", trigger: "blur" }],
  quantity: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑信息
const handleEdit = (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status,
  });
  dialogVisible.value = true;
};

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, "确认删除", {
    type: "warning",
  }).then(async () => {
    const res = await deleteEquipmentApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除成功");
      load();
    }
  });
};

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, ...equipmentData } = form;
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData);
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.img = res.data?.url;
    }
  } catch {}
};

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });
  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};

onMounted(() => {
  loadLabs();
  load();
});
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<details>
<summary><code>backend/app/models/lab.py</code>（2026-10-20）</summary>

```python
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Integer, String


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = {"comment": "实验室信息"}

    name: Mapped[str] = mapped_column(String(50), comment="名称")
    description: Mapped[str] = mapped_column(String(500), comment="简介", nullable=True)
    img: Mapped[str] = mapped_column(String(100), comment="封面", nullable=True)
    location: Mapped[str] = mapped_column(String(100), comment="位置", nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, comment="容量", default=0)
    open_time: Mapped[str] = mapped_column(
        String(20), comment="开放的开始时间", nullable=True
    )
    close_time: Mapped[str] = mapped_column(
        String(20), comment="开放的结束时间", nullable=True
    )
    status: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="状态: True-启用, False-禁用"
    )
```

</details>

<details>
<summary><code>backend/app/models/equipment.py</code>（2026-10-20）</summary>

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Integer, String
from app.database import Base
from app.models.lab import Lab


class Equipment(Base):
    __tablename__ = "equipments"
    __table_args__ = {"comment": "实验室设备表"}

    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id"), comment="所属实验室", nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), comment="设备名称", nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(500), comment="说明", nullable=True
    )
    img: Mapped[str | None] = mapped_column(String(200), comment="图片", nullable=True)
    spec: Mapped[str | None] = mapped_column(
        String(100), comment="型号规格", nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, comment="数量", default=1)
    status: Mapped[int] = mapped_column(default=1, comment="状态(0-维修,1-正常)")

    lab: Mapped[Lab] = relationship()
```

</details>

### 10.31 本章修补代码快照（2026-10-20）

以下为该日期保存的阶段快照，供理解修改过程；完整运行请使用同一版本的工作区文件。

<details>
<summary><code>backend/app/schemas/lab.py</code></summary>

```python
from pydantic import BaseModel, ConfigDict, Field


class LabResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int
    open_time: str | None = None
    close_time: str | None = None
    status: bool

    model_config = ConfigDict(from_attributes=True)


class LabCreateRequest(BaseModel):
    name: str
    description: str | None = None
    img: str | None = None
    location: str | None = None
    capacity: int = Field(gt=0)
    open_time: str | None = None
    close_time: str | None = None
    status: bool = True


class LabUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    img: str | None = None
    capacity: int | None = Field(default=None, gt=0)
    open_time: str | None = None
    close_time: str | None = None
    status: bool | None = None
```

</details>

<details>
<summary><code>backend/app/services/lab_service.py</code></summary>

```python
from operator import or_
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_lab_info(Lab: Lab) -> LabResponse:
    return LabResponse.model_validate(Lab)


def update_Lab_info(db: Session, Lab: Lab, data: LabUpdateRequest):
    Lab_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in Lab_dict.items():
        setattr(Lab, field, value)
    db.commit()
    db.refresh(Lab)
    return LabResponse.model_validate(Lab)


def get_lab_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    status: bool | None = None,
):
    # select * from Lab where name like '%计算机实验室%'
    query = db.query(Lab)

    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
    if status:
        query = query.filter(Lab.status == status)
    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items], total=total
    )


def get_lab(db: Session, lab_id: int):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return LabResponse.model_validate(lab)


def create_lab(db: Session, data: LabCreateRequest):
    """新增"""

    exist = db.query(Lab).filter(Lab.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室已存在")

    lab = Lab(
        **data.model_dump(exclude_none=True)
    )  # {"key1": "value1", "key2": "value2"} -> key1=value1, key2=value2
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, Lab_id: int, data: LabUpdateRequest):
    """更新"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    Lab_dict = data.model_dump(exclude_none=True)
    for field, value in Lab_dict.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, Lab_id: int):
    """删除"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    if db.query(Reservation.id).filter(Reservation.lab_id == Lab_id).first():
        raise BusinessException(
            message="该实验室存在预约记录，不能删除，可将实验室设为关闭状态", code=409
        )
    if db.query(Equipment.id).filter(Equipment.lab_id == Lab_id).first():
        raise BusinessException(
            message="该实验室下仍有设备，请先删除或转移设备", code=409
        )

    try:
        db.delete(lab)
        db.commit()
    except IntegrityError as exc:
        # 检查后仍可能新增关联记录，提交失败时回滚并返回业务提示。
        db.rollback()
        raise BusinessException(
            message="该实验室存在关联数据，无法删除", code=409
        ) from exc
```

</details>

<details>
<summary><code>backend/app/services/equipment_service.py</code></summary>

```python
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.schemas.equipment import (
    EquipmentResponse,
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def get_equipment_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    lab_id: int | None = None,
):
    """分页模糊查询列表"""

    # select * from equipment where name like '%计算机%';
    query = db.query(Equipment)
    if lab_id is not None:
        query = query.filter(Equipment.lab_id == lab_id)
    if keywords:
        query = query.filter(Equipment.name.ilike(f"%{keywords}%"))
    total = query.count()
    items = (
        query.order_by(Equipment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        data = EquipmentResponse.model_validate(item)
        data.lab_name = item.lab.name if item.lab else None
        result.append(data)
    return PageResponse(list=result, total=total)


def create_equipment(db: Session, data: EquipmentCreateRequest):
    """新增"""
    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(Equipment.lab_id == data.lab_id, Equipment.name == data.name)
        .first()
    )
    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdateRequest):
    """更新"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")

    payload = data.model_dump(exclude_none=True)
    lab_id = payload.get("lab_id", equipment.lab_id)
    name = payload.get("name", equipment.name)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(
            Equipment.lab_id == lab_id,
            Equipment.name == name,
            Equipment.id != equipment.id,
        )
        .first()
    )

    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")

    for field, value in payload.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def delete_equipment(db: Session, equipment_id: int):
    """删除"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")
    if (
        db.query(Reservation.id)
        .filter(Reservation.equipment_id == equipment_id)
        .first()
    ):
        raise BusinessException(message="该设备存在预约记录，不能删除", code=409)

    try:
        db.delete(equipment)
        db.commit()
    except IntegrityError as exc:
        # 检查后仍可能新增关联记录，提交失败时回滚并返回业务提示。
        db.rollback()
        raise BusinessException(
            message="该设备存在关联数据，无法删除", code=409
        ) from exc
```

</details>

<details>
<summary><code>frontend/src/views/Equipment.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>设备管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.lab_id"
          placeholder="所属实验室"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
        >
          <el-option
            v-for="item in labOptions"
            :key="item.id"
            :label="item.name"
            :value="item.id"
          />
        </el-select>

        <el-input
          placeholder="请输入设备名称或型号"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="success" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? "正常" : "维修" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="所属实验室" prop="lab_id">
            <el-select
              v-model="form.lab_id"
              placeholder="请选择实验室"
              style="width: 100%"
            >
              <el-option
                v-for="item in labOptions"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="设备名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入设备名称" />
          </el-form-item>

          <el-form-item label="说明">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              placeholder="请输入说明"
            />
          </el-form-item>

          <el-form-item label="图片">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>

          <el-form-item label="型号规格">
            <el-input v-model="form.spec" placeholder="例如 RTX4090 24G" />
          </el-form-item>

          <el-form-item label="数量" prop="quantity">
            <el-input-number v-model="form.quantity" :min="1" :max="999" />
          </el-form-item>

          <el-form-item label="状态">
            <el-radio-group v-model="form.status">
              <el-radio :value="1">正常</el-radio>
              <el-radio :value="0">维修</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi,
} from "@/api/equipment";
import { getLabPageList } from "@/api/lab";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { uploadFileApi } from "@/api/files";

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});

const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const labOptions = ref([]);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});

// 加载分页数据
const load = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = {
  lab_id: [{ required: true, message: "请选择实验室", trigger: "change" }],
  name: [{ required: true, message: "请输入设备名称", trigger: "blur" }],
  quantity: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    lab_id: null,
    name: "",
    description: "",
    img: "",
    spec: "",
    quantity: 1,
    status: 1,
  });
};

const handleSearch = () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑信息
const handleEdit = (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status,
  });
  dialogVisible.value = true;
};

// 删除信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除【${row.name}】？`, "确认删除", {
      type: "warning",
    });
    const res = await deleteEquipmentApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除成功");
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, ...equipmentData } = form;
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData);
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.img = res.data?.url;
    }
  } catch {}
};

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });
  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};

onMounted(() => {
  loadLabs();
  load();
});
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<details>
<summary><code>frontend/src/views/Lab.vue</code></summary>

```vue
<template>
  <div style="width: 50%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室管理</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入账号或名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
        <el-button type="primary" :icon="Plus" @click="handleCreate"
          >新增</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="封面" width="100">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <img
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 50%"
                :src="row.img"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column prop="description" label="简介" width="140" />
        <el-table-column prop="location" label="位置" width="200" />
        <el-table-column label="开放时间">
          <template #default="{ row }"
            >{{ row.open_time }} - {{ row.close_time }}</template
          >
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? "开启" : "关闭" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)"
              >编辑</el-button
            >
            <el-button type="danger" text bg @click="handleDelete(row)"
              >删除</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
      <el-dialog
        v-model="dialogVisible"
        :title="form.id ? '编辑' : '新增'"
        width="450"
      >
        <el-form
          id="user-form"
          ref="formRef"
          :rules="rules"
          :model="form"
          label-width="80px"
          style="width: 100%; padding-right: 30px; padding-top: 16px"
          v-loading="formLoading"
          @submit.prevent="handleSave"
        >
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" placeholder="请输入名称" />
          </el-form-item>

          <el-form-item label="简介">
            <el-input
              type="textarea"
              v-model="form.description"
              placeholder="请输入简介"
            />
          </el-form-item>

          <el-form-item label="封面">
            <el-upload
              class="avatar-uploader"
              :http-request="handleFileUpload"
              :show-file-list="false"
              accept="image/jpeg,image/png,image/gif,image/webp"
              :before-upload="beforeAvatarUpload"
            >
              <img v-if="form.img" :src="form.img" class="avatar" />
              <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
          </el-form-item>
          <el-form-item label="位置">
            <el-input
              type="textarea"
              v-model="form.location"
              placeholder="请输入位置"
            />
          </el-form-item>
          <el-form-item label="容量" prop="capacity">
            <el-input-number
              v-model="form.capacity"
              :min="1"
              :precision="0"
              placeholder="请输入容量"
            />
          </el-form-item>
          <el-form-item label="开放时间">
            <el-time-picker
              v-model="form.open_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="开始时间"
              style="width: 140px; margin-right: 8px"
            />
            <el-time-picker
              v-model="form.close_time"
              format="HH:mm"
              value-format="HH:mm"
              placeholder="结束时间"
              style="width: 140px"
            />
          </el-form-item>
          <el-form-item label="状态" prop="status" for="">
            <el-radio-group v-model="form.status">
              <el-radio :value="true">正常</el-radio>
              <el-radio :value="false">禁用</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button
            type="primary"
            native-type="submit"
            form="user-form"
            :loading="formLoading"
          >
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false"
            >取消</el-button
          >
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from "vue";
import {
  getLabPageList,
  createLabApi,
  updateLabApi,
  deleteLabApi,
} from "@/api/lab";
import { Search, Plus } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { uploadFileApi } from "@/api/files";

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: "",
});

// 加载分页数据
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const formLoading = ref(false);
const form = reactive({
  id: null,
  name: "",
  description: "",
  img: "",
  location: "",
  capacity: 1,
  open_time: "",
  close_time: "",
  status: true,
});

const load = async () => {
  loading.value = true;
  try {
    const res = await getLabPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords,
    });
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const rules = computed(() => ({
  name: [{ required: true, message: "请输入实验室名称", trigger: "blur" }],
  capacity: [
    { required: true, message: "请输入容量", trigger: "blur" },
    { type: "integer", min: 1, message: "容量必须为正整数", trigger: "change" },
  ],
}));

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = async () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 编辑信息
const handleEdit = async (row) => {
  resetForm();
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    img: row.img,
    location: row.location,
    capacity: row.capacity,
    open_time: row.open_time,
    close_time: row.close_time,
    status: row.status,
  });
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

// 删除信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除【${row.name}】？`, "确认删除", {
      type: "warning",
    });
    const res = await deleteLabApi(row.id);
    if (res.code === 200) {
      ElMessage.success("删除成功");
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return;
  formLoading.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const { id, ...labData } = form;
    const res = id
      ? await updateLabApi(id, labData)
      : await createLabApi(labData);
    if (res.code === 200) {
      dialogVisible.value = false;
      ElMessage.success("操作成功");
      await load();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false;
  }
};

onMounted(() => {
  load();
});

const beforeAvatarUpload = (file) => {
  const imageTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];

  if (!imageTypes.includes(file.type)) {
    ElMessage.error("只能上传图片");
    return false;
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error("上传图片大小不能超过2M");
    return false;
  }

  return true;
};

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file);
    if (res.code === 200) {
      form.img = res.data?.url;
    }
  } catch {}
};
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
```

</details>

<a id="15-lab-browse"></a>

## 11. 学生端实验室与设备浏览

阶段起点：2026-10-19。本章说明学生怎样找到实验室、查看介绍与关联设备。预约按钮的早期占位快照保留日期；当前按钮已接通公共预约弹窗，提交、查询、审核和自动过期分别在后面的预约章节说明。管理端 Equipment.vue 的后续修改已归入资源管理章。

### 11.1 先分清四个页面的职责

| 文件                                | 面向的操作           | 页面主要内容                                           |
| ----------------------------------- | -------------------- | ------------------------------------------------------ |
| frontend/src/views/Lab.vue          | 管理实验室资料       | 搜索、表格、新增和编辑弹窗、删除                       |
| frontend/src/views/Equipment.vue    | 管理设备资料         | 搜索、按实验室筛选、新增和编辑；本次模板移除了删除按钮 |
| frontend/src/views/LabList.vue      | 浏览实验室           | 封面卡片、位置、容量、时间、查看设备按钮               |
| frontend/src/views/LabEquipment.vue | 浏览某个实验室的设备 | 实验室简介、设备图片、规格、数量、状态                 |

菜单中，管理员看到管理入口，student 角色看到实验室列表入口。两个浏览页面不提供资源编辑表单。

页面不同，仍可以复用同一查询接口。例如，Lab.vue 用实验室列表接口填充表格，LabList.vue 用这个接口填充卡片。后端返回的是数据，前端决定把数据画成什么样。

注意：“菜单按角色显示”与“接口按角色授权”是两个独立机制。本次后端查询接口允许符合当前用户依赖检查的登录用户调用，并没有额外限定必须是 student。

### 11.2 学生浏览的文件地图

| 层                                  | 主要变化                                          |
| ----------------------------------- | ------------------------------------------------- |
| backend/app/services/lab_service.py | 列表新增 status 参数；新增 get_lab 按 ID 查询详情 |
| backend/app/api/lab.py              | 列表改为登录用户可查；新增 GET /{lab_id}          |
| backend/app/api/equipment.py        | 设备列表改为登录用户可查                          |
| frontend/src/api/lab.js             | 新增 getLab(lab_id) 请求函数                      |
| frontend/src/views/LabList.vue      | 新增卡片式实验室浏览页面                          |
| frontend/src/views/LabEquipment.vue | 新增实验室介绍和关联设备浏览页面                  |
| frontend/src/router/index.js        | 增加 lablist、labequipment 两个子路由             |
| frontend/src/layouts/Layout.vue     | 增加学生菜单入口，并尝试根据当前路由设置高亮      |
| frontend/src/views/Equipment.vue    | 统一 page_size 属性；移除模板中的删除按钮         |

本次对照发现，实验室与设备的 models、schemas，以及 equipment_service.py 的核心业务逻辑与第 10 节快照一致。关联查询不是重新实现了一套，而是复用了之前的 lab_id 筛选和 lab_name 组装。

第 11.23 节保存本次相关文件的完整快照；早期快照继续保留，便于观察功能怎样逐步长出来。

### 11.3 把整个流程连起来

假设数据库里有 ID 为 8 的实验室。学生打开列表，点击它的“查看设备”，整体流程如下：

```mermaid
sequenceDiagram
    participant U as 学生
    participant L as LabList.vue
    participant R as Vue Router
    participant E as LabEquipment.vue
    participant A as FastAPI
    participant D as 数据库
    U->>L: 打开实验室列表
    L->>A: GET /api/lab/list?page=1&page_size=10
    A->>D: 搜索、统计总数、取当前页
    D-->>A: 实验室记录
    A-->>L: data.list 与 data.total
    L-->>U: 显示卡片
    U->>L: 点击 ID 为 8 的实验室
    L->>R: push 路径及 query.lab_id
    R->>E: /manager/labequipment?lab_id=8
    E->>E: 读取 ID，转成数字并校验
    par 请求实验室介绍
        E->>A: GET /api/lab/8
        A->>D: 查询 ID 为 8 的实验室
        A-->>E: 实验室详情对象
    and 请求设备列表
        E->>A: GET /api/equipment/list?lab_id=8&page=1&page_size=10
        A->>D: 按 lab_id 筛选设备
        A-->>E: 设备列表与总数
    end
    E-->>U: 显示介绍和设备表格
```

两次后端请求都会经过原来的 request.js，携带当前 token。图中省略了重复的身份验证和统一响应包装，后面的章节会展开其中的差别。

你可以把这次开发理解为：先提供一个资源入口，再把用户选择的资源 ID 传到下一页，下一页根据 ID 查询所需数据。

### 11.4 为什么必须同时调整后端查询权限

上一版查询接口使用：

```python
current_user: User = Depends(get_current_admin)
```

现在实验室列表、实验室详情、设备列表都使用：

```python
current_user: User = Depends(get_current_user)
```

这里的 Depends 表示“在执行接口函数之前，先执行这个依赖所要求的检查，并把结果传进来”。

当前 get_current_user 会验证 token、查询用户是否存在、检查账号是否禁用。只有这些条件满足后，接口才继续执行。get_current_admin 又在这条链上检查数据库用户的 role 是否为 admin。

所以改动后的权限表为：

| HTTP 请求                         | 当前依赖          | 当前要求               |
| --------------------------------- | ----------------- | ---------------------- |
| GET /api/lab/list                 | get_current_user  | 有效登录且账号可用     |
| GET /api/lab/{lab_id}             | get_current_user  | 有效登录且账号可用     |
| GET /api/equipment/list           | get_current_user  | 有效登录且账号可用     |
| POST、PUT、DELETE /api/lab…       | get_current_admin | 上述条件，并且为管理员 |
| POST、PUT、DELETE /api/equipment… | get_current_admin | 上述条件，并且为管理员 |

即使函数体没有读取 current_user.name，依赖仍会执行。这个参数已经承担了进入接口前的权限检查。

如果只新增学生菜单，却保留原来的管理员查询依赖，学生会进入页面，然后查询被后端拒绝。这就是本次必须同时修改前后端的原因。

当前前端路由守卫仍主要检查本地是否有 token，没有逐个路由检查角色；隐藏菜单也不会阻止用户手动输入路径。资源新增、修改和删除的最终权限仍由后端依赖决定。

### 11.5 新增详情接口：从路径取得一个 ID

backend/app/api/lab.py 中新增：

```python
@router.get("/{lab_id}")
def get_lab_detail(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab(db, lab_id)
    return Response.success(data=res)
```

其中的地址逐层拼接：

```text
main.py 注册 API 的前缀 /api
  + 本文件 APIRouter 的前缀 /lab
  + 装饰器上的 /{lab_id}
  = /api/lab/{lab_id}
```

请求 /api/lab/8 时，8 占据 {lab_id} 的位置。lab_id: int 要求 FastAPI 将这个路径值解析成整数。请求 /api/lab/abc 时，路径能匹配，但整数校验失败，进入项目的参数异常处理流程。

业务函数新增：

```python
def get_lab(db: Session, lab_id: int):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return LabResponse.model_validate(lab)
```

逐句理解：

1. db.query(Lab) 从实验室模型发起查询。
2. filter(Lab.id == lab_id) 限定目标 ID。
3. first() 取第一条，没有时得到 None。
4. 不存在时 raise 抛出业务异常，正常的 return 不再执行。
5. 存在时把 ORM 对象转换成约定好的 LabResponse。

这个接口返回“一间实验室的对象”。列表接口返回“分页对象，其中包含多个实验室”。前端不能把它们当成相同结构使用。

另一个容易忽略的地方：当前 /list 定义在 /{lab_id} 前面。固定路径需要先匹配，避免 list 被当成动态 ID。这个顺序符合 [FastAPI 对路径匹配顺序的说明](https://fastapi.tiangolo.com/tutorial/path-params/#order-matters)。

### 11.6 新增 status 筛选：参数接通了，但 False 分支还有问题

接口新增：

```python
status: bool | None = None
```

这里有三个有意义的状态：

| 传入情况     | 进入 Python 函数后的值 | 预期用途       |
| ------------ | ---------------------- | -------------- |
| 不传 status  | None                   | 不按状态筛选   |
| status=true  | True                   | 只查启用实验室 |
| status=false | False                  | 只查停用实验室 |

URL 中的 true、false 是文本，FastAPI 根据 bool 类型声明把它们解析为布尔值。服务函数收到的已经是 True 或 False。

当前 lab_service.py 实际写法是：

```python
if status:
    query = query.filter(Lab.status == status)
```

Python 的 if 判断的是“条件真假”。True 会进入分支，False 和 None 都不会进入。因此当前实际结果是：

| status | 当前是否追加筛选条件 | 当前结果                 |
| ------ | -------------------- | ------------------------ |
| None   | 否                   | 所有状态                 |
| True   | 是                   | 启用状态                 |
| False  | 否                   | 所有状态，未实现只查停用 |

本次内存数据库检查已经复现这个行为：创建一间启用、一间停用实验室后，status=False 返回两间。

应把条件判断改成“是否提供了状态”。下面是修正片段，**尚未写入业务源码**：

```python
if status is not None:
    query = query.filter(Lab.status == status)
```

不要把 if status 理解为“只要传了参数”。布尔条件里，False 本身也是一个正常的筛选值。

还有第二层区别：LabList.vue 当前 params 没有 status: true，调用时不会主动要求只查启用实验室。所以当前学生卡片列表可能包含停用实验室；详情接口也没有按启用状态限制访问。

如果产品要求学生只能看启用实验室，需要先明确规则，再在学生查询和详情的后端逻辑落实规则，前端也可以配合传参。仅在卡片查询里增加参数，仍不能限制用户直接按 ID 请求停用实验室详情。

2026-10-24 对照工作区仍为 if status，False 筛选问题尚未修复。导入清理或文件格式变化不等于该业务条件已改变。

### 11.7 LabList.vue：从接口结果到卡片数组

页面中与列表直接有关的状态是：

```js
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});
```

ref 用来保存一个响应式值：脚本中用 .value 读写；模板中通常自动解包。reactive 包装对象后，可以直接修改 params.page 等属性。

这些名字的作用：

| 名字      | 保存什么                 | 谁使用它               |
| --------- | ------------------------ | ---------------------- |
| loading   | 是否正在查询             | v-loading 显示加载状态 |
| tableData | 当前页实验室数组         | v-for 生成卡片         |
| total     | 筛选后的记录总数         | 分页组件               |
| params    | 页码、页大小、名称关键词 | 请求参数               |

虽然变量还叫 tableData，这个页面并没有使用表格；名字不会改变数据的用途。

load 的核心是：

```js
loading.value = true;
try {
  const res = await getLabPageList(params);
  if (res.code === 200) {
    tableData.value = res.data?.list;
    total.value = res.data?.total;
  }
} finally {
  loading.value = false;
}
```

getLabPageList 把 params 交给 request 的 params 配置，形成 GET 查询字符串。await 等待请求对应的 Promise 完成。统一响应由 request.js 解包后，res 是业务对象，因此读取 res.data.list。

finally 表示无论正常完成还是抛出错误，都会做最后的清理，所以加载状态会恢复。它不负责“吃掉”错误；LabList.vue 的 load 没有 catch，网络错误对应的 Promise 仍可能向调用方拒绝。拦截器显示错误消息，也不会自动把所有拒绝变成成功。

当前 lab_id: null 对实验室列表没有筛选作用。后端列表函数没有声明 lab_id 参数。参数名称写进对象，只代表前端准备发送它，不代表后端已经实现对应功能。

名称查询时：

```js
const handleSearch = () => {
  params.page = 1;
  load();
};
```

先回第一页，是为了避免“原来在第 5 页，新关键词只有 1 页数据，结果画面为空”。回车、查询按钮和清空输入都复用这一个函数。

### 11.8 卡片怎么由一个数组生成

关键模板为：

```html
<el-row :gutter="16" v-loading="loading">
  <el-col
    v-for="item in tableData"
    :key="item.id"
    :span="6"
    style="margin-bottom: 16px"
  >
    <!-- 当前 item 对应一张实验室卡片 -->
  </el-col>
</el-row>
```

v-for 让同一段模板随数组重复。item 是这一轮取出的实验室对象；它不是保留字，可以改名，但对应表达式也要一起改。

:key="item.id" 为每张卡片提供稳定标识，帮助 Vue 在更新数组时识别同一条记录。不要把 key 当成后端权限或数据库主键约束；这里是前端渲染标识。

Element Plus 栅格按 24 份分列，span 为 6 时，一行通常放 4 张；gutter 控制列间间距。当前没有配置不同屏幕尺寸的列数，小屏布局仍要验收。参见 [Element Plus Layout](https://element-plus.org/en-US/component/layout)。

卡片中的语法也都来自已学过的 JavaScript：

```html
<div>{{ item.name }}</div>
<div>位置：{{ item.location || '-' }}</div>
<div>
  开放时间： {{ item.open_time && item.close_time ? `${item.open_time} -
  ${item.close_time}` : '-' }}
</div>
```

- {{ … }} 把表达式结果显示为文本。
- || 表示左边是假值时采用右边；位置缺失或为空字符串时显示短横线。
- && 要求开始时间和结束时间都有可用值。
- 条件 ? 结果一 : 结果二 是三元表达式。
- 反引号和 ${…} 构成模板字符串，用来拼接时间文本。

封面有值时显示 img，没有值时显示灰色占位块，使用的是 v-if / v-else。object-fit: cover 让图片填满固定区域，图片边缘可能被裁掉。

本页只是展示这些时间字符串，没有计算当前时刻能否预约，也没有验证开始时间早于结束时间。

### 11.9 点击“查看设备”后，先发生前端路由跳转

LabList.vue 中当前函数是：

```js
const handelViewEquipment = (lab) => {
  router.push({
    path: "/manager/labequipment",
    query: { lab_id: lab.id },
  });
};
```

点击卡片时，模板调用 handelViewEquipment(item)，所以函数参数 lab 就是这张卡片的数据对象。

假设 lab.id 为 8，导航得到：

```text
/manager/labequipment?lab_id=8
```

其中：

| 部分                  | 意义                     |
| --------------------- | ------------------------ |
| /manager/labequipment | 要显示哪个前端页面       |
| ?                     | 路径与查询字符串的分隔符 |
| lab_id=8              | 传给目标页面的查询条件   |

这个 router.push 负责导航；它本身不会查询实验室数据库。进入目标页面后，页面初始化代码才发起后端请求。路由对象中的 query 用法见 [Vue Router 编程式导航](https://router.vuejs.org/guide/essentials/navigation.html)。

新增路由定义在 /manager 的 children 中：

```js
{
  path: 'lablist',
  name: 'LabList',
  component: () => import('@/views/LabList.vue')
},
{
  path: 'labequipment',
  name: 'LabEquipment',
  component: () => import('@/views/LabEquipment.vue')
}
```

这段是 children 数组中的两个对象片段。子路径没有开头的 /，因此与父路径组成完整路径。component 中的箭头函数在需要该路由时加载页面模块；布局中的 router-view 显示对应子页面。

函数名中的 handel 是当前代码拼写。调用处与定义处保持一致时可以运行；以后整理时可以统一为 handle，提高可读性。

### 11.10 目标页怎样取到这个 ID：useRoute 与 useRouter

LabEquipment.vue 使用：

```js
const route = useRoute();
const router = useRouter();

const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id),
});
```

这两个工具的用途不同：

| 写法        | 取得什么       | 本页用途                 |
| ----------- | -------------- | ------------------------ |
| useRoute()  | 当前路由的信息 | 读取 query.lab_id        |
| useRouter() | 路由器实例     | 返回实验室列表、跳转页面 |

它们在组件的 setup 环境中调用；本页使用 script setup，所以顶层代码就在组件创建时的 setup 环境执行。原来通过 import router from '@/router' 取得实例也能导航，本页改用组合式 API。参见 [Vue Router 与组合式 API](https://router.vuejs.org/guide/advanced/composition-api.html)。

普通地址 ?lab_id=8 解析出的值通常是字符串 "8"。Number("8") 将它转成数字 8，便于校验和传参。

这里务必区分三个位置：

```text
浏览器页面：
/manager/labequipment?lab_id=8
    route.query.lab_id 读到 "8"

实验室详情 API：
GET /api/lab/8
    后端从路径参数得到 lab_id = 8

设备列表 API：
GET /api/equipment/list?lab_id=8&page=1&page_size=10
    后端从查询参数得到 lab_id = 8
```

同一个 ID 可以出现在不同地址的不同位置。前后端没有因为变量同名就自动相连，是代码明确完成读取、转换和再次发送。

params 是页面内自定义的查询对象，其名称也不是 Vue Router 中“动态路径参数 params”的特殊用法；本页从 route.query 取 ID，没有定义 /labequipment/:lab_id 这样的动态前端路径。

### 11.11 为什么 onMounted 先判断 ID，再发请求

当前初始化代码为：

```js
onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning("缺少有效的实验室查询条件 [lab_id]");
    return;
  }
  loadLab();
  loadEquipment();
});
```

onMounted 的回调在组件挂载后运行。外面的函数调用注册回调，Vue 在适当时机执行里面的代码。

Number.isInteger 判断是否为整数，<= 0 排除零和负数，|| 表示两种错误情况任意一种成立就拒绝。return 退出本次回调，后面的两个查询不会启动。

| 浏览器查询值           | Number 转换结果 | 当前是否查询 |
| ---------------------- | --------------- | ------------ |
| "8"                    | 8               | 是           |
| 未提供，得到 undefined | NaN             | 否           |
| 空字符串               | 0               | 否           |
| "abc"                  | NaN             | 否           |
| "0" 或 "-1"            | 0 或 -1         | 否           |
| "1.5"                  | 1.5             | 否           |

NaN 表示一次数字转换没有得到有效数字，Number.isInteger(NaN) 为 false。Number(null) 也会得到 0，本页同样会拒绝。

这是前端的格式检查，不能证明“该 ID 在数据库里存在”。正整数 99999 仍可能没有对应实验室，这部分由 get_lab 处理。

另外，这段 Number 转换不是严格限定 URL 只能包含十进制数字文本，也没有单独处理重复 query 产生的数组；如果以后需要严格的输入格式和安全整数范围，应再明确校验规则。后端类型、范围和资源检查仍然需要独立成立。

### 11.12 页面为什么发两个请求，结果各放在哪里

实验室介绍用：

```js
const lab = ref(null);

const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id);
    if (res.code === 200) {
      lab.value = res.data;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
};
```

设备列表用：

```js
const loadEquipment = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list ?? [];
      total.value = res.data?.total ?? 0;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false;
  }
};
```

一个页面需要的数据有两个用途：lab 保存一间实验室介绍，tableData 保存该实验室当前页的设备数组。loading 当前只表示设备列表查询是否进行中，不是两个请求合在一起的总加载状态。

初始化中的 loadLab()、loadEquipment() 没有互相 await。第一个函数遇到 await 暂停后，第二个请求也可以启动，返回顺序不固定。

因此当前存在这些正常可解释的现象：

- 实验室介绍先出现，设备表格还在加载。
- 设备表格先出现，实验室介绍稍后才出现。
- 详情请求失败，设备请求仍独立进行。
- ID 格式正确但数据库中不存在时，详情提示“实验室不存在”，设备筛选通常得到空列表。

如果需求要求“确认实验室存在且可访问后才查询设备”，就需要改成先 await 详情并明确检查结果成功；当前还没有这种编排。

本页的 catch 没写错误参数，表示不需要直接读取错误对象。拦截器处理网络错误或非成功业务码提示，本页避免重复提示。

但“业务失败”与“Promise 拒绝”仍要区分：当前 request.js 对 HTTP 200 且 data.code 非 200 的响应会显示提示；除 code 为 401 的分支外，它仍返回业务对象。所以某些业务错误不会进入这里的 catch，而是由 if (res.code === 200) 阻止赋值。不要误记为“所有非 200 业务码都会进入 catch”。

### 11.13 实验室介绍和图片预览怎样显示

页面标题：

```html
<span>{{ lab?.name || '实验室' }}设备列表</span>
```

刚进入页面时 lab 为 null，lab?.name 使用可选链访问：lab 缺失时得到 undefined，不继续读取 name，随后 || 采用“实验室”。数据回来后 lab.value 被赋值，Vue 更新标题。

介绍区域的 v-if="lab" 则表示：有实验室对象后，才创建这一块内容。它没有检查实验室的启用状态，只检查对象是否存在。

设备图片使用了 Element Plus 的 el-image：

```html
<el-image
  v-if="row.img"
  :src="row.img"
  :preview-src-list="[row.img]"
  :preview-teleported="true"
/>
```

这里 row 来自表格列的作用域插槽：

```html
<template #default="{ row }">
  <!-- 根据当前这一行的 row 自定义单元格 -->
</template>
```

#default 是默认插槽名，{ row } 是从组件传入的插槽数据中取出 row。每一行数据都可以据此画出自己的图片或按钮。

src 是缩略图地址；preview-src-list 要求一个数组，所以这里用 [row.img] 把单个地址包起来。preview-teleported 为 true 时，预览层挂载到 body，有助于避免部分父容器样式对预览层的影响。属性含义见 [Element Plus Image](https://element-plus.org/en-US/component/image)。

这次增加的是图片展示和预览。图片地址仍来自之前的文件上传及资源资料保存流程，没有新增一套上传接口。能否显示还取决于文件是否存在、地址是否正确、静态文件代理是否正常。

### 11.14 设备状态标签与按钮禁用有细微差别

状态标签使用：

```html
<el-tag :type="row.status === 1 ? 'success' : 'danger'">
  {{ row.status === 1 ? '正常' : '维修' }}
</el-tag>
```

=== 是严格相等，数字 1 才会按这里的规则显示为正常。当前 EquipmentResponse 把 status 定义为 int，模型注释约定 0 为维修、1 为正常。

按钮使用的是：

```html
<el-button :disabled="!row.status" @click="hanldeReserveEquipment(row)">
  预约
</el-button>
```

! 表示取反。数字 0 是假值，!0 为 true，所以按钮禁用；数字 1 是真值，!1 为 false，所以按钮可点击。

在“status 只可能是 0 或 1”的前提下，两处逻辑一致。但当前后端只是 int 类型，没有把允许值限定为 0、1。若出现数字 2，标签会显示“维修”，按钮却不会禁用。

若希望只允许状态 1 操作，前端可参考 :disabled="row.status !== 1"，后端同时明确状态允许值及业务规则。这是整理建议，当前源码仍使用 !row.status。

还有两个层次要分清：

- 当前设备列表会显示维修设备，没有通过查询条件把它们隐藏。
- 禁用按钮只是界面行为；将来真正预约时，还需要后端重新查询状态，并判断实验室、时间和可用数量等实际业务条件。

不要把“按钮可以点”理解成“预约已经成功”。

### 11.15 分页、返回结构与 ?? 的用途

设备页使用：

```html
<el-pagination
  v-model:current-page="params.page"
  v-model:page-size="params.page_size"
  :total="total"
  background
  layout="total, prev, pager, next"
  @current-change="loadEquipment"
/>
```

点击下一页后，当前页更新到 params.page，事件调用 loadEquipment；请求仍携带原来的 lab_id，所以查询范围还是同一个实验室。

equipment_service.py 的筛选先于 count、offset 和 limit：

```python
query = db.query(Equipment)
if lab_id is not None:
    query = query.filter(Equipment.lab_id == lab_id)
if keywords:
    query = query.filter(Equipment.name.ilike(f"%{keywords}%"))
total = query.count()
```

因此 total 是当前筛选条件下的设备记录总数。它不是所有实验室的总数，也不是把每条记录的 quantity 加在一起。quantity 为 10 的一条记录，仍只计为一条列表记录。

后续 offset((page - 1) \* page_size) 跳过前面页的数据，limit(page_size) 限制当前页条数。返回前再为每条设备补充 lab_name，这部分沿用第 10 节逻辑。

两个请求的结构可以用下面的示意 JSON 对照；内容是假设的数据：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": 8,
    "name": "计算机实验室",
    "capacity": 20,
    "status": true
  }
}
```

上面是详情结构的简化示意，省略了部分字段。分页则是：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "list": [
      {
        "id": 21,
        "lab_id": 8,
        "lab_name": "计算机实验室",
        "name": "工作站",
        "quantity": 10,
        "status": 1
      }
    ],
    "total": 1
  }
}
```

所以详情写 lab.value = res.data，列表写 tableData.value = res.data.list。

当前设备页进一步使用：

```js
tableData.value = res.data?.list ?? [];
total.value = res.data?.total ?? 0;
```

?. 处理 data 缺失时的属性访问；?? 是空值合并运算符，只在左边为 null 或 undefined 时采用右边。

例如，合法总数 0 会保持为 0；缺失列表变为 []，缺失总数变为 0。?? 不会把任意错误类型都转换正确；如果后端错误地返回字符串作为 list，仍需要修正接口或增加类型校验。

LabList.vue 当前没有这层 ?? 默认值，两页写法还不完全一致。

### 11.16 当前路由 ID 只在创建页面时读取一次

虽然 useRoute 取得的是响应式路由对象，但这一句：

```js
lab_id: Number(route.query.lab_id);
```

执行的是“此刻读取、转换，然后把结果放入 params”。它没有自动创建 params.lab_id 与 route.query.lab_id 的持续绑定。

这会带来一个边界：同一组件被复用，只把地址从 lab_id=8 改成 lab_id=9 时，setup 和 onMounted 不一定重新执行，params 仍可能保留旧 ID。

当前从 LabList.vue 进入设备页，会创建目标页并按 ID 加载，符合这条正常使用路径。若以后增加“在设备页直接切换实验室”的操作，或者要求浏览器前进后退到不同 query 时同步刷新，就需要补充路由变化处理。

参考改造步骤如下，尚未写入源码：

1. 监听 route.query.lab_id 这一项，或使用路由更新守卫。
2. 每次变化都重新转换并校验 ID。
3. 更新 params.lab_id，把 params.page 重置为 1。
4. 清理旧实验室和设备显示，再加载新数据。
5. 避免旧请求晚返回后覆盖新实验室的数据。

如果采用 immediate 的 watch 负责首次加载，应合并原来的 onMounted 查询，避免进入页面就请求两遍。路由对象的响应式属性监听方式可查 [Vue Router 组合式 API 文档](https://router.vuejs.org/guide/advanced/composition-api.html)。

### 11.17 预约按钮：从占位到公共弹窗

当前代码中有三处预约入口：

| 位置                    | 调用函数                    | 实际行为                                  |
| ----------------------- | --------------------------- | ----------------------------------------- |
| LabList.vue 卡片        | handelViewReserve(lab)      | ElMessage.info 显示“稍后开发”加实验室名称 |
| LabEquipment.vue 顶部   | hanldeReserveLab()          | 空函数                                    |
| LabEquipment.vue 设备行 | hanldeReserveEquipment(row) | 空函数                                    |

两段函数现在是：

```js
const hanldeReserveLab = () => {};
const hanldeReserveEquipment = () => {};
```

=> {} 定义一个函数，空的大括号表示函数体没有语句。点击按钮会调用它，但不会请求后端或保存数据。

设备行虽然传了 row，当前函数没有声明接收参数，也没有使用这条数据。JavaScript 允许调用时传入多于形参的实参，因此不会仅因这一点报错。

目前应把功能进度记录为“资源浏览和预约入口已写出，预约业务待开发”。真正预约至少还要定义预约数据、提交内容、登录用户归属、时段、数量和冲突处理等需求；本节不把这些按钮算作预约功能完成。

当前提交入口已接入 ReserveDialog 和 POST /api/reservation；上面的占位行为仅描述 2026-10-19 阶段，完整提交过程见第 12 节。

### 11.18 Layout.vue：角色菜单与当前路径高亮

本节保留当时的实现和建议；后续已实际调整 Layout.vue，最新的 useRouter、useRoute 和菜单配置见[第 7.12 节](#17-login-navigation)。

新增菜单项：

```html
<el-menu-item index="/manager/lablist" v-if="userInfo?.role === 'student'">
  <el-icon><House /></el-icon>
  <span>实验室列表</span>
</el-menu-item>
```

userInfo 来自之前的 useUser 共享响应式状态。模板中自动解包 ref，?. 避免用户信息暂缺时读取 role 报错。

v-if 条件为真才创建学生入口；管理员仍有实验室管理、设备管理和用户管理入口。index 配合 el-menu 的 router 模式用于导航，default-active 指定激活项。参见 [Element Plus Menu](https://element-plus.org/en-US/component/menu)。

当前 el-menu 同时写了：

```html
:default-active="router.currentRoute.value.path" default-active="/manager/home"
```

前者动态读取当前路径，后者是固定文本，二者指向同一个组件属性。本次用项目安装的 Vue 编译器检查，生成的实际属性保留了前面的动态表达式，未报模板编译错误。

仍建议只保留一处明确配置，避免阅读歧义；不要依赖重复属性来表达默认值。建议片段如下，未修改源码：

```html
<el-menu
  router
  :default-active="router.currentRoute.value.path"
  style="height: 100%"
>
  <!-- 原有菜单项 -->
</el-menu>
```

另一个独立问题是：设备浏览页路径为 /manager/labequipment，但菜单项 index 是 /manager/lablist。当前动态表达式不会自动把两者看作同一个栏目，进入设备页时缺少与该路径对应的菜单项。

如果希望设备页也保持“实验室列表”栏目高亮，可以把设备页路径映射为 /manager/lablist，再把映射结果交给 default-active。高亮只是界面状态，不决定哪个接口能访问。

### 11.19 LabList.vue 中需要整理的复制遗留

当前浏览流程之外，LabList.vue 还保留了一些管理页代码。初学时要学会判断“定义了”与“真正被调用了”的区别。

| 当前内容                                              | 是否用于本页正常浏览             | 影响或整理方向                              |
| ----------------------------------------------------- | -------------------------------- | ------------------------------------------- |
| form、formRef、dialogVisible、resetForm、handleCreate | 模板没有相应编辑弹窗或创建入口   | 可以按浏览页职责清理                        |
| handleCreate 中的 nextTick()                          | 当前模板未调用该函数             | 未导入 nextTick；以后调用这个闲置路径会报错 |
| labOptions 与 loadLabs                                | 结果未用于当前模板               | onMounted 多发一次列表请求                  |
| params.lab_id                                         | 实验室列表接口未声明这个筛选参数 | 不能据此筛选实验室列表                      |
| 卡片 header 的裸 template                             | 没有指定命名插槽                 | 不会成为 el-card 的标题插槽                 |

其中额外请求很具体：onMounted 同时执行 loadLabs() 和 load()。前者查 page_size=100 只是填充未使用的 labOptions，后者才填充真正显示的卡片。当前页面因此会发出两次实验室列表请求。

标题处现在是：

```html
<el-card>
  <template>
    <div>实验室列表</div>
  </template>
  <!-- 其他内容 -->
</el-card>
```

本次模板编译确认它生成普通 template 元素，没有生成 header 插槽，标题内容不能按预期进入卡片标题区域。若想显示 el-card 的标题，应改为下面的命名插槽；这是建议，尚未写入源码：

```html
<el-card>
  <template #header>
    <div>实验室列表</div>
  </template>
  <!-- 其他内容 -->
</el-card>
```

#header 是 v-slot:header 的简写，表示把内容传给组件名为 header 的插槽。这个名字由 el-card 组件约定，不能随意写成别的名字。参见 [Element Plus Card](https://element-plus.org/en-US/component/card)。

这些问题中，有的会影响画面，有的只是冗余，有的要等特定函数执行才出错。不要看到“未导入 nextTick”就误判整张页面一定无法打开。

### 11.20 如果从零写这一版，按什么顺序实现

这次没有改变资源表结构，前提是第 10 节的实验室与设备模型、关联和管理端已完成。建议按下面顺序复现这一增量：

1. 在实验室服务中写 get_lab，先明确“找到”和“找不到”分别返回或抛出什么。
2. 注册 GET /api/lab/{lab_id}，放在 /list 后面；查询接入 get_current_user，写入继续接入管理员依赖。
3. 调整设备列表的查询依赖，复用现有 lab_id 筛选，不重新复制设备查询。
4. 在前端 api/lab.js 写 getLab(lab_id)，确认返回的是 Promise，await 后得到业务响应对象。
5. 写最小 LabList.vue：params、load、onMounted、v-for 卡片和分页。先显示名称，再补图片及其他字段。
6. 注册两个页面子路由，在学生菜单中提供实验室列表入口。
7. 给卡片按钮添加 router.push，通过 query 带上实验室 ID。
8. 写 LabEquipment.vue：读取和校验 ID，分别加载详情与设备，并显示加载状态、空列表和图片。
9. 对照本章检查状态筛选、无效 ID、权限、空数据及路由复用边界。
10. 按下一节在真实浏览器验收，最后再设计预约业务。

为了学习，建议每完成一步就确认输入和输出。例如先在浏览器网络面板看见 /api/lab/8 返回正确对象，再检查标题是否更新；不要一次写完四个页面后才排查哪一层出了问题。

本节快照忠实保存当前实现，包括上面已经指出的边界。复现时先理解原代码，再决定是否应用明确标注的整理建议；两者的预期结果需要分别记录。

### 11.21 真实浏览器验收清单

下面尚未在本次任务中实际操作完成。请使用学习数据库准备两间实验室和多条设备：一间启用、一间停用；设备分属不同实验室，并包含状态为 0 和 1 的记录。为验证分页，需要让某个查询结果超过一页。

| 操作                                       | 当前应观察到什么                                            |
| ------------------------------------------ | ----------------------------------------------------------- |
| 学生登录并查看侧栏                         | 有“实验室列表”；无管理员管理菜单入口                        |
| 打开实验室列表，观察 Network               | 卡片正常加载；当前还会出现一次未使用的 page_size=100 查询   |
| 按名称查询、清空、回车                     | 页码回到 1，卡片和总数按新条件更新                          |
| 翻页                                       | page 改变，展示对应页；名称筛选仍随请求发送                 |
| 查看 ID 为 8 的实验室设备                  | 页面地址带 lab_id=8，同时出现详情和设备列表请求             |
| 对比设备所属实验室                         | 请求含 lab_id=8，结果应只属于该实验室                       |
| 打开不存在但为正整数的 ID                  | 详情提示不存在；设备列表请求独立执行，通常为空              |
| 去掉 lab_id 或改为 abc、0、负数、小数      | 提示查询条件无效，不发起两项初始化查询                      |
| 查看设备图片                               | 有图时显示缩略图，可打开预览；无图时不显示图片组件          |
| 查看维修设备                               | 标签显示维修；状态为数字 0 时预约按钮禁用                   |
| 点击各预约入口                             | 卡片只显示稍后开发；详情页两个入口没有预约请求              |
| 请求 status=true 与 status=false           | True 能筛选；当前 False 仍返回所有状态，修正后再验          |
| 查看停用实验室                             | 当前学生页未传 status，详情也未限制启用状态；与需求对照确认 |
| 保持同一个设备页，只改变 query 的实验室 ID | 检查是否仍显示旧数据，决定是否补路由监听                    |
| 进入设备页观察侧栏高亮                     | 当前路径没有对应菜单项，按栏目规则决定是否映射              |
| 学生尝试资源写入接口                       | 后端拒绝；不能因为隐藏了按钮就省略此项检查                  |
| 退出登录或让 token 失效后再查询            | 前端守卫及后端身份验证按各自机制处理                        |
| 管理员进入设备管理                         | 页大小绑定使用 page_size；行操作当前只有编辑                |

查看接口时，要同时看 HTTP 状态和 JSON 中的 code。当前 BusinessException 处理器使用 HTTP 200 承载业务错误码；例如“实验室不存在”的默认业务 code 为 500，不会因为文字含“找不到”就自动变成 HTTP 404。

浏览器 Network 中观察完整响应，再与 request.js 返回给页面的对象对比，可以巩固“HTTP 响应外壳”和“业务数据”的区别。

### 11.22 本次完成的隔离检查与验证范围

已经执行：

- 用 SQLite 内存数据库加载实际模型和实际服务函数，检查实验室分页、名称筛选、启用筛选、详情存在与不存在、设备按 lab_id 隔离和关联名称返回。
- 复现 status=False 未生效；确认停用实验室仍可通过当前详情服务查询，维修设备仍包含在设备列表中。
- 静态检查接口依赖：三个 GET 查询使用 get_current_user，资源写入使用 get_current_admin；/list 位于动态详情路径之前。
- 编译 LabList.vue、LabEquipment.vue、Equipment.vue、Layout.vue 的脚本和模板；检查两个前端 API 文件及路由文件的 JavaScript 语法。
- 提取当前页面中的实际函数并使用模拟请求检查：路由带上 lab_id、1 个有效与 7 个无效 ID、空列表默认值、请求失败后恢复 loading、详情结果写入 lab。
- 检查编译产物中的动态菜单属性、LabList.vue 缺少 header 插槽，以及闲置创建函数未导入 nextTick；确认设备分页绑定已修正。

这些检查使用内存数据和模拟依赖，没有导入项目真实数据库配置，没有连接或修改真实数据库，也没有把点击按钮的浏览器流程当作已经完成。

隔离检查可以证明这段代码在相应输入下怎样运行；它不能替代真实 MySQL、Vite 代理、图片地址、登录状态和页面交互共同参与的验收。第 11.21 节及全项目从零搭建检查继续保留。

本章外部资料仅用于核对框架行为，项目具体实现以本地代码和下方快照为依据。引用均链接到对应官方页面；查阅时需结合项目安装版本。

### 11.23 本章阶段代码快照（2026-10-19）

以下快照记录 2026-10-19 读取到的实现，便于按本章复习和复现。没有把本章建议自动合并进业务代码。

equipment_service.py 和前端 api/equipment.js 本次对照没有变化，但它们承担设备筛选与请求封装，所以一并保留。models、schemas 等未变化文件可接着参考第 10 节，避免把历史章节与最新章节混成同一天的版本。

<details>
<summary><code>backend/app/services/lab_service.py</code></summary>

```python
from operator import or_
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.lab import Lab
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from sqlalchemy.orm import Session

from app.utils.password import hash_password, verify_password


def get_lab_info(Lab: Lab) -> LabResponse:
    return LabResponse.model_validate(Lab)


def update_Lab_info(db: Session, Lab: Lab, data: LabUpdateRequest):
    Lab_dict = data.model_dump(
        exclude_none=True, exclude={"role", "status"}
    )  # pydantic对象转换成字典
    for field, value in Lab_dict.items():
        setattr(Lab, field, value)
    db.commit()
    db.refresh(Lab)
    return LabResponse.model_validate(Lab)


def get_lab_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    status: bool | None = None,
):
    # select * from Lab where name like '%计算机实验室%'
    query = db.query(Lab)

    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
    if status:
        query = query.filter(Lab.status == status)
    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items], total=total
    )


def get_lab(db: Session, lab_id: int):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return LabResponse.model_validate(lab)


def create_lab(db: Session, data: LabCreateRequest):
    """新增"""

    exist = db.query(Lab).filter(Lab.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室已存在")

    lab = Lab(
        **data.model_dump(exclude_none=True)
    )  # {"key1": "value1", "key2": "value2"} -> key1=value1, key2=value2
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, Lab_id: int, data: LabUpdateRequest):
    """更新"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    Lab_dict = data.model_dump(exclude_none=True)
    for field, value in Lab_dict.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, Lab_id: int):
    """删除"""

    lab = db.query(Lab).filter(Lab.id == Lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    db.delete(lab)
    db.commit()
```

</details>

<details>
<summary><code>backend/app/api/lab.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.lab import Lab
from app.models.user import User
from app.schemas.lab import (
    LabCreateRequest,
    LabResponse,
    LabUpdateRequest,
)
from app.services import lab_service

router = APIRouter(prefix="/lab", tags=["实验室信息"])


@router.get("/list")
def get_lab_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    status: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab_page_list(db, page, page_size, keywords, status)
    return Response.success(data=res)


@router.get("/{lab_id}")
def get_lab_detail(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab(db, lab_id)
    return Response.success(data=res)


@router.post("")
def create_lab(
    data: LabCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.create_lab(db, data)
    return Response.success(data=res)


@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.update_lab(db, lab_id, data)
    return Response.success(data=res)


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab_service.delete_lab(db, lab_id)
    return Response.success()
```

</details>

<details>
<summary><code>backend/app/api/equipment.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.models.user import User
from app.dependencies.auth import get_current_admin, get_current_user
from app.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
)
from app.services import equipment_service
from app.database import get_db

router = APIRouter(prefix="/equipment", tags=["实验室设备接口"])


@router.get("/list")
def get_equipment_list(
    page: int = 1,
    page_size: int = 10,
    keywords: str | None = None,
    lab_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = equipment_service.get_equipment_page_list(
        db, page, page_size, keywords, lab_id
    )
    return Response.success(data=res)


@router.post("")
def create_equipment(
    data: EquipmentCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = equipment_service.create_equipment(db, data)
    return Response.success(data=res)


@router.put("/{equipment_id}")
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = equipment_service.update_equipment(db, equipment_id, data)
    return Response.success(data=res)


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    equipment_service.delete_equipment(db, equipment_id)
    return Response.success()
```

</details>

<details>
<summary><code>backend/app/services/equipment_service.py</code></summary>

```python
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.schemas.equipment import (
    EquipmentResponse,
    EquipmentCreateRequest,
    EquipmentUpdateRequest,
)
from sqlalchemy.orm import Session


def get_equipment_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    lab_id: int | None = None,
):
    """分页模糊查询列表"""

    # select * from equipment where name like '%计算机%';
    query = db.query(Equipment)
    if lab_id is not None:
        query = query.filter(Equipment.lab_id == lab_id)
    if keywords:
        query = query.filter(Equipment.name.ilike(f"%{keywords}%"))
    total = query.count()
    items = (
        query.order_by(Equipment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        data = EquipmentResponse.model_validate(item)
        data.lab_name = item.lab.name if item.lab else None
        result.append(data)
    return PageResponse(list=result, total=total)


def create_equipment(db: Session, data: EquipmentCreateRequest):
    """新增"""
    lab = db.query(Lab).filter(Lab.id == data.lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(Equipment.lab_id == data.lab_id, Equipment.name == data.name)
        .first()
    )
    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")
    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdateRequest):
    """更新"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")

    payload = data.model_dump(exclude_none=True)
    lab_id = payload.get("lab_id", equipment.lab_id)
    name = payload.get("name", equipment.name)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(
            Equipment.lab_id == lab_id,
            Equipment.name == name,
            Equipment.id != equipment.id,
        )
        .first()
    )

    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")

    for field, value in payload.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    res = EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res


def delete_equipment(db: Session, equipment_id: int):
    """删除"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")
    db.delete(equipment)
    db.commit()
```

</details>

<details>
<summary><code>frontend/src/api/lab.js</code></summary>

```js
import request from "@/utils/request";

// 分页模糊查询实验室列表
export function getLabPageList(params) {
  return request({
    url: "/api/lab/list",
    method: "get",
    params,
  });
}

// 分页模糊查询实验室列表
export function getLab(lab_id) {
  return request({
    url: `/api/lab/${lab_id}`,
    method: "get",
  });
}

// 新增实验室
export function createLabApi(data) {
  return request({
    url: "/api/lab",
    method: "post",
    data,
  });
}

// 修改实验室
export function updateLabApi(labId, data) {
  return request({
    url: `/api/lab/${labId}`,
    method: "put",
    data,
  });
}

// 删除实验室
export function deleteLabApi(labId) {
  return request({
    url: `/api/lab/${labId}`,
    method: "delete",
  });
}
```

</details>

<details>
<summary><code>frontend/src/api/equipment.js</code></summary>

```js
import request from "@/utils/request";

// 分页模糊查询列表
export function getEquipmentPageList(params) {
  return request({
    url: "/api/equipment/list",
    method: "get",
    params,
  });
}

// 新增
export function createEquipmentApi(data) {
  return request({
    url: "/api/equipment",
    method: "post",
    data,
  });
}

// 修改
export function updateEquipmentApi(equipmentId, data) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: "put",
    data,
  });
}

// 删除
export function deleteEquipmentApi(equipmentId) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: "delete",
  });
}
```

</details>

<details>
<summary><code>frontend/src/views/LabList.vue</code></summary>

```vue
<template>
  <div>
    <el-card>
      <template>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室列表</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
      </div>
      <div>
        <el-row :gutter="16" v-loading="loading">
          <el-col
            v-for="item in tableData"
            :key="item.id"
            :span="6"
            style="margin-bottom: 16px"
          >
            <el-card shadow="hover">
              <img
                v-if="item.img"
                :src="item.img"
                alt=""
                style="
                  display: block;
                  width: 100%;
                  height: 150px;
                  object-fit: cover;
                  border-radius: 6px;
                "
              />
              <div
                v-else
                style="width: 100%; height: 150px; background-color: #f5f7fa; border-radius: 6px"
              ></div>
              <div style="font-size: 16px; font-weight: bold; margin-top: 10px">
                {{ item.name }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                位置: {{ item.location || "-" }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                容量: {{ item.capacity }} 人
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                开放时间:
                {{
                  item.open_time && item.close_time
                    ? `${item.open_time} - ${item.close_time}`
                    : "-"
                }}
              </div>
              <div style="margin-top: 12px; display: flex; gap: 8px">
                <el-button style="flex: 1" @click="handelViewEquipment(item)"
                  >查看设备</el-button
                >
                <el-button
                  style="flex: 1"
                  type="primary"
                  @click="handelViewReserve(item)"
                  >预约</el-button
                >
              </div>
            </el-card>
          </el-col>
        </el-row>
        <div style="margin-top: 10px; display: flex; justify-content: flex-end">
          <el-pagination
            v-model:current-page="params.page"
            v-model:page-size="params.page_size"
            :total="total"
            background
            layout="total, prev, pager, next"
            @current-change="load"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { getLabPageList } from "@/api/lab";
import { Search } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import router from "@/router";

const loading = ref(false);
const tableData = ref([]);
const labOptions = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const form = reactive({
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});

// 加载分页数据
const load = async () => {
  loading.value = true;
  try {
    const res = await getLabPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });
  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};

const handelViewEquipment = (lab) => {
  router.push({ path: "/manager/labequipment", query: { lab_id: lab.id } });
};

const handelViewReserve = (lab) => {
  ElMessage.info(`稍后开发${lab.name}`);
};

onMounted(() => {
  loadLabs();
  load();
});
</script>
```

</details>

<details>
<summary><code>frontend/src/views/LabEquipment.vue</code></summary>

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div
          style="display: flex; justify-content: space-between; align-items: center"
        >
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || "实验室" }}设备列表</span>
          </div>
          <div>
            <el-button type="primary" @click="hanldeReserveLab"
              >预约实验室</el-button
            >
            <el-button @click="router.push('/manager/lablist')"
              >返回实验室列表</el-button
            >
          </div>
        </div>
      </template>
      <div
        v-if="lab"
        style="color: #666; margin-bottom: 16px; background-color: antiquewhite; padding: 10px"
      >
        <div style="margin-bottom: 10px">简介：{{ lab.description }}</div>
        <div>
          位置：{{ lab.location }}
          <span style="margin: 0 10px">|</span>
          容纳 {{ lab.capacity }} 人
          <span style="margin: 0 10px">|</span>
          开放：{{
            lab.open_time && lab.close_time
              ? `${lab.open_time} - ${lab.close_time}`
              : "-"
          }}
        </div>
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <el-image
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                :preview-src-list="[row.img]"
                :preview-teleported="true"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? "正常" : "维修" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              :disabled="!row.status"
              type="primary"
              text
              bg
              @click="hanldeReserveEquipment(row)"
              >预约</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="loadEquipment"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { getLab } from "@/api/lab";
import { ElMessage } from "element-plus";
import { ref, reactive, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getEquipmentPageList } from "@/api/equipment";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const lab = ref(null);
const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id), // "8" -> 8
});

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list ?? [];
      total.value = res.data?.total ?? 0;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false;
  }
};

const hanldeReserveLab = () => {};
const hanldeReserveEquipment = () => {};
const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id);
    if (res.code === 200) {
      lab.value = res.data;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
};

onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning("缺少有效的实验室查询条件 [lab_id]");
    return;
  }
  loadLab();
  loadEquipment();
});
</script>
```

</details>

<details>
<summary><code>frontend/src/layouts/Layout.vue</code></summary>

```vue
<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div
              style="display: flex; align-items: center; margin-right: 20px; cursor: pointer"
            >
              <img
                :src="userInfo?.avatar"
                alt=""
                style="width: 30px; border-radius: 50%"
              />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || "用户" }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu
            router
            :default-active="router.currentRoute.value.path"
            style="height: 100%"
            default-active="/manager/home"
          >
            <el-menu-item index="/manager/home">
              <el-icon><icon-menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/lablist"
              v-if="userInfo?.role === 'student'"
            >
              <el-icon><House /></el-icon>
              <span>实验室列表</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/lab"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/equipment"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item
              index="/manager/user"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu as IconMenu,
  House,
  Setting,
  User,
} from "@element-plus/icons-vue";
import router from "@/router";
import { logout } from "@/utils/auth";
import { useUser } from "@/utils/user";
const { userInfo } = useUser();

const handleLogout = () => {
  logout();
  router.push("/login");
};

const goPerson = () => {
  router.push("/manager/profile");
};

const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/manager/profile");
  } else if (command === "password") {
    router.push("/manager/password");
  } else if (command === "logout") {
    logout();
    router.push("/login");
  }
};
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from "@/utils/auth";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: "/manager/home" },
    {
      path: "/manager",
      name: "Layout",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          name: "Home",
          component: () => import("@/views/Home.vue"),
        },
        {
          path: "lab",
          name: "Lab",
          component: () => import("@/views/Lab.vue"),
        },
        {
          path: "equipment",
          name: "Equipment",
          component: () => import("@/views/Equipment.vue"),
        },
        {
          path: "user",
          name: "User",
          component: () => import("@/views/User.vue"),
        },
        {
          path: "profile",
          name: "Profile",
          component: () => import("@/views/Profile.vue"),
        },
        {
          path: "password",
          name: "Password",
          component: () => import("@/views/Password.vue"),
        },
        {
          path: "lablist",
          name: "LabList",
          component: () => import("@/views/LabList.vue"),
        },
        {
          path: "labequipment",
          name: "LabEquipment",
          component: () => import("@/views/LabEquipment.vue"),
        },
      ],
    },
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
    },
  ],
});

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken();
  if (to.path === "/login" || to.path === "/register") {
    return true;
  } else {
    return token ? true : "/login";
  }
});

export default router;
```

</details>

Equipment.vue 的管理页面快照见[资源模型与页面阶段快照](#resource-evolution-snapshots)。

<a id="16-reservation"></a>

## 12. 预约提交、资源校验与事务并发

阶段起点：2026-10-20。本章把预约模型、时间规则、资源归属、并发事务、提交弹窗和验收连成一条流程。查询、取消、审核及自动过期在下一章继续。历史审查来源见[检查记录](#historical-regression)，未解决项见[遗留问题总表](#issue-status)。

### 12.1 先确定预约要保存什么

之前的实验室和设备是“资源资料”，例如名称、位置、数量。预约新增的是“谁希望在什么时间使用哪个资源”。

一次预约需要回答：

| 问题                      | 当前字段                    |
| ------------------------- | --------------------------- |
| 谁提交                    | user_id，由当前登录用户确定 |
| 哪个实验室                | lab_id                      |
| 整间实验室还是某台/组设备 | equipment_id 是否为空       |
| 哪一天                    | date                        |
| 哪个时间段                | start_time、end_time        |
| 有什么说明                | remark                      |
| 目前处理到哪一步          | status                      |

当前用一张 reservation 表保存两种预约。equipment_id 为 NULL，表示预约实验室；不为空，表示预约这个设备记录。

设备的 quantity 只是资源资料中的数量。预约请求没有预约数量字段，当前按一条设备记录整体判断是否冲突，不能把它解释为已经支持“10 台设备中的 2 台”。

### 12.2 文件地图与阅读顺序

| 层           | 文件                                        | 负责什么                                |
| ------------ | ------------------------------------------- | --------------------------------------- |
| 数据库       | backend/app/models/reservation.py           | 表、外键、状态和 ORM 关系               |
| 输入模型     | backend/app/schemas/reservation.py          | 接收预约字段、规范时间字符串            |
| 业务         | backend/app/services/reservation_service.py | 时间、资源、归属、冲突、事务及写入      |
| HTTP 接口    | backend/app/api/reservation.py              | 接收请求、取得当前用户和数据库会话      |
| API 注册     | backend/app/api/**init**.py                 | 把预约路由加入 /api                     |
| 应用入口     | backend/app/main.py                         | 导入模型、建表、注册统一 API 和异常处理 |
| 前端请求     | frontend/src/api/reservation.js             | 封装 POST 请求                          |
| 公共弹窗     | frontend/src/components/ReserveDialog.vue   | 输入日期时段、校验并提交                |
| 实验室卡片   | frontend/src/views/LabList.vue              | 选择实验室并打开弹窗                    |
| 实验室设备页 | frontend/src/views/LabEquipment.vue         | 选择整间实验室或设备并打开弹窗          |

建议先读模型和请求结构，再读正常流程，然后读[本章的并发处理](#reservation-concurrency)。这样看到锁、重试和异常时，能够知道它们在保护哪一条业务规则。

### 12.3 新表与外键：为什么预约要关联三个模型

预约模型的三个外键分别指向：

```text
reservation.user_id      → users.id
reservation.lab_id       → labs.id
reservation.equipment_id → equipments.id，可为空
```

外键保证引用的记录存在。例如设备 ID 指向一条不存在的设备记录时，正确启用的数据库外键会拒绝这种关联。

但是三个外键分别成立，不代表“设备属于提交的实验室”。A 实验室和 B 实验室设备都是真实记录时，外键仍可能同时合法。设备归属需要业务层额外检查，这正是本次修补的重点。

模型中的：

```python
user: Mapped[User] = relationship()
lab: Mapped[Lab] = relationship()
equipment: Mapped[Equipment] = relationship()
```

让 ORM 对象可以通过 reservation.user、reservation.lab、reservation.equipment 访问关联对象。relationship 不等于自动校验所有业务关系，也不会自动替你写预约审核流程。

equipment_id 使用 nullable=True，因此整间实验室预约的 equipment 关系实际可能为 None。当前类型标注仍写 Mapped[int]、Mapped[Equipment]，以后可以整理成可选类型，让编辑器提示与允许空值的实际含义一致。

当前日期与时间仍保存为字符串列；预约日期列甚至允许数据库 NULL，但创建请求要求传 date。数据库约束、请求模型和业务规则是三层不同的限制。

### 12.4 数据库表名从 lab 到 labs 的演进

当前 Lab.**tablename** 已从 "lab" 改为 "labs"，设备模型的 ForeignKey 也从 "lab.id" 改为 "labs.id"。新预约表直接引用 labs.id。

这个改动不影响前端仍使用 /api/lab 作为接口地址。数据库表名和 HTTP 路径由各自代码约定，不需要同名。

但它会影响旧数据库：

- 新的空数据库会按模型建立 labs 表。
- 旧库的 lab 表不会因为修改 Python 字符串而自动改名。
- create_all() 可能新建空 labs 表，旧数据仍在 lab 中。
- 已有 equipments 的外键也不会自动从 lab.id 迁到 labs.id。

本次已有的 add_username_unique 脚本只处理用户名唯一性，不处理表名、实验室数据或设备外键。

因此从第 10、11 章升级旧学习库时，先备份，再核对实际表结构、数据、ID 和关联外键，准备迁移方案。不能在未检查时直接把旧表删除。当前没有这项自动迁移脚本，本次文档工作也没有执行旧库迁移。

若从空目录、空数据库复现本轮版本，使用当前模型中的 labs 即可，不需要先创建旧 lab 表再改名。

### 12.5 请求模型里的时间规范化

当前 ReservationCreateRequest 接收：

```python
class ReservationCreateRequest(BaseModel):
    lab_id: int
    equipment_id: int | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None
```

没有默认值的字段是必填；equipment_id、remark 可以不传或传空值。

模型还增加字段校验器：

```python
@field_validator("start_time", "end_time")
@classmethod
def normalize_time(cls, value: str) -> str:
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError("时间格式应为 HH:MM, 例如 09:00") from None
```

这是类内部的方法片段，完整类见本章快照。

可以按下面的顺序理解：

1. Pydantic 创建请求模型时，处理 start_time 和 end_time 两个字段。
2. field_validator 把这个方法注册为字段校验器，不需要接口手动调用。
3. cls 是当前类；这次方法并未使用 cls，但 @classmethod 约定第一个参数接收类。
4. strptime 把文本解析为日期时间对象；strftime 按指定格式输出文本。
5. "9:00" 可以规范为 "09:00"；不能解析的值触发 ValueError。
6. from None 隐藏异常链中原始解析错误的上下文，向外给出当前自定义错误。

字段校验器返回什么，后续业务函数拿到的字段值就是什么。机制可查 [Pydantic 字段校验器](https://docs.pydantic.dev/latest/concepts/validators/)。

当前统一 RequestValidationError 处理器会把字段校验错误包装为 HTTP 422、message“请求参数校验错误”。因此前端不一定直接显示这里写的 HH:MM 详细提示。

还要注意：这里只规范时间，没有把 date 从 str 改为真正的日期类型。不要把“两个时间字段有校验器”理解成整个预约日期与时段已经完整校验。

### 12.6 新接口怎样接入现有应用

backend/app/api/reservation.py：

```python
router = APIRouter(prefix="/reservation", tags=["预约服务接口"])


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.create_reservation(data=data, current_user=current_user, db=db)
    return Response.success()
```

完整地址由两个路由前缀组成：

```text
api/__init__.py：APIRouter(prefix="/api")
        + reservation.py：prefix="/reservation"
        + @router.post("")
        = POST /api/reservation
```

api.include_router(reservation_router) 注册预约路由；main.py 再 app.include_router(api) 注册到应用。

main.py 还显式导入 Reservation，使表的元数据在 create_all() 前注册。文件存在于 models 目录，并不等于 Python 自动执行过里面的类定义。

接口使用 get_current_user，当前没有单独限制只有 student 可提交。实际要求是登录身份有效、用户存在且账号可用。

请求体没有 user_id。业务代码把 current_user.id 写入预约，避免客户端直接指定预约归属。status 同样由服务端写为 0，不由本次请求自由指定。

### 12.7 一次提交的完整调用链

```mermaid
sequenceDiagram
    participant U as 用户
    participant P as LabList或LabEquipment
    participant C as ReserveDialog
    participant R as request.js
    participant A as reservation API
    participant S as reservation_service
    participant D as 数据库
    U->>P: 点击预约
    P->>C: 传入资源信息，visible设为true
    U->>C: 填写日期、时段和备注
    C->>C: 校验表单，设置submitting
    C->>R: createReservationApi(payload)
    R->>A: POST /api/reservation，附带token
    A->>A: 请求模型与当前用户检查
    A->>S: data、current_user、db
    S->>S: 日期和时段检查
    S->>D: 获取实验室及可选设备的事务锁
    S->>S: 检查状态、开放时间和设备归属
    S->>D: 锁内查询重叠预约
    alt 没有冲突
        S->>D: 插入status=0，提交事务
        A-->>R: code=200，data=null
        R-->>C: 业务响应对象
        C->>P: emit update:visible false
        C-->>U: 提示预约已提交，等待审核
    else 冲突或校验失败
        S->>D: 回滚事务，释放锁
        A-->>R: 统一错误响应
        R-->>U: 显示错误提示
        C->>C: 保留表单，恢复submitting
    end
```

锁的具体作用在本章后面的[并发处理](#reservation-concurrency)中展开。这里先记住，查冲突和写入预约必须在同一套事务规则里完成，不能把它们当成互不相关的两步。

### 12.8 业务函数先检查日期与时间

服务先把请求里的开始、结束时间解析成 time 对象，再与当前时间、实验室开放时间比较。

当前规则如下：

| 条件                                | 当前处理                   |
| ----------------------------------- | -------------------------- |
| date 文本小于今天的 YYYY-MM-DD 文本 | 拒绝，预约日期不能小于当天 |
| end_time 小于 start_time            | 拒绝                       |
| 日期是今天，开始时间小于当前分钟    | 拒绝                       |
| 实验室不存在或关闭                  | 拒绝                       |
| 有开放开始时间，预约开始更早        | 拒绝                       |
| 有关闭时间，预约结束更晚            | 拒绝                       |
| 设备不存在、归属不符或状态不是 1    | 拒绝                       |

当天时间会去掉秒和微秒，因此比较精度是分钟。预约业务仍使用服务器的 datetime.now() 本地时间；JWT 改成 UTC 并没有自动把预约业务也改成统一时区。

当前存在几个明确边界：

- 日期仅做字符串比较，没有验证日历上是否存在这一天。
- 使用 end_time < start_time，等于时不会被这一条拒绝，所以零时长问题仍在。
- 当前时段模型不支持结束时间跨到次日。
- 实验室自身开放时间没有同等完整的保存校验，数据库中不合法的文本仍可能让 strptime 抛错。
- props 和页面上的禁用按钮不能代替后端校验；当前后端检查设备状态是否严格等于 1。

这些不是本轮教程新加的功能，而是对现有检查范围的解释。应按第 18.12 节继续完善。

### 12.9 怎样判断两个时间段重叠

已有预约记为 A，新预约记为 B。重叠条件是：

```text
A 的开始 < B 的结束
并且
A 的结束 > B 的开始
```

例如已有 09:00–10:00：

| 新预约      | 是否重叠 | 原因                 |
| ----------- | -------- | -------------------- |
| 09:00–10:00 | 是       | 完全相同             |
| 09:30–10:30 | 是       | 09:30–10:00 共同占用 |
| 08:30–09:30 | 是       | 09:00–09:30 共同占用 |
| 08:00–11:00 | 是       | 包含已有时段         |
| 10:00–11:00 | 否       | 只是首尾相邻         |
| 08:00–09:00 | 否       | 只是首尾相邻         |

严格的 < 和 > 让相邻时段可以衔接。理解成左闭右开的区间 [开始, 结束) 会比较方便，但前提是先要求开始小于结束；当前零时长规则还没有补齐。

实际查询使用：

```python
query = db.query(Reservation).filter(
    Reservation.date == data.date,
    Reservation.status.in_([0, 1]),
    func.time(Reservation.start_time) < end_time.strftime("%H:%M:%S"),
    func.time(Reservation.end_time) > start_time.strftime("%H:%M:%S"),
)
```

filter 中多个条件共同成立才算匹配。in\_([0, 1]) 表示只考虑待审核和已通过记录。func.time 生成数据库 TIME 函数表达式，让存储的时间文本按数据库时间进行比较；它不会把任意非法历史文本都变成有效预约数据。

### 12.10 实验室预约与设备预约的冲突范围不同

设备预约追加：

```python
query = query.filter(Reservation.equipment_id == data.equipment_id)
```

整间实验室预约追加：

```python
query = query.filter(
    Reservation.lab_id == lab.id,
    Reservation.equipment_id.is_(None),
)
```

is\_(None) 对应 SQL 的 IS NULL。SQL 里的空值判断与普通值相等比较不同，所以这里明确使用空值判断表达式。

当前规则是：

- 实验室预约只与同实验室的“整间预约”比较。
- 设备预约只与同一个设备 ID 的预约比较。
- 不同设备可以在同一时段分别预约。
- 整间实验室和其中设备，也可能在同一时段分别预约。

后端现在会串行处理同一实验室的预约提交，但“先后处理请求”和“业务上互相冲突”是两个概念。事务锁不会自动补出实验室与设备之间的互斥规则。

设备冲突不再依赖历史预约的 lab_id，这样设备更换所属实验室后，旧记录仍会参与同设备冲突检查。设备转移前如何处理未来预约，是另一项尚未完整定义的规则。

<a id="17-logic-fixes"></a>
<a id="reservation-concurrency"></a>

### 12.11 “先查没有，再创建”为什么仍然会重复

假设只写：

```text
查询：这个时间段有没有预约？
没有 → 插入预约 → 提交
```

单人逐次点击可能一直正常，但两个请求可以交错：

| 时刻 | 请求 A         | 请求 B           |
| ---- | -------------- | ---------------- |
| 1    | 查询，没有预约 |                  |
| 2    |                | 查询，也没有预约 |
| 3    | 插入并提交     |                  |
| 4    |                | 插入并提交       |

两个请求都没有违背自己当时看见的结果，最终却占用了同一资源。

这叫竞态：结果依赖多个操作的执行先后。并发并不要求每一行代码在物理上完全同时执行，只要流程交错就可能出现。

前端 submitting 只能保护当前组件；另外一名用户不会共享这个变量。只给“资源、日期、开始、结束完全相同”加唯一约束，也挡不住 09:00–10:00 与 09:30–10:30 的部分重叠。

因此当前预约修补使用事务锁，让影响同一资源的检查和插入按约定顺序完成。账号重名则适合用数据库唯一约束，两类问题采用的工具不同。

### 12.12 先理解 Session、事务、commit 和 rollback

Session 是代码和数据库交互的会话；事务把一组数据库操作组织成一次需要一起完成或撤销的工作。

在预约中，可以把事务范围理解成：

```text
获取资源锁
  → 检查最新资源及预约
  → 插入新记录
  → commit 成功，持久保存并释放事务锁

中间发生失败
  → rollback 撤销本次未提交操作并释放事务锁
  → 把错误继续交给上层
```

db.add() 把对象交给会话管理，不等于已经提交；commit() 会在需要时先把变更发送给数据库，再提交事务。

当前代码没有另起一个显式 with db.begin() 包裹整个函数。SQLAlchemy 会在数据库操作时启动事务，认证查询也可能已经让同一会话进入事务。服务成功时 commit，失败时 rollback，构成这里的边界。

数据库写入失败后，会话需要正确回滚，才能恢复到可继续使用的状态。相关机制可查 [SQLAlchemy Session 回滚](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#rolling-back)。

回滚只影响本次事务尚未提交的操作，不会把别人的已提交预约撤销，也不等于删除所有历史记录。

### 12.13 为什么先锁实验室，而不是只锁“查到的预约”

一个从未有人预约的时间段，冲突查询会返回空结果。如果只围绕已经查到的预约行设计锁，第一次预约可能没有稳定的记录可以作为共同入口。

当前实现先对已经存在的实验室行执行：

```python
db.execute(
    update(Lab)
    .where(Lab.id == data.lab_id)
    .values(id=Lab.id, update_time=Lab.update_time)
    .execution_options(synchronize_session=False)
)
```

从 SQL 意义上，可以理解成：

```sql
UPDATE labs
SET id = id, update_time = update_time
WHERE id = :lab_id;
```

:lab_id 是参数占位符，这段 SQL 用于解释 ORM 表达式，不是让你把冒号原样当作普通 MySQL 交互命令执行。

这次 UPDATE 不打算改变资料值，目的是在事务内取得写锁。显式保留 update_time，是因为基础模型有更新时间的 onupdate 规则；预约不应该把实验室资料的更新时间刷新成预约提交时间。

synchronize_session=False 表示这次批量 SQL 不去额外同步会话中已有对象的属性。随后查询使用 populate_existing()，重新用查询到的数据填充已存在的 ORM 对象，避免继续使用旧属性。

接下来的查询还加 with_for_update()。在 MySQL/InnoDB 下，它生成锁定读取，读取资源并持锁到事务结束。设备预约还会锁定设备行并重新检查归属和状态。

当前按实验室作为共同入口，意味着同一实验室内不同设备、甚至不同日期的提交也会在这个实验室行上等待。它简化了顺序控制，但不是高并发吞吐量优化方案。

SQLite 测试中的写锁粒度与 InnoDB 行锁不同，不能仅凭临时 SQLite 通过，就断言真实 MySQL 的所有锁行为已经验收。

### 12.14 为什么冲突查询还要 with_for_update()

服务最后执行：

```python
if query.with_for_update().first():
    raise BusinessException(message="该时段已预约", code=409)
```

“已经拿到实验室锁”与“用什么方式读取预约”各有作用。

MySQL/InnoDB 的 REPEATABLE READ 隔离级别下，普通一致性读取可能继续使用当前事务已有的读取快照。认证阶段先查过用户，事务就可能已经开始读取；后面再用普通查询，不一定按你直觉中的“重新看最新结果”。

锁定读用于读取最新可用数据，并与其他事务的锁协调。这里让等待到实验室锁的请求，再检查刚刚已经提交的预约。原理见 [MySQL 锁定读](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html)。

因此当前流程同时包含：

1. 实验室行提供稳定的提交顺序入口。
2. 设备行保护当前设备状态与归属检查。
3. 冲突查询采用锁定读。
4. 插入与提交完成后才释放锁。

以后新增其他预约写入入口，也需要遵守一致的事务与资源检查规则；否则绕过这条服务路径的写入不会自动获得同样的保护。

### 12.15 外层包装函数：失败回滚和有限重试

reservation_service.py 将主要逻辑放进 \_create_reservation，外层 create_reservation 负责异常处理。

下划线开头是“内部辅助函数”的命名约定，不是 Python 强制的访问权限。接口调用外层函数，避免漏掉回滚和重试。

当前按 range(3) 执行，attempt 依次为 0、1、2：

| 异常情况                      | 当前处理                              |
| ----------------------------- | ------------------------------------- |
| MySQL 死锁码 1213，前两次尝试 | 先回滚，短暂等待，再重新执行整个事务  |
| 第三次仍死锁                  | 回滚，返回业务 code=409，提示资源正忙 |
| 锁等待超时码 1205             | 回滚，直接返回上述忙碌提示            |
| 其他 OperationalError         | 回滚后继续抛出原异常                  |
| 业务校验失败或其他 Exception  | 回滚后继续抛出                        |

最多是总共执行三次，不是首次之后再重试三次。等待分别是 0.01、0.02 秒，只在前两次死锁重试前发生。

死锁可以理解为多个事务各自持有某些锁，又互相等待对方释放。数据库会选择回滚某个事务，应用要准备重新执行完整流程。参见 [MySQL 死锁处理](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html)。

为什么不能只重试最后的 INSERT？因为数据库状态可能已经变化，资源和冲突检查也必须重新做。

异常语法有两个常见形式：

- 单独的 raise：把当前异常继续抛给上层。
- raise BusinessException(...) from exc：抛出面向业务的异常，同时保留原始异常作为原因，便于定位。

这里 rollback 后再 raise，确保失败不会留下仍持锁的未结束事务。当前返回的 409 是业务码，统一 BusinessException 处理器仍使用 HTTP 200。

### 12.16 设备存在还不够：必须属于所选实验室

当前新增：

```python
if equipment.lab_id != lab.id:
    raise BusinessException(message="该设备不属于所选实验室", code=400)
```

例如请求 lab_id=1、equipment_id=9，而设备 9 实际属于实验室 2，接口应该拒绝。即使前端正常页面不会这样组装参数，后端仍要独立检查。

设备冲突现在只按实际设备 ID 查，不再额外限定历史预约的 lab_id。这样历史记录里的实验室 ID 与设备现在的位置不同，也不会被冲突查询漏掉。

这解决了审查中“跨实验室构造参数”以及“只因设备移位而漏查历史冲突”的关键部分。

但管理员更新设备时，仍没有专门处理“设备还有未来有效预约，是否允许搬迁”的流程；预约历史也仍保留原来的实验室 ID。不要把冲突查询修正写成设备转移业务已全部完成。

### 12.17 两个父页面怎样复用一个弹窗

LabList.vue 中保存：

```js
const reserveVisible = ref(false);
const currentLab = ref(null);

const handelReserve = (lab) => {
  currentLab.value = lab;
  reserveVisible.value = true;
};
```

模板传入实验室：

```html
<reserve-dialog
  v-model:visible="reserveVisible"
  :lab-id="currentLab?.id"
  :lab-name="currentLab?.name"
/>
```

这里没有传设备，所以弹窗提交整间实验室预约。

LabEquipment.vue 则增加 currentEquipment，区分两种按钮：

```js
const hanldeReserveLab = () => {
  currentEquipment.value = null;
  reserveVisible.value = true;
};

const hanldeReserveEquipment = (equipment) => {
  currentEquipment.value = equipment;
  reserveVisible.value = true;
};
```

点“预约实验室”时先清空 currentEquipment 很重要：否则刚刚选过设备，再切回实验室预约，弹窗可能仍带着上一次的设备 ID。

父页面负责“选中了谁”，公共组件负责“怎么填写和提交”。这是本次组件复用的主要设计思想。

### 12.18 defineProps、defineEmits 和 v-model:visible

ReserveDialog.vue 声明：

```js
const props = defineProps({
  visible: Boolean,
  labId: Number,
  labName: String,
  equipmentId: Number,
  equipmentName: String,
});

const emit = defineEmits(["update:visible"]);
```

props 是父组件传给子组件的数据。lab-id 在模板中对应脚本中的 labId，这是 Vue 组件属性的常见命名对应。

defineProps、defineEmits 是 script setup 的编译宏，不需要像 ref 一样从 vue 导入。emit 是得到的事件发送函数，可以把变化通知父组件。

父组件的：

```html
<ReserveDialog v-model:visible="reserveVisible" />
```

可以理解为以下属性与事件配对：

```html
<ReserveDialog
  :visible="reserveVisible"
  @update:visible="reserveVisible = $event"
/>
```

$event 就是子组件发送的值。子组件执行 emit('update:visible', false)，父组件便把自己的 reserveVisible 更新为 false，再把新的 visible 传回子组件。参见 [Vue 组件 v-model](https://vuejs.org/guide/components/v-model.html)。

这条流程没有直接给 props.visible 赋值。数据由父组件持有，子组件通过事件提出更新。

当前 props 只声明了类型，没有 required:true，也没有正整数约束。目标实验室详情尚未加载或失败时，父页面仍可能传入 undefined；这种输入仍需要后端兜底，页面以后可以在资源准备好前禁用按钮。

### 12.19 弹窗内部怎样控制打开、重置与关闭

el-dialog 读取 visible，并在关闭时向上通知：

```html
<el-dialog
  :model-value="visible"
  title="预约"
  @open="handleOpen"
  @close="emit('update:visible', false)"
>
  <!-- 表单和按钮 -->
</el-dialog>
```

这里分成两层：父页面控制 ReserveDialog.visible，ReserveDialog 再把 visible 交给 el-dialog 的 model-value。

打开后：

```js
const handleOpen = async () => {
  await nextTick();
  formRef.value?.resetFields();
};
```

nextTick 等待本轮 Vue 更新，让表单引用有机会准备完成。?. 表示引用还没有时不继续调用。

resetFields 会按表单字段保存的初始值恢复并清理校验状态，不是简单把所有字段都变成空字符串。当前初始日期为空，开始和结束默认是 09:00、17:00。恢复规则见 [Element Plus Form](https://element-plus.org/en-US/component/form.html)。

默认时段不会自动匹配每个实验室的开放时间。例如实验室 16:00 关闭，用户还需要调整默认结束时间，后端也会再次检查。

### 12.20 日期和时间控件：显示格式与提交值

日期控件有：

```html
<el-date-picker
  v-model="form.date"
  type="date"
  format="YYYY-MM-DD"
  value-format="YYYY-MM-DD"
/>
```

format 控制界面显示，value-format 控制绑定到 form.date 的值格式。当前绑定得到日期字符串，而不是直接把 Date 对象作为请求体字段。参见 [Element Plus DatePicker](https://element-plus.org/en-US/component/date-picker.html)。

时间控件同样用 format、value-format 设置 HH:mm，绑定到 form.startTime、form.endTime。

这里前端格式字符串是 YYYY-MM-DD、HH:mm；Python 的解析格式是 %Y-%m-%d、%H:%M。它们属于不同库的约定，不能互换。

当前前端 rules 主要检查日期和两个时间必填，没有实现完整的“不能过去、结束必须晚于开始、必须在开放时间内”等联动校验。用户可选中一个值，不代表预约一定会被接受。

### 12.21 从表单对象转换成 API 请求体

前端 API 函数：

```js
export function createReservationApi(data) {
  return request({
    url: "/api/reservation",
    method: "post",
    data,
  });
}
```

组件提交时显式组织字段：

```js
const res = await createReservationApi({
  lab_id: props.labId,
  equipment_id: props.equipmentId ?? null,
  date: form.date,
  start_time: form.startTime,
  end_time: form.endTime,
  remark: form.remark,
});
```

不是所有名字都会自动转换。labId → lab_id、startTime → start_time 都是这段代码明确映射的结果。

?? null 把 undefined 或 null 的设备 ID 统一为 null，让后端按整间实验室预约处理；数字设备 ID 则保持原值。

名称只用来展示，接口凭 ID 查询真实记录。当前请求也没有包含 user_id 和 status，后端分别使用当前用户 ID 和固定的初始状态。

request 返回 Promise，await 后 res 是拦截器解包后的业务响应对象。这个机制延续之前 loginApi 的讲解。

### 12.22 submitting 为什么放在表单校验之前

提交函数开头：

```js
if (submitting.value || !formRef.value) return;
submitting.value = true;
```

同一个弹窗已经在提交时直接返回；表单引用还不存在时也返回。随后马上设置 submitting=true，再去等待校验，避免快速双击在异步校验期间启动两条提交。

表单校验：

```js
const valid = await formRef.value.validate().catch(() => false);
if (!valid) return;
```

校验失败的拒绝被转换成 false，随后提前返回。由于这段代码位于 try 内，finally 仍会执行，把 submitting 恢复成 false。

请求成功时显示“预约已提交，请等待审核”，并 emit 关闭弹窗。网络失败时进入 catch，当前填写的表单保留，finally 恢复按钮状态。

当前 request.js 对业务 code=409 会提示，但仍返回业务对象，所以这类冲突通常不会进入组件 catch，而是让 if (res.code === 200) 不成立。业务 code=401 和 HTTP 请求失败会走拒绝路径。

submitting 保护当前组件的一次操作；两个浏览器、两个用户甚至直接调用接口都可以同时请求，因此真正的并发占用检查还要由数据库事务负责。

### 12.23 成功返回与预约状态的含义

服务构造 Reservation、db.add()、db.commit() 后结束，没有返回预约 ID 或完整记录。API 调用 Response.success()，所以当前成功结构是：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": null
}
```

不能在前端写 res.data.id 并期待取得新预约 ID；这项响应数据尚未提供。

模型约定的状态为：

| 值  | 含义   | 当前冲突查询是否考虑 |
| --- | ------ | -------------------- |
| 0   | 待审核 | 是                   |
| 1   | 已通过 | 是                   |
| 2   | 已拒绝 | 否                   |
| 3   | 已取消 | 否                   |

本轮提交只写入 0。状态字段允许表达后续阶段，不代表已经有接口把 0 改成 1、2、3。

在本章记录的 2026-10-20 版本中，待审核记录参与冲突判断，但还不能通过页面查看、取消或审核。第 13 节已补齐这些流程：拒绝和取消后不再占用时段，通过后继续占用。

### 12.24 从零编写这一模块的顺序

1. 先明确整间实验室和设备的预约规则，选择当前“一张表 + 可空 equipment_id”的设计。
2. 在已有 users、labs、equipments 模型上增加 Reservation，并在建表前导入。
3. 编写 ReservationCreateRequest，固定前后端字段名及时间格式。
4. 写服务中的资源、日期、开放时间和归属校验。
5. 写重叠公式和有效状态范围；结合本章并发处理把校验和插入放入受保护的事务。
6. 注册 POST /api/reservation，使用当前用户作为预约人。
7. 添加 createReservationApi，先确认接口请求和业务响应结构。
8. 写公共 ReserveDialog，完成 props、表单、校验、提交及关闭事件。
9. 从两个父页面传入目标资源，实验室预约时清空设备选择。
10. 恢复并运行对应回归用例（原 tests 目录当前缺失），再进行下一节的真实浏览器验收。

新库使用当前模型；旧库先完成第 12.4 节的结构核对和第 3.6 节的用户名索引升级。不要把“能在现有电脑运行”当成已经验证过从空环境复现。

### 12.25 本轮预约的浏览器验收清单

以下为待执行的端到端检查；本次仅运行了隔离测试和构建，没有在浏览器连真实 MySQL 完成这些操作。

| 操作                         | 应检查的结果                                                  |
| ---------------------------- | ------------------------------------------------------------- |
| 从实验室卡片打开预约         | 实验室名称正确，不显示设备字段                                |
| 从设备行打开预约             | 实验室与设备名称正确，请求携带正确设备 ID                     |
| 先预约设备，再打开实验室预约 | equipment_id 为 null，没有遗留上次选择                        |
| 关闭弹窗后重新打开           | 字段按初始值恢复，校验提示清理                                |
| 日期留空后提交               | 前端校验不通过，不发送创建请求                                |
| 正常提交                     | 新记录 user_id 来自登录用户，status=0；界面关闭并提示等待审核 |
| 快速连续点击提交             | 单个组件不同时发出多次创建请求                                |
| 同资源完全重叠或部分重叠     | 后端返回业务 code=409，表单保留                               |
| 相邻时段                     | 在其他条件满足时允许提交                                      |
| 不同用户同时抢同一时段       | 真实 MySQL 下核对仅一个成功，其他冲突或可重试提示             |
| 设备不属于指定实验室         | 后端拒绝，且没有残留预约                                      |
| 实验室关闭或设备维修         | 后端拒绝                                                      |
| 开始早于开放、结束晚于关闭   | 后端拒绝                                                      |
| 当天已过去的开始时间         | 按服务端当前分钟拒绝                                          |
| 零时长、非法日期             | 当前仍有漏洞，作为后续修补验收用例，不记为已正确拒绝          |
| 查看、审核、取消预约         | 当日没有入口；2026-10-21 已实现，按第 13.25 节验收            |
| 直接调用接口时登录失效       | 后端拒绝，前端按当前会话处理 401                              |

遇到业务 code=409，要同时检查 HTTP 状态：当前 BusinessException 的统一响应使用 HTTP 200。HTTP 200 只表示 HTTP 请求得到正常处理的响应，业务是否成功还要看 JSON.code。

### 12.26 预约事务与资源校验复习

| 问题                                                  | 核对要点                                   |
| ----------------------------------------------------- | ------------------------------------------ |
| 两个用户都查到“没有预约”，为什么仍不能各自提交？      | 检查和写入之间会交错，需要事务内的协调     |
| 实验室锁能不能自动禁止设备和整间实验室同一时间预约？  | 不能，锁决定操作顺序，冲突条件决定业务互斥 |
| equipment_id 和 lab_id 都存在，是否足以证明归属正确？ | 还要检查 equipment.lab_id == lab.id        |
| db.rollback 与 db.rollback() 有什么不同？             | 前者取得方法，后者调用方法                 |

### 12.27 本章阶段代码快照（2026-10-20）

以下记录 2026-10-20 的当前实现，包括已在代码中落地的并发修补；本章并发处理各节已拆开解释。示例和快照中的时间、资源规则保持当前状态，没有自动应用本章提出的待办。

<details>
<summary><code>backend/app/models/reservation.py</code></summary>

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String
from app.database import Base
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.user import User


class Reservation(Base):
    __tablename__ = "reservation"
    __table_args__ = {"comment": "预约信息"}

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="预约人", nullable=False
    )
    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id"), comment="实验室", nullable=False
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipments.id"), comment="设备, 空则表示预约实验室", nullable=True
    )
    date: Mapped[str] = mapped_column(String(20), comment="预约日期", nullable=True)
    start_time: Mapped[str] = mapped_column(
        String(20), comment="开始时间", nullable=False
    )
    end_time: Mapped[str] = mapped_column(
        String(20), comment="结束时间", nullable=False
    )
    remark: Mapped[str] = mapped_column(String(255), comment="备注", nullable=True)
    status: Mapped[int] = mapped_column(
        default=0, comment="预约状态: 0待审核, 1已通过, 2已拒绝, 3已取消”"
    )

    user: Mapped[User] = relationship()
    lab: Mapped[Lab] = relationship()
    equipment: Mapped[Equipment] = relationship()
```

</details>

<details>
<summary><code>backend/app/schemas/reservation.py</code></summary>

```python
from datetime import datetime
from pydantic import BaseModel, field_validator


class ReservationCreateRequest(BaseModel):
    lab_id: int
    equipment_id: int | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_time(cls, value: str) -> str:
        try:
            # 接受 9:00 等输入，统一为 09:00 后再交给业务层。
            return datetime.strptime(value, "%H:%M").strftime("%H:%M")
        except ValueError:
            raise ValueError("时间格式应为 HH:MM, 例如 09:00") from None
```

</details>

<details>
<summary><code>backend/app/services/reservation_service.py</code></summary>

```python
from datetime import datetime
from time import sleep
from sqlalchemy import func, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest


def create_reservation(db: Session, current_user: User, data: ReservationCreateRequest):
    for attempt in range(3):
        try:
            _create_reservation(db, current_user, data)
            return
        except OperationalError as exc:
            db.rollback()
            error_code = exc.orig.args[0] if exc.orig.args else None
            # InnoDB 死锁需要重试整个事务，每次仍重新持锁并检查冲突。
            if error_code == 1213 and attempt < 2:
                sleep(0.01 * (attempt + 1))
                continue
            if error_code in (1205, 1213):
                raise BusinessException(
                    message="预约资源正忙，请稍后重试", code=409
                ) from exc
            raise
        except Exception:
            # 包括业务校验失败在内，及时释放本次事务持有的资源锁。
            db.rollback()
            raise


def _create_reservation(db: Session, current_user: User, data: ReservationCreateRequest):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.time().replace(second=0, microsecond=0)
    start_time = datetime.strptime(data.start_time, "%H:%M").time()
    end_time = datetime.strptime(data.end_time, "%H:%M").time()
    if data.date < current_date:
        raise BusinessException(message="预约日期不能小于当天的日期")
    if end_time < start_time:
        raise BusinessException(message="预约的结束时间不能小于预约的开始时间")
    if data.date == current_date and start_time < current_time:
        raise BusinessException(message="当天预约的开始时间不能小于当前的时间")
    # 先锁定稳定存在的实验室行，再检查冲突并提交，避免空时段无行可锁。
    # 无值变更的 UPDATE 在 MySQL/InnoDB 和 SQLite 中均能持有写锁；
    # 显式保留 update_time，避免预约操作修改实验室的更新时间。
    db.execute(
        update(Lab)
        .where(Lab.id == data.lab_id)
        .values(id=Lab.id, update_time=Lab.update_time)
        .execution_options(synchronize_session=False)
    )
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")
    if lab.open_time and start_time < datetime.strptime(lab.open_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能早于实验室的开放时间")
    if lab.close_time and end_time > datetime.strptime(lab.close_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能晚于实验室的关闭时间")

    # equipment_id 不为空 则表示这次是预约的实验室设备
    if data.equipment_id is not None:
        equipment = (
            db.query(Equipment)
            .filter(Equipment.id == data.equipment_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        if equipment.lab_id != lab.id:
            raise BusinessException(message="该设备不属于所选实验室", code=400)
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")

    # 实验室或者设备是否是可预约的状态
    query = db.query(Reservation).filter(
        Reservation.date == data.date,
        Reservation.status.in_([0, 1]),  # 0表示待审核 1已通过
        func.time(Reservation.start_time) < end_time.strftime("%H:%M:%S"),
        func.time(Reservation.end_time) > start_time.strftime("%H:%M:%S"),
    )
    if data.equipment_id is not None:
        query = query.filter(
            Reservation.equipment_id == data.equipment_id
        )  # 预约实验室设备
    else:
        query = query.filter(
            Reservation.lab_id == lab.id, Reservation.equipment_id.is_(None)
        )  # 只预约实验室
    # InnoDB 默认 REPEATABLE READ 下使用当前读，避免复用认证查询建立的旧快照。
    if query.with_for_update().first():
        raise BusinessException(message="该时段已预约", code=409)

    reservation_model = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        remark=data.remark,
        status=0,
    )
    db.add(reservation_model)
    db.commit()
```

</details>

<details>
<summary><code>backend/app/api/reservation.py</code></summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest
from app.services import reservation_service

router = APIRouter(prefix="/reservation", tags=["预约服务接口"])


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.create_reservation(data=data, current_user=current_user, db=db)
    return Response.success()
```

</details>

<details>
<summary><code>frontend/src/api/reservation.js</code></summary>

```js
import request from "@/utils/request";

// 创建预约
export function createReservationApi(data) {
  return request({
    url: "/api/reservation",
    method: "post",
    data,
  });
}
```

</details>

<details>
<summary><code>frontend/src/components/ReserveDialog.vue</code></summary>

```vue
<template>
  <div>
    <el-dialog
      :model-value="visible"
      title="预约"
      width="450"
      @open="handleOpen"
      @close="emit('update:visible', false)"
    >
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-width="80px"
        style="width: 100%; padding-right: 30px; padding-top: 16px"
      >
        <el-form-item label="实验室">
          <el-input :model-value="labName" disabled />
        </el-form-item>

        <el-form-item v-if="equipmentId != null" label="设备">
          <el-input :model-value="equipmentName" disabled />
        </el-form-item>

        <el-form-item label="预约日期" prop="date">
          <el-date-picker
            v-model="form.date"
            type="date"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            placeholder="请选择日期"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="开始时间" prop="startTime">
          <el-time-picker
            v-model="form.startTime"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="请选择开始时间"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="结束时间" prop="endTime">
          <el-time-picker
            v-model="form.endTime"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="请选择结束时间"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="备注" prop="remark">
          <el-input
            type="textarea"
            v-model="form.remark"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit"
          >提交预约</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { createReservationApi } from "@/api/reservation";
import { ElMessage } from "element-plus";
import { ref, reactive, nextTick } from "vue";
const props = defineProps({
  visible: Boolean,
  labId: Number,
  labName: String,
  equipmentId: Number,
  equipmentName: String,
});
const submitting = ref(false);
const formRef = ref();
const emit = defineEmits(["update:visible"]);
const form = reactive({
  date: "",
  startTime: "09:00",
  endTime: "17:00",
  remark: "",
});
const rules = {
  date: [{ required: true, message: "请选择预约日期", trigger: "change" }],
  startTime: [{ required: true, message: "请选择开始时间", trigger: "change" }],
  endTime: [{ required: true, message: "请选择结束时间", trigger: "change" }],
};
const handleOpen = async () => {
  await nextTick();
  formRef.value?.resetFields();
};
const handleSubmit = async () => {
  if (submitting.value || !formRef.value) return;
  submitting.value = true;
  try {
    const valid = await formRef.value.validate().catch(() => false);
    if (!valid) return;
    const res = await createReservationApi({
      lab_id: props.labId,
      equipment_id: props.equipmentId ?? null,
      date: form.date,
      start_time: form.startTime,
      end_time: form.endTime,
      remark: form.remark,
    });
    if (res.code === 200) {
      ElMessage.success("预约已提交, 请等待审核");
      emit("update:visible", false);
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    submitting.value = false;
  }
};
</script>
```

</details>

<details>
<summary><code>frontend/src/views/LabList.vue</code></summary>

```vue
<template>
  <div>
    <el-card>
      <template>
        <div style="font-size: 16px; font-weight: bold">
          <span>实验室列表</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-input
          placeholder="请输入名称查询"
          v-model="params.keywords"
          style="width: 240px; margin-right: 8px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>

        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
      </div>
      <div>
        <el-row :gutter="16" v-loading="loading">
          <el-col
            v-for="item in tableData"
            :key="item.id"
            :span="6"
            style="margin-bottom: 16px"
          >
            <el-card shadow="hover">
              <img
                v-if="item.img"
                :src="item.img"
                alt=""
                style="
                  display: block;
                  width: 100%;
                  height: 150px;
                  object-fit: cover;
                  border-radius: 6px;
                "
              />
              <div
                v-else
                style="width: 100%; height: 150px; background-color: #f5f7fa; border-radius: 6px"
              ></div>
              <div style="font-size: 16px; font-weight: bold; margin-top: 10px">
                {{ item.name }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                位置: {{ item.location || "-" }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                容量: {{ item.capacity }} 人
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                开放时间:
                {{
                  item.open_time && item.close_time
                    ? `${item.open_time} - ${item.close_time}`
                    : "-"
                }}
              </div>
              <div style="margin-top: 12px; display: flex; gap: 8px">
                <el-button style="flex: 1" @click="handelViewEquipment(item)"
                  >查看设备</el-button
                >
                <el-button
                  style="flex: 1"
                  type="primary"
                  @click="handelReserve(item)"
                  >预约</el-button
                >
              </div>
            </el-card>
          </el-col>
        </el-row>
        <div style="margin-top: 10px; display: flex; justify-content: flex-end">
          <el-pagination
            v-model:current-page="params.page"
            v-model:page-size="params.page_size"
            :total="total"
            background
            layout="total, prev, pager, next"
            @current-change="load"
          />
        </div>
      </div>
    </el-card>
    <reserve-dialog
      v-model:visible="reserveVisible"
      :lab-id="currentLab?.id"
      :lab-name="currentLab?.name"
    ></reserve-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { getLabPageList } from "@/api/lab";
import { Search } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import router from "@/router";
import ReserveDialog from "@/components/ReserveDialog.vue";
const reserveVisible = ref(false);
const currentLab = ref(null);
const loading = ref(false);
const tableData = ref([]);
const labOptions = ref([]);
const total = ref(0);
const dialogVisible = ref(false);
const formRef = ref();
const form = reactive({
  id: null,
  lab_id: null,
  name: "",
  description: "",
  img: "",
  spec: "",
  quantity: 1,
  status: 1,
});

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: "",
  lab_id: null,
});

// 加载分页数据
const load = async () => {
  loading.value = true;
  try {
    const res = await getLabPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: "",
    description: "",
    img: "",
    location: "",
    capacity: 20,
    open_time: "08:30",
    close_time: "20:30",
    status: true,
  });
};

const handleSearch = () => {
  params.page = 1;
  load();
};

const handleCreate = async () => {
  resetForm();
  dialogVisible.value = true;
  await nextTick();
  formRef.value?.clearValidate();
};

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 });
  if (res.code === 200) {
    labOptions.value = res.data?.list;
  }
};

const handelViewEquipment = (lab) => {
  router.push({ path: "/manager/labequipment", query: { lab_id: lab.id } });
};

const handelReserve = (lab) => {
  currentLab.value = lab;
  reserveVisible.value = true;
};

onMounted(() => {
  loadLabs();
  load();
});
</script>
```

</details>

<details>
<summary><code>frontend/src/views/LabEquipment.vue</code></summary>

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div
          style="display: flex; justify-content: space-between; align-items: center"
        >
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || "实验室" }}设备列表</span>
          </div>
          <div>
            <el-button type="primary" @click="hanldeReserveLab"
              >预约实验室</el-button
            >
            <el-button @click="router.push('/manager/lablist')"
              >返回实验室列表</el-button
            >
          </div>
        </div>
      </template>
      <div
        v-if="lab"
        style="color: #666; margin-bottom: 16px; background-color: antiquewhite; padding: 10px"
      >
        <div style="margin-bottom: 10px">简介：{{ lab.description }}</div>
        <div>
          位置：{{ lab.location }}
          <span style="margin: 0 10px">|</span>
          容纳 {{ lab.capacity }} 人
          <span style="margin: 0 10px">|</span>
          开放：{{
            lab.open_time && lab.close_time
              ? `${lab.open_time} - ${lab.close_time}`
              : "-"
          }}
        </div>
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="img" label="图片" width="90">
          <template #default="{ row }">
            <div style="min-height: 50px">
              <el-image
                v-if="row.img"
                style="display: block; width: 50px; height: 50px; border-radius: 6px"
                :src="row.img"
                :preview-src-list="[row.img]"
                :preview-teleported="true"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="所属实验室" />
        <el-table-column prop="name" label="设备名称" />

        <el-table-column prop="spec" label="型号规格" />
        <el-table-column prop="quantity" label="数量" width="80" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? "正常" : "维修" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              :disabled="!row.status"
              type="primary"
              text
              bg
              @click="hanldeReserveEquipment(row)"
              >预约</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="loadEquipment"
        />
      </div>
    </el-card>
    <reserve-dialog
      v-model:visible="reserveVisible"
      :lab-id="lab?.id"
      :lab-name="lab?.name"
      :equipment-id="currentEquipment?.id"
      :equipment-name="currentEquipment?.name"
    ></reserve-dialog>
  </div>
</template>

<script setup>
import { getLab } from "@/api/lab";
import { ElMessage } from "element-plus";
import { ref, reactive, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getEquipmentPageList } from "@/api/equipment";
import ReserveDialog from "@/components/ReserveDialog.vue";
const route = useRoute();
const router = useRouter();
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const lab = ref(null);
const reserveVisible = ref(false);
const currentEquipment = ref(null);
const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id), // "8" -> 8
});

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true;
  try {
    const res = await getEquipmentPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list ?? [];
      total.value = res.data?.total ?? 0;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false;
  }
};

const hanldeReserveLab = () => {
  currentEquipment.value = null;
  reserveVisible.value = true;
};
const hanldeReserveEquipment = (equipment) => {
  currentEquipment.value = equipment;
  reserveVisible.value = true;
};
const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id);
    if (res.code === 200) {
      lab.value = res.data;
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
};

onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning("缺少有效的实验室查询条件 [lab_id]");
    return;
  }
  loadLab();
  loadEquipment();
});
</script>
```

</details>

总路由与 main.py 的同阶段快照见[应用入口阶段快照](#entry-history)。

Lab、Equipment 模型的 labs 表名版本见[资源模型与页面阶段快照](#resource-evolution-snapshots)。

<a id="18-reservation-workflow"></a>

## 13. 预约查询、取消、审核与自动过期

阶段起点：2026-10-21；自动过期补充于 2026-10-23。先定义预约状态，再依次讲查询、取消、审核与扫描，最后核对竞争条件、页面问题和验收。服务代码就近展示；后台任务的创建和关闭见[应用生命周期](#app-lifespan)。

### 13.1 从提交预约到处理预约

一次预约现在可以经历这样的过程：

```text
学生浏览实验室或设备
  → ReserveDialog.vue 填写申请
  → POST /api/reservation 保存待审核记录
  → MyReservation.vue 查询自己的申请
  → 本人取消，或者由管理员在 AuditReservation.vue 审核
  → 修改数据库中的 status
  → 页面重新查询，显示最新结果
```

申请仍使用原来的公共弹窗和创建接口。本次主要增加的是列表接口、取消接口、审核接口、两个列表页面，以及菜单与路由入口。没有另外创建“待审核表”“通过表”或“取消表”：各种状态的记录都在 reservation 表中。

当前普通注册创建 student 角色，前端菜单也按 student/admin 显示；后端列表则把所有非 admin 用户限制为查询本人。不要把这两处判断误认为同一段代码。

### 13.2 用状态转换理解业务规则

2026-10-23 补充：状态 0 还会在后台扫描发现预约结束时间已到时自动转为 3；状态 3 当前未区分本人取消和自动过期。扫描行为与并发边界见本章[自动过期](#reservation-expiry)及[验收范围](#expiry-validation)。

**状态**表示记录现在处于哪个阶段；**状态转换**表示某个操作允许把它从哪个阶段改到哪个阶段。

```mermaid
stateDiagram-v2
    state "待审核（0）" as Pending
    state "已通过（1）" as Approved
    state "已拒绝（2）" as Rejected
    state "已取消 / 已过期（3）" as Cancelled
    [*] --> Pending: 提交申请
    Pending --> Approved: 管理员通过
    Pending --> Rejected: 管理员拒绝
    Pending --> Cancelled: 本人取消
    Pending --> Cancelled: 扫描发现预约已结束
```

这张图描述当前正常、顺序执行时的业务规则；并发保证还需要第 13.22 节的处理。

| 当前状态       | 谁可以操作                               | 允许的操作                                      | 是否参与同资源时段冲突检查 |
| -------------- | ---------------------------------------- | ----------------------------------------------- | -------------------------- |
| 0：待审核      | 本人、管理员或后台扫描，分别执行相应规则 | 本人取消；管理员通过/拒绝；结束时间到后自动过期 | 是                         |
| 1：已通过      | 当前没有继续转换的接口                   | 不能再审核，不能取消                            | 是                         |
| 2：已拒绝      | 当前没有继续转换的接口                   | 可另行提交新申请                                | 否                         |
| 3：已取消/过期 | 当前没有继续转换的接口                   | 可另行提交新申请                                | 否                         |

“取消”和“删除”不同。取消只把 status 改为 3，原 ID、预约人、日期和资源仍保留。拒绝也一样保留记录。这与前一轮“有任意预约历史的用户或资源禁止删除”的规则相容：不再占用时段，不等于可以抹掉历史归属。

管理员有审核权限，但当前取消函数仍只允许本人取消自己的待审核记录，没有“管理员替任何人取消”的特殊分支。

### 13.3 文件地图与从零编写顺序

| 文件                                        | 本次职责                                          |
| ------------------------------------------- | ------------------------------------------------- |
| backend/app/models/reservation.py           | 沿用预约表、status 和关联关系；本轮没有新增字段   |
| backend/app/schemas/reservation.py          | 新增列表响应模型、审核请求模型                    |
| backend/app/services/reservation_service.py | 查询范围、分页、名称组装、取消和审核的状态检查    |
| backend/app/api/reservation.py              | GET 列表、PUT 取消、PUT 审核及身份依赖            |
| frontend/src/api/reservation.js             | 封装三个新请求                                    |
| frontend/src/views/MyReservation.vue        | 本人预约查询、筛选、翻页和取消                    |
| frontend/src/views/AuditReservation.vue     | 管理员查询、查看预约人、通过和拒绝                |
| frontend/src/router/index.js                | 注册两个页面                                      |
| frontend/src/layouts/Layout.vue             | 按角色显示预约菜单                                |
| frontend/vite.config.js                     | 本轮修正 uploads 代理注释，代理目标和行为没有变化 |

这些文件不是每个都要重复写业务规则。页面负责收集操作与展示，API 层负责接收请求和检查身份，service 层负责业务与数据库操作，schema 负责数据形状与类型。

### 13.4 数据库模型、请求模型与响应模型为什么要分开

| 模型                     | 用在哪里              | 举例                                     |
| ------------------------ | --------------------- | ---------------------------------------- |
| Reservation              | SQLAlchemy 数据库模型 | 对应 reservation 表的一行                |
| ReservationCreateRequest | 创建请求              | 接收 lab_id、日期、时段等                |
| ReservationResponse      | 查询响应              | 返回记录字段，还包括 lab_name 等展示字段 |
| AuditReservationRequest  | 审核请求              | 只接收 status                            |

数据库里保存 lab_id，是为了关联实验室；页面需要 lab_name，是为了显示名称。响应模型可以比数据库表多出展示字段，不必因此给预约表增加同名列。

本次审核模型：

```python
class AuditReservationRequest(BaseModel):
    status: int  # 1 or 2
```

status: int 声明整数类型；后面的注释供人阅读，不会自动限制为 1 或 2。当前真正的允许值检查在 service 中：

```python
if status not in [1, 2]:
    raise BusinessException(message="审核状态错误")
```

因此 `{"status": 3}` 可以先通过这个请求模型，但随后会被业务层拒绝。将来可用 Literal 或枚举把允许值也写进模型，届时非法输入的错误路径和状态码可能变化，需要同步测试。

### 13.5 查询、取消与审核接口的接入

API 总路由前缀是 /api，预约路由前缀是 /reservation，各函数再提供最后一段路径：

| HTTP 方法 | 完整路径                                 | 参数来源                           | 身份与业务限制                       |
| --------- | ---------------------------------------- | ---------------------------------- | ------------------------------------ |
| GET       | /api/reservation/list                    | 查询字符串 page、page_size、status | 有效登录；service 决定数据范围       |
| PUT       | /api/reservation/{reservation_id}/cancel | URL 中的预约 ID                    | 有效登录；service 检查本人、待审核   |
| PUT       | /api/reservation/{reservation_id}/audit  | URL 中的 ID、JSON 中的 status      | 管理员；service 检查目标状态与待审核 |

例如：

```http
GET /api/reservation/list?page=1&page_size=10&status=0
```

这里的 0 在 URL 中是文本，FastAPI 根据 status: int | None 转换、校验为 Python 整数。省略 status 使用 None，意思是“不按状态过滤”；显式传 0 则是“只查待审核”。

审核函数虽然没有在函数体中使用 current_user，下面的依赖仍然会先执行：

```python
current_user: User = Depends(get_current_admin)
```

Depends 表示“在调用当前接口前，先取得这个依赖的结果”。get_current_admin 又依赖 get_current_user：验证 token、按用户 ID 查询数据库、检查用户状态，再检查数据库用户的 role 是否为 admin。它不是根据前端菜单决定权限，也不是只信任前端传来的角色。

审核 service 没有接收 current_user，管理员校验发生在 API 边界。将来从定时任务或其他入口调用该 service 时，也应明确调用权限，不能以为函数内部自动完成管理员认证。

### 13.6 同一个列表接口，为什么学生只看到自己

关键代码：

```python
query = db.query(Reservation)
if current_user.role != "admin":
    query = query.filter(Reservation.user_id == current_user.id)
if status is not None:
    query = query.filter(Reservation.status == status)
```

query 可以理解成逐步拼装的查询条件。filter 用来追加条件，并返回带有条件的查询对象，所以这里把结果重新赋给 query。

假设学生 A 的 ID 为 7，并筛选待审核，最终查询的含义是：

```sql
SELECT *
FROM reservation
WHERE user_id = 7 AND status = 0;
```

管理员不添加 user_id 条件，所以可以看到不同用户的记录。列表请求无需传 user_id；即使有人修改浏览器里的用户信息，后端仍使用已认证的 current_user。

这里必须写 `if status is not None`。Python 中整数 0 被当作假值，若写 `if status`，就会跳过“待审核”的筛选。这正好对应前面实验室布尔筛选的学习重点：检查“是否提供”，不能简单代替为检查“是否为真”。

### 13.7 count、offset、limit 怎样组成分页

当前代码先统计满足筛选的全部记录，再取其中一页：

```python
total = query.count()
items = (
    query.order_by(Reservation.id.desc())
    .offset((page - 1) * page_size)
    .limit(page_size)
    .all()
)
```

- count()：统计过滤后的总数，供分页组件显示。
- order_by(...desc())：按 ID 从大到小，通常新记录在前；不是按预约日期排序。
- offset：跳过多少条。例如第 3 页、每页 10 条，跳过 20 条。
- limit：本次最多取多少条。
- all()：执行这一页的查询，取得 ORM 对象列表。

total 不等于当前页数组长度。假设总共有 25 条，第 3 页只返回 5 条，但 total 仍是 25。

当前 page 和 page_size 只标注了 int，尚未限制 page >= 1、合理的 page_size 上限；status 也没有限制为 0～3。这些属于输入边界待完善项。

### 13.8 model_validate 与名称字段的组装

列表不会直接把数据库对象原样交给页面，而是逐行转换：

```python
res = ReservationResponse.model_validate(item)
res.user_name = item.user.name if item.user else None
res.lab_name = item.lab.name if item.lab else None
res.equipment_name = item.equipment.name if item.equipment else None
res.type = "设备" if item.equipment_id else "实验室"
```

ReservationResponse 中配置了：

```python
model_config = ConfigDict(from_attributes=True)
```

这使 model_validate 可以按字段名读取对象属性，例如 item.id、item.status，校验并建立一个响应模型。它与 model_dump 的方向不同：model_validate 是“输入数据或对象 → 模型”，model_dump 是“模型 → 字典”。model_config 是框架约定的配置名，不能随意改名。[Pydantic 对象属性校验说明](https://docs.pydantic.dev/latest/concepts/models/#arbitrary-class-instances)

`item.lab` 来自 Reservation 的 SQLAlchemy relationship；lab_id 把预约与 labs 表中的实验室关联起来。访问关联对象时，ORM 可能需要额外查询。当前没有显式配置列表的批量预加载，大量记录时可再评估关联查询开销。

`item.lab.name if item.lab else None` 是 Python 条件表达式：存在关联实验室就取名称，否则用 None。equipment 可以为空，因为整间实验室预约没有设备 ID。

`lab_name` 不是 Reservation 上已有的同名属性，model_validate 不会猜出它等于 lab.name。因此响应模型先允许它为 None，再由 service 明确填入。user_name 和 equipment_name 同理。

type 是当前响应中组装出的“实验室”或“设备”文字，不是预约表新增的字段；user_name 取的是用户的 name，而非登录账号 username。这些名称取自当前关联资料，若实验室或用户改名，下一次查询可能显示新名称，尚未保存提交时的名称快照。

### 13.9 lab_name 最后怎样显示到表格

你当前选中的代码是：

```vue
<el-table-column prop="lab_name" label="实验室" width="200" />
```

它的作用是：对表格中的每一行，读取该行对象的 lab_name，显示在标题为“实验室”的这一列，列宽为 200。

完整的数据路线是：

```text
reservation.lab_id
  → ORM 关联 item.lab
  → item.lab.name
  → service 赋值 res.lab_name
  → PageResponse.list 中的一项
  → Response.data.list
  → 前端 res.data.list
  → tableData.value
  → el-table 的一行 row
  → prop="lab_name" 读取 row.lab_name
```

列表响应示例（以下 ID 与名称仅用于说明）：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "list": [
      {
        "id": 42,
        "user_id": 7,
        "user_name": "学生A",
        "lab_id": 8,
        "lab_name": "物理实验室",
        "equipment_id": null,
        "equipment_name": null,
        "type": "实验室",
        "date": "2099-10-21",
        "start_time": "09:00",
        "end_time": "10:00",
        "remark": "课程实验",
        "status": 0
      }
    ],
    "total": 1
  }
}
```

prop 是 Element Plus 规定的列属性，它指向 data 数组中对象的字段。它不会自己发送 HTTP 请求，也不会直接查询数据库。[Element Plus 表格说明](https://element-plus.org/en-US/component/table.html)

如果标题显示了但名称为空，沿这条路线检查 Network 的响应是否有 lab_name、页面是否赋值 tableData、列名是否一致。只改 label 会改变标题；把 prop 改成 labName，后端也必须提供同名字段才能显示。

### 13.10 前端 API：params、data 与路径参数

这三个位置承担不同的事情：

```js
// 查询条件放在 URL 查询字符串
getReservationPageList({ page: 1, page_size: 10, status: 0 });

// ID 放在路径中，当前取消接口不需要请求体
cancelReservationApi(42);

// ID 在路径中；审核结果放在 JSON 请求体
auditReservationApi(42, 1);
```

审核封装的关键部分：

```js
return request({
  url: `/api/reservation/${id}/audit`,
  method: "put",
  data: { status },
});
```

反引号定义模板字符串，`${id}` 把实际 ID 插入地址。`{ status }` 是对象属性简写，等价于 `{ status: status }`。

与前面的 loginApi 一样，request 是默认导入的 Axios 实例，调用后返回 Promise。await 等到请求完成；request.js 的响应拦截器返回响应正文，因此页面得到的是包含 code、message、data 的对象，不是完整 Axios Response。列表数据才需要再读 res.data.list。

### 13.11 两个页面怎样筛选和显示状态

两个页面结构基本相同，但默认值不同：

| 页面                 | params.status 初始值 | 初次列表范围           | 操作列                 |
| -------------------- | -------------------- | ---------------------- | ---------------------- |
| MyReservation.vue    | null                 | 普通用户自己的全部状态 | 待审核行显示取消       |
| AuditReservation.vue | 0                    | 管理员可见的全部待审核 | 待审核行显示通过、拒绝 |

管理员页面还增加 user_name 列，便于区分申请人。它目前的卡片标题仍写“我的预约记录”，属于复制后的文案待调整，实际查询范围由后端身份决定。

筛选项写成 `:value="0"`，表示数字 0；如果写 `value="0"`，通常传给绑定值的是字符串。下面的严格比较要求类型一致：

```vue
<template v-if="row.status === 0">
  <el-button @click="handleAudit(row, 1)">通过</el-button>
  <el-button @click="handleAudit(row, 2)">拒绝</el-button>
</template>
```

`#default="{ row }"` 是默认作用域插槽：表格把当前行传给这段模板，`{ row }` 取出行对象，再用自己的标签和按钮渲染。

状态名称函数：

```js
const statusText = (status) => {
  return { 0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已取消" }[status] || "-";
};
```

这里创建了一张“数字 → 文字”的映射表，再用 `[status]` 查值。例如 status=2 得到“已拒绝”；没有对应值时用 `'-'`。statusType 用相同方法得到 warning、success、danger、info，控制标签颜色。

隐藏非待审核行的按钮是界面提示，真正阻止非法操作的仍是后端状态检查。

### 13.12 列表 load、分页与响应式更新

两个页面都用 ref 保存列表、总数和加载状态，用 reactive 保存查询条件。onMounted 调用 load，进入页面就开始查询。

当前 load 的主要动作：

```js
const res = await getReservationPageList(params);
if (res.code === 200) {
  tableData.value = res.data?.list;
  total.value = res.data?.total;
}
```

脚本中要用 `.value` 读写 ref；模板里的 tableData 和 total 会自动解包。新数组赋给 tableData.value 后，Vue 更新表格，不需要手动拼接 HTML。

`?.` 是可选链：当 data 为 null 或 undefined 时，表达式得到 undefined，避免直接读属性报错；它不等于“没有数据自动给空数组”。若需要默认数组和数字，可以写 `res.data?.list ?? []`、`res.data?.total ?? 0`。

handleSearch 先把 page 改为 1 再查询，是为了避免在第 3 页切换筛选后，新结果只有一页却仍请求第 3 页。分页组件的 current-change 调用 load；当前布局没有每页条数选择器，只提供总数、上一页、页码和下一页。

有两个实际细节需要理解：

1. 页面使用 pageSize，后端接收 page_size；API 封装直接传 params，并没有转换名字。现在两边默认都是 10，所以看起来能用，但不是后端识别了 pageSize。
2. loading 初始为 false，finally 只把它设回 false，load 开始时没有设为 true，所以当前 v-loading 不会因查询自动开启。

建议写法见第 13.23 节，当前源码快照仍保留真实实现。

### 13.13 本人取消：从确认框到数据库

前端操作顺序：

```text
点击当前行的取消按钮
  → await 确认框
  → 确认后调用 cancelReservationApi(row.id)
  → res.code === 200 时提示成功
  → await load() 重新取得列表
```

确认框返回 Promise。点击确认才继续向下执行；关闭或取消确认框会进入 catch，因此不会发出预约取消请求。页面的 catch 还接住网络失败，网络错误提示由 request.js 负责。

后端取消函数的顺序不能漏掉：

```python
item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
if not item:
    raise BusinessException(message="预约记录不存在")
if item.user_id != current_user.id:
    raise BusinessException(message="无权限", code=403)
if item.status != 0:
    raise BusinessException(message="当前状态无法取消")
item.status = 3
db.commit()
```

first() 取得第一条匹配记录，没有则是 None。raise 使函数在错误处结束，不会继续执行修改和 commit。

item.status = 3 先改变当前 ORM 对象；commit 提交事务，ORM 会把修改写入数据库。当前使用的是更新操作，不调用 db.delete，也不从前端数组中直接删除这行。正常返回 Response.success() 的 data 是 null，页面通过重新查询得到新的状态。

### 13.14 管理员通过与拒绝：一个接口两种结果

两个按钮复用 handleAudit(row, status)：通过传 1，拒绝传 2。页面根据 status 生成确认文字，确认后发送请求。

后端先检查目标状态，再查询记录并检查原状态：

```python
if status not in [1, 2]:
    raise BusinessException(message="审核状态错误")
item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
if not item:
    raise BusinessException(message="预约记录不存在")
if item.status != 0:
    raise BusinessException(message="当前状态不支持审核")
item.status = status
db.commit()
```

这是“只能把待审核改为通过或拒绝”，不是让管理员随意传任意数字修改记录。

当前审核请求只包含 status，没有拒绝理由输入框，也没有保存审核人或审核时间的专门字段。继承的 update_time 是记录最后更新时间，不足以替代完整审核记录。

管理员页面默认只查 status=0。通过或拒绝成功后 load 再次查询，这条记录不再满足过滤条件，于是从当前表格中消失。切换到已通过或已拒绝可重新看到；它没有被删除。

普通用户页面不会收到实时推送；管理员处理后，用户需要重新查询或再次进入页面才能看到新结果。

<a id="21-ai-fixes"></a>
<a id="reservation-expiry"></a>

### 13.15 过期扫描为什么独立于 HTTP 请求

旧流程只有本人取消与管理员审核。新增 `expire_pending_reservations()` 用独立 Session 扫描待审核记录，不需要用户点击按钮，也不使用接口 Depends 注入的 db。

当前判定规则是：日期早于今天，或者日期是今天且结束时间不晚于当前小时分钟，就把 status 从 0 改为 3。采用的是预约结束时间，已开始但未结束的申请仍可能留在待审核。日期与时间是字符串，比较依赖规范格式，尚未解决预约提交章指出的非法日期和零时长校验。

状态 3 同时表示用户取消和扫描过期；当前模型没有取消来源字段。状态 1、2、3 不在扫描范围。

### 13.16 changed 初始化与事务提交

```python
changed = False
for item in items:
    if item.date < today or (item.date == today and item.end_time <= time):
        item.status = 3
        changed = True
if changed:
    db.commit()
```

曾经 changed 只在 if 分支中赋值：无记录或所有记录未过期时，该分支一次也不进入，执行 if changed 就出现 UnboundLocalError。初始 False 表示“目前没有修改”，发现过期记录再改为 True。

多个记录修改后统一 commit；无修改则无需提交。finally 中 close 负责释放 Session。当前没有单独捕获扫描异常并重试，函数失败会继续向上抛出。

**错误复盘（2026-10-23）**

| 故障           | 原因               | 已保存的修补或定位方式 |
| -------------- | ------------------ | ---------------------- |
| changed 未赋值 | 仅在发现过期时赋值 | 在循环前初始化 False   |

### 13.17 扫描周期、异步等待与执行边界

以下是 2026-10-23 的同步调用阶段；当前已将扫描放到线程，见第 13.29 节。

```python
async def run_expire_scan():
    while True:
        expire_pending_reservations()
        await asyncio.sleep(60)
```

启动时第一轮立即执行，随后每次扫描结束等待 60 秒，实际间隔还包含扫描耗时。await sleep 期间让出事件循环；它前面的同步数据库函数仍在事件循环线程中执行，不会因为外层写了 async 自动变成异步数据库访问。

扫描任务由[应用 lifespan](#app-lifespan)创建和关闭。同步数据库访问仍在事件循环线程执行；异常会使当前任务退出，重试和任务监控仍需补齐。

<a id="reservation-expiry-code"></a>

### 13.18 reservation_service.py：过期扫描代码快照（2026-10-23）

该片段复用模块中的 asyncio、datetime、SessionLocal、Reservation 导入。

```python
def expire_pending_reservations():
    """批量取消过期的预约"""
    db = SessionLocal()
    try:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")
        items = db.query(Reservation).filter(Reservation.status == 0).all()
        changed = False
        for item in items:
            if item.date < today or (item.date == today and item.end_time <= time):
                item.status = 3
                changed = True
        if changed:
            db.commit()
    finally:
        db.close()


async def run_expire_scan():
    while True:
        expire_pending_reservations()
        await asyncio.sleep(60)
```

<a id="expiry-validation"></a>

### 13.19 自动过期的历史检查与待验收边界

2026-10-23 文档核对覆盖过期扫描与 lifespan，确认 changed 在循环前初始化、关闭时 cancel 后 await。此前对话曾在内存数据库中做过 6 项过期扫描/生命周期检查；这些是历史临时检查，不代表本次重新执行，也不能代替真实 MySQL 的竞争验证。

需要检查：无记录、全未过期、部分过期、跨日、结束时间恰好等于当前分钟、状态 1/2/3 不受影响、退出和重载、扫描异常退出、多个应用进程重复扫描，以及审核/取消/扫描同时更新。当前扫描按服务器本地日期时间比较规范字符串，部署时还应核对预约业务采用的时区。

当前状态 3 不区分本人取消与自动过期；状态转换仍缺少原状态条件的原子更新。扫描功能没有改变“已通过预约能否取消”或“设备预约是否占用整间实验室”的业务政策。

### 13.20 错误、权限与 Promise 的关系

| 场景                               | 当前后端响应方式                                   | 页面如何处理                         |
| ---------------------------------- | -------------------------------------------------- | ------------------------------------ |
| 查询、取消或审核成功               | HTTP 200，业务 code=200                            | 读取列表或提示并刷新                 |
| 取消他人记录、普通用户审核         | HTTP 200，业务 code=403                            | 拦截器提示；不执行成功分支           |
| 记录不存在、状态不允许、审核值错误 | 当前 BusinessException 默认业务 code=500，HTTP 200 | 拦截器提示；不执行成功分支           |
| 缺少必需字段或参数类型不合法       | HTTP 422                                           | 响应错误分支提示，Promise 拒绝       |
| 无有效登录凭证                     | 通常 HTTP 401                                      | 按 request.js 的会话规则处理登录失效 |

不要把表中业务 code=500 全部理解成服务器崩溃：当前业务异常类默认就是这个值。也不要根据 HTTP 200 就显示“审核成功”，必须检查正文中的 code。

当前拦截器遇到一般业务错误时提示信息，但仍 return data；因此 `await auditReservationApi(...)` 可能正常返回一个 code 非 200 的对象，不一定进入 catch。两个页面写 `if (res.code === 200)` 是必要的。

### 13.21 路由、菜单和代理分别做什么

前端两个子路由位于 /manager 下：

```js
{
  path: 'myreservation',
  name: 'MyReservation',
  component: () => import('@/views/MyReservation.vue')
}
```

完整页面地址是 /manager/myreservation；管理员页对应 /manager/auditreservation。`() => import(...)` 表示导航需要组件时再加载它。

Layout 的菜单 index 与完整页面路径对应，el-menu 的 router 属性让点击触发导航；外层布局中的 router-view 显示当前子页面。`:default-active="route.path"` 根据当前地址设置菜单选中项。

前端菜单用 userInfo.role 控制显示，但当前 router.beforeEach 只检查是否有 token，没有管理员专属路由校验。因此普通用户直接输入审核页地址仍可能打开页面外壳；列表接口仍只返回本人数据，审核接口仍由后端拒绝。不能把“菜单不可见”讲成“页面地址绝对不可进入”。

相反，管理员若手动进入 MyReservation 页面，共用列表接口仍按管理员身份返回全部用户记录；页面名不决定后端查询范围。

Vite 的 /api 代理把 API 请求转发到后端 8000 端口；/manager/... 是前端页面路径，二者不是同一套路由。本次 vite.config.js 只修正了 /uploads 的注释，没有新增预约专用代理。

### 13.22 创建预约有锁，为什么取消与审核还可能竞争

前一轮 create_reservation 的事务锁只在调用那个创建流程时执行。新 cancel_reservation 和 audit_reservation 都是普通查询后检查，再修改、提交，没有行锁、版本号或带 status=0 条件的原子更新。

从源码可推导出这样的交错风险：

```text
用户请求读取 status=0
管理员请求也读取 status=0
用户检查通过，提交 status=3
管理员根据此前读到的 0 检查通过，提交 status=1
结果：两边都可能提示成功，最后的写入覆盖前一个结果
```

两个管理员分别点击通过与拒绝也有同类风险。这是代码分析发现的并发边界，本轮未在真实 MySQL 上复现或完成修补。顺序执行时第二次会被拒绝，不等于同时执行也有同样保证。

后续可选择一致的加锁流程，或者让数据库在同一条更新中判断旧状态。下面只是取消的 SQL 思路，**尚未写入业务源码**：

```sql
UPDATE reservation
SET status = 3
WHERE id = :reservation_id
  AND user_id = :current_user_id
  AND status = 0;
```

`:reservation_id` 等是绑定参数占位符，不是让用户把原始输入拼接进 SQL。更新条件同时限定记录、归属和原状态；检查受影响行数，只有成功匹配 1 条才返回操作成功。审核也需要相应的旧状态条件，并保留管理员依赖。

完整改造还要处理未匹配时的反馈、commit/rollback、驱动的行数返回方式，以及与创建预约的锁顺序是否一致，不能只复制这条 SQL 就宣称并发问题全部解决。[SQLAlchemy 更新及匹配行数说明](https://docs.sqlalchemy.org/en/20/tutorial/data_update.html#getting-affected-row-count-from-update-delete)

### 13.23 当前代码细节与建议改法

2026-10-23 复核：预约两页的 pageSize 映射、loading、Search 导入与审核标题问题仍存在。新 AI 页的 loading/catch 修补并未同时修改这两个页面；下面建议仍需另行实施。

以下均为阅读源码发现的待完善项，本轮仅修改文档。

**列表参数和 loading。** 两个页面可参考下面的 load 改法，仍使用原有的 params.pageSize：

```js
const load = async () => {
  loading.value = true;
  try {
    const res = await getReservationPageList({
      page: params.page,
      page_size: params.pageSize,
      status: params.status === "" ? undefined : (params.status ?? undefined),
    });
    if (res.code === 200) {
      tableData.value = res.data?.list ?? [];
      total.value = res.data?.total ?? 0;
    }
  } catch {
    // 请求拦截器已提示失败；这里明确结束本次页面查询。
  } finally {
    loading.value = false;
  }
};
```

这段建议明确映射 page_size，并把没有筛选条件的值处理为不传，同时保留合法的 0。不要写 `params.status || undefined`，那会把 0 也丢掉。

如果允许快速连续查询，还需要防止旧响应覆盖新响应，并让 loading 表示最新请求的状态；上面仅演示参数和基础加载状态，不是所有请求竞争的完整解决方案。

**Search 图标。** 两个新页面使用 `:icon="Search"`，但没有导入 Search。main.js 的 app.component 全局注册能支持 `<Search />` 组件标签，不会自动建立表达式变量 Search。可以在 script setup 中加入下面的导入，或者使用已注册组件名的适当写法：

```js
import { Search } from "@element-plus/icons-vue";
```

本轮 Vue 编译检查确认脚本没有 Search 绑定，但构建仍可通过；模板访问未定义的上下文属性不一定是编译错误。应在浏览器检查图标及控制台提示。

**其他本轮边界。**

| 项目         | 当前行为                                          | 后续处理方向                                     |
| ------------ | ------------------------------------------------- | ------------------------------------------------ |
| 筛选事件     | 同时绑定 change 和 clear 调用 handleSearch        | 清空时检查是否重复发请求，保留足够的一套触发逻辑 |
| 查询异常     | load 有 finally，但没有 catch                     | 明确处理被拒绝的 Promise，保留统一错误提示       |
| 审核页标题   | 仍为“我的预约记录”                                | 改为与管理员用途一致的文案                       |
| 操作中的按钮 | 没有按行提交状态                                  | 防止连续点击，同时保留后端并发保护               |
| 审核条件     | 只校验目标状态、记录存在和原状态                  | 明确过期申请、资源停用/维修后的审核规则          |
| 审核记录     | 只有状态变化，无专门审核人、理由字段              | 需要追溯时增加模型、迁移、请求与页面             |
| 关联名称     | 显示当前资料名称                                  | 需要保留历史原名时明确快照方案                   |
| 预约规则     | 仍分开判断实验室/设备冲突，未用 quantity 分配名额 | 先确定业务规则，再改查询与测试                   |

日期有效性、零时长、基础数据和其他前轮遗留项继续见第 18.12 节。写出主要业务流程后，可以按这些明确边界逐项完善，不需要把“教程还需验证”理解成前面的代码白写了。

2026-10-23 的 Promise 修补只涉及 AIChat.vue；MyReservation.vue 与 AuditReservation.vue 的 loading、catch、图标和分页待办仍需各自验收，不能随 AI 页修补一起标记完成。

### 13.24 如果从空目录复现这一模块，按什么顺序

先完成前面章节的环境、用户认证、实验室设备模型、统一响应和[预约提交与并发](#16-reservation)的创建预约。然后按下面顺序扩展：

1. 画出第 13.2 节状态图，确定每个操作的调用者与允许的原状态。
2. 保持 Reservation 表和三种关联模型一致，确认现有库已具备正确表名和外键。本轮新增查询与操作无需增加数据库字段。
3. 写 ReservationResponse 和 AuditReservationRequest，明确展示字段与写入字段。
4. 写 get_reservation_page_list：先限制数据范围，再加状态过滤、总数、排序和分页，最后转换响应模型并填入名称。
5. 写取消和审核 service：逐项检查记录、归属或目标值、原状态，再更新并提交；并把并发保护列为实现要求。
6. 写三个 API 路由并注册到已有预约路由中，分别使用 get_current_user、get_current_admin。
7. 先用后端 /docs 检查请求和响应，再写 frontend/src/api/reservation.js，避免页面与接口参数各写一套名字。
8. 写 MyReservation.vue，从列表显示开始，加筛选与分页，最后加确认取消和成功刷新。
9. 写 AuditReservation.vue，复用查询方式，默认待审核，增加预约人、通过和拒绝。
10. 在 router/index.js 加页面，再在 Layout 按角色加菜单；确认 router-view 正确显示子页面。
11. 用第 13.25 节的三个账号完成正常和错误路径验收，记录真实结果。
12. 在独立空目录和学习数据库中重新安装、配置并运行，验证自己可以不依赖已有虚拟环境、node_modules 和旧数据库复现项目。

第 13.28 节保存当前代码作对照。复现时不应直接把“当前快照”当作没有边界问题的最终模板；建议修正的代码要自己实现并验证，随后更新对应快照与测试。

### 13.25 三个账号的浏览器与接口验收清单

以下清单尚未在本轮真实浏览器中执行。准备学生 A、学生 B、管理员 C，以及启用的实验室和正常设备。日期选未来有效日期，时段位于开放时间内。为了检查分页，至少准备 11 条满足同一筛选条件的记录，可使用不同不重叠时段或不同日期。

| 检查项           | 操作                                       | 预期结果                                         |
| ---------------- | ------------------------------------------ | ------------------------------------------------ |
| 实验室申请       | A 提交整间实验室预约                       | 新记录 status=0，type 显示实验室，设备列为占位符 |
| 设备申请         | A 提交所属设备预约                         | lab_name、equipment_name 与所选资源对应          |
| 本人范围         | A、B 分别登录查看我的预约                  | 两人各自只看到自己的记录                         |
| 管理员范围       | C 进入审核页                               | 默认全部用户的待审核记录，显示预约人             |
| 状态 0           | 选择待审核                                 | 不混入 1、2、3；确认 0 没被当作无条件            |
| 清空筛选         | 清除状态选择                               | 查看允许范围内全部状态；观察有无重复请求         |
| 分页             | 查询超过一页的结果并翻页                   | 总数、ID 顺序、每页结果正确；请求参数与后端一致  |
| 关闭确认框       | A 点击取消后关闭确认框                     | 无 PUT 取消请求，数据库状态不变                  |
| 本人取消         | A 确认取消自己的待审核记录                 | 状态改为 3，记录保留，不再显示取消按钮           |
| 越权取消         | B 或 C 调用 A 的取消接口                   | code=403，记录不变；管理员也无替人取消特例       |
| 审核通过         | C 通过一条待审核记录                       | 状态改为 1；从默认待审核列表消失，可切换筛选查看 |
| 审核拒绝         | C 拒绝另一条待审核记录                     | 状态改为 2；历史记录保留                         |
| 普通用户审核     | A 直接调用 audit 接口                      | code=403，状态不变                               |
| 不合法目标       | C 提交 status=0、3 或其他整数              | 业务拒绝，不改变记录                             |
| 不合法原状态     | 对 1、2、3 再次取消或审核                  | 业务拒绝，不改变记录                             |
| 无此记录         | 使用不存在的预约 ID                        | 显示业务错误，不提示操作成功                     |
| 占用与释放       | 对 0/1 再约同资源重叠时段；对 2/3 重新申请 | 0/1 阻止；2/3 在其他条件满足时允许               |
| 用户看到审核结果 | C 处理后 A 重新查询                        | 状态更新；不期待当前代码自动实时推送             |
| 接口失败         | 停止测试后端后查询/操作                    | 显示错误，不误提示成功；检查加载与按钮状态       |
| 同时操作         | 两个会话同时取消/审核或分别通过/拒绝       | 修补目标是只允许一次有效状态转换；当前不能保证   |

边界测试应在学习数据中做。接口权限测试不能只用隐藏按钮证明，需要直接调用接口，检查业务 code 与数据库实际状态。

### 13.26 本轮已经完成的检查与尚未覆盖的范围

本轮只更新两份文档，未修改业务代码、迁移数据库或更改现有账号。

已完成检查：

- 对 backend/app 下 Python 源码进行语法解析，检查通过。
- 从实际源码提取数据库模型类和预约业务函数，用内存 SQLite 创建临时表，不加载项目的真实数据库配置。检查普通用户与管理员查询范围、状态 0、分页顺序及总数、名称字段、越权取消、不同原状态、合法/非法审核值、记录保留，以及取消/拒绝后重新申请、通过后仍冲突。连同对 API 依赖的静态核对，共 33 个断言通过。
- 编译两个新 Vue 单文件组件，并提取实际页面函数，模拟 API 和确认框，检查默认筛选、列表赋值、确认成功、关闭确认框、业务失败与网络失败等行为，共 18 组场景检查通过。其中也验证了 pageSize 未映射、loading 始终未开启、Search 没有脚本绑定的当前事实；“检查通过”不意味着这些问题已修复。
- 在 frontend 运行 npm.cmd run build，构建通过，仍有大于 500 kB 的包体积提示。

这些临时检查没有保存为新增测试文件。它们不包含真正的 HTTP 登录与鉴权请求、真实浏览器交互、MySQL/InnoDB 锁竞争、旧库迁移，也不证明界面图标和加载提示已经正确。审核权限的依赖绑定核对与 service 的业务校验检查，也不能代替完整 HTTP 权限测试。

原后端测试、前端登录测试与 docs 审查文件仍未恢复。[历史回归记录](#historical-regression)中的 19 项后端与 6 项登录测试是历史结果；2026-10-26 新增的 frontend/tests/ai.test.js 为独立的 SSE 解析测试，结果见第 15.61 节，不能视为旧用例重新通过。运行测试命令时应检查实际发现的文件和用例数。

本地可重复运行的基础检查命令如下，分别在对应目录执行：

```powershell
# backend 目录：只检查 Python 语法，不是业务回归测试
.\.venv\Scripts\python.exe -m compileall -q app
```

```powershell
# frontend 目录：检查能否构建，不等于浏览器联调通过
npm.cmd run build
```

后续应把这些业务场景保存为可维护的测试文件，并完成真实浏览器清单。只有在空目录完整复现并验收后，才能完成本笔记最初约定的“从零复现整个项目”目标。

### 13.27 复习问题：检查自己是否能重新写出来

| 问题                                      | 应能说明的重点                                             |
| ----------------------------------------- | ---------------------------------------------------------- |
| 为什么列表不用让前端传 user_id？          | 后端从认证用户决定数据范围，普通用户不能自己选择查询别人   |
| 为什么 status=0 必须用 is not None 判断？ | 0 是合法筛选值，同时也是 Python 假值                       |
| lab_name 来自哪张表，在哪里赋值？         | labs 的 name，经 item.lab 取得，再写入 ReservationResponse |
| prop="lab_name" 是否会自己发请求？        | 不会；它只读取表格行对象中的字段                           |
| model_validate 与 model_dump 的方向？     | 输入对象建立模型；模型转换为字典                           |
| 为什么管理员审核后行消失？                | 默认筛选待审核，重新查询后已审核记录不再匹配               |
| 为什么取消后的历史仍不能随意删除？        | 时段占用和历史关联保护是两种不同规则                       |
| 隐藏审核菜单是否足以保护接口？            | 不足；后端 get_current_admin 必须独立执行                  |
| 为什么 pageSize=10 看似能分页？           | 后端忽略这个未声明名字，刚好使用 page_size 默认 10         |
| 创建预约有锁，是否保护了审核？            | 没有；不同函数必须各自保证所需的事务与状态约束             |
| 构建通过是否说明本轮业务全部验收？        | 不说明；还需真实 HTTP、数据库并发、浏览器与空环境复现      |

### 13.28 本章阶段代码快照（2026-10-21）

以下按 2026-10-21 当前文件原样保存，便于与前面的分步讲解对照。代码中保留了第 13.23 节标明的待完善点；第 12.27 节的预约创建入口、公共弹窗及 Reservation 模型继续作为前置内容。不要用旧版 reservation service 覆盖本章新增的查询与操作函数。

#### 13.28.1 backend/app/schemas/reservation.py

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ReservationCreateRequest(BaseModel):
    lab_id: int
    equipment_id: int | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_time(cls, value: str) -> str:
        try:
            # 接受 9:00 等输入，统一为 09:00 后再交给业务层。
            return datetime.strptime(value, "%H:%M").strftime("%H:%M")
        except ValueError:
            raise ValueError("时间格式应为 HH:MM, 例如 09:00") from None


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    lab_id: int
    lab_name: str | None = None
    equipment_id: int | None = None
    equipment_name: str | None = None
    type: str | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)


class AuditReservationRequest(BaseModel):
    status: int  # 1 or 2
```

#### 13.28.2 backend/app/services/reservation_service.py

```python
from datetime import datetime
from time import sleep
from sqlalchemy import func, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest, ReservationResponse


def get_reservation_page_list(
    db: Session,
    current_user: User,
    page: int,
    page_size: int,
    status: int | None = None,
):
    """查询预约记录"""
    query = db.query(Reservation)
    if current_user.role != "admin":
        query = query.filter(Reservation.user_id == current_user.id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    total = query.count()
    items = (
        query.order_by(Reservation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    result = []
    for item in items:
        res = ReservationResponse.model_validate(item)
        res.user_name = item.user.name if item.user else None
        res.lab_name = item.lab.name if item.lab else None
        res.equipment_name = item.equipment.name if item.equipment else None
        res.type = "设备" if item.equipment_id else "实验室"
        result.append(res)
    return PageResponse(list=result, total=total)


def create_reservation(db: Session, current_user: User, data: ReservationCreateRequest):
    for attempt in range(3):
        try:
            _create_reservation(db, current_user, data)
            return
        except OperationalError as exc:
            db.rollback()
            error_code = exc.orig.args[0] if exc.orig.args else None
            # InnoDB 死锁需要重试整个事务，每次仍重新持锁并检查冲突。
            if error_code == 1213 and attempt < 2:
                sleep(0.01 * (attempt + 1))
                continue
            if error_code in (1205, 1213):
                raise BusinessException(
                    message="预约资源正忙，请稍后重试", code=409
                ) from exc
            raise
        except Exception:
            # 包括业务校验失败在内，及时释放本次事务持有的资源锁。
            db.rollback()
            raise


def _create_reservation(
    db: Session, current_user: User, data: ReservationCreateRequest
):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.time().replace(second=0, microsecond=0)
    start_time = datetime.strptime(data.start_time, "%H:%M").time()
    end_time = datetime.strptime(data.end_time, "%H:%M").time()
    if data.date < current_date:
        raise BusinessException(message="预约日期不能小于当天的日期")
    if end_time < start_time:
        raise BusinessException(message="预约的结束时间不能小于预约的开始时间")
    if data.date == current_date and start_time < current_time:
        raise BusinessException(message="当天预约的开始时间不能小于当前的时间")
    # 先锁定稳定存在的实验室行，再检查冲突并提交，避免空时段无行可锁。
    # 无值变更的 UPDATE 在 MySQL/InnoDB 和 SQLite 中均能持有写锁；
    # 显式保留 update_time，避免预约操作修改实验室的更新时间。
    db.execute(
        update(Lab)
        .where(Lab.id == data.lab_id)
        .values(id=Lab.id, update_time=Lab.update_time)
        .execution_options(synchronize_session=False)
    )
    lab = (
        db.query(Lab)
        .filter(Lab.id == data.lab_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not lab:
        raise BusinessException(message="实验室不存在")
    if lab.status != 1:
        raise BusinessException(message="实验室已关闭")
    if lab.open_time and start_time < datetime.strptime(lab.open_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能早于实验室的开放时间")
    if lab.close_time and end_time > datetime.strptime(lab.close_time, "%H:%M").time():
        raise BusinessException(message="预约时间不能晚于实验室的关闭时间")

    # equipment_id 不为空 则表示这次是预约的实验室设备
    if data.equipment_id is not None:
        equipment = (
            db.query(Equipment)
            .filter(Equipment.id == data.equipment_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not equipment:
            raise BusinessException(message="实验室设备不存在")
        if equipment.lab_id != lab.id:
            raise BusinessException(message="该设备不属于所选实验室", code=400)
        if equipment.status != 1:
            raise BusinessException(message="实验室设备正在维修")

    # 实验室或者设备是否是可预约的状态
    query = db.query(Reservation).filter(
        Reservation.date == data.date,
        Reservation.status.in_([0, 1]),  # 0表示待审核 1已通过
        func.time(Reservation.start_time) < end_time.strftime("%H:%M:%S"),
        func.time(Reservation.end_time) > start_time.strftime("%H:%M:%S"),
    )
    if data.equipment_id is not None:
        query = query.filter(
            Reservation.equipment_id == data.equipment_id
        )  # 预约实验室设备
    else:
        query = query.filter(
            Reservation.lab_id == lab.id, Reservation.equipment_id.is_(None)
        )  # 只预约实验室
    # InnoDB 默认 REPEATABLE READ 下使用当前读，避免复用认证查询建立的旧快照。
    if query.with_for_update().first():
        raise BusinessException(message="该时段已预约", code=409)

    reservation_model = Reservation(
        user_id=current_user.id,
        lab_id=data.lab_id,
        equipment_id=data.equipment_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        remark=data.remark,
        status=0,
    )
    db.add(reservation_model)
    db.commit()


def cancel_reservation(db: Session, current_user: User, reservation_id: int):
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.user_id != current_user.id:
        raise BusinessException(message="无权限", code=403)
    if item.status != 0:
        raise BusinessException(message="当前状态无法取消")
    item.status = 3
    db.commit()


def audit_reservation(db: Session, reservation_id: int, status: int):
    """管理员审核预约"""
    if status not in [1, 2]:
        raise BusinessException(message="审核状态错误")
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != 0:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    db.commit()
```

#### 13.28.3 backend/app/api/reservation.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.reservation import AuditReservationRequest, ReservationCreateRequest
from app.services import reservation_service

router = APIRouter(prefix="/reservation", tags=["预约服务接口"])


@router.get("/list")
def get_reservation_page_list(
    page: int = 1,
    page_size: int = 10,
    status: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = reservation_service.get_reservation_page_list(
        db=db, current_user=current_user, page=page, page_size=page_size, status=status
    )
    return Response.success(data=res)


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.create_reservation(data=data, current_user=current_user, db=db)
    return Response.success()


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.cancel_reservation(
        reservation_id=reservation_id, current_user=current_user, db=db
    )
    return Response.success()


@router.put("/{reservation_id}/audit")
def audit_reservation(
    reservation_id: int,
    data: AuditReservationRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    reservation_service.audit_reservation(
        reservation_id=reservation_id,
        db=db,
        status=data.status,
    )
    return Response.success()
```

#### 13.28.4 frontend/src/api/reservation.js

```js
import request from "@/utils/request";

// 创建预约
export function createReservationApi(data) {
  return request({
    url: "/api/reservation",
    method: "post",
    data,
  });
}

// 查询预约记录
export function getReservationPageList(params) {
  return request({
    url: "/api/reservation/list",
    method: "get",
    params,
  });
}

// 取消预约
export function cancelReservationApi(id) {
  return request({
    url: `/api/reservation/${id}/cancel`,
    method: "put",
  });
}

// 审核预约
export function auditReservationApi(id, status) {
  return request({
    url: `/api/reservation/${id}/audit`,
    method: "put",
    data: { status },
  });
}
```

#### 13.28.5 frontend/src/views/MyReservation.vue

```vue
<template>
  <div style="width: 60%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>我的预约记录</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.status"
          placeholder=" 请选择状态"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
          @clear="handleSearch"
        >
          <el-option :value="0" label="待审核" />
          <el-option :value="1" label="已通过" />
          <el-option :value="2" label="已拒绝" />
          <el-option :value="3" label="已取消" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column label="预约类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === '实验室' ? 'success' : 'primary'">{{
              row.type
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="实验室" width="200" />
        <el-table-column label="设备" width="200">
          <template #default="{ row }">
            {{ row.equipment_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column label="预约时段" width="130">
          <template #default="{ row }"
            >{{ row.start_time }} - {{ row.end_time }}</template
          >
        </el-table-column>
        <el-table-column prop="remark" label="备注" />
        <el-table-column prop="status" label="预约状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 0"
              type="danger"
              text
              bg
              @click="handleCancel(row)"
              >取消</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import {
  cancelReservationApi,
  getReservationPageList,
} from "@/api/reservation";
import { ElMessage, ElMessageBox } from "element-plus";
const statusType = (status) => {
  return (
    { 0: "warning", 1: "success", 2: "danger", 3: "info" }[status] || "info"
  );
};

const statusText = (status) => {
  return { 0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已取消" }[status] || "-";
};
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const params = reactive({
  page: 1,
  pageSize: 10,
  status: null,
});

const load = async () => {
  try {
    const res = await getReservationPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const handleCancel = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认取消 [${row.lab_name}] 的预约?`,
      "确认取消",
      {
        type: "warning",
      },
    );
    const res = await cancelReservationApi(row.id);
    if (res.code === 200) {
      ElMessage.success("取消预约成功");
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};

const handleSearch = () => {
  params.page = 1;
  load();
};

onMounted(() => {
  load();
});
</script>
```

#### 13.28.6 frontend/src/views/AuditReservation.vue

```vue
<template>
  <div style="width: 60%">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>我的预约记录</span>
        </div>
      </template>
      <div style="margin-bottom: 10px">
        <el-select
          v-model="params.status"
          placeholder=" 请选择状态"
          clearable
          style="width: 200px; margin-right: 8px"
          @change="handleSearch"
          @clear="handleSearch"
        >
          <el-option :value="0" label="待审核" />
          <el-option :value="1" label="已通过" />
          <el-option :value="2" label="已拒绝" />
          <el-option :value="3" label="已取消" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleSearch"
          >查询</el-button
        >
      </div>
      <el-table
        :header-cell-style="{ backgroundColor: '#fdf', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column label="预约类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === '实验室' ? 'success' : 'primary'">{{
              row.type
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lab_name" label="实验室" width="200" />
        <el-table-column label="设备" width="200">
          <template #default="{ row }">
            {{ row.equipment_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column label="预约时段" width="130">
          <template #default="{ row }"
            >{{ row.start_time }} - {{ row.end_time }}</template
          >
        </el-table-column>
        <el-table-column prop="remark" label="备注" />
        <el-table-column prop="user_name" label="预约人" width="100" />
        <el-table-column prop="status" label="预约状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <template v-if="row.status === 0">
              <el-button type="success" text bg @click="handleAudit(row, 1)"
                >通过</el-button
              >
              <el-button type="danger" text bg @click="handleAudit(row, 2)"
                >拒绝</el-button
              >
            </template>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { auditReservationApi, getReservationPageList } from "@/api/reservation";
import { ElMessage, ElMessageBox } from "element-plus";
const statusType = (status) => {
  return (
    { 0: "warning", 1: "success", 2: "danger", 3: "info" }[status] || "info"
  );
};

const statusText = (status) => {
  return { 0: "待审核", 1: "已通过", 2: "已拒绝", 3: "已取消" }[status] || "-";
};
const loading = ref(false);
const tableData = ref([]);
const total = ref(0);
const params = reactive({
  page: 1,
  pageSize: 10,
  status: 0,
});

const load = async () => {
  try {
    const res = await getReservationPageList(params);
    if (res.code === 200) {
      tableData.value = res.data?.list;
      total.value = res.data?.total;
    }
  } finally {
    loading.value = false;
  }
};

const handleAudit = async (row, status) => {
  try {
    const action = status === 1 ? "通过" : "拒绝";
    await ElMessageBox.confirm(
      `确认 ${action} [${row.lab_name}] 的审核?`,
      "审核",
      {
        type: "warning",
      },
    );
    const res = await auditReservationApi(row.id, status);
    if (res.code === 200) {
      ElMessage.success(`审核${action}`);
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};

const handleSearch = () => {
  params.page = 1;
  load();
};

onMounted(() => {
  load();
});
</script>
```

#### 13.28.7 frontend/src/router/index.js

```js
import { getToken } from "@/utils/auth";
import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", redirect: "/manager/home" },
    {
      path: "/manager",
      name: "Layout",
      component: () => import("@/layouts/Layout.vue"),
      children: [
        {
          path: "home",
          name: "Home",
          component: () => import("@/views/Home.vue"),
        },
        {
          path: "lab",
          name: "Lab",
          component: () => import("@/views/Lab.vue"),
        },
        {
          path: "equipment",
          name: "Equipment",
          component: () => import("@/views/Equipment.vue"),
        },
        {
          path: "user",
          name: "User",
          component: () => import("@/views/User.vue"),
        },
        {
          path: "profile",
          name: "Profile",
          component: () => import("@/views/Profile.vue"),
        },
        {
          path: "password",
          name: "Password",
          component: () => import("@/views/Password.vue"),
        },
        {
          path: "lablist",
          name: "LabList",
          component: () => import("@/views/LabList.vue"),
        },
        {
          path: "labequipment",
          name: "LabEquipment",
          component: () => import("@/views/LabEquipment.vue"),
        },
        {
          path: "myreservation",
          name: "MyReservation",
          component: () => import("@/views/MyReservation.vue"),
        },
        {
          path: "auditreservation",
          name: "AuditReservation",
          component: () => import("@/views/AuditReservation.vue"),
        },
      ],
    },
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/Login.vue"),
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/Register.vue"),
    },
  ],
});

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken();
  if (to.path === "/login" || to.path === "/register") {
    return true;
  } else {
    return token ? true : "/login";
  }
});

export default router;
```

#### 13.28.8 frontend/src/layouts/Layout.vue

```vue
<template>
  <div>
    <el-container style="min-height: 100vh">
      <el-header
        style="
          display: flex;
          align-items: center;
          border-bottom: 1px solid #ddd;
          background-color: #fff;
        "
      >
        <div
          style="display: flex; align-items: center; font-size: 24px; font-weight: bold"
        >
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div
              style="display: flex; align-items: center; margin-right: 20px; cursor: pointer"
            >
              <img
                :src="userInfo?.avatar"
                alt=""
                style="width: 30px; border-radius: 50%"
              />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || "用户" }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-container>
        <el-aside width="220px">
          <el-menu router :default-active="route.path" style="height: 100%">
            <el-menu-item index="/manager/home">
              <el-icon><Menu /></el-icon>
              <span>系统首页</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/auditreservation"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><DocumentChecked /></el-icon>
              <span>预约审核管理</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/lab"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/equipment"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/user"
              v-if="userInfo?.role === 'admin'"
            >
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/lablist"
              v-if="userInfo?.role === 'student'"
            >
              <el-icon><House /></el-icon>
              <span>实验室列表</span>
            </el-menu-item>

            <el-menu-item
              index="/manager/myreservation"
              v-if="userInfo?.role === 'student'"
            >
              <el-icon><Tickets /></el-icon>
              <span>我的预约</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import {
  Menu,
  House,
  Setting,
  User,
  Tickets,
  DocumentChecked,
} from "@element-plus/icons-vue";
import { useRoute, useRouter } from "vue-router";
import { logout } from "@/utils/auth";
import { useUser } from "@/utils/user";
const router = useRouter();
const route = useRoute();
const { userInfo } = useUser();

const handleLogout = () => {
  logout();
  router.push("/login");
};

const goPerson = () => {
  router.push("/manager/profile");
};

const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/manager/profile");
  } else if (command === "password") {
    router.push("/manager/password");
  } else if (command === "logout") {
    logout();
    router.push("/login");
  }
};
</script>
```

#### 13.28.9 frontend/vite.config.js

```js
import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueDevTools from "vite-plugin-vue-devtools";

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000", //  /api -> http://127.0.0.1:8000/api
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8000", //  /uploads -> http://127.0.0.1:8000/uploads
        changeOrigin: true,
      },
    },
  },
});
```

<a id="expiry-thread-scan"></a>

### 13.29 当前扫描：to_thread 与取消收尾（2026-10-26）

第 13.17～13.18 节保留早期同步扫描的讲解与快照。本轮 run_expire_scan 将数据库扫描移入线程：

```python
async def run_expire_scan():
    """扫描执行业务"""
    try:
        while True:
            await asyncio.to_thread(expire_pending_reservations)
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        return
```

await asyncio.to_thread(expire_pending_reservations) 把同步数据库工作交给工作线程，避免直接阻塞同一事件循环中的 SSE 等异步任务；外层仍等待这一轮扫描完成，再 sleep(60)。因此扫描间隔仍是“扫描耗时 + 60 秒”，当前单个循环不会主动重叠启动两次扫描。

expire_pending_reservations 内部创建独立 Session，finally 关闭；这里没有把接口的 db 会话传给线程。过期判定和 status=0 → 3 的规则未变，审核/取消/扫描的竞争也没有因此自动解决。

新循环捕获 CancelledError 后 return，main.py 仍负责 task.cancel() 并 await。取消等待中的协程不等于强制停止已经开始的线程工作：扫描可能继续完成数据库操作，再执行自己的会话清理。当前没有额外等待线程工作结束的应用级机制，也没有针对普通扫描异常的日志重试，不能把这项改动表述为“后台任务所有失败与退出问题都修好了”。[Python 线程执行说明](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)

真实验收应同时观察长扫描期间的聊天事件到达、无数据/已过期记录、停服时正在执行的数据库操作，以及多进程部署是否重复扫描。当前仅核对源码，未对业务数据库运行扫描。

<a id="20-ai-rag"></a>

## 14. AI 对话、向量知识库与 RAG

阶段起点：2026-10-23。本章解释消息结构、向量知识库、检索、提示词和前端发送，并把对应错误复盘放在发生位置。代码快照保留加入工具前的基础 RAG 版本；2026-10-24 的数据库只读工具、最多 3 轮模型调用与 60 秒超时在下一章接续。

**2026-10-25 当前说明**：第 14.1～14.18 节是基础阶段，保留用于比较固定前置 RAG；第 14.19～14.20 节说明本地缓存与预热的当前实现。聊天由框架 Agent 按工具请求检索，并提供创建预约工具；框架基础见第 15.20 节之后，2026-10-26 当前 SSE 执行入口见第 15.42 节之后。

### 14.1 当前阶段实现了什么

项目已经具备聊天界面、登录后的聊天接口、历史消息传递、本地知识库检索及调用聊天模型的基础流程。这种“先检索资料，再让模型结合资料生成回答”的流程称为 RAG（检索增强生成）。

在本章记录的 2026-10-23 版本中，Python 固定执行检索和生成步骤，没有 tools 定义或工具循环。2026-10-24 已加入数据库资源资料查询，但仍没有时段空闲、可用库存计算及预约写入工具，见第 15 节。

后续实现智能体时，可以复用本章的消息结构、模型客户端、认证入口和前端，再增加可供模型调用的业务工具。一个“帮我预约”的回答文本本身不会创建数据库记录。

### 14.2 AI 与知识库的文件地图

| 文件                               | 负责什么                           | 怎样与下一层连接                                    |
| ---------------------------------- | ---------------------------------- | --------------------------------------------------- |
| frontend/src/router/index.js       | aichat 子路由                      | 加载 AIChat.vue，完整路径 /manager/aichat           |
| frontend/src/layouts/Layout.vue    | 学生菜单及 ChatDotRound 图标       | 菜单点击进入该路由                                  |
| frontend/src/views/AIChat.vue      | 消息、输入框、发送状态与渲染       | handleSend 调用 chatApi                             |
| frontend/src/api/ai.js             | POST /api/ai/chat，30 秒超时       | 复用 utils/request.js 的 Axios 实例                 |
| backend/app/api/**init**.py        | 合并 ai_router                     | /api 与 /ai、/chat 拼成完整地址                     |
| backend/app/schemas/ai.py          | ChatMessage、ChatRequest           | 校验 JSON 字段和嵌套消息列表                        |
| backend/app/api/ai.py              | 登录依赖、调用服务、包装响应       | ai_service.chat(data)                               |
| backend/app/services/ai_service.py | 整理历史、组装提示词、调用模型     | kb_service.search 与 client.chat.completions.create |
| backend/app/services/kb_service.py | 加载向量模型、集合初始化与检索筛选 | 读取 data/kb，持久化到 data/chroma                  |
| backend/app/config.py              | 三个 LLM 配置与 BASE_DIR           | 创建模型客户端、确定数据路径                        |

### 14.3 新配置与依赖：两种模型各做什么

当前 requirements.txt 新增 openai、chromadb、sentence-transformers；前端新增 marked、dompurify。安装以项目依赖文件为准。本章讨论的是当前项目所固定版本的用法。

```dotenv
LLM_API_KEY=YOUR_LLM_API_KEY
LLM_MODEL=YOUR_CHAT_MODEL_ID
LLM_BASE_URL=https://YOUR_PROVIDER_HOST/v1
```

将上述三个字段加入已有 backend/.env，保留 DATABASE_URL、JWT_SECRET_KEY 等旧字段。这里全是占位值。LLM_BASE_URL 是兼容聊天接口的基础地址，LLM_MODEL 必须是该服务支持的模型标识。config.py 中三个字段都是没有默认值的 str，Settings() 会在导入时校验它们是否存在。

| 模型         | 当前选择位置                            | 输入和输出                        |
| ------------ | --------------------------------------- | --------------------------------- |
| 文本向量模型 | kb_service.py 中 BAAI/bge-small-zh-v1.5 | 文档或问题 → 数值向量，用于检索   |
| 聊天模型     | settings.LLM_MODEL                      | system 与历史 messages → 回答文本 |

配置聊天 API 密钥不会替代向量模型的安装和下载。向量模型在本地执行，聊天客户端根据 LLM_BASE_URL 向所配置的服务发送请求。

### 14.4 启动和首次提问是两个时机

```text
启动后端
  → 导入 api 路由 → 导入 ai_service → 导入 kb_service
  → 创建模块级 _embedding_fn，加载/必要时下载 BGE 模型
  → 应用 lifespan 启动预约扫描

首次有效用户提问
  → ai_service.chat → kb_service.search → get_collection
  → 创建 data/chroma → 获取或创建 lab_kb
  → 集合为空时读取 Markdown 并向量化写入
  → 对问题向量化并检索 → 组装提示词 → 聊天模型
```

`BASE_DIR = Path(__file__).resolve().parent.parent` 在 config.py 中得到 backend 目录，因此数据位于 backend/data，不受从哪个工作目录启动的直接影响。

这里有两个不同的缓存：`_embedding_fn` 是模型对象，`_collection` 是集合对象。它们是进程内变量；Chroma 文件才负责跨进程保留数据。早期使用默认向量模型时日志出现过 all-MiniLM-L6-v2 的 ONNX 下载路径，那是历史阶段，当前源码显式使用 BGE。

模型版本边界：当前显式使用 BGE，向量集合必须匹配嵌入模型。早期默认 ONNX 模型的下载日志仅是历史记录，不能据此判断当前使用的模型。

### 14.5 请求体怎样变成 Python 对象

```python
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
```

前端提交示例：

```json
{ "messages": [{ "role": "user", "content": "实验室安全规范" }] }
```

FastAPI 把外层 JSON 校验成 ChatRequest，列表中的元素变成 ChatMessage，因此刚进入循环时能写 `message.role`。当前 role 是普通字符串，schema 没有限定 Literal 枚举；业务函数再筛掉非 user/assistant 的消息和空白内容。

api/ai.py 同时声明了 get_current_user 和 get_db。登录身份在依赖中校验，db 参数当前没有交给聊天服务，不能据此认为模型已经接入实时预约查询。学生菜单限制也不等于接口限制为学生；后端要求的是有效登录用户。

### 14.6 model_dump、reversed 和 next 怎样配合

当前核心代码：

```python
history = []
for message in data.messages:
    if message.role in ("user", "assistant") and message.content.strip():
        history.append(message.model_dump())

question = next(
    (item["content"] for item in reversed(history) if item["role"] == "user"), ""
)
```

逐步理解：

1. message 最初是 Pydantic 对象，可以用点号取属性。
2. model_dump() 把它转换成字典，history 保存的是转换后的结果。
3. reversed(history) 从后往前遍历，仍然取出字典，不会还原成对象。
4. 生成器只产生 user 消息的 content；next 取第一条，得到最近一次用户问题。
5. 没有匹配时使用默认值空字符串，避免 StopIteration。

```python
# history 中的一项
item = {"role": "user", "content": "实验室安全规范"}
question = item["content"]
```

`message.content.strip()` 当前只用于判空，存入 history 的仍是原始 content；它没有在后端把每条内容都替换成去空白后的值。若仅包含 assistant 消息，history 可以非空但 question 为空，此时跳过知识检索。这是当前实现的边界。

**错误复盘（2026-10-23）**

| 故障                       | 原因                 | 已保存的修补或定位方式        |
| -------------------------- | -------------------- | ----------------------------- |
| history 元素没有 role 属性 | model_dump 后是 dict | item["role"]、item["content"] |

### 14.7 get_collection：原文如何进入向量库

`global _collection` 表示函数要修改模块级缓存。已有集合对象时直接返回；首次调用才建立目录并使用 PersistentClient。

读取过程包含三个平行列表：

| 列表  | 一项的例子                | 用途                                     |
| ----- | ------------------------- | ---------------------------------------- |
| ids   | 安全规则                  | path.stem，作为文档标识                  |
| docs  | Markdown 文件的全文       | 文档正文，由 embedding_function 转成向量 |
| metas | {"source": "安全规则.md"} | 记录来源，返回时拼入提示词               |

`sorted(KB_DIR.glob("*.md"))` 只匹配当前目录的 Markdown；`read_text(encoding="UTF-8").strip()` 去掉首尾空白；空文档被跳过。每份非空文件整体作为一条文档，没有进一步切块。

```python
col.add(ids=ids, documents=docs, metadatas=metas)
```

这里没有显式传 embeddings，集合绑定的 `_embedding_fn` 会负责计算。`PersistentClient(path=str(CHROMA_DIR))` 将数据保存在指定目录，可以看到 chroma.sqlite3 和索引目录等文件；不需要为每篇 Markdown 找一个同名向量文件。

只有空集合才执行初始入库。已有 4 条记录后，修改安全规则.md、增加第 5 个文件或重启服务，都不会自动触发更新已有集合。后续可按文档 ID 和内容摘要实现 upsert/删除同步；切换向量模型则应创建新索引并重新嵌入原文。本章仅讲解现状和改进方向，没有执行数据重建。

维护索引时应同时核对原文、文档 ID 和嵌入模型；“文件已修改”与“检索已读到新内容”需要分别验证。

### 14.8 query 返回的嵌套列表为什么取 [0]

```python
limit = min(5, col.count())
res = col.query(query_texts=[query], n_results=limit)
docs = (res.get("documents") or [[]])[0]
metas = (res.get("metadatas") or [[]])[0]
distances = (res.get("distances") or [[]])[0]
```

query_texts 接收问题列表。本次只传一个问题，所以返回值的外层只有这一组结果；每组里面才是多个匹配文档。下面只用于解释结构：

```python
res = {
    "documents": [["安全文档正文", "预约文档正文"]],
    "metadatas": [[{"source": "安全规则.md"}, {"source": "预约规则.md"}]],
    "distances": [[0.2, 0.8]],
}
```

`[0]` 取第一个问题的整组结果。`or [[]]` 在字段为 None 或外层空列表时提供一组空结果，避免直接访问空外层的第零项。它并不自动修复所有异常结构，例如内层本身为 None 或元数据项为 None 的情况仍需另行处理。

### 14.9 zip、分数筛选、排序与取前两条

```python
score_parts = []
for doc, meta, dist in zip(docs, metas, distances):
    score = 1 / (1 + dist)
    if score < 0.5:
        continue
    name = meta.get("source") or ""
    score_parts.append({"score": score, "content": f"[{name}]\n{doc}"})
score_parts.sort(key=lambda x: x["score"], reverse=True)
final_parts = [item["content"] for item in score_parts[:2]]
return "\n\n".join(final_parts)
```

zip 每次把相同位置的文档、元数据、距离组成三个值，依次赋给 doc、meta、dist。若只写 zip(docs, metas)，每次只有两个值，三个变量接收时就会报 expected 3, got 2。zip 默认在最短列表结束时停止。

分数示例是演算值，不是实测结果：

| distance | 1 / (1 + distance) | 当前是否保留           |
| -------- | ------------------ | ---------------------- |
| 0.2      | 约 0.833           | 是                     |
| 0.8      | 约 0.556           | 是                     |
| 1.0      | 0.5                | 是，代码仅排除小于 0.5 |
| 1.2      | 约 0.455           | 否                     |

在非负距离下，该变换让距离越小分数越高。它不表示“模型有 83.3% 把握回答正确”，也不是统一标准的相似度。当前创建集合没有在业务代码中显式指定距离空间，具体含义要结合实际集合配置；不要在切换模型或度量后原样解释同一阈值。

`sort` 修改原列表，lambda 指定按 score 排序，reverse=True 表示从高到低。`[:2]` 取最多两项；`final_parts` 只保留字符串，才能传给 join。全部被过滤时返回空字符串，聊天服务仍会调用模型，只是不追加知识内容。

**错误复盘（2026-10-23）**

| 故障              | 原因                        | 已保存的修补或定位方式            |
| ----------------- | --------------------------- | --------------------------------- |
| expected 3, got 2 | zip 两个列表却解包三个变量  | zip(docs, metas, distances)       |
| join 遇到 dict    | 拼接了 score_parts 字典列表 | 提取 content 后 join(final_parts) |
| 检索仅返回首项    | return 曾缩进在循环内       | 循环结束后统一筛选和返回          |

相同报错再次出现时，先比对堆栈行与磁盘内容，再检查 IDE 未保存缓冲区、运行进程和加载路径。此前 zip 问题重复出现时，重新读取文件仍能看到两个参数；不能只凭“上一轮改过”认定当前文件正确。

### 14.10 提示词、消息展开与模型返回

```python
system_prompt = SYSTEM_PROMPT
knowledge = kb_service.search(query=question) if question else ""
if knowledge:
    system_prompt += "\n\n以下是检索到的实验室的资料: \n" + knowledge
```

每次请求先初始化局部 system_prompt，避免未赋值，也避免把前一次问题的资料不断积累到全局常量中。SYSTEM_PROMPT 规定回答范围，检索资料作为文本追加；检索本身没有改变模型参数。

```python
messages = [
    {"role": "system", "content": system_prompt},
    *history,
]
```

`*history` 把列表中的每条字典展开到新列表。如果直接写 history，则会多出一层嵌套列表。模型客户端使用配置好的 model 发起调用，代码通过 `res.choices[0].message.content` 读取回答，再由 API 包装成 ChatMessage 返回。

当前为同步、一次性响应，没有流式输出。知识检索和 get_client() 在 try 之前，它们抛出的非业务异常会进入全局 500 处理；模型调用部分的大部分异常被转换成“调用失败”。代码中空回答的 BusinessException 也会被同一个宽泛 except 捕获，所以实际提示会变成统一失败文案。定位错误应看完整堆栈和异常发生阶段，不要只看页面的 500。

**错误复盘（2026-10-23）**

| 故障                 | 原因                       | 已保存的修补或定位方式     |
| -------------------- | -------------------------- | -------------------------- |
| system_prompt 未赋值 | 局部变量在 += 前没有初始值 | 每次请求设置 SYSTEM_PROMPT |

### 14.11 前端发送流程：状态与 Promise

AIChat.vue 初始只有一条 assistant 欢迎语。handleSend 读取 `input.value.trim()`，空输入或正在发送就返回；随后把用户消息压入 messages，清空输入，设置 loading，再调用 chatApi。

```text
输入 → messages.push(user) → chatApi({messages: history})
     → Axios 附带 token → 后端
     → res.code === 200 → messages.push(res.data)
     → nextTick 后滚动到底部 → finally 清除 loading
```

Axios 拦截器会把 HTTP 响应的 body 返回给页面，因此页面拿到的 res 已是统一业务结构。业务错误和 HTTP 错误应分别判断：BusinessException 当前通常是 HTTP 200、body.code 非 200；未捕获异常则可能是 HTTP 500，并让 Promise 被拒绝。

页面 catch 结束失败请求的控制流，错误提示由拦截器负责；finally 无论成功失败都会复原按钮。失败时已加入的用户消息仍保留在历史中，没有自动恢复输入或创建失败气泡。`nextTick` 等 Vue 更新 DOM 后再读取滚动容器高度，否则新增气泡可能还没渲染。

**错误复盘（2026-10-23）**

| 故障                    | 原因                    | 已保存的修补或定位方式                                   |
| ----------------------- | ----------------------- | -------------------------------------------------------- |
| Vue 未处理 Promise 拒绝 | handleSend 只有 finally | catch 结束失败流程，统一拦截器提示；finally 清除 loading |

### 14.12 Markdown、v-html 与页面路由

`marked.parse(text)` 将 Markdown 转成 HTML，`DOMPurify.sanitize(rawHtml)` 清理后再交给 v-html。用户和助手消息都走同一渲染函数，因此用户输入 Markdown 标题时也会以标题字号显示。模板中的 Enter 发送、Shift+Enter 换行来自按键修饰符。

Layout 的 student 条件控制菜单显示，router 的 aichat 子路径控制页面加载。最终接口是否允许调用，由后端 get_current_user 决定。页面不持久化历史，也不会把用户自然语言转为预约表单提交。

### 14.13 知识内容必须与实际业务核对

当前四篇资料分别覆盖安全、开放时间、设备使用和预约规则。检索算法正确，并不保证资料内容正确。

| 当前知识文本                   | 当前代码行为                              | 需要处理的差异               |
| ------------------------------ | ----------------------------------------- | ---------------------------- |
| 预约规则写已通过也可本人取消   | cancel_reservation 只允许 status == 0     | 明确政策后修正文档或实现     |
| 设备使用写约设备同时占用实验室 | 创建预约分别查询设备冲突和整间实验室冲突  | 文档规则尚未落实为数据库校验 |
| 开放时间写死在 Markdown        | 实验室表也有可维护的 open_time/close_time | 两个来源没有同步机制         |

此处记录审查结果，未擅自调整业务政策或重建已有向量。即使修正原文，也要同步索引后才能让检索读取新规则。

### 14.14 从当前问答继续接入智能体

建议先为实时实验室查询提供明确的输入、输出模型，作为只读工具；再让模型按问题决定是否调用，并把工具结果加入消息继续生成回答。预约写入工具要复用已有身份、设备归属、时段冲突和事务保护。

工具参数应接受资源 ID、日期、时段等明确字段，用户身份来自服务端登录上下文。涉及预约、取消的操作需要让用户确认具体对象与时段，并处理工具失败和重复提交。这是当时的开发方向；第 15 节已实现只读工具定义与调用循环，预约写入及确认交互仍未实现。

### 14.15 从零复现与本章验收

实现顺序：配置和依赖 → schemas → 最小模型调用 → 登录聊天路由 → API 合并 → 前端 API/页面/菜单 → 知识原文 → 集合初始化 → 检索筛选 → 拼入提示词 → 异常与状态处理。

验收时分别观察：浏览器 Network 的请求体和响应、Uvicorn 的异常堆栈、实际检索资料、模型收到的消息。可在排序后、return 前临时添加：

```python
print("score_parts:", score_parts, flush=True)
```

先保存文件，再确认后端加载了新代码，然后发送问题。输出在后端终端；只启动应用不会自动执行 search，空集合提前 return 时也不会走到末尾打印。筛选后的空列表若执行到 print，仍会输出 []。当前保存的源码没有这条调试 print，示例需要自己加入后才会生效。

必须覆盖：最近一条 user 消息、空白输入、空集合、多个返回文档、全部低于阈值、真实接口失败及首次模型加载耗时。向量目录和四条记录只能证明某阶段的入库结果，不能替代当前模型配置下的检索及完整聊天验收。

**错误复盘（2026-10-23）**

| 故障           | 原因                               | 已保存的修补或定位方式                                     |
| -------------- | ---------------------------------- | ---------------------------------------------------------- |
| 看不到调试打印 | 保存文件中没有该语句，或未运行到它 | 保存、确认重载、发请求并查看后端终端；print 放在 return 前 |

<a id="ai-validation"></a>

### 14.16 AI 与检索的历史检查、真实联调范围

2026-10-23 文档更新逐文件核对了 AI schema/API/service、知识检索、前端发送、路由与菜单和模型配置。修补原因已在消息转换、检索排序、提示词与前端发送各节就地说明。

此前做过多轮 AI 检索和接口隔离验证，其中一轮 8 项，重复修补后另做 3 项。这些是历史临时检查，次数不能相加当成一个新测试套件，也不代表真实模型联调已完成。当次新增检查针对文档结构、链接和快照与源码的一致性，没有调用真实大模型或改动数据库。

仍需验收 BGE 与现有集合兼容性、中文检索阈值、聊天服务连通性和延迟、首次加载耗时、知识原文同步索引以及完整浏览器操作。前端超时在当时为 30 秒，2026-10-24 已改为 60 秒，当前工具调用的实际验收见第 15.17 节。

知识原文与业务规则先核对一致；只读工具与后续预约写入工具分别验证权限和行为，不能由聊天回答推定数据库操作已经完成。

### 14.17 复习练习

1. 分别画出导入模型、建立集合、查询向量、调用聊天模型四个时机。
2. 用两个 ChatMessage 演示 model_dump 前后取字段方式。
3. 用三个距离手算分数，并解释为什么最终只取两条。
4. 分别说明浏览器 HTTP 500 和 HTTP 200、body.code=500 的区别。
5. 修改一篇 Markdown 后，解释为何重启还可能读到旧内容。
6. 查找预约规则与 cancel_reservation 的差异，写出需要同步的文件和索引步骤。

### 14.18 本章阶段代码快照（2026-10-23）

以下快照从本次核对的工作区文件生成，日期为 2026-10-23；用于对照前面的讲解。旧章节快照保留历史，不要混合不同阶段的模型配置与消息处理方式。

#### backend/app/schemas/ai.py

```python
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
```

#### backend/app/api/ai.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI相关的api"])


@router.post("/chat")
def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = ai_service.chat(data=data)
    return Response.success(data=ChatMessage(role="assistant", content=content))
```

#### backend/app/services/ai_service.py

```python
from openai import OpenAI
from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import kb_service

SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答，不要编造资料里没有的时间、规则、设备。
你目前查不到真实的实验室空闲、设备库存、预约记录。
如果用户问现在/哪些实验室能约、某台设备此刻有没有空，请说明去「实验室列表」查看。
除了实验室相关的问题之外，不要回复无关的问题。
"""


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的APIKey")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat(data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    system_prompt = SYSTEM_PROMPT
    knowledge = kb_service.search(query=question) if question else ""
    if knowledge:
        system_prompt += "\n\n以下是检索到的实验室的资料: \n" + knowledge

    client = get_client()

    try:
        res = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                *history,
            ],
        )
        content = res.choices[0].message.content
        if not content:
            raise BusinessException(message="大模型没有返回内容")
        return content

    except Exception:
        raise BusinessException(message="大模型调用失败, 请稍后重试")
```

#### backend/app/services/kb_service.py

```python
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from app.config import BASE_DIR

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"

_collection = None
_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5"
)


def get_collection() -> Collection:
    """向量库的初始化"""
    global _collection
    if _collection is not None:
        return _collection
    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(
        name="lab_kb", embedding_function=_embedding_fn
    )
    if col.count() == 0:
        ids = []
        docs = []
        metas = []
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="UTF-8").strip()
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            col.add(ids=ids, documents=docs, metadatas=metas)
    _collection = col
    return _collection


def search(query: str):
    """根据关键字去检索向量库"""
    col = get_collection()
    if col.count() == 0:
        return ""
    limit = min(5, col.count())
    res = col.query(query_texts=[query], n_results=limit)
    docs = (res.get("documents") or [[]])[0]  # [list]
    metas = (res.get("metadatas") or [[]])[0]  # [list]
    distances = (res.get("distances") or [[]])[0]
    """
    以下是检索出来的资料:
    [预约规则.md]

    # 实验室预约规则...


    [安全规范.md]

    安全规范....
    """
    score_parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        # 0-1    越接近1表示越相关
        score = 1 / (1 + dist)
        if score < 0.5:
            continue
        name = meta.get("source") or ""
        score_parts.append({"score": score, "content": f"[{name}]\n{doc}"})
    score_parts.sort(key=lambda x: x["score"], reverse=True)
    final_parts = [item["content"] for item in score_parts[:2]]
    return "\n\n".join(final_parts)
```

#### frontend/src/api/ai.js

```javascript
import request from "@/utils/request";

export function chatApi(data) {
  return request({
    url: "/api/ai/chat",
    method: "post",
    data,
    timeout: 30000,
  });
}
```

#### frontend/src/views/AIChat.vue

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>AI智能助手</span>
        </div>
      </template>
      <div
        ref="listRef"
        style="
          height: 480px;
          overflow-y: auto;
          padding: 8px 4px;
          background-color: #fafafa;
          border-radius: 6px;
        "
      >
        <div
          v-for="(item, index) in messages"
          :key="index"
          :style="{
            display: 'flex',
            justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '12px',
          }"
        >
          <div
            :style="{
              maxWidth: '70%',
              padding: '10px 12px',
              borderRadius: '8px',
              backgroundColor: item.role === 'user' ? '#409eff' : '#fff',
              color: item.role === 'user' ? '#fff' : '#333',
              lineHeight: '1.6',
              boxShadow: '0 1px 2px rgba(0 ,0, 0, 0.06)',
            }"
            v-html="parseMarkdown(item.content)"
          ></div>
        </div>
      </div>
      <!-- 输入框 -->
      <div
        style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end"
      >
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="问问实验室怎么预约、开放时间..."
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.stop
        ></el-input>
        <el-button type="primary" :loading="loading" @click="handleSend"
          >发送</el-button
        >
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify"; // 过滤危险的 HTML，防止 XSS 攻击
import { chatApi } from "@/api/ai";

// 将 markdown 字符串转换为安全的 HTML 字符串
const parseMarkdown = (text) => {
  if (!text) return "";
  // 使用 marked 解析，然后用 DOMPurify 清理
  const rawHtml = marked.parse(text);
  return DOMPurify.sanitize(rawHtml);
};

const messages = ref([
  {
    role: "assistant",
    content:
      "您好，我是实验室助手。你可以向我提问怎么预约、取消实验室或者设备。具体实验室信息请到【实验室列表】页查看",
  },
]);

const input = ref("");
const loading = ref(false);
const listRef = ref();

const scrollToBottom = () => {
  nextTick(() => {
    const elem = listRef.value;
    if (elem) elem.scrollTop = elem.scrollHeight;
  });
};

const handleSend = async () => {
  const text = input.value.trim();
  if (!text || loading.value) return;
  messages.value.push({ role: "user", content: text });
  input.value = "";
  loading.value = true;
  scrollToBottom();
  try {
    const history = messages.value.filter(
      (item) => item.role === "user" || item.role === "assistant",
    );
    const res = await chatApi({ messages: history });
    if (res.code === 200) {
      messages.value.push(res.data);
      scrollToBottom();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false;
  }
};
</script>
```

<a id="kb-local-cache"></a>

### 14.19 当前知识库：本地模型缓存、延迟加载与预热（2026-10-25）

前面保留 2026-10-23 的基础 RAG 教程；本节说明当前 kb_service 的变化。BGE、Chroma、按文件入库与距离筛选仍然复用，模型准备时机和错误反馈有调整。

| 位置 | 当前写法 | 与早期版本的区别 |
| --- | --- | --- |
| 模块变量 | `_embedding_fn = None`，另有 EMBEDDING_MODEL_NAME | 导入模块不立即创建嵌入模型 |
| get_embedding_fn | 首次建立模型，之后复用进程内对象 | 实际加载延迟到调用点 |
| 模型构造 | `local_files_only=True` | 只读取已准备的本地缓存，不在应用加载中自动下载缺失文件 |
| 缓存加载异常 | 捕获 OSError，抛出 BusinessException(code=503) | 给出预先下载模型的操作说明；其他异常仍按上层路径处理 |
| get_collection | 绑定 get_embedding_fn()，空集合才初始化 | 未改变原文不会自动同步的边界 |
| warmup | 先 get_collection，集合非空再查询一次“预热” | 提前准备模型/集合及一次查询，不访问聊天模型 |

从 backend 目录，在可联网环境使用后端虚拟环境准备完整缓存：

```powershell
.\.venv\Scripts\python.exe -c "from huggingface_hub import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5')"
```

这个命令仅供准备环境，本次文档更新没有执行下载。向量模型缓存与 backend/data/chroma 是两个位置；有 Chroma 文件不代表 BGE 缓存完整，也不保证集合与当前模型匹配。

当前源码的预热默认开关是 True。若在 `.env` 中设 `KB_WARMUP_ON_STARTUP=false`，则跳过启动预热，由第一次实际 search_lab_docs 检索触发加载。设为 true 时，main.py 等待 warmup；失败记录日志并继续启动。环境配置可覆盖默认值，本文不读取或展示真实 `.env`。

warmup 不会刷新已经有数据的集合；改了 Markdown 仍需同步索引。预热异常与工具检索异常的呈现路径不同：前者由 main.py 记录日志，后者被 search_lab_docs 包装成工具错误结果交回模型。原知识规则与业务实现的冲突也仍需按第 14.13 节核对。

### 14.20 当前 kb_service.py 代码快照（2026-10-25）

这份完整快照用于当前框架版本。第 14.18 节继续保留早期模块级模型加载的快照；两份快照不要混用。新版 Agent 如何把 search 包装成工具，见第 15.30 节。

<details>
<summary><code>backend/app/services/kb_service.py</code>（2026-10-25）</summary>

```python
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions
from app.common.exceptions import BusinessException
from app.config import BASE_DIR

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"

_collection = None
_embedding_fn = None
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def get_embedding_fn():
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn
    try:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_NAME,
            local_files_only=True,
        )
    except OSError as exc:
        raise BusinessException(
            message=(
                "知识库向量模型的本地缓存缺失或不完整，请先在可访问 Hugging Face 的网络下，"
                "使用后端虚拟环境执行：python -c \"from huggingface_hub import "
                "snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5')\""
            ),
            code=503,
        ) from exc
    return _embedding_fn


def get_collection() -> Collection:
    """向量库的初始化"""
    global _collection
    if _collection is not None:
        return _collection
    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(
        name="lab_kb", embedding_function=get_embedding_fn()
    )
    if col.count() == 0:
        ids = []
        docs = []
        metas = []
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="UTF-8").strip()
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            col.add(ids=ids, documents=docs, metadatas=metas)
    _collection = col
    return _collection


def warmup():
    """启动的时候初始化向量库  启动预热"""
    col = get_collection()
    if col.count() > 0:
        col.query(query_texts=["预热"], n_results=1)


def search(query: str):
    """根据关键字去检索向量库"""
    col = get_collection()
    if col.count() == 0:
        return ""
    limit = min(5, col.count())
    res = col.query(query_texts=[query], n_results=limit)
    docs = (res.get("documents") or [[]])[0]  # [list]
    metas = (res.get("metadatas") or [[]])[0]  # [list]
    distances = (res.get("distances") or [[]])[0]
    """
    以下是检索出来的资料:
    [预约规则.md]

    # 实验室预约规则...


    [安全规范.md]

    安全规范....
    """
    score_parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        # 0-1    越接近1表示越相关
        score = 1 / (1 + dist)
        if score < 0.5:
            continue
        name = meta.get("source") or ""
        score_parts.append({"score": score, "content": f"[{name}]\n{doc}"})
    score_parts.sort(key=lambda x: x["score"], reverse=True)
    final_parts = [item["content"] for item in score_parts[:2]]
    return "\n\n".join(final_parts)
```

</details>

<a id="22-tool-calling"></a>

## 15. Agent 两种实现与 SSE：自定义工具循环、LangChain / LangGraph

本章按两种实现、三个阶段对照学习：第 15.1～15.19 节保留 2026-10-24 自定义 Tool Calling；第 15.20～15.41 节保留 2026-10-25 框架 JSON 方案；第 15.42～15.63 节讲当前框架 SSE 方案。当前注册的是 /chat/stream，旧 /chat 与 run_agent 已注释。示例名称、ID 和调用 ID 均为演示值。

阅读导航：[旧自定义执行路线](#22-tool-route) → [框架 JSON 阶段](#langchain-langgraph-agent) → [两种实现对照](#agent-framework-comparison) → [当前 SSE 完整调用链](#agent-sse) → [流式测试与验收](#sse-validation)。

**以下第 15.1～15.19 节描述旧方案。** 其中“当前”“两项只读工具”“最多 3 轮”“未提供预约写入”等表述均属于该阶段；原 data/tools/ai_config.py 现移至 data/config_global/ai_config.py，历史快照中的路径与内容继续保留。

### 15.1 工具调用的文件地图

| 文件                                | 本次改动                                      | 对运行流程的影响                             |
| ----------------------------------- | --------------------------------------------- | -------------------------------------------- |
| backend/data/tools/ai_config.py     | 新增 SYSTEM_PROMPT 与 TOOLS                   | 把提示词和工具描述集中到可导入的 Python 模块 |
| backend/app/services/ai_service.py  | 新增 run_tool；chat 接收 db；增加循环         | 解析工具请求，执行查询，再把结果交回模型     |
| backend/app/api/ai.py               | 调用改成 ai_service.chat(db=db, data=data)    | 把数据库会话真正传入 AI 业务层               |
| frontend/src/api/ai.js              | timeout 从 30000 改为 60000                   | 整个聊天 HTTP 请求最多等待 60 秒             |
| frontend/src/views/AIChat.vue       | 欢迎语增加资源信息查询说明                    | 界面告知能力；发送和展示主线沿用旧代码       |
| backend/app/services/lab_service.py | 删除一行空行                                  | 本轮没有改变实验室查询逻辑；工具复用既有函数 |
| .gitignore                          | backend/data/chroma 改为 backend/data/chroma/ | 明确忽略目录，不改变工具执行逻辑             |

equipment_service.py、schemas/ai.py、路由注册和 kb_service 是本次使用的既有代码，不是都新增或修改了。新增的 data/tools 属于源码，应随项目保存；data/chroma 是生成的索引目录，二者不能一起当成可丢弃缓存。

### 15.2 工具调用的本质：模型提出请求，应用执行函数

工具描述相当于交给模型的“可用功能说明书”，包含名称、用途和参数。模型分析问题后，可以返回结构化请求，例如：

```json
{
  "id": "call_labs_01",
  "type": "function",
  "function": {
    "name": "list_open_labs",
    "arguments": "{\"keywords\":\"物理\"}"
  }
}
```

含义是“请调用 list_open_labs，关键词是物理”。此时模型没有直接访问 MySQL。真正的读取发生在 run_tool 调用 lab_service 时。

整体过程是：提供工具说明 → 模型提出调用 → 应用执行函数 → 把结果发回模型 → 模型继续回答或继续提出调用。项目使用 Chat Completions 的 tool_calls / tool_call_id 格式，不要与其他 API 的消息结构混用。[OpenAI 官方 Function Calling 文档](https://developers.openai.com/api/docs/guides/function-calling)

工具 name 是一个约定的字符串。只有 run_tool 中有对应分支，它才会执行已编写的功能；向 TOOLS 随便添加一个名字，不会自动生成同名 Python 函数。

<a id="22-tool-route"></a>

### 15.3 实际路线：问“物理实验室有哪些设备”

下面是一条可能发生的路线。是否分两次查询由模型输出决定，后端没有针对这句中文写死规则。

```mermaid
sequenceDiagram
    actor U as 用户
    participant V as AIChat.vue
    participant API as 前端 api/ai.js
    participant B as 后端 api/ai.py
    participant A as ai_service.py
    participant K as kb_service.py
    participant L as 聊天模型
    participant S as lab_service / equipment_service
    participant DB as MySQL
    U->>V: 输入问题，点击发送或按 Enter
    V->>API: handleSend → chatApi({messages: history})
    API->>B: request.js → POST /api/ai/chat
    Note over B: ChatRequest、get_current_user、get_db
    B->>A: chat(db=db, data=data)
    A->>K: search(question)
    K-->>A: 静态资料或空字符串
    A->>L: 第 1 轮：system + history + TOOLS
    L-->>A: list_open_labs，keywords=物理
    A->>S: run_tool → get_lab_page_list(status=1)
    S->>DB: 查询启用实验室
    DB-->>S: 实验室记录，含 ID
    S-->>A: 分页结果 → 精简字段 → JSON 字符串
    A->>L: 第 2 轮：追加 assistant 调用和 tool 结果
    L-->>A: list_lab_equipments，lab_id=查到的 ID
    A->>S: run_tool → get_equipment_page_list(lab_id=...)
    S->>DB: 查询设备
    DB-->>S: 设备记录
    S-->>A: 精简字段 → JSON 字符串
    A->>L: 第 3 轮：再追加调用和结果
    L-->>A: 最终回答，无 tool_calls
    A-->>B: content 字符串
    B-->>V: Response.success(ChatMessage)，经请求拦截器返回
    V->>V: messages.push → Markdown 转换与清理 → 显示
```

逐个打开文件追踪：

1. [AIChat.vue](frontend/src/views/AIChat.vue)：发送按钮的 `@click="handleSend"`、回车事件和 handleSend。
2. [前端 ai.js](frontend/src/api/ai.js)：chatApi；继续经过 utils/request.js 的 token 与响应拦截器。
3. [后端 api/ai.py](backend/app/api/ai.py)：`@router.post("/chat")` 的 chat 函数。
4. [ai_service.py](backend/app/services/ai_service.py)：chat → kb_service.search → 模型请求 → run_tool。
5. [ai_config.py（现保留路径）](backend/data/config_global/ai_config.py)：SYSTEM_PROMPT 与 TOOLS，为模型请求提供配置。
6. [lab_service.py](backend/app/services/lab_service.py) 的 get_lab_page_list；[equipment_service.py](backend/app/services/equipment_service.py) 的 get_equipment_page_list。
7. 回到 chat：追加结果消息，下一轮请求模型，最后返回正文字符串。

浏览器通常只发一个 /api/ai/chat 请求，内部多次模型请求和数据库读取都发生在后端。run_tool 直接调用 Python service，不经过 api/lab.py、api/equipment.py，也不会跳转到 Lab.vue 或 Equipment.vue。

### 15.4 ai_config.py 与 app/config.py 不同

ai_service 顶部新增：

```python
from data.tools.ai_config import SYSTEM_PROMPT, TOOLS
```

SYSTEM_PROMPT 是字符串，说明助手用途、资料使用方式、资源查询要调用工具，以及预约应去实验室列表页面提交。TOOLS 是列表，里面的字典描述可调用函数。

ai_config.py 是普通 Python 源码；app/config.py 才是通过 Settings 读取数据库、JWT 和模型服务配置的模块。修改提示词不会替换 LLM_API_KEY，也不会自动修改知识原文。

从 backend 目录启动时，这个模块路径可以解析到 data/tools/ai_config.py；当前目录没有另外提供 **init**.py，使用命名空间包导入方式。kb_service 只扫描 data/kb/\*.md，不会把工具 Python 文件放进知识库。

提示词是对模型行为的要求，实际能力来自 run_tool 的分支。当前没有预约写入分支，所以模型写出“已经预约”的文字，也不会由此自动创建 reservation 记录。

### 15.5 TOOLS 描述了哪些内容

以设备工具为例，可以这样拆开阅读：

| 字段                     | 当前内容或作用             | 和代码的对应关系                           |
| ------------------------ | -------------------------- | ------------------------------------------ |
| type                     | function                   | 后续读取 function.name、function.arguments |
| function.name            | list_lab_equipments        | 与 run_tool 的名称判断匹配                 |
| description              | 查询某个实验室下的设备列表 | 帮助模型判断何时使用                       |
| parameters.type          | object                     | 希望 arguments 表示一个 JSON 对象          |
| properties.lab_id.type   | integer                    | 描述实验室 ID 类型                         |
| properties.keywords.type | string                     | 描述可选名称关键词                         |

parameters 使用 JSON Schema 形式描述输入，但当前没有 `required: ["lab_id"]`。参数出现在 properties 里，不等于已经声明它必填；缺参时目前依靠 run_tool 返回错误。

浏览器请求由 ChatRequest 校验；模型生成的 arguments 则由 json.loads 解析。这是两个输入边界。工具描述里的 integer 不代表本地已经拿到经过严格校验的正整数。

后续可以给每种工具增加专用参数模型，校验 ID 的正整数范围、关键词类型与长度、是否允许额外字段。这些是改进方向，本次只整理现有实现。

### 15.6 db 怎样从 API 一直传到查询函数

API 中改为：

```python
content = ai_service.chat(db=db, data=data)
return Response.success(data=ChatMessage(role="assistant", content=content))
```

db 来自 Depends(get_db)，是数据库 Session。它的传递路线为：

```text
database.py：get_db 产生 Session
  → api/ai.py：chat 的 db 参数
  → ai_service.py：chat(db, data)
  → run_tool(db, name, arguments)
  → lab_service / equipment_service
  → SQLAlchemy 查询 MySQL
```

模型端只收到消息、工具描述和精简后的查询结果，不会拿到 Session 对象或 DATABASE_URL。数据库会话不是可直接传送的聊天 JSON。

API 仍用 get_current_user 检查登录，但 current_user 没有传给 chat/run_tool。当前只读工具查询资源资料；将来查询“我的预约”或执行修改时，需要将服务端用户上下文传入并实施权限限制，不能让模型通过参数决定自己的身份。

### 15.7 工具循环之前仍然先执行 RAG

chat 前半段保留原有过程：

```text
检查 messages 非空
  → 保留 user/assistant 且 content 非空白的消息
  → model_dump 转为字典
  → reversed + next 找最新 user 问题
  → kb_service.search(question)
  → 把知识资料拼入 system_prompt
  → get_client() 创建模型客户端
  → messages = [{"role": "system", "content": system_prompt}, *history]
```

`*history` 在新列表中展开历史消息。浏览器提交的 system 或 tool 角色不会直接进入 history，system 由后端自己建立。

本次没有把知识检索改为可选工具。只要有用户问题，仍先执行 search，即使问题只需要数据库资料；知识库准备或检索失败可能阻止后续工具阶段。

RAG 提供静态规则与说明，数据库工具提供查询时读到的资源资料。两者更新时间和意义可能不同。工具接入不会自动修复 Markdown 中与业务代码矛盾的规则，也不会自动重建 Chroma。

### 15.8 模型响应怎样区分正文与工具调用

核心代码：

```python
res = client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
)
msg = res.choices[0].message
tool_calls = msg.tool_calls or []
```

res 是 SDK 响应对象；choices[0] 取第一个候选，message 是本轮模型消息。它可能包含最终正文，也可能主要包含工具请求。

`msg.tool_calls or []` 在没有调用时提供空列表，便于后续判断和遍历。auto 允许模型不调用、调用一个或多个工具；提示词虽然要求资源查询必须调用，当前程序没有再检查它是否遵守。[OpenAI 工具选择说明](https://developers.openai.com/api/docs/guides/function-calling#tool-choice)

没有 tool_calls 时，代码检查 content 非空且非纯空白，然后直接返回。有 tool_calls 时，即使同时有 content，也先处理工具请求，不把中间文字立即返回页面。

### 15.9 run_tool 的 JSON 解析与基础语法

函数签名表示接收会话、名称和参数字符串，返回字符串：

```python
def run_tool(db: Session, name: str, arguments: str) -> str:
    ...
```

arguments 可能是 `'{"lab_id":8}'`，先要解析成字典，才能用 args.get：

```python
try:
    args = json.loads(arguments or "{}")
except json.JSONDecodeError:
    return json.dumps({"error": "参数不是合法的json"}, ensure_ascii=False)

if not isinstance(args, dict):
    return json.dumps({"error": "参数必须是JSON对象"}, ensure_ascii=False)
```

json.loads 把 JSON 文本变成 Python 对象；json.dumps 把 Python 对象变回 JSON 文本。arguments or "{}" 在参数为空字符串等假值时使用空对象文本。JSONDecodeError 表示语法不合法，isinstance 则检查解析结果是否为字典：合法 JSON 也可能是列表、数字或 null。

ensure_ascii=False 让中文以可读字符保留，它不负责参数类型或权限校验。`-> str` 是返回类型注解，不会把任意对象自动变成字符串。

当前只检查了第一层对象形状，例如 `{"keywords":123}` 可以解析成字典，但整数没有字符串的 strip 方法；它会在执行阶段被捕获成工具错误。

### 15.10 分发到两个已有 service

**实验室工具。** 名称匹配 list_open_labs 后：

```python
keywords = (args.get("keywords") or "").strip() or None
page = lab_service.get_lab_page_list(
    db, page=1, page_size=10, keywords=keywords, status=1
)
```

keywords 缺省或空白时得到 None，否则去掉首尾空格。get_lab_page_list 用 Lab 查询 labs 表，按名称和启用状态筛选、统计、分页。

这里传 status=1，只表示“启用”。没有按当前时钟、指定日期、时段或已有预约计算空闲。返回开放时间字段也不等于已经判断“现在处于开放时段”。

page 是 PageResponse 模型，page.list 是这一页资源，page.total 是符合条件的总数。工具用列表推导式为每条记录建立精简字典，仅保留 id、name、location、capacity、open_time、close_time，然后返回：

```python
return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)
```

**设备工具。** 名称匹配 list_lab_equipments 后：

```python
lab_id = args.get("lab_id")
if not lab_id:
    return json.dumps({"error": "参数缺少实验室的 lab_id"}, ensure_ascii=False)
keywords = (args.get("keywords") or "").strip() or None
page = equipment_service.get_equipment_page_list(
    db, page=1, page_size=10, keywords=keywords, lab_id=int(lab_id)
)
```

int(lab_id) 尝试转换整数，但不是严格正整数校验：负数不会因此被拒绝，某些其他数字类型也可能被转换。if not lab_id 主要拦住缺省和部分假值。

equipment_service 查询 equipments，再从关联实验室补充 lab_name。工具保留 id、lab_id、lab_name、name、spec、quantity、status，外层结果字段叫 equipments。

当前设备工具没有检查目标实验室是否启用，没有过滤维修设备；不存在的实验室 ID 通常得到空设备列表，而不是先验证实验室后报不存在。quantity 是设备资料中的数量，不是扣除预约后的可用库存。

两个工具都固定第一页、每页 10 条。total 可以大于结果数组长度；模型当前无法通过工具参数继续翻页。回答应区分“查询到的前 10 条”和“全部资源”。

### 15.11 assistant 调用消息与 tool 结果为什么要配对

chat 先把本轮 assistant 消息加入 messages，保留 tool_calls 的 id、name、arguments；再执行：

```python
for call in tool_calls:
    result = run_tool(db, call.function.name, call.function.arguments)
    messages.append(
        {"role": "tool", "content": result, "tool_call_id": call.id}
    )
```

assistant 消息记录“模型要求做什么”，tool 消息记录“应用执行后得到什么”。tool_call_id 对应本次调用的 id，不是实验室 ID 或用户 ID。

下一轮模型收到的新增消息示意：

```json
[
  {
    "role": "assistant",
    "content": "",
    "tool_calls": [
      {
        "id": "call_labs_01",
        "type": "function",
        "function": {
          "name": "list_open_labs",
          "arguments": "{\"keywords\":\"物理\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_labs_01",
    "content": "{\"total\":1,\"labs\":[{\"id\":8,\"name\":\"物理实验室\"}]}"
  }
]
```

arguments 和 tool.content 本身都是字符串，所以在外层 JSON 中需要转义引号。模型可以根据结果中的实验室 ID 8，再提出设备查询。

普通 for 循环意味着本地逐个执行，而不是启动并行任务。每个调用都有对应结果；一个工具返回 error 时，当前实现仍继续处理同轮其他调用，再把这些结果一起交回模型。

### 15.12 三轮模型调用不是三个工具

外层 `for _ in range(3)` 最多执行三次循环体。range(3) 产生 0、1、2；这里用 `_` 表示不使用编号。每轮调用一次 create，因此限制的是代码层面的模型调用轮数。

| 情况               | 第 1 轮    | 第 2 轮          | 第 3 轮      | 当前结果                                     |
| ------------------ | ---------- | ---------------- | ------------ | -------------------------------------------- |
| 普通回答           | 正文       | 不执行           | 不执行       | 成功                                         |
| 一次查询           | 工具请求   | 正文             | 不执行       | 成功                                         |
| 先查实验室再查设备 | 实验室工具 | 设备工具         | 正文         | 成功                                         |
| 持续要求查询       | 工具请求   | 工具请求         | 仍是工具请求 | 第三轮工具也执行，但没有第四轮汇总，随后失败 |
| 单轮多工具         | 多个调用   | 可回答或继续调用 | 视情况执行   | 工具总数可以超过三次                         |

后续可分别定义模型轮数、工具总次数和整体耗时，或预留最终汇总机会。当前源码没有这样分开预算。SDK 的网络重试又是另一层机制，不应把三轮理解成底层绝对只尝试三次 HTTP。

### 15.13 后端 messages 与前端历史的区别

前端 messages 是 Vue ref，保存欢迎语、用户问题和最终回答。后端 messages 是本次 chat 内的临时列表，还包含 system、assistant.tool_calls 与 tool 结果。

后端只返回最终 content，没有返回内部完整轨迹。因此工具执行过程不会显示成独立卡片；下一次提问会重新建立后端消息列表，上一次的工具原始结果不会自动以 tool 消息保留。最终文字可能提到资源 ID，但这不等于保存了完整执行记录。刷新页面仍会丢失内存聊天历史，本次没有新增聊天表。

工具结果会发给所配置的模型服务，这也是模型能按数据库资料回答的原因。当前通过字段白名单精简 rows；数据库会话、连接配置和用户密码不在这些正常返回字段中。

### 15.14 前端只改两处，为什么能显示新的查询答案

AIChat.vue 仍沿用：

```text
handleSend：trim 输入，检查空值与 loading
  → 加入 user 消息，清空输入，开启 loading
  → chatApi({ messages: history })
  → 成功时 messages.value.push(res.data)
  → marked.parse → DOMPurify.sanitize → v-html
  → scrollToBottom；finally 恢复 loading
```

请求与最终响应形状没有改变：

```json
{ "messages": [{ "role": "user", "content": "有哪些启用实验室？" }] }
```

```json
{
  "code": 200,
  "message": "请求成功",
  "data": { "role": "assistant", "content": "根据工具查询结果整理的回答……" }
}
```

工具循环放在后端内部，前端继续显示一条最终文本即可。欢迎语说明能力，真正建立能力的是 db 传递、工具声明、分发和回传循环。

ai.js 的 timeout=60000 覆盖公共 request 的 30000 默认值，只影响这个聊天请求。它覆盖检索、查询、多轮模型处理和网络耗时，不是每轮各有一分钟。当前仍是一次性响应，没有流式进度或后端联动取消；浏览器超时不保证后端工作立即停止。

### 15.15 工具错误与聊天错误怎样返回

run_tool 的参数解析失败、缺参、未知名称或执行异常通常被转换为 JSON error 字符串，放进 role=tool 交给模型。模型可以解释失败或请求补充信息。它不是直接向浏览器发送 Response.error，整个聊天也未必因此失败。

chat 循环内另有空回答和轮次耗尽检查，但它们抛出的 BusinessException 也会被外层捕获。下面省略 try 内的循环，仅展示异常包装结构：

```python
try:
    ...
except Exception as exc:
    raise BusinessException(message="大模型调用失败, 请稍后重试") from exc
```

BusinessException 继承 Exception，所以“模型没有返回内容”“工具调用次数已达上限”的具体提示最终被统一提示替代。`from exc` 保留异常因果链，方便追踪原因，不会让页面自动显示原来的 message。

history 校验、kb_service.search、get_client 位于这段 try 之前，它们的异常不能都归为这条包装分支。例如未提供 API Key 时，get_client 抛出的业务错误直接向外传播。

run_tool 的宽泛捕获会把 str(exc) 放进模型消息，可能带入数据库驱动或内部执行细节。后续应区分可展示业务错误与内部诊断；如果 SQL 失败使会话需要回滚，仅捕获并返回文本也不等于恢复数据库会话。本轮没有改写业务错误处理，以上均为当前边界说明。

### 15.16 已实现能力与待完善边界

| 当前事实                   | 正确理解                         | 后续方向                               |
| -------------------------- | -------------------------------- | -------------------------------------- |
| list_open_labs 传 status=1 | 查询启用资源资料                 | 时段空闲还需日期、开放时间和冲突查询   |
| 返回 quantity、status      | 数量与状态是设备资料             | 可用数量计算、维修设备筛选需明确规则   |
| 提示词要求资源查询用工具   | 这是给模型的要求                 | auto 模式尚无强制使用后的核对          |
| 只允许两个名称分支         | 当前只有两种只读能力             | 新工具需同步声明、分发、参数和权限     |
| API 验证登录               | 保护聊天入口                     | 私人数据和写操作需在工具层使用当前用户 |
| 每次最多 10 条             | 固定第一页                       | 分页、结果上限和截断说明               |
| 单轮可以多个请求           | 批量提出调用                     | 本地仍顺序执行                         |
| RAG 与工具共存             | 静态规则和数据库资料一起辅助回答 | 处理来源冲突、索引更新、依据说明       |

参数由模型生成，工具结果由应用查询，最终文字又由模型生成；三个环节不能互相替代校验。查到“启用”不代表最终文字中的“现在可预约”就成立。当前也没有创建、取消、审核预约的 AI 工具。

### 15.17 从零编写和真实验收顺序

在第 14 节的聊天与知识检索基础上：

1. 确定只读查询范围和返回字段，选择已有的两个分页 service。
2. 新建 ai_config.py，写提示词和工具描述，确保名称与分发条件一致。
3. 写 run_tool，先解析与校验参数，再调用 service，整理字段并返回 JSON 字符串。
4. 改 chat 参数和 API 调用，让 db 沿函数参数传到工具执行层。
5. 模型请求加入 tools、tool_choice，区分直接正文和工具请求。
6. 保留 assistant 调用消息，逐个执行，再追加配对的 tool 结果并继续请求模型。
7. 明确预算和错误分支，测试缺参、失败和轮次耗尽，避免把统一错误掩盖理解成问题已处理好。
8. 保持前端最终响应协议，调整欢迎语与超时，确认 loading 和失败提示。
9. 先用模拟模型固定触发分支，再用学习数据库与实际模型服务联调，最后在独立环境复现。

以下真实联调清单尚未在本轮浏览器中执行：

| 问题或条件                           | 要观察什么                                             |
| ------------------------------------ | ------------------------------------------------------ |
| “有哪些启用实验室？”                 | 是否真调实验室工具、停用记录是否排除、是否误称时段空闲 |
| “物理实验室有哪些设备？”             | 是否取得正确 ID 再查询，结果与 tool_call_id 是否配对   |
| 直接提供已知实验室 ID                | 能否直接查设备，返回资源是否对应                       |
| 无匹配或无设备                       | 是否如实报告空结果，不编造                             |
| 名称对应多个实验室                   | 是否澄清或列选项，不任意认定对象                       |
| 结果超过 10 条                       | 是否区分 total 和这一页结果                            |
| 维修设备、停用实验室                 | 两个工具各自实际过滤范围是否清楚                       |
| “明天九点是否空闲？”                 | 不把资料查询当作时段冲突计算                           |
| “替我预约/取消/审核”                 | 当前无工具，不应声称已经完成写入                       |
| 无效 JSON、缺 ID、错误类型、未知名称 | 可用模拟输出固定触发，检查 error 回传                  |
| 三轮都要求工具                       | 验证第三轮执行后的耗尽与最终统一错误                   |
| 模型不支持 tools、缓慢或失败         | 后端异常与前端等待/恢复行为                            |
| 退出后再请求                         | 后端身份检查拒绝；不能只凭菜单判断                     |

### 15.18 本轮验证范围与复习问题

2026-10-24，提取实际 ai_service.py 函数，把模型客户端、kb_service 和查询 service 替换为模拟对象，完成 **30 个断言**。覆盖 JSON 解析与对象形状、未知工具、缺少/错误 ID、关键词清理与类型、固定分页和 status 参数、直接回答、角色过滤、知识拼接、先查实验室再查设备、单轮多工具、消息 ID 配对、轮次耗尽、空回答和模型异常包装。

检查通过说明指定分支符合源码表现，包括确认若干待完善行为，不代表这些问题已经修复。没有调用真实模型、访问现有 MySQL 或初始化/重建 Chroma；临时检查没有保存为仓库测试文件。前端 npm.cmd run build 通过，仍有包体积提示。文档片段与快照另作静态核对，真实模型选择、中文检索、数据库结果及完整页面交互仍需按上节验收。

复习问题：

1. 为什么 TOOLS 有名称，还需要 run_tool 的对应分支？
2. arguments、args、result 分别是什么类型？loads 和 dumps 的方向有何不同？
3. lab_id 和 tool_call_id 分别关联什么？
4. 一次浏览器提问为什么可能调用三轮模型？
5. 第三轮工具成功执行，为什么聊天仍可能失败？
6. db 和 current_user 分别传到哪一层？未来“我的预约”工具还需补什么？
7. 为什么显示了资源资料，仍不能认定支持空闲查询或自动预约？

### 15.19 本章阶段代码快照（2026-10-24）

以下保存本轮核心文件原样内容，包含上文已说明的待完善点。第 14.18 节保留加入工具之前的快照；复现当前版本应以本章 AI 配置、服务和接口组合为准。lab_service 的空行变化和 .gitignore 的目录写法已在第 15.1 节说明，不重复收录整份文件。

#### 15.19.1 backend/data/tools/ai_config.py

```python
SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答规则、安全、文档里的开放时间说明。
查询当前有哪些开放实验室、某实验室有哪些设备时，必须调用工具，不要编造。
你不能替用户提交预约，也不能直接改数据库。
如果用户要预约，请说明去「实验室列表」选择后提交，等待管理员审核。
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_labs",
            "description": "查询当前开放中的实验室列表，可以按名称关键字来筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "实验室的名称关键字，可以为空",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lab_equipments",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {
                        "type": "integer",
                        "description": "实验室 ID",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "设备名称的关键字，可以为空",
                    },
                },
            },
        },
    },
]
```

#### 15.19.2 backend/app/schemas/ai.py

```python
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
```

#### 15.19.3 backend/app/api/ai.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["AI相关的api"])


@router.post("/chat")
def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = ai_service.chat(db=db, data=data)
    return Response.success(data=ChatMessage(role="assistant", content=content))
```

#### 15.19.4 backend/app/services/ai_service.py

```python
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import equipment_service, kb_service, lab_service
from data.tools.ai_config import SYSTEM_PROMPT, TOOLS


def run_tool(db: Session, name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "参数不是合法的json"}, ensure_ascii=False)

    if not isinstance(args, dict):
        return json.dumps({"error": "参数必须是JSON对象"}, ensure_ascii=False)

    try:
        if name == "list_open_labs":
            keywords = (args.get("keywords") or "").strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)

        if name == "list_lab_equipments":
            lab_id = args.get("lab_id")
            if not lab_id:
                return json.dumps(
                    {"error": "参数缺少实验室的 lab_id"}, ensure_ascii=False
                )
            keywords = (args.get("keywords") or "").strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, keywords=keywords, lab_id=int(lab_id)
            )
            rows = [
                {
                    "id": item.id,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "name": item.name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return json.dumps(
                {"total": page.total, "equipments": rows}, ensure_ascii=False
            )

        return json.dumps({"error": f"未找到对应的tool: {name}"}, ensure_ascii=False)

    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def get_client() -> OpenAI:
    """创建OPENAI的客户端"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的APIKey")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat(db: Session, data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    # 取出用户最新的一条提问内容
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    system_prompt = SYSTEM_PROMPT
    knowledge = kb_service.search(query=question) if question else ""
    if knowledge:
        system_prompt += "\n\n以下是检索到的实验室的资料: \n" + knowledge

    client = get_client()
    messages = [{"role": "system", "content": system_prompt}, *history]

    try:
        for _ in range(3):
            res = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = res.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:  # 若没有tool调用, 则直接返回大模型的输出结果内容
                content = msg.content
                if not content or not content.strip():
                    raise BusinessException(message="大模型没有返回内容")
                return content
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            for call in tool_calls:
                result = run_tool(db, call.function.name, call.function.arguments)
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": call.id}
                )

        raise BusinessException(message="工具调用次数已达上限，请缩小查询范围后重试")
    except Exception as exc:
        raise BusinessException(message="大模型调用失败, 请稍后重试") from exc
```

#### 15.19.5 frontend/src/api/ai.js

```js
import request from "@/utils/request";

export function chatApi(data) {
  return request({
    url: "/api/ai/chat",
    method: "post",
    data,
    timeout: 60000,
  });
}
```

#### 15.19.6 frontend/src/views/AIChat.vue

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>AI智能助手</span>
        </div>
      </template>
      <div
        ref="listRef"
        style="
          height: 480px;
          overflow-y: auto;
          padding: 8px 4px;
          background-color: #fafafa;
          border-radius: 6px;
        "
      >
        <div
          v-for="(item, index) in messages"
          :key="index"
          :style="{
            display: 'flex',
            justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '12px',
          }"
        >
          <div
            :style="{
              maxWidth: '70%',
              padding: '10px 12px',
              borderRadius: '8px',
              backgroundColor: item.role === 'user' ? '#409eff' : '#fff',
              color: item.role === 'user' ? '#fff' : '#333',
              lineHeight: '1.6',
              boxShadow: '0 1px 2px rgba(0 ,0, 0, 0.06)',
            }"
            v-html="parseMarkdown(item.content)"
          ></div>
        </div>
      </div>
      <!-- 输入框 -->
      <div
        style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end"
      >
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="问问实验室怎么预约、开放时间..."
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.stop
        ></el-input>
        <el-button type="primary" :loading="loading" @click="handleSend"
          >发送</el-button
        >
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify"; // 过滤危险的 HTML，防止 XSS 攻击
import { chatApi } from "@/api/ai";

// 将 markdown 字符串转换为安全的 HTML 字符串
const parseMarkdown = (text) => {
  if (!text) return "";
  // 使用 marked 解析，然后用 DOMPurify 清理
  const rawHtml = marked.parse(text);
  return DOMPurify.sanitize(rawHtml);
};

const messages = ref([
  {
    role: "assistant",
    content:
      "您好, 我是实验室助手。你可以向我提问怎么预约、取消实验室或者设备, 也可以问我现在系统所存在的实验室与设备的具体信息。",
  },
]);

const input = ref("");
const loading = ref(false);
const listRef = ref();

const scrollToBottom = () => {
  nextTick(() => {
    const elem = listRef.value;
    if (elem) elem.scrollTop = elem.scrollHeight;
  });
};

const handleSend = async () => {
  const text = input.value.trim();
  if (!text || loading.value) return;
  messages.value.push({ role: "user", content: text });
  input.value = "";
  loading.value = true;
  scrollToBottom();
  try {
    const history = messages.value.filter(
      (item) => item.role === "user" || item.role === "assistant",
    );
    const res = await chatApi({ messages: history });
    if (res.code === 200) {
      messages.value.push(res.data);
      scrollToBottom();
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false;
  }
};
</script>
```

<a id="langchain-langgraph-agent"></a>

### 15.20 两套实现怎样并存：保留旧代码，明确当前入口

第 15.20～15.41 节按 2026-10-25 工作区讲解框架 JSON 版本，保留正文和快照用于对比。下面的“当前 /chat”“60 秒”“串行工具”“最终内容校验”等结论限于该阶段；2026-10-26 实际 SSE 入口及变化见[第 15.42 节起](#agent-sse)。先区分“文件仍在”“模块仍被导入”和“接口实际调用了哪个函数”。

| 层次 | 保留的自定义实现 | 当前框架实现 |
| --- | --- | --- |
| 调度服务 | `backend/app/services/ai_service.py`，手写 chat/run_tool | `backend/app/services/agent_service.py`，build_agent/run_agent |
| 工具配置 | `backend/data/config_global/ai_config.py`，SYSTEM_PROMPT/TOOLS | `backend/data/config_global/agent_config.py`，SYSTEM_PROMPT/build_tools |
| API 调用 | `ai_service.chat(db=db, data=data)`，旧路由函数已注释 | `agent_service.run_agent(db=db, current_user=current_user, data=data)` |
| 消息与执行循环 | 字典、JSON 参数、for 循环和手工追加工具消息 | LangChain 消息对象、工具对象与 LangGraph 图执行 |
| 当前工具能力 | 两项只读资源查询；进入循环前固定检索知识 | 五个工具；按模型工具请求检索、查询资源、获取日期和创建预约 |

旧版 `ai_config.py` 从 `data/tools` 移到了 `data/config_global`；`ai_service.py` 的 import 已相应改变。第 15.19 节保存的 `backend/data/tools/ai_config.py` 是 2026-10-24 的路径，不表示今天应再建一份同名目录。复习旧版时，讲解与代码快照继续有效，定位现有文件用新路径。

当前 `api/ai.py` 仍导入 `ai_service`，但正在注册的 `/chat` 函数调用 `agent_service`。因此旧模块可能参与 Python 导入，旧 chat/run_tool 并不处理当前 HTTP 聊天请求。代码没有根据提问自动选择两套 Agent，也没有提供运行时切换开关。

建议按第 15.1～15.19 节理解协议细节，再读本节之后的框架实现，最后看[逐项对照](#agent-framework-comparison)。旧实现有意保留，便于看清哪些工作交给框架、哪些业务仍由项目负责。

### 15.21 LangChain 与 LangGraph 分别负责什么

本次 requirements.txt 新增：

```text
langgraph==1.2.11
langchain-openai==1.6.2
langchain-core==1.6.3
```

| 本项目使用的组件 | 来自哪里 | 在项目中的职责 |
| --- | --- | --- |
| ChatOpenAI | langchain_openai | 读取聊天服务配置，调用兼容接口，返回 AIMessage |
| SystemMessage/HumanMessage/AIMessage | langchain_core.messages | 表达系统指令、用户输入和助手消息 |
| @tool | langchain_core.tools | 把带类型标注的函数包装为可描述、可调用的工具 |
| MessagesState/StateGraph/START | langgraph.graph | 定义消息状态与节点执行关系 |
| ToolNode/tools_condition | langgraph.prebuilt | 执行工具、生成工具结果消息，并决定是否继续工具路径 |

LangChain 在这里提供模型、消息与工具抽象；LangGraph 负责把“调用模型 → 执行工具 → 再调用模型”组织成图。项目直接使用 StateGraph，没有调用高层 `create_agent()`，也没有新增一个名为 `langchain` 的直接依赖行。安装以当前 requirements.txt 为准，传递依赖交给包管理器处理。

改成框架后，FastAPI、SQLAlchemy、Pydantic、业务 service、Chroma 和前端仍在原来的位置。框架不会替项目决定谁能预约、哪些时段冲突、写入成功后是什么状态。

### 15.22 从网页输入到图执行：先看完整路线

当前前端仍发送同一个 `/api/ai/chat` 请求，返回值也仍是统一 Response 包裹的 ChatMessage。

```mermaid
flowchart TD
    V["AIChat.vue → chatApi"] --> API["POST /api/ai/chat：取得 current_user 和 db"]
    API --> RUN["run_agent：过滤历史，构造消息对象"]
    RUN --> BUILD["build_tools + ChatOpenAI.bind_tools + compile"]
    BUILD --> START["START：SystemMessage + history"]
    START --> A["agent：model.invoke"]
    A --> C{"tools_condition：末条消息有工具调用？"}
    C -->|有| T["tools：ToolNode 执行允许的工具"]
    T --> K["知识库 / 日期 / 资源查询 / 预约 service"]
    K --> M["ToolMessage 合并到 messages"]
    M --> A
    C -->|无| E["结束图执行"]
    E --> CHECK["检查最终 AIMessage，提取文本"]
    CHECK --> OUT["Response.success → Markdown 页面"]
```

图中一次 `agent` 节点调用才对应一次模型请求；一个 HTTP 请求可能经过多次模型和工具节点。模型是否调用工具以及调用顺序由消息与模型响应决定，流程图不是“每次一定执行全部五个工具”。

源码把图变量拼成 `gragh`，注释中也有 `LangGragh`；本文使用框架正式名称 LangGraph，代码快照保留源码写法，查找时搜索 build_agent、StateGraph 或 gragh 都能定位。

### 15.23 API 怎样传递当前用户与数据库会话

`api/ai.py` 的关键调用是：

```python
content = agent_service.run_agent(db=db, current_user=current_user, data=data)
```

`current_user` 来自 `Depends(get_current_user)`，`db` 来自 `Depends(get_db)`。run_agent 将它们交给 build_agent，build_agent 再交给 build_tools。当前身份不由模型填写，也不是从聊天正文中解析出来的 user_id。

```text
API 的登录用户与请求 Session
  → run_agent(db, current_user, data)
  → build_agent(db, current_user)
  → build_tools(db, current_user)
  → create_lab_reservation 的函数闭包
  → reservation_service.create_reservation(db, current_user, data)
```

build_tools 在函数内部定义五个工具。内部函数可以使用外层的 db 和 current_user，这叫闭包；例如创建预约工具签名只列资源、日期、时段等参数，没有让模型传入用户对象和数据库会话。

每次 HTTP 请求都会重新创建工具和图，绑定这次请求的上下文。不能把这一版包含请求 Session 和用户对象的图直接缓存为所有用户共用的全局对象，否则会混用请求上下文。

### 15.24 @tool：从函数签名生成工具描述与参数结构

看当前最简单的工具：

```python
@tool
def get_today() -> str:
    """获取服务器当前日期，格式为 YYYY-MM-DD"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d")
```

默认工具名来自函数名，说明来自 docstring，参数类型与默认值用于推导输入结构。装饰后的 get_today 是 LangChain 工具对象，build_tools 返回的是工具对象列表，供模型绑定和 ToolNode 使用。[官方工具说明](https://docs.langchain.com/oss/python/langchain/tools)

在本项目中，`list_lab_equipments(lab_id: int, keywords: str = "")` 的 lab_id 没有默认值，因此成为必填参数；keywords 有默认值，可以省略。`equipment_id: int | None = None` 表示允许不指定设备，从而提交整间实验室预约。

这改善了旧 JSON schema 没声明 lab_id 必填的情况，但不能推导出所有业务限制。`int` 本身不要求正数，`date: str` 不代表日期一定存在；开放时间、归属、状态与冲突仍需 schema/service 检查。把函数装饰成工具，也不会替它增加“用户已确认”的校验。

### 15.25 bind_tools 与 ToolNode：模型看见工具和后端执行工具

当前模型构造最后调用：

```python
model = ChatOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    model=settings.LLM_MODEL,
    temperature=0,
).bind_tools(tools)
```

bind_tools 让后续模型请求携带工具描述；ToolNode(tools) 则在模型返回结构化工具调用后执行相应工具。这两处使用同一份 tools。只把 ToolNode 放进图，不会自动让模型知道可用工具；只 bind_tools，也不会让 Python 函数自行执行。[模型工具调用说明](https://docs.langchain.com/oss/python/langchain/models#tool-calling)

LLM_BASE_URL 和 LLM_MODEL 必须对应支持结构化工具调用的兼容服务。`temperature=0` 是生成参数，不是“结果保证正确”或“每次保证同样调用工具”。新版没有在代码中要求每轮都调用工具，普通问候可以直接回答。

### 15.26 三种输入消息与 ToolMessage：为何不再手工拼字典

run_agent 遍历 ChatRequest.messages，当前规则是：

| 输入 | 处理方式 |
| --- | --- |
| 非空 user 内容 | strip 后转成 HumanMessage |
| 非空 assistant 内容 | strip 后转成 AIMessage |
| 空白内容或其他 role | 不进入 history |
| 原 messages 为空，或过滤后 history 为空 | 抛出业务异常 |

系统提示词从 agent_config 导入，构造 SystemMessage 并放在 history 前面。客户端提交的 system/tool 消息不会作为系统指令或工具结果直接进入图。当前仍允许仅含 assistant 的非空历史，没有额外要求必须以 user 结尾。

模型返回 AIMessage，可能含正文，也可能含 tool_calls。工具执行后由 ToolNode 生成 ToolMessage，关联具体工具调用 ID，再交给模型。旧方案里手写的 assistant 工具请求与 role=tool 结果配对，变成了框架消息类型和工具节点的职责。

过滤 role 并不证明历史文本可信：user/assistant 内容仍来自前端，特别是先前“已确认”的助手文字不能作为服务端业务确认凭据。

### 15.27 MessagesState：节点只返回增量，历史为什么还在

agent_node 读取完整消息，再返回这一轮响应：

```python
def agent_node(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}
```

这里返回的是状态更新，不是自己重新构造全部历史。当前安装包的 MessagesState 为 messages 配置了 add_messages：新 ID 消息通常追加，已有 ID 消息按 ID 更新。因此返回 `[response]` 后，系统消息、用户问题和前面的工具结果仍留在状态中。

不要把这里改成无 reducer 的普通列表状态，再以为相同写法仍会合并；也不要无理由把全部旧消息连同新消息重复返回。状态 schema 的合并规则决定了节点输出如何生效。[Graph API 的消息状态说明](https://docs.langchain.com/oss/python/langgraph/graph-api#working-with-messages-in-graph-state)

### 15.28 StateGraph、条件边与 compile 怎样接起循环

当前 build_agent 注册两个节点：agent 与 tools。普通边 `START → agent` 决定入口，`tools → agent` 让模型读取工具结果。agent 后面使用条件边：

```python
gragh.add_conditional_edges("agent", tools_condition)
```

tools_condition 检查末条消息的工具调用：有调用时返回 tools 路径，否则走结束路径。这里的工具节点名字恰好叫 `"tools"`，与默认路由值对应；如果只重命名节点而不调整条件路由，图就不再按原设计连接。[tools_condition 参考](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/tools_condition)

`compile()` 把图定义编译成可执行对象，不会立即请求模型或执行预约。实际运行发生在 `agent.invoke(...)`。虽然源码只显式导入 START，没有导入 END，条件函数仍可将流程路由到结束状态。

### 15.29 五个工具分别调用哪里，返回什么

| 工具 | 模型提供的参数 | 实际调用 | 输出及当前范围 |
| --- | --- | --- | --- |
| search_lab_docs | query | kb_service.search | 检索文本，或“没有检索到相关的资料”；失败返回 JSON error |
| list_open_labs | 可选 keywords | lab_service.get_lab_page_list | 第 1 页、最多 10 条 status=1 的实验室及 total |
| list_lab_equipments | lab_id、可选 keywords | equipment_service.get_equipment_page_list | 第 1 页、最多 10 条设备及 total；包含数量、状态，不过滤维修设备 |
| create_lab_reservation | lab_id、date、start_time、end_time；可选 equipment_id、remark | ReservationCreateRequest → reservation_service.create_reservation | 成功 JSON 含 ok、资源 ID、日期、规范化时段；状态为待审核 |
| get_today | 无 | datetime.now().strftime | 服务器当前日期字符串 |

查询工具的 open 表示启用状态，不是给定时段空闲。设备 quantity 是资料数量，不是扣减预约后的余量。工具不读取任意 SQL，也不接受模型给出的 Python 函数名执行；允许执行的入口由返回的五个工具对象决定。

项目仍未提供 AI 取消、审核、查询本人预约的工具，也没有单独的时段可用性工具。创建时会校验冲突，不代表查询资料时已计算空闲。

### 15.30 RAG 的位置改变：从固定前置检索到模型可选工具

旧 ai_service.chat 每次先找最近的 user 问题，调用 kb_service.search，再把资料追加到 system_prompt。新 run_agent 不再固定执行这段检索：模型通过 search_lab_docs 取资料，结果以工具消息参与下一次回答。

底层检索算法没有被整体换成 LangChain Retriever：仍使用现有 Chroma、BGE、Markdown 入库以及最多 5 条候选/前 2 条筛选。改变的是检索的触发入口和结果进入对话的位置。

SYSTEM_PROMPT 要求规则、开放时间问题优先查资料，但当前没有额外代码强制验证模型一定调用 search_lab_docs。资源与日期问题可以使用其他工具，普通聊天也可能无需检索。模型本地缓存、预热、原文与索引同步见第 14.19～14.20 节。

### 15.31 相对日期与确认：两次 HTTP 请求怎样连起来

以“明天上午预约某实验室”为例，以下是符合提示词要求的示意，具体资源 ID 和日期必须来自真实工具结果：

1. 第一次发送问题，前端把已有 user/assistant 历史一并提交。
2. 模型调用 get_today 得到服务器日期，再据此换算“明天”；查询资源取得真实 ID 和名称。
3. 若缺少明确开始/结束时间，继续询问；资料完整后复述资源、日期、起止时间，请用户确认。
4. 本次图结束，确认问题作为普通助手文本返回页面。
5. 用户发送“确认预约”，这是第二次 POST；前端把前一轮问题、确认摘要和新回复一起发送。
6. 新建的图从这些文本历史重建上下文，模型调用 create_lab_reservation；工具成功后再答复“已提交，待管理员审核”。

get_today 只返回日期，真正的“明天/后天”换算仍由模型完成。它使用服务器 datetime.now()，代码没有指定业务时区；部署时服务器日期需与预约服务的日期比较保持一致。

当前确认写在 SYSTEM_PROMPT 中，没有 `interrupt()`、确认节点、checkpointer、待确认对象 ID 或服务端 confirmed 字段。它是提示词约定的对话流程，不是后端已强制执行的人工审批。后续若加强确认，需要把用户确认绑定到具体资源与时段，在写入前校验；不能仅因聊天历史里出现“确认”二字就当作不可绕过的授权。

### 15.32 真实预约写入：模型参数经过两层校验

create_lab_reservation 用工具参数构造 ReservationCreateRequest，再调用原预约服务。主要顺序是：

```text
结构化工具参数
  → @tool 推导的输入结构进行校验
  → ReservationCreateRequest：规范化开始/结束时间
  → create_reservation(db, current_user, data)
  → 日期/时间、资源状态、设备归属与同资源冲突检查
  → 原事务锁、失败回滚与死锁重试
  → 写入 user_id=current_user.id、status=0，并 commit
  → 工具 JSON 成功结果 → 模型解释 → HTTP 返回
```

AI 没有自己拼 INSERT，也没有越过原有资源校验。创建服务的完整实现见[预约提交与事务](#reservation-concurrency)，新增工具复用的是同一函数，已有非法日期、零时长及跨资源互斥边界也仍存在。

成功 JSON 返回规范化后的 start_time/end_time，不返回新预约 ID，不能按返回体不存在的 id 去展示详情。成功仅代表已提交待审核申请；最终能否使用仍由管理员审核决定。

一次图执行不是覆盖所有工具的数据库事务。预约服务已经 commit 后，如果后续模型生成失败或前端 60 秒超时，预约记录仍可能存在。应先在“我的预约”核对，再决定是否重试；当前没有请求级幂等键或整图回滚机制。`max_concurrency=1` 也不会自动解决重复提交。

### 15.33 recursion_limit 与 max_concurrency 控制不同的事情

当前调用配置：

```python
config={"recursion_limit": 10, "max_concurrency": 1}
```

recursion_limit 限制图一次运行的 super-step 数量，不等于 10 次用户对话、10 个工具或恰好 10 次模型请求。在当前串行环中，agent 与 tools 会交替消耗图步骤；一次 tools 节点还可能包含多个工具调用。源码注释“10 轮对话”可以作为粗略记忆，准确含义应按图步骤理解。[LangGraph 递归限制说明](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)

max_concurrency=1 用来限制当前同步工具执行的并发度。多个工具共享这次请求的 SQLAlchemy Session，不能让它们同时使用同一会话。本地安装包的同步 ToolNode 使用 get_executor_for_config，执行器读取 max_concurrency 作为工作线程上限，因此这里会逐个执行这一批工具。

串行不等于同一个线程，也不限制其他 HTTP 请求、其他应用进程或后台扫描。图步骤上限不是耗时上限；当前没有额外在 ChatOpenAI 构造中指定模型 timeout，前端 60 秒仍覆盖整个 HTTP 请求。达到步骤上限的框架异常目前会变成通用模型调用失败提示。

### 15.34 最终结果为何还要检查 AIMessage 与回复内容

run_agent 取得 result.messages 的最后一项后，依次检查：

1. messages 是否为空。
2. 最后一项是否为 AIMessage，且不存在仍待执行的 tool_calls。
3. 是否含 invalid_tool_calls；有则抛出业务 code=502。
4. content 为字符串时 strip；为列表时拼接字符串项和字典项中的 text；其他类型按空内容处理。
5. 用正则检查 `<tool_call>` 或 `<function...>` 形式的伪工具标签；发现则返回业务错误，不作为正常答案展示。
6. 有非空文本才返回，否则提示没有有效回复内容。

模型写出“调用 create_lab_reservation”或一段 XML 样式标签，不等于工具已经执行。是否真的执行要看结构化工具调用及服务结果。末尾文本检查是针对已知错误格式的防护，不会验证回答中的每个业务事实，也不能撤销此前已经提交的预约。

content 的列表处理是当前代码的简化文本提取，不能据此宣称支持全部多模态响应类型。

### 15.35 异常分三层：工具结果、图执行和 API 响应

| 发生位置 | 当前处理 | 对使用者意味着什么 |
| --- | --- | --- |
| 工具内部的检索/查询异常 | 返回 JSON 字符串，含 ok=false/error | 作为工具结果给模型；模型可能解释错误或继续尝试 |
| 创建预约的 BusinessException | 取 exc.message 放进失败 JSON | 不伪造成功；业务错误文案可以用于回答 |
| invoke 中的 BusinessException | 原样继续抛出 | 保留现有业务异常信息 |
| invoke 中其他异常，包括图步数耗尽 | 转成“大模型调用失败，请稍后重试” | 当前没有对各类框架错误分别展示 |
| 最终内容或伪工具标签检查失败 | 抛出 BusinessException，部分使用 code=502 | 统一异常处理器生成失败响应 |

build_agent 在 try 之前调用，工具构造、模型初始化或图编译失败不受 invoke 那个 except 包裹。输入过滤和最终内容检查也有各自的位置，排错时应先看异常发生在哪一步。

四个有业务执行的工具会捕获异常并返回文本；装饰器层的参数校验不一定进入函数体，不能把所有参数错误都解释成函数中的 except 捕获。应分别观察 ToolNode 结果与最终 API 返回。

本项目 BusinessException 处理器使用 HTTP 200 + body.code 表达业务错误。因此这里的业务 code=502 不一定是 HTTP 502；前端仍检查统一响应中的 code。部分工具返回原始异常字符串，后续还需整理日志与面向用户的错误信息。

### 15.36 前端几乎不改：接口契约保留，历史仍在浏览器内存

AIChat.vue 的欢迎语新增了“还能让我帮你预约实验室或设备”。handleSend 仍过滤 user/assistant、提交 `{messages: history}`，收到成功 ChatMessage 后追加到页面。api/ai.js 仍是 60000 毫秒超时，页面仍使用 marked 与 DOMPurify。

MessagesState、工具调用 ID 和数据库会话都没有被要求放进前端 JSON。前端收到的是最终助手文本，不是图运行的全部消息，也没有单独展示每一步工具执行轨迹。

每次 run_agent 重新 build_agent 并 compile；当前没有 checkpointer、thread_id 或服务端会话持久化。跨请求能继续对话依靠前端重传文本历史，刷新后恢复欢迎语，不能把 MessagesState 理解成已经保存了用户的长期记忆。

欢迎语提到“怎么取消”可以解释为询问操作方法；当前工具列表并没有 cancel_reservation，不能据欢迎语推定助手能直接取消申请。

<a id="agent-framework-comparison"></a>

### 15.37 自定义方案与框架方案逐项对照

| 关注点 | 旧自定义方案：仍保留 | 当前 LangChain / LangGraph 方案 | 迁移后仍需自己做 |
| --- | --- | --- | --- |
| 工具声明 | 手写 TOOLS JSON schema | @tool 从签名与 docstring 构造工具 | 设计有意义的参数、描述与业务约束 |
| 模型调用 | OpenAI 客户端 + create | ChatOpenAI.bind_tools + invoke | 配置兼容服务，验证结构化调用 |
| 消息表示 | role/content 字典 | Message 对象与 MessagesState | 过滤输入、管理历史范围 |
| 参数解析 | json.loads 与字典判断 | 工具 schema 与 ToolNode 调用 | 日期、权限、资源与业务规则 |
| 函数选择 | run_tool 的 if 分支 | ToolNode 中注册的工具对象 | 明确允许暴露哪些操作 |
| 工具消息配对 | 手工保存调用 ID、追加 role=tool | ToolNode 返回匹配的 ToolMessage | 确认最终答案依据真实结果 |
| 循环 | range(3) 控制模型调用次数 | 节点、条件边、recursion_limit | 结束策略、延迟预算与错误反馈 |
| RAG 时机 | 每次先固定检索 | search_lab_docs 按模型工具请求执行 | 资料准确性、索引同步、必要时强制检索 |
| 用户与会话 | 查询函数接收 db，未用 current_user 写入 | 闭包绑定请求 db/current_user | 跨请求隔离与会话生命周期 |
| 能力范围 | 只读实验室/设备资料 | 加入知识检索、日期、创建预约工具 | 确认门禁、幂等、空闲查询与完整验收 |
| 状态与记忆 | 单次请求内维护 messages | 单次图运行内合并消息 | 持久化、thread_id、跨请求恢复 |
| 排错方式 | 直接跟踪 JSON、for 与分发函数 | 跟踪消息对象、节点、条件路由与工具结果 | 业务日志、可复现检查和真实联调 |

自定义方案便于看见工具协议的每一步，少量工具时调用关系直接；增加分支和循环后，维护消息配对与执行流程的代码会增长。框架方案减少这类调度代码，扩展流程时可通过节点与边表达，但需要理解 reducer、状态、工具 schema 和框架异常。

新增预约能力来自项目实际新增的工具及 current_user 传递，不是仅安装 LangGraph 就自动获得。两种实现都依赖原业务 service；比较时应把“执行方式改变”和“新增业务能力”分开看。

### 15.38 从零复现这一版的顺序

1. 保留旧 ai_service 与 ai_config，先读通原工具协议；核对迁移后的 config_global 路径。
2. 安装当前 requirements.txt，配置三个 LLM 字段；单独准备 BGE 本地缓存与预热开关。
3. 用既有查询 service 写只读 @tool，理解签名、默认值、描述和字符串返回。
4. 添加 get_today、search_lab_docs，再包装原 create_reservation；保持用户身份来自登录依赖。
5. 在 build_agent 中创建工具列表，给 ChatOpenAI 绑定同一份工具。
6. 定义 MessagesState、agent_node、ToolNode 与条件边，compile 后再 invoke。
7. 实现输入消息过滤、图预算、串行工具配置、最终文本归一化和错误分层。
8. 将正在注册的 API 函数改为 run_agent，前端继续复用 ChatMessage 协议。
9. 在专用学习环境按下一节检查真实工具与数据库结果；保留旧代码，比较相同只读问题在两条实现中的执行过程。

不要在同一条 `/chat` 路径同时注册两个同方法处理函数来“保留两版”；当前源码采用保留旧函数注释、只注册新函数的方式。

<a id="agent-current-validation"></a>

### 15.39 当前核对范围与真实验收清单

2026-10-25 本次更新核对实际 API、agent_service、两份配置、知识库、应用入口、依赖与前端，并检查新增快照、目录、锚点和旧教程保留情况。MessagesState 的合并、同步 ToolNode 的执行器配置也对照了本地安装包。没有调用真实模型、访问业务数据库、下载模型或重建 Chroma；第 15.18 节的 30 个断言属于旧自定义方案历史记录，不是新版框架已通过的测试数量。

| 验收场景 | 应观察的证据 |
| --- | --- |
| 未登录、已登录及不同用户 | API 认证生效；创建记录的 user_id 来自当前登录用户 |
| 问安全规则；模型缓存缺失 | 观察是否调用 search_lab_docs；错误能结束请求，不假称找到资料 |
| 启用实验室、某实验室设备 | 结构化 tool_calls 与实际查询结果一致；核对无匹配和超过 10 条情况 |
| 今天/明天/后天 | 观察 get_today 返回值及日期换算，核对服务器时区 |
| 资料不全、未确认、确认后又修改时段 | 观察模型是否继续询问和重新复述；记录提示词确认能否被绕过，不将其算作强制门禁 |
| 确认实验室或设备预约 | 工具成功后实际新增 status=0 记录；管理员审核前不称“已获准使用” |
| 停用资源、维修设备、设备归属错误、时段冲突 | service 拒绝写入；工具返回失败，最终回答不假称成功 |
| 工具缺参/错类型、非法日期、零时长 | 区分框架类型校验与尚待完善的业务规则，记录真实结果 |
| 同轮多个工具 | 确认当前串行配置；前一工具失败时后续动作是否符合预期 |
| 反复请求工具、模型服务失败、伪 XML 调用 | 流程能结束并给出错误，不把标签当正常答案 |
| 写入后模型失败、60 秒超时、重复确认 | 先查实际预约记录，记录重复提交和结果追踪边界 |
| 开/关预热、缓存不完整、刷新浏览器 | 启动路径与开关相符；失败记录日志；刷新会丢失前端历史 |

### 15.40 对照复习：把框架中的每一步还原出来

1. 旧方案哪个 if/for 分支，分别对应新的条件边与 tools 节点？
2. 只写 ToolNode 没有 bind_tools，模型为什么可能不知道可用工具？
3. agent_node 只返回一条消息，哪段合并规则让前面的历史仍存在？
4. db/current_user 没出现在工具参数中，工具为什么仍能使用它们？
5. 为什么 recursion_limit=10 不能解释成 10 次模型调用？
6. 用户说“确认预约”后，哪些事实仍需要服务端校验？当前缺少什么强制确认机制？
7. 预约 commit 成功后模型报错，为什么不能直接断言预约失败？
8. 刷新页面后历史丢失，说明 MessagesState 与持久化会话有什么区别？
9. 对同一句资源查询，分别画出旧 run_tool 和新 ToolNode 的输入、输出与结果 ID。

### 15.41 当前框架代码快照（2026-10-25）

以下直接保存本次读取的工作区文件，包括保留旧入口的注释；快照用于解释现状，不代表上面的待验收项均已完成。旧自定义完整快照仍在第 15.19 节，现有旧配置文件位于 data/config_global/ai_config.py；当前知识库与生命周期快照分别在第 14.20、6.8 节。

<details>
<summary><code>backend/app/api/ai.py</code>（2026-10-25）</summary>

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import ai_service
from app.services import agent_service

router = APIRouter(prefix="/ai", tags=["AI相关的api"])


# @router.post("/chat")
# def chat(
#     data: ChatRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     content = ai_service.chat(db=db, data=data)
#     return Response.success(data=ChatMessage(role="assistant", content=content))


@router.post("/chat")
def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = agent_service.run_agent(db=db, current_user=current_user, data=data)
    return Response.success(data=ChatMessage(role="assistant", content=content))
```

</details>

<details>
<summary><code>backend/data/config_global/agent_config.py</code>（2026-10-25）</summary>

```python
import json
from datetime import datetime
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreateRequest
from app.models.user import User
from app.services import equipment_service, kb_service, lab_service, reservation_service

SYSTEM_PROMPT = """你是智能实验室预约系统的 Agent，回答要简洁。
你可以：
1. 使用 search_lab_docs 查询实验室的规则、安全、开放时间等问题
2. 使用 list_open_labs / list_lab_equipments 查询真实的实验室和设备
3. 在用户进行预约确认后，使用 create_lab_reservation 来进行真实的预约写库
4. 使用 get_today 来进行日期的换算

## 必须遵守
工具必须通过接口提供的工具调用机制执行，不要把 <tool_call> 或 <function=...> 等标记作为回复内容。
工具名和参数以实际提供的工具定义为准，不要编造不存在的 search_for 等工具。
只有工具返回成功后，才能告诉用户预约已提交；工具返回错误时说明失败原因，不要声称成功。
当用户提到了 今天、明天、后天 等日期相关的问题，请先调用 get_today 来获取日期，**不要直接返回"我需要确定明天的具体日期"**

在提交预约之前必须向用户复述实验室ID与名称（或设备ID和名称）、日期、开始时间、结束时间。并得到用户确认再进行实际操作。
用户没说【确认】【确认预约】【就这样预约】等确定性回复之前，不要调用 create_lab_reservation。
工作流的确认环节里如果缺少了 lab_id，请先 list_open_labs 查到了 lab_id 再创建，不要瞎写。
工作流的确认环节里如果缺少了 equipment_id，请先 list_lab_equipments 查到了 equipment_id 再创建，不要瞎写。

预约成功后状态是待审核，必须管理员确认后实验室（或设备）才能使用。
不要瞎编数据库里没有的实验室或者设备信息。
如果是问开放时间或者实验室规则，优先调用 search_lab_docs，不要凭空回复。
"""


def build_tools(db: Session, current_user: User):

    @tool
    def search_lab_docs(query: str) -> str:
        """根据用户的提问去检索知识库"""
        try:
            return kb_service.search(query) or "没有检索到相关的资料"
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def list_open_labs(keywords: str = "") -> str:
        """查询开放中的实验室"""
        try:
            keywords = keywords.strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def list_lab_equipments(lab_id: int, keywords: str = "") -> str:
        """查询隶属于实验室的设备"""
        try:
            keywords = keywords.strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, lab_id=int(lab_id), keywords=keywords
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return json.dumps(
                {"total": page.total, "equipments": rows}, ensure_ascii=False
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def create_lab_reservation(
        lab_id: int,
        date: str,
        start_time: str,
        end_time: str,
        equipment_id: int | None = None,
        remark: str | None = None,
    ) -> str:
        """创建预约"""
        try:
            data = ReservationCreateRequest(
                lab_id=lab_id,
                equipment_id=equipment_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                remark=remark,
            )
            reservation_service.create_reservation(db, current_user, data)

            return json.dumps(
                {
                    "ok": True,
                    "message": "预约已提交，请等待管理员审核",
                    "lab_id": lab_id,
                    "equipment_id": equipment_id,
                    "date": date,
                    "start_time": data.start_time,
                    "end_time": data.end_time,
                },
                ensure_ascii=False,
            )
        except BusinessException as exc:
            return json.dumps({"ok": False, "error": exc.message}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def get_today() -> str:
        """获取服务器当前日期，格式为 YYYY-MM-DD"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    return [
        search_lab_docs,
        list_open_labs,
        list_lab_equipments,
        create_lab_reservation,
        get_today,
    ]
```

</details>

<details>
<summary><code>backend/app/services/agent_service.py</code>（2026-10-25）</summary>

```python
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest
from data.config_global.agent_config import SYSTEM_PROMPT, build_tools


def build_agent(db: Session, current_user: User):
    tools = build_tools(db=db, current_user=current_user)
    model = ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=0,
    ).bind_tools(tools)

    def agent_node(state: MessagesState):
        """LangGragh 执行的工作流的节点"""
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    gragh = StateGraph(MessagesState)
    gragh.add_node("agent", agent_node)  # 调用大模型的节点
    gragh.add_node("tools", ToolNode(tools))  # tool call的节点
    gragh.add_edge(START, "agent")  # 流程的起点, call LLM
    gragh.add_conditional_edges(
        "agent", tools_condition
    )  # 判断是否有 tool_call, 有就继续call, 没有就END 输出
    gragh.add_edge("tools", "agent")  # agent查看tool调用的结果
    return gragh.compile()


def run_agent(db: Session, current_user: User, data: ChatRequest):
    """大模型对话"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")

    history = []
    for message in data.messages:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))

    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    agent = build_agent(db, current_user)
    try:
        result = agent.invoke(
            {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]},
            # Tools share this request's SQLAlchemy session; execute them sequentially.
            config={"recursion_limit": 10, "max_concurrency": 1},
        )  # 设置对话循环的上限是10轮
    except BusinessException:
        raise
    except Exception:
        raise BusinessException(message="大模型调用失败，请稍后重试")

    messages = result.get("messages") or []
    if not messages:
        raise BusinessException(message="大模型没有任何返回内容")

    message = messages[-1]
    if not isinstance(message, AIMessage) or message.tool_calls:
        raise BusinessException(message="大模型没有返回有效的回复内容")

    if message.invalid_tool_calls:
        raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

    content = message.content

    # 处理字符串类型的回复
    if isinstance(content, str):
        content = content.strip()

    # 处理列表类型的回复
    elif isinstance(content, list):
        content = "".join(
            (
                part
                if isinstance(part, str)
                else part.get("text", "") if isinstance(part, dict) else ""
            )
            for part in content
        ).strip()

    else:
        content = ""

    if re.search(r"<\s*/?\s*(?:tool_call|function)\b", content, re.IGNORECASE):
        raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

    if content:
        return content

    raise BusinessException(message="大模型没有返回有效的回复内容")
```

</details>

<details>
<summary><code>frontend/src/views/AIChat.vue</code>（2026-10-25）</summary>

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>AI智能助手</span>
        </div>
      </template>
      <div
        ref="listRef"
        style="
          height: 480px;
          overflow-y: auto;
          padding: 8px 4px;
          background-color: #fafafa;
          border-radius: 6px;
        "
      >
        <div
          v-for="(item, index) in messages"
          :key="index"
          :style="{
            display: 'flex',
            justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '12px'
          }"
        >
          <div
            :style="{
              maxWidth: '70%',
              padding: '10px 12px',
              borderRadius: '8px',
              backgroundColor: item.role === 'user' ? '#409eff' : '#fff',
              color: item.role === 'user' ? '#fff' : '#333',
              lineHeight: '1.6',
              boxShadow: '0 1px 2px rgba(0 ,0, 0, 0.06)'
            }"
            v-html="parseMarkdown(item.content)"
          ></div>
        </div>
      </div>
      <!-- 输入框 -->
      <div style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="问问实验室怎么预约、开放时间..."
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.stop
        ></el-input>
        <el-button type="primary" :loading="loading" @click="handleSend">发送</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify' // 过滤危险的 HTML，防止 XSS 攻击
import { chatApi } from '@/api/ai'

// 将 markdown 字符串转换为安全的 HTML 字符串
const parseMarkdown = (text) => {
  if (!text) return ''
  // 使用 marked 解析，然后用 DOMPurify 清理
  const rawHtml = marked.parse(text)
  return DOMPurify.sanitize(rawHtml)
}

const messages = ref([
  {
    role: 'assistant',
    content:
      '你好, 我是实验室助手。你可以向我提问怎么预约、取消实验室或者设备, 也可以问我现在系统所存在的实验室与设备的具体信息, 还能让我帮你预约实验室或设备。'
  }
])

const input = ref('')
const loading = ref(false)
const listRef = ref()

const scrollToBottom = () => {
  nextTick(() => {
    const elem = listRef.value
    if (elem) elem.scrollTop = elem.scrollHeight
  })
}

const handleSend = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()
  try {
    const history = messages.value.filter(
      (item) => item.role === 'user' || item.role === 'assistant'
    )
    const res = await chatApi({ messages: history })
    if (res.code === 200) {
      messages.value.push(res.data)
      scrollToBottom()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false
  }
}
</script>
```

</details>

<a id="agent-sse"></a>

### 15.42 SSE 版本的文件地图与实际入口（2026-10-26）

本节起讲解当前流式版本。第 15.1～15.19 节保留自定义工具循环，第 15.20～15.41 节保留 LangChain/LangGraph 一次性 JSON 版本，便于比较从协议、框架到输出方式的演进。

| 文件 | 当前变化 | 与下一层的连接 |
| --- | --- | --- |
| backend/app/api/ai.py | 注册 POST /chat/stream，返回 StreamingResponse | 调用 stream_agent，将字典编码为 SSE 帧 |
| backend/app/services/agent_service.py | streaming=True、异步模型节点、astream_events、三个辅助函数 | 将框架事件变成六种页面事件 |
| backend/data/config_global/agent_config.py | 增加 TOOL_LABELS | 把工具名转换为中文状态文案；五个业务工具仍复用原服务 |
| frontend/src/api/ai.js | chatStreamApi 使用 fetch 读响应流 | 解码字节、缓存半帧、解析 JSON，再调用 onEvent |
| frontend/src/views/AIChat.vue | 提前创建响应式助手消息，显示状态、步骤与增量正文 | 按 evt.type 更新同一个消息对象 |
| frontend/tests/ai.test.js | 使用真实 API 模块和模拟 ReadableStream | 验证分块解析、鉴权、错误传递与释放 reader 锁 |
| backend/app/services/reservation_service.py | 扫描改用 asyncio.to_thread，并处理取消 | 与聊天共用事件循环时不再直接同步执行扫描，详见第 13.29 节 |

总路由 `/api`、AI 前缀 `/ai` 与接口 `/chat/stream` 拼成 `/api/ai/chat/stream`。旧 `/chat` 的两个处理函数均已注释，旧 run_agent 也已注释；保留注释不等于旧 URL 仍提供服务。旧自定义 ai_service 与配置文件继续保留，当前聊天由 stream_agent 执行。

### 15.43 一次流式提问怎样经过前后端

```mermaid
sequenceDiagram
    actor U as 用户
    participant V as AIChat.vue
    participant F as chatStreamApi / fetch
    participant A as chat_stream / StreamingResponse
    participant G as stream_agent / LangGraph
    U->>V: 输入问题并发送
    V->>V: 加入用户消息和 reactive 空助手消息
    V->>F: 历史 + onEvent 回调
    F->>A: POST /api/ai/chat/stream，JSON 与 Bearer token
    A->>G: async for 读取事件
    G-->>A: status：正在思考
    A-->>F: data: JSON + 空行
    F-->>V: onEvent(status)
    loop 图执行中的模型和工具事件
        G-->>A: tool_start / tool_end / token
        A-->>F: 持续发送 SSE 帧
        F->>F: UTF-8 解码 → 按空行分帧 → JSON.parse
        F-->>V: onEvent(evt)
        V->>V: 更新 status/steps/content，nextTick 后滚动
    end
    G-->>A: done，或异常时 error
    A-->>F: 结束响应流
    F-->>V: 读取函数完成或抛错
    V->>V: finally 复原 loading 和状态
```

这是一次 HTTP 请求内的多次服务器推送，不是每个 token 都发一个新请求，也不是 WebSocket 双向连接。用户再次输入确认时仍发起下一次 POST；当前页面在 loading 时会阻止再次发送。

### 15.44 SSE 帧格式与项目的六种事件

后端每次发送的格式是：

```python
yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
```

外层是 SSE 文本，`data:` 后才是 JSON；两个换行标记帧结束。ensure_ascii=False 让中文保留为可读字符，但网络上传输的仍是 UTF-8 字节。[SSE 格式说明](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

```text
data: {"type":"status","message":"正在思考..."}

data: {"type":"tool_start","name":"list_open_labs","label":"查询开放的实验室"}

data: {"type":"token","content":"找到以下实验室"}

data: {"type":"done"}

```

| JSON 的 type | 携带字段 | 当前意义 |
| --- | --- | --- |
| status | message | 图运行前的状态提示 |
| tool_start | name、label | 某个工具开始执行 |
| tool_end | name、label、preview | 工具返回；preview 是截断后的输出文本 |
| token | content | 模型正文增量，可能为空或包含多个字符 |
| done | 无正文 | 框架事件迭代正常结束 |
| error | message | 业务异常或通用执行失败提示 |

本项目没有发送 SSE 的 `event:` 字段；这里的 type 是 JSON 内部字段，由自定义回调分发。`{"type":"done"}` 是实际完成事件；前端也兼容忽略 `data: [DONE]`，但后端目前不发送这个标记。

### 15.45 async def、yield、async for 与 StreamingResponse

普通 async 函数使用 await 等待结果；async 函数里出现 yield 后，它成为异步生成器，调用时得到可以逐步迭代的对象。stream_agent 每 yield 一次，外层 event_generate 就收到一个事件字典。

event_generate 再把字典编码成字符串，并交给 StreamingResponse。返回 StreamingResponse 对象不意味着此时图已经执行完，正文会在后续响应发送过程中逐段产生。

| 设置 | 作用与边界 |
| --- | --- |
| media_type="text/event-stream" | 声明正文是 SSE 流，不是一次性 Response.success JSON |
| Cache-Control: no-cache | 要求缓存重验证；不能单独保证代理立即转发每个片段 |
| Connection: keep-alive | 当前代码显式设置的连接头，不是应用级心跳 |
| X-Accel-Buffering: no | 向支持该头的 Nginx 请求关闭响应缓冲；实际代理配置仍需验证 |

应用 yield 不保证用户立刻看到一个字；模型输出、服务端发送、代理、网络和浏览器处理都会影响到达节奏。后端帧数、网络数据块数与页面更新次数并不需要一一对应。

### 15.46 streaming=True 与 ainvoke 为什么能一起使用

build_agent 的图结构仍是 START → agent → 条件边 → tools → agent。变化在模型与节点：ChatOpenAI 开启 streaming=True，agent_node 改成 async def，并使用 `await model.ainvoke(state["messages"])`。

节点仍等待本轮完整 AIMessage，再返回 `{"messages": [response]}` 更新图状态；外层 astream_events 同时能观察模型运行中产生的流式事件。这解释了“节点返回完整消息”与“页面提前收到增量文本”为什么可以同时成立。

```python
async for event in agent.astream_events(
    inputs, version="v2", config={"recursion_limit": 10}
):
    kind = event.get("event")
```

这里读取的是 Runnable 事件流；version="v2" 表示这套事件的格式，不是 SSE 版本，也不是对话轮数。不要与 graph.astream 的 stream_mode 或其他接口中的同名 version 参数混为一谈。本地 langchain_core 的 astream_events 文档列出了 event、name、data、metadata 等字段；项目只向浏览器转发需要的部分。[LangGraph 流式机制](https://docs.langchain.com/oss/python/langgraph/streaming)

源码中 `await model.astream(...)` 是注释，不是当前运行路径。astream 通常通过 async for 消费输出，不能只把方法名替换后就当成与 ainvoke 相同的返回值使用。

### 15.47 三个辅助函数与工具过程展示

`_build_history()` 把非空 user/assistant 内容去掉首尾空白，转成 HumanMessage/AIMessage；过滤后为空则抛业务异常。系统提示词由服务端加入，前端步骤文案不作为系统指令。

`_tool_output_preview(output, limit=200)` 先取 ToolMessage.content；不是字符串时用 str 转换，再截取最多 200 个字符并加省略号。这个限制按字符串字符计，不按字节或模型 token 计；它是显示预览，不是 JSON 解析或业务成功判断。

TOOL_LABELS 将五个工具映射到中文名称；事件中同时保留机器名称 name 和展示 label。未找到映射时回退到工具名。

| 框架事件 | 项目事件 | 内容来源 |
| --- | --- | --- |
| on_tool_start | tool_start | event.name → name 与 TOOL_LABELS |
| on_tool_end | tool_end | 同一工具名称，加 event.data.output 的预览 |
| on_chat_model_stream | token | event.data.chunk 经 _chunk_text 提取正文 |

工具内部可以返回 `{"ok":false,"error":"..."}` 而不抛异常，此时仍可能收到 tool_end。页面显示“创建预约单完成”只表示工具函数返回，不能等同于数据库写入成功；需要结合工具结果与实际预约记录判断。

当前自定义事件没有暴露 run_id 或 tool_call_id，同名工具重复调用时只展示顺序步骤。若以后做可折叠的精确调用配对，需要增加稳定的调用标识。

### 15.48 _chunk_text：正文增量不是每次恰好一个字

_chunk_text 对 None 返回空字符串；通过 getattr 取得 content。字符串直接返回；列表则把字符串项和字典中的 text 拼接；其他非空类型转成字符串。

当前 metadata 过滤允许 `langgraph_node` 为 agent 或 None 的模型事件，其余节点跳过。它没有区分图循环中“工具调用前的模型说明”和“最后一轮答案”，同一请求的多个模型轮次正文都可能被追加进同一个气泡。

token 是本项目事件名，content 可能是半句、多个字、空格、换行或空字符串，不是计费 token 的计数。正文追加时不能对每个片段单独 trim，否则会破坏单词间空格、Markdown 换行或代码缩进。

当前即使 _chunk_text 返回空串也会 yield token；前端仍会清掉 status。列表提取假设 text 是字符串，没有完整多模态类型校验。该实现只展示正文和工具过程，不展示模型私有推理内容。

### 15.49 错误发生在响应之前还是流里面

| 阶段 | 当前表现 | 前端处理 |
| --- | --- | --- |
| 请求体校验或认证失败 | FastAPI 在进入响应流前返回 HTTP/JSON 错误 | chatStreamApi 检查 401、res.ok 和响应类型 |
| stream_agent 输入、建图或运行抛业务异常 | yield type=error，message 为业务文案 | 页面显示错误提示；没有正文时把文案放进气泡 |
| stream_agent 中其他 Exception | yield 通用 error | 提示“大模型调用失败，请稍后重试” |
| 传输中断、JSON 解析失败、回调抛错 | fetch/reader/解析函数的 Promise 拒绝 | handleSend 的 catch 与 finally 收尾 |

流开始发送之后，错误不能靠重新返回一份 Response.success/Response.error 来替换已经发出的正文。本实现把错误放进事件通道；因此 HTTP 200 也可能包含 error 事件。

正常循环结束会发 done；异常分支发 error 后生成器结束，不再补发 done。没有请求级“异常发生就撤销所有工具”的机制，预约如果已经 commit，后续出错仍可能留下记录。

### 15.50 为什么用 POST fetch，而不是原来的 Axios

chatStreamApi 向 `/api/ai/chat/stream` 发 POST，body 仍为 JSON.stringify(data)，请求头显式设置 application/json、text/event-stream 和 Bearer token。baseUrl 来自 VITE_API_BASE_URL，并去掉末尾一个斜杠；为空时继续使用同源开发代理。

原生 EventSource 接口不提供这里需要的 POST body 和任意 Authorization 头配置，因此项目选择 fetch 读取响应流。SSE 是正文格式，不要求前端一定使用 EventSource；本实现也不会自动获得 EventSource 的重连能力。

fetch 不经过 utils/request.js 的 Axios 拦截器。当前 401 只抛“登录已失效”错误，页面负责提示，没有自动清理登录、跳转或复用旧请求会话版本检查。原 chatApi 的 timeout:60000 已注释，新请求没有设置超时或 AbortController，不能继续说“当前聊天 60 秒自动超时”。

收到响应头后依次检查：401 → HTTP 是否成功且存在 body → content-type 是否包含 text/event-stream。普通 fetch 遇到 HTTP 4xx/5xx 不会仅因此自动拒绝 Promise，代码必须检查状态。其他 HTTP 错误目前多为通用文案，没有统一读取 JSON 错误详情。

### 15.51 getReader、TextDecoder 和 buffer 各解决什么问题

```text
reader.read()：取得任意大小的字节块
  → TextDecoder(stream:true)：保留可能跨块的 UTF-8 字节
  → buffer：保留可能跨块的 SSE 文本帧
  → split(空行)：取出完整帧
  → dispatchEvent：从 data: 解析 JSON
  → onEvent：更新页面
```

一个汉字的 UTF-8 字节可能分在两次 read 中；一条 JSON 也可能分在多个网络块中。TextDecoder 的流模式处理前一种边界，buffer 处理后一种边界，二者不能互相替代。

每次读取后立即把解码结果加入 buffer，再按 `/\r?\n\r?\n/` 分割。`chunks.pop()` 取走最后尚未结束的残片，其余完整帧立即分发。即使连接还没关闭，页面也能看到已经到达的完整事件；不能把分发循环放到整个 while 结束之后。

读取完成时调用无参数 decoder.decode() 冲刷残余字节，再处理剩余文本。[TextDecoder 的 stream 选项](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/decode)

### 15.52 dispatchEvent、最后半帧与 releaseLock

dispatchEvent 按行拆一帧，只保留 data: 行；每行去掉前缀和前导空白，多行 data 用换行连接。随后跳过空数据与 [DONE]，JSON.parse 后调用 onEvent。

若 JSON 本身不合法，抛“流式回复格式错误，请重试”；onEvent 放在 JSON 的 try/catch 之外，回调自己的异常会原样向 handleSend 传播，不会误报成 JSON 错误。

EOF 时非空 buffer 也会尝试解析，这是本客户端对缺少末尾空行的容错行为。它不是“服务器以后可以省略分隔符”的约定，也不能把截断的半个 JSON 修复成完整数据。解析器面向当前后端格式，支持 LF/CRLF 和多行 data，未实现完整的 id/retry/事件名/重连协议。

finally 中 reader.releaseLock() 释放读取器占用，让流不再被这个 reader 锁住；它不等于 reader.cancel()，也不等于取消 HTTP 或停止后端预约。当前没有限制 buffer 大小；未出现 done 就正常 EOF 也会被接受，异常截断检测仍需补齐。

### 15.53 reactive 助手消息：为什么创建后持续修改同一个对象

页面先放入用户消息，再创建：

```js
const assistant = reactive({
  role: 'assistant',
  content: '',
  status: '正在思考...',
  steps: []
})
messages.value.push(assistant)
```

回调一直修改这个 assistant 代理。若把普通对象 push 进响应式数组，却仍通过原来的普通对象引用改字段，修改可能绕过代理，造成正文到达但页面没有及时更新。使用 reactive 保证这里持有的引用就是响应式代理；通过数组中的代理访问也能追踪变化，不能把问题泛化成“数组里放对象都无效”。

token 到达后使用 `assistant.content += evt.content || ''`。追加而非覆盖，才能保留先前片段；done 只清理状态，不能再追加一份完整答案，否则会显示重复正文。

### 15.54 页面状态与下一轮 history 为什么要拆开

页面消息有 role/content/status/steps 四类字段；后端请求仍只需要 role/content。

```js
const history = messages.value
  .filter((item) => item.role === 'user' || item.role === 'assistant')
  .slice(0, -1)
  .map(({ role, content }) => ({ role, content }))
```

slice(0,-1) 排除刚刚插入的空助手；map 解构并重建对象，去掉状态和步骤。这里依赖“当前空助手恰好位于最后”的插入顺序。若以后插入系统提示行或并发发送，要同步调整选择规则。

status 表示此刻在做什么，steps 留下本次工具过程，content 保存要继续参与对话的正文。步骤不会单独回传，但已经输出的模型说明、半截正文或作为 content 写入的错误文案可能在下一次作为 assistant 历史重传；当前没有单独的失败消息过滤标记。

### 15.55 六种事件怎样更新 UI，loading 何时结束

| 收到事件 | 页面更新 |
| --- | --- |
| status | 替换 assistant.status |
| tool_start | 状态改为“正在…”；steps 追加“开始” |
| tool_end | 状态改为“…完成”；追加完成和 preview |
| token | content 追加增量；清空当前状态 |
| done | 清空状态，不再追加正文 |
| error | 清空状态、ElMessage.error；无正文时填入错误文案 |

状态和步骤通过插值显示，正文仍走 marked → DOMPurify → v-html。每个事件后都请求滚动，nextTick 让滚动发生在 DOM 更新后。流式 Markdown 可能暂时只有半个列表或代码围栏，继续收到正文后重新解析即可；当前没有节流，长文本高频更新的开销仍需观察。

loading 在 chatStreamApi 读取结束或失败后的 finally 中复原，不是收到 done 就立刻结束网络读取。error 回调也没有主动 throw 或 cancel，正常情况下由后端随后结束流。已有部分正文遇错时会保留，错误通过提示框展示，避免把已收到的内容直接覆盖。

### 15.56 流式版本没有自动继承旧版的保护

| 项目 | 2026-10-25 JSON 版本 | 当前 SSE 版本 |
| --- | --- | --- |
| 返回结果 | 检查最后一条 AIMessage 后返回文本 | 逐事件转发正文，迭代结束发送 done |
| invalid_tool_calls、伪 XML 检查 | run_agent 中显式检查 | 检查代码位于已注释的 run_agent，stream_agent 未复用 |
| 空答案检查 | 最终正文为空则报错 | 没有统计是否收到非空正文，可能只结束而没有答案 |
| 工具并发设置 | invoke 配置 max_concurrency=1 | astream_events 仅传 recursion_limit=10 |
| 前端请求超时 | Axios 60000 毫秒 | 当前 fetch 未配置应用级超时 |
| 取消与重连 | 无专门协议 | 仍未实现停止按钮、心跳、事件 ID 或自动重连 |

当前异步 ToolNode 在安装包中用 asyncio.gather 收集同批工具调用，同批多个工具可能并发访问闭包中的同一 Session。不能继续沿用第 15.33 节“本请求工具串行”的结论，也不能仅凭改成 async 就认为同步 SQLAlchemy Session 安全；这属于待核对与修补项，本文未改变业务源码。

done 说明事件迭代走到正常结束，不证明模型回答有效，也不证明任何预约已成功。逐段展示后，最终发现错误不能把用户已经看到的内容当作从未出现；后续可增加输出阶段标识、最终结果校验和失败标记。

<a id="sse-session-lifecycle"></a>

### 15.57 FastAPI 版本与流式数据库会话的生命周期

项目 requirements.txt 固定 FastAPI 0.115.13，get_db 使用 yield/finally close。本地 routing.py 显示依赖退出栈在返回 Response 对象之前退出；官方文档也说明 0.118.0 之前相关版本在发送 StreamingResponse 前执行 yield 依赖清理，0.118.0 才恢复到响应发送后清理。[FastAPI 流响应与 yield 依赖](https://fastapi.tiangolo.com/advanced/advanced-dependencies/#dependencies-with-yield-and-streamingresponse-technical-details)

当前 event_generate 把依赖提供的 db 交给后续流式工具；不能直接套用“直到流结束才 close”的教程结论。SQLAlchemy Session 默认 close 后可能重置并再次使用，不一定马上报“对象已关闭”，但后续重新取连接时的释放、用户 ORM 对象状态和错误收尾仍需验证。

这与同批工具共享 Session 的并发问题是两个层面：一是生命周期，二是同一时刻由谁使用。后续方案可考虑由生成器明确创建/关闭流内会话，或核对版本升级后的依赖清理行为；无论采用哪种，都需要同时验证认证用户上下文、断连清理和事务失败。本次只记录现状与待办，没有升级 FastAPI 或连接真实数据库。

### 15.58 DeepSeek 兼容配置与“正在思考”的含义

build_agent 使用 urlparse 解析 LLM_BASE_URL，仅当 hostname 等于 `api.deepseek.com` 时，传入：

```python
extra_body={"thinking": {"type": "disabled"}}
```

其他主机的 extra_body 为 None。这个判断看实际 URL 的主机名，不根据模型名称猜测提供方，也不会自动覆盖兼容代理域名。

源码注释说明当前对话只保留正文；DeepSeek 的思考模式配合工具调用涉及 reasoning_content 的回传约定，因此该官方端点分支选择禁用思考模式。[DeepSeek 思考模式与工具调用说明](https://api-docs.deepseek.com/guides/thinking_mode/)

页面“正在思考...”来自本地 status 事件，工具步骤来自应用执行事件；这些是进度提示，不是模型内部思维链。开启 SSE 也不代表已经支持 reasoning_content 的展示、存储或回传。

### 15.59 三个阶段放在一起比较

| 对照点 | 自定义工具循环 | 框架 JSON 版本 | 当前框架 SSE 版本 |
| --- | --- | --- | --- |
| 历史入口 | ai_service.chat | run_agent | stream_agent |
| 执行方式 | 手写 range/消息配对 | StateGraph.invoke | astream_events + 异步节点 |
| HTTP 结果 | 一次性 Response JSON | 一次性 Response JSON | POST 流响应，data: JSON 事件 |
| 前端入口 | chatApi/Axios | chatApi/Axios | chatStreamApi/fetch/reader |
| 页面更新 | 完整答案后新增助手消息 | 完整答案后新增助手消息 | 先放 reactive 助手，再更新状态、步骤和正文 |
| 学习重点 | 工具协议细节 | 消息状态与图调度 | 异步生成器、流事件、网络分块与 UI 增量 |

SSE 主要改变结果传递和界面反馈，五个工具仍调用原业务服务。它没有自动补齐后端强制确认、幂等、取消/审核工具或空闲时段计算。与本次一起修改的预约扫描线程化放在第 13.29 节，便于从对应业务文件继续学习。

### 15.60 从零复现 SSE 版本的顺序

1. 先读懂第 15.20～15.41 节的消息图，保留旧方案与阶段快照。
2. 约定六种事件和各字段，区分正文、过程、结束及错误。
3. 抽取历史转换、片段提取和预览函数，添加 TOOL_LABELS。
4. 模型开启流式输出，节点改为 ainvoke；用 astream_events 映射框架事件。
5. 注册 /chat/stream，逐事件 JSON 编码并追加 SSE 空行。
6. 前端实现 POST fetch、认证头、状态检查、UTF-8 解码与半帧缓存。
7. 页面创建 reactive 助手，用回调更新同一对象；重传历史只带 role/content。
8. 运行现有解析测试，验证“连接未关闭就可收到事件”。
9. 在真实浏览器、代理和模型环境检查分段显示，再验收数据库生命周期、工具并发与失败收尾。

不要把“后端 yield 正常”“解析单测通过”“浏览器真正逐段显示”“预约正确写库”合并成同一个验证结论。

<a id="sse-validation"></a>

### 15.61 本次检查记录与真实 SSE 验收

2026-10-26 在 frontend 目录实际执行现有测试：

```powershell
node --test tests/ai.test.js
```

结果为 **7 项通过、0 失败**。测试通过 Vite SSR 加载实际 chatStreamApi，模拟 fetch、localStorage 与 ReadableStream；检查覆盖：

1. 流未关闭前就分发事件，并发送正确 URL、token 与历史。
2. 按字节拆分中文与 CRLF 帧时保持内容正确，忽略注释和兼容 [DONE]。
3. EOF 前最后一帧没有末尾空行时仍能分发。
4. 401 的登录失效提示。
5. 非 SSE 响应类型被拒绝。
6. 非法 JSON 报错且释放 reader 锁。
7. onEvent 回调异常原样传播。

这些用例不挂载 AIChat.vue，不连接真实后端、模型、MySQL 或代理；不能据此认定 Vue 打字机效果、工具并发、会话清理与真实预约流程已验收。frontend/tests 现在存在 ai.test.js，但它不是恢复了早期 6 项登录测试；旧自定义方案的 30 个断言也不是本次流式测试数量。

| 真实验收场景 | 要观察的结果 |
| --- | --- |
| 普通问答与长回答 | 连接未关闭前持续出现内容；空格、换行和代码块不丢失 |
| 知识/资源/日期工具 | 状态和过程先后合理，tool_end 的失败 JSON 不被误称成功 |
| 预约创建成功与冲突 | 查实际待审核记录；错误提示与数据库结果一致 |
| 多工具、同名工具连续调用 | 核对并发与步骤归属，检查共享 Session 的行为 |
| 空历史、无有效文本、伪工具标签 | 核对 error/done 与缺失的最终校验，不把空结束视为有效回答 |
| 断网、关页面、服务端异常 | 部分正文保留、loading 收尾、连接和数据库资源释放 |
| 未收到 done 就 EOF、长时间无数据 | 记录当前缺少终止校验、超时和心跳的行为 |
| 写入后断流、重复确认 | 先核对“我的预约”，避免将输出失败误判为未写库 |
| Vite、直连与 Nginx 部署 | Authorization、代理转发、无明显缓冲和真实首片延迟 |
| 后台扫描同时运行、重载退出 | to_thread 不阻塞主事件循环；取消后线程内任务收尾另行检查 |

### 15.62 SSE 复习练习

1. 分别解释模型 token 片段、SSE 帧、网络字节块和 Vue 更新为什么不是同一个单位。
2. 为什么 TextDecoder 已经设置 stream:true，仍然需要字符串 buffer？
3. 如果只有 releaseLock，没有 cancel/AbortController，会停止哪些操作、不会停止哪些操作？
4. 工具返回 ok=false 时，为什么仍可能出现 tool_end 和“完成”状态？
5. 为什么 done 不应该再携带一份正文直接追加？当前怎样识别没有 done 的中断？
6. 对照旧版，列出流式版本未继承的最终输出校验与并发设置。
7. 为什么 FastAPI 的具体版本会影响流中的数据库 Session？
8. 错误发生在已经收到一半正文之后，页面、历史和数据库各自可能留下什么？

### 15.63 当前 SSE 代码快照（2026-10-26）

以下保存当前 API、Agent、工具标签、前端解析、页面和已有测试，规范化行尾空白。保留源码中的旧代码注释，便于比较迁移过程；第 15.19 与 15.41 节的历史快照继续保留。预约扫描的当前片段在第 13.29 节。

<details>
<summary><code>backend/app/api/ai.py</code>（2026-10-26）</summary>

```python
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import ai_service
from app.services import agent_service

router = APIRouter(prefix="/ai", tags=["AI相关的api"])


# @router.post("/chat")
# def chat(
#     data: ChatRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     content = ai_service.chat(db=db, data=data)
#     return Response.success(data=ChatMessage(role="assistant", content=content))


# @router.post("/chat")
# def chat_agent(
#     data: ChatRequest,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     content = agent_service.run_agent(db=db, current_user=current_user, data=data)
#     return Response.success(data=ChatMessage(role="assistant", content=content))


@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    async def event_generate():
        async for event in agent_service.stream_agent(
            db=db, current_user=current_user, data=data
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generate(),
        media_type="text/event-stream",  # 告诉浏览器这是 SSE 流
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 避免缓存吐出
        },
    )
```

</details>

<details>
<summary><code>backend/app/services/agent_service.py</code>（2026-10-26）</summary>

```python
import re
from typing import Any
from urllib.parse import urlparse
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.config import settings
from app.models.user import User
from app.schemas.ai import ChatRequest
from data.config_global.agent_config import build_tools, SYSTEM_PROMPT, TOOL_LABELS


def _build_history(data: ChatRequest) -> list:
    """将前端的消息转成 LangChain 的消息对象"""
    history = []
    for message in data.messages:
        if message.role == "user" and message.content.strip():
            history.append(HumanMessage(content=message.content.strip()))
        elif message.role == "assistant" and message.content.strip():
            history.append(AIMessage(content=message.content.strip()))
    if not history:
        raise BusinessException(message="请输入您的对话内容")
    return history


def _tool_output_preview(output: Any, limit: int = 200):
    """把工具输出的结果收成短文本预览, 避免整段的JSON污染了输出的区域"""
    if isinstance(output, ToolMessage):
        output = output.content

    text = (
        output if isinstance(output, str) else str(output)
    )  # output 有可能是 dict -> str

    return text if len(text) <= limit else text[:limit] + "..."


def _chunk_text(chunk: Any):
    """
    从模型的流式输出里面 拿到纯文本
    chunk.content 可能是 str [{type, text}, ....] 等类型 这个需要统一处理成字符串
    """
    if chunk is None:
        return ""

    # chunk 如果是 AiMessage 类型的 则可以取出 content
    content = getattr(chunk, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text") or "")
        return "".join(parts)

    return str(content) if content is not None else ""


def build_agent(db: Session, current_user: User):
    tools = build_tools(db=db, current_user=current_user)
    model = ChatOpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
        temperature=0,
        # 当前对话只保存正文；DeepSeek 的思考模式要求额外回传 reasoning_content。
        extra_body=(
            {"thinking": {"type": "disabled"}}
            if urlparse(settings.LLM_BASE_URL).hostname == "api.deepseek.com"
            else None
        ),
        streaming=True,  # 使用流式输出, stream_event 用于接收逐字返回的token
    ).bind_tools(tools)

    async def agent_node(state: MessagesState):
        """LangGragh 执行的工作流的节点"""
        # response = model.invoke(state["messages"])
        response = await model.ainvoke(state["messages"])
        # response = await model.astream(state["messages"])
        return {"messages": [response]}

    gragh = StateGraph(MessagesState)
    gragh.add_node("agent", agent_node)  # 调用大模型的节点
    gragh.add_node("tools", ToolNode(tools))  # tool call的节点
    gragh.add_edge(START, "agent")  # 流程的起点, call LLM
    gragh.add_conditional_edges(
        "agent", tools_condition
    )  # 判断是否有 tool_call, 有就继续call, 没有就END 输出
    gragh.add_edge("tools", "agent")  # agent查看tool调用的结果
    return gragh.compile()


# def run_agent(db: Session, current_user: User, data: ChatRequest):
#     """大模型对话"""
#     try:
#         if not data.messages:
#             raise BusinessException(message="对话内容为空")

#         history = _build_history(data)

#         agent = build_agent(db, current_user)
#         try:
#             result = agent.invoke(
#                 {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]},
#                 # Tools share this request's SQLAlchemy session; execute them sequentially.
#                 config={"recursion_limit": 10, "max_concurrency": 1},
#             )  # 设置对话循环的上限是10轮
#         except BusinessException:
#             raise
#         except Exception:
#             raise BusinessException(message="大模型调用失败，请稍后重试")

#         messages = result.get("messages") or []
#         if not messages:
#             raise BusinessException(message="大模型没有任何返回内容")

#         message = messages[-1]
#         if not isinstance(message, AIMessage) or message.tool_calls:
#             raise BusinessException(message="大模型没有返回有效的回复内容")

#         if message.invalid_tool_calls:
#             raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

#         content = message.content

#         # 处理字符串类型的回复
#         if isinstance(content, str):
#             content = content.strip()

#         # 处理列表类型的回复
#         elif isinstance(content, list):
#             content = "".join(
#                 (
#                     part
#                     if isinstance(part, str)
#                     else part.get("text", "") if isinstance(part, dict) else ""
#                 )
#                 for part in content
#             ).strip()

#         else:
#             content = ""

#         if re.search(r"<\s*/?\s*(?:tool_call|function)\b", content, re.IGNORECASE):
#             raise BusinessException(message="助手未能正确调用工具，请重试", code=502)

#         if content:
#             return content

#         raise BusinessException(message="大模型没有返回有效的回复内容")

#     except BusinessException as e:
#         yield {"type": "error", "message": e.message}
#     except Exception:
#         yield {"type": "error", "message": "大模型调用失败，请稍后重试"}


async def stream_agent(db: Session, current_user: User, data: ChatRequest):
    """
    生成器：边跑 agent 边 yield 事件，提供 SSE 输出给前端
    事件的类型: status | tool_start | tool_end | token | done | error
    """
    try:
        if not data.messages:
            raise BusinessException(message="对话内容为空")

        history = _build_history(data)

        agent = build_agent(db, current_user)
        inputs = {"messages": [SystemMessage(content=SYSTEM_PROMPT), *history]}

        yield {"type": "status", "message": "正在思考..."}

        async for event in agent.astream_events(
            inputs, version="v2", config={"recursion_limit": 10}
        ):
            kind = event.get("event")
            if kind == "on_tool_start":
                name = event.get("name") or ""  # tool的名称
                yield {
                    "type": "tool_start",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                }
            elif kind == "on_tool_end":
                name = event.get("name") or ""  # tool的名称
                yield {
                    "type": "tool_end",
                    "name": name,
                    "label": TOOL_LABELS.get(name, name),
                    "preview": _tool_output_preview(
                        (event.get("data") or {}).get("output")
                    ),
                }
            elif kind == "on_chat_model_stream":
                metadata = event.get("metadata") or {}
                if metadata.get("langgraph_node") not in (None, "agent"):
                    continue
                text = _chunk_text((event.get("data") or {}).get("chunk"))
                yield {"type": "token", "content": text}
        yield {"type": "done"}

    except BusinessException as e:
        yield {"type": "error", "message": e.message}
    except Exception:
        yield {"type": "error", "message": "大模型调用失败，请稍后重试"}
```

</details>

<details>
<summary><code>backend/data/config_global/agent_config.py</code>（2026-10-26）</summary>

```python
import json
from datetime import datetime
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from app.common.exceptions import BusinessException
from app.schemas.reservation import ReservationCreateRequest
from app.models.user import User
from app.services import equipment_service, kb_service, lab_service, reservation_service

SYSTEM_PROMPT = """你是智能实验室预约系统的 Agent，回答要简洁。
你可以：
1. 使用 search_lab_docs 查询实验室的规则、安全、开放时间等问题
2. 使用 list_open_labs / list_lab_equipments 查询真实的实验室和设备
3. 在用户进行预约确认后，使用 create_lab_reservation 来进行真实的预约写库
4. 使用 get_today 来进行日期的换算

## 必须遵守
工具必须通过接口提供的工具调用机制执行，不要把 <tool_call> 或 <function=...> 等标记作为回复内容。
工具名和参数以实际提供的工具定义为准，不要编造不存在的 search_for 等工具。
只有工具返回成功后，才能告诉用户预约已提交；工具返回错误时说明失败原因，不要声称成功。
当用户提到了 今天、明天、后天 等日期相关的问题，请先调用 get_today 来获取日期，**不要直接返回"我需要确定明天的具体日期"**

在提交预约之前必须向用户复述实验室ID与名称（或设备ID和名称）、日期、开始时间、结束时间。并得到用户确认再进行实际操作。
用户没说【确认】【确认预约】【就这样预约】等确定性回复之前，不要调用 create_lab_reservation。
工作流的确认环节里如果缺少了 lab_id，请先 list_open_labs 查到了 lab_id 再创建，不要瞎写。
工作流的确认环节里如果缺少了 equipment_id，请先 list_lab_equipments 查到了 equipment_id 再创建，不要瞎写。

预约成功后状态是待审核，必须管理员确认后实验室（或设备）才能使用。
不要瞎编数据库里没有的实验室或者设备信息。
如果是问开放时间或者实验室规则，优先调用 search_lab_docs，不要凭空回复。
"""

TOOL_LABELS = {
    "search_lab_docs": "检索实验室知识库",
    "list_open_labs": "查询开放的实验室",
    "list_lab_equipments": "查询实验室设备",
    "create_lab_reservation": "创建预约单",
    "get_today": "获取今天的日期",
}


def build_tools(db: Session, current_user: User):

    @tool
    def search_lab_docs(query: str) -> str:
        """根据用户的提问去检索知识库"""
        try:
            return kb_service.search(query) or "没有检索到相关的资料"
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def list_open_labs(keywords: str = "") -> str:
        """查询开放中的实验室"""
        try:
            keywords = keywords.strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def list_lab_equipments(lab_id: int, keywords: str = "") -> str:
        """查询隶属于实验室的设备"""
        try:
            keywords = keywords.strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, lab_id=int(lab_id), keywords=keywords
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return json.dumps(
                {"total": page.total, "equipments": rows}, ensure_ascii=False
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def create_lab_reservation(
        lab_id: int,
        date: str,
        start_time: str,
        end_time: str,
        equipment_id: int | None = None,
        remark: str | None = None,
    ) -> str:
        """创建预约"""
        try:
            data = ReservationCreateRequest(
                lab_id=lab_id,
                equipment_id=equipment_id,
                date=date,
                start_time=start_time,
                end_time=end_time,
                remark=remark,
            )
            reservation_service.create_reservation(db, current_user, data)

            return json.dumps(
                {
                    "ok": True,
                    "message": "预约已提交，请等待管理员审核",
                    "lab_id": lab_id,
                    "equipment_id": equipment_id,
                    "date": date,
                    "start_time": data.start_time,
                    "end_time": data.end_time,
                },
                ensure_ascii=False,
            )
        except BusinessException as exc:
            return json.dumps({"ok": False, "error": exc.message}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    @tool
    def get_today() -> str:
        """获取服务器当前日期，格式为 YYYY-MM-DD"""
        now = datetime.now()
        return now.strftime("%Y-%m-%d")

    return [
        search_lab_docs,
        list_open_labs,
        list_lab_equipments,
        create_lab_reservation,
        get_today,
    ]
```

</details>

<details>
<summary><code>frontend/src/api/ai.js</code>（2026-10-26）</summary>

```js
// import request from '@/utils/request'
import { getToken } from '@/utils/auth'

// export function chatApi(data) {
//   return request({
//     url: '/api/ai/chat',
//     method: 'post',
//     data,
//     timeout: 60000
//   })
// }

export async function chatStreamApi(data, onEvent) {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  const token = getToken()

  const res = await fetch(`${baseUrl}/api/ai/chat/stream`, {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })

  if (res.status === 401) {
    throw new Error('登录已失效，请重新登录')
  }

  if (!res.ok || !res.body) {
    throw new Error('流式接口请求失败')
  }
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    throw new Error('流式接口返回异常')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')

  const dispatchEvent = (chunk) => {
    const data = chunk
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
      .trim()

    if (!data || data === '[DONE]') return

    let event
    try {
      event = JSON.parse(data)
    } catch {
      throw new Error('流式回复格式错误，请重试')
    }
    onEvent(event)
  }

  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })

      // 每次收到数据就处理完整事件，保留跨网络数据块的残余内容。
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop()
      for (const chunk of chunks) dispatchEvent(chunk)

      if (done) {
        if (buffer.trim()) dispatchEvent(buffer)
        break
      }
    }
  } finally {
    reader.releaseLock()
  }
}
```

</details>

<details>
<summary><code>frontend/src/views/AIChat.vue</code>（2026-10-26）</summary>

```vue
<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>AI智能助手</span>
        </div>
      </template>
      <div
        ref="listRef"
        style="
          height: 480px;
          overflow-y: auto;
          padding: 8px 4px;
          background-color: #fafafa;
          border-radius: 6px;
        "
      >
        <div
          v-for="(item, index) in messages"
          :key="index"
          :style="{
            display: 'flex',
            justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '12px'
          }"
        >
          <div
            :style="{
              maxWidth: '70%',
              padding: '10px 12px',
              borderRadius: '8px',
              backgroundColor: item.role === 'user' ? '#409eff' : '#fff',
              color: item.role === 'user' ? '#fff' : '#333',
              lineHeight: '1.6',
              boxShadow: '0 1px 2px rgba(0 ,0, 0, 0.06)'
            }"
          >
            <!-- 当前进行中的一句话，如「正在查询开放实验室...」 -->
            <div
              v-if="item.role === 'assistant' && item.status"
              style="margin-bottom: 6px; font-size: 12px; color: #909399"
            >
              {{ item.status }}
            </div>

            <!-- 本轮已发生的过程列表，只展示不回传给后端 -->
            <div
              v-if="item.role === 'assistant' && item.steps?.length"
              style="margin-bottom: 8px; font-size: 12px; color: #909399; line-height: 1.5"
            >
              <div v-for="(step, i) in item.steps" :key="i">· {{ step }}</div>
            </div>

            <div v-html="parseMarkdown(item.content)"></div>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="问问实验室怎么预约、开放时间..."
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.stop
        ></el-input>
        <el-button type="primary" :loading="loading" @click="handleSend">发送</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify' // 过滤危险的 HTML，防止 XSS 攻击
import { chatStreamApi } from '@/api/ai'
import { ElMessage } from 'element-plus'

// 将 markdown 字符串转换为安全的 HTML 字符串
const parseMarkdown = (text) => {
  if (!text) return ''
  // 使用 marked 解析，然后用 DOMPurify 清理
  const rawHtml = marked.parse(text)
  return DOMPurify.sanitize(rawHtml)
}

const messages = ref([
  {
    role: 'assistant',
    content:
      '你好, 我是实验室助手。你可以向我提问怎么预约、取消实验室或者设备, 也可以问我现在系统所存在的实验室与设备的具体信息, 还能让我帮你预约实验室或设备。'
  }
])

const input = ref('')
const loading = ref(false)
const listRef = ref()

const scrollToBottom = () => {
  nextTick(() => {
    const elem = listRef.value
    if (elem) elem.scrollTop = elem.scrollHeight
  })
}

// const handleSend = async () => {
//   const text = input.value.trim()
//   if (!text || loading.value) return
//   messages.value.push({ role: 'user', content: text })
//   input.value = ''
//   loading.value = true
//   scrollToBottom()
//   try {
//     const history = messages.value.filter(
//       (item) => item.role === 'user' || item.role === 'assistant'
//     )
//     const res = await chatApi({ messages: history })
//     if (res.code === 200) {
//       messages.value.push(res.data)
//       scrollToBottom()
//     }
//   } catch {
//     // 请求失败时由请求拦截器提示错误。
//   } finally {
//     loading.value = false
//   }
// }
const handleSend = async () => {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  // 必须用 reactive：普通对象 push 后再改字段，视图可能不更新
  const assistant = reactive({
    role: 'assistant',
    content: '', // 正文：靠 token 一点点拼
    status: '正在思考...', // 当前状态文案
    steps: [] // 过程流水，不进下次 history
  })
  messages.value.push(assistant)

  const history = messages.value
    .filter((item) => item.role === 'user' || item.role === 'assistant')
    .slice(0, -1) // 去掉刚插入的空助手，避免把空 content 送回去
    // 只保留 role/content; status, steps 丢掉
    .map(({ role, content }) => ({ role, content }))

  try {
    // 第二个参数是回调：每解析出一条 SSE 事件就进一次
    await chatStreamApi({ messages: history }, (evt) => {
      if (evt.type === 'status') {
        assistant.status = evt.message || '正在思考...'
      } else if (evt.type === 'tool_start') {
        const label = evt.label || evt.name || '工具'
        assistant.status = `正在${label}...`
        assistant.steps.push(`开始: ${label}`)
      } else if (evt.type === 'tool_end') {
        const label = evt.label || evt.name || '工具'
        assistant.status = `${label}完成`
        assistant.steps.push(`完成: ${label}`)
        if (evt.preview) {
          assistant.steps.push(`输出结果: ${evt.preview}`)
        }
      } else if (evt.type === 'token') {
        assistant.content += evt.content || '' // 打字机：追加，不是覆盖
        assistant.status = '' // 开始出字后清掉「正在...」，避免叠在一起
      } else if (evt.type === 'done') {
        assistant.status = ''
        // 注意：不要在这里再 append 一段完整正文，否则会双份
      } else if (evt.type === 'error') {
        assistant.status = ''
        if (!assistant.content) {
          assistant.content = evt.message || '请求失败'
        }
        ElMessage.error(evt.message || '请求失败')
      }
      scrollToBottom()
    })
  } catch (err) {
    assistant.status = ''
    if (!assistant.content) {
      assistant.content = err.message || '网络异常'
    }
    ElMessage.error(err.message || '网络异常')
  } finally {
    loading.value = false
    assistant.status = ''
    scrollToBottom()
  }
}
</script>
```

</details>

<details>
<summary><code>frontend/tests/ai.test.js</code>（2026-10-26）</summary>

```js
import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'

let server
let chatStreamApi
const encoder = new TextEncoder()

before(async () => {
  server = await createServer({
    configFile: false,
    envFile: false,
    root: fileURLToPath(new URL('..', import.meta.url)),
    resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } },
    server: { middlewareMode: true, hmr: false, watch: null },
    optimizeDeps: { noDiscovery: true },
    logLevel: 'error'
  })
  ;({ chatStreamApi } = await server.ssrLoadModule('/src/api/ai.js'))
})

after(async () => {
  await server?.close()
})

const mockResponse = (t, response) => {
  t.mock.method(globalThis, 'fetch', async () => response)
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: () => 'test-token' }
  })
  t.after(() => {
    if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor)
    else delete globalThis.localStorage
  })
}

test(
  'delivers replies before the connection closes and sends authenticated history',
  { timeout: 5000 },
  async (t) => {
    let controller
    const stream = new ReadableStream({
      start(value) {
        controller = value
      }
    })
    mockResponse(t, new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } }))
    const firstEvent = Promise.withResolvers()
    const history = { messages: [{ role: 'user', content: '你好' }] }
    const pending = chatStreamApi(history, firstEvent.resolve)

    controller.enqueue(encoder.encode('data: {"type":"token","content":"你好"}\n\n'))
    try {
      assert.deepEqual(await firstEvent.promise, { type: 'token', content: '你好' })
      const [url, options] = fetch.mock.calls[0].arguments
      assert.equal(url, '/api/ai/chat/stream')
      assert.equal(options.headers.Authorization, 'Bearer test-token')
      assert.deepEqual(JSON.parse(options.body), history)
    } finally {
      controller.close()
      await pending
    }
  }
)

test('preserves events and Chinese text across byte boundaries and CRLF frames', async (t) => {
  const expected = [
    { type: 'status', message: '正在思考...' },
    { type: 'tool_start', label: '查询实验室' },
    { type: 'tool_end', preview: '有两间实验室' },
    { type: 'token', content: '你好，实验室助手' },
    { type: 'done' }
  ]
  const wire =
    ': keep-alive\r\n\r\n' +
    expected.map((event) => `data: ${JSON.stringify(event)}\r\n\r\n`).join('') +
    'data: [DONE]\r\n\r\n'
  const stream = new ReadableStream({
    start(controller) {
      for (const byte of encoder.encode(wire)) controller.enqueue(Uint8Array.of(byte))
      controller.close()
    }
  })
  mockResponse(t, new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } }))
  const events = []
  await chatStreamApi({}, (event) => events.push(event))
  assert.deepEqual(events, expected)
  assert.equal(stream.locked, false)
})

test('delivers a final event without a trailing blank line', async (t) => {
  mockResponse(
    t,
    new Response('data: {"type":"error","message":"模型不可用"}', {
      headers: { 'Content-Type': 'text/event-stream' }
    })
  )
  const events = []
  await chatStreamApi({}, (event) => events.push(event))
  assert.deepEqual(events, [{ type: 'error', message: '模型不可用' }])
})

test('reports an expired login', async (t) => {
  mockResponse(t, new Response(null, { status: 401 }))
  await assert.rejects(
    chatStreamApi({}, () => {}),
    /登录已失效/
  )
})

test('reports responses without an SSE content type', async (t) => {
  mockResponse(t, new Response(new Uint8Array()))
  await assert.rejects(
    chatStreamApi({}, () => {}),
    /流式接口返回异常/
  )
})

test('reports malformed events and releases the stream', async (t) => {
  const response = new Response('data: invalid-json\n\n', {
    headers: { 'Content-Type': 'text/event-stream' }
  })
  mockResponse(t, response)
  await assert.rejects(
    chatStreamApi({}, () => {}),
    /流式回复格式错误/
  )
  assert.equal(response.body.locked, false)
})

test('propagates event handler errors to the send handler', async (t) => {
  mockResponse(
    t,
    new Response('data: {"type":"done"}\n\n', {
      headers: { 'Content-Type': 'text/event-stream' }
    })
  )
  const error = new Error('handler failed')
  await assert.rejects(
    chatStreamApi({}, () => {
      throw error
    }),
    error
  )
})
```

</details>

<a id="19-code-flow"></a>

## 16. 整项目执行路线：从页面操作到数据库再返回

路线起点：2026-10-21，结合后续 AI 和后台扫描说明启动变化。前面的功能章节侧重模块内部实现，本章从网页操作串起文件、函数、请求和返回值。README 的第 15 节提供图形速查，AI 工具调用路线见第 15.3 节。

本章速查：[审核通过的十二步](#19-audit-flow) · [账号与个人资料](#19-account-flow) · [用户和资源管理](#19-management-flow) · [学生浏览与预约](#19-student-flow) · [失败返回路线](#19-error-flow) · [实际跟踪方法](#19-debug-flow)。

### 16.1 先区分四种不同的“流通”

| 现象      | 当前项目中的例子                                        | 实际发生的事情                                             |
| --------- | ------------------------------------------------------- | ---------------------------------------------------------- |
| 导入模块  | import { auditReservationApi } from '@/api/reservation' | 取得另一个模块导出的函数；这一行不等于发审核请求           |
| 调用函数  | auditReservationApi(row.id, 1)                          | JavaScript 调用这个函数，传入 ID 和审核状态                |
| HTTP 请求 | PUT /api/reservation/42/audit                           | 浏览器把方法、地址、请求头和 JSON 发给后端，由后端匹配接口 |
| 页面导航  | router.push('/manager/myreservation')                   | Vue Router 改变当前地址，显示对应页面组件                  |

你说的“从 AuditReservation.vue 跳到 reservation.js”，在代码层面通常属于**函数调用**。管理员点击“通过”时，页面地址保持不变；随后发送 HTTP 请求，操作成功后重新查询列表。

也要区分“打开一个文件阅读”和“程序执行一个函数”：IDE 的转到定义只帮助你找到代码，运行中的程序并不会打开编辑器里的文件。

下面使用“完整文件路径 + 函数名/模板定位词”。在 VS Code 中按 Ctrl+P 输入路径打开文件，再搜索函数名。相同名字可能出现在不同目录，例如前后端都有 auth、user、reservation，因此阅读时要看完整路径。

### 16.2 启动阶段：两套程序分别准备好

2026-10-25：AI 路由调用 agent_service。导入 kb_service 时不立即加载模型；lifespan 根据 KB_WARMUP_ON_STARTUP 决定是否等待本地模型/集合预热（源码默认 True），之后创建扫描任务。关闭预热时首次实际检索再加载；详细见[当前生命周期](#kb-startup-lifecycle)和[知识库本地缓存](#kb-local-cache)。

**前端启动路线。**

```text
frontend/package.json 中的 dev 脚本
  → npm run dev 启动 Vite
  → Vite 读取 frontend/vite.config.js 和对应模式的环境配置
  → 浏览器打开前端地址，取得 frontend/index.html
  → <script type="module" src="/src/main.js">
  → frontend/src/main.js
      createApp(App)
      app.use(router)
      app.use(ElementPlus, ...)
      注册图标组件
      app.mount('#app')
  → frontend/src/App.vue 的 <router-view />
  → frontend/src/router/index.js 匹配当前地址
  → /login 显示 Login.vue
     /manager/... 显示 Layout.vue，再由里面的 <router-view /> 显示子页面
```

index.html 的 `<div id="app"></div>` 是 Vue 挂载界面的位置。main.js 负责建立应用，不包含每个业务按钮的处理逻辑；具体业务在 views 下的组件中。

router/index.js 的 beforeEach 先用 utils/auth.js.getToken() 读取本地 token。登录页和注册页直接放行，其他页面没有 token 就转到 /login。这里仅判断本地是否存在 token；token 是否真实有效，还需要后端接口验证。

用户进入 /manager/home 后，Home.vue 从 useUser() 读取 userInfo 显示欢迎语。当前 Home.vue 没有在加载时重新请求个人信息，不要为它画出不存在的首页查询接口。

**后端启动路线。**

```text
在 backend 目录运行 uvicorn app.main:app
  → 导入 backend/app/main.py，取得名为 app 的 FastAPI 对象
  → 导入链准备配置、数据库、模型和接口
      config.py：Settings() 取得数据库/JWT/LLM 配置，准备 uploads 目录
      database.py：create_engine(settings.DATABASE_URL)、SessionLocal、Base
      models/*.py：注册表、字段与关联关系
      api/__init__.py：建立 /api 总路由，include_router 各功能路由
      AI 当前执行依赖：agent_service → agent_config → kb_service（导入不立即加载模型）
  → main.py：Base.metadata.create_all(bind=engine)
  → main.py：建立 app，注册中间件、总路由、异常处理器、/uploads 静态目录
  → lifespan：开关为 true 时等待本地模型/集合预热，异常记日志后继续
  → lifespan 创建预约扫描任务：立即扫描，随后每轮结束等待 60 秒
  → Uvicorn 接收 HTTP 请求，交给这个 app
  → 关闭时 lifespan 取消扫描任务并等待退出
```

这是依赖关系的梳理，不是把互相导入的文件硬排成每次都相同的逐行清单。Python 在导入时执行模块顶层代码；后续每次请求不会重新执行整份 main.py，也不会每次都重新创建表。

`@router.put(...)` 等装饰器把“方法和路径对应哪个函数”登记到路由中。登记时不会替用户进行一次审核，真正收到匹配请求并完成参数、依赖处理后，才调用对应接口函数。

数据库模型定义也不是数据库里的一条数据：models/reservation.py 描述表结构，而真正的预约记录由 create_reservation 等运行时业务函数写入。

### 16.3 请求阶段：正向发送与反向返回

```mermaid
flowchart TD
    U["用户操作 / 页面挂载"] --> V["views/*.vue：事件函数 / load"]
    V --> A["frontend/src/api/*.js：构造请求"]
    A --> R["utils/request.js：请求拦截器"]
    R --> H["HTTP：方法、URL、头、查询参数或请求体"]
    H --> P["开发环境 /api 代理 → FastAPI"]
    P --> D["schemas 校验；按接口声明解析 dependencies 与 get_db"]
    D --> API["backend/app/api/*.py：接口函数"]
    API --> S["services/*_service.py：业务判断"]
    S --> DB[(数据库)]
    DB --> S
    S --> O["接口 Response.success → JSON"]
    O --> I["request.js：响应拦截器"]
    I --> V2["await 取得结果 → 更新页面变量"]
    V2 --> SHOW["Vue 更新表格、表单、菜单或提示"]
    D -.失败.-> E["common/exceptions.py → 错误响应"]
    S -.失败.-> E
    E --> I
```

这张图是大多数业务接口的通路。两个明确的例外是：GET /api/user/me 直接使用认证依赖取得的用户；POST /api/files/upload 在接口函数内写磁盘，没有 files_service，也没有文件数据库表。

在任何具体功能中，都可以先问六个问题：触发点是什么、调用哪个前端 API、发什么 HTTP、进入哪个后端函数、改什么数据、页面如何接住结果。下面逐个回答。

<a id="19-audit-flow"></a>

### 16.4 完整例子：管理员点击某条预约的“通过”

假设管理员已经登录，表格中有一条 `id=42、status=0` 的预约。42 只是说明流程的示例 ID。

#### 第一步：先有列表数据，按钮才有 row

打开 [frontend/src/views/AuditReservation.vue](frontend/src/views/AuditReservation.vue)，定位 onMounted 和 load：

```js
onMounted(() => {
  load();
});
```

load 调用 getReservationPageList(params)，把返回列表赋给 tableData.value。模板里的 `<el-table :data="tableData">` 据此生成行；作用域插槽 `#default="{ row }"` 取得当前这一行。

因此 row.id 来自此前列表接口的响应，不是点击按钮时凭空生成的数字。列表的查询、名称组装路线在第 13.6～13.9 节已经逐层解释。

#### 第二步：按钮把当前行和目标状态交给页面函数

同一文件中定位：

```vue
<el-button type="success" text bg @click="handleAudit(row, 1)">通过</el-button>
```

`@click` 把点击事件绑定到表达式。点击后相当于调用 `handleAudit(当前行对象, 1)`：第一个参数用于取得预约 ID 和提示名称，第二个参数 1 表示通过。按钮放在 `row.status === 0` 的条件模板里。

#### 第三步：handleAudit 先确认，再调用导入的 API 函数

页面 script setup 中有：

```js
import { auditReservationApi, getReservationPageList } from "@/api/reservation";
```

vite.config.js 把 @ 配置为 frontend/src 的别名，所以这个导入指向 [frontend/src/api/reservation.js](frontend/src/api/reservation.js)。花括号里的名字需要与该文件的具名导出对应。

页面的实际函数：

```js
const handleAudit = async (row, status) => {
  try {
    const action = status === 1 ? "通过" : "拒绝";
    await ElMessageBox.confirm(
      `确认 ${action} [${row.lab_name}] 的审核?`,
      "审核",
      {
        type: "warning",
      },
    );
    const res = await auditReservationApi(row.id, status);
    if (res.code === 200) {
      ElMessage.success(`审核${action}`);
      await load();
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
};
```

执行到确认框的 await 时，当前函数等待用户选择。确认后继续调用 auditReservationApi；取消或关闭确认框会进入 catch，这次不会发出审核请求。

`await auditReservationApi(...)` 会让这个异步函数等待结果，并不是让整个浏览器停止响应。下面先沿着这次调用向后端追踪，稍后再回到 `if (res.code === 200)`。

#### 第四步：reservation.js 把参数变成 HTTP 请求配置

在前端 API 文件中定位 auditReservationApi：

```js
export function auditReservationApi(id, status) {
  return request({
    url: `/api/reservation/${id}/audit`,
    method: "put",
    data: { status },
  });
}
```

传入 42、1 后，配置的含义是：

```text
method = PUT
url = /api/reservation/42/audit
data = { status: 1 }
```

id 被放进 URL；status 被放进请求体。这里没有把整行 row、lab_name 或管理员角色一起发送给后端。`return` 把 request 返回的 Promise 交回调用者，页面才可以 await 它。

#### 第五步：request 就是 request.js 导出的 service

前端 API 文件顶部的：

```js
import request from "@/utils/request";
```

对应 [frontend/src/utils/request.js](frontend/src/utils/request.js) 最后的 `export default service`。request 是这里为默认导出起的本地名字，调用它就是调用配置好的 Axios 实例。

请求拦截器从 [frontend/src/utils/auth.js](frontend/src/utils/auth.js) 的 getToken() 取得 localStorage 中的 token，放进 `config.headers.Authorization`，同时记录当前 `_authVersion`。最终的请求大致如下：

```http
PUT /api/reservation/42/audit
Authorization: Bearer <当前登录token>
Content-Type: application/json

{"status": 1}
```

Axios 完成 JSON 序列化和网络发送。前端当前登录者的身份凭证在请求头里，而不是在 status 中。

#### 第六步：开发代理把 HTTP 交给后端

在 API 基地址留空并使用 Vite 开发代理的配置下，浏览器请求前端源的 /api/reservation/42/audit。[frontend/vite.config.js](frontend/vite.config.js) 的 /api 代理将它转发到：

```text
http://127.0.0.1:8000/api/reservation/42/audit
```

代理转发时保留 /api 前缀，当前没有 rewrite 删除它。Vite 不执行审核业务，数据库写入仍由 Python 后端完成。生产环境需要相应的 API 地址或反向代理，不能把 Vite 开发代理当作后端业务的一部分。

#### 第七步：后端用“方法 + 路径”找到接口

前缀的来源：

```text
backend/app/main.py：app.include_router(api)
backend/app/api/__init__.py：APIRouter(prefix="/api")，注册 reservation_router
backend/app/api/reservation.py：APIRouter(prefix="/reservation")
同文件装饰器：@router.put("/{reservation_id}/audit")
合成：PUT /api/reservation/{reservation_id}/audit
```

所以请求中的 42 对应路径参数 reservation_id。HTTP 不携带“请执行某个 Python 文件”的命令，FastAPI 按启动时注册的路由关系定位函数。

#### 第八步：参数与依赖准备好，才执行接口函数体

在 [backend/app/api/reservation.py](backend/app/api/reservation.py) 中定位 audit_reservation。它声明：

```python
def audit_reservation(
    reservation_id: int,
    data: AuditReservationRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    reservation_service.audit_reservation(
        reservation_id=reservation_id,
        db=db,
        status=data.status,
    )
    return Response.success()
```

在进入函数体前，框架需要处理这些输入：

| 参数           | 从哪里得到                                                             | 在此例中的含义                           |
| -------------- | ---------------------------------------------------------------------- | ---------------------------------------- |
| reservation_id | URL 路径                                                               | 整数 42                                  |
| data           | JSON 请求体，经 schemas/reservation.py 的 AuditReservationRequest 校验 | 模型对象，data.status 为 1               |
| current_user   | dependencies/auth.py 的 get_current_admin                              | 数据库查到且已验证权限的管理员 User 对象 |
| db             | database.py 的 get_db                                                  | 当前请求使用的 SQLAlchemy Session        |

这张表说明依赖关系，不规定这些输入严格按表格从上到下处理。关键是：校验或依赖出错时，不会继续执行正常的审核函数体。

管理员依赖内部的路线是：

```text
OAuth2PasswordBearer 从 Authorization 提取 token
  → get_current_user
      utils/jwt.py：decode_access_token 校验签名和有效期，取得 user_id
      db.query(User) 查询 users 表
      检查用户存在、账号启用
  → get_current_admin 检查 current_user.role == 'admin'
  → 返回管理员 User 对象
```

get_db 通过 SessionLocal 创建会话，用 yield 提供给请求处理，最终 close 释放会话资源。它没有替每个写入操作自动 commit；提交在具体业务函数中。

#### 第九步：API 函数调用 service 中的另一个同名函数

接口函数执行：

```python
reservation_service.audit_reservation(
    reservation_id=reservation_id,
    db=db,
    status=data.status,
)
```

跳到 [backend/app/services/reservation_service.py](backend/app/services/reservation_service.py) 搜索 `def audit_reservation`。前面的 `reservation_service.` 指明从哪个模块取函数，因此它不会递归调用当前 API 文件里的同名函数。

service 接收到的是 Python 对象和整数，不是浏览器的原始 HTTP 字节。实际业务代码是：

```python
def audit_reservation(db: Session, reservation_id: int, status: int):
    """管理员审核预约"""
    if status not in [1, 2]:
        raise BusinessException(message="审核状态错误")
    item = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not item:
        raise BusinessException(message="预约记录不存在")
    if item.status != 0:
        raise BusinessException(message="当前状态不支持审核")
    item.status = status
    db.commit()
```

#### 第十步：ORM 把对象操作变成数据库操作

Reservation 来自 [backend/app/models/reservation.py](backend/app/models/reservation.py)，映射到 reservation 表。按 ID 查询得到 item，当前 item.status 必须为 0；设置 item.status=1 后，commit 将修改提交。

可以用下面的简化 SQL 理解意图，但它不是抓取到的完整 SQL 日志，实际更新还可能涉及 update_time：

```sql
SELECT * FROM reservation WHERE id = 42;
UPDATE reservation SET status = 1 WHERE id = 42;
COMMIT;
```

这个当前实现的更新没有把 status=0 放进数据库更新条件，校验发生在此前的 Python 读取上。因此这条路线讲的是正常顺序执行；同时取消与审核的竞争问题仍见第 13.22 节，不能因为出现 commit 就认为所有并发都已安全。

#### 第十一步：结果沿着调用关系返回

service 正常结束，没有显式返回详情；API 接着执行 Response.success()。[backend/app/common/response.py](backend/app/common/response.py) 构造响应对象，FastAPI 将它序列化为 JSON：

```json
{ "code": 200, "message": "请求成功", "data": null }
```

HTTP 响应返回后进入前端 request.js 的响应拦截器。拦截器拿到的是 Axios Response，通过 `const data = res.data` 取出正文，最后 return data。

于是 AuditReservation.vue 中这句 await 完成：

```js
const res = await auditReservationApi(row.id, status);
```

这里的 res 已经是上面 JSON 对应的 JavaScript 对象。因此用 res.code 判断业务结果，不需要再写 res.data.code。审核的 res.data 为 null，也不应该期待里面自动带回一整页最新预约。

#### 第十二步：页面另发 GET，重新绘制列表

审核函数成功分支执行 ElMessage.success，然后 await load。第二次请求路线是：

```text
AuditReservation.vue：load()
  → frontend/src/api/reservation.js：getReservationPageList(params)
  → request.js → GET /api/reservation/list
  → backend/app/api/reservation.py：get_reservation_page_list
  → backend/app/services/reservation_service.py：get_reservation_page_list
  → 角色过滤、status 过滤、count、分页、名称组装
  → PageResponse(list, total)
  → Response.success(data=分页结果) → JSON → 响应拦截器
  → 页面 tableData.value = res.data?.list
         total.value = res.data?.total
  → Vue 更新表格和分页总数
```

页面默认 status=0；ID 42 已变为 1，不再满足筛选，于是从待审核表格消失。它仍在数据库中，切换为“已通过”后可再查到。

因此正常点击一次“通过”并确认，通常对应一个 PUT 审核请求和紧随其后的一个 GET 列表请求；初次进入页面的 GET 是更早的一次请求。没有 router.push，当前页面地址也没有因审核而改变。当前 pageSize/page_size 的差异仍保留，详见第 13.12 节。

<a id="19-account-flow"></a>

### 16.5 注册与登录：从账号表单到登录状态

**注册的执行路线。**

```text
frontend/src/views/Register.vue
  <el-form @submit.prevent="register">，提交按钮触发表单提交
  → register() 检查 loadingValue、执行 formRef.validate()
  → frontend/src/api/auth.js：registerApi(form)
  → request.js → POST /api/auth/register
  → backend/app/api/auth.py：register(data: RegisterRequest, db)
  → backend/app/services/auth_service.py：register(db, data)
      查 users.username 是否重复
      utils/password.py：hash_password(data.password)
      创建 User，role='student'
      db.add → commit；唯一约束失败时 rollback 并给出业务错误
  → Response.success(message='注册成功')
  → request.js 返回正文
  → Register.vue：提示成功 → router.push('/login')
```

`@submit.prevent` 的 prevent 阻止表单原生提交造成整页刷新，改由 register 函数负责发送 API 请求。页面的 confirmPassword 用来检查两次密码一致；RegisterRequest 没有这个字段，当前默认模型配置会忽略这个额外字段，数据库也不保存确认密码。

**登录的执行路线。**

```text
frontend/src/views/Login.vue：表单 @submit.prevent="login"
  → login() 校验 form
  → frontend/src/api/auth.js：loginApi(form)
  → request.js → POST /api/auth/login
  → backend/app/api/auth.py：login，接收 LoginRequest
  → backend/app/services/auth_service.py：login
      查询 User → utils/password.py.verify_password
      检查账号启用 → utils/jwt.py.create_access_token(user.id)
      返回 LoginResponse(token, user=UserResponse)
  → API：Response.success(message='登录成功', data=result)
  → 页面取得 res.data.token、res.data.user
  → frontend/src/utils/user.js：useUser().saveLoginData(res.data)
      utils/auth.js.setToken → localStorage 保存 token，增加 authVersion
      utils/auth.js.setUserInfo → localStorage 保存用户 JSON
      userInfo.value = data.user → 更新共享响应式状态
  → Login.vue：router.replace('/manager/home')，检查导航结果
  → Layout.vue 显示角色菜单，Home.vue 显示欢迎信息
```

登录这一步才有页面导航；审核请求成功后的 load 则只有重新请求数据。两者都调用了后端，但最终页面动作不同。

token 和用户 JSON 都由前端保存；后端没有因为 saveLoginData 而再次写数据库。后续接口身份检查会验证 token 并重新查询 users，所以浏览器里显示的角色不能代替后端权限判断。

### 16.6 个人资料查询、修改与共享显示

从 Layout.vue 的下拉菜单选择“个人信息”，先触发 `@command="handleCommand"`，handleCommand 收到 profile，调用 router.push('/manager/profile')，路由显示 Profile.vue。

**查询时：**

```text
frontend/src/views/Profile.vue：onMounted → loadUserInfo()
  → frontend/src/api/user.js：getUserInfo()
  → GET /api/user/me
  → backend/app/dependencies/auth.py：get_current_user 查询并验证用户
  → backend/app/api/user.py：get_user_info(current_user)
      UserResponse.model_validate(current_user)
      Response.success(data=用户响应模型)
  → request.js → Profile.vue
      Object.assign(form, res.data)
  → v-model 绑定的输入框显示用户资料
```

这里没有调用 user_service.get_user_info。虽然该 service 函数存在，当前 API 选择直接转换 current_user。画执行路线必须沿调用点核对，不能因为文件中有某函数就把它放到路线里。

另一个同名函数要区分：`frontend/src/api/user.js.getUserInfo()` 发 HTTP 查询；`frontend/src/utils/auth.js.getUserInfo()` 只读取 localStorage。Profile 使用的是前者，useUser 初始化共享状态时使用的是后者。

**保存时：**

```text
Profile.vue：表单 @submit.prevent="handleSubmit"
  → handleSubmit 校验表单 → api/user.js.updateUserInfo(form)
  → PUT /api/user/me
  → api/user.py.update_user_info，参数为 UserUpdateRequest
  → user_service.py.update_user_info(db, current_user, data)
      model_dump(exclude_none=True, exclude={'role', 'status'})
      setattr 更新允许字段 → commit → refresh
      返回 UserResponse
  → Response.success(data=res) → request.js → Profile.vue
  → useUser().updateUser(res.data)
      setUserInfo 更新 localStorage
      userInfo.value 更新共享响应式对象
  → Layout.vue 的头像/名称及 Home.vue 的欢迎语随状态更新
```

个人资料里的用户名与角色显示并不意味着可以通过这个接口修改它们。username 不在 UserUpdateRequest 中，role/status 又被个人资料 service 排除。管理员更新他人的信息走另一个接口，见第 16.9 节。

### 16.7 图片：选择文件、上传、保存地址和读取图片

头像在 Profile.vue，实验室图片在 Lab.vue，设备图片在 Equipment.vue。这三个页面都连接到相同的上传 API，但业务字段不同。

| 阶段     | 位置与定位词                                                   | 数据变化                                          |
| -------- | -------------------------------------------------------------- | ------------------------------------------------- |
| 选择     | 页面 el-upload 的 before-upload / beforeAvatarUpload           | 浏览器 File 对象，检查图片类型和大小              |
| 上传函数 | 页面 :http-request="handleFileUpload"                          | 从组件参数中取出 file                             |
| 构造请求 | frontend/src/api/files.js：uploadFileApi                       | FormData.append('file', file)                     |
| 后端接收 | backend/app/api/files.py：upload(file: UploadFile = File(...)) | Multipart 文件变成 UploadFile                     |
| 保存磁盘 | 同一个 upload 函数                                             | 检查扩展名和大小，生成 disk_name，写入 UPLOAD_DIR |
| 返回地址 | schemas/files.py 的 FileResponse，经 Response.success          | data.url 为 /uploads/文件名                       |
| 页面预览 | handleFileUpload 成功分支                                      | Profile 写 form.avatar；Lab/Equipment 写 form.img |
| 业务保存 | 页面另一次表单提交                                             | 把该 URL 放进个人资料、实验室或设备更新/创建请求  |
| 展示图片 | img 的 src 等图片绑定                                          | 浏览器自行 GET /uploads/文件名，取得图片内容      |

上传路线没有单独的 files_service，也没有把图片字节放入用户表。上传后，文件已经在磁盘上，但用户/资源资料尚未因这一步自动保存。必须继续点击表单保存，URL 才写进相应数据库字段。

图片读取走的是：

```text
浏览器 <img src="/uploads/xxx.jpg">
  → 开发环境 Vite 的 /uploads 代理
  → backend/app/main.py 中 app.mount('/uploads', StaticFiles(...))
  → 读取 backend/uploads/xxx.jpg
  → 返回图片内容给浏览器
```

它不调用 uploadFileApi，也不进入 Axios 的响应拦截器。`/api/files/upload` 负责接收新文件，`/uploads/...` 负责读取已有文件，是两种独立的 HTTP 路线。当前上传接口未声明登录依赖，不能因前端使用了统一 request 就认为后端已校验登录。

### 16.8 修改密码与退出登录

**修改密码的路线。** 在 Layout.vue 的下拉菜单选择 password，handleCommand 导航到 /manager/password，显示 [frontend/src/views/Password.vue](frontend/src/views/Password.vue)。

```text
Password.vue：表单 @submit.prevent="handleSubmit"
  → handleSubmit() 校验旧密码、新密码和确认密码
  → frontend/src/api/user.js：updatePassword({
        old_password: form.oldPassword,
        new_password: form.newPassword
    })
  → request.js → PUT /api/user/password
  → backend/app/api/user.py：update_password
      PasswordUpdateRequest 解析请求体，get_current_user 验证登录
  → backend/app/services/user_service.py：update_password
      verify_password 检查旧密码
      拒绝新旧密码相同
      hash_password 生成新密码哈希
      user.password = 新哈希 → commit → refresh
  → Response.success() → 页面 res.code === 200
  → utils/auth.js.logout() → router.push('/login')
```

这里前端控件字段是 oldPassword/newPassword，而接口字段是 old_password/new_password，映射发生在 handleSubmit 传参时，不是框架自动把所有驼峰名转换成下划线名。confirmPassword 只参与页面校验，没有放进这次请求体。

**普通退出的路线。**

```text
Layout.vue：下拉菜单 command='logout'
  → handleCommand('logout')
  → frontend/src/utils/auth.js：logout()
      removeToken()：删除 localStorage token，增加 authVersion
      removeUserInfo()：删除 localStorage userInfo
  → router.push('/login')
```

当前没有向后端发送 logout 请求，也没有服务端 token 撤销表。logout 本身只清理存储，没有直接把 utils/user.js 的共享 userInfo.value 设为 null；重新登录时 saveLoginData 会再更新它。不要把“清理 localStorage”“更新内存响应式变量”“使服务端旧凭证失效”画成同一个动作。

<a id="19-management-flow"></a>

### 16.9 管理员用户列表、创建、编辑与删除

入口是 Layout.vue 的 /manager/user 菜单，页面为 [frontend/src/views/User.vue](frontend/src/views/User.vue)。下面 API 列的前端函数均在 [frontend/src/api/user.js](frontend/src/api/user.js)，后端接口均在 [backend/app/api/user.py](backend/app/api/user.py)，业务函数均在 [backend/app/services/user_service.py](backend/app/services/user_service.py)。

| 网页触发点 → 页面函数                                        | 前端 API 函数   | HTTP                       | 后端接口函数 → service 函数        |
| ------------------------------------------------------------ | --------------- | -------------------------- | ---------------------------------- |
| onMounted、查询、翻页 → load；查询先由 handleSearch 重置页码 | getUserPageList | GET /api/user/list         | get_user_list → get_user_page_list |
| 新增按钮 → handleCreate；填完表单提交 → handleSave           | createUserApi   | POST /api/user             | create_user → create_user          |
| 编辑按钮 → handleEdit(row)；提交 → handleSave                | updateUserApi   | PUT /api/user/{user_id}    | update_user → update_user          |
| 删除按钮 → handleDelete(row)，确认后                         | deleteUserApi   | DELETE /api/user/{user_id} | delete_user → delete_user          |

**列表。** load 构造 `{ page, page_size: params.pageSize, keywords }`；后端服务按关键词查询 users，统计总数、排序和分页，再将每个 User 转为 UserResponse，返回 PageResponse。页面从 res.data.list、res.data.total 更新 tableData 和 total。所有用户管理接口都使用 get_current_admin。

**新增。** handleCreate 调用 resetForm、打开 dialogVisible，再清除校验提示。这一步只是改页面变量；不会创建用户。真正点击表单提交时，handleSave 校验表单，把 `{ id, username, password, ...userData }` 解构出来，id 为空就调用 createUserApi。后端检查用户名、生成密码哈希、构造 User、commit，再返回不含密码哈希的 UserResponse。成功后页面关闭弹窗并 load 查询新列表。

**编辑。** handleEdit(row) 用当前列表行回填 form，并不是调用单独的用户详情接口。handleSave 发现 id 存在，就调用 updateUserApi(id, userData)。这个分支不把 username、password 一起提交；后端 UserUpdateRequest 也没有这两个字段。管理员编辑用户与用户自己修改密码是两条不同路线。

**删除。** handleDelete 先等待确认，再调用 deleteUserApi(row.id)。service 检查不能删除当前登录账号，并检查是否有预约历史；允许时 db.delete/commit，失败时抛业务异常。只有 code=200 才提示成功并 load，取消确认框则不发 DELETE。

### 16.10 实验室管理：相同界面模式，换成实验室数据

页面为 [frontend/src/views/Lab.vue](frontend/src/views/Lab.vue)，前端 API 为 [frontend/src/api/lab.js](frontend/src/api/lab.js)，后端入口为 [backend/app/api/lab.py](backend/app/api/lab.py)，业务层为 [backend/app/services/lab_service.py](backend/app/services/lab_service.py)。

| 网页触发点 → 页面函数                       | 前端 API 函数  | HTTP                     | 后端接口函数 → service 函数      |
| ------------------------------------------- | -------------- | ------------------------ | -------------------------------- |
| onMounted / handleSearch / 翻页 → load      | getLabPageList | GET /api/lab/list        | get_lab_list → get_lab_page_list |
| handleCreate → 填写表单 → handleSave，无 id | createLabApi   | POST /api/lab            | create_lab → create_lab          |
| handleEdit(row) → handleSave，有 id         | updateLabApi   | PUT /api/lab/{lab_id}    | update_lab → update_lab          |
| handleDelete(row) → 确认                    | deleteLabApi   | DELETE /api/lab/{lab_id} | delete_lab → delete_lab          |

handleSave 从 form 中取出 id，剩余字段构成 labData，包括名称、简介、图片地址、位置、容量、开放时间和状态。创建使用 LabCreateRequest，修改使用 LabUpdateRequest；后端服务使用 Lab ORM 操作 labs 表。

保存成功的回程：`LabResponse → Response.success → request.js → Lab.vue 关闭弹窗 → load → tableData/total → 表格`。删除成功没有返回新列表，仍需 load 另查。删除前会检查 Reservation 和 Equipment，保护有预约或设备关联的实验室。

实验室查询接口只要求 get_current_user，因为学生浏览页也要复用；创建、更新、删除使用 get_current_admin。图片上传路线则复用第 16.7 节，先取得 URL，再把 form.img 随 labData 保存。

### 16.11 设备管理：主列表之外还有实验室下拉框

页面为 [frontend/src/views/Equipment.vue](frontend/src/views/Equipment.vue)，前端 API 为 [frontend/src/api/equipment.js](frontend/src/api/equipment.js)，后端入口为 [backend/app/api/equipment.py](backend/app/api/equipment.py)，业务层为 [backend/app/services/equipment_service.py](backend/app/services/equipment_service.py)。

| 网页触发点 → 页面函数                  | 前端 API 函数        | HTTP                                 | 后端接口函数 → service 函数                  |
| -------------------------------------- | -------------------- | ------------------------------------ | -------------------------------------------- |
| onMounted / handleSearch / 翻页 → load | getEquipmentPageList | GET /api/equipment/list              | get_equipment_list → get_equipment_page_list |
| handleCreate → handleSave，无 id       | createEquipmentApi   | POST /api/equipment                  | create_equipment → create_equipment          |
| handleEdit(row) → handleSave，有 id    | updateEquipmentApi   | PUT /api/equipment/{equipment_id}    | update_equipment → update_equipment          |
| handleDelete(row) → 确认               | deleteEquipmentApi   | DELETE /api/equipment/{equipment_id} | delete_equipment → delete_equipment          |

设备页面 onMounted 还调用 loadLabs，这不是同一个设备列表请求：

```text
Equipment.vue：loadLabs()
  → frontend/src/api/lab.js：getLabPageList({ page: 1, page_size: 100 })
  → GET /api/lab/list → lab_service.get_lab_page_list
  → 返回实验室列表 → labOptions.value
  → 下拉框显示 item.name，选中值绑定为实验室 ID
```

查询条件里的 params.lab_id 用来筛选设备；表单里的 form.lab_id 用来指定设备所属实验室。它们服务于不同动作，不能因为名字相同就认为改筛选会自动修改设备归属。

保存时 handleSave 去掉 id，传递 equipmentData。service 会核对目标实验室存在，同一个实验室不能有另一台同名设备，随后创建或更新 Equipment 并 commit。响应的 lab_name 从 equipment.lab.name 补充，所以设备表格可以显示实验室名称。

编辑按钮同样先用 row 回填表单，没有独立设备详情请求；删除前检查是否存在关联预约。查询只要求登录，写入要求管理员。设备图片也使用 form.img 和统一上传流程。

<a id="19-student-flow"></a>

### 16.12 学生浏览：页面导航时怎样把实验室 ID 传过去

入口为 Layout.vue 的“实验室列表”，显示 [frontend/src/views/LabList.vue](frontend/src/views/LabList.vue)。

```text
LabList.vue：onMounted → load()
  → api/lab.js.getLabPageList(params)
  → GET /api/lab/list
  → api/lab.py.get_lab_list
  → lab_service.py.get_lab_page_list
  → PageResponse → 页面 tableData、total → 卡片列表
```

当前 LabList.onMounted 还调用一次 loadLabs，查询最多 100 条实验室放进 labOptions；这是现有代码保留的额外请求，主要卡片数据仍来自 load，不要把两个函数当成同一次请求。

点击卡片“查看设备”时，定位实际拼写 `handelViewEquipment(item)`：

```js
const handelViewEquipment = (lab) => {
  router.push({ path: "/manager/labequipment", query: { lab_id: lab.id } });
};
```

这是一次真正的页面导航。例如 lab.id 为 8，浏览器地址变成 /manager/labequipment?lab_id=8。Vue Router 显示 [frontend/src/views/LabEquipment.vue](frontend/src/views/LabEquipment.vue)，新页面用 useRoute() 获取路由对象，再用 `Number(route.query.lab_id)` 转为数字。

LabEquipment.onMounted 检查 ID 是正整数后启动两条请求：

| 页面函数      | 前端 API                                      | 后端接口 → 业务函数                                                                                      | 返回到哪个页面变量                                 |
| ------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| loadLab       | api/lab.js.getLab(params.lab_id)              | GET /api/lab/{lab_id} → api/lab.py.get_lab_detail → lab_service.get_lab                                  | lab.value，供实验室名称、介绍和图片使用            |
| loadEquipment | api/equipment.js.getEquipmentPageList(params) | GET /api/equipment/list → get_equipment_list → equipment_service.get_equipment_page_list，按 lab_id 过滤 | tableData.value、total.value，供设备表格和分页使用 |

onMounted 中这两个函数调用没有互相 await，因此不能认为“一定先返回实验室详情，再请求设备”。两者都使用已从路由取得的 lab_id，可以各自完成。

当前代码主要在组件创建和挂载时读取 ID；同页切换 query 后如何自动重查仍见第 11.16 节。源码中的 handel/hanlde 拼写在本章保留，是为了与你的实际搜索结果一致。

### 16.13 提交预约：父页面把资源交给公共弹窗

三种入口最终调用同一个 [frontend/src/components/ReserveDialog.vue](frontend/src/components/ReserveDialog.vue)：

| 入口                      | 页面函数                    | 页面先改变什么                             | 传入弹窗的资源                   |
| ------------------------- | --------------------------- | ------------------------------------------ | -------------------------------- |
| LabList 卡片“预约”        | handelReserve(lab)          | currentLab=lab，reserveVisible=true        | labId、labName；没有设备 ID      |
| LabEquipment“预约实验室”  | hanldeReserveLab()          | currentEquipment=null，reserveVisible=true | 当前 lab 的 ID/名称；没有设备 ID |
| LabEquipment 设备行“预约” | hanldeReserveEquipment(row) | currentEquipment=row，reserveVisible=true  | 当前 lab 加当前设备的 ID/名称    |

**先打开，后提交。** 点击以上按钮只是选定资源并打开弹窗，没有立即创建预约。父页面用 `:lab-id`、`:equipment-id` 等属性传递信息，子组件通过 defineProps 接收；`v-model:visible="reserveVisible"` 连接弹窗开关。

弹窗打开触发 handleOpen，等待 nextTick 后重置表单；真正点击“提交预约”才进入 handleSubmit：

```text
ReserveDialog.vue：@click="handleSubmit"
  → 检查 submitting，执行表单校验
  → frontend/src/api/reservation.js：createReservationApi({
        lab_id: props.labId,
        equipment_id: props.equipmentId ?? null,
        date: form.date,
        start_time: form.startTime,
        end_time: form.endTime,
        remark: form.remark
    })
  → request.js → POST /api/reservation
  → backend/app/api/reservation.py：create_reservation
      ReservationCreateRequest 校验输入并规范化时间
      get_current_user 取得预约人；get_db 提供会话
  → services/reservation_service.py：create_reservation
      外层负责异常回滚和部分数据库错误的有限重试
  → 同文件 _create_reservation
      日期时段检查 → 锁定资源 → 检查启用、开放时间、设备归属
      检查同资源 status=0/1 的时段冲突
      Reservation(user_id=current_user.id, ..., status=0)
      db.add → commit
  → Response.success() → request.js → ReserveDialog.vue
      提示“预约已提交” → emit('update:visible', false)
  → 父页面 reserveVisible 变为 false，弹窗关闭
```

props 是“父组件传给子组件”，emit 是“子组件通知父组件”。这里 emit 通知的是关闭弹窗，不是发 HTTP，也没有自动导航到“我的预约”。父组件当前也没有通过成功事件自动刷新预约列表；用户另行进入“我的预约”后才查询新记录。

创建请求没有 user_id，避免把预约人交给前端选择；后端从已认证的 current_user.id 填入。页面表单中 startTime/endTime 到接口 start_time/end_time 的转换发生在 handleSubmit，和修改密码的字段映射是同一类思路。

### 16.14 我的预约：查询和取消分别走哪条路

页面为 [frontend/src/views/MyReservation.vue](frontend/src/views/MyReservation.vue)。首次进入 `onMounted → load()`；筛选变化由 handleSearch 把 page 设回 1 再 load；翻页由 current-change 调用 load。

查询主线：

```text
MyReservation.vue：load
  → api/reservation.js：getReservationPageList(params)
  → GET /api/reservation/list
  → api/reservation.py：get_reservation_page_list
  → reservation_service.py：get_reservation_page_list
      非管理员添加 Reservation.user_id == current_user.id
      有 status 时加状态条件；count、排序和分页
      ReservationResponse.model_validate(item)
      填 user_name、lab_name、equipment_name、type
  → Response.success(data=PageResponse)
  → tableData.value、total.value → 表格
```

默认 status=null 表示不按状态过滤，不表示不检查用户归属。lab_name 等字段的完整流向见第 13.9 节。

取消主线：

```text
模板 @click="handleCancel(row)"
  → handleCancel 等待确认框
  → api/reservation.js：cancelReservationApi(row.id)
  → PUT /api/reservation/{reservation_id}/cancel，无请求体
  → api/reservation.py：cancel_reservation
  → reservation_service.py：cancel_reservation(db, current_user, reservation_id)
      查记录 → 检查属于本人 → 检查 status=0
      item.status=3 → commit
  → Response.success() → request.js
  → MyReservation.vue：成功提示 → await load()
  → 另发 GET 列表请求 → 更新当前表格
```

取消后的显示取决于当前筛选：如果查询全部状态，这条记录仍在并显示“已取消”；如果只查待审核，它会从本次结果中消失。后端始终保留这行历史数据。

### 16.15 管理员查询与拒绝：复用哪些部分

管理员从 Layout.vue 的“预约审核管理”进入 AuditReservation.vue。列表通路与 MyReservation 相同，区别在于默认 status=0，后端检测到 current_user.role 为 admin 后不附加“仅本人”条件，前端还显示 user_name 列。

拒绝按钮定位：

```vue
<el-button type="danger" text bg @click="handleAudit(row, 2)">拒绝</el-button>
```

后续执行完全沿第 16.4 节的 handleAudit → auditReservationApi → PUT audit → API → service 路线，只是请求体改为 `{"status": 2}`。成功后 status=2，再调用 load。当前没有额外的 rejectReservationApi、拒绝专用接口或拒绝理由字段。

“管理员可以查看全部”是 service 的数据过滤逻辑；“管理员可以审核”是 API 的 get_current_admin 依赖；“只对待审核显示按钮”是模板的 v-if。它们位于不同层，各自负责不同事情。

<a id="19-error-flow"></a>

### 16.16 公共异常路线：失败怎样回到页面

以“普通用户直接调用审核接口”为例：

```text
请求到达 audit 路由
  → dependencies/auth.py：get_current_admin
  → role 不是 admin，raise BusinessException(code=403)
  → 不执行正常审核函数体，不修改预约
  → main.py 已注册的 business_exception_handler
  → common/exceptions.py 构造 JSONResponse
      HTTP 200，正文 code=403、message='无权限访问'
  → request.js 的响应成功回调收到 HTTP 200
      data.code !== 200，ElMessage.error 提示
      return data
  → 页面 await 得到 code=403 的对象
      不进入 if (res.code === 200)，不显示审核成功，也不调用成功刷新
```

如果请求格式错误，例如审核请求体缺少 status，RequestValidationError 由 validation_exception_handler 转成 HTTP 422；Axios 进入响应错误回调并拒绝 Promise，页面进入 catch。其他未处理异常则由全局异常处理器处理。

登录失效还多一条路线：request.js 的 handleUnauthorized 先比较请求记录的认证版本及 token，避免旧会话请求误清新登录；确认属于当前会话后，按当前代码提示并清理登录、导航到登录页。

所以，排错时要同时看 Network 的 HTTP 状态和 JSON 中的 code。当前一般业务错误不一定进入 catch；“代码运行到了 await 后面”也不等于操作成功。

### 16.17 数据在不同位置叫什么：一张表串起来

| 业务数据    | 页面中的位置                         | 发到后端的形式            | 后端中的位置                                        | 最后在哪里体现                                      |
| ----------- | ------------------------------------ | ------------------------- | --------------------------------------------------- | --------------------------------------------------- |
| 审核记录 ID | row.id                               | URL 的 /42/audit          | reservation_id: int                                 | 查找 reservation.id                                 |
| 通过/拒绝   | handleAudit 的 status 参数           | JSON 的 status            | AuditReservationRequest.status → service 的 status  | reservation.status，再经列表返回 row.status         |
| 预约人身份  | localStorage 中的 token              | Authorization 请求头      | get_current_user → User.id                          | 创建时写 reservation.user_id；查询/取消用于归属检查 |
| 实验室名称  | 列表 row.lab_name                    | 审核时不发送此字段        | 查询时 item.lab.name → ReservationResponse.lab_name | prop="lab_name" 对应的单元格                        |
| 预约时段    | ReserveDialog.form.startTime/endTime | start_time/end_time       | ReservationCreateRequest → Reservation              | 列表 row.start_time/end_time                        |
| 每页条数    | User/Lab 页 params.pageSize          | load 显式转换为 page_size | API 的 page_size                                    | offset/limit 结果；预约两页当前还缺该转换           |
| 图片文件    | 浏览器 File 对象                     | FormData 的 file          | UploadFile → 磁盘文件                               | 返回 /uploads URL 供浏览器读取                      |
| 图片地址    | form.avatar 或 form.img              | 普通 JSON 字符串字段      | 用户/资源请求模型                                   | 数据库 avatar/img 字段                              |
| 当前昵称    | utils/user.js 的 userInfo.value.name | 更新资料时作为 name 提交  | UserUpdateRequest → users.name                      | 返回后 updateUser，布局与首页更新                   |

后端 JSON 中的 null 对应前端的 null；Python 则使用 None。数据跨过 HTTP 边界后不是共享同一个内存对象：浏览器修改 row.status 不会自动修改 MySQL，必须发送被后端接受的写入请求。

<a id="19-debug-flow"></a>

### 16.18 实际复习时怎样一步步跟踪

以审核通过为练习，不必一次打开整个项目。先并排打开这六个文件：

1. frontend/src/views/AuditReservation.vue：按钮、handleAudit、load。
2. frontend/src/api/reservation.js：auditReservationApi、getReservationPageList。
3. frontend/src/utils/request.js：请求与响应拦截器。
4. backend/app/api/reservation.py：audit_reservation、get_reservation_page_list。
5. backend/app/services/reservation_service.py：两个同名业务函数。
6. backend/app/models/reservation.py：表名、status、关联关系。

遇到身份问题再打开 dependencies/auth.py；遇到数据类型问题打开 schemas/reservation.py；遇到错误响应打开 common/exceptions.py。

按下面顺序检查实际运行：

| 检查位置               | 看什么                                      | 能回答的问题                          |
| ---------------------- | ------------------------------------------- | ------------------------------------- |
| 页面按钮与 handleAudit | row.id、status 是否为预期；是否确认         | 页面到底调用了什么操作                |
| 浏览器 Network         | PUT 的 URL、Payload、响应；随后有无 GET     | HTTP 有没有发出，发的 ID/状态是否正确 |
| request.js             | 是否附带 Authorization；响应被哪个分支处理  | 登录凭证、业务错误、网络错误如何处理  |
| 后端路由函数           | 是否进入函数体；data.status、reservation_id | 方法路径是否匹配，参数/依赖是否通过   |
| service                | 记录是否存在、原状态、是否执行 commit       | 业务判断和数据库写入停在哪一步        |
| 页面 load              | GET 响应里的 list/total，tableData.value    | 数据已更新但页面为何看起来没有变化    |

在 VS Code 中对导入的函数使用“转到定义”可以跟踪同一种语言内部的调用；在 HTTP 边界，需要根据 Network 中的“方法 + URL”去后端找装饰器，不能期待一个前端断点直接跨进 Python。调试 token 时查看是否存在即可，不要把真实凭证复制进公开文档或截图。

本章内容依据当前源码逐文件核对，属于执行关系说明；没有新增业务代码，也没有因此把真实浏览器验收标为通过。复习时若能不看本章，自己说清“按钮 → 函数 → HTTP → 后端校验 → 数据库 → 响应 → 页面更新”，就已经从认识单个文件进步到理解整个功能的协作过程。

---

维护说明：章节按日期保存实现过程。已有问题修正后同步更新进度；正常流程、已知边界、隔离验证和真实浏览器验收分别记录。整个项目的从零复现仍需最终完成一次完整检查。

<a id="agent-request-flow"></a>

### 16.19 AI 流式预约路线：历史、图事件与页面增量

当前路径是 AIChat.vue.handleSend → chatStreamApi → POST /api/ai/chat/stream。FastAPI 校验输入与身份，返回 StreamingResponse；event_generate 从 stream_agent 读取事件，再编码为 data: JSON 加空行。

stream_agent 构造消息与图，astream_events 观察模型和工具执行。agent 节点用 ainvoke，模型增量转成 token；工具开始/结束转成中文进度与输出预览。创建预约仍进入 ReservationCreateRequest → create_reservation，写入当前用户的待审核记录，规则与原服务一致。

前端 reader 读取字节，TextDecoder 处理 UTF-8 边界，buffer 保留半帧；完整事件交给回调，更新同一个 reactive 助手的 status/steps/content。history 下一次只重传 role/content，结束或错误后释放 reader 锁并复原 loading。六种事件、断流和数据库边界见[SSE 教程](#agent-sse)及[实际验收](#sse-validation)。

确认通常仍是两次请求，且目前仅由提示词约束；输出中断不会自动撤销已经提交的预约。旧一次性 JSON 方案的调用路线保留在第 15.22 节。

<a id="09-check"></a>

## 17. 启动、联调、排错与验证记录

先区分基础学习副本与完整项目的启动要求，再按检查清单验证。历史隔离测试只说明当时覆盖范围；真实 MySQL、模型服务、浏览器与从空环境复现需要独立验收。

### 17.1 当前学习副本的创建顺序

1. 创建 learning-demo/backend/app 等目录与空的包文件。
2. 创建虚拟环境，安装 requirements.txt。
3. 在 MySQL 中创建学习数据库。
4. 准备 backend/.env，配置连接和生成的 JWT 密钥。
5. 按第 3～6 节创建后端文件。
6. 可选执行 seed_user.py，或通过注册接口创建账号。
7. 启动后端，检查根路径和 /docs。
8. 创建 Vue 项目，安装前端依赖。
9. 创建环境配置和路径别名。
10. 按第 7 节创建前端工具、API、页面和路由。
11. 启动前端，逐个完成下面的检查。

所有命令都要在标明的目录执行，不要把原项目与学习副本的虚拟环境、数据库、端口混用。

### 17.2 完整项目的从零复现顺序

在已理解各功能模块的前提下，按同一版本的工作区文件复现完整项目：

1. 安装后端和前端锁定依赖，创建专用学习数据库；配置数据库、JWT 与三个必填 LLM 字段。
2. 同步 users、labs、equipments、reservation 模型，核对外键；新库由模型建表，旧库先备份并分别处理表名和用户名唯一索引迁移。
3. 完成统一响应、认证、注册登录、本人资料与上传、密码修改和管理员用户管理，准备学习管理员。
4. 完成实验室/设备管理、学生浏览，核对查询权限、容量、表单重置和关联删除。
5. 实现预约模型、时间与归属校验、冲突查询、事务回滚和重试；接入公共预约弹窗。
6. 接入本人查询/取消和管理员审核；实现独立 Session 的过期扫描，在 main.py 中安排启动与退出清理。
7. 整合 JWT UTC、前端会话版本、useRouter 导航与 useRoute 菜单状态，分别核对浏览器操作。
8. 配置 AI 页面、LLM 与 BGE 本地缓存/预热；保留旧自定义循环，接入 LangChain 工具、LangGraph 消息图与预约写入，核对索引同步和确认边界。
9. 运行现有 SSE 测试并维护对应回归；原后端与登录测试文件仍需恢复，不能把当前 7 项或发现 0 项当成历史 19/6 项重新通过。
10. 在学习 MySQL、真实模型服务和浏览器分别验收正常与错误路径，包括并发、状态竞争、上传、检索及工具调用。
11. 用新的空目录和空学习库再走一遍，记录遗漏依赖、配置、数据初始化与迁移差异。

README 提供依赖、配置和学习管理员的准备方式；普通注册仍默认 student，没有内置管理员密码。各功能章的验收清单与最终验收章共同记录尚未完成项。

目标是能解释并独立复现。完整端到端验收与从空环境复现完成前，本教程仍保留待办。

### 17.3 两个终端分别启动

终端一：学习副本 backend 目录。

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

终端二：学习副本 frontend 目录。

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

前端配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

修改前后端环境配置后，重启相应的开发服务器。

### 17.4 后端检查

先在 `http://127.0.0.1:8001/docs` 检查注册与登录接口。

注册示例：

```json
{
  "username": "new_student",
  "password": "Learn123!"
}
```

预期：第一次 code 200；再次注册同账号，HTTP 200 但业务 code 409；密码少于 6 个字符，HTTP 422。

登录示例：

```json
{
  "username": "new_student",
  "password": "Learn123!"
}
```

预期：code 200，data 包含 token 与 user。密码错误或账号不存在时，HTTP 200 但业务 code 400。

用户信息接口需要 Bearer token；仅在地址栏访问不会自动带上 localStorage 中的 token。优先通过前端登录后在 Network 面板检查。

### 17.5 前端检查清单

以下方框用于记录你自己的实际运行结果，本笔记不会预先勾选：

- [ ] 未登录访问 /manager/home，会跳转 /login。
- [ ] 两次密码不一致时，注册页不给后端提交请求。
- [ ] 新账号可以注册，重复账号显示错误。
- [ ] 错误密码显示错误，页面不会进入登录成功流程。
- [ ] 正确登录后，浏览器保存 token 和 userInfo。
- [ ] 首页发送 GET /api/user/info。
- [ ] 该请求带有 Authorization: Bearer ...。
- [ ] 后端返回的用户信息没有 password。
- [ ] 刷新首页后，重新获取当前用户资料。
- [ ] 退出登录后，缓存与响应式用户信息被清空。
- [ ] 退出后访问受保护页面，会返回登录页。
- [ ] 无效或过期 token 返回 401，并清理登录状态。
- [ ] 后端未运行时，页面显示网络错误并结束加载状态。

### 17.6 无效 token 实验

在学习副本页面的浏览器 Console 中执行：

```js
localStorage.setItem("token", "not-a-valid-token");
location.reload();
```

预期：

```text
路由守卫发现 token 存在，放行
  → 首页请求用户信息
  → 后端验证失败，返回 401
  → request.js 清理缓存与响应式状态
  → 回到登录页
```

实验只修改自己的学习环境。它说明 token 的存在与有效性需要分别检查。

可选的过期实验：在学习副本后端配置中临时设置 `JWT_EXPIRE_HOURS=0`，重启后端并重新登录，首页应发现 token 已过期。完成后恢复 24，重启并重新登录以获得新的有效 token。

### 17.7 看浏览器 Network 时关注什么

| 位置            | 看什么                          |
| --------------- | ------------------------------- |
| Request URL     | 最终地址和端口是否正确          |
| Request Method  | GET 或 POST 是否与后端匹配      |
| Request Headers | 是否带 Authorization            |
| Payload         | 请求体字段及值                  |
| Status Code     | HTTP 200、401、403、422、500 等 |
| Response        | JSON 中 code、message、data     |

如果看到 OPTIONS 请求，可能是浏览器在做跨域预检；它不等于业务接口被重复调用。

### 17.8 常见问题

| 现象                                      | 首先检查                                                |
| ----------------------------------------- | ------------------------------------------------------- |
| 连接失败                                  | MySQL、后端是否启动，端口是否正确                       |
| ModuleNotFoundError                       | 是否用学习副本的 Python，依赖是否安装，启动目录是否正确 |
| 前端提示找不到 @/...                      | vite.config.js 是否设置别名，路径和大小写是否一致       |
| 浏览器 CORS 错误                          | allow_origins 是否包含实际前端来源                      |
| 设置 DATABASE_URL 后仍连接到其他库        | 同名进程环境变量、是否重启、是否启动了正确项目          |
| 新加模型字段未出现在旧表                  | create_all 不负责迁移已有表结构                         |
| 401                                       | 是否带 token，是否过期，是否与当前密钥匹配              |
| 403                                       | 身份已识别，但账号状态或权限不允许                      |
| 422                                       | 请求字段类型、长度、必填条件是否符合后端模型            |
| 页面 res.data 与预期不同                  | 是否已经经过响应拦截器解包                              |
| localStorage 更新但页面没变化             | 是否同步更新了响应式 userInfo                           |
| 默认导入改名后报未定义                    | 是否也修改了这个文件中的调用名                          |
| 登录后切换 localhost / 127.0.0.1 就丢状态 | 浏览器来源不同，存储不同                                |

本笔记中的全局错误响应只给出通用提示。进一步定位服务器错误需要结合后端终端堆栈与日志，相关排错教学尚未完成。

### 17.9 基础学习阶段的历史检查记录（2026-10-10）

整理时已完成以下检查：

- UTF-8 中文内容读取正常，没有未填完的章节占位标记。
- 当时 11 个目录锚点与正文对应，代码块的围栏成对闭合。
- 16 个完整后端参考文件通过 Python 编译语法检查。
- 8 个完整 JavaScript 参考文件通过 Node.js 语法检查。
- 7 个 Vue 示例通过组件解析与模板编译；其中 5 个包含脚本的示例也通过脚本编译。
- 后端参考文件中的 app 模块引用与笔记提供的目录对应。

这些检查没有启动整合后的前后端，也没有代替第 17.5 节的实际功能验收。问答中的局部语法片段需要结合上下文阅读，不能一律当作完整文件运行。

### 17.10 历史审查记录的来源与验证方法

原 docs/logic-review-2026-10-20.md 包含 18 项问题及两项待明确的业务规则，是修补前的检查记录（当前工作区无此文件）。

原 docs/logic-fixes-2026-10-20.md 说明按问题名称选择修复的 7 项（当前工作区无此文件）。名称与代码对应如下：

| 指定修补           | 当前实现位置                                                   |
| ------------------ | -------------------------------------------------------------- |
| 并发重复预约       | reservation_service 的事务锁、锁内冲突检查和重试               |
| 设备归属校验       | equipment.lab_id 与 lab.id 比较；冲突按设备 ID 查询            |
| 并发注册同名账号   | User 唯一约束、注册/管理员创建的 IntegrityError 处理、迁移脚本 |
| 新增设备继承旧值   | Equipment.vue.resetForm                                        |
| 容量输入冲突       | Lab.vue 数字控件、LabCreateRequest/LabUpdateRequest 的 Field   |
| 删除有预约用户失败 | user_service 关联检查、回滚，User.vue 捕获确认框及请求异常     |
| JWT 时间偏差       | utils/jwt.py 使用 timezone.utc                                 |

源码还有实验室/设备关联删除、登录跳转及旧请求 401 处理等变化，已分别归入相关功能章节。它们不需要强行归入“7 项指定修补”。

学习时用“错误怎样触发 → 修改怎样阻止它 → 还有哪些限制 → 怎样验证”的顺序，比只记住新增了几个 try/except 更容易复现。

<a id="historical-regression"></a>

### 17.11 历史回归测试证明了什么（2026-10-20）

2026-10-26：frontend/tests 现已有 SSE 的 ai.test.js；下面提到缺失的原测试文件和历史 19/6 项仍未恢复。当前 7 项流解析测试独立记录在第 15.61 节。

2026-10-20 当时重新执行了仓库中的测试；当前缺少对应测试目录，下面命令保留为历史记录：

```powershell
# 在 backend 目录
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

当时结果为 19 项通过。测试文件为 backend/tests/test_logic_fixes.py（当前工作区无此文件），主要覆盖：

- 同资源完全相同和部分重叠时段的并发提交，最终一条成功、一条业务冲突。
- 相邻时段、不同日期和不同资源；状态 0/1 阻塞，2/3 不阻塞。
- 设备归属不符、历史实验室 ID 不同的同设备冲突、失败后释放事务。
- 预约不改变实验室资料更新时间。
- 模拟 MySQL 死锁重试、等待超时和重试耗尽。
- 注册与管理员创建交错时的用户名唯一约束。
- 任意预约历史阻止删除用户，以及关联检查后的写入竞态。
- 唯一索引重复执行、重复账号时停止且保留数据。
- 容量输入限制和 JWT UTC 有效期。

ThreadPoolExecutor 模拟多个执行线程，Barrier 让它们在某一步会合后再继续，扩大或固定原先容易偶发的交错窗口。patch 可以把“数据库死锁”等条件替换成可控异常，从而验证错误分支。

这些检查使用临时 SQLite，测试在导入应用前覆盖 DATABASE_URL 和 JWT 测试配置，不连接项目现有 MySQL。模拟 MySQL 错误码并不等于真实 InnoDB 并发测试。

前端本轮运行 npm.cmd run build，构建通过，有包体积提示。另外提取实际组件/工具函数，用模拟依赖检查了预约字段映射、重复点击、校验失败、冲突和网络失败，以及新旧会话 401 的处理。

随后针对登录页路由实例新增了 6 项前端回归测试，运行 `npm.cmd test` 全部通过；测试方式、命令和浏览器待验收项见[第 7.12 节](#17-login-navigation)。这与上面的 19 项后端测试是两套检查。

当前没有在真实浏览器中完成端到端验收，也没有运行旧库迁移。应把这些未做项与已通过检查分别记录。

**复习自测**

| 问题                                     | 核对要点                                                |
| ---------------------------------------- | ------------------------------------------------------- |
| 19 项测试通过能否证明 MySQL 并发已验收？ | 不能，当前实际数据库测试是 SQLite，MySQL 错误分支为模拟 |

<a id="10-pending"></a>

## 18. 功能待办、遗留问题与最终验收

勾选“已讲解”或记录历史检查，不表示当前学习副本已验收。先按功能查待办，再看遗留问题总表，最后对照完整复现与结束条件。

### 18.1 已经讲解的内容

以下勾选表示“已讲解”，不表示你的学习副本已经验证成功。

- [x] 前端、后端、数据库和 HTTP 的职责。
- [x] 项目需求与逐步实现的设计顺序。
- [x] Python 虚拟环境、后端依赖与 FastAPI 启动。
- [x] 第一个接口、查询参数、自动接口文档。
- [x] Vue 项目、响应式变量、第一次前后端请求。
- [x] CORS 基础。
- [x] .env、BaseSettings 和 model_config。
- [x] SQLAlchemy 连接、会话、模型、建表及种子用户。
- [x] 统一响应和主要异常类型。
- [x] 注册接口、密码哈希与 Register.vue 表单校验。
- [x] 登录接口、JWT 签发与 Login.vue。
- [x] localStorage 与共享响应式用户信息。
- [x] Axios 实例、默认导出、请求与响应拦截器。
- [x] Promise、await 与 loginApi 返回值。
- [x] get_current_user、Depends、用户信息接口。
- [x] 首页重新获取用户信息、登录失效和退出登录。
- [x] cls、默认导入改名和 model_dump 等语法问答。
- [x] 个人资料查询与修改：Object.assign、请求字段范围、setattr 与数据库提交。
- [x] 头像上传、FormData、文件响应、静态文件访问与开发代理。
- [x] Layout 共享用户资料、个人信息子路由和上传 Promise 的行为。
- [x] 本人密码修改、原密码验证、新密码哈希与重新登录流程。
- [x] 管理员依赖、用户关键词搜索与分页结果。
- [x] 用户表格、作用域插槽、分页组件和新增编辑弹窗。
- [x] 用户创建、按 ID 更新、删除与后端禁止删除本人。
- [x] 本人更新和管理员更新复用模型导致的权限边界问题。
- [x] 实验室模型、CRUD、封面、容量与开放时间。
- [x] 设备模型、外键、relationship、关联名称和实验室筛选。
- [x] 设备查重、跨实验室移动、删除约束与按需关系加载。
- [x] 字典 \*\* 解包、设备表单重置与分页字段对照。

### 18.2 前端布局、导航与会话验收

- [x] 按原项目 Layout.vue 讲解页头、侧栏和内容区域。
- [x] 讲清父路由、children 与两层 router-view 的显示关系。
- [x] 说明菜单点击导航及当前 default-active 固定值的行为。
- [x] 区分页面名称、菜单文案、路由路径与后端权限。
- [x] 说明首页、实验室、设备、用户和 Profile 的现有路由。
- [x] 说明哪些页面有真实功能，哪些只是占位内容。
- [ ] 检查或调整当前路径与菜单高亮的对应关系。
- [ ] 完成一次导航、刷新、退出登录的检查。

### 18.3 文件上传与静态访问验收

- [x] 讲解 UploadFile、multipart/form-data 和表单文件请求。
- [x] 核对当前环境与依赖清单的差异。
- [x] python-multipart 已纳入依赖清单（2026-10-20）；学习环境仍需实际安装并运行上传流程。
- [x] 按原项目 files.py 解释文件名、扩展名和大小校验。
- [x] 解释生成新文件名、分块读取与写入目录。
- [x] 讲解 UPLOAD_DIR、StaticFiles 和 /uploads 挂载。
- [x] 说明磁盘文件路径与浏览器访问 URL 的区别。
- [x] 讲解你新编写的前端上传请求与 Profile 头像页面。
- [ ] 检查上传成功、类型不允许、超过大小限制等情况。
- [ ] 结合真实需求明确上传接口是否要求登录。

### 18.4 个人资料、头像与依赖待办

- [x] 当前 Profile 已移除未定义的 handleAvatarSuccess 绑定（2026-10-14 已核对）。
- [ ] 让自定义上传 Promise 明确表达业务成功与失败。
- [ ] 检查上传未完成时提前保存资料的行为。
- [ ] 补齐资料修改的后端格式与长度校验。
- [ ] 明确 null、空字符串与“清空字段”的更新语义。
- [ ] 检查查询资料和退出登录时的共享 userInfo 同步。
- [x] python-multipart 已加入 requirements.txt 并固定版本（2026-10-20 核对）。
- [ ] 将直接使用的图标包显式列为前端依赖；当前锁文件已通过 Element Plus 包含该传递依赖。
- [ ] 完成第 8.17 节的真实浏览器与数据库功能检查。

### 18.5 密码与用户管理待办

- [x] 本人资料服务已排除 role/status，隔离验证确认不再通过该路径修改（2026-10-15）。
- [ ] 可选整理：按本人和管理员用途拆分输入模型，使字段范围更明确。
- [ ] 设置后端密码长度及字节校验，统一各入口规则并遮盖密码输入。
- [ ] 统一 status 的布尔值与单选框类型。
- [ ] 解决创建模型名称可缺失与数据库 NOT NULL 的冲突。
- [ ] 约束分页参数与角色允许值。
- [x] 用户删除已捕获取消、关闭及请求失败；有预约记录时后端拒绝删除并提示禁用（2026-10-20，见[用户删除](#user-deletion)）。
- [ ] 明确自我禁用、自我降级和当前用户缓存同步策略。
- [ ] 准备学习数据库的初始管理员，完成第 9.24 节浏览器检查。
- [ ] 若需求要求改密后所有会话失效，增加相应服务端机制。

### 18.6 实验室与设备管理待办

- [x] Equipment.vue 已按实际设备字段重置 lab_id、spec、quantity 和整数 status（2026-10-20）。
- [x] 将设备分页绑定与实际 page_size 参数统一（2026-10-19 核对已修正，见第 10.24 节）。
- [x] 实验室容量改用数字输入；后端创建必填且大于 0，更新时提供的容量也须大于 0（2026-10-20）。
- [ ] 统一实验室搜索提示、设备型号搜索提示与真实查询行为。
- [ ] 明确实验室时间格式、清空和跨夜规则。
- [ ] 处理实验室改名查重及数据库唯一约束策略。
- [x] 实验室有设备或预约记录、设备有预约记录时禁止删除，返回业务提示并处理提交时的关联冲突（2026-10-20）。
- [ ] 核对实际数据库外键，必要时单独执行迁移。
- [ ] 按数据规模考虑实验室选项加载与关系查询优化。
- [ ] 完成第 10.27 节浏览器验收，更新完整复现版本。

### 18.7 学生浏览与资源权限待办

- [x] 增加实验室卡片列表、详情接口、按实验室 ID 查询设备和对应页面路由，完成隔离检查。
- [x] 将实验室和设备的查询接口改为当前登录用户可调用，写入接口继续校验管理员依赖。
- [ ] 将实验室状态筛选的 if status 改为明确判断是否传参，并验证 False 的筛选结果。
- [ ] 明确学生能否查看停用实验室；若只允许启用资源，前后端都要落实该规则。
- [ ] 修正 LabList.vue 的 header 插槽，清理无用表单、额外列表请求及未导入 nextTick 的闲置逻辑。
- [x] 菜单重复属性已整理为 :default-active="route.path"（第 7.12 节）；设备详情页映射到实验室列表菜单的高亮规则仍需确定。
- [ ] 如需支持同页切换实验室，监听路由 lab_id，重置分页并处理请求先后顺序。
- [x] 预约按钮已接入公共弹窗、POST 接口和预约表，保存待审核记录；加入资源及重叠检查和并发保护（2026-10-20，见[预约提交与并发](#16-reservation)）。
- [x] 补齐预约查询、审核、取消（2026-10-21，第 13 节）。
- [ ] 完善日期、零时长、数量和实验室/设备互斥规则。
- [ ] 完成第 11.21 节真实浏览器验收，并与前面章节合并进行从零复现检查。

### 18.8 预约提交、并发与迁移验收

- [x] 完成预约提交及 7 项指定修补的代码讲解，核对审查报告与当前代码的对应状态。
- [x] 2026-10-20 曾重新运行 19 项后端隔离回归测试、前端构建，以及预约弹窗和旧会话 401 的函数检查；当前工作区缺少原后端测试文件。
- [x] 补充登录页与布局使用当前应用路由实例的改法；当时 6 项前端登录回归测试通过，当前工作区缺少原前端测试文件。
- [ ] 在有备份的学习库核对 lab → labs 的数据、ID 和外键迁移；当前没有这项自动迁移脚本。
- [ ] 旧 users 表检查重复账号并执行用户名唯一索引升级；本次未对现有数据库执行。
- [ ] 在真实 MySQL/InnoDB 环境验证并发预约、锁等待和回滚。
- [ ] 完成第 12.25 节浏览器验收；第 18.12 节未解决项继续跟进。
- [ ] 在真实浏览器确认登录后首页内容立即显示，并完成第 7.12 节的导航、退出和重新登录检查。
- [ ] 在空目录、空学习数据库中完成一次安装、初始化、管理资源、提交、查询、取消和审核预约的完整复现。

### 18.9 查询、取消、审核与扫描验收

- [x] 完成两种角色的数据范围、名称组装、分页响应、状态转换和页面操作的教学说明。
- [x] 完成 33 个后端隔离断言、18 组前端场景检查与前端构建；检查范围见第 13.26 节。
- [ ] 统一前端 pageSize 与后端 page_size，并增加分页范围与状态取值校验。
- [ ] 补齐列表 loading、Search 图标绑定，调整审核页面标题；处理筛选重复请求和查询失败反馈。
- [ ] 为取消与审核增加原子状态转换或一致的事务锁，并在真实 MySQL 验证竞争操作。
- [ ] 明确过期申请、资源关闭后的审核，以及是否需要审核人、审核时间和拒绝理由。
- [ ] 恢复并维护可重复运行的测试文件；不要仅保留一次性测试结果。
- [ ] 按第 13.25 节完成三个账号的浏览器验收，再进行全项目从零复现。

- [ ] 验证自动过期的时间边界、异常恢复、多进程重复和与审核/取消的竞争，见[自动过期验收](#expiry-validation)。

### 18.10 AI 与知识库验收

AI/RAG、本地缓存/预热和 SSE 发送已讲解；真实模型、集合兼容、中文阈值、索引同步与长连接超时/取消策略仍待联调。旧 Axios 60 秒配置不作用于当前 fetch。历史检查见[AI 验证记录](#ai-validation)，当前检查见[SSE 验收](#sse-validation)。

### 18.11 两种 Agent 实现、SSE 与当前框架验收

- [x] 保留自定义循环与框架 JSON 的完整教程和阶段快照，增加 SSE 前后端完整调用链。
- [x] 讲解六种事件、异步生成器、分块解码、响应式助手、历史过滤、DeepSeek 分支与线程化扫描。
- [x] 2026-10-26 实际运行现有 frontend/tests/ai.test.js，7 项通过；不等于旧 30 个模拟断言或历史登录 6 项重新通过。
- [ ] 在真实浏览器、模型与代理下核对首片延迟、逐段正文、工具过程和错误反馈。
- [ ] 核对 FastAPI 0.115.13 的流式依赖清理与异步 ToolNode 共用 Session 的并发问题。
- [ ] 补齐流式最终输出校验、无 done 的异常截断识别、取消/超时/心跳策略与稳定调用 ID。
- [ ] 实现后端强制确认、幂等与写入后结果追踪；验收断流后已经提交预约的行为。
- [ ] 继续核对资源权限、日期、时段冲突、知识索引、缓存预热与扫描退出，按[流式验收清单](#sse-validation)记录真实结果。

<a id="issue-status"></a>

### 18.12 遗留问题总表：已修复、部分完成与待处理

以下按原审查的问题编号对照，避免把“修补了 7 项”误读成“18 项全部修好”。

| 审查项                            | 当前状态                                           | 仍需注意                                                         |
| --------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------- |
| 1 并发重复预约                    | 已加入事务锁、锁定读、回滚和重试；历史隔离检查通过 | 真实 MySQL/InnoDB 并发待验收                                     |
| 2 设备归属缺失                    | 已修补                                             | 以后新增预约入口也要复用规则                                     |
| 3 设备转移绕过预约                | 部分处理                                           | 同设备历史冲突不再因 lab_id 变化漏查；未来预约与转移政策尚未补齐 |
| 4 缺少查询、审核和取消            | 2026-10-21 已补齐主要流程                          | 第 13 节；并发状态转换及浏览器验收仍待完善                       |
| 5 并发同名账号                    | 代码与升级脚本已补齐                               | 旧库约束实际升级尚未执行                                         |
| 6 非法日期与零时长                | 仍待修补                                           | 时间文本已规范，date 仍是 str，结束等于开始仍可通过这项校验      |
| 7 基础数据约束不足                | 部分处理                                           | 容量已修补；设备数量/状态、开放时间等仍待完善                    |
| 8 新增设备继承旧值                | 已修补                                             | 按当前字段重置                                                   |
| 9 容量输入类型冲突                | 已修补                                             | 需结合真实浏览器再验                                             |
| 10 有预约用户删除异常             | 已修补                                             | 任意预约历史都阻止删除，提供禁用方案                             |
| 11 JWT 时区偏差                   | 已修补；历史回归曾通过                             | 不代表旧 token 已具备撤销机制                                    |
| 12 改密后旧 token 仍有效          | 未处理                                             | 需定义并实现服务端会话失效策略                                   |
| 13 最后一个管理员可自我降级/禁用  | 未处理                                             | 当前仍缺少有效管理员数量保护                                     |
| 14 文件上传没有登录依赖           | 未处理                                             | 当前接口仍可匿名访问                                             |
| 15 超过 bcrypt 字节限制的密码异常 | 未处理                                             | 注册、登录、改密和管理员创建需统一规则                           |
| 16 型号搜索提示与实现不符         | 未处理                                             | 当前只查设备名称                                                 |
| 17 status=False 实验室筛选被忽略  | 未处理                                             | 当前仍为 if status                                               |
| 18 用户编辑状态布尔/数字不一致    | 未处理                                             | 前后端或表单转换需要统一                                         |

额外两项业务规则仍待决定和实现：整间实验室预约是否占用其中设备；设备是否允许按 quantity 中的部分数量预约。

本表描述当前代码和测试范围，不把文档里提出的建议自动算作已完成修改。

### 18.13 后端结构与排错复习

- [ ] 从 main.py 重新串联模块加载、配置读取、建表和注册路由。
- [ ] 系统梳理 api、services、models、schemas、dependencies、utils、common 的职责。
- [ ] 对照原项目解释调用链，而不是只记住文件夹名称。
- [ ] 展开数据库事务、会话关闭和异常处理顺序。
- [ ] 说明建表与数据库迁移的区别，核对用户名唯一约束。
- [ ] 讲解终端堆栈、浏览器 Console 和 Network 的排错方式。
- [ ] 核对 JWT 时间、异常捕获及接口文档认证方式的实现差异。
- [ ] 说明前端退出仅清除本地状态，当前 JWT 方案没有服务端即时撤销机制。

这些核对项不代表已经发现并修复了原项目全部问题；实施调整前需要确定学习副本与原项目的范围。

本节作为自行复习的核对表：应用入口、事务、迁移和整项目路线已在相应章节讲解，勾选应依据你是否能独立说明并复现，不表示这些内容仍未写入教程。

### 18.14 完整项目的从零复现验收

- [ ] 提供最终目录结构与文件创建顺序。
- [ ] 整理所有依赖与版本、前后端环境配置样例。
- [ ] 整理数据库创建和初始化方式。
- [ ] 核对前后端启动命令、端口和 CORS。
- [ ] 完成注册登录、资料上传、用户/资源管理、预约全过程、AI 检索与工具调用的端到端检查。
- [ ] 整理常见错误与定位步骤。
- [ ] 完成一次不依赖原项目运行目录的重新创建。
- [ ] 更新本笔记，使内容与最终复现版本一致。

### 18.15 建议的复习练习

1. 不看笔记，口述从点击登录按钮到首页显示昵称的过程。
2. 修改 /hello 的默认名字，说明改动为什么会影响响应。
3. 给注册模型加入一个简单规则，再检查前后端分别如何报错。
4. 将默认导入 request 改为 service，并修改调用，观察功能是否一致。
5. 用无效 token 解释为什么路由守卫放行后，后端仍能拒绝请求。
6. 比较 Response 对象、Python 字典、JSON 字符串和前端对象。
7. 对照第 17 节检查自己的学习副本，把实际通过的项目勾选出来。

### 18.16 何时才能说“全部教程完成”

需要同时达到：

1. 原项目实际已有功能的主要代码已解释清楚。
2. 你能说明一次请求经过哪些前后端文件，以及每层的职责。
3. 你能自行准备依赖、配置数据库并启动两端。
4. 你能从空目录复现已经约定的项目功能，而不只是复制某一段代码。
5. 正常流程和重要失败场景完成实际检查。
6. 尚未实现的占位页面与已实现功能的边界已经明确。

目前尚未达到全部条件，因此整个教程仍在进行中。

<a id="08-questions"></a>

## 19. 语法与框架机制速查

这一节按你问过的问题整理，可以独立复习。

### 19.1 @router.post("/login") 怎样把前后端联系起来

`@...` 是 Python 装饰器写法。模块加载时，FastAPI 通过它登记“某个 HTTP 方法和路径由哪个函数处理”。

```python
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    ...
```

它登记的是 POST 请求，不是在启动时调用登录业务。实际触发登录业务的是浏览器之后发出的 HTTP 请求。

完整连接：

```text
前端 loginApi(form)
  → POST http://127.0.0.1:8001/api/auth/login
  → FastAPI 匹配 POST 方法和 /api/auth/login 路径
  → 将 JSON 请求体校验成 LoginRequest
  → Depends(get_db) 提供会话
  → 调用 login(data, db)
  → 返回 HTTP 响应
```

前端路由 `/login` 表示“显示登录页面”；后端 `/api/auth/login` 表示“处理登录请求”。两个路径分属不同职责。

### 19.2 cls 是什么

```python
@classmethod
def success(cls, message: str = "请求成功", data: Any = None):
    return cls(code=200, message=message, data=data)
```

调用：

```python
result = Response.success(message="登录成功")
```

Python 自动把调用这个方法的类传给 `cls`。在这里，`cls` 就是 `Response`。

所以：

```python
return cls(code=200, message=message, data=data)
```

在本次调用中相当于创建：

```python
Response(code=200, message=message, data=data)
```

`cls` 是惯用参数名，不是特殊关键字；自动传入类的行为由 `@classmethod` 决定。惯例中，实例方法使用 `self`，类方法使用 `cls`。

如果子类继承这个方法，并通过子类调用，`cls` 可以指向子类。因此这种写法也便于继承。

### 19.3 不使用 cls 怎样写

一种写法是静态方法：

```python
from typing import Any
from pydantic import BaseModel


class Response(BaseModel):
    code: int
    message: str
    data: Any = None

    @staticmethod
    def success(message: str = "请求成功", data: Any = None):
        return Response(code=200, message=message, data=data)
```

调用方式仍然是 `Response.success(...)`，但内部固定创建 `Response`，不会根据调用的子类自动改变。

也可以不用包装方法，直接创建：

```python
result = Response(
    code=200,
    message="登录成功",
    data=None,
)
```

这里提供的是替代写法示例，不要把它追加到第 4 节的类后面创建第二个同名类。

### 19.4 为什么 request({...}) 会调用 service

`request.js`：

```js
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

export default service;
```

`api/auth.js`：

```js
import request from "@/utils/request";
```

默认导入的本地名字是 `request`，它引用的就是默认导出的 `service`。

Axios 创建的实例可以作为函数调用，因此：

```js
request({
  url: "/api/auth/login",
  method: "post",
  data: form,
});
```

就是调用那个 Axios 实例发出请求。JavaScript 不会因为名字叫 `request` 就自动寻找一个叫 `service` 的函数，联系来自 import/export。

### 19.5 import request 能改成 import service 吗

可以：

```js
import service from "@/utils/request";

export function loginApi(data) {
  return service({
    url: "/api/auth/login",
    method: "post",
    data,
  });
}
```

默认导入允许自行选择本地名字。改名后，这个文件中的调用也要改成 `service(...)`。

具名导入规则不同：

```js
import { useUser } from "@/utils/user";
```

它匹配导出的名字；如需改本地名字，可以显式使用别名：

```js
import { useUser as getUserState } from "@/utils/user";
```

### 19.6 export default service 的作用

它把 `service` 指定为这个模块的默认导出，其他文件可以通过默认导入使用同一个实例。

- 不会在这行代码中发 HTTP 请求。
- 不会把变量名强制规定成 `service`。
- 一个模块只能有一个默认导出，但可以有多个具名导出。
- 多个文件导入此模块，在同一模块运行环境中通常共享同一个已创建实例。

`export default service` 导出的是变量的值；`export default service()` 会先调用，再导出返回值，行为不同。

### 19.7 loginApi 的 return 到底返回什么

```js
export function loginApi(data) {
  return request({
    url: "/api/auth/login",
    method: "post",
    data,
  });
}
```

立即返回的是 **Promise 对象**，表示一个尚在进行或已经完成的异步操作。

```js
const promise = loginApi(form);
```

在当前封装下：

```js
const res = await loginApi(form);
```

请求成功后，`res` 是响应拦截器中 `return response.data` 返回的后端 JSON 内容，例如：

```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "这里是示例 token",
    "user": {
      "id": 1,
      "username": "demo_student",
      "name": "示例学生",
      "role": "student",
      "email": null,
      "phone": null,
      "status": true
    }
  }
}
```

时间顺序：

```text
request(...) 返回 Promise
  → loginApi 将这个 Promise 返回给页面
  → HTTP 请求完成
  → 响应拦截器处理结果
  → await 得到成功值，或抛出失败原因
```

两种写法是在说明不同用法；如果把两次 `loginApi(form)` 都执行，会发出两次请求。

必须区分两个 `data`：

| 表达式                   | 含义                                          |
| ------------------------ | --------------------------------------------- |
| 原始 Axios response.data | 整个后端 JSON 内容                            |
| 当前页面 res.data        | 后端 JSON 内部的业务 data，例如 token 和 user |

网络错误或被拒绝的 Promise 会让 `await` 抛出异常，进入 `catch`。

HTTP 200 但业务 code 为 400 的请求，在当前拦截器中仍可能成功返回，因此不能把“await 没报错”直接等同于“登录成功”。

### 19.8 async、await 和 Promise 的关系

- Promise 表示异步操作的结果。
- `async` 函数返回 Promise，即使其中 return 的是普通值。
- `await` 等待 Promise 成功后取得值；失败时在当前位置抛出异常。
- 等待网络时，并不是把整个浏览器界面停住。
- `Promise.reject(error)` 产生拒绝状态的 Promise，将错误继续交给调用方。

页面的 `finally` 会在成功或失败后执行，所以适合恢复：

```js
loadingValue.value = false;
```

### 19.9 userInfo 在其他文件怎么调用

```vue
<template>
  <p>欢迎你：{{ userInfo?.name }}</p>
</template>

<script setup>
import { useUser } from "@/utils/user";

const { userInfo, updateUser } = useUser();

function changeName() {
  if (userInfo.value) {
    updateUser({
      ...userInfo.value,
      name: "新的昵称",
    });
  }
}
</script>
```

- `useUser()` 返回一个包含 ref 和函数的对象。
- `const { userInfo } = ...` 是对象解构，取出属性。
- 脚本中使用 `userInfo.value`。
- 在这里的模板中，Vue 会自动解包这个顶层 ref，所以使用 `userInfo.name`。
- `?.` 是可选链，值为 null 或 undefined 时避免继续访问导致错误。
- `...` 是展开语法，这里复制已有用户字段，再覆盖 name。
- `updateUser` 只修改浏览器缓存和前端状态，不会自动更新数据库。
- 文件没有单独导出 `userInfo`，因此不能直接写 `import { userInfo }`。

原文件注释“仅供页面 setup 函数使用”是作者给出的使用建议；当前函数没有使用强制绑定组件生命周期的 API，注释本身不会限制 JavaScript 的调用位置。

### 19.10 .env 如何被 DATABASE_URL 读取

`DATABASE_URL` 是声明的配置字段。`env_file` 告诉 BaseSettings 到哪里读文件。实例化 `Settings()` 时，库按字段名匹配环境变量和文件内容。

不是 `DATABASE_URL` 自己去“引用 model_config”；是 BaseSettings 同时读取配置规则和字段声明，再组装对象。

```text
.env 中：DATABASE_URL=...
Settings 中：DATABASE_URL: str
Settings()：查找、转换、校验
settings.DATABASE_URL：访问已经加载的值
```

`model_config`、`env_file` 不可以随意换名字，因为它们是库识别的约定名称。`BASE_DIR`、`settings` 等自定义变量可以改名，但引用必须一起修改。

### 19.11 .model_dump() 的作用

```python
result = Response.error(
    code=401,
    message="登录信息无效，请重新登录",
)

content = result.model_dump()
```

`result` 是 Pydantic 模型对象，`content` 是 Python 字典：

```python
{
    "code": 401,
    "message": "登录信息无效，请重新登录",
    "data": None,
}
```

该方法来自父类 `BaseModel`。它返回转换结果，原模型对象仍然存在；不会保存数据库、发送请求或写文件。

| 写法                           | 结果                             |
| ------------------------------ | -------------------------------- |
| result.model_dump()            | Python 字典；默认 Python 模式    |
| result.model_dump(mode="json") | 字典，字段转换为 JSON 支持的类型 |
| result.model_dump_json()       | JSON 字符串                      |

普通模型的嵌套模型也会递归转换。默认 Python 模式可能保留 datetime 等 Python 类型，不保证所有值都可直接交给标准 JSON 编码器。

当前错误响应只有整数、字符串和 None，使用 `.model_dump()` 就足够；含日期时间等字段时，可用 `.model_dump(mode="json")` 或 FastAPI 的 `jsonable_encoder`。

```text
Response 对象
  → .model_dump()
  → Python 字典
  → JSONResponse 编码
  → HTTP 响应
  → 前端收到 JSON
```

Python 的 `None` 在 JSON 中变成 `null`。

普通接口可以直接返回 `Response.success(...)`，因为 FastAPI 会处理转换。手动构造 `JSONResponse` 时，需要先准备可编码的数据。

### 19.12 model_validate 与 model_dump 的区别

```text
数据库对象 / 输入数据
  → UserResponse.model_validate(...)
  → Pydantic 模型
  → .model_dump()
  → Python 字典
```

- `model_validate`：创建并校验模型。
- `model_dump`：把已经创建的模型转换成输出结构。

### 19.13 Depends 传函数还是调用结果

```python
current_user: User = Depends(get_current_user)
```

把函数交给 FastAPI，让框架在处理请求时调用，并继续处理这个函数自身的依赖。

`Depends(get_current_user())` 会先立刻调用函数，再把返回值交给 Depends，通常不符合这里的需求。

同理，`Depends(get_db)` 中传入函数，而不是提前执行 `get_db()`。

如果自己直接调用一个写有 Depends 默认参数的普通 Python 函数，Python 不会自动帮你解析依赖；这种注入行为发生在 FastAPI 管理的调用流程中。

<a id="11-references"></a>

## 20. 官方参考资料

笔记中的项目说明来自本对话已查看的本地代码；以下官方资料用于进一步查询框架和语言行为。文档网站的最新版本可能高于项目锁定版本，需要结合依赖版本阅读。

### 20.1 Python 与后端

- [Python 虚拟环境](https://docs.python.org/3.13/library/venv.html)
- [FastAPI 第一个应用](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [FastAPI 请求体](https://fastapi.tiangolo.com/tutorial/body/)
- [FastAPI 多文件项目与路由](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI 带 yield 的依赖](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
- [FastAPI 异常处理](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [FastAPI 直接返回响应](https://fastapi.tiangolo.com/advanced/response-directly/)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [FastAPI Bearer token 与安全机制](https://fastapi.tiangolo.com/tutorial/security/first-steps/)
- [FastAPI JWT 身份验证](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic 配置](https://docs.pydantic.dev/latest/concepts/config/)
- [Pydantic 模型](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic 序列化与 model_dump](https://docs.pydantic.dev/latest/concepts/serialization/)
- [SQLAlchemy 数据库引擎](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [SQLAlchemy ORM 入门](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
- [PyMySQL 安装](https://pymysql.readthedocs.io/en/latest/user/installation.html)
- [bcrypt 项目说明](https://github.com/pyca/bcrypt)
- [PyJWT 使用说明](https://pyjwt.readthedocs.io/en/stable/usage.html)
- [PyJWT API 与异常](https://pyjwt.readthedocs.io/en/stable/api.html)

### 20.2 前端

- [Vue 入门](https://vuejs.org/guide/quick-start.html)
- [Vue 响应式基础](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)
- [Vue 组合式函数](https://vuejs.org/guide/reusability/composables.html)
- [Vue onMounted](https://vuejs.org/api/composition-api-lifecycle.html#onmounted)
- [Vue Router 页面导航](https://router.vuejs.org/guide/essentials/navigation.html)
- [Vue Router 导航守卫](https://router.vuejs.org/guide/advanced/navigation-guards.html)
- [Vite 环境变量](https://vite.dev/guide/env-and-mode)
- [Axios 实例](https://axios-http.com/docs/instance)
- [Axios 响应结构](https://axios-http.com/docs/res_schema)
- [Axios 拦截器](https://axios-http.com/docs/interceptors)
- [Element Plus 表单](https://element-plus.org/en-US/component/form.html)
- [JavaScript import](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Statements/import)
- [JavaScript Promise](https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Promise)

### 20.3 LangChain 与 LangGraph

本项目按 requirements.txt 的锁定版本和实际源码讲解；在线文档可能继续演进，示例导入路径应与安装版本核对。

- [LangChain 工具定义](https://docs.langchain.com/oss/python/langchain/tools)：函数签名、类型与工具描述。
- [模型的工具调用](https://docs.langchain.com/oss/python/langchain/models#tool-calling)：工具绑定与模型消息。
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)：状态、reducer、节点、边与编译。
- [tools_condition](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/tools_condition)：工具路径与结束条件。
- [ToolNode](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/ToolNode)：工具执行节点。
- [图执行步数限制](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit)：recursion_limit 的单位与边界。

### 20.4 SSE、流式解码与异步生命周期

- [MDN：SSE 消息格式](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)。
- [MDN：TextDecoder.decode](https://developer.mozilla.org/en-US/docs/Web/API/TextDecoder/decode)。
- [LangGraph：流式机制](https://docs.langchain.com/oss/python/langgraph/streaming)；本项目具体使用 astream_events，事件字段还需核对锁定版本。
- [FastAPI：yield 依赖与 StreamingResponse](https://fastapi.tiangolo.com/advanced/advanced-dependencies/#dependencies-with-yield-and-streamingresponse-technical-details)。
- [Python：asyncio.to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)。
- [DeepSeek：思考模式与工具调用](https://api-docs.deepseek.com/guides/thinking_mode/)。
