# Zhibo Space

个人博客系统，Django + Vue 3，也是我论文的配套实现：论文里设计的混合检索与降级策略，在这套代码里有完整落地。博客之外，项目围绕内容做了一组 AI 能力——站内问答（RAG）、写作助手、自动摘要与标签。

## 功能

博客本体：

- 文章：Markdown 写作与渲染、树形分类、标签、置顶、浏览量与点赞
- 评论：楼中楼回复，可按文章开关，支持审核后展示
- 用户：注册登录（JWT），作者与普通读者权限分离
- 后台：Dashboard 流量统计（ECharts）、文章/评论管理、站点参数配置

AI 部分（需配置模型 API Key，不配不影响博客本体运行）：

- RAG 问答：默认自动召回 Top-5 篇已发布文章作为上下文，也可手动指定参考文章；检索失败时降级为普通问答
- AI 写作助手：按主题生成草稿，一键保存为文章到后台
- 自动摘要 / 自动标签：文章发布后由 Celery 异步生成，写回文章字段
- 服务层另实现了评论 AI 审核与自动分类（含单元测试），尚未接入业务流程

## 技术栈

| | |
|---|---|
| 后端 | Django 6、Django REST Framework、SimpleJWT、django-mptt |
| 数据库 | PostgreSQL + pgvector（1024 维向量） |
| 缓存 / 队列 | Redis、django-redis、Celery |
| 检索 | jieba 分词、PostgreSQL 全文检索、pgvector 向量检索、RRF 融合排序 |
| 模型服务 | DeepSeek（生成）、SiliconFlow bge-m3（向量） |
| 前端 | Vue 3、Vite、Element Plus、Pinia、ECharts、markdown-it |

## 几处实现细节

**混合检索**：查询先经 jieba 分词，同时跑 PostgreSQL FTS 和 pgvector 向量检索，各取 2×limit 条候选，用 Reciprocal Rank Fusion 合并排序。向量这条路失败时整体降级为纯全文检索，不影响搜索可用性。

**AI 调用缓存**：每次大模型调用先对输入做哈希查 `AICache` 表，命中直接返回，避免重复计费和等待。

**异步生成**：文章保存触发 `generate_article_ai.delay()`，摘要与标签由 Celery worker 生成，不阻塞发布请求。

**渲染安全**：Markdown 渲染后经 bleach 白名单过滤再入库。

## 本地运行

环境要求：Python 3.12+（本地用 3.14）、Node.js 20.19+（本地用 26）、PostgreSQL（需安装 pgvector 扩展）、Redis。

1. 建库并启用向量扩展，准备环境配置：

```sql
CREATE DATABASE blog;
\c blog
CREATE EXTENSION vector;
```

```bash
cd backend
copy .env.example .env    # 填数据库/Redis 密码；要用 AI 功能再填两个 API Key
```

2. 后端（迁移必须在 pgvector 扩启用之后执行）：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8100
```

3. 前端（另开终端）：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 ，后端接口在 http://127.0.0.1:8100 。

Celery worker（自动摘要/标签需要，另开终端）：

```bash
.venv\Scripts\python -m celery -A config worker --pool=solo --loglevel=info
```

Windows 下也可以用根目录的 `start_all.bat` 一次拉起 Redis、Django、Celery、Vite，`stop_all.bat` 一键停止。脚本里的 Redis 路径写的是我本机的位置，用时需要改。

## 项目结构

```
blog-project/
├── backend/                 # Django
│   ├── config/              # 全局配置、根路由
│   ├── blog/                # 文章、分类、标签、评论、混合检索
│   ├── aigc/                # AI 功能：生成、缓存、Celery 任务
│   ├── users/               # 用户模型与认证
│   ├── stats/               # 访问统计
│   └── sysconf/             # 站点配置
├── frontend/                # Vue 3 + Vite
│   └── src/
│       ├── views/           # 前台页面与 admin 后台
│       ├── stores/          # Pinia 状态
│       └── router/
├── start_all.bat
└── stop_all.bat
```

## 说明

- `backend/.env` 含密码和 Key，不进版本库，模板见 `backend/.env.example`
- 启动脚本里带演示账号，仅限本地演示；正式部署请改掉并更换 `DJANGO_SECRET_KEY`
- 未配置 Key 时 AI 功能不可用，博客其余功能不受影响
