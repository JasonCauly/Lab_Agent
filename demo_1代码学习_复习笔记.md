# demo_1代码学习：复习笔记与后续任务

整理日期：2026-10-20。

> **使用方式**：先阅读概念和执行流程，再对照文件看代码。代码块中标明了文件路径。末尾的待办清单区分“已经讲过”和“尚待讲解、验证”。
>
> **最终目标**：理解 lab-agent 的设计与代码，并能够从空目录创建、配置、运行和检查项目。
>
> **当前进度**：第 16 节新增实验室与设备预约提交教程；第 17 节讲解事务锁、设备归属、用户名唯一约束、关联删除、表单和 JWT 等修补，以及登录请求竞态处理。预约查询、审核、取消尚未实现；旧库迁移、真实 MySQL 并发与浏览器验收、全项目从零复现仍需完成。章节按日期保留历史代码，最新行为以相应更新章节为准。
>
> **验证说明**：此前部分基础示例完成过验证。本笔记已经完成目录链接、代码块和整合示例的静态检查，但注册登录、身份验证等整合功能仍需在学习副本中实际运行确认。“已经讲过”不等于“已经在你的学习副本验证通过”。

本笔记没有保存原项目的数据库密码、JWT 密钥或真实 token。配置示例中的占位符需要换成学习环境自己的值。

## 目录

1. [项目是什么，以及如何从零设计](#01-overview)
2. [目录、环境与第一个前后端请求](#02-start)
3. [配置、数据库与用户模型](#03-database)
4. [统一响应与异常处理](#04-response)
5. [注册与登录的后端代码](#05-auth-backend)
6. [验证 token 与获取当前用户](#06-current-user)
7. [前端请求、登录状态与页面代码](#07-frontend)
8. [本对话中的语法问答](#08-questions)
9. [启动、检查与常见问题](#09-check)
10. [尚未完成的工作和最终验收](#10-pending)
11. [官方参考资料](#11-references)
12. [新增教程：个人信息查询、修改、头像上传与开发代理](#12-profile)
13. [新增教程：密码修改、用户分页列表与管理员增删改](#13-user-management)
14. [新增教程：实验室管理与设备列表管理](#14-lab-equipment)
15. [新增教程：学生端实验室列表、详情与关联设备浏览](#15-lab-browse)
16. [新增教程：实验室与设备预约提交](#16-reservation)
17. [新增教程：逻辑修补、事务并发与回归验证](#17-logic-fixes)

<a id="01-overview"></a>

## 1. 项目是什么，以及如何从零设计

### 1.1 四个主要角色

| 部分 | 负责什么 | 例子 |
| --- | --- | --- |
| 前端 | 显示页面、接收操作、发出请求 | 登录页、注册页、菜单 |
| 后端 | 校验输入、处理业务、检查身份、访问数据库 | 判断密码是否正确、创建用户 |
| 数据库 | 持久保存数据 | 用户账号、密码哈希、昵称 |
| HTTP | 让浏览器与后端交换信息 | POST 登录、GET 用户信息 |

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

| 项目 | 后端端口 | 前端端口 | 用途 |
| --- | --- | --- | --- |
| 原 lab-agent | 8000 | 5173 | 对照原代码 |
| learning-demo | 8001 | 5174 | 练习从零编写 |

原项目目前已查看的功能包括注册、登录、获取当前用户和文件上传。实验室、设备等部分前端页面主要是占位内容；不能仅凭项目名称推断已存在完整的 Agent 或实验室业务。

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
import { ref } from 'vue'
import axios from 'axios'

const name = ref('student')
const message = ref('')

async function sayHello() {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_API_BASE_URL}/hello`,
      {
        params: { name: name.value },
        timeout: 5000
      }
    )

    message.value = response.data.message
  } catch {
    message.value = '请求失败，请检查后端是否启动'
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

| 名称 | 理解方式 |
| --- | --- |
| engine | 管理数据库连接与连接池 |
| SessionLocal | 创建数据库会话的工厂 |
| db | 某次使用的数据库会话 |
| Base | 所有数据库模型共用的父类 |
| get_db | 给接口提供数据库会话，并在结束后关闭 |

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

`Response.success(...)` 创建一个响应数据对象，不会自己发出 HTTP 请求。`cls` 和 `@classmethod` 的具体解释见第 8 节。

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

| 情况 | 异常 | 学习副本的 HTTP 状态 | JSON code |
| --- | --- | --- | --- |
| 账号已存在 | BusinessException | 200 | 409 |
| 账号或密码错误 | BusinessException | 200 | 400 |
| 登录凭证无效 | HTTPException | 401 | 401 |
| 当前账号被禁用 | HTTPException | 403 | 403 |
| 请求字段不符合规则 | RequestValidationError | 422 | 422 |
| 未被以上处理器处理的服务器错误 | Exception | 500 | 500 |

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

普通接口返回 Pydantic 模型时，FastAPI 可以处理序列化。自己构造 `JSONResponse` 时，需要先准备可编码的内容；`.model_dump()` 的详细解释见第 8 节。

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

### 5.4 注册与登录的业务逻辑

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

### 5.5 注册与登录接口

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

<a id="06-current-user"></a>

## 6. 验证 token 与获取当前用户

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

| 前缀与路径 | 最终地址 | 方法 |
| --- | --- | --- |
| /api + /auth + /register | /api/auth/register | POST |
| /api + /auth + /login | /api/auth/login | POST |
| /api + /user + /info | /api/user/info | GET |

### 6.4 当前进度的后端入口整合版

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

<a id="07-frontend"></a>

## 7. 前端请求、登录状态与页面代码

下面是当前教学进度的前端整合版。先保留简单布局，完整侧栏、菜单和嵌套路由教学留到后续。

### 7.1 安装依赖与设置路径别名

在学习副本 `frontend` 目录运行：

```powershell
npm.cmd install axios@1.20.0 element-plus@2.14.6 vue-router@5.3.1 @element-plus/icons-vue --save-exact
```

前面安装过 Axios 的话，可以按实际情况只安装缺少的包。保留 npm 更新的锁文件。

`frontend/vite.config.js`：

```js
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
```

因此：

```js
import request from '@/utils/request'
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
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

createApp(App)
  .use(router)
  .use(ElementPlus, { locale: zhCn })
  .mount('#app')
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
const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUserInfo() {
  const raw = localStorage.getItem(USER_KEY)

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setUserInfo(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

export function logout() {
  removeToken()
  removeUserInfo()
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
import { ref } from 'vue'
import {
  getUserInfo,
  setToken,
  setUserInfo,
  logout
} from './auth'

const userInfo = ref(getUserInfo())

export function useUser() {
  function saveLoginData(data) {
    setToken(data.token)
    setUserInfo(data.user)
    userInfo.value = data.user
  }

  function updateUser(user) {
    setUserInfo(user)
    userInfo.value = user
  }

  function reloadUser() {
    userInfo.value = getUserInfo()
  }

  return {
    userInfo,
    saveLoginData,
    updateUser,
    reloadUser
  }
}

export function clearLoginData() {
  logout()
  userInfo.value = null
}
```

`userInfo` 在函数外定义，因此同一前端应用中，多个组件调用 `useUser()` 得到的是同一个 ref。

`clearLoginData` 是上一节为学习副本添加的函数，确保退出登录时也清空内存中的用户信息。原项目之前读取的 `user.js` 没有这个函数。

只修改 localStorage 不会自动触发 Vue 界面更新；只修改 ref 又不会自动持久保存。以上函数同时完成两项工作。

### 7.5 Axios 请求封装

`frontend/src/utils/request.js`：

```js
import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'
import { getToken } from '@/utils/auth'
import { clearLoginData } from '@/utils/user'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000
})

function handleUnauthorized(message) {
  ElMessage.error(message || '登录已过期，请重新登录')
  clearLoginData()
  router.replace('/login')
}

service.interceptors.request.use(
  config => {
    const token = getToken()

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  error => Promise.reject(error)
)

service.interceptors.response.use(
  response => {
    const data = response.data

    if (data.code === 401) {
      handleUnauthorized(data.message)
      return Promise.reject(data)
    }

    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
    }

    return data
  },
  error => {
    if (error.response) {
      const status = error.response.status
      const message = error.response.data?.message

      if (status === 401) {
        handleUnauthorized(message)
      } else {
        ElMessage.error(message || '请求失败')
      }
    } else {
      ElMessage.error('网络异常，请检查后端服务')
    }

    return Promise.reject(error)
  }
)

export default service
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

### 7.6 前端 API 文件

`frontend/src/api/auth.js`：

```js
import request from '@/utils/request'

export function registerApi(data) {
  return request({
    url: '/api/auth/register',
    method: 'post',
    data
  })
}

export function loginApi(data) {
  return request({
    url: '/api/auth/login',
    method: 'post',
    data
  })
}
```

`frontend/src/api/user.js`：

```js
import request from '@/utils/request'

export function getUserInfoApi() {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}
```

`data` 是对象属性简写，相当于 `data: data`。这个包装函数的 `return` 返回 Promise，具体解释见第 8 节。

### 7.7 注册页

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

      <el-button
        type="primary"
        :loading="loadingValue"
        @click="register"
      >
        注册
      </el-button>
    </el-form>

    <router-link to="/login">已有账号，去登录</router-link>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

import { registerApi } from '@/api/auth'

const router = useRouter()
const formRef = ref()
const loadingValue = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

function validateConfirmPassword(rule, value, callback) {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.password) {
    callback(new Error('两次密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { min: 3, max: 50, message: '账号长度为 3～50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function register() {
  const valid = await formRef.value.validate().catch(() => false)

  if (!valid) {
    return
  }

  loadingValue.value = true

  try {
    const res = await registerApi(form)

    if (res.code === 200) {
      ElMessage.success('注册成功')
      await router.push('/login')
    }
  } catch {
    // request.js 已显示请求错误。
  } finally {
    loadingValue.value = false
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

### 7.8 登录页

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

      <el-button
        type="primary"
        :loading="loadingValue"
        @click="login"
      >
        登录
      </el-button>
    </el-form>

    <router-link to="/register">没有账号，去注册</router-link>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'

const router = useRouter()
const formRef = ref()
const loadingValue = ref(false)
const { saveLoginData } = useUser()

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

async function login() {
  const valid = await formRef.value.validate().catch(() => false)

  if (!valid) {
    return
  }

  loadingValue.value = true

  try {
    const res = await loginApi(form)

    if (res.code === 200) {
      saveLoginData(res.data)
      ElMessage.success('登录成功')
      await router.push('/manager/home')
    }
  } catch {
    // request.js 已显示请求错误。
  } finally {
    loadingValue.value = false
  }
}
</script>
```

`saveLoginData` 接收的是 `res.data`，其中包含 `token` 和 `user`，不是整个 `res`。

### 7.9 首页

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

    <el-button :disabled="loading" @click="handleLogout">
      退出登录
    </el-button>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getUserInfoApi } from '@/api/user'
import { useUser, clearLoginData } from '@/utils/user'

const router = useRouter()
const { userInfo, updateUser } = useUser()

const loading = ref(true)
const loadError = ref('')

async function loadUser() {
  loading.value = true
  loadError.value = ''

  try {
    const res = await getUserInfoApi()

    if (res.code === 200) {
      updateUser(res.data)
    } else {
      loadError.value = res.message || '用户信息获取失败'
    }
  } catch {
    loadError.value = '用户信息获取失败，请重试'
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  clearLoginData()
  await router.replace('/login')
}

onMounted(loadUser)
</script>
```

`onMounted(loadUser)` 是注册回调，在组件挂载后调用函数。`onMounted(loadUser())` 会先调用函数，再把它的返回值传进去，含义不同。

首页获取数据期间显示加载状态，成功后才显示用户资料。

### 7.10 最小布局与路由守卫

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
import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/manager/home'
    },
    {
      path: '/login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/register',
      component: () => import('@/views/Register.vue')
    },
    {
      path: '/manager',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        {
          path: 'home',
          component: () => import('@/views/Home.vue')
        }
      ]
    }
  ]
})

router.beforeEach(to => {
  if (to.path === '/login' || to.path === '/register') {
    return true
  }

  return getToken() ? true : '/login'
})

export default router
```

- 外层 App 的 `router-view` 显示 Layout。
- Layout 的 `router-view` 显示子页面 Home。
- 子路径 `home` 与父路径 `/manager` 合成 `/manager/home`。
- `beforeEach` 在导航前执行，返回 true 放行，返回路径进行重定向。
- 这个守卫只检查 token 是否存在；后端验证其真实性和有效期。
- `push` 通常增加历史记录，`replace` 替换当前历史记录。

完整布局、侧栏菜单、选中项与路由的对应关系尚待下一节展开。

<a id="08-questions"></a>

## 8. 本对话中的语法问答

这一节按你问过的问题整理，可以独立复习。

### 8.1 @router.post("/login") 怎样把前后端联系起来

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

### 8.2 cls 是什么

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

### 8.3 不使用 cls 怎样写

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

### 8.4 为什么 request({...}) 会调用 service

`request.js`：

```js
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL
})

export default service
```

`api/auth.js`：

```js
import request from '@/utils/request'
```

默认导入的本地名字是 `request`，它引用的就是默认导出的 `service`。

Axios 创建的实例可以作为函数调用，因此：

```js
request({
  url: '/api/auth/login',
  method: 'post',
  data: form
})
```

就是调用那个 Axios 实例发出请求。JavaScript 不会因为名字叫 `request` 就自动寻找一个叫 `service` 的函数，联系来自 import/export。

### 8.5 import request 能改成 import service 吗

可以：

```js
import service from '@/utils/request'

export function loginApi(data) {
  return service({
    url: '/api/auth/login',
    method: 'post',
    data
  })
}
```

默认导入允许自行选择本地名字。改名后，这个文件中的调用也要改成 `service(...)`。

具名导入规则不同：

```js
import { useUser } from '@/utils/user'
```

它匹配导出的名字；如需改本地名字，可以显式使用别名：

```js
import { useUser as getUserState } from '@/utils/user'
```

### 8.6 export default service 的作用

它把 `service` 指定为这个模块的默认导出，其他文件可以通过默认导入使用同一个实例。

- 不会在这行代码中发 HTTP 请求。
- 不会把变量名强制规定成 `service`。
- 一个模块只能有一个默认导出，但可以有多个具名导出。
- 多个文件导入此模块，在同一模块运行环境中通常共享同一个已创建实例。

`export default service` 导出的是变量的值；`export default service()` 会先调用，再导出返回值，行为不同。

### 8.7 loginApi 的 return 到底返回什么

```js
export function loginApi(data) {
  return request({
    url: '/api/auth/login',
    method: 'post',
    data
  })
}
```

立即返回的是 **Promise 对象**，表示一个尚在进行或已经完成的异步操作。

```js
const promise = loginApi(form)
```

在当前封装下：

```js
const res = await loginApi(form)
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

| 表达式 | 含义 |
| --- | --- |
| 原始 Axios response.data | 整个后端 JSON 内容 |
| 当前页面 res.data | 后端 JSON 内部的业务 data，例如 token 和 user |

网络错误或被拒绝的 Promise 会让 `await` 抛出异常，进入 `catch`。

HTTP 200 但业务 code 为 400 的请求，在当前拦截器中仍可能成功返回，因此不能把“await 没报错”直接等同于“登录成功”。

### 8.8 async、await 和 Promise 的关系

- Promise 表示异步操作的结果。
- `async` 函数返回 Promise，即使其中 return 的是普通值。
- `await` 等待 Promise 成功后取得值；失败时在当前位置抛出异常。
- 等待网络时，并不是把整个浏览器界面停住。
- `Promise.reject(error)` 产生拒绝状态的 Promise，将错误继续交给调用方。

页面的 `finally` 会在成功或失败后执行，所以适合恢复：

```js
loadingValue.value = false
```

### 8.9 userInfo 在其他文件怎么调用

```vue
<template>
  <p>欢迎你：{{ userInfo?.name }}</p>
</template>

<script setup>
import { useUser } from '@/utils/user'

const { userInfo, updateUser } = useUser()

function changeName() {
  if (userInfo.value) {
    updateUser({
      ...userInfo.value,
      name: '新的昵称'
    })
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

### 8.10 .env 如何被 DATABASE_URL 读取

`DATABASE_URL` 是声明的配置字段。`env_file` 告诉 BaseSettings 到哪里读文件。实例化 `Settings()` 时，库按字段名匹配环境变量和文件内容。

不是 `DATABASE_URL` 自己去“引用 model_config”；是 BaseSettings 同时读取配置规则和字段声明，再组装对象。

```text
.env 中：DATABASE_URL=...
Settings 中：DATABASE_URL: str
Settings()：查找、转换、校验
settings.DATABASE_URL：访问已经加载的值
```

`model_config`、`env_file` 不可以随意换名字，因为它们是库识别的约定名称。`BASE_DIR`、`settings` 等自定义变量可以改名，但引用必须一起修改。

### 8.11 .model_dump() 的作用

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

| 写法 | 结果 |
| --- | --- |
| result.model_dump() | Python 字典；默认 Python 模式 |
| result.model_dump(mode="json") | 字典，字段转换为 JSON 支持的类型 |
| result.model_dump_json() | JSON 字符串 |

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

### 8.12 model_validate 与 model_dump 的区别

```text
数据库对象 / 输入数据
  → UserResponse.model_validate(...)
  → Pydantic 模型
  → .model_dump()
  → Python 字典
```

- `model_validate`：创建并校验模型。
- `model_dump`：把已经创建的模型转换成输出结构。

### 8.13 Depends 传函数还是调用结果

```python
current_user: User = Depends(get_current_user)
```

把函数交给 FastAPI，让框架在处理请求时调用，并继续处理这个函数自身的依赖。

`Depends(get_current_user())` 会先立刻调用函数，再把返回值交给 Depends，通常不符合这里的需求。

同理，`Depends(get_db)` 中传入函数，而不是提前执行 `get_db()`。

如果自己直接调用一个写有 Depends 默认参数的普通 Python 函数，Python 不会自动帮你解析依赖；这种注入行为发生在 FastAPI 管理的调用流程中。

<a id="09-check"></a>

## 9. 启动、检查与常见问题

### 9.1 当前学习副本的创建顺序

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

### 9.2 两个终端分别启动

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

### 9.3 后端检查

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

### 9.4 前端检查清单

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

### 9.5 无效 token 实验

在学习副本页面的浏览器 Console 中执行：

```js
localStorage.setItem('token', 'not-a-valid-token')
location.reload()
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

### 9.6 看浏览器 Network 时关注什么

| 位置 | 看什么 |
| --- | --- |
| Request URL | 最终地址和端口是否正确 |
| Request Method | GET 或 POST 是否与后端匹配 |
| Request Headers | 是否带 Authorization |
| Payload | 请求体字段及值 |
| Status Code | HTTP 200、401、403、422、500 等 |
| Response | JSON 中 code、message、data |

如果看到 OPTIONS 请求，可能是浏览器在做跨域预检；它不等于业务接口被重复调用。

### 9.7 常见问题

| 现象 | 首先检查 |
| --- | --- |
| 连接失败 | MySQL、后端是否启动，端口是否正确 |
| ModuleNotFoundError | 是否用学习副本的 Python，依赖是否安装，启动目录是否正确 |
| 前端提示找不到 @/... | vite.config.js 是否设置别名，路径和大小写是否一致 |
| 浏览器 CORS 错误 | allow_origins 是否包含实际前端来源 |
| 设置 DATABASE_URL 后仍连接到其他库 | 同名进程环境变量、是否重启、是否启动了正确项目 |
| 新加模型字段未出现在旧表 | create_all 不负责迁移已有表结构 |
| 401 | 是否带 token，是否过期，是否与当前密钥匹配 |
| 403 | 身份已识别，但账号状态或权限不允许 |
| 422 | 请求字段类型、长度、必填条件是否符合后端模型 |
| 页面 res.data 与预期不同 | 是否已经经过响应拦截器解包 |
| localStorage 更新但页面没变化 | 是否同步更新了响应式 userInfo |
| 默认导入改名后报未定义 | 是否也修改了这个文件中的调用名 |
| 登录后切换 localhost / 127.0.0.1 就丢状态 | 浏览器来源不同，存储不同 |

本笔记中的全局错误响应只给出通用提示。进一步定位服务器错误需要结合后端终端堆栈与日志，相关排错教学尚未完成。

### 9.8 前 11 节的检查记录（2026-10-10）

整理时已完成以下检查：

- UTF-8 中文内容读取正常，没有未填完的章节占位标记。
- 11 个目录锚点与正文对应，代码块的围栏成对闭合。
- 16 个完整后端参考文件通过 Python 编译语法检查。
- 8 个完整 JavaScript 参考文件通过 Node.js 语法检查。
- 7 个 Vue 示例通过组件解析与模板编译；其中 5 个包含脚本的示例也通过脚本编译。
- 后端参考文件中的 app 模块引用与笔记提供的目录对应。

这些检查没有启动整合后的前后端，也没有代替第 9.4 节的实际功能验收。问答中的局部语法片段需要结合上下文阅读，不能一律当作完整文件运行。

<a id="10-pending"></a>

## 10. 尚未完成的工作和最终验收

### 10.1 已经讲解的内容

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
- [x] 字典 ** 解包、设备表单重置与分页字段对照。

### 10.2 已讲解：页面布局与前端路由（见第 12 节）

- [x] 按原项目 Layout.vue 讲解页头、侧栏和内容区域。
- [x] 讲清父路由、children 与两层 router-view 的显示关系。
- [x] 说明菜单点击导航及当前 default-active 固定值的行为。
- [x] 区分页面名称、菜单文案、路由路径与后端权限。
- [x] 说明首页、实验室、设备、用户和 Profile 的现有路由。
- [x] 说明哪些页面有真实功能，哪些只是占位内容。
- [ ] 检查或调整当前路径与菜单高亮的对应关系。
- [ ] 完成一次导航、刷新、退出登录的检查。

### 10.3 已讲解：文件上传与文件访问（完整运行检查待完成）

- [x] 讲解 UploadFile、multipart/form-data 和表单文件请求。
- [x] 核对当前环境与依赖清单的差异。
- [ ] 核对并补齐 python-multipart 等上传依赖。
- [x] 按原项目 files.py 解释文件名、扩展名和大小校验。
- [x] 解释生成新文件名、分块读取与写入目录。
- [x] 讲解 UPLOAD_DIR、StaticFiles 和 /uploads 挂载。
- [x] 说明磁盘文件路径与浏览器访问 URL 的区别。
- [x] 讲解你新编写的前端上传请求与 Profile 头像页面。
- [ ] 检查上传成功、类型不允许、超过大小限制等情况。
- [ ] 结合真实需求明确上传接口是否要求登录。

### 10.4 后续：后端结构与排错

- [ ] 从 main.py 重新串联模块加载、配置读取、建表和注册路由。
- [ ] 系统梳理 api、services、models、schemas、dependencies、utils、common 的职责。
- [ ] 对照原项目解释调用链，而不是只记住文件夹名称。
- [ ] 展开数据库事务、会话关闭和异常处理顺序。
- [ ] 说明建表与数据库迁移的区别，核对用户名唯一约束。
- [ ] 讲解终端堆栈、浏览器 Console 和 Network 的排错方式。
- [ ] 核对 JWT 时间、异常捕获及接口文档认证方式的实现差异。
- [ ] 说明前端退出仅清除本地状态，当前 JWT 方案没有服务端即时撤销机制。

这些核对项不代表已经发现并修复了原项目全部问题；实施调整前需要确定学习副本与原项目的范围。

### 10.5 后续：完整的从零复现

- [ ] 提供最终目录结构与文件创建顺序。
- [ ] 整理所有依赖与版本、前后端环境配置样例。
- [ ] 整理数据库创建和初始化方式。
- [ ] 核对前后端启动命令、端口和 CORS。
- [ ] 完成注册、登录、用户信息、导航、上传等端到端检查。
- [ ] 整理常见错误与定位步骤。
- [ ] 完成一次不依赖原项目运行目录的重新创建。
- [ ] 更新本笔记，使内容与最终复现版本一致。

### 10.6 何时才能说“全部教程完成”

需要同时达到：

1. 原项目实际已有功能的主要代码已解释清楚。
2. 你能说明一次请求经过哪些前后端文件，以及每层的职责。
3. 你能自行准备依赖、配置数据库并启动两端。
4. 你能从空目录复现已经约定的项目功能，而不只是复制某一段代码。
5. 正常流程和重要失败场景完成实际检查。
6. 尚未实现的占位页面与已实现功能的边界已经明确。

目前尚未达到全部条件，因此整个教程仍在进行中。

### 10.7 建议的复习练习

1. 不看笔记，口述从点击登录按钮到首页显示昵称的过程。
2. 修改 /hello 的默认名字，说明改动为什么会影响响应。
3. 给注册模型加入一个简单规则，再检查前后端分别如何报错。
4. 将默认导入 request 改为 service，并修改调用，观察功能是否一致。
5. 用无效 token 解释为什么路由守卫放行后，后端仍能拒绝请求。
6. 比较 Response 对象、Python 字典、JSON 字符串和前端对象。
7. 对照第 9 节检查自己的学习副本，把实际通过的项目勾选出来。

### 10.8 本次新增功能尚待处理与验收

- [x] 当前 Profile 已移除未定义的 handleAvatarSuccess 绑定（2026-10-14 已核对）。
- [ ] 让自定义上传 Promise 明确表达业务成功与失败。
- [ ] 检查上传未完成时提前保存资料的行为。
- [ ] 补齐资料修改的后端格式与长度校验。
- [ ] 明确 null、空字符串与“清空字段”的更新语义。
- [ ] 检查查询资料和退出登录时的共享 userInfo 同步。
- [x] python-multipart 已加入 requirements.txt 并固定版本（2026-10-20 核对）。
- [ ] 将直接使用的图标包显式列为前端依赖；当前锁文件已通过 Element Plus 包含该传递依赖。
- [ ] 完成第 12.17 节的真实浏览器与数据库功能检查。

### 10.9 密码与用户管理的新增待办（第 13 节）

- [x] 本人资料服务已排除 role/status，隔离验证确认不再通过该路径修改（2026-10-15）。
- [ ] 可选整理：按本人和管理员用途拆分输入模型，使字段范围更明确。
- [ ] 设置后端密码长度及字节校验，统一各入口规则并遮盖密码输入。
- [ ] 统一 status 的布尔值与单选框类型。
- [ ] 解决创建模型名称可缺失与数据库 NOT NULL 的冲突。
- [ ] 约束分页参数与角色允许值。
- [x] 用户删除已捕获取消、关闭及请求失败；有预约记录时后端拒绝删除并提示禁用（2026-10-20，见第 17 节）。
- [ ] 明确自我禁用、自我降级和当前用户缓存同步策略。
- [ ] 准备学习数据库的初始管理员，完成第 13.22 节浏览器检查。
- [ ] 若需求要求改密后所有会话失效，增加相应服务端机制。

### 10.10 实验室与设备管理的新增待办（第 14 节）

- [x] Equipment.vue 已按实际设备字段重置 lab_id、spec、quantity 和整数 status（2026-10-20）。
- [x] 将设备分页绑定与实际 page_size 参数统一（2026-10-19 核对已修正，见第 15.18 节）。
- [x] 实验室容量改用数字输入；后端创建必填且大于 0，更新时提供的容量也须大于 0（2026-10-20）。
- [ ] 统一实验室搜索提示、设备型号搜索提示与真实查询行为。
- [ ] 明确实验室时间格式、清空和跨夜规则。
- [ ] 处理实验室改名查重及数据库唯一约束策略。
- [x] 实验室有设备或预约记录、设备有预约记录时禁止删除，返回业务提示并处理提交时的关联冲突（2026-10-20）。
- [ ] 核对实际数据库外键，必要时单独执行迁移。
- [ ] 按数据规模考虑实验室选项加载与关系查询优化。
- [ ] 完成第 14.24 节浏览器验收，更新完整复现版本。

### 10.11 学生端实验室与设备浏览的新增待办（第 15 节）

- [x] 增加实验室卡片列表、详情接口、按实验室 ID 查询设备和对应页面路由，完成隔离检查。
- [x] 将实验室和设备的查询接口改为当前登录用户可调用，写入接口继续校验管理员依赖。
- [ ] 将实验室状态筛选的 if status 改为明确判断是否传参，并验证 False 的筛选结果。
- [ ] 明确学生能否查看停用实验室；若只允许启用资源，前后端都要落实该规则。
- [ ] 修正 LabList.vue 的 header 插槽，清理无用表单、额外列表请求及未导入 nextTick 的闲置逻辑。
- [ ] 整理菜单重复属性，确定设备详情页的菜单高亮规则。
- [ ] 如需支持同页切换实验室，监听路由 lab_id，重置分页并处理请求先后顺序。
- [x] 预约按钮已接入公共弹窗、POST 接口和预约表，保存待审核记录；加入资源及重叠检查和并发保护（2026-10-20，第 16、17 节）。
- [ ] 补齐预约查询、审核、取消；完善日期、零时长、数量和实验室/设备互斥规则。
- [ ] 完成第 15.22 节真实浏览器验收，并与前面章节合并进行从零复现检查。

### 10.12 预约与修补后的新增验收（第 16、17 节）

- [x] 完成预约提交及 7 项指定修补的代码讲解，核对审查报告与当前代码的对应状态。
- [x] 重新运行 19 项后端隔离回归测试、前端构建，以及预约弹窗和旧会话 401 的函数检查。
- [ ] 在有备份的学习库核对 lab → labs 的数据、ID 和外键迁移；当前没有这项自动迁移脚本。
- [ ] 旧 users 表检查重复账号并执行用户名唯一索引升级；本次未对现有数据库执行。
- [ ] 在真实 MySQL/InnoDB 环境验证并发预约、锁等待和回滚。
- [ ] 完成第 16.19 节浏览器验收；第 17.16 节未解决项继续跟进。
- [ ] 在空目录、空学习数据库中完成一次安装、初始化、管理资源和提交预约的完整复现。

<a id="11-references"></a>

## 11. 官方参考资料

笔记中的项目说明来自本对话已查看的本地代码；以下官方资料用于进一步查询框架和语言行为。文档网站的最新版本可能高于项目锁定版本，需要结合依赖版本阅读。

### Python 与后端

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

### 前端

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

---

<a id="12-profile"></a>

## 12. 新增教程：个人信息查询、修改、头像上传与开发代理

更新时间：2026-10-12。本节根据本次读取的当前原项目代码讲解。

> 第 1～11 节保留此前学习副本的教学版本；本节记录你新编写的原项目实现。两个版本的函数名称、接口配置和端口可能不同。
>
> 本节已完成代码阅读、语法检查和隔离的数据库服务验证，未对你的真实数据库执行修改，也未改动业务源码。浏览器中的完整交互仍需要按末尾清单检查。

### 12.1 这次新增功能的整体设计

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

### 12.2 这次文件分别负责什么

| 文件 | 本次职责 |
| --- | --- |
| backend/app/services/user_service.py | 把输入模型转换成字段和值，修改用户对象并提交数据库 |
| backend/app/schemas/user.py | 定义用户返回结构和允许修改的字段，返回结构加入 avatar |
| backend/app/schemas/files.py | 定义上传文件返回的名称、大小和访问地址 |
| backend/app/api/user.py | 注册 GET 查询和 PUT 修改接口，取得当前登录用户 |
| backend/app/api/files.py | 检查文件并保存到磁盘，返回 FileResponse |
| frontend/src/api/user.js | 封装查询和修改个人资料的 HTTP 请求 |
| frontend/src/api/files.js | 使用 FormData 封装文件上传请求 |
| frontend/src/views/Profile.vue | 显示资料、校验输入、上传头像、保存修改 |
| frontend/src/layouts/Layout.vue | 显示共享的昵称与头像，提供个人信息入口 |
| frontend/src/router/index.js | 将 /manager/profile 映射到 Profile.vue |
| frontend/.env.development | API baseURL 改为留空，使用相对地址 |
| frontend/vite.config.js | 开发时将 /api 和 /uploads 转发到后端 |

还需要联动理解已有的 `request.js`、`utils/user.js`、`utils/auth.js`、`dependencies/auth.py`、`models/user.py`、`main.py` 和 `config.py`。

本次涉及的地址：

| 操作 | 地址 | 方法 | 内容 |
| --- | --- | --- | --- |
| 查询本人资料 | /api/user/info | GET | 请求头携带 token |
| 修改本人资料 | /api/user/update | PUT | JSON 对象 |
| 上传文件 | /api/files/upload | POST | multipart/form-data |
| 读取头像图片 | /uploads/生成的文件名 | GET | 浏览器根据 img 的 src 请求 |

### 12.3 查询资料：从导航到填充表单

#### 第一步：点击个人信息

Layout 中：

```js
const goPerson = () => {
  router.push('/manager/profile')
}
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
  loadUserInfo()
})
```

组件挂载后，回调调用 `loadUserInfo`。函数设置：

```js
loading.value = true
```

表单上的 `v-loading="loading"` 使用 Element Plus 的加载指令显示遮罩。finally 把 loading 恢复为 false，成功失败都会结束加载状态。

#### 第三步：前端 API 发请求

当前 `frontend/src/api/user.js` 的查询函数名是 `getUserInfo`：

```js
export function getUserInfo() {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}
```

它与 `utils/auth.js` 中同名函数的职责不同：

| 函数来源 | 实际动作 |
| --- | --- |
| @/api/user 的 getUserInfo | 发 HTTP 请求，得到 Promise |
| @/utils/auth 的 getUserInfo | 从 localStorage 读取缓存，直接返回对象或 null |

看调用时要看 import 的路径，不能只看函数名字。同一个文件需要使用两者时，可以通过 `as` 给其中一个导入起别名。

`request.js` 会添加 Authorization，并将 Axios 原始响应中的 data 返回给页面。所以：

```js
const res = await getUserInfo()
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
  Object.assign(form, res.data)
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

### 12.4 UserResponse：让接口返回头像

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

### 12.5 UserUpdateRequest：定义允许修改的范围

> 历史版本提示：下面是 2026-10-12 的字段范围。2026-10-14 的模型已经加入 role/status，因此“不处理角色”的旧结论不再适用于当前本人接口；见第 13.2 节。

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

### 12.6 PUT 修改接口与 Depends

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

| 参数 | 来源 |
| --- | --- |
| data | JSON 请求体，经 UserUpdateRequest 校验 |
| current_user | 身份依赖验证 token 后查询到的用户 |
| db | 数据库会话依赖 |

前端不能通过提交其他用户 ID 指定要修改谁。当前修改对象由身份依赖确定。

get_current_user 内部也依赖 get_db。FastAPI 在同一次请求中默认缓存依赖结果，因此这里两处使用同一个 get_db 时通常得到同一个会话。当前用户是该会话已经查询并管理的对象，可以直接修改其属性后提交。[FastAPI 子依赖与缓存](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)

本接口使用 PUT，但实现方式是“只修改部分提供了非 None 值的字段”。从行为上看属于部分更新；HTTP 方法本身不会自动产生数据库修改。

### 12.7 核心：model_dump、items、setattr、commit

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

| 请求内容 | 更新字典 | 对邮箱的影响 |
| --- | --- | --- |
| 没有 email | 不包含 email | 保持原值 |
| email 为 null | 不包含 email | 保持原值 |
| email 为 "" | 包含 email: "" | 保存空字符串 |
| email 为有效字符串 | 包含该字符串 | 保存新值 |

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

### 12.8 前端保存资料与同步页头

提交函数先校验：

```js
const valid = await formRef.value.validate().catch(() => false)
if (!valid) return
```

校验规则：

- 名称必填。
- 邮箱使用组件库的 email 类型规则。
- 手机号使用手机号格式的正则表达式。

正则 `/^1[3-9]\d{9}$/` 中：

| 片段 | 含义 |
| --- | --- |
| ^ | 从字符串开头匹配 |
| 1 | 第一个字符为 1 |
| [3-9] | 第二个字符为 3～9 的数字 |
| \d{9} | 后面跟 9 个数字 |
| $ | 匹配到字符串末尾 |

它是格式校验，不是号码存在性验证。

通过校验后：

```js
submitting.value = true

try {
  const res = await updateUserInfo(form)

  if (res.code === 200) {
    updateUser(res.data)
    ElMessage.success('更新成功')
  }
} finally {
  submitting.value = false
}
```

当前实际函数还有 catch，错误提示由 request.js 统一显示。

API 包装中的 method 是 put，data 是 form：

```js
return request({
  url: '/api/user/update',
  method: 'put',
  data
})
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

| 名称 | 所在位置 | 作用 |
| --- | --- | --- |
| updateUserInfo | @/api/user | 发请求，保存到后端 |
| update_user_info | 后端服务 | 修改 ORM 对象并提交 |
| updateUser | @/utils/user | 更新前端缓存和共享状态 |

当前 loadUserInfo 只执行 Object.assign(form, res.data)，不会同步共享 userInfo。因此，查询到新资料会更新 Profile 表单；页头共享资料在当前写法中主要通过登录和保存成功后更新。

### 12.9 ref、reactive、computed 与页面状态

| 变量 | 类型 | 用途 |
| --- | --- | --- |
| loading | ref | 控制查询过程的加载遮罩 |
| submitting | ref | 控制保存按钮的加载状态 |
| formRef | ref | 存放表单组件实例，以调用 validate |
| form | reactive | 保存当前编辑的资料 |
| roleLabel | computed | 把角色代码映射成显示文字 |
| userInfo | 共享 ref | 保存布局等组件使用的用户状态 |

form 和共享 userInfo 是两份不同用途的数据：form 保存未提交的编辑内容，userInfo 保存共享的用户资料。修改表单不会立即改变页头；保存成功调用 updateUser 后再同步。

你的计算属性：

```js
const roleLabel = computed(() => {
  return form.role === 'admin'
    ? '管理员'
    : form.role === 'student'
      ? '学生'
      : '未知角色'
})
```

computed 根据依赖计算结果，form.role 改变时它会更新。三元表达式的形式是：

```text
条件 ? 条件成立时的值 : 条件不成立时的值
```

这里只定义了 getter，所以 roleLabel 是只读计算属性。账号和角色输入框被 disabled，用户无法在页面中编辑。只用于显示时，可以用 :model-value="roleLabel" 表达这一意图，避免使用需要写回的 v-model。[Vue 计算属性](https://vuejs.org/guide/essentials/computed.html)

### 12.10 Profile 的头像上传组件

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

| 配置 | 当前含义 |
| --- | --- |
| http-request | 使用自定义函数发上传请求 |
| show-file-list=false | 不显示默认文件列表 |
| accept | 文件选择器的类型提示 |
| before-upload | 上传前检查文件 |
| on-success | 上传成功时的回调，目前绑定名称未定义 |

http-request 是组件的一个函数属性，不是后端路由，也不是 Vue 的路由导航。[Element Plus 上传组件](https://element-plus.org/en-US/component/upload.html)

Profile 模板中的 Plus 没有在该页面单独 import，但 main.js 通过遍历 ElementPlusIconsVue 全局注册图标，因此当前项目可以使用它。若迁移到前面没有全局注册的学习副本，则需要显式导入 Plus 或采用同样的注册方式。

#### 上传前检查

```js
const imageTypes = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp'
]
```

file.type 是浏览器提供的 MIME 类型，file.size 是字节数。

```js
if (!imageTypes.includes(file.type)) {
  return false
}

if (file.size / 1024 / 1024 > 2) {
  return false
}

return true
```

includes 判断数组是否包含某值。两次除以 1024 把字节换算成此处采用的 MB 量级。

before-upload 返回 false 会阻止这次上传。当前限制是图片且不超过 2 × 1024 × 1024 字节。

accept 是选择提示，before-upload 是前端检查；它们不会自动把同样的规则传给后端。

#### 自定义上传函数的参数

当前写法：

```js
const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)

    if (res.code === 200) {
      form.avatar = res.data?.url
    }
  } catch {}
}
```

`({ file })` 是对参数对象的解构。组件传入的是一个包含 file 等属性的对象，函数直接取出 file。

它相当于：

```js
const handleFileUpload = async (options) => {
  const file = options.file
  // 使用 file 上传
}
```

上传完成后 form.avatar 变为后端地址，v-if 和 img 的 :src 随着响应式属性变化而更新。此时只是更新表单预览，尚未保存用户记录。

### 12.11 files.js：FormData 上传二进制文件

当前函数：

```js
export function uploadFileApi(file) {
  const formData = new FormData()
  formData.append('file', file)

  return request({
    url: '/api/files/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
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

### 12.12 后端 files.py：接收并保存文件

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

| 位置 | 类型规则 | 大小规则 |
| --- | --- | --- |
| Profile 头像组件 | JPEG、PNG、GIF、WebP 的 MIME 类型 | 2 MB |
| 通用后端上传接口 | 配置的扩展名，包括图片、PDF、Office、ZIP | 100 MB |

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

### 12.13 FileResponse 与头像访问地址

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

| 内容 | 例子 | 谁使用 |
| --- | --- | --- |
| 磁盘路径 | backend/uploads/生成的文件名.png | 后端文件系统 |
| URL 路径 | /uploads/生成的文件名.png | 浏览器 |
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

### 12.14 .env 留空与 Vite 代理为什么配合使用

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

### 12.15 Layout、菜单、插槽与头像显示

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
const { userInfo } = useUser()
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

# 是 v-slot 的简写。这些是组件提供的具名插槽，允许你把内容放到指定区域；与 URL 的 # 锚点无关。

#### scoped 与普通样式

Profile 中第一个 style 使用 scoped，主要约束本组件样式。第二个普通 style 可以匹配组件库生成的内部 .el-upload 等元素，同时也可能影响其他使用相同类名的区域。

这里不是两个独立页面的样式文件，而是同一个 Vue 单文件组件中的两组样式规则。

### 12.16 当前代码中需要单独注意的点

本节讲解与检查只修改笔记，没有自动修复下面的业务源码。

| 当前事实 | 影响或下一步 |
| --- | --- |
| Profile 绑定 handleAvatarSuccess，但脚本没有定义 | 可能产生运行时警告；当前预览由 handleFileUpload 更新，应删除多余绑定或补齐回调 |
| 自定义上传函数 catch 为空，成功时也没有 return res | 组件得到的 Promise 可能以 undefined 成功完成；失败被吞掉后，组件也可能按成功处理 |
| request.js 对一般业务 code 非 200 仍返回成功 Promise | 上传组件不能只依赖 Promise 是否成功，还需明确处理业务 code |
| 上传过程中没有单独的 uploading 状态 | 可能在文件上传未完成时保存，提交旧头像地址 |
| UserUpdateRequest 没有格式和长度规则 | 邮箱、手机号和最大长度不能仅靠页面校验保证 |
| exclude_none=True 排除显式 null | 当前不能通过 null 清空已有可空字段，需要确认是否符合交互设计 |
| Profile 查询只更新 form | 不会把重新查询到的资料同步到页头共享状态 |
| 当前 Layout 退出只调用存储 logout | shared userInfo 没有直接清空；此前学习副本的 clearLoginData 尚未加入当前原项目 |
| 通用上传接口没有身份依赖 | 当前可以不经登录验证调用，是否加登录限制需要按需求决定 |
| 服务中 get_user_info 定义后未被 GET API 调用 | 可统一分层写法，但当前查询路径仍可以工作 |
| requirements 未列 python-multipart，package.json 未直接列 icons-vue | 当前环境已装不代表新环境能按清单稳定复现，需要补齐依赖声明 |

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
  const res = await uploadFileApi(file)

  if (res.code !== 200 || !res.data?.url) {
    throw new Error(res.message || '上传失败')
  }

  form.avatar = res.data.url
  return res
}
```

让请求失败继续拒绝，并明确拒绝业务失败；成功时给组件返回响应内容。预览已经在该函数中更新时，可以移除不存在的 on-success 绑定。

如果选择保留 on-success 回调，应定义对应函数，并明确由哪个位置负责更新预览，避免重复处理。

### 12.17 本次验证记录与实际运行检查

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

| 依赖 | 当前安装版本 |
| --- | --- |
| FastAPI | 0.115.13 |
| Pydantic | 2.13.5 |
| SQLAlchemy | 2.0.41 |
| python-multipart | 0.0.32 |
| @element-plus/icons-vue | 2.3.2 |

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

### 12.18 从前面学习副本继续复现这一功能

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
11. 处理第 12.16 节中的已知问题，再完成第 12.17 节的交互检查。

迁移时注意：

- 前面笔记使用 getUserInfoApi，本次原项目使用 getUserInfo，导入和调用要一致。
- 前面笔记使用 clearLoginData，本次原项目的 utils/user.js 尚未导出它。
- 前面学习副本端口为 8001/5174，本次原项目代理目标为 8000。
- schemas 的字段增加不会自动迁移旧数据库表。
- 保存旧头像替换记录，不会自动删除以前上传的磁盘文件；旧文件处理尚未实现。

不要把不同阶段的文件片段直接拼接后就认为已经完成复现，最后仍需检查实际调用名称和依赖。

### 12.19 本节复习练习

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

### 12.20 补充参考

- [Pydantic 字段排除：exclude_none、exclude_unset](https://docs.pydantic.dev/latest/concepts/serialization/)
- [FastAPI 同请求的子依赖缓存](https://fastapi.tiangolo.com/tutorial/dependencies/sub-dependencies/)
- [FastAPI 文件上传](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Vue 计算属性](https://vuejs.org/guide/essentials/computed.html)
- [Element Plus Upload 参数与回调](https://element-plus.org/en-US/component/upload.html)
- [Vite 开发代理](https://vite.dev/config/server-options.html#server-proxy)
- [MDN FormData](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest_API/Using_FormData_Objects)
- [Python setattr](https://docs.python.org/3.13/library/functions.html#setattr)

### 12.21 本次相关代码快照

下面保留本次读取的 12 个指定文件，供日后修改代码时对照。快照是当时的实际写法，包含第 12.16 节已说明的待处理问题，不是自动修正后的版本。

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
import request from '@/utils/request'

export function uploadFileApi(file) {
  const formData = new FormData()
  formData.append('file', file)

  return request({
    url: '/api/files/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
```

</details>

<details>
<summary><code>frontend/src/api/user.js</code></summary>

```js
import request from '@/utils/request'

// 获取个人信息
export function getUserInfo() {
  return request({
    url: '/api/user/info',
    method: 'get'
  })
}

// 更新个人信息
export function updateUserInfo(data) {
  return request({
    url: '/api/user/update',
    method: 'put',
    data
  })
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
        <div style="display: flex; align-items: center; font-size: 24px; font-weight: bold">
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown>
            <div style="display: flex; align-items: center; margin-right: 20px; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || '用户' }}
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goPerson">个人信息</el-dropdown-item>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
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
import { Menu as IconMenu, House, Setting, User } from '@element-plus/icons-vue'
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
const { userInfo } = useUser()

const handleLogout = () => {
  logout()
  router.push('/login')
}

const goPerson = () => {
  router.push('/manager/profile')
}
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/Home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/Lab.vue')
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue')
        },
        {
          path: 'equ',
          name: 'Equ',
          component: () => import('@/views/Equ.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/User.vue')
        }
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue')
    }
  ]
})

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken()
  if (to.path === '/login' || to.path === '/register') {
    return true
  } else {
    return token ? true : '/login'
  }
})

export default router
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getUserInfo, updateUserInfo } from '@/api/user'
import { uploadFileApi } from '@/api/files'
import { useUser } from '@/utils/user'
const { updateUser } = useUser()

const loading = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = reactive({
  username: '',
  name: '',
  role: '',
  email: '',
  phone: '',
  avatar: ''
})

const roleLabel = computed(() => {
  return form.role === 'admin' ? '管理员' : form.role === 'student' ? '学生' : '未知角色'
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式错误', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误', trigger: 'blur' }]
}

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.avatar = res.data?.url
    }
  } catch {}
}

//  发送请求查询用户信息
const loadUserInfo = async () => {
  loading.value = true
  try {
    const res = await getUserInfo()
    if (res.code === 200) {
      Object.assign(form, res.data)
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return
  } finally {
    loading.value = false
  }
}

//  发送请求更新用户信息
const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const res = await updateUserInfo(form)
    if (res.code === 200) {
      updateUser(res.data)
      ElMessage.success('更新成功')
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadUserInfo()
})
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
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', //  /api -> http://127.0.0.1:8000/api
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000', //  /api -> http://127.0.0.1:8000/uploads
        changeOrigin: true
      }
    }
  }
})
```

</details>

---

<a id="13-user-management"></a>

## 13. 新增教程：密码修改、用户分页列表与管理员增删改

更新时间：2026-10-14。本节依据当前读取到的代码，接续第 12 节。

> 本节更新了个人资料接口地址和用户更新模型。第 12 节保留的是 2026-10-12 的历史版本；它的“角色不在个人更新模型中”等结论不能直接套用到当前代码。
>
> 本次只更新复习笔记，未修复业务源码。检查使用语法编译和内存数据库，没有修改真实用户记录。完整浏览器交互仍待验收。

### 13.1 新增功能在项目中的位置

本次从“本人查看、修改资料”扩展为：

- 已登录用户修改自己的密码。
- 管理员查询全体用户，支持关键词和分页。
- 管理员新增、编辑、删除用户。

CRUD 是四个英文操作的缩写：

| 字母 | 操作 | 本项目例子 |
| --- | --- | --- |
| C：Create | 创建 | 新增用户 |
| R：Read | 读取 | 用户列表、个人资料 |
| U：Update | 更新 | 编辑用户、修改密码 |
| D：Delete | 删除 | 删除用户记录 |

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

### 13.2 先明确：当前代码有一个权限边界问题

> 2026-10-15 修正说明：当前本人资料服务已在 model_dump 中明确 exclude={"role", "status"}，隔离验证确认这两个字段不再写入。下文保留 2026-10-14 的问题分析；模型拆分仍是整理方案，当前修正详见第 14.23 节。

当前 UserUpdateRequest 增加了：

```python
role: str | None = None
status: bool | None = None
```

管理员修改用户确实需要这些字段，但本人修改接口 PUT /api/user/me 也继续使用同一个模型，并调用同一个“遍历所有非 None 字段赋值”的服务逻辑。

因此，当前本人接口不仅能修改名称和联系方式，也会接受并保存 role、status。普通用户可能改变自己的角色，随后通过管理员校验。

这个问题已在隔离数据库中确认：原来的学生对象经本人更新服务修改角色后，能通过 get_current_admin。未在真实数据库中执行该操作。

**需要优先拆分本人修改模型与管理员修改模型，并在 API 参数类型上使用各自的模型。**只把前端角色输入框 disabled，不会限制其他客户端提交角色字段。

具体参考设计见第 13.18 节。这个问题不影响我们理解原代码如何执行，但必须明确当前权限检查还不完整。

### 13.3 当前文件与接口对照

| 文件 | 本次变化 |
| --- | --- |
| backend/app/schemas/user.py | 新增创建用户、修改密码模型；用户更新模型加入角色和状态 |
| backend/app/common/response.py | 新增 PageResponse |
| backend/app/dependencies/auth.py | 新增 get_current_admin |
| backend/app/services/user_service.py | 新增改密、分页、创建、按 ID 更新和删除函数 |
| backend/app/api/user.py | 注册本人、密码、列表和管理员 CRUD 接口 |
| frontend/src/api/user.js | 对应各接口的请求包装 |
| frontend/src/views/Password.vue | 本人修改密码页面 |
| frontend/src/views/User.vue | 列表、搜索、分页与新增编辑弹窗 |
| frontend/src/layouts/Layout.vue | command 下拉菜单、修改密码入口、管理员菜单显示 |
| frontend/src/router/index.js | 增加 /manager/password 子路由 |

当前接口：

| 方法 | 路径 | 当前权限依赖 | 动作 |
| --- | --- | --- | --- |
| GET | /api/user/me | get_current_user | 查询本人 |
| PUT | /api/user/me | get_current_user | 修改本人，当前字段范围有问题 |
| PUT | /api/user/password | get_current_user | 修改本人密码 |
| GET | /api/user/list | get_current_admin | 搜索和分页查询用户 |
| POST | /api/user | get_current_admin | 新增用户 |
| PUT | /api/user/{user_id} | get_current_admin | 修改指定用户 |
| DELETE | /api/user/{user_id} | get_current_admin | 删除指定用户 |

旧地址 /api/user/info 和 /api/user/update 已改成同一个资源地址 /api/user/me，通过 GET 与 PUT 区分查询和修改。前端 api/user.js 已同步；复现时其他调用也要检查是否仍使用旧地址。

### 13.4 下拉 command 与页面路由

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
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
```

router 的 password 子路由加载 Password.vue。这里是前端导航，随后页面提交时才访问后端接口。

用户管理菜单：

```html
<el-menu-item
  index="/manager/user"
  v-if="userInfo?.role === 'admin'"
>
  用户管理
</el-menu-item>
```

v-if 控制菜单是否显示。当前路由守卫仍只检查 token，未独立检查管理员角色；普通用户直接访问用户管理页面时，后端列表接口才会拒绝其操作。

前端使用缓存中的角色决定显示，后端使用数据库中的角色决定权限，二者职责不同。

### 13.5 get_current_admin：依赖还可以依赖其他依赖

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

### 13.6 密码修改：页面字段与接口字段

Password.vue 中：

```js
const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
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
  new_password: form.newPassword
})
```

confirmPassword 只用于页面比较两次输入，没有发送给后端。camelCase 与 snake_case 不会自动对应，当前转换由这个对象构造完成。

前端校验包括：

- 原密码必填。
- 新密码必填。
- 确认密码不能为空，且与新密码一致。

当前三个 el-input 都没有设置 type="password"，按默认文本方式显示输入内容。type="password" 控制显示遮盖，不等于传输加密。

### 13.7 密码修改：服务函数的顺序

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
ElMessage.success('修改密码成功')
logout()
await router.push('/login')
```

这是前端选择的交互：清理当前浏览器存储，让用户用新密码重新登录。

当前 JWT 没有密码版本或撤销机制，改密服务也没有让旧 token 失效。清理这个浏览器的 token 不等于其他浏览器或已经复制的 token 被后端撤销。

本次隔离验证确认：旧密码不再匹配，新密码匹配，数据库保存的是新哈希。

#### 当前缺少的密码规则

PasswordUpdateRequest 只声明 str，没有最小长度、最大字节数等规则。当前服务可以给空字符串计算哈希并保存；超过 bcrypt 限制的新密码会到达库中产生 ValueError，而不是请求校验阶段的 422。

前端必填校验不能代替后端校验。密码规则应在所有创建和修改入口保持一致。

### 13.8 分页查询：GET params 与后端查询参数

前端列表调用：

```js
const res = await getUserPageList({
  page: params.page,
  page_size: params.pageSize,
  keywords: params.keywords
})
```

API 包装：

```js
export function getUserPageList(params) {
  return request({
    url: '/api/user/list',
    method: 'get',
    params
  })
}
```

params 会进入 URL 查询部分，例如：

```text
/api/user/list?page=2&page_size=10&keywords=demo
```

与 data 的区别：

| Axios 配置 | 这里的用途 |
| --- | --- |
| params | 查询参数，出现在 URL 中 |
| data | 请求内容，例如创建用户的 JSON |

前端变量 pageSize 转成后端字段 page_size，是 load 函数显式映射的结果。

后端参数：

```python
page: int = 1
page_size: int = 10
keywords: str | None = None
```

这些参数不是路径占位变量，也不是 Pydantic 请求体，因此 FastAPI 将它们作为查询参数读取。int 会解析类型，但当前没有限制正数或最大页大小。

### 13.9 查询构造、模糊搜索与 OR

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

这里构造的是 SQLAlchemy 查询表达式，匹配值会作为参数处理，不是把完整 SQL 直接拼接出来。输入中的 % 和 _ 仍有 LIKE 通配含义，当前没有做“纯字面关键词”的转义。

#### 为什么 from operator import or_ 当前也能运行

你的导入是：

```python
from operator import or_
```

operator.or_(a, b) 等价于 a | b。SQLAlchemy 对这里的 SQL 条件表达式重载了 |，所以这两个条件仍然形成 SQL OR。本次隔离验证也确认查询能按账号或名称匹配。

通常从 sqlalchemy 导入 or_ 能更清楚地表达数据库条件，也支持不同的调用组织；不能简单把当前写法判定为必然报错。

也不能直接换成 Python 普通 or，因为普通 or 会做 Python 真值判断，而这里需要组合 SQL 条件。[SQLAlchemy 运算符说明](https://docs.sqlalchemy.org/en/20/core/operators.html)

### 13.10 count、offset、limit、all 与排序

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

| 操作 | 含义 |
| --- | --- |
| count() | 统计所有符合筛选条件的记录数 |
| order_by(User.id.desc()) | ID 从大到小排序，新记录通常在前面 |
| offset(...) | 跳过前面的记录 |
| limit(page_size) | 最多取这一页的数量 |
| all() | 执行查询，得到用户对象列表 |

页大小为 10 时：

| 页码 | offset | 读取范围 |
| --- | --- | --- |
| 1 | 0 | 前 10 条 |
| 2 | 10 | 跳过 10 条，再取 10 条 |
| 3 | 20 | 跳过 20 条，再取 10 条 |

total 在分页截取前统计。它是符合关键词的总数量，不是当前页的行数。

db.query、filter、order_by 等主要构造查询；count 与 all 会执行查询。这个函数通常会有一次计数查询和一次分页查询。

### 13.11 PageResponse 与列表推导式

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

### 13.12 el-table、作用域插槽与分页组件

前端接收：

```js
tableData.value = res.data?.list
total.value = res.data?.total
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

### 13.13 搜索为什么先重置到第一页

```js
const handleSearch = async () => {
  params.page = 1
  load()
}
```

原来可能在第 5 页，新的关键词只有 1 页结果。先回到第一页，可以避免用旧页码请求新筛选结果。

输入框的 @keyup.enter 是 Enter 键事件修饰符，@clear 处理清空操作，查询按钮也调用同一个函数。

当前虽然把 handleSearch 声明为 async，但没有 await load，函数自身不会等列表加载完才结束。列表 loading 仍由 load 管理；若调用方需要等待或接收失败，应明确返回或 await 这个 Promise。

### 13.14 一个弹窗同时完成新增与编辑

弹窗是否打开：

```js
const dialogVisible = ref(false)
```

模式判断使用 form.id：

| 状态 | form.id | 行为 |
| --- | --- | --- |
| 新增 | null | 显示密码，账号可编辑，调用 POST |
| 编辑 | 已有 ID | 隐藏密码，账号禁用，调用 PUT |

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

### 13.15 nextTick、动态校验与原生提交

打开新增或编辑窗口后：

```js
dialogVisible.value = true
await nextTick()
formRef.value?.clearValidate()
```

Vue 的页面更新不是每次赋值就同步完成。nextTick 等待这一轮 DOM 更新，随后更适合操作新显示的表单组件。clearValidate 清除旧的校验错误，不会清空字段值。[Vue nextTick](https://vuejs.org/api/general.html#nexttick)

问号表示表单实例暂时没有时，不继续调用方法，避免直接访问不存在的对象。

校验规则是计算属性：

```js
const rules = computed(() => ({
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
  ],
  password: form.id ? [] : [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 3, max: 10, message: '密码是3-10位', trigger: 'blur' }
  ]
}))
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
<el-button
  native-type="submit"
  form="user-form"
  :loading="formLoading"
>
  确定
</el-button>
```

native-type 设置原生按钮的 type。form 属性通过 ID 将按钮关联到对应的 HTML 表单，即使按钮不在 form 标签内部。

@submit.prevent 监听表单提交，并阻止默认的浏览器提交和页面刷新，转而调用异步 handleSave。用户按 Enter 和点击确定可以走同一条提交逻辑。

el-form-item 的 for 与输入框 id 用于标签关联；prop 与 rules/model 的字段关系仍是另一套用途。

### 13.16 handleSave 的解构、剩余属性与模式分支

核心：

```js
const { id, username, password, ...userData } = form

const res = id
  ? await updateUserApi(id, userData)
  : await createUserApi({ username, password, ...userData })
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

### 13.17 后端创建、按 ID 更新与删除

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
url: `/api/user/${userId}`
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
ElMessageBox.confirm(
  `确认删除用户【${row.username}】？`,
  '确认删除',
  { type: 'warning' }
).then(async () => {
  const res = await deleteUserApi(row.id)

  if (res.code === 200) {
    ElMessage.success('删除用户成功')
    load()
  }
})
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

### 13.18 本人修改模型与管理员模型的参考拆分

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

| 接口 | 建议请求模型 |
| --- | --- |
| PUT /me | ProfileUpdateRequest |
| PUT /{user_id} | AdminUserUpdateRequest |

Literal 限定角色只能是给出的值，避免任意角色字符串。

需要同时修改 API 的请求参数类型和对应服务的类型声明。只新增模型但接口继续使用旧模型，字段范围不会自动改变。

格式、长度和清空语义仍需独立设计。此示例只展示权限字段拆分，不是全部校验的最终实现。

### 13.19 静态路由与动态路由的注册顺序

当前 PUT 路由中，/me 和 /password 定义在 /{user_id} 前。

FastAPI 按注册顺序匹配路由。/{user_id} 可以先在路径层面接收 me 这样的字符串，再发生 int 校验错误；不能依赖 user_id: int 就认为静态路径永远不会被匹配。

把固定路径放在宽泛的动态路径前，能避免被遮住。当前代码的顺序符合这一安排。[FastAPI 路由顺序](https://fastapi.tiangolo.com/tutorial/path-params/#order-matters)

POST 的装饰器使用空路径 `@router.post("")`。

它表示使用当前 router 的根路径。与 /api 和 /user 前缀组合后，创建地址就是 /api/user，不是“没有注册路径”。

### 13.20 布尔状态与数字单选框的类型不一致

后端 UserResponse 返回：

```json
{"status": true}
```

编辑时复制：

```js
status: row.status
```

但单选框使用：

```html
<el-radio :value="1">正常</el-radio>
<el-radio :value="0">禁用</el-radio>
```

这是数字 1、0，与布尔 true、false 不是相同的值：

```js
true === 1   // false
false === 0  // false
```

本次检查到的 Element Plus Radio 使用严格比较判断选中状态，所以编辑回填可能无法显示预期的单选项。

可以统一为布尔值：

```html
<el-radio :value="true">正常</el-radio>
<el-radio :value="false">禁用</el-radio>
```

同时将 form 初始和重置的 status 改为 true。或者保留数字控件，在回填时显式转换；不要在不同环节混用后期待组件自动匹配。

Pydantic 会处理请求中的 bool 输入，不代表 Vue 控件已经在显示层做了同样转换。[Element Plus Radio](https://element-plus.org/en-US/component/radio.html)

### 13.21 本次检查记录与问题清单

#### 已完成的隔离检查

使用实际 schema、服务函数和管理员依赖的代码，在内存 SQLite 中完成 20 项检查，包括：

- 创建用户与默认密码哈希，响应不含密码。
- 管理员依赖放行管理员，拒绝学生。
- 重复账号被拒绝。
- 原密码错误、新旧相同被拒绝。
- 改密后新密码匹配、旧密码不匹配。
- 模糊搜索匹配账号和名称，空结果处理。
- 分页 total、倒序和 offset/limit。
- operator.or_ 对当前表达式构造 SQL OR。
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

#### 当前需要完善的点

| 优先项 | 当前事实 | 需要处理 |
| --- | --- | --- |
| 权限边界 | /me 与管理员更新共用含 role/status 的模型 | 拆分模型并绑定到不同接口 |
| 密码校验 | 新密码只声明 str，后端允许空值 | 统一必填、长度、UTF-8 字节限制 |
| 密码显示 | Password.vue 输入框默认文本 | 使用密码输入框 |
| 状态类型 | 接口返回 bool，单选框使用数字 | 统一或显式转换 |
| 新建用户契约 | name 可不传，数据库不允许 NULL | 要求名称或提供明确默认 |
| 分页范围 | page/page_size 只校验 int | 限制页码、页大小与合理上限 |
| 删除 Promise | confirm().then 没有 catch | 分别处理取消与请求失败 |
| 角色输入 | 请求模型接受任意 role 字符串 | 使用限定值或规则 |
| 事务错误 | 修改服务未显式处理回滚 | 明确失败后的会话处理 |
| 当前用户状态 | 管理员编辑本人不更新共享 userInfo | 确定自我修改限制和缓存同步 |
| 改密失效 | 清理本地 token，不撤销其他有效 token | 根据需求设计服务端失效机制 |
| 管理员初始化 | 注册默认学生，管理 API 又要求管理员 | 从零复现需准备受控的初始管理员 |

这些是分析结果和待办，不代表本次已修改源码。

### 13.22 浏览器实际验收清单

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

### 13.23 从零复现时的新增顺序

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
12. 完成第 13.22 节的功能检查。

第一位管理员不能依靠允许学生自行修改角色来产生。最终复现章节需要给出明确的学习数据库初始化方式；本次没有向真实数据库创建管理员。

### 13.24 复习问题

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

### 13.25 本节官方参考

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

### 13.26 当前代码快照

以下保存本次核心文件的实际内容，供复习和比较。保留原写法及已经指出的问题；第 12 节快照不被覆盖，便于观察项目怎样逐步演变。

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
import request from '@/utils/request'

// 获取个人信息
export function getUserInfo() {
  return request({
    url: '/api/user/me',
    method: 'get'
  })
}

// 更新个人信息
export function updateUserInfo(data) {
  return request({
    url: '/api/user/me',
    method: 'put',
    data
  })
}

// 更新用户密码
export function updatePassword(data) {
  return request({
    url: '/api/user/password',
    method: 'put',
    data
  })
}

// 分页模糊查询用户列表
export function getUserPageList(params) {
  return request({
    url: '/api/user/list',
    method: 'get',
    params
  })
}

// 新增用户
export function createUserApi(data) {
  return request({
    url: '/api/user',
    method: 'post',
    data
  })
}

// 修改用户
export function updateUserApi(userId, data) {
  return request({
    url: `/api/user/${userId}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deleteUserApi(userId) {
  return request({
    url: `/api/user/${userId}`,
    method: 'delete'
  })
}
```

</details>

<details>
<summary><code>frontend/src/views/Password.vue</code></summary>

```vue
<template>
  <div style="width: 420px; max-width: 100%; margin-left: 60px; margin-top: 40px">
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
import { ref, reactive } from 'vue'
import { updatePassword } from '@/api/user'
import router from '@/router'
import { ElMessage } from 'element-plus'
import { logout } from '@/utils/auth'

const submitting = ref(false)
const formRef = ref()
const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请确认密码'))
  } else {
    if (value !== form.newPassword) {
      callback(new Error('两次输入密码不一致!'))
    } else {
      callback()
    }
  }
}

const rules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }],
  confirmPassword: [{ validator: validatePass, trigger: 'blur' }]
}

const handleSubmit = async () => {
  if (submitting.value) return
  submitting.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const res = await updatePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword
    })
    if (res.code === 200) {
      ElMessage.success('修改密码成功')
      logout()
      await router.push('/login')
    }
  } catch {
    // 请求拦截器已显示错误提示。
    return
  } finally {
    submitting.value = false
  }
}
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
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增</el-button>
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
            {{ row.role === 'admin' ? '管理员' : '学生' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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

          <el-form-item v-if="!form.id" label="密码" prop="password" for="user-form-password">
            <el-input
              id="user-form-password"
              type="password"
              show-password
              v-model="form.password"
              placeholder="请输入密码"
            />
          </el-form-item>

          <el-form-item label="名称" prop="name" for="user-form-name">
            <el-input id="user-form-name" v-model="form.name" placeholder="请输入名称" />
          </el-form-item>

          <el-form-item label="角色" prop="role" for="user-form-role">
            <el-select id="user-form-role" v-model="form.role">
              <el-option label="学生" value="student"></el-option>
              <el-option label="管理员" value="admin"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="邮箱" prop="email" for="user-form-email">
            <el-input id="user-form-email" v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone" for="user-form-phone">
            <el-input id="user-form-phone" v-model="form.phone" placeholder="请输入手机号" />
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { getUserPageList, createUserApi, updateUserApi, deleteUserApi } from '@/api/user'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})

// 加载分页数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  username: '',
  password: '',
  name: '',
  role: '',
  email: '',
  phone: '',
  avatar: '',
  status: 1
})

const load = async () => {
  loading.value = true
  try {
    const res = await getUserPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = computed(() => ({
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: form.id ? [] : [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 3, max: 10, message: '密码是3-10位', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式错误', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误', trigger: 'blur' }]
}))

const resetForm = () => {
  Object.assign(form, {
    id: null,
    username: '',
    password: '',
    name: '',
    role: 'student',
    email: '',
    phone: '',
    avatar: '',
    status: 1
  })
}

const handleSearch = async () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑用户信息
const handleEdit = async (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.role,
    email: row.email,
    phone: row.phone,
    avatar: row.avatar,
    status: row.status
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 删除用户信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除用户【${row.username}】？`, '确认删除', { type: 'warning' }).then(
    async () => {
      const res = await deleteUserApi(row.id)
      if (res.code === 200) {
        ElMessage.success('删除用户成功')
        load()
      }
    }
  )
}

// 保存用户信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, username, password, ...userData } = form
    const res = id
      ? await updateUserApi(id, userData)
      : await createUserApi({ username, password, ...userData })
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

onMounted(() => {
  load()
})
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
        <div style="display: flex; align-items: center; font-size: 24px; font-weight: bold">
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; margin-right: 20px; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || '用户' }}
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
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
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
import { Menu as IconMenu, House, Setting, User } from '@element-plus/icons-vue'
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
const { userInfo } = useUser()

const handleLogout = () => {
  logout()
  router.push('/login')
}

const goPerson = () => {
  router.push('/manager/profile')
}

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/Home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/Lab.vue')
        },
        {
          path: 'equ',
          name: 'Equ',
          component: () => import('@/views/Equ.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/User.vue')
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue')
        },
        {
          path: 'password',
          name: 'Password',
          component: () => import('@/views/Password.vue')
        }
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue')
    }
  ]
})

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken()
  if (to.path === '/login' || to.path === '/register') {
    return true
  } else {
    return token ? true : '/login'
  }
})

export default router
```

</details>

---

<a id="14-lab-equipment"></a>

## 14. 新增教程：实验室管理与设备列表管理

更新时间：2026-10-15。本节根据当前原项目新增的实验室和设备模块讲解。

> **2026-10-19 更新提示**：本节保留 10 月 15 日代码。当前列表查询已改用 get_current_user，新增实验室详情和学生端浏览页面，设备分页属性也已修正；最新讲解和快照见第 15 节。下文“全部接口需要管理员”等判断仅适用于本节日期。

> 本节延续用户管理中的分页、弹窗、表单校验和 CRUD 思路，新增重点是实验室与设备的关联、外键、ORM relationship、组合筛选和关联名称返回。
>
> 本次只更新笔记，没有改动业务源码。验证采用语法检查、内存数据库和单独的前端函数/规则检查，没有修改真实数据库；完整浏览器流程仍需要实际验收。

### 14.1 本次实现了什么

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

### 14.2 文件地图

| 层 | 实验室模块 | 设备模块 |
| --- | --- | --- |
| 数据库模型 | app/models/lab.py | app/models/equipment.py |
| 输入与输出模型 | app/schemas/lab.py | app/schemas/equipment.py |
| 业务逻辑 | app/services/lab_service.py | app/services/equipment_service.py |
| 后端接口 | app/api/lab.py | app/api/equipment.py |
| 前端请求 | src/api/lab.js | src/api/equipment.js |
| 页面 | src/views/Lab.vue | src/views/Equipment.vue |

还需要理解这些连接位置：

- app/api/__init__.py：把两个后端 router 加入总路由。
- app/main.py：导入模块、创建缺失表、注册应用路由。
- src/router/index.js：把页面组件映射到前端路径。
- src/layouts/Layout.vue：显示管理员菜单。
- 原有文件上传工具：封面或图片上传后，把 URL 存入 img。

这里的 backend/app 和 frontend 前缀在表格中省略，完整快照位于第 14.26 节。

### 14.3 数据设计：一个实验室可以有多条设备记录

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

| lab.id | 实验室 |
| --- | --- |
| 1 | 计算机实验室 |
| 2 | 电子实验室 |

| equipments.id | lab_id | 设备名称 | quantity |
| --- | --- | --- | --- |
| 10 | 1 | 工作站 | 20 |
| 11 | 1 | 投影仪 | 1 |
| 12 | 2 | 示波器 | 8 |

设备通过实验室 ID 建立关联。实验室更名后，不需要把所有设备中的名字都重写一次。

一条设备记录可以代表某类设备及其数量；当前没有给每一件物理设备单独分配资产编号。

### 14.4 Lab 数据库模型

当前表名是单数 lab。继承 Base 后，也拥有 id、create_time、update_time。

主要字段：

| 字段 | 类型与含义 |
| --- | --- |
| name | String(50)，名称 |
| description | String(500)，简介，可为 NULL |
| img | String(100)，封面 URL，可为 NULL |
| location | String(100)，位置，可为 NULL |
| capacity | Integer，容量，ORM 默认 0 |
| open_time / close_time | String(20)，开始和结束时间 |
| status | Boolean，默认 True |

Mapped 描述映射属性，mapped_column 声明列。数据库字段有长度不等于 Pydantic 请求模型已经设置同样的长度限制。

当前 description、img 等使用 Mapped[str]，同时明确 nullable=True，数据库仍允许 NULL；注解若写成 str | None，会与可空含义更一致。

status 的 True/False 在页面中显示为开启/关闭，编辑单选框也使用 :value="true" 与 :value="false"，类型是对应的。

### 14.5 Equipment 的 ForeignKey 与 relationship

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

| 定义 | 作用 |
| --- | --- |
| lab_id 列 | 存储所属实验室 ID |
| ForeignKey("lab.id") | 声明数据库外键，指向表 lab 的 id |
| lab 属性 | 通过 ORM 访问对应的 Lab 对象 |

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

### 14.6 两种 status 与数字字段不能混淆

| 字段 | 当前类型 | 页面含义 |
| --- | --- | --- |
| Lab.status | bool | 开启/关闭或正常/禁用 |
| Equipment.status | int | 1 正常，0 维修 |
| Lab.capacity | int | 容量 |
| Equipment.quantity | int | 数量 |

实验室状态与设备状态表达不同业务事实。实验室关闭并不自动把所有设备改成维修。

当前新增设备服务只确认实验室存在，没有要求它必须开启。所以管理员目前可以维护关闭实验室中的设备。

数量和状态的 0 也不同：quantity=0 表示数量为零，status=0 表示维修。当前后端模型没有范围限制，quantity 为零甚至负数都需要额外规则才能拒绝。

### 14.7 Create、Update、Response 三种模型

两个模块各有三类 Pydantic 模型：

| 模型 | 用途 |
| --- | --- |
| CreateRequest | 新建一条记录需要的字段与默认值 |
| UpdateRequest | 更新允许修改的字段，通常允许省略 |
| Response | 返回给前端的字段结构 |

实验室创建要求 name，默认 capacity=0、status=True。设备创建要求 lab_id 和 name，默认 quantity=1、status=1。

更新模型中的字段使用默认 None，配合 exclude_none=True，表示当前写法跳过值为 None 的字段。

两个响应模型都用 from_attributes=True 从 ORM 属性读取。EquipmentResponse 还增加了 lab_name，用于页面展示实验室名称。

img 保存图片 URL，不保存图片二进制。LabResponse 的 capacity 虽然返回了，当前实验室表格没有单独显示容量列；表单和数据库中仍可以有这个值。

### 14.8 新语法：字典的 ** 解包

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

这里的 ** 把字典拆成关键字参数，不是进行乘法或幂运算。键名需要对应构造对象可以接收的属性。

设备创建使用 Equipment(**data.model_dump())，没有排除 None。其可空说明、图片和规格字段可以接收 None。

### 14.9 当前后端接口与权限

| 模块 | 方法 | 地址 | 操作 |
| --- | --- | --- | --- |
| 实验室 | GET | /api/lab/list | 搜索分页 |
| 实验室 | POST | /api/lab | 创建 |
| 实验室 | PUT | /api/lab/{lab_id} | 修改 |
| 实验室 | DELETE | /api/lab/{lab_id} | 删除 |
| 设备 | GET | /api/equipment/list | 搜索分页，可按 lab_id 筛选 |
| 设备 | POST | /api/equipment | 创建 |
| 设备 | PUT | /api/equipment/{equipment_id} | 修改 |
| 设备 | DELETE | /api/equipment/{equipment_id} | 删除 |

8 个接口都声明 Depends(get_current_admin)。本次检查确认它们都接入该依赖，不只是前端隐藏按钮。

依赖会先完成用户认证和管理员校验。服务函数通常假设调用者已经经过 API 层权限检查，服务函数本身没有重复检查管理员。

### 14.10 为什么新增 Equipment 表不要求 main 显式导入它

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

### 14.11 实验室列表与增删改的调用过程

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

### 14.12 每次打开表单的默认值

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

### 14.13 容量输入与整数校验

当前模板：

```html
<el-input :min="1" v-model="form.capacity" />
```

校验规则要求 integer。普通 el-input 作为文本输入，编辑后通常产生字符串，例如 "30"。:min 不会自动把字符串转换成数字，也不等于整数输入控件。

本次按本地 Element Plus 的规则处理方式验证：

| 值 | 整数规则结果 |
| --- | --- |
| 数字 30 | 通过 |
| 字符串 "30" | 不通过 |

因此，未修改的数字回填可能正常，但用户编辑容量后可能无法提交。

参考调整是使用数值组件：

```html
<el-input-number v-model="form.capacity" :min="1" />
```

这只是笔记中的建议，没有写入源码。后端也应按业务决定容量是否允许 0，并在输入模型中保持一致的范围要求。

### 14.14 时间选择器：显示格式与绑定格式

当前组件同时设置：

```html
<el-time-picker
  v-model="form.open_time"
  format="HH:mm"
  value-format="HH:mm"
/>
```

- format 控制输入框显示什么格式。
- value-format 控制绑定到 form 的值采用什么格式。

因此当前可以把 "08:30" 这样的字符串交给后端，而不是必须传一个 JavaScript Date 对象。[Element Plus TimePicker](https://element-plus.org/en-US/component/time-picker)

后端当前用 String(20) 和 str 保存时间，没有验证真实时间格式、开始结束顺序或跨夜规则。本次隔离检查确认 "25:99" 等字符串仍能通过当前模型并保存。

如果控件清空后提交 null，更新服务会用 exclude_none 跳过它，旧时间可能保留。需明确清空与跨夜的业务含义，再统一前后端规则。

### 14.15 设备页为什么先加载实验室选项

设备页面需要一份实验室列表：

```js
const labOptions = ref([])

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })

  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}
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

### 14.16 按实验室和关键词组合筛选

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

### 14.17 创建设备：先查实验室，再查同名记录

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

| 情况 | 结果 |
| --- | --- |
| A 实验室已有“工作站”，再在 A 新建同名 | 拒绝 |
| A 实验室已有“工作站”，在 B 新建同名 | 允许 |
| A 的设备名称相同，但规格不同 | 仍按同名拒绝 |

规格不是当前查重条件的一部分，设备也不是全局名称唯一。

这项规则目前通过服务查询实现，模型没有 (lab_id, name) 组合唯一约束。若要在并发创建时仍保证唯一，需要数据库约束和相应的异常处理。

### 14.18 更新设备：先确定修改后的实验室与名称

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

### 14.19 lab_name 为什么要手动补充

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

### 14.20 删除实验室与外键约束

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

### 14.21 设备页当前重置与分页绑定问题

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
    name: '',
    description: '',
    img: '',
    spec: '',
    quantity: 1,
    status: 1
  })
}
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

### 14.22 图片上传与复用结构时的核对项

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

两页上传函数仍有空 catch，成功后没有明确 return 响应；上传组件的 Promise 状态问题与第 12.16 节相同。上传未完成时提前保存，也需要检查是否会提交旧图片地址。

当前其他核对项：

| 当前事实 | 需要处理或确认 |
| --- | --- |
| 实验室搜索提示仍写账号 | 与实际只按名称查询的行为一致 |
| 设备搜索提示包含型号 | 决定加入 spec 搜索还是更正文案 |
| 编辑设备未等待 nextTick 清理校验 | 检查上次错误是否残留 |
| 实验室下拉只取前 100 条 | 规模增大后需要完整选项加载策略 |
| 两页确认删除没有 catch | 处理取消与网络失败的 Promise |
| 后端未限制容量、数量、状态取值、时间格式和字符串长度 | 根据业务统一前后端校验 |
| 页码与页大小未设范围 | 避免无效分页参数 |
| 实验室改名不查重 | 补齐更新路径及数据库唯一性策略 |
| 所有页面 form ID 仍叫 user-form | 核对当前匹配关系和未来同时挂载时的唯一性 |

lab_service 中还保留 get_lab_info、update_Lab_info 等未被当前 API 调用的函数，以及密码工具等未使用导入。这些可整理，但它们不会因为定义在文件里就自动执行。

特别是 update_Lab_info 中排除 status，不代表当前实验室更新无法改状态。API 调用的是 update_lab，后者会保存 status。应沿实际调用链分析。

### 14.23 上一章本人角色修改问题已经修正

当前 user_service.update_user_info 改为：

```python
user_dict = data.model_dump(
    exclude_none=True,
    exclude={"role", "status"},
)
```

exclude 明确把两个字段从赋值字典中移除，即使请求提供它们也不会在这个服务中保存。

本次隔离验证同时提供了名称、角色和状态，结果名称更新，角色与状态保持原值，说明该修改路径已修正。

第 13 节保留的是发现问题时的旧代码。当前可以继续使用字段排除控制写入范围；再拆分请求模型是让接口声明更清楚的整理方向，不是说当前过滤修正没有作用。

该结论只覆盖已检查的本人资料修改路径，不等于已经审计或验证整个项目的所有权限功能。

### 14.24 本次验证记录与实际验收

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

### 14.25 继续复现的顺序与参考资料

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
13. 完成第 14.24 节的实际功能检查。

旧设备路径 /manager/equ 已改成 /manager/equipment，组件也变成 Equipment.vue。当前没有给旧路径配置别名或重定向，不会自动映射过去。

从包中导入 lab_service、equipment_service，会加载相应子模块；不要求把所有服务代码写进 services/__init__.py。

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

### 14.26 本次相关代码快照

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
<summary><code>backend/app/api/__init__.py</code></summary>

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
<summary><code>backend/app/main.py</code></summary>

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
<summary><code>frontend/src/api/lab.js</code></summary>

```js
import request from '@/utils/request'

// 分页模糊查询实验室列表
export function getLabPageList(params) {
  return request({
    url: '/api/lab/list',
    method: 'get',
    params
  })
}

// 新增实验室
export function createLabApi(data) {
  return request({
    url: '/api/lab',
    method: 'post',
    data
  })
}

// 修改实验室
export function updateLabApi(labId, data) {
  return request({
    url: `/api/lab/${labId}`,
    method: 'put',
    data
  })
}

// 删除实验室
export function deleteLabApi(labId) {
  return request({
    url: `/api/lab/${labId}`,
    method: 'delete'
  })
}
```

</details>

<details>
<summary><code>frontend/src/api/equipment.js</code></summary>

```js
import request from '@/utils/request'

// 分页模糊查询列表
export function getEquipmentPageList(params) {
  return request({
    url: '/api/equipment/list',
    method: 'get',
    params
  })
}

// 新增
export function createEquipmentApi(data) {
  return request({
    url: '/api/equipment',
    method: 'post',
    data
  })
}

// 修改
export function updateEquipmentApi(equipmentId, data) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: 'put',
    data
  })
}

// 删除
export function deleteEquipmentApi(equipmentId) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: 'delete'
  })
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
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增</el-button>
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
          <template #default="{ row }">{{ row.open_time }} - {{ row.close_time }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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
            <el-input type="textarea" v-model="form.description" placeholder="请输入简介" />
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
            <el-input type="textarea" v-model="form.location" placeholder="请输入位置" />
          </el-form-item>
          <el-form-item label="容量" prop="capacity">
            <el-input :min="1" v-model="form.capacity" placeholder="请输入容量" />
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { getLabPageList, createLabApi, updateLabApi, deleteLabApi } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})

// 加载分页数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  name: '',
  description: '',
  img: '',
  location: '',
  capacity: 1,
  open_time: '',
  close_time: '',
  status: true
})

const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = computed(() => ({
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'blur' },
    { type: 'integer', min: 1, message: '容量必须为正整数', trigger: 'change' }
  ]
}))

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = async () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = async (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    img: row.img,
    location: row.location,
    capacity: row.capacity,
    open_time: row.open_time,
    close_time: row.close_time,
    status: row.status
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' }).then(
    async () => {
      const res = await deleteLabApi(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    }
  )
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...labData } = form
    const res = id ? await updateLabApi(id, labData) : await createLabApi(labData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

onMounted(() => {
  load()
})

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}
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

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="success" :icon="Plus" @click="handleCreate">新增</el-button>
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
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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
            <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%">
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi
} from '@/api/equipment'
import { getLabPageList } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

const loading = ref(false)
const tableData = ref([])
const labOptions = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = {
  lab_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = async () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status
  })
  dialogVisible.value = true
}

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' }).then(
    async () => {
      const res = await deleteEquipmentApi(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    }
  )
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...equipmentData } = form
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

onMounted(() => {
  loadLabs()
  load()
})
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
        <div style="display: flex; align-items: center; font-size: 24px; font-weight: bold">
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; margin-right: 20px; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || '用户' }}
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
            <el-menu-item index="/manager/lab" v-if="userInfo?.role === 'admin'">
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/equipment" v-if="userInfo?.role === 'admin'">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
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
import { Menu as IconMenu, House, Setting, User } from '@element-plus/icons-vue'
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
const { userInfo } = useUser()

const handleLogout = () => {
  logout()
  router.push('/login')
}

const goPerson = () => {
  router.push('/manager/profile')
}

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/Home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/Lab.vue')
        },
        {
          path: 'equipment',
          name: 'Equipment',
          component: () => import('@/views/Equipment.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/User.vue')
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue')
        },
        {
          path: 'password',
          name: 'Password',
          component: () => import('@/views/Password.vue')
        }
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue')
    }
  ]
})

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken()
  if (to.path === '/login' || to.path === '/register') {
    return true
  } else {
    return token ? true : '/login'
  }
})

export default router
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

---

<a id="15-lab-browse"></a>

## 15. 新增教程：学生端实验室列表、详情与关联设备浏览

更新时间：2026-10-19。本节对照第 14 节的代码快照，讲解你最近完成的前后端改动。

> **2026-10-20 更新提示**：本节保留当日历史。预约入口现已接通提交功能，设备重置、容量输入和关联删除已有修补，设备管理删除按钮也已恢复。最新说明见第 16、17 节；预约查询、审核与取消仍未实现。

> 本次更新教学文档，业务源码保持本次读取时的内容。第 14 节解释资源怎样创建和维护，本节解释学生怎样找到实验室、查看介绍，并查询这个实验室的设备。
>
> 下面明确区分三类内容：当前源码、便于理解的示例、尚未写入源码的改进方案。当前已经写出资源浏览流程；预约按钮尚未接通预约业务。功能的真实浏览器验收和全项目从零复现仍需继续完成。

### 15.1 先分清四个页面的职责

| 文件 | 面向的操作 | 页面主要内容 |
| --- | --- | --- |
| frontend/src/views/Lab.vue | 管理实验室资料 | 搜索、表格、新增和编辑弹窗、删除 |
| frontend/src/views/Equipment.vue | 管理设备资料 | 搜索、按实验室筛选、新增和编辑；本次模板移除了删除按钮 |
| frontend/src/views/LabList.vue | 浏览实验室 | 封面卡片、位置、容量、时间、查看设备按钮 |
| frontend/src/views/LabEquipment.vue | 浏览某个实验室的设备 | 实验室简介、设备图片、规格、数量、状态 |

菜单中，管理员看到管理入口，student 角色看到实验室列表入口。两个浏览页面不提供资源编辑表单。

页面不同，仍可以复用同一查询接口。例如，Lab.vue 用实验室列表接口填充表格，LabList.vue 用这个接口填充卡片。后端返回的是数据，前端决定把数据画成什么样。

注意：“菜单按角色显示”与“接口按角色授权”是两个独立机制。本次后端查询接口允许符合当前用户依赖检查的登录用户调用，并没有额外限定必须是 student。

### 15.2 本次新增和修改的文件地图

| 层 | 主要变化 |
| --- | --- |
| backend/app/services/lab_service.py | 列表新增 status 参数；新增 get_lab 按 ID 查询详情 |
| backend/app/api/lab.py | 列表改为登录用户可查；新增 GET /{lab_id} |
| backend/app/api/equipment.py | 设备列表改为登录用户可查 |
| frontend/src/api/lab.js | 新增 getLab(lab_id) 请求函数 |
| frontend/src/views/LabList.vue | 新增卡片式实验室浏览页面 |
| frontend/src/views/LabEquipment.vue | 新增实验室介绍和关联设备浏览页面 |
| frontend/src/router/index.js | 增加 lablist、labequipment 两个子路由 |
| frontend/src/layouts/Layout.vue | 增加学生菜单入口，并尝试根据当前路由设置高亮 |
| frontend/src/views/Equipment.vue | 统一 page_size 属性；移除模板中的删除按钮 |

本次对照发现，实验室与设备的 models、schemas，以及 equipment_service.py 的核心业务逻辑与第 14 节快照一致。关联查询不是重新实现了一套，而是复用了之前的 lab_id 筛选和 lab_name 组装。

第 15.24 节保存本次相关文件的完整快照；早期快照继续保留，便于观察功能怎样逐步长出来。

### 15.3 把整个流程连起来

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

### 15.4 为什么必须同时调整后端查询权限

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

| HTTP 请求 | 当前依赖 | 当前要求 |
| --- | --- | --- |
| GET /api/lab/list | get_current_user | 有效登录且账号可用 |
| GET /api/lab/{lab_id} | get_current_user | 有效登录且账号可用 |
| GET /api/equipment/list | get_current_user | 有效登录且账号可用 |
| POST、PUT、DELETE /api/lab… | get_current_admin | 上述条件，并且为管理员 |
| POST、PUT、DELETE /api/equipment… | get_current_admin | 上述条件，并且为管理员 |

即使函数体没有读取 current_user.name，依赖仍会执行。这个参数已经承担了进入接口前的权限检查。

如果只新增学生菜单，却保留原来的管理员查询依赖，学生会进入页面，然后查询被后端拒绝。这就是本次必须同时修改前后端的原因。

当前前端路由守卫仍主要检查本地是否有 token，没有逐个路由检查角色；隐藏菜单也不会阻止用户手动输入路径。资源新增、修改和删除的最终权限仍由后端依赖决定。

### 15.5 新增详情接口：从路径取得一个 ID

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

### 15.6 新增 status 筛选：参数接通了，但 False 分支还有问题

接口新增：

```python
status: bool | None = None
```

这里有三个有意义的状态：

| 传入情况 | 进入 Python 函数后的值 | 预期用途 |
| --- | --- | --- |
| 不传 status | None | 不按状态筛选 |
| status=true | True | 只查启用实验室 |
| status=false | False | 只查停用实验室 |

URL 中的 true、false 是文本，FastAPI 根据 bool 类型声明把它们解析为布尔值。服务函数收到的已经是 True 或 False。

当前 lab_service.py 实际写法是：

```python
if status:
    query = query.filter(Lab.status == status)
```

Python 的 if 判断的是“条件真假”。True 会进入分支，False 和 None 都不会进入。因此当前实际结果是：

| status | 当前是否追加筛选条件 | 当前结果 |
| --- | --- | --- |
| None | 否 | 所有状态 |
| True | 是 | 启用状态 |
| False | 否 | 所有状态，未实现只查停用 |

本次内存数据库检查已经复现这个行为：创建一间启用、一间停用实验室后，status=False 返回两间。

应把条件判断改成“是否提供了状态”。下面是修正片段，**尚未写入业务源码**：

```python
if status is not None:
    query = query.filter(Lab.status == status)
```

不要把 if status 理解为“只要传了参数”。布尔条件里，False 本身也是一个正常的筛选值。

还有第二层区别：LabList.vue 当前 params 没有 status: true，调用时不会主动要求只查启用实验室。所以当前学生卡片列表可能包含停用实验室；详情接口也没有按启用状态限制访问。

如果产品要求学生只能看启用实验室，需要先明确规则，再在学生查询和详情的后端逻辑落实规则，前端也可以配合传参。仅在卡片查询里增加参数，仍不能限制用户直接按 ID 请求停用实验室详情。

### 15.7 LabList.vue：从接口结果到卡片数组

页面中与列表直接有关的状态是：

```js
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})
```

ref 用来保存一个响应式值：脚本中用 .value 读写；模板中通常自动解包。reactive 包装对象后，可以直接修改 params.page 等属性。

这些名字的作用：

| 名字 | 保存什么 | 谁使用它 |
| --- | --- | --- |
| loading | 是否正在查询 | v-loading 显示加载状态 |
| tableData | 当前页实验室数组 | v-for 生成卡片 |
| total | 筛选后的记录总数 | 分页组件 |
| params | 页码、页大小、名称关键词 | 请求参数 |

虽然变量还叫 tableData，这个页面并没有使用表格；名字不会改变数据的用途。

load 的核心是：

```js
loading.value = true
try {
  const res = await getLabPageList(params)
  if (res.code === 200) {
    tableData.value = res.data?.list
    total.value = res.data?.total
  }
} finally {
  loading.value = false
}
```

getLabPageList 把 params 交给 request 的 params 配置，形成 GET 查询字符串。await 等待请求对应的 Promise 完成。统一响应由 request.js 解包后，res 是业务对象，因此读取 res.data.list。

finally 表示无论正常完成还是抛出错误，都会做最后的清理，所以加载状态会恢复。它不负责“吃掉”错误；LabList.vue 的 load 没有 catch，网络错误对应的 Promise 仍可能向调用方拒绝。拦截器显示错误消息，也不会自动把所有拒绝变成成功。

当前 lab_id: null 对实验室列表没有筛选作用。后端列表函数没有声明 lab_id 参数。参数名称写进对象，只代表前端准备发送它，不代表后端已经实现对应功能。

名称查询时：

```js
const handleSearch = () => {
  params.page = 1
  load()
}
```

先回第一页，是为了避免“原来在第 5 页，新关键词只有 1 页数据，结果画面为空”。回车、查询按钮和清空输入都复用这一个函数。

### 15.8 卡片怎么由一个数组生成

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
  开放时间：
  {{ item.open_time && item.close_time ? `${item.open_time} - ${item.close_time}` : '-' }}
</div>
```

- {{ … }} 把表达式结果显示为文本。
- || 表示左边是假值时采用右边；位置缺失或为空字符串时显示短横线。
- && 要求开始时间和结束时间都有可用值。
- 条件 ? 结果一 : 结果二 是三元表达式。
- 反引号和 ${…} 构成模板字符串，用来拼接时间文本。

封面有值时显示 img，没有值时显示灰色占位块，使用的是 v-if / v-else。object-fit: cover 让图片填满固定区域，图片边缘可能被裁掉。

本页只是展示这些时间字符串，没有计算当前时刻能否预约，也没有验证开始时间早于结束时间。

### 15.9 点击“查看设备”后，先发生前端路由跳转

LabList.vue 中当前函数是：

```js
const handelViewEquipment = (lab) => {
  router.push({
    path: '/manager/labequipment',
    query: { lab_id: lab.id }
  })
}
```

点击卡片时，模板调用 handelViewEquipment(item)，所以函数参数 lab 就是这张卡片的数据对象。

假设 lab.id 为 8，导航得到：

```text
/manager/labequipment?lab_id=8
```

其中：

| 部分 | 意义 |
| --- | --- |
| /manager/labequipment | 要显示哪个前端页面 |
| ? | 路径与查询字符串的分隔符 |
| lab_id=8 | 传给目标页面的查询条件 |

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

### 15.10 目标页怎样取到这个 ID：useRoute 与 useRouter

LabEquipment.vue 使用：

```js
const route = useRoute()
const router = useRouter()

const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id)
})
```

这两个工具的用途不同：

| 写法 | 取得什么 | 本页用途 |
| --- | --- | --- |
| useRoute() | 当前路由的信息 | 读取 query.lab_id |
| useRouter() | 路由器实例 | 返回实验室列表、跳转页面 |

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

### 15.11 为什么 onMounted 先判断 ID，再发请求

当前初始化代码为：

```js
onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning('缺少有效的实验室查询条件 [lab_id]')
    return
  }
  loadLab()
  loadEquipment()
})
```

onMounted 的回调在组件挂载后运行。外面的函数调用注册回调，Vue 在适当时机执行里面的代码。

Number.isInteger 判断是否为整数，<= 0 排除零和负数，|| 表示两种错误情况任意一种成立就拒绝。return 退出本次回调，后面的两个查询不会启动。

| 浏览器查询值 | Number 转换结果 | 当前是否查询 |
| --- | --- | --- |
| "8" | 8 | 是 |
| 未提供，得到 undefined | NaN | 否 |
| 空字符串 | 0 | 否 |
| "abc" | NaN | 否 |
| "0" 或 "-1" | 0 或 -1 | 否 |
| "1.5" | 1.5 | 否 |

NaN 表示一次数字转换没有得到有效数字，Number.isInteger(NaN) 为 false。Number(null) 也会得到 0，本页同样会拒绝。

这是前端的格式检查，不能证明“该 ID 在数据库里存在”。正整数 99999 仍可能没有对应实验室，这部分由 get_lab 处理。

另外，这段 Number 转换不是严格限定 URL 只能包含十进制数字文本，也没有单独处理重复 query 产生的数组；如果以后需要严格的输入格式和安全整数范围，应再明确校验规则。后端类型、范围和资源检查仍然需要独立成立。

### 15.12 页面为什么发两个请求，结果各放在哪里

实验室介绍用：

```js
const lab = ref(null)

const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id)
    if (res.code === 200) {
      lab.value = res.data
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
}
```

设备列表用：

```js
const loadEquipment = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list ?? []
      total.value = res.data?.total ?? 0
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false
  }
}
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

### 15.13 实验室介绍和图片预览怎样显示

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

### 15.14 设备状态标签与按钮禁用有细微差别

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

### 15.15 分页、返回结构与 ?? 的用途

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

后续 offset((page - 1) * page_size) 跳过前面页的数据，limit(page_size) 限制当前页条数。返回前再为每条设备补充 lab_name，这部分沿用第 14 节逻辑。

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
tableData.value = res.data?.list ?? []
total.value = res.data?.total ?? 0
```

?. 处理 data 缺失时的属性访问；?? 是空值合并运算符，只在左边为 null 或 undefined 时采用右边。

例如，合法总数 0 会保持为 0；缺失列表变为 []，缺失总数变为 0。?? 不会把任意错误类型都转换正确；如果后端错误地返回字符串作为 list，仍需要修正接口或增加类型校验。

LabList.vue 当前没有这层 ?? 默认值，两页写法还不完全一致。

### 15.16 当前路由 ID 只在创建页面时读取一次

虽然 useRoute 取得的是响应式路由对象，但这一句：

```js
lab_id: Number(route.query.lab_id)
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

### 15.17 预约按钮目前具体执行了什么

当前代码中有三处预约入口：

| 位置 | 调用函数 | 实际行为 |
| --- | --- | --- |
| LabList.vue 卡片 | handelViewReserve(lab) | ElMessage.info 显示“稍后开发”加实验室名称 |
| LabEquipment.vue 顶部 | hanldeReserveLab() | 空函数 |
| LabEquipment.vue 设备行 | hanldeReserveEquipment(row) | 空函数 |

两段函数现在是：

```js
const hanldeReserveLab = () => {}
const hanldeReserveEquipment = () => {}
```

=> {} 定义一个函数，空的大括号表示函数体没有语句。点击按钮会调用它，但不会请求后端或保存数据。

设备行虽然传了 row，当前函数没有声明接收参数，也没有使用这条数据。JavaScript 允许调用时传入多于形参的实参，因此不会仅因这一点报错。

目前应把功能进度记录为“资源浏览和预约入口已写出，预约业务待开发”。真正预约至少还要定义预约数据、提交内容、登录用户归属、时段、数量和冲突处理等需求；本节不把这些按钮算作预约功能完成。

### 15.18 管理端 Equipment.vue 的最新改动

第一项改动是上一章指出的分页绑定已经修正：

```html
v-model:page-size="params.page_size"
```

现在模板绑定和请求对象使用同一个属性。本次读取与静态检查已经确认，因此第 10.10 节对应任务改为完成。

当前 layout 没有 sizes 项，也就没有页大小选择器。如果以后加上，仍需要处理页大小变化后的页码和重新加载。

第二项改动是模板删除了“删除”按钮，现在行操作只显示“编辑”。但是：

- Equipment.vue 中的 handleDelete 逻辑还保留着。
- frontend/src/api/equipment.js 仍有删除请求函数。
- 后端 DELETE /api/equipment/{equipment_id} 仍保留管理员依赖及删除逻辑。

所以这是界面入口的变化，不能写成“后端删除功能已经移除”。之后可以根据产品需求恢复入口，或清理不再使用的代码。

第三项是 handleSearch 不再声明 async。它内部只是设置页码并调用 load，没有 await；去掉 async 符合当前写法，也不会因此停止请求。当前调用方仍没有等待 load 完成。

上一章 Equipment.vue.resetForm 复制实验室字段的问题仍存在：lab_id、spec、quantity 没有正确重置，status 被写成布尔 true。这里没有因为分页修复就一并解决，继续保留待办。

### 15.19 Layout.vue：角色菜单与当前路径高亮

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
:default-active="router.currentRoute.value.path"
default-active="/manager/home"
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

### 15.20 LabList.vue 中需要整理的复制遗留

当前浏览流程之外，LabList.vue 还保留了一些管理页代码。初学时要学会判断“定义了”与“真正被调用了”的区别。

| 当前内容 | 是否用于本页正常浏览 | 影响或整理方向 |
| --- | --- | --- |
| form、formRef、dialogVisible、resetForm、handleCreate | 模板没有相应编辑弹窗或创建入口 | 可以按浏览页职责清理 |
| handleCreate 中的 nextTick() | 当前模板未调用该函数 | 未导入 nextTick；以后调用这个闲置路径会报错 |
| labOptions 与 loadLabs | 结果未用于当前模板 | onMounted 多发一次列表请求 |
| params.lab_id | 实验室列表接口未声明这个筛选参数 | 不能据此筛选实验室列表 |
| 卡片 header 的裸 template | 没有指定命名插槽 | 不会成为 el-card 的标题插槽 |

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

### 15.21 如果从零写这一版，按什么顺序实现

这次没有改变资源表结构，前提是第 14 节的实验室与设备模型、关联和管理端已完成。建议按下面顺序复现这一增量：

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

### 15.22 真实浏览器验收清单

下面尚未在本次任务中实际操作完成。请使用学习数据库准备两间实验室和多条设备：一间启用、一间停用；设备分属不同实验室，并包含状态为 0 和 1 的记录。为验证分页，需要让某个查询结果超过一页。

| 操作 | 当前应观察到什么 |
| --- | --- |
| 学生登录并查看侧栏 | 有“实验室列表”；无管理员管理菜单入口 |
| 打开实验室列表，观察 Network | 卡片正常加载；当前还会出现一次未使用的 page_size=100 查询 |
| 按名称查询、清空、回车 | 页码回到 1，卡片和总数按新条件更新 |
| 翻页 | page 改变，展示对应页；名称筛选仍随请求发送 |
| 查看 ID 为 8 的实验室设备 | 页面地址带 lab_id=8，同时出现详情和设备列表请求 |
| 对比设备所属实验室 | 请求含 lab_id=8，结果应只属于该实验室 |
| 打开不存在但为正整数的 ID | 详情提示不存在；设备列表请求独立执行，通常为空 |
| 去掉 lab_id 或改为 abc、0、负数、小数 | 提示查询条件无效，不发起两项初始化查询 |
| 查看设备图片 | 有图时显示缩略图，可打开预览；无图时不显示图片组件 |
| 查看维修设备 | 标签显示维修；状态为数字 0 时预约按钮禁用 |
| 点击各预约入口 | 卡片只显示稍后开发；详情页两个入口没有预约请求 |
| 请求 status=true 与 status=false | True 能筛选；当前 False 仍返回所有状态，修正后再验 |
| 查看停用实验室 | 当前学生页未传 status，详情也未限制启用状态；与需求对照确认 |
| 保持同一个设备页，只改变 query 的实验室 ID | 检查是否仍显示旧数据，决定是否补路由监听 |
| 进入设备页观察侧栏高亮 | 当前路径没有对应菜单项，按栏目规则决定是否映射 |
| 学生尝试资源写入接口 | 后端拒绝；不能因为隐藏了按钮就省略此项检查 |
| 退出登录或让 token 失效后再查询 | 前端守卫及后端身份验证按各自机制处理 |
| 管理员进入设备管理 | 页大小绑定使用 page_size；行操作当前只有编辑 |

查看接口时，要同时看 HTTP 状态和 JSON 中的 code。当前 BusinessException 处理器使用 HTTP 200 承载业务错误码；例如“实验室不存在”的默认业务 code 为 500，不会因为文字含“找不到”就自动变成 HTTP 404。

浏览器 Network 中观察完整响应，再与 request.js 返回给页面的对象对比，可以巩固“HTTP 响应外壳”和“业务数据”的区别。

### 15.23 本次完成的隔离检查与验证范围

已经执行：

- 用 SQLite 内存数据库加载实际模型和实际服务函数，检查实验室分页、名称筛选、启用筛选、详情存在与不存在、设备按 lab_id 隔离和关联名称返回。
- 复现 status=False 未生效；确认停用实验室仍可通过当前详情服务查询，维修设备仍包含在设备列表中。
- 静态检查接口依赖：三个 GET 查询使用 get_current_user，资源写入使用 get_current_admin；/list 位于动态详情路径之前。
- 编译 LabList.vue、LabEquipment.vue、Equipment.vue、Layout.vue 的脚本和模板；检查两个前端 API 文件及路由文件的 JavaScript 语法。
- 提取当前页面中的实际函数并使用模拟请求检查：路由带上 lab_id、1 个有效与 7 个无效 ID、空列表默认值、请求失败后恢复 loading、详情结果写入 lab。
- 检查编译产物中的动态菜单属性、LabList.vue 缺少 header 插槽，以及闲置创建函数未导入 nextTick；确认设备分页绑定已修正。

这些检查使用内存数据和模拟依赖，没有导入项目真实数据库配置，没有连接或修改真实数据库，也没有把点击按钮的浏览器流程当作已经完成。

隔离检查可以证明这段代码在相应输入下怎样运行；它不能替代真实 MySQL、Vite 代理、图片地址、登录状态和页面交互共同参与的验收。第 15.22 节及全项目从零搭建检查继续保留。

本章外部资料仅用于核对框架行为，项目具体实现以本地代码和下方快照为依据。引用均链接到对应官方页面；查阅时需结合项目安装版本。

### 15.24 本次相关代码快照

以下快照记录 2026-10-19 读取到的实现，便于按本章复习和复现。没有把本章建议自动合并进业务代码。

equipment_service.py 和前端 api/equipment.js 本次对照没有变化，但它们承担设备筛选与请求封装，所以一并保留。models、schemas 等未变化文件可接着参考第 14 节，避免把历史章节与最新章节混成同一天的版本。

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
import request from '@/utils/request'

// 分页模糊查询实验室列表
export function getLabPageList(params) {
  return request({
    url: '/api/lab/list',
    method: 'get',
    params
  })
}

// 分页模糊查询实验室列表
export function getLab(lab_id) {
  return request({
    url: `/api/lab/${lab_id}`,
    method: 'get'
  })
}

// 新增实验室
export function createLabApi(data) {
  return request({
    url: '/api/lab',
    method: 'post',
    data
  })
}

// 修改实验室
export function updateLabApi(labId, data) {
  return request({
    url: `/api/lab/${labId}`,
    method: 'put',
    data
  })
}

// 删除实验室
export function deleteLabApi(labId) {
  return request({
    url: `/api/lab/${labId}`,
    method: 'delete'
  })
}
```

</details>

<details>
<summary><code>frontend/src/api/equipment.js</code></summary>

```js
import request from '@/utils/request'

// 分页模糊查询列表
export function getEquipmentPageList(params) {
  return request({
    url: '/api/equipment/list',
    method: 'get',
    params
  })
}

// 新增
export function createEquipmentApi(data) {
  return request({
    url: '/api/equipment',
    method: 'post',
    data
  })
}

// 修改
export function updateEquipmentApi(equipmentId, data) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: 'put',
    data
  })
}

// 删除
export function deleteEquipmentApi(equipmentId) {
  return request({
    url: `/api/equipment/${equipmentId}`,
    method: 'delete'
  })
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

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      </div>
      <div>
        <el-row :gutter="16" v-loading="loading">
          <el-col v-for="item in tableData" :key="item.id" :span="6" style="margin-bottom: 16px">
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
                位置: {{ item.location || '-' }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                容量: {{ item.capacity }} 人
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                开放时间:
                {{
                  item.open_time && item.close_time ? `${item.open_time} - ${item.close_time}` : '-'
                }}
              </div>
              <div style="margin-top: 12px; display: flex; gap: 8px">
                <el-button style="flex: 1" @click="handelViewEquipment(item)">查看设备</el-button>
                <el-button style="flex: 1" type="primary" @click="handelViewReserve(item)"
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
import { ref, reactive, onMounted } from 'vue'
import { getLabPageList } from '@/api/lab'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import router from '@/router'

const loading = ref(false)
const tableData = ref([])
const labOptions = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

const handelViewEquipment = (lab) => {
  router.push({ path: '/manager/labequipment', query: { lab_id: lab.id } })
}

const handelViewReserve = (lab) => {
  ElMessage.info(`稍后开发${lab.name}`)
}

onMounted(() => {
  loadLabs()
  load()
})
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
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || '实验室' }}设备列表</span>
          </div>
          <div>
            <el-button type="primary" @click="hanldeReserveLab">预约实验室</el-button>
            <el-button @click="router.push('/manager/lablist')">返回实验室列表</el-button>
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
          开放：{{ lab.open_time && lab.close_time ? `${lab.open_time} - ${lab.close_time}` : '-' }}
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
              {{ row.status === 1 ? '正常' : '维修' }}
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
import { getLab } from '@/api/lab'
import { ElMessage } from 'element-plus'
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEquipmentPageList } from '@/api/equipment'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const lab = ref(null)
const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id) // "8" -> 8
})

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list ?? []
      total.value = res.data?.total ?? 0
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false
  }
}

const hanldeReserveLab = () => {}
const hanldeReserveEquipment = () => {}
const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id)
    if (res.code === 200) {
      lab.value = res.data
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
}

onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning('缺少有效的实验室查询条件 [lab_id]')
    return
  }
  loadLab()
  loadEquipment()
})
</script>
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

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="success" :icon="Plus" @click="handleCreate">新增</el-button>
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
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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
            <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%">
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi
} from '@/api/equipment'
import { getLabPageList } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const labOptions = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = {
  lab_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status
  })
  dialogVisible.value = true
}

// 删除信息
const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' }).then(
    async () => {
      const res = await deleteEquipmentApi(row.id)
      if (res.code === 200) {
        ElMessage.success('删除成功')
        load()
      }
    }
  )
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...equipmentData } = form
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

onMounted(() => {
  loadLabs()
  load()
})
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
        <div style="display: flex; align-items: center; font-size: 24px; font-weight: bold">
          <img style="width: 40px" src="@/assets/imgs/logo.png" alt="" />
          <div style="margin-left: 5px">智能实验室预约系统</div>
        </div>
        <div style="margin-left: auto">
          <el-dropdown @command="handleCommand">
            <div style="display: flex; align-items: center; margin-right: 20px; cursor: pointer">
              <img :src="userInfo?.avatar" alt="" style="width: 30px; border-radius: 50%" />
              <div style="margin-left: 3px">
                {{ userInfo?.name || userInfo?.username || '用户' }}
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
            <el-menu-item index="/manager/lablist" v-if="userInfo?.role === 'student'">
              <el-icon><House /></el-icon>
              <span>实验室列表</span>
            </el-menu-item>
            <el-menu-item index="/manager/lab" v-if="userInfo?.role === 'admin'">
              <el-icon><House /></el-icon>
              <span>实验室管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/equipment" v-if="userInfo?.role === 'admin'">
              <el-icon><Setting /></el-icon>
              <span>设备列表管理</span>
            </el-menu-item>
            <el-menu-item index="/manager/user" v-if="userInfo?.role === 'admin'">
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
import { Menu as IconMenu, House, Setting, User } from '@element-plus/icons-vue'
import router from '@/router'
import { logout } from '@/utils/auth'
import { useUser } from '@/utils/user'
const { userInfo } = useUser()

const handleLogout = () => {
  logout()
  router.push('/login')
}

const goPerson = () => {
  router.push('/manager/profile')
}

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/manager/profile')
  } else if (command === 'password') {
    router.push('/manager/password')
  } else if (command === 'logout') {
    logout()
    router.push('/login')
  }
}
</script>
```

</details>

<details>
<summary><code>frontend/src/router/index.js</code></summary>

```js
import { getToken } from '@/utils/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/manager/home' },
    {
      path: '/manager',
      name: 'Layout',
      component: () => import('@/layouts/Layout.vue'),
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/Home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/Lab.vue')
        },
        {
          path: 'equipment',
          name: 'Equipment',
          component: () => import('@/views/Equipment.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/User.vue')
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue')
        },
        {
          path: 'password',
          name: 'Password',
          component: () => import('@/views/Password.vue')
        },
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
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue')
    }
  ]
})

// 路由守卫
router.beforeEach((to, from) => {
  const token = getToken()
  if (to.path === '/login' || to.path === '/register') {
    return true
  } else {
    return token ? true : '/login'
  }
})

export default router
```

</details>

---

<a id="16-reservation"></a>

## 16. 新增教程：实验室与设备预约提交

更新时间：2026-10-20。本章根据本轮预约代码讲解，第 17 章继续解释相应修补和验证。

> 第 15 章中预约按钮是占位；现在三个预约入口都接到了公共弹窗，并能请求后端保存待审核记录。本章描述的是“提交预约”这个阶段，查询、审核和取消还需要继续开发。
>
> [逻辑审查](docs/logic-review-2026-10-20.md)记录修补前的问题，[指定修补说明](docs/logic-fixes-2026-10-20.md)记录后续处理。阅读时不能把两份文档都当成当前最终状态；第 17.16 节给出逐项对照。

### 16.1 先确定预约要保存什么

之前的实验室和设备是“资源资料”，例如名称、位置、数量。预约新增的是“谁希望在什么时间使用哪个资源”。

一次预约需要回答：

| 问题 | 当前字段 |
| --- | --- |
| 谁提交 | user_id，由当前登录用户确定 |
| 哪个实验室 | lab_id |
| 整间实验室还是某台/组设备 | equipment_id 是否为空 |
| 哪一天 | date |
| 哪个时间段 | start_time、end_time |
| 有什么说明 | remark |
| 目前处理到哪一步 | status |

当前用一张 reservation 表保存两种预约。equipment_id 为 NULL，表示预约实验室；不为空，表示预约这个设备记录。

设备的 quantity 只是资源资料中的数量。预约请求没有预约数量字段，当前按一条设备记录整体判断是否冲突，不能把它解释为已经支持“10 台设备中的 2 台”。

### 16.2 文件地图与阅读顺序

| 层 | 文件 | 负责什么 |
| --- | --- | --- |
| 数据库 | backend/app/models/reservation.py | 表、外键、状态和 ORM 关系 |
| 输入模型 | backend/app/schemas/reservation.py | 接收预约字段、规范时间字符串 |
| 业务 | backend/app/services/reservation_service.py | 时间、资源、归属、冲突、事务及写入 |
| HTTP 接口 | backend/app/api/reservation.py | 接收请求、取得当前用户和数据库会话 |
| API 注册 | backend/app/api/__init__.py | 把预约路由加入 /api |
| 应用入口 | backend/app/main.py | 导入模型、建表、注册统一 API 和异常处理 |
| 前端请求 | frontend/src/api/reservation.js | 封装 POST 请求 |
| 公共弹窗 | frontend/src/components/ReserveDialog.vue | 输入日期时段、校验并提交 |
| 实验室卡片 | frontend/src/views/LabList.vue | 选择实验室并打开弹窗 |
| 实验室设备页 | frontend/src/views/LabEquipment.vue | 选择整间实验室或设备并打开弹窗 |

建议先读模型和请求结构，再读正常流程，然后读第 17 章的并发处理。这样看到锁、重试和异常时，能够知道它们在保护哪一条业务规则。

### 16.3 新表与外键：为什么预约要关联三个模型

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

### 16.4 本次还有表名变化：lab 改为 labs

当前 Lab.__tablename__ 已从 "lab" 改为 "labs"，设备模型的 ForeignKey 也从 "lab.id" 改为 "labs.id"。新预约表直接引用 labs.id。

这个改动不影响前端仍使用 /api/lab 作为接口地址。数据库表名和 HTTP 路径由各自代码约定，不需要同名。

但它会影响旧数据库：

- 新的空数据库会按模型建立 labs 表。
- 旧库的 lab 表不会因为修改 Python 字符串而自动改名。
- create_all() 可能新建空 labs 表，旧数据仍在 lab 中。
- 已有 equipments 的外键也不会自动从 lab.id 迁到 labs.id。

本次已有的 add_username_unique 脚本只处理用户名唯一性，不处理表名、实验室数据或设备外键。

因此从第 14、15 章升级旧学习库时，先备份，再核对实际表结构、数据、ID 和关联外键，准备迁移方案。不能在未检查时直接把旧表删除。当前没有这项自动迁移脚本，本次文档工作也没有执行旧库迁移。

若从空目录、空数据库复现本轮版本，使用当前模型中的 labs 即可，不需要先创建旧 lab 表再改名。

### 16.5 请求模型里的时间规范化

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

### 16.6 新接口怎样接入现有应用

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

### 16.7 一次提交的完整调用链

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

锁的具体作用放在第 17 章。这里先记住，查冲突和写入预约必须在同一套事务规则里完成，不能把它们当成互不相关的两步。

### 16.8 业务函数先检查日期与时间

服务先把请求里的开始、结束时间解析成 time 对象，再与当前时间、实验室开放时间比较。

当前规则如下：

| 条件 | 当前处理 |
| --- | --- |
| date 文本小于今天的 YYYY-MM-DD 文本 | 拒绝，预约日期不能小于当天 |
| end_time 小于 start_time | 拒绝 |
| 日期是今天，开始时间小于当前分钟 | 拒绝 |
| 实验室不存在或关闭 | 拒绝 |
| 有开放开始时间，预约开始更早 | 拒绝 |
| 有关闭时间，预约结束更晚 | 拒绝 |
| 设备不存在、归属不符或状态不是 1 | 拒绝 |

当天时间会去掉秒和微秒，因此比较精度是分钟。预约业务仍使用服务器的 datetime.now() 本地时间；JWT 改成 UTC 并没有自动把预约业务也改成统一时区。

当前存在几个明确边界：

- 日期仅做字符串比较，没有验证日历上是否存在这一天。
- 使用 end_time < start_time，等于时不会被这一条拒绝，所以零时长问题仍在。
- 当前时段模型不支持结束时间跨到次日。
- 实验室自身开放时间没有同等完整的保存校验，数据库中不合法的文本仍可能让 strptime 抛错。
- props 和页面上的禁用按钮不能代替后端校验；当前后端检查设备状态是否严格等于 1。

这些不是本轮教程新加的功能，而是对现有检查范围的解释。应按第 17.16 节继续完善。

### 16.9 怎样判断两个时间段重叠

已有预约记为 A，新预约记为 B。重叠条件是：

```text
A 的开始 < B 的结束
并且
A 的结束 > B 的开始
```

例如已有 09:00–10:00：

| 新预约 | 是否重叠 | 原因 |
| --- | --- | --- |
| 09:00–10:00 | 是 | 完全相同 |
| 09:30–10:30 | 是 | 09:30–10:00 共同占用 |
| 08:30–09:30 | 是 | 09:00–09:30 共同占用 |
| 08:00–11:00 | 是 | 包含已有时段 |
| 10:00–11:00 | 否 | 只是首尾相邻 |
| 08:00–09:00 | 否 | 只是首尾相邻 |

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

filter 中多个条件共同成立才算匹配。in_([0, 1]) 表示只考虑待审核和已通过记录。func.time 生成数据库 TIME 函数表达式，让存储的时间文本按数据库时间进行比较；它不会把任意非法历史文本都变成有效预约数据。

### 16.10 实验室预约与设备预约的冲突范围不同

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

is_(None) 对应 SQL 的 IS NULL。SQL 里的空值判断与普通值相等比较不同，所以这里明确使用空值判断表达式。

当前规则是：

- 实验室预约只与同实验室的“整间预约”比较。
- 设备预约只与同一个设备 ID 的预约比较。
- 不同设备可以在同一时段分别预约。
- 整间实验室和其中设备，也可能在同一时段分别预约。

后端现在会串行处理同一实验室的预约提交，但“先后处理请求”和“业务上互相冲突”是两个概念。事务锁不会自动补出实验室与设备之间的互斥规则。

设备冲突不再依赖历史预约的 lab_id，这样设备更换所属实验室后，旧记录仍会参与同设备冲突检查。设备转移前如何处理未来预约，是另一项尚未完整定义的规则。

### 16.11 两个父页面怎样复用一个弹窗

LabList.vue 中保存：

```js
const reserveVisible = ref(false)
const currentLab = ref(null)

const handelReserve = (lab) => {
  currentLab.value = lab
  reserveVisible.value = true
}
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
  currentEquipment.value = null
  reserveVisible.value = true
}

const hanldeReserveEquipment = (equipment) => {
  currentEquipment.value = equipment
  reserveVisible.value = true
}
```

点“预约实验室”时先清空 currentEquipment 很重要：否则刚刚选过设备，再切回实验室预约，弹窗可能仍带着上一次的设备 ID。

父页面负责“选中了谁”，公共组件负责“怎么填写和提交”。这是本次组件复用的主要设计思想。

### 16.12 defineProps、defineEmits 和 v-model:visible

ReserveDialog.vue 声明：

```js
const props = defineProps({
  visible: Boolean,
  labId: Number,
  labName: String,
  equipmentId: Number,
  equipmentName: String
})

const emit = defineEmits(['update:visible'])
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

### 16.13 弹窗内部怎样控制打开、重置与关闭

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
  await nextTick()
  formRef.value?.resetFields()
}
```

nextTick 等待本轮 Vue 更新，让表单引用有机会准备完成。?. 表示引用还没有时不继续调用。

resetFields 会按表单字段保存的初始值恢复并清理校验状态，不是简单把所有字段都变成空字符串。当前初始日期为空，开始和结束默认是 09:00、17:00。恢复规则见 [Element Plus Form](https://element-plus.org/en-US/component/form.html)。

默认时段不会自动匹配每个实验室的开放时间。例如实验室 16:00 关闭，用户还需要调整默认结束时间，后端也会再次检查。

### 16.14 日期和时间控件：显示格式与提交值

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

### 16.15 从表单对象转换成 API 请求体

前端 API 函数：

```js
export function createReservationApi(data) {
  return request({
    url: '/api/reservation',
    method: 'post',
    data
  })
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
  remark: form.remark
})
```

不是所有名字都会自动转换。labId → lab_id、startTime → start_time 都是这段代码明确映射的结果。

?? null 把 undefined 或 null 的设备 ID 统一为 null，让后端按整间实验室预约处理；数字设备 ID 则保持原值。

名称只用来展示，接口凭 ID 查询真实记录。当前请求也没有包含 user_id 和 status，后端分别使用当前用户 ID 和固定的初始状态。

request 返回 Promise，await 后 res 是拦截器解包后的业务响应对象。这个机制延续之前 loginApi 的讲解。

### 16.16 submitting 为什么放在表单校验之前

提交函数开头：

```js
if (submitting.value || !formRef.value) return
submitting.value = true
```

同一个弹窗已经在提交时直接返回；表单引用还不存在时也返回。随后马上设置 submitting=true，再去等待校验，避免快速双击在异步校验期间启动两条提交。

表单校验：

```js
const valid = await formRef.value.validate().catch(() => false)
if (!valid) return
```

校验失败的拒绝被转换成 false，随后提前返回。由于这段代码位于 try 内，finally 仍会执行，把 submitting 恢复成 false。

请求成功时显示“预约已提交，请等待审核”，并 emit 关闭弹窗。网络失败时进入 catch，当前填写的表单保留，finally 恢复按钮状态。

当前 request.js 对业务 code=409 会提示，但仍返回业务对象，所以这类冲突通常不会进入组件 catch，而是让 if (res.code === 200) 不成立。业务 code=401 和 HTTP 请求失败会走拒绝路径。

submitting 保护当前组件的一次操作；两个浏览器、两个用户甚至直接调用接口都可以同时请求，因此真正的并发占用检查还要由数据库事务负责。

### 16.17 成功返回与预约状态的含义

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

| 值 | 含义 | 当前冲突查询是否考虑 |
| --- | --- | --- |
| 0 | 待审核 | 是 |
| 1 | 已通过 | 是 |
| 2 | 已拒绝 | 否 |
| 3 | 已取消 | 否 |

本轮提交只写入 0。状态字段允许表达后续阶段，不代表已经有接口把 0 改成 1、2、3。

因此现在待审核记录会持续参与对应日期和时段的冲突判断，而用户还不能通过页面查看、取消，管理员也不能通过正常页面审核。下一步需要围绕真实流程补齐状态转换和权限。

### 16.18 从零编写这一模块的顺序

1. 先明确整间实验室和设备的预约规则，选择当前“一张表 + 可空 equipment_id”的设计。
2. 在已有 users、labs、equipments 模型上增加 Reservation，并在建表前导入。
3. 编写 ReservationCreateRequest，固定前后端字段名及时间格式。
4. 写服务中的资源、日期、开放时间和归属校验。
5. 写重叠公式和有效状态范围；结合第 17 章把校验和插入放入受保护的事务。
6. 注册 POST /api/reservation，使用当前用户作为预约人。
7. 添加 createReservationApi，先确认接口请求和业务响应结构。
8. 写公共 ReserveDialog，完成 props、表单、校验、提交及关闭事件。
9. 从两个父页面传入目标资源，实验室预约时清空设备选择。
10. 运行已有回归测试，再进行下一节的真实浏览器验收。

新库使用当前模型；旧库先完成第 16.4 节的结构核对和第 17.9 节的用户名索引升级。不要把“能在现有电脑运行”当成已经验证过从空环境复现。

### 16.19 本轮预约的浏览器验收清单

以下为待执行的端到端检查；本次仅运行了隔离测试和构建，没有在浏览器连真实 MySQL 完成这些操作。

| 操作 | 应检查的结果 |
| --- | --- |
| 从实验室卡片打开预约 | 实验室名称正确，不显示设备字段 |
| 从设备行打开预约 | 实验室与设备名称正确，请求携带正确设备 ID |
| 先预约设备，再打开实验室预约 | equipment_id 为 null，没有遗留上次选择 |
| 关闭弹窗后重新打开 | 字段按初始值恢复，校验提示清理 |
| 日期留空后提交 | 前端校验不通过，不发送创建请求 |
| 正常提交 | 新记录 user_id 来自登录用户，status=0；界面关闭并提示等待审核 |
| 快速连续点击提交 | 单个组件不同时发出多次创建请求 |
| 同资源完全重叠或部分重叠 | 后端返回业务 code=409，表单保留 |
| 相邻时段 | 在其他条件满足时允许提交 |
| 不同用户同时抢同一时段 | 真实 MySQL 下核对仅一个成功，其他冲突或可重试提示 |
| 设备不属于指定实验室 | 后端拒绝，且没有残留预约 |
| 实验室关闭或设备维修 | 后端拒绝 |
| 开始早于开放、结束晚于关闭 | 后端拒绝 |
| 当天已过去的开始时间 | 按服务端当前分钟拒绝 |
| 零时长、非法日期 | 当前仍有漏洞，作为后续修补验收用例，不记为已正确拒绝 |
| 查看、审核、取消预约 | 当前没有入口，不记为已实现 |
| 直接调用接口时登录失效 | 后端拒绝，前端按当前会话处理 401 |

遇到业务 code=409，要同时检查 HTTP 状态：当前 BusinessException 的统一响应使用 HTTP 200。HTTP 200 只表示 HTTP 请求得到正常处理的响应，业务是否成功还要看 JSON.code。

### 16.20 本章代码快照

以下记录 2026-10-20 的当前实现，包括已在代码中落地的并发修补；后续第 17 章会拆开解释。示例和快照中的时间、资源规则保持当前状态，没有自动应用本章提出的待办。

<details>
<summary><code>backend/app/models/lab.py</code></summary>

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
<summary><code>backend/app/api/__init__.py</code></summary>

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
<summary><code>backend/app/main.py</code></summary>

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

<details>
<summary><code>frontend/src/api/reservation.js</code></summary>

```js
import request from '@/utils/request'

// 创建预约
export function createReservationApi(data) {
  return request({
    url: '/api/reservation',
    method: 'post',
    data
  })
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
          <el-input type="textarea" v-model="form.remark" placeholder="请输入备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交预约</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { createReservationApi } from '@/api/reservation'
import { ElMessage } from 'element-plus'
import { ref, reactive, nextTick } from 'vue'
const props = defineProps({
  visible: Boolean,
  labId: Number,
  labName: String,
  equipmentId: Number,
  equipmentName: String
})
const submitting = ref(false)
const formRef = ref()
const emit = defineEmits(['update:visible'])
const form = reactive({
  date: '',
  startTime: '09:00',
  endTime: '17:00',
  remark: ''
})
const rules = {
  date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  startTime: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  endTime: [{ required: true, message: '请选择结束时间', trigger: 'change' }]
}
const handleOpen = async () => {
  await nextTick()
  formRef.value?.resetFields()
}
const handleSubmit = async () => {
  if (submitting.value || !formRef.value) return
  submitting.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const res = await createReservationApi({
      lab_id: props.labId,
      equipment_id: props.equipmentId ?? null,
      date: form.date,
      start_time: form.startTime,
      end_time: form.endTime,
      remark: form.remark
    })
    if (res.code === 200) {
      ElMessage.success('预约已提交, 请等待审核')
      emit('update:visible', false)
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    submitting.value = false
  }
}
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

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
      </div>
      <div>
        <el-row :gutter="16" v-loading="loading">
          <el-col v-for="item in tableData" :key="item.id" :span="6" style="margin-bottom: 16px">
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
                位置: {{ item.location || '-' }}
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                容量: {{ item.capacity }} 人
              </div>
              <div style="font-size: 13px; margin-top: 6px; color: #666">
                开放时间:
                {{
                  item.open_time && item.close_time ? `${item.open_time} - ${item.close_time}` : '-'
                }}
              </div>
              <div style="margin-top: 12px; display: flex; gap: 8px">
                <el-button style="flex: 1" @click="handelViewEquipment(item)">查看设备</el-button>
                <el-button style="flex: 1" type="primary" @click="handelReserve(item)"
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
import { ref, reactive, onMounted } from 'vue'
import { getLabPageList } from '@/api/lab'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import ReserveDialog from '@/components/ReserveDialog.vue'
const reserveVisible = ref(false)
const currentLab = ref(null)
const loading = ref(false)
const tableData = ref([])
const labOptions = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

const handelViewEquipment = (lab) => {
  router.push({ path: '/manager/labequipment', query: { lab_id: lab.id } })
}

const handelReserve = (lab) => {
  currentLab.value = lab
  reserveVisible.value = true
}

onMounted(() => {
  loadLabs()
  load()
})
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
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="font-size: 16px; font-weight: bold">
            <span>{{ lab?.name || '实验室' }}设备列表</span>
          </div>
          <div>
            <el-button type="primary" @click="hanldeReserveLab">预约实验室</el-button>
            <el-button @click="router.push('/manager/lablist')">返回实验室列表</el-button>
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
          开放：{{ lab.open_time && lab.close_time ? `${lab.open_time} - ${lab.close_time}` : '-' }}
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
              {{ row.status === 1 ? '正常' : '维修' }}
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
import { getLab } from '@/api/lab'
import { ElMessage } from 'element-plus'
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEquipmentPageList } from '@/api/equipment'
import ReserveDialog from '@/components/ReserveDialog.vue'
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const lab = ref(null)
const reserveVisible = ref(false)
const currentEquipment = ref(null)
const params = reactive({
  page: 1,
  page_size: 10,
  lab_id: Number(route.query.lab_id) // "8" -> 8
})

// 加载设备分页数据
const loadEquipment = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list ?? []
      total.value = res.data?.total ?? 0
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  } finally {
    loading.value = false
  }
}

const hanldeReserveLab = () => {
  currentEquipment.value = null
  reserveVisible.value = true
}
const hanldeReserveEquipment = (equipment) => {
  currentEquipment.value = equipment
  reserveVisible.value = true
}
const loadLab = async () => {
  try {
    const res = await getLab(params.lab_id)
    if (res.code === 200) {
      lab.value = res.data
    }
  } catch {
    // 请求失败时由请求拦截器提示错误。
  }
}

onMounted(() => {
  if (!Number.isInteger(params.lab_id) || params.lab_id <= 0) {
    ElMessage.warning('缺少有效的实验室查询条件 [lab_id]')
    return
  }
  loadLab()
  loadEquipment()
})
</script>
```

</details>

<a id="17-logic-fixes"></a>

## 17. 新增教程：逻辑修补、事务并发与回归验证

更新时间：2026-10-20。本章把修补与原来的错误原因联系起来，帮助你理解“正常操作能成功”之后，还需要怎样处理同时请求、失败和旧数据。

### 17.1 怎样阅读“审查”和“修补”两份记录

[logic-review-2026-10-20.md](docs/logic-review-2026-10-20.md)包含 18 项问题及两项待明确的业务规则，是修补前的检查记录。

[logic-fixes-2026-10-20.md](docs/logic-fixes-2026-10-20.md)说明按问题名称选择修复的 7 项。名称与代码对应如下：

| 指定修补 | 当前实现位置 |
| --- | --- |
| 并发重复预约 | reservation_service 的事务锁、锁内冲突检查和重试 |
| 设备归属校验 | equipment.lab_id 与 lab.id 比较；冲突按设备 ID 查询 |
| 并发注册同名账号 | User 唯一约束、注册/管理员创建的 IntegrityError 处理、迁移脚本 |
| 新增设备继承旧值 | Equipment.vue.resetForm |
| 容量输入冲突 | Lab.vue 数字控件、LabCreateRequest/LabUpdateRequest 的 Field |
| 删除有预约用户失败 | user_service 关联检查、回滚，User.vue 捕获确认框及请求异常 |
| JWT 时间偏差 | utils/jwt.py 使用 timezone.utc |

源码还有实验室/设备关联删除、登录跳转及旧请求 401 处理等变化，本章一并讲解。它们不需要强行归入“7 项指定修补”。

学习时用“错误怎样触发 → 修改怎样阻止它 → 还有哪些限制 → 怎样验证”的顺序，比只记住新增了几个 try/except 更容易复现。

### 17.2 “先查没有，再创建”为什么仍然会重复

假设只写：

```text
查询：这个时间段有没有预约？
没有 → 插入预约 → 提交
```

单人逐次点击可能一直正常，但两个请求可以交错：

| 时刻 | 请求 A | 请求 B |
| --- | --- | --- |
| 1 | 查询，没有预约 | |
| 2 | | 查询，也没有预约 |
| 3 | 插入并提交 | |
| 4 | | 插入并提交 |

两个请求都没有违背自己当时看见的结果，最终却占用了同一资源。

这叫竞态：结果依赖多个操作的执行先后。并发并不要求每一行代码在物理上完全同时执行，只要流程交错就可能出现。

前端 submitting 只能保护当前组件；另外一名用户不会共享这个变量。只给“资源、日期、开始、结束完全相同”加唯一约束，也挡不住 09:00–10:00 与 09:30–10:30 的部分重叠。

因此当前预约修补使用事务锁，让影响同一资源的检查和插入按约定顺序完成。账号重名则适合用数据库唯一约束，两类问题采用的工具不同。

### 17.3 先理解 Session、事务、commit 和 rollback

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

### 17.4 为什么先锁实验室，而不是只锁“查到的预约”

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

### 17.5 为什么冲突查询还要 with_for_update()

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

### 17.6 外层包装函数：失败回滚和有限重试

reservation_service.py 将主要逻辑放进 _create_reservation，外层 create_reservation 负责异常处理。

下划线开头是“内部辅助函数”的命名约定，不是 Python 强制的访问权限。接口调用外层函数，避免漏掉回滚和重试。

当前按 range(3) 执行，attempt 依次为 0、1、2：

| 异常情况 | 当前处理 |
| --- | --- |
| MySQL 死锁码 1213，前两次尝试 | 先回滚，短暂等待，再重新执行整个事务 |
| 第三次仍死锁 | 回滚，返回业务 code=409，提示资源正忙 |
| 锁等待超时码 1205 | 回滚，直接返回上述忙碌提示 |
| 其他 OperationalError | 回滚后继续抛出原异常 |
| 业务校验失败或其他 Exception | 回滚后继续抛出 |

最多是总共执行三次，不是首次之后再重试三次。等待分别是 0.01、0.02 秒，只在前两次死锁重试前发生。

死锁可以理解为多个事务各自持有某些锁，又互相等待对方释放。数据库会选择回滚某个事务，应用要准备重新执行完整流程。参见 [MySQL 死锁处理](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html)。

为什么不能只重试最后的 INSERT？因为数据库状态可能已经变化，资源和冲突检查也必须重新做。

异常语法有两个常见形式：

- 单独的 raise：把当前异常继续抛给上层。
- raise BusinessException(...) from exc：抛出面向业务的异常，同时保留原始异常作为原因，便于定位。

这里 rollback 后再 raise，确保失败不会留下仍持锁的未结束事务。当前返回的 409 是业务码，统一 BusinessException 处理器仍使用 HTTP 200。

### 17.7 设备存在还不够：必须属于所选实验室

当前新增：

```python
if equipment.lab_id != lab.id:
    raise BusinessException(message="该设备不属于所选实验室", code=400)
```

例如请求 lab_id=1、equipment_id=9，而设备 9 实际属于实验室 2，接口应该拒绝。即使前端正常页面不会这样组装参数，后端仍要独立检查。

设备冲突现在只按实际设备 ID 查，不再额外限定历史预约的 lab_id。这样历史记录里的实验室 ID 与设备现在的位置不同，也不会被冲突查询漏掉。

这解决了审查中“跨实验室构造参数”以及“只因设备移位而漏查历史冲突”的关键部分。

但管理员更新设备时，仍没有专门处理“设备还有未来有效预约，是否允许搬迁”的流程；预约历史也仍保留原来的实验室 ID。不要把冲突查询修正写成设备转移业务已全部完成。

### 17.8 用户名唯一性：前置查询加数据库最终约束

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

如果数据库没有真正安装唯一约束，这个异常分支不会凭空阻止同名写入。因此已有库必须执行下一节的升级。

注册服务还修正了原来的 db.rollback：

```python
db.rollback()
```

不带括号只是取得方法对象；带括号才执行回滚。这与前面 JavaScript 中“函数本身”和“调用函数”是同一类基础区别。

### 17.9 升级脚本为什么不能省略，怎样保证可重复执行

模型声明只会影响新表创建；已有 users 表不会被 create_all() 自动追加唯一约束。

backend/app/migrations/add_username_unique.py 的 upgrade(connection) 依次执行：

1. inspect(connection) 读取数据库实际已有的唯一约束和索引。
2. 如果已存在仅针对 username 的唯一约束或唯一索引，返回 False，表示无需修改。
3. 用反射加载已有 users 表结构。
4. GROUP BY username、HAVING COUNT(*) > 1 查找重复用户名。
5. 发现重复则抛错，保留账号和预约数据，由维护者先核实处理。
6. 没有重复则创建 uq_users_username 唯一索引，返回 True。

脚本可以重复执行，而不会每次再建一个相同约束，这种性质叫幂等。它不是“执行多少次都会新增一条相同数据”，而是重复执行不会再次改变已达到目标的状态。

操作命令必须在 backend 目录运行：

```powershell
.\.venv\Scripts\python.exe -m app.migrations.add_username_unique
```

-m 后面是 Python 模块路径，用点分隔，不能写成文件系统中的反斜杠路径。

脚本读取实际项目数据库配置，会修改目标库结构。运行前应备份、确认配置目标并暂停账号创建等相关写入；若两个检查与建索引之间仍有人写入重复账号，升级也可能失败。

本次只运行测试中的临时 SQLite 版本，没有对你的 MySQL 执行这个命令。该脚本也不处理第 16.4 节的 lab → labs 迁移。

### 17.10 设备表单和实验室容量修补

设备 resetForm 现在覆盖：

```js
Object.assign(form, {
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})
```

这样从编辑切到新增时，实验室、型号、数量都恢复默认，status 保持与设备单选项一致的数字 1。上一章残留的 location、capacity、开放时间等实验室字段不再由这个重置函数添加。

Object.assign 只覆盖列出的键；修补后应在重新加载的干净页面状态检查，不能指望它删除旧运行状态里曾经存在的额外属性。

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

### 17.11 有历史关联时怎样删除

当前三个资源的删除策略如下：

| 删除对象 | 服务先检查什么 | 存在关联时的结果 |
| --- | --- | --- |
| 用户 | 是否为当前登录用户；是否有任意预约记录 | 拒绝删除本人；有预约时提示可禁用 |
| 实验室 | 是否有预约；是否仍有设备 | 拒绝，提示关闭实验室或先处理设备 |
| 设备 | 是否有任意预约记录 | 拒绝删除 |

这里的“任意预约”没有排除拒绝、取消或过去的记录。保留历史归属和“是否占用未来时段”是两种不同判断。

为什么先查过，提交时还要捕获 IntegrityError？因为关联检查结束后、实际删除提交前，另一个请求仍可能新建关联记录。数据库外键是最后一道约束；提交失败时回滚并返回业务 code=409，避免直接把约束错误暴露成模糊的 500。

前端 User.vue、Lab.vue、Equipment.vue 都把确认和请求放在同一个 try 中：

```js
try {
  await ElMessageBox.confirm('确认删除？', '确认删除', { type: 'warning' })
  const res = await deleteUserApi(row.id)
  if (res.code === 200) {
    ElMessage.success('删除用户成功')
    await load()
  }
} catch {
  // 取消、关闭和请求失败都在这里结束这次操作。
}
```

这是简化的用户删除片段，完整写法见快照。

确认框的取消和关闭也会让等待的 Promise 拒绝，catch 可以接住这种正常操作。请求失败的提示由拦截器处理。业务 code=409 通常仍返回对象，因此不会进入成功刷新分支。

Equipment.vue 的删除按钮本轮已经恢复，不能继续沿用第 15 章“只有编辑入口”的描述。

### 17.12 JWT 时间修正：给时间带上 UTC 时区

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

### 17.13 额外变化：防止旧请求的 401 清除新登录

本次 auth.js 增加了模块内变量 authVersion；setToken、removeToken 每调用一次，就把它加 1。

请求发出时，拦截器记录：

```js
config._authVersion = getAuthVersion()
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
if (config?._authVersion !== getAuthVersion()) return
const token = getToken()
if (token && config.headers?.Authorization !== `Bearer ${token}`) return
```

只有错误属于当前这次登录状态，才提示并执行 logout、router.replace('/login')。token 文本相同但已经重新登录时，版本号仍能区分先后两次会话操作。

一次有效注销会增加版本，所以其他同批旧请求的 401 再回来时，不会重复清理和提示。

这里提前 return 只是跳过全局注销处理；响应拦截器仍会 Promise.reject，让原请求表达失败。没有把未授权请求变成业务成功。

authVersion 只存在当前页面的 JavaScript 模块内，刷新会重建，也不是跨标签页共享状态，更不是后端 token 撤销列表。因此它解决的是当前页面异步请求的先后问题。

### 17.14 登录成功后，为什么还检查跳转结果

Login.vue 在保存登录数据后，改成等待 router.replace('/manager/home')。

replace 替换当前浏览历史记录，避免成功登录后浏览器后退马上回到刚才的登录页。随后代码检查实际路径是不是 /manager/home，再显示“登录成功”。

导航 Promise 可能结束但返回导航失败信息，加载路由组件也可能抛错。因此现在分别处理“没有到达首页”和“首页加载失败”。导航失败的行为可查 [Vue Router Navigation Failures](https://router.vuejs.org/guide/advanced/navigation-failures.html)。

保存 token 与导航成功是两个步骤。当前保存先发生，导航失败不会自动回滚已经保存的 token；页面提示用户重试或刷新。

这个变化与上一节配合：一方面避免旧请求清掉新 token，另一方面避免首页尚未真正到达，就立刻给出完整登录成功的界面反馈。

### 17.15 回归测试到底证明了什么

本轮重新执行了仓库现有测试：

```powershell
# 在 backend 目录
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

结果为 19 项通过。测试文件是 [backend/tests/test_logic_fixes.py](backend/tests/test_logic_fixes.py)，主要覆盖：

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

当前没有在真实浏览器中完成端到端验收，也没有运行旧库迁移。应把这些未做项与已通过检查分别记录。

### 17.16 原审查 18 项问题的当前状态

以下按原审查的问题编号对照，避免把“修补了 7 项”误读成“18 项全部修好”。

| 审查项 | 当前状态 | 仍需注意 |
| --- | --- | --- |
| 1 并发重复预约 | 已加入事务锁、锁定读、回滚和重试，隔离测试通过 | 真实 MySQL/InnoDB 并发待验收 |
| 2 设备归属缺失 | 已修补 | 以后新增预约入口也要复用规则 |
| 3 设备转移绕过预约 | 部分处理 | 同设备历史冲突不再因 lab_id 变化漏查；未来预约与转移政策尚未补齐 |
| 4 缺少查询、审核和取消 | 未实现 | 目前只能提交待审核记录 |
| 5 并发同名账号 | 代码与升级脚本已补齐 | 旧库约束实际升级尚未执行 |
| 6 非法日期与零时长 | 仍待修补 | 时间文本已规范，date 仍是 str，结束等于开始仍可通过这项校验 |
| 7 基础数据约束不足 | 部分处理 | 容量已修补；设备数量/状态、开放时间等仍待完善 |
| 8 新增设备继承旧值 | 已修补 | 按当前字段重置 |
| 9 容量输入类型冲突 | 已修补 | 需结合真实浏览器再验 |
| 10 有预约用户删除异常 | 已修补 | 任意预约历史都阻止删除，提供禁用方案 |
| 11 JWT 时区偏差 | 已修补并回归验证 | 不代表旧 token 已具备撤销机制 |
| 12 改密后旧 token 仍有效 | 未处理 | 需定义并实现服务端会话失效策略 |
| 13 最后一个管理员可自我降级/禁用 | 未处理 | 当前仍缺少有效管理员数量保护 |
| 14 文件上传没有登录依赖 | 未处理 | 当前接口仍可匿名访问 |
| 15 超过 bcrypt 字节限制的密码异常 | 未处理 | 注册、登录、改密和管理员创建需统一规则 |
| 16 型号搜索提示与实现不符 | 未处理 | 当前只查设备名称 |
| 17 status=False 实验室筛选被忽略 | 未处理 | 当前仍为 if status |
| 18 用户编辑状态布尔/数字不一致 | 未处理 | 前后端或表单转换需要统一 |

额外两项业务规则仍待决定和实现：整间实验室预约是否占用其中设备；设备是否允许按 quantity 中的部分数量预约。

本表描述当前代码和测试范围，不把文档里提出的建议自动算作已完成修改。

### 17.17 对前面教程结论的更新

| 之前的记录 | 当前更新 |
| --- | --- |
| 第 14、15 章使用 lab 表 | 当前模型改用 labs，旧库需要单独核对迁移 |
| 第 15 章预约按钮为空或只提示 | 当前已接入 ReserveDialog 和 POST 提交 |
| 第 14、15 章设备 resetForm 有残留 | 已按实际设备字段修补 |
| 第 14 章容量输入可能得到字符串 | 当前使用数字控件，并加后端正数约束 |
| 第 15 章设备管理移除删除按钮 | 本轮已恢复 |
| 关联资源删除可能直接触发数据库错误 | 当前对用户、实验室和设备增加检查及失败回滚 |
| 早期 README 提示单独安装 multipart | 当前 requirements.txt 已包含它及 cryptography |
| request.js 收到 401 直接清理登录 | 当前先确认是否属于仍有效的前端会话版本 |

历史代码快照继续保留。章节上的日期说明它记录哪个阶段，不能把第 14 章的旧 models 与本章新的 reservation.py 随意混合，尤其要保持外键引用表名一致。

目前图标包仍是 Element Plus 的传递依赖，锁文件已包含；把直接使用的 @element-plus/icons-vue 显式列入 package.json 仍是依赖整理项。

### 17.18 怎样把本轮变化放进从零复现过程

在已学完前面基础模块的前提下，建议这样复现当前版本：

1. 用清单安装依赖，创建专用学习数据库，配置自己的数据库连接和 JWT 密钥。
2. 同步当前 models：users、labs、equipments、reservation，确认外键表名一致。
3. 新库由当前模型建表；旧库先备份、处理 lab → labs 迁移，再核对用户名唯一约束。
4. 写预约请求模型、服务及 API，验证正常路径和冲突路径，补齐回滚。
5. 同步注册、管理员创建和关联删除的错误处理。
6. 完成前端公共弹窗、父页面资源选择、容量/设备重置及删除流程。
7. 整合 JWT UTC 修正、前端会话版本和登录导航处理。
8. 运行 19 项隔离回归测试和前端构建，处理明确失败后再继续。
9. 在真实 MySQL/InnoDB 学习库和浏览器完成第 16.19 节验收。
10. 用新的空目录和空学习库重新走一次，记录遗漏依赖、默认管理员准备、数据初始化和迁移区别。

README 当前补充了学习环境管理员的准备方式；普通注册默认仍为 student，没有内置管理员密码。

最终目标仍是你能独立解释并复现，而不是只把现有目录复制一份。完整端到端验收和从空环境复现完成前，本教程不标记为全部结束。

### 17.19 本轮复习练习

先自己回答，再对照右侧核对。

| 问题 | 核对要点 |
| --- | --- |
| 两个用户都查到“没有预约”，为什么仍不能各自提交？ | 检查和写入之间会交错，需要事务内的协调 |
| 实验室锁能不能自动禁止设备和整间实验室同一时间预约？ | 不能，锁决定操作顺序，冲突条件决定业务互斥 |
| equipment_id 和 lab_id 都存在，是否足以证明归属正确？ | 还要检查 equipment.lab_id == lab.id |
| 用户名模型加了唯一约束，旧数据库是否立即生效？ | 不会，需要实际升级数据库 |
| db.rollback 与 db.rollback() 有什么不同？ | 前者取得方法，后者调用方法 |
| 一个预约已取消，为什么当前用户删除仍被阻止？ | 删除检查保护任意历史归属，不按占用时段规则筛选 |
| authVersion 能不能让另一台设备上的旧 token 失效？ | 不能，它是当前页面内的请求先后标识 |
| 19 项测试通过能否证明 MySQL 并发已验收？ | 不能，当前实际数据库测试是 SQLite，MySQL 错误分支为模拟 |

### 17.20 本章修补代码快照

以下保存本轮相关实现。预约服务、Reservation 模型、公共弹窗及两个预约入口在第 16.20 节；本节保存其他修补文件。完整回归测试另见仓库中的 backend/tests/test_logic_fixes.py，避免把测试结果当作未执行的建议。

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

<details>
<summary><code>frontend/src/utils/auth.js</code></summary>

```js
// 存储token、用户信息, 获取token、用户信息, 删除token、用户信息
const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'
let authVersion = 0

export function getAuthVersion() {
  return authVersion
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
  authVersion++
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  authVersion++
}

export function getUserInfo() {
  const str = localStorage.getItem(USER_KEY)
  if (!str) return null

  try {
    return JSON.parse(str)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setUserInfo(userInfo) {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

// 登出
export function logout() {
  removeToken()
  removeUserInfo()
}
```

</details>

<details>
<summary><code>frontend/src/utils/request.js</code></summary>

```js
import axios from 'axios'
import { getAuthVersion, getToken, logout } from './auth'
import router from '@/router'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000 // 30s
})

const handleUnauthorized = (config, message) => {
  // 旧会话的请求失败，不能使重新登录后的会话失效。
  if (config?._authVersion !== getAuthVersion()) return
  const token = getToken()
  if (token && config.headers?.Authorization !== `Bearer ${token}`) return
  ElMessage.error(message)
  if (token) {
    logout()
    router.replace('/login')
  }
}

// 请求的拦截器的配置
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    config._authVersion = getAuthVersion()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// 返回的拦截器配置
service.interceptors.response.use(
  (res) => {
    const data = res.data
    console.log('response:', res)
    if (data.code === 401) {
      handleUnauthorized(res.config, data.message || '登录已过期，请重新登录')
      return Promise.reject(data)
    }
    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
    }
    return data
  },
  (err) => {
    if (err.response) {
      const httpStatusCode = err.response.status
      if (httpStatusCode === 401) {
        handleUnauthorized(err.config, err.response.data?.message || '登录已过期，请重新登录')
      } else {
        ElMessage.error(err.response.data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络异常，请检查后端服务')
    }
    return Promise.reject(err)
  }
)

export default service
```

</details>

<details>
<summary><code>frontend/src/views/Login.vue</code></summary>

```vue
<template>
  <div class="login-container">
    <div class="login-box">
      <h1 style="font-size: 28px">实验室预约系统</h1>
      <div style="margin-top: 5px; margin-bottom: 30px">基于Agent智能预约系统</div>
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
            还没有账号？请<router-link style="color: var(--el-color-primary)" to="/register"
              >注册</router-link
            >
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'
const { saveLoginData } = useUser()

const formRef = ref()

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
    // { min: 3, max: 20, message: '账号长度在3到20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
    // { min: 6, max: 20, message: '密码长度在6到20个字符之间', trigger: 'blur' }
  ]
}

const form = reactive({
  username: '',
  password: ''
})

const loadingValue = ref(false)

const login = async () => {
  if (loadingValue.value) return
  loadingValue.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const res = await loginApi(form)
    if (res.code === 200) {
      saveLoginData(res.data)
      try {
        const failure = await router.replace('/manager/home')
        if (router.currentRoute.value.path === '/manager/home') {
          ElMessage.success('登录成功')
        } else {
          console.error('登录后跳转首页未完成:', failure)
          ElMessage.error('首页跳转未完成，请重试')
        }
      } catch (error) {
        console.error('登录后加载首页失败:', error)
        ElMessage.error('首页加载失败，请刷新页面后重试')
      }
    }
  } catch {
    // 登录请求失败时由请求拦截器提示错误。
  } finally {
    loadingValue.value = false
  }
}
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

        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="success" :icon="Plus" @click="handleCreate">新增</el-button>
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
              {{ row.status === 1 ? '正常' : '维修' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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
            <el-select v-model="form.lab_id" placeholder="请选择实验室" style="width: 100%">
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import {
  getEquipmentPageList,
  createEquipmentApi,
  updateEquipmentApi,
  deleteEquipmentApi
} from '@/api/equipment'
import { getLabPageList } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  page_size: 10,
  keywords: '',
  lab_id: null
})

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const labOptions = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  lab_id: null,
  name: '',
  description: '',
  img: '',
  spec: '',
  quantity: 1,
  status: 1
})

// 加载分页数据
const load = async () => {
  loading.value = true
  try {
    const res = await getEquipmentPageList(params)
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = {
  lab_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const resetForm = () => {
  Object.assign(form, {
    id: null,
    lab_id: null,
    name: '',
    description: '',
    img: '',
    spec: '',
    quantity: 1,
    status: 1
  })
}

const handleSearch = () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    lab_id: row.lab_id,
    name: row.name,
    description: row.description,
    img: row.img,
    spec: row.spec,
    quantity: row.quantity,
    status: row.status
  })
  dialogVisible.value = true
}

// 删除信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' })
    const res = await deleteEquipmentApi(row.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      await load()
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...equipmentData } = form
    const res = id
      ? await updateEquipmentApi(id, equipmentData)
      : await createEquipmentApi(equipmentData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}

const loadLabs = async () => {
  const res = await getLabPageList({ page: 1, page_size: 100 })
  if (res.code === 200) {
    labOptions.value = res.data?.list
  }
}

onMounted(() => {
  loadLabs()
  load()
})
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
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增</el-button>
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
          <template #default="{ row }">{{ row.open_time }} - {{ row.close_time }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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
            <el-input type="textarea" v-model="form.description" placeholder="请输入简介" />
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
            <el-input type="textarea" v-model="form.location" placeholder="请输入位置" />
          </el-form-item>
          <el-form-item label="容量" prop="capacity">
            <el-input-number v-model="form.capacity" :min="1" :precision="0" placeholder="请输入容量" />
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { getLabPageList, createLabApi, updateLabApi, deleteLabApi } from '@/api/lab'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFileApi } from '@/api/files'

const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})

// 加载分页数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  name: '',
  description: '',
  img: '',
  location: '',
  capacity: 1,
  open_time: '',
  close_time: '',
  status: true
})

const load = async () => {
  loading.value = true
  try {
    const res = await getLabPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = computed(() => ({
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  capacity: [
    { required: true, message: '请输入容量', trigger: 'blur' },
    { type: 'integer', min: 1, message: '容量必须为正整数', trigger: 'change' }
  ]
}))

const resetForm = () => {
  Object.assign(form, {
    id: null,
    name: '',
    description: '',
    img: '',
    location: '',
    capacity: 20,
    open_time: '08:30',
    close_time: '20:30',
    status: true
  })
}

const handleSearch = async () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑信息
const handleEdit = async (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    name: row.name,
    description: row.description,
    img: row.img,
    location: row.location,
    capacity: row.capacity,
    open_time: row.open_time,
    close_time: row.close_time,
    status: row.status
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 删除信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除【${row.name}】？`, '确认删除', { type: 'warning' })
    const res = await deleteLabApi(row.id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      await load()
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
}

// 保存信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, ...labData } = form
    const res = id ? await updateLabApi(id, labData) : await createLabApi(labData)
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

onMounted(() => {
  load()
})

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

  if (!imageTypes.includes(file.type)) {
    ElMessage.error('只能上传图片')
    return false
  }

  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('上传图片大小不能超过2M')
    return false
  }

  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.img = res.data?.url
    }
  } catch {}
}
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
        <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
        <el-button type="primary" :icon="Plus" @click="handleCreate">新增</el-button>
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
            {{ row.role === 'admin' ? '管理员' : '学生' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'">
              {{ row.status ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button type="primary" text bg @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" text bg @click="handleDelete(row)">删除</el-button>
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
      <el-dialog v-model="dialogVisible" :title="form.id ? '编辑' : '新增'" width="450">
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

          <el-form-item v-if="!form.id" label="密码" prop="password" for="user-form-password">
            <el-input
              id="user-form-password"
              type="password"
              show-password
              v-model="form.password"
              placeholder="请输入密码"
            />
          </el-form-item>

          <el-form-item label="名称" prop="name" for="user-form-name">
            <el-input id="user-form-name" v-model="form.name" placeholder="请输入名称" />
          </el-form-item>

          <el-form-item label="角色" prop="role" for="user-form-role">
            <el-select id="user-form-role" v-model="form.role">
              <el-option label="学生" value="student"></el-option>
              <el-option label="管理员" value="admin"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="邮箱" prop="email" for="user-form-email">
            <el-input id="user-form-email" v-model="form.email" placeholder="请输入邮箱" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone" for="user-form-phone">
            <el-input id="user-form-phone" v-model="form.phone" placeholder="请输入手机号" />
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
          <el-button type="primary" native-type="submit" form="user-form" :loading="formLoading">
            确定
          </el-button>
          <el-button :disabled="formLoading" @click="dialogVisible = false">取消</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { getUserPageList, createUserApi, updateUserApi, deleteUserApi } from '@/api/user'
import { Search, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})

// 加载分页数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const formLoading = ref(false)
const form = reactive({
  id: null,
  username: '',
  password: '',
  name: '',
  role: '',
  email: '',
  phone: '',
  avatar: '',
  status: 1
})

const load = async () => {
  loading.value = true
  try {
    const res = await getUserPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const rules = computed(() => ({
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: form.id ? [] : [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 3, max: 10, message: '密码是3-10位', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式错误', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式错误', trigger: 'blur' }]
}))

const resetForm = () => {
  Object.assign(form, {
    id: null,
    username: '',
    password: '',
    name: '',
    role: 'student',
    email: '',
    phone: '',
    avatar: '',
    status: 1
  })
}

const handleSearch = async () => {
  params.page = 1
  load()
}

const handleCreate = async () => {
  resetForm()
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 编辑用户信息
const handleEdit = async (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.role,
    email: row.email,
    phone: row.phone,
    avatar: row.avatar,
    status: row.status
  })
  dialogVisible.value = true
  await nextTick()
  formRef.value?.clearValidate()
}

// 删除用户信息
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除用户【${row.username}】？`, '确认删除', { type: 'warning' })
    const res = await deleteUserApi(row.id)
    if (res.code === 200) {
      ElMessage.success('删除用户成功')
      await load()
    }
  } catch {
    // 取消或关闭确认框无需处理，请求失败时由请求拦截器提示错误。
  }
}

// 保存用户信息
const handleSave = async () => {
  if (formLoading.value || !formRef.value) return
  formLoading.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const { id, username, password, ...userData } = form
    const res = id
      ? await updateUserApi(id, userData)
      : await createUserApi({ username, password, ...userData })
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('操作成功')
      await load()
    }
  } catch {
    // 请求失败时由请求拦截器提示错误，保留表单以便重试。
  } finally {
    formLoading.value = false
  }
}

onMounted(() => {
  load()
})
</script>
```

</details>

---

维护说明：章节按日期保存实现过程。已有问题修正后同步更新进度；正常流程、已知边界、隔离验证和真实浏览器验收分别记录。整个项目的从零复现仍需最终完成一次完整检查。










