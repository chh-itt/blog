<script setup>
// 智能搜索页：混合检索（全文 + 语义 + RRF 融合），创新点2 前台入口
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { blogApi } from '../api'

const route = useRoute()
const router = useRouter()
const q = ref('')
const results = ref([])
const loading = ref(false)
const searched = ref(false)

async function doSearch() {
  const keyword = q.value.trim()
  if (!keyword) {
    ElMessageWarning()
    return
  }
  loading.value = true
  searched.value = true
  try {
    const data = await blogApi.search(keyword)
    results.value = data.results || []
  } finally {
    loading.value = false
  }
}

function ElMessageWarning() {
  // 轻提示避免引入额外依赖
  import('element-plus').then(({ ElMessage }) => ElMessage.warning('请输入搜索关键词'))
}

function onSearchClick() {
  router.replace({ query: { q: q.value } })
  doSearch()
}

watch(
  () => route.query.q,
  (val) => {
    if (val) {
      q.value = String(val)
      doSearch()
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (route.query.q) q.value = String(route.query.q)
})
</script>

<template>
  <div>
    <NavBar />

    <div class="page-container">
      <div class="search-bar">
        <el-input
          v-model="q"
          size="large"
          placeholder="输入问题或关键词，如：Redis 缓存、Django 部署、什么是 RAG？"
          @keyup.enter="onSearchClick"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button type="primary" @click="onSearchClick">
              <el-icon><MagicStick /></el-icon> 智能搜索
            </el-button>
          </template>
        </el-input>
        <div class="search-tip">
          <el-icon color="#7c5cff"><InfoFilled /></el-icon>
          采用「全文检索 + 语义向量检索」混合检索，RRF 融合排序，结果更准确
        </div>
      </div>

      <div v-loading="loading">
        <template v-if="searched">
          <div class="result-count">共找到 {{ results.length }} 篇相关文章</div>

          <el-card
            v-for="r in results"
            :key="r.id"
            class="result-card"
            shadow="hover"
            @click="router.push(`/article/${r.id}`)"
          >
            <div class="result-head">
              <el-tag v-if="r.category" size="small" type="primary" effect="plain">
                {{ r.category.name }}
              </el-tag>
              <h3 class="result-title">{{ r.title }}</h3>
            </div>
            <p v-if="r.ai_summary" class="ai-summary">
              <span class="ai-label">AI摘要</span>{{ r.ai_summary }}
            </p>
            <p v-else class="result-summary">{{ r.summary }}</p>
            <div class="result-meta">
              <span>匹配度评分：<b class="score">{{ r.score }}</b></span>
              <span>{{ r.views }} 阅读</span>
            </div>
          </el-card>

          <el-empty v-if="!loading && !results.length" description="没有找到相关文章，换个关键词试试" />
        </template>
        <el-empty v-else description="输入关键词开始智能搜索" :image-size="120" />
      </div>
    </div>

    <Footer />
  </div>
</template>

<style scoped>
.search-bar {
  margin-bottom: 20px;
}

.search-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.result-count {
  color: #606266;
  font-size: 14px;
  margin-bottom: 14px;
}

.result-card {
  margin-bottom: 14px;
  cursor: pointer;
  transition: transform 0.2s;
}

.result-card:hover {
  transform: translateY(-2px);
}

.result-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-title {
  font-size: 17px;
  color: #1f2d3d;
  margin: 0;
}

.ai-summary {
  background: linear-gradient(90deg, #f5f2ff, #f0f7ff);
  border-left: 3px solid #7c5cff;
  padding: 8px 12px;
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  color: #5a4d8f;
  margin: 8px 0;
}

.ai-label {
  font-weight: 700;
  color: #7c5cff;
  margin-right: 6px;
}

.result-summary {
  color: #606266;
  font-size: 13px;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 12px;
}

.score {
  color: #f56c6c;
}
</style>
