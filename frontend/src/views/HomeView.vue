<script setup>
// 首页：文章瀑布流 + 分类侧栏 + 标签云 + AI 摘要展示
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { blogApi } from '../api'

const router = useRouter()
const articles = ref([])
const categories = ref([])
const tags = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const activeCategory = ref('')
const keyword = ref('')

async function loadArticles() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (activeCategory.value) params.category = activeCategory.value
    if (keyword.value) params.search = keyword.value
    const data = await blogApi.listArticles(params)
    articles.value = data.results || []
    total.value = data.count || 0
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  categories.value = await blogApi.categories()
  tags.value = await blogApi.tags()
}

function onPageChange(p) {
  page.value = p
  loadArticles()
}

function selectCategory(catId) {
  activeCategory.value = activeCategory.value === catId ? '' : catId
  page.value = 1
  loadArticles()
}

function searchTag(tag) {
  router.push({ path: '/search', query: { q: tag.name } })
}

onMounted(() => {
  loadArticles()
  loadMeta()
})
</script>

<template>
  <div>
    <NavBar />

    <!-- 顶部横幅 -->
    <section class="hero">
      <h1>智博空间</h1>
      <p>记录技术成长，分享开发经验 —— AI 加持的智能博客</p>
      <el-input
        v-model="keyword"
        placeholder="输入关键词搜索文章（支持全文+语义混合检索）"
        class="hero-search"
        @keyup.enter="page = 1; loadArticles()"
      >
        <template #append>
          <el-button @click="page = 1; loadArticles()">
            <el-icon><Search /></el-icon>搜索
          </el-button>
        </template>
      </el-input>
    </section>

    <div class="page-container home-layout">
      <!-- 左侧：分类与标签 -->
      <aside class="sidebar">
        <el-card>
          <template #header><b>文章分类</b></template>
          <div class="cat-list">
            <div
              class="cat-item"
              :class="{ active: !activeCategory }"
              @click="selectCategory('')"
            >
              全部文章
            </div>
            <div
              v-for="cat in categories"
              :key="cat.id"
              class="cat-item"
              :class="{ active: activeCategory === cat.id }"
              @click="selectCategory(cat.id)"
            >
              {{ cat.name }}
              <span class="count-badge">{{ cat.children?.length || 0 }} 子类</span>
            </div>
          </div>
        </el-card>

        <el-card class="tag-card">
          <template #header><b>热门标签</b></template>
          <div class="tag-cloud">
            <el-tag
              v-for="tag in tags.slice(0, 12)"
              :key="tag.id"
              class="tag-item"
              type="info"
              effect="plain"
              @click="searchTag(tag)"
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </el-card>
      </aside>

      <!-- 右侧：文章列表 -->
      <main class="content">
        <div v-loading="loading">
          <el-card
            v-for="art in articles"
            :key="art.id"
            class="article-card"
            shadow="hover"
            @click="router.push(`/article/${art.id}`)"
          >
            <div class="article-head">
              <el-tag v-if="art.is_top" type="danger" size="small">置顶</el-tag>
              <el-tag v-if="art.category" size="small" type="primary" effect="plain">
                {{ art.category.name }}
              </el-tag>
              <h3 class="article-title">{{ art.title }}</h3>
            </div>

            <!-- AI 摘要（创新点1） -->
            <p v-if="art.ai_summary" class="ai-summary">
              <el-icon color="#7c5cff"><MagicStick /></el-icon>
              <span class="ai-label">AI摘要</span>
              {{ art.ai_summary }}
            </p>
            <p v-else class="article-summary">{{ art.summary }}</p>

            <div class="article-tags">
              <el-tag
                v-for="t in (art.ai_tags && art.ai_tags.length ? art.ai_tags : [])"
                :key="t"
                size="small"
                type="warning"
                effect="light"
                class="tag-item"
              >
                {{ t }}
              </el-tag>
            </div>

            <div class="article-meta">
              <span><el-icon><User /></el-icon> {{ art.author?.nickname || art.author?.username }}</span>
              <span><el-icon><Calendar /></el-icon> {{ (art.published_at || '').slice(0, 10) }}</span>
              <span><el-icon><View /></el-icon> {{ art.views }}</span>
              <span><el-icon><Star /></el-icon> {{ art.likes }}</span>
            </div>
          </el-card>

          <el-empty v-if="!loading && !articles.length" description="暂无文章" />

          <div class="pagination-wrap">
            <el-pagination
              background
              layout="prev, pager, next"
              :total="total"
              :page-size="pageSize"
              :current-page="page"
              @current-change="onPageChange"
            />
          </div>
        </div>
      </main>
    </div>

    <Footer />
  </div>
</template>

<style scoped>
.hero {
  background: linear-gradient(135deg, #eaf3ff 0%, #f3efff 100%);
  text-align: center;
  padding: 48px 16px 40px;
}

.hero h1 {
  font-size: 34px;
  margin-bottom: 12px;
  background: linear-gradient(90deg, #409eff, #7c5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero p {
  color: #606266;
  margin-bottom: 24px;
}

.hero-search {
  max-width: 560px;
  margin: 0 auto;
}

.home-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 20px;
  align-items: start;
}

.sidebar {
  position: sticky;
  top: 76px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cat-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: #606266;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.cat-item:hover {
  background: #f0f7ff;
  color: #409eff;
}

.cat-item.active {
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.count-badge {
  font-size: 11px;
  color: #c0c4cc;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  cursor: pointer;
}

.article-card {
  margin-bottom: 16px;
  cursor: pointer;
  transition: transform 0.2s;
}

.article-card:hover {
  transform: translateY(-2px);
}

.article-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.article-title {
  font-size: 18px;
  margin: 0;
  color: #1f2d3d;
}

.ai-summary {
  background: linear-gradient(90deg, #f5f2ff, #f0f7ff);
  border-left: 3px solid #7c5cff;
  padding: 10px 12px;
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  color: #5a4d8f;
  margin: 8px 0;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.ai-label {
  font-weight: 700;
  font-size: 12px;
  color: #7c5cff;
  white-space: nowrap;
}

.article-summary {
  color: #606266;
  font-size: 14px;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 6px 0;
}

.article-meta {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 13px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.article-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

@media (max-width: 900px) {
  .home-layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    position: static;
  }
}
</style>
