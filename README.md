<p align="center">
  <img src="assets/logo.svg" alt="DeepCareer Logo" width="120" height="120">
</p>

<h1 align="center">DeepCareer</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-17+-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/React-18+-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <strong>AI 驱动的智能职位推荐系统</strong><br>
  基于多维度匹配算法 + 向量语义搜索 + 实时爬虫的一站式求职解决方案
</p>

<p align="center">
  <a href="#-特性">特性</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-技术栈">技术栈</a> •
  <a href="#-项目结构">项目结构</a> •
  <a href="#-api-文档">API 文档</a> •
  <a href="#-贡献">贡献</a>
</p>

---

## ✨ 特性

### 🎯 核心功能

- **智能简历解析** - 支持 PDF/DOCX/图片，自动提取结构化信息
- **多维度职位匹配** - 职位方向、技能、经验、学历、语义相似度 5 维评分
- **实时职位爬取** - 基于 Playwright 的 BOSS 直聘爬虫，支持 Cookie 认证
- **流式匹配响应** - SSE 实时推送匹配结果，边爬边匹配
- **本地向量搜索** - 基于 Sentence-Transformers 的语义匹配，无需云服务

### 🔥 技术亮点

| 特性 | 描述 |
|------|------|
| **双模式提取** | 规则提取（免费快速）+ LLM 提取（高精度）|
| **职位方向匹配** | 18 种职位类别识别，技术/非技术方向区分 |
| **反爬虫策略** | 随机 UA、智能延迟、请求重试、并发控制 |
| **全异步架构** | FastAPI + AsyncIO，高并发低延迟 |
| **本地 Embedding** | 无需 OpenAI API，支持离线运行 |

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| **Python** | 3.11+ | 推荐 3.11.x |
| **Node.js** | 18+ | 推荐 18.x LTS |
| **PostgreSQL** | 17+ | 需要 pgvector 扩展 |
| **Redis** | 7+ | 可选，用于缓存 |

---

### 方式一：Docker 一键部署（推荐新手）

最简单的方式，无需手动安装数据库。

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/DeepCareer.git
cd DeepCareer

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（可选）和 BOSS_COOKIE

# 3. 一键启动所有服务
docker-compose up -d

# 4. 查看服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f app
```

启动后访问：
- 前端界面：http://localhost:3000
- API 文档：http://localhost:8001/docs

```bash
# 停止服务
docker-compose down

# 停止并清除数据
docker-compose down -v
```

---

### 方式二：本地开发环境（完整安装）

适合需要修改代码的开发者。

#### Step 1: 安装 PostgreSQL

**macOS (Homebrew):**
```bash
# 安装 PostgreSQL
brew install postgresql@17

# 启动服务
brew services start postgresql@17

# 安装 pgvector 扩展
brew install pgvector

# 创建数据库和用户
psql postgres <<EOF
CREATE USER admin WITH PASSWORD '123456';
CREATE DATABASE deepcareer OWNER admin;
\c deepcareer
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

**Ubuntu/Debian:**
```bash
# 添加 PostgreSQL 官方源
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# 安装 PostgreSQL 和 pgvector
sudo apt install postgresql-17 postgresql-17-pgvector

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql <<EOF
CREATE USER admin WITH PASSWORD '123456';
CREATE DATABASE deepcareer OWNER admin;
\c deepcareer
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

**Windows:**
1. 下载 [PostgreSQL 17 安装包](https://www.postgresql.org/download/windows/)
2. 安装时记住设置的密码
3. 使用 pgAdmin 创建数据库 `deepcareer`
4. 执行 SQL: `CREATE EXTENSION IF NOT EXISTS vector;`

#### Step 2: 安装 Redis（可选）

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**Windows:**
下载 [Redis for Windows](https://github.com/tporadowski/redis/releases)

#### Step 3: 安装 Python 环境

```bash
# 推荐使用 pyenv 管理 Python 版本
# macOS
brew install pyenv
pyenv install 3.11.7
pyenv global 3.11.7

# 或直接使用系统 Python（需要 3.11+）
python3 --version  # 确认版本
```

#### Step 4: 安装 Node.js

```bash
# 推荐使用 nvm 管理 Node 版本
# macOS/Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 或直接下载安装
# https://nodejs.org/
```

#### Step 5: 克隆并配置项目

```bash
# 克隆项目
git clone https://github.com/yourusername/DeepCareer.git
cd DeepCareer

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（爬虫需要）
playwright install chromium

# 安装 CLI 工具
pip install -e .

# 配置环境变量
cp .env.example .env
```

#### Step 6: 编辑 .env 配置

```bash
# 编辑 .env 文件
nano .env  # 或用其他编辑器
```

必须配置的项：
```env
# 数据库配置（与 Step 1 创建的一致）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deepcareer
POSTGRES_USER=admin
POSTGRES_PASSWORD=123456

# OpenAI 配置（可选，不配置则只能用规则提取）
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 爬虫 Cookie（从浏览器复制，用于爬取职位）
BOSS_COOKIE=your_cookie_here
```

#### Step 7: 初始化数据库

```bash
# 首次启动会自动创建表结构
# 或手动执行初始化脚本
psql -U admin -d deepcareer -f database/init_db.sql
```

#### Step 8: 启动服务

```bash
# 方式1: 使用 CLI 一键启动（推荐）
deepcareer dev

# 方式2: 分别启动
# 终端1 - 后端
deepcareer serve -p 8001 -r

# 终端2 - 前端
cd frontend
npm install
npm run dev
```

#### Step 9: 验证安装

```bash
# 检查后端健康状态
curl http://localhost:8001/health

# 检查数据库连接
curl http://localhost:8001/api/v2/jobs

# 查看支持的城市
deepcareer cities
```

---

### 获取 BOSS 直聘 Cookie

爬虫需要登录态 Cookie 才能获取完整职位信息：

1. 打开浏览器，访问 [BOSS 直聘](https://www.zhipin.com)
2. 登录你的账号
3. 按 F12 打开开发者工具
4. 切换到 Network 标签
5. 刷新页面，点击任意请求
6. 在 Headers 中找到 `Cookie` 字段
7. 复制整个 Cookie 值到 `.env` 文件的 `BOSS_COOKIE`

---

### 常见问题

**Q: PostgreSQL 连接失败？**
```bash
# 检查服务是否运行
pg_isready -h localhost -p 5432

# 检查用户权限
psql -U admin -d deepcareer -c "SELECT 1;"
```

**Q: pgvector 扩展安装失败？**
```bash
# 确认扩展已安装
psql -U admin -d deepcareer -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 如果没有，手动创建
psql -U admin -d deepcareer -c "CREATE EXTENSION vector;"
```

**Q: Playwright 浏览器下载失败？**
```bash
# 使用国内镜像
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
```

**Q: 前端启动报错？**
```bash
# 清除缓存重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```
- **API 文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/health

---

## 🐳 Docker 部署

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

---

## 🛠 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **FastAPI** | 高性能异步 Web 框架 |
| **SQLAlchemy** | 异步 ORM |
| **PostgreSQL + pgvector** | 关系数据库 + 向量搜索 |
| **Playwright** | 浏览器自动化爬虫 |
| **Sentence-Transformers** | 本地 Embedding 模型 |
| **Pydantic** | 数据验证 |
| **Redis** | 缓存（可选）|

### 前端

| 技术 | 用途 |
|------|------|
| **React 18** | UI 框架 |
| **Vite** | 构建工具 |
| **Ant Design** | 组件库 |
| **Axios** | HTTP 客户端 |

---

## 📁 项目结构

```
DeepCareer/
├── backend/                    # 后端代码
│   ├── api/                    # API 路由
│   │   ├── resume_v2.py        # 简历管理 API
│   │   ├── job_v2.py           # 职位管理 API
│   │   ├── smart_match.py      # 智能匹配 API
│   │   └── crawler.py          # 爬虫 API
│   ├── models/                 # 数据模型
│   │   ├── resume_v2.py        # 简历模型
│   │   └── job_v2.py           # 职位模型
│   ├── services/               # 业务服务
│   │   ├── extractor_service.py    # 信息提取
│   │   ├── matcher_service.py      # 匹配算法
│   │   └── embedding_service.py    # 向量服务
│   ├── crawlers/               # 爬虫模块
│   │   └── boss_web_crawler_playwright.py
│   ├── config.py               # 配置管理
│   └── main.py                 # 应用入口
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   └── api/                # API 封装
│   └── package.json
├── database/                   # 数据库脚本
├── docker-compose.yml          # Docker 编排
├── requirements.txt            # Python 依赖
└── README.md
```

---

## 📖 API 文档

### 简历管理

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v2/resumes/upload` | 上传简历 |
| GET | `/api/v2/resumes` | 获取简历列表 |
| GET | `/api/v2/resumes/{id}` | 获取简历详情 |
| POST | `/api/v2/resumes/{id}/extract-with-llm` | AI 重新解析 |

### 职位管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v2/jobs` | 获取职位列表（支持搜索筛选）|
| GET | `/api/v2/jobs/{id}` | 获取职位详情 |
| POST | `/api/v2/jobs` | 创建职位 |

### 智能匹配

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v2/smart-match/stream` | 流式智能匹配（SSE）|
| POST | `/api/v2/smart-match` | 普通智能匹配 |

### 爬虫

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v2/crawler/boss` | 爬取 BOSS 直聘职位 |

---

## ⚙️ 配置说明

### 核心配置 (.env)

```env
# OpenAI 配置（可选，用于 LLM 提取）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 本地 Embedding（推荐）
USE_LOCAL_EMBEDDING=true
LOCAL_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# 数据库
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deepcareer
POSTGRES_USER=admin
POSTGRES_PASSWORD=123456

# 应用
APP_PORT=8001
DEBUG=true

# 爬虫 Cookie（从浏览器获取）
BOSS_COOKIE=lastCity=101280600; ...
```

### 匹配权重配置

```python
# backend/services/matcher_service.py
weights = {
    'position': 0.30,   # 职位方向 30%
    'skills': 0.25,     # 技能匹配 25%
    'experience': 0.20, # 经验匹配 20%
    'education': 0.15,  # 学历匹配 15%
    'semantic': 0.10    # 语义相似度 10%
}
```

---

## 🔧 开发指南

### CLI 命令行工具

DeepCareer 提供强大的命令行工具：

```bash
# 安装
pip install -e .

# 查看帮助
deepcareer --help
```

| 命令 | 说明 | 示例 |
|------|------|------|
| `crawl` | 爬取 BOSS 直聘职位 | `deepcareer crawl -c 深圳 -k Python -n 20` |
| `serve` | 启动后端 API 服务 | `deepcareer serve -p 8001 -r` |
| `dev` | 同时启动前后端 | `deepcareer dev` |
| `frontend` | 启动前端服务 | `deepcareer frontend -i` |
| `cities` | 列出支持的城市 | `deepcareer cities` |

详细文档请参考 [TECHNICAL.md](TECHNICAL.md#cli-命令行工具)

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行测试
pytest tests/
```

### 代码风格

```bash
# 格式化代码
black backend/
isort backend/

# 类型检查
mypy backend/
```

### 日志查看

```bash
# 实时查看日志
tail -f logs/deepcareer.log
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [Playwright](https://playwright.dev/)
- [Sentence-Transformers](https://www.sbert.net/)
- [Ant Design](https://ant.design/)

---

<p align="center">
  <strong>DeepCareer</strong> - 让 AI 帮你找到理想工作 🚀
</p>
