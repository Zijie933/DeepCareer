<p align="center">
  <img src="assets/logo.svg" alt="DeepCareer Logo" width="120" height="120">
</p>

<h1 align="center">DeepCareer</h1>

<p align="center">
  <a href="./README.md">简体中文</a> | <a href="./README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-17+-blue.svg" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/React-18+-61DAFB.svg" alt="React">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
  <strong>AI-Powered Intelligent Job Recommendation System</strong><br>
  An all-in-one job-seeking solution based on multi-dimensional matching algorithms + vector semantic search + real-time crawlers
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-project-structure">Project Structure</a> •
  <a href="#-api-documentation">API Docs</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## ✨ Features

### 🎯 Core Features

- **Smart Resume Parsing** - Supports PDF/DOCX/Images, automatically extracts structured information
- **Multi-dimensional Job Matching** - 5-dimensional scoring: job direction, skills, experience, education, semantic similarity
- **Real-time Job Crawling** - Playwright-based job crawler with Cookie authentication
- **Streaming Match Response** - SSE real-time push of matching results, crawl and match simultaneously
- **Local Vector Search** - Sentence-Transformers based semantic matching, no cloud services needed

### 🔥 Technical Highlights

| Feature | Description |
|---------|-------------|
| **Dual-mode Extraction** | Rule-based (free & fast) + LLM extraction (high precision) |
| **Job Direction Matching** | 18 job categories recognition, tech/non-tech distinction |
| **Anti-crawler Strategy** | Random UA, smart delays, request retry, concurrency control |
| **Fully Async Architecture** | FastAPI + AsyncIO, high concurrency & low latency |
| **Local Embedding** | No OpenAI API needed, supports offline operation |

---

## 🚀 Quick Start

### Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| **Python** | 3.11+ | Recommended 3.11.x |
| **Node.js** | 18+ | Recommended 18.x LTS |
| **PostgreSQL** | 17+ | Requires pgvector extension |
| **Redis** | 7+ | Optional, for caching |

---

### Option 1: Docker One-Click Deployment (Recommended for Beginners)

The simplest way, no manual database installation needed.

```bash
# 1. Clone the project
git clone https://github.com/Zijie933/DeepCareer.git
cd DeepCareer

# 2. Configure environment variables
cp .env.example .env
# Edit .env, fill in OPENAI_API_KEY (optional) and BOSS_COOKIE

# 3. Start all services with one command
docker-compose up -d

# 4. Check service status
docker-compose ps

# 5. View logs
docker-compose logs -f app
```

After startup, access:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8001/docs

```bash
# Stop services
docker-compose down

# Stop and clear data
docker-compose down -v
```

---

### Option 2: Local Development Environment (Full Installation)

Suitable for developers who need to modify code.

#### Step 1: Install PostgreSQL

**macOS (Homebrew):**
```bash
# Install PostgreSQL
brew install postgresql@17

# Start service
brew services start postgresql@17

# Install pgvector extension
brew install pgvector

# Create database and user
psql postgres <<EOF
CREATE USER admin WITH PASSWORD '123456';
CREATE DATABASE deepcareer OWNER admin;
\c deepcareer
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

**Ubuntu/Debian:**
```bash
# Add PostgreSQL official repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update

# Install PostgreSQL and pgvector
sudo apt install postgresql-17 postgresql-17-pgvector

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE USER admin WITH PASSWORD '123456';
CREATE DATABASE deepcareer OWNER admin;
\c deepcareer
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

**Windows:**
1. Download [PostgreSQL 17 installer](https://www.postgresql.org/download/windows/)
2. Remember the password set during installation
3. Use pgAdmin to create database `deepcareer`
4. Execute SQL: `CREATE EXTENSION IF NOT EXISTS vector;`

#### Step 2: Install Redis (Optional)

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
Download [Redis for Windows](https://github.com/tporadowski/redis/releases)

#### Step 3: Install Python Environment

```bash
# Recommended: use pyenv to manage Python versions
# macOS
brew install pyenv
pyenv install 3.11.7
pyenv global 3.11.7

# Or use system Python directly (requires 3.11+)
python3 --version  # Verify version
```

#### Step 4: Install Node.js

```bash
# Recommended: use nvm to manage Node versions
# macOS/Linux
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Or download directly
# https://nodejs.org/
```

#### Step 5: Clone and Configure Project

```bash
# Clone project
git clone https://github.com/yourusername/DeepCareer.git
cd DeepCareer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser (required for crawler)
playwright install chromium

# Install CLI tool
pip install -e .

# Configure environment variables
cp .env.example .env
```

#### Step 6: Edit .env Configuration

```bash
# Edit .env file
nano .env  # Or use another editor
```

Required configurations:
```env
# Database configuration (must match Step 1)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deepcareer
POSTGRES_USER=admin
POSTGRES_PASSWORD=123456

# OpenAI configuration (optional, for LLM extraction)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Crawler Cookie (copy from browser, for job crawling)
BOSS_COOKIE=your_cookie_here
```

#### Step 7: Initialize Database

```bash
# First startup will auto-create table structure
# Or manually execute initialization script
psql -U admin -d deepcareer -f database/init_db.sql
```

#### Step 8: Start Services

```bash
# Method 1: One-click start with CLI (recommended)
deepcareer dev

# Method 2: Start separately
# Terminal 1 - Backend
deepcareer serve -p 8001 -r

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

#### Step 9: Verify Installation

```bash
# Check backend health status
curl http://localhost:8001/health

# Check database connection
curl http://localhost:8001/api/v2/jobs

# View supported cities
deepcareer cities
```

---

### Getting BOSS Zhipin Cookie

The crawler needs login Cookie to get complete job information:

1. Open browser, visit [BOSS Zhipin](https://www.zhipin.com)
2. Log in to your account
3. Press F12 to open Developer Tools
4. Switch to Network tab
5. Refresh page, click any request
6. Find `Cookie` field in Headers
7. Copy the entire Cookie value to `BOSS_COOKIE` in `.env` file

---

### Common Issues

**Q: PostgreSQL connection failed?**
```bash
# Check if service is running
pg_isready -h localhost -p 5432

# Check user permissions
psql -U admin -d deepcareer -c "SELECT 1;"
```

**Q: pgvector extension installation failed?**
```bash
# Confirm extension is installed
psql -U admin -d deepcareer -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# If not, manually create
psql -U admin -d deepcareer -c "CREATE EXTENSION vector;"
```

**Q: Playwright browser download failed?**
```bash
# Use mirror (for China)
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
```

**Q: Frontend startup error?**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

---

## 🐳 Docker Deployment

```bash
# Start all services with one command
docker-compose up -d

# View logs
docker-compose logs -f app
```

---

## 🛠 Tech Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async web framework |
| **SQLAlchemy** | Async ORM |
| **PostgreSQL + pgvector** | Relational database + vector search |
| **Playwright** | Browser automation crawler |
| **Sentence-Transformers** | Local Embedding model |
| **Pydantic** | Data validation |
| **Redis** | Cache (optional) |

### Frontend

| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **Vite** | Build tool |
| **Ant Design** | Component library |
| **Axios** | HTTP client |

---

## 📁 Project Structure

```
DeepCareer/
├── backend/                    # Backend code
│   ├── api/                    # API routes
│   │   ├── resume_v2.py        # Resume management API
│   │   ├── job_v2.py           # Job management API
│   │   ├── smart_match.py      # Smart matching API
│   │   └── crawler.py          # Crawler API
│   ├── models/                 # Data models
│   │   ├── resume_v2.py        # Resume model
│   │   └── job_v2.py           # Job model
│   ├── services/               # Business services
│   │   ├── extractor_service.py    # Information extraction
│   │   ├── matcher_service.py      # Matching algorithm
│   │   └── embedding_service.py    # Vector service
│   ├── crawlers/               # Crawler module
│   │   └── boss_web_crawler_playwright.py
│   ├── config.py               # Configuration management
│   └── main.py                 # Application entry
├── frontend/                   # Frontend code
│   ├── src/
│   │   ├── pages/              # Page components
│   │   ├── components/         # Common components
│   │   └── api/                # API wrappers
│   └── package.json
├── database/                   # Database scripts
├── docker-compose.yml          # Docker orchestration
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 📖 API Documentation

### Resume Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/resumes/upload` | Upload resume |
| GET | `/api/v2/resumes` | Get resume list |
| GET | `/api/v2/resumes/{id}` | Get resume details |
| POST | `/api/v2/resumes/{id}/extract-with-llm` | AI re-parse |

### Job Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v2/jobs` | Get job list (with search & filter) |
| GET | `/api/v2/jobs/{id}` | Get job details |
| POST | `/api/v2/jobs` | Create job |

### Smart Matching

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/smart-match/stream` | Streaming smart match (SSE) |
| POST | `/api/v2/smart-match` | Regular smart match |

### Crawler

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v2/crawler/boss` | Crawl BOSS Zhipin jobs |

---

## ⚙️ Configuration

### Core Configuration (.env)

```env
# OpenAI configuration (optional, for LLM extraction)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# Local Embedding (recommended)
USE_LOCAL_EMBEDDING=true
LOCAL_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deepcareer
POSTGRES_USER=admin
POSTGRES_PASSWORD=123456

# Application
APP_PORT=8001
DEBUG=true

# Crawler Cookie (get from browser)
BOSS_COOKIE=lastCity=101280600; ...
```

### Matching Weight Configuration

```python
# backend/services/matcher_service.py
weights = {
    'position': 0.30,   # Job direction 30%
    'skills': 0.25,     # Skill matching 25%
    'experience': 0.20, # Experience matching 20%
    'education': 0.15,  # Education matching 15%
    'semantic': 0.10    # Semantic similarity 10%
}
```

---

## 🔧 Development Guide

### CLI Tool

DeepCareer provides a powerful command-line tool:

```bash
# Install
pip install -e .

# View help
deepcareer --help
```

| Command | Description | Example |
|---------|-------------|---------|
| `crawl` | Crawl BOSS Zhipin jobs | `deepcareer crawl -c 深圳 -k Python -n 20` |
| `serve` | Start backend API service | `deepcareer serve -p 8001 -r` |
| `dev` | Start both frontend and backend | `deepcareer dev` |
| `frontend` | Start frontend service | `deepcareer frontend -i` |
| `cities` | List supported cities | `deepcareer cities` |

For detailed documentation, see [TECHNICAL_EN.md](TECHNICAL_EN.md#cli-command-line-tool)

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Style

```bash
# Format code
black backend/
isort backend/

# Type checking
mypy backend/
```

### Log Viewing

```bash
# Real-time log viewing
tail -f logs/deepcareer.log
```

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Submit Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/)
- [Playwright](https://playwright.dev/)
- [Sentence-Transformers](https://www.sbert.net/)
- [Ant Design](https://ant.design/)

---

<p align="center">
  <strong>DeepCareer</strong> - Let AI help you find your dream job 🚀
</p>
