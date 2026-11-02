<script setup>
// AI 智能内容服务页（创新点1）：自动摘要 / 自动标签 / 写作助手 / RAG问答 / 评论审核
// 摘要/标签卡片 =「选择我的文章 → 生成 → 预览 → 手动保存到文章」；
// 写新文章时用后台编辑页的 AI 摘要/标签/写作按钮。
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { aigcApi, blogApi } from '../api'

const router = useRouter()

// ---------- 我的文章（选择器数据） ----------
const myArticles = ref([])
const articleLoading = ref(false)

async function loadArticles() {
  articleLoading.value = true
  try {
    myArticles.value = await blogApi.myArticles()
  } finally {
    articleLoading.value = false
  }
}

// 选择器显示：标题 + 是否已有 AI 字段
function optionLabel(art) {
  const marks = []
  if (art.ai_summary) marks.push('已摘要')
  if (art.ai_tags && art.ai_tags.length) marks.push('已标签')
  const mark = marks.length ? ` [${marks.join('/')}]` : ''
  const title = art.title.length > 26 ? art.title.slice(0, 26) + '…' : art.title
  return `${title}${mark}`
}

// ---------- AI 自动摘要 ----------
const summaryArticleId = ref(null)
const summaryResult = ref('')
const summaryCache = ref(false)
const summaryLoading = ref(false)
const summarySaving = ref(false)
const summarySaved = ref(false)

async function doSummary() {
  if (!summaryArticleId.value) return ElMessage.warning('请先选择文章')
  summaryLoading.value = true
  try {
    const art = await blogApi.getArticle(summaryArticleId.value)
    if (!(art.content_md || '').trim()) return ElMessage.warning('该文章正文为空，无法生成摘要')
    const data = await aigcApi.summary({ text: art.content_md })
    summaryResult.value = data.result
    summaryCache.value = data.from_cache
    summarySaved.value = false
  } finally {
    summaryLoading.value = false
  }
}

async function saveSummary() {
  if (!summaryArticleId.value || !summaryResult.value) return
  const art = myArticles.value.find((a) => a.id === summaryArticleId.value)
  if (art?.ai_summary) {
    try {
      await ElMessageBox.confirm('该文章已有 AI 摘要，保存将覆盖旧摘要。是否继续？', '覆盖确认', { type: 'warning' })
    } catch {
      return // 用户取消
    }
  }
  summarySaving.value = true
  try {
    await blogApi.updateArticle(summaryArticleId.value, { ai_summary: summaryResult.value })
    summarySaved.value = true
    ElMessage.success('AI 摘要已保存到文章')
    await loadArticles()
  } finally {
    summarySaving.value = false
  }
}

// ---------- AI 自动标签 ----------
const tagsArticleId = ref(null)
const tagsResult = ref([])
const tagsCache = ref(false)
const tagsLoading = ref(false)
const tagsSaving = ref(false)
const tagsSaved = ref(false)

async function doTags() {
  if (!tagsArticleId.value) return ElMessage.warning('请先选择文章')
  tagsLoading.value = true
  try {
    const art = await blogApi.getArticle(tagsArticleId.value)
    const data = await aigcApi.tags({ title: art.title, content: art.content_md })
    tagsResult.value = Array.isArray(data.result) ? data.result : []
    tagsCache.value = data.from_cache
    tagsSaved.value = false
  } finally {
    tagsLoading.value = false
  }
}

async function saveTags() {
  if (!tagsArticleId.value || !tagsResult.value.length) return
  const art = myArticles.value.find((a) => a.id === tagsArticleId.value)
  if (art?.ai_tags?.length) {
    try {
      await ElMessageBox.confirm('该文章已有 AI 标签，应用将覆盖旧标签。是否继续？', '覆盖确认', { type: 'warning' })
    } catch {
      return // 用户取消
    }
  }
  tagsSaving.value = true
  try {
    await blogApi.updateArticle(tagsArticleId.value, { ai_tags: tagsResult.value })
    tagsSaved.value = true
    ElMessage.success('AI 标签已应用到文章（ai_tags 建议标签）')
    await loadArticles()
  } finally {
    tagsSaving.value = false
  }
}

// ---------- 写作助手 ----------
const writerPrompt = ref('')
const writerResult = ref('')
const writerCache = ref(false)
const writerLoading = ref(false)

async function doWriter() {
  if (!writerPrompt.value.trim()) return ElMessage.warning('请输入写作主题')
  writerLoading.value = true
  try {
    const data = await aigcApi.writer({ prompt: writerPrompt.value })
    writerResult.value = data.result
    writerCache.value = data.from_cache
  } finally {
    writerLoading.value = false
  }
}

// 生成结果一键「保存为草稿文章」：暂存到 sessionStorage 后跳转后台编辑页
function saveAsDraft() {
  if (!writerResult.value) return ElMessage.warning('请先生成写作内容')
  const firstLine = writerResult.value.split('\n').find((l) => l.trim().startsWith('#'))?.replace(/^#+\s*/, '').trim()
  sessionStorage.setItem(
    'ai_draft',
    JSON.stringify({
      title: firstLine || writerPrompt.value.slice(0, 30),
      content_md: writerResult.value,
    })
  )
  ElMessage.success('已暂存草稿，跳转到文章编辑页…')
  router.push('/admin/article-edit')
}

// ---------- RAG 问答 ----------
const qaQuestion = ref('')
const qaContext = ref('')
const qaResult = ref('')
const qaCache = ref(false)
const qaLoading = ref(false)

async function doQa() {
  if (!qaQuestion.value.trim()) return ElMessage.warning('请输入问题')
  qaLoading.value = true
  try {
    const data = await aigcApi.qa({ question: qaQuestion.value, context: qaContext.value })
    qaResult.value = data.result
    qaCache.value = data.from_cache
  } finally {
    qaLoading.value = false
  }
}

// ---------- 评论审核 ----------
const moderateText = ref('')
const moderateResult = ref(null)
const moderateCache = ref(false)
const moderateLoading = ref(false)

async function doModerate() {
  if (!moderateText.value.trim()) return ElMessage.warning('请输入评论内容')
  moderateLoading.value = true
  try {
    const data = await aigcApi.moderate({ text: moderateText.value })
    moderateResult.value = data.result
    moderateCache.value = data.from_cache
  } finally {
    moderateLoading.value = false
  }
}

onMounted(loadArticles)
</script>

<template>
  <div>
    <NavBar />

    <div class="ai-hero">
      <h1><el-icon :size="26" color="#7c5cff"><MagicStick /></el-icon> AI 智能内容服务</h1>
      <p>基于 DeepSeek 大模型 · Prompt 工程 · 结果缓存（ai_cache）· Celery 异步</p>
    </div>

    <div class="page-container ai-grid">
      <!-- ① 自动摘要：选文章生成并保存 -->
      <el-card class="ai-card" v-loading="articleLoading">
        <template #header>
          <div class="card-head">
            <b><el-icon><Document /></el-icon> AI 自动摘要</b>
            <el-tag v-if="summaryCache" size="small" type="success">缓存命中</el-tag>
          </div>
        </template>
        <el-select
          v-model="summaryArticleId"
          placeholder="选择我的文章"
          filterable
          style="width: 100%"
          class="mb8"
        >
          <el-option v-for="a in myArticles" :key="a.id" :label="optionLabel(a)" :value="a.id" />
        </el-select>
        <div class="card-actions">
          <el-button type="primary" :loading="summaryLoading" @click="doSummary">生成摘要</el-button>
          <el-button
            v-if="summaryResult"
            type="success"
            plain
            :loading="summarySaving"
            @click="saveSummary"
          >
            <el-icon><CircleCheck /></el-icon>保存到文章
          </el-button>
        </div>
        <el-alert
          v-if="summaryResult"
          :title="summaryResult"
          type="success"
          :closable="false"
          class="result-box"
        />
        <el-tag v-if="summarySaved" type="success" effect="plain" class="saved-tip">已保存 ✓</el-tag>
      </el-card>

      <!-- ② 自动标签：选文章生成并应用 -->
      <el-card class="ai-card" v-loading="articleLoading">
        <template #header>
          <div class="card-head">
            <b><el-icon><PriceTag /></el-icon> AI 自动标签</b>
            <el-tag v-if="tagsCache" size="small" type="success">缓存命中</el-tag>
          </div>
        </template>
        <el-select
          v-model="tagsArticleId"
          placeholder="选择我的文章"
          filterable
          style="width: 100%"
          class="mb8"
        >
          <el-option v-for="a in myArticles" :key="a.id" :label="optionLabel(a)" :value="a.id" />
        </el-select>
        <div class="card-actions">
          <el-button type="primary" :loading="tagsLoading" @click="doTags">提取标签</el-button>
          <el-button
            v-if="tagsResult.length"
            type="success"
            plain
            :loading="tagsSaving"
            @click="saveTags"
          >
            <el-icon><CircleCheck /></el-icon>应用到文章
          </el-button>
        </div>
        <div v-if="tagsResult.length" class="tags-result">
          <el-tag v-for="t in tagsResult" :key="t" type="warning" effect="light" size="large" class="tag-item">
            {{ t }}
          </el-tag>
        </div>
        <el-tag v-if="tagsSaved" type="success" effect="plain" class="saved-tip">已应用 ✓</el-tag>
      </el-card>

      <!-- ③ 写作助手 -->
      <el-card class="ai-card">
        <template #header>
          <div class="card-head">
            <b><el-icon><EditPen /></el-icon> AI 写作助手</b>
            <el-tag v-if="writerCache" size="small" type="success">缓存命中</el-tag>
          </div>
        </template>
        <el-input v-model="writerPrompt" type="textarea" :rows="4" placeholder="例如：写一篇介绍 Redis 缓存策略的技术文章，包含缓存穿透、击穿、雪崩的解决方案" />
        <div class="card-actions">
          <el-button type="primary" :loading="writerLoading" @click="doWriter">开始写作</el-button>
        </div>
        <el-alert v-if="writerResult" :title="'AI 生成结果'" type="info" :closable="false" class="result-box">
          <div class="writer-content">{{ writerResult }}</div>
          <div class="writer-actions">
            <el-button type="success" size="small" @click="saveAsDraft">
              <el-icon><Plus /></el-icon>保存为草稿文章
            </el-button>
          </div>
        </el-alert>
      </el-card>

      <!-- ④ RAG 问答 -->
      <el-card class="ai-card">
        <template #header>
          <div class="card-head">
            <b><el-icon><ChatDotRound /></el-icon> RAG 智能问答</b>
            <el-tag v-if="qaCache" size="small" type="success">缓存命中</el-tag>
          </div>
        </template>
        <el-input v-model="qaQuestion" placeholder="你的问题，如：Django 6.0 相比旧版有什么改进？" class="mb8" />
        <el-input v-model="qaContext" type="textarea" :rows="4" placeholder="参考资料（可粘贴混合检索召回的文章片段）" />
        <div class="card-actions">
          <el-button type="primary" :loading="qaLoading" @click="doQa">AI 解答</el-button>
        </div>
        <el-alert v-if="qaResult" title="AI 回答" type="success" :closable="false" class="result-box">
          <div class="writer-content">{{ qaResult }}</div>
        </el-alert>
      </el-card>

      <!-- ⑤ 评论审核 -->
      <el-card class="ai-card wide">
        <template #header>
          <div class="card-head">
            <b><el-icon><CircleCheck /></el-icon> AI 评论自动审核</b>
            <el-tag v-if="moderateCache" size="small" type="success">缓存命中</el-tag>
          </div>
        </template>
        <el-input v-model="moderateText" type="textarea" :rows="3" placeholder="输入一条评论，AI 判断是否通过审核" />
        <div class="card-actions">
          <el-button type="primary" :loading="moderateLoading" @click="doModerate">智能审核</el-button>
        </div>
        <el-alert
          v-if="moderateResult"
          :type="moderateResult.result === 'pass' ? 'success' : 'error'"
          :closable="false"
          class="result-box"
        >
          <b>{{ moderateResult.result === 'pass' ? '✓ 审核通过' : '✗ 建议拒绝' }}</b>
          <div class="writer-content">{{ moderateResult.reason }}</div>
        </el-alert>
      </el-card>
    </div>

    <Footer />
  </div>
</template>

<style scoped>
.ai-hero {
  background: linear-gradient(135deg, #f3efff 0%, #eaf3ff 100%);
  text-align: center;
  padding: 36px 16px;
}

.ai-hero h1 {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 26px;
  color: #1f2d3d;
  margin-bottom: 8px;
}

.ai-hero p {
  color: #909399;
  font-size: 14px;
}

.ai-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.ai-card.wide {
  grid-column: 1 / -1;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-head b {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.mb8 {
  margin-bottom: 8px;
}

.card-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.result-box {
  margin-top: 14px;
  white-space: pre-wrap;
}

.writer-content {
  margin-top: 6px;
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
}

.writer-actions {
  margin-top: 12px;
}

.tags-result {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  font-size: 14px;
}

.saved-tip {
  margin-top: 10px;
}

@media (max-width: 900px) {
  .ai-grid {
    grid-template-columns: 1fr;
  }
}
</style>
