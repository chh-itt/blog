<script setup>
// 文章详情页：Markdown 渲染 + AI 摘要/标签 + 评论区 + 相关文章推荐
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import MarkdownIt from 'markdown-it'
import { ElMessage } from 'element-plus'
import { blogApi } from '../api'
import { useUserStore } from '../stores/user'

const route = useRoute()
const userStore = useUserStore()
const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const article = ref(null)
const related = ref([])
const comments = ref([])
const commentText = ref('')
const submitting = ref(false)
const loading = ref(true)

const articleId = computed(() => Number(route.params.id))
const contentHtml = computed(() => (article.value ? md.render(article.value.content_md || '') : ''))

async function load() {
  loading.value = true
  try {
    article.value = await blogApi.getArticle(articleId.value)
    loadRelated()
    loadComments()
  } finally {
    loading.value = false
  }
}

async function loadRelated() {
  try {
    const data = await blogApi.related(articleId.value)
    related.value = data.results || []
  } catch (e) {
    related.value = []
  }
}

async function loadComments() {
  try {
    const data = await blogApi.comments(articleId.value)
    comments.value = data.results || []
  } catch (e) {
    comments.value = []
  }
}

async function submitComment() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录后再评论')
    return
  }
  if (!commentText.value.trim()) {
    ElMessage.warning('评论内容不能为空')
    return
  }
  submitting.value = true
  try {
    await blogApi.postComment(articleId.value, { content: commentText.value })
    commentText.value = ''
    ElMessage.success('评论已提交，等待博主审核通过后展示')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <NavBar />

    <div v-loading="loading" class="page-container article-page">
      <template v-if="article">
        <el-card class="article-card">
          <h1 class="title">{{ article.title }}</h1>

          <div class="meta">
            <span><el-icon><User /></el-icon> {{ article.author?.nickname || article.author?.username }}</span>
            <span><el-icon><Calendar /></el-icon> {{ (article.published_at || '').slice(0, 10) }}</span>
            <span><el-icon><View /></el-icon> {{ article.views }} 阅读</span>
            <span><el-icon><Star /></el-icon> {{ article.likes }} 点赞</span>
          </div>

          <!-- AI 摘要（创新点1） -->
          <div v-if="article.ai_summary" class="ai-box">
            <div class="ai-box-title">
              <el-icon color="#7c5cff"><MagicStick /></el-icon>
              AI 智能摘要
            </div>
            <p>{{ article.ai_summary }}</p>
          </div>

          <div class="tags-row">
            <el-tag
              v-for="t in (article.ai_tags || [])"
              :key="t"
              size="small"
              type="warning"
              effect="light"
            >
              {{ t }}
            </el-tag>
          </div>

          <!-- Markdown 正文 -->
          <div class="markdown-body" v-html="contentHtml"></div>
        </el-card>

        <!-- 相关文章推荐（创新点2） -->
        <el-card v-if="related.length" class="related-card">
          <template #header><b>相关文章推荐（基于语义相似度）</b></template>
          <ul class="related-list">
            <li v-for="r in related" :key="r.id">
              <router-link :to="`/article/${r.id}`">{{ r.title }}</router-link>
              <span class="rel-views">{{ r.views }} 阅读</span>
            </li>
          </ul>
        </el-card>

        <!-- 评论区 -->
        <el-card class="comment-card">
          <template #header><b>评论（{{ comments.length }}）</b></template>

          <div class="comment-input">
            <el-input
              v-model="commentText"
              type="textarea"
              :rows="3"
              placeholder="友善评论，博主审核后展示~"
              maxlength="500"
              show-word-limit
            />
            <div class="comment-actions">
              <el-button type="primary" :loading="submitting" @click="submitComment">
                发表评论
              </el-button>
            </div>
          </div>

          <el-empty v-if="!comments.length" description="还没有评论，来抢沙发~" :image-size="70" />

          <div v-for="c in comments" :key="c.id" class="comment-item">
            <el-avatar :size="34">{{ (c.user?.nickname || c.user?.username || '?').charAt(0) }}</el-avatar>
            <div class="comment-body">
              <div class="comment-head">
                <b>{{ c.user?.nickname || c.user?.username }}</b>
                <span class="comment-time">{{ (c.created_at || '').replace('T', ' ').slice(0, 16) }}</span>
              </div>
              <p class="comment-content">{{ c.content }}</p>
            </div>
          </div>
        </el-card>
      </template>

      <el-empty v-else-if="!loading" description="文章不存在或已下架" />
    </div>

    <Footer />
  </div>
</template>

<style scoped>
.article-page {
  max-width: 860px;
}

.article-card {
  padding: 8px 16px;
}

.title {
  font-size: 26px;
  color: #1f2d3d;
  margin-bottom: 12px;
}

.meta {
  display: flex;
  gap: 18px;
  color: #909399;
  font-size: 13px;
  padding-bottom: 14px;
  border-bottom: 1px dashed #ebeef5;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ai-box {
  background: linear-gradient(90deg, #f5f2ff, #f0f7ff);
  border: 1px solid #e6e0ff;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.ai-box-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #7c5cff;
  margin-bottom: 8px;
  font-size: 14px;
}

.ai-box p {
  color: #5a4d8f;
  font-size: 14px;
  line-height: 1.8;
}

.tags-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.related-card {
  margin-top: 16px;
}

.related-list {
  list-style: none;
}

.related-list li {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f2f3f5;
}

.related-list li a {
  color: #409eff;
  font-size: 14px;
}

.related-list li a:hover {
  text-decoration: underline;
}

.rel-views {
  color: #c0c4cc;
  font-size: 12px;
}

.comment-card {
  margin-top: 16px;
}

.comment-input {
  margin-bottom: 20px;
}

.comment-actions {
  margin-top: 10px;
  text-align: right;
}

.comment-item {
  display: flex;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid #f2f3f5;
}

.comment-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.comment-time {
  color: #c0c4cc;
  font-size: 12px;
}

.comment-content {
  color: #303133;
  font-size: 14px;
  line-height: 1.7;
}
</style>
