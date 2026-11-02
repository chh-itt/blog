<script setup>
// 文章编辑页：Markdown 写作 + AI 摘要/标签辅助（创新点1 集成到创作流程）
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import { aigcApi, blogApi } from '../../api'

const route = useRoute()
const router = useRouter()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const articleId = computed(() => (route.params.id ? Number(route.params.id) : null))
const saving = ref(false)
const loading = ref(!!articleId.value)

const form = ref({
  title: '',
  summary: '',
  content_md: '',
  content_html: '',
  status: 0, // 0 草稿 1 发布
  is_top: false,
  allow_comment: true,
  category: null,
  tags: [],
})

const categories = ref([])
const allTags = ref([])
const previewHtml = computed(() => md.render(form.value.content_md || ''))

// 分类选项：顶层 + 子分类扁平化（子类显示"父类 / 子类"）
const categoryOptions = computed(() => {
  const opts = []
  for (const c of categories.value || []) {
    opts.push({ id: c.id, label: c.name })
    for (const ch of c.children || []) {
      opts.push({ id: ch.id, label: `${c.name} / ${ch.name}` })
    }
  }
  return opts
})

// AI 辅助状态
const aiSummaryLoading = ref(false)
const aiTagsLoading = ref(false)
const aiCatLoading = ref(false)

// AI 写作助手（创新点1 集成到创作流程）
const aiWriterVisible = ref(false)
const aiWriterPrompt = ref('')
const aiWriterLoading = ref(false)
const aiWriterResult = ref('')

async function aiWrite() {
  if (!aiWriterPrompt.value.trim()) return ElMessage.warning('请输入写作主题或要点')
  aiWriterLoading.value = true
  try {
    const data = await aigcApi.writer({ prompt: aiWriterPrompt.value })
    aiWriterResult.value = data.result
    if (data.from_cache) ElMessage.success('AI 生成成功（缓存命中）')
    else ElMessage.success('AI 生成成功')
  } finally {
    aiWriterLoading.value = false
  }
}

function insertWriter() {
  if (!aiWriterResult.value) return
  form.value.content_md =
    (form.value.content_md ? form.value.content_md.trimEnd() + '\n\n' : '') + aiWriterResult.value
  aiWriterVisible.value = false
  aiWriterResult.value = ''
  aiWriterPrompt.value = ''
  ElMessage.success('AI 内容已插入正文末尾')
}

function replaceWriter() {
  if (!aiWriterResult.value) return
  form.value.content_md = aiWriterResult.value
  aiWriterVisible.value = false
  aiWriterResult.value = ''
  aiWriterPrompt.value = ''
  ElMessage.success('AI 内容已替换全文')
}

// 从 AI 助手页「保存为草稿文章」跳转而来：预填标题与正文（仅新建文章时）
function loadAiDraft() {
  if (articleId.value) return // 编辑已有文章时不覆盖
  const raw = sessionStorage.getItem('ai_draft')
  if (!raw) return
  try {
    const d = JSON.parse(raw)
    if (d.content_md) form.value.content_md = d.content_md
    if (d.title) form.value.title = d.title
    sessionStorage.removeItem('ai_draft')
    ElMessage.success('已带入 AI 生成的草稿，可直接编辑后发布')
  } catch {
    /* 忽略损坏的暂存数据 */
  }
}

async function loadMeta() {
  categories.value = await blogApi.categories()
  allTags.value = await blogApi.tags()
}

async function loadArticle() {
  if (!articleId.value) return
  loading.value = true
  try {
    // 用「我的文章详情」接口加载（含草稿与正文；列表接口为性能不带正文）
    const art = await blogApi.myArticle(articleId.value)
    form.value = {
      title: art.title,
      summary: art.summary,
      content_md: art.content_md || '',
      content_html: art.content_html || '',
      status: art.status,
      is_top: art.is_top,
      allow_comment: art.allow_comment,
      category: art.category?.id || null,
      tags: art.tags?.map((t) => t.id) || [],
    }
  } finally {
    loading.value = false
  }
}

async function save(publish = false) {
  if (!form.value.title.trim() || !form.value.content_md.trim()) {
    ElMessage.warning('标题和正文不能为空')
    return
  }
  if (publish) form.value.status = 1
  saving.value = true
  try {
    // 手动输入的新分类（allow-create 产生的是字符串名）→ 先入库再保存
    if (typeof form.value.category === 'string') {
      if (form.value.category.trim()) {
        const cat = await blogApi.ensureCategory(form.value.category.trim())
        form.value.category = cat.id
      } else {
        form.value.category = null
      }
    }
    const payload = {
      title: form.value.title,
      summary: form.value.summary,
      content_md: form.value.content_md,
      content_html: md.render(form.value.content_md),
      status: form.value.status,
      is_top: form.value.is_top,
      allow_comment: form.value.allow_comment,
      category: form.value.category || null,
      tags: form.value.tags,
    }
    if (articleId.value) {
      await blogApi.updateArticle(articleId.value, payload)
    } else {
      await blogApi.createArticle(payload)
    }
    ElMessage.success(publish ? '文章已发布' : '草稿已保存')
    router.push('/admin/articles')
  } finally {
    saving.value = false
  }
}

// AI 自动摘要（创新点1）
async function aiSummary() {
  if (!form.value.content_md.trim()) return ElMessage.warning('请先填写正文')
  aiSummaryLoading.value = true
  try {
    const data = await aigcApi.summary({ text: form.value.content_md })
    form.value.summary = data.result
    if (data.from_cache) ElMessage.success('AI 摘要生成成功（缓存命中）')
    else ElMessage.success('AI 摘要生成成功')
  } finally {
    aiSummaryLoading.value = false
  }
}

// AI 自动标签（创新点1）：生成 → 自动入库（不存在则创建）→ 合并选中
async function aiTags() {
  if (!form.value.title.trim()) return ElMessage.warning('请先填写标题')
  aiTagsLoading.value = true
  try {
    const data = await aigcApi.tags({ title: form.value.title, content: form.value.content_md })
    const names = data.result
    // 批量确保标签存在：已有标签复用 id，新标签自动创建
    const ensured = await blogApi.ensureTags(names)
    const newCount = ensured.filter((t) => t.created).length
    const ids = ensured.map((t) => t.id)
    form.value.tags = [...new Set([...form.value.tags, ...ids])]
    // 刷新可选标签列表（新建的标签也出现在下拉里）
    allTags.value = await blogApi.tags()
    const hit = data.from_cache ? '（缓存命中）' : ''
    ElMessage.success(`AI 标签已应用 ${ensured.length} 个（新建 ${newCount} 个）${hit}`)
  } finally {
    aiTagsLoading.value = false
  }
}

// AI 自动分类（创新点1）：识别 → 入库（同名复用，否则新建）→ 选中
async function aiCategory() {
  if (!form.value.title.trim()) return ElMessage.warning('请先填写标题')
  aiCatLoading.value = true
  try {
    // 现有分类名作为候选，让 AI 优先复用已有分类
    const names = categoryOptions.value.map((o) => o.label.split(' / ').pop())
    const data = await aigcApi.classify({
      title: form.value.title,
      content: form.value.content_md,
      candidates: names,
    })
    const catName = data.result?.category
    if (!catName) return ElMessage.warning('AI 未识别出合适分类，可手动输入')
    const cat = await blogApi.ensureCategory(catName)
    form.value.category = cat.id
    categories.value = await blogApi.categories() // 刷新（新建分类也出现在下拉/前台侧栏）
    const hit = data.from_cache ? '（缓存命中）' : ''
    ElMessage.success(`AI 分类：${catName}${cat.created ? '（已新建）' : ''}${hit}`)
  } finally {
    aiCatLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadMeta(), loadArticle()])
  loadAiDraft()
})
</script>

<template>
  <div v-loading="loading">
    <div class="toolbar">
      <h3>{{ articleId ? '编辑文章' : '新建文章' }}</h3>
      <div>
        <el-button @click="save(false)" :loading="saving">存为草稿</el-button>
        <el-button type="primary" @click="save(true)" :loading="saving">发布文章</el-button>
      </div>
    </div>

    <el-card>
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入文章标题" size="large" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类">
              <div class="ai-assist-row">
                <el-select
                  v-model="form.category"
                  filterable
                  allow-create
                  default-first-option
                  placeholder="选择或输入新分类"
                  clearable
                  style="width: 100%"
                >
                  <el-option
                    v-for="cat in categoryOptions"
                    :key="cat.id"
                    :label="cat.label"
                    :value="cat.id"
                  />
                </el-select>
                <el-button
                  type="warning"
                  plain
                  :loading="aiCatLoading"
                  @click="aiCategory"
                  class="ai-btn"
                >
                  <el-icon><FolderOpened /></el-icon>AI 分类
                </el-button>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-select v-model="form.tags" multiple placeholder="选择标签" style="width: 100%">
                <el-option v-for="t in allTags" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- AI 摘要辅助 -->
        <el-form-item label="摘要">
          <div class="ai-assist-row">
            <el-input v-model="form.summary" type="textarea" :rows="2" placeholder="文章摘要（可点击右侧按钮用 AI 生成）" />
            <el-button
              type="warning"
              :loading="aiSummaryLoading"
              @click="aiSummary"
              class="ai-btn"
            >
              <el-icon><MagicStick /></el-icon>AI 摘要
            </el-button>
            <el-button
              type="warning"
              plain
              :loading="aiTagsLoading"
              @click="aiTags"
              class="ai-btn"
            >
              <el-icon><PriceTag /></el-icon>AI 标签
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="正文（Markdown）">
          <div class="ai-write-toolbar">
            <el-button type="warning" plain size="small" @click="aiWriterVisible = true">
              <el-icon><EditPen /></el-icon>AI 写作助手
            </el-button>
          </div>
          <el-input
            v-model="form.content_md"
            type="textarea"
            :rows="16"
            placeholder="# 标题&#10;&#10;正文内容..."
          />
        </el-form-item>

        <el-form-item label="预览">
          <div class="markdown-body preview-box" v-html="previewHtml"></div>
        </el-form-item>

        <el-form-item>
          <el-switch v-model="form.is_top" active-text="置顶" />
          <el-switch v-model="form.allow_comment" active-text="允许评论" class="ml16" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- AI 写作助手弹窗 -->
    <el-dialog v-model="aiWriterVisible" title="AI 写作助手" width="680px">
      <el-input
        v-model="aiWriterPrompt"
        type="textarea"
        :rows="4"
        placeholder="输入写作主题或要点，例如：写一段介绍 Django 异步 ORM 相对同步查询优势的内容"
      />
      <div class="ai-write-actions">
        <el-button type="primary" :loading="aiWriterLoading" @click="aiWrite">生成内容</el-button>
      </div>
      <div v-if="aiWriterResult" class="ai-write-result">
        <div class="writer-content">{{ aiWriterResult }}</div>
        <div class="ai-write-actions">
          <el-button type="success" @click="insertWriter">插入正文末尾</el-button>
          <el-button @click="replaceWriter">替换全文</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.ai-assist-row {
  display: flex;
  gap: 8px;
  width: 100%;
}

.ai-assist-row .el-textarea {
  flex: 1;
}

.ai-btn {
  height: auto;
}

.ml16 {
  margin-left: 16px;
}

.ai-write-toolbar {
  margin-bottom: 8px;
}

.ai-write-actions {
  margin-top: 10px;
}

.ai-write-result {
  margin-top: 12px;
}

.writer-content {
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
}

.preview-box {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  width: 100%;
  min-height: 100px;
  background: #fff;
}
</style>
