<script setup>
// 评论审核：待审列表 + 人工审核 + AI 自动审核（创新点1-E）
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { blogApi } from '../../api'

const pending = ref([])
const loading = ref(false)
const aiLoadingId = ref(null)

async function load() {
  loading.value = true
  try {
    pending.value = await blogApi.pendingComments()
  } finally {
    loading.value = false
  }
}

async function moderate(id, action) {
  try {
    await blogApi.moderateComment(id, action)
    ElMessage.success(action === 'approve' ? '已通过' : '已拒绝')
    load()
  } catch (e) {
    /* 拦截器提示 */
  }
}

async function autoModerate(id) {
  aiLoadingId.value = id
  try {
    const data = await blogApi.autoModerate(id)
    const passed = data.result?.result === 'pass'
    ElMessage.success(passed ? `AI 审核通过：${data.result?.reason}` : `AI 建议拒绝：${data.result?.reason}`)
    load()
  } catch (e) {
    /* 拦截器提示 */
  } finally {
    aiLoadingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h3>待审核评论（{{ pending.length }}）</h3>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-card v-loading="loading">
      <el-empty v-if="!loading && !pending.length" description="没有待审核的评论" />

      <el-table v-else :data="pending" stripe>
        <el-table-column label="评论内容" min-width="280">
          <template #default="{ row }">
            <div class="comment-cell">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="评论者" width="120">
          <template #default="{ row }">{{ row.user?.nickname || row.user?.username }}</template>
        </el-table-column>
        <el-table-column label="文章" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.article?.title }}</template>
        </el-table-column>
        <el-table-column label="时间" width="120">
          <template #default="{ row }">{{ (row.created_at || '').replace('T', ' ').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button
              type="warning"
              size="small"
              :loading="aiLoadingId === row.id"
              @click="autoModerate(row.id)"
            >
              <el-icon><MagicStick /></el-icon>AI 审核
            </el-button>
            <el-button type="success" size="small" @click="moderate(row.id, 'approve')">通过</el-button>
            <el-button type="danger" size="small" @click="moderate(row.id, 'reject')">拒绝</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.comment-cell {
  max-width: 320px;
  white-space: pre-wrap;
}
</style>
