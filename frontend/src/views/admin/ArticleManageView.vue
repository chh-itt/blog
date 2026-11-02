<script setup>
// 文章管理：列表 + 编辑/删除 + 新建
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { blogApi } from '../../api'

const router = useRouter()
const articles = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await blogApi.myArticles()
    // 防御：兼容返回分页结构的情况（正常应直接是数组）
    articles.value = Array.isArray(data) ? data : (data?.results || [])
  } finally {
    loading.value = false
  }
}

async function remove(id, title) {
  try {
    await ElMessageBox.confirm(`确定删除《${title}》吗？此操作不可恢复`, '删除确认', {
      type: 'warning',
    })
    await blogApi.deleteArticle(id)
    ElMessage.success('删除成功')
    load()
  } catch (e) {
    /* 取消或失败 */
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h3>我的文章（{{ articles.length }}）</h3>
      <el-button type="primary" @click="router.push('/admin/article-edit')">
        <el-icon><Plus /></el-icon>新建文章
      </el-button>
    </div>

    <el-card v-loading="loading">
      <el-table :data="articles" stripe>
        <el-table-column prop="title" label="标题" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '已发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AI摘要" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.ai_summary" type="warning" size="small">已生成</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="views" label="浏览" width="80" />
        <el-table-column prop="likes" label="点赞" width="80" />
        <el-table-column label="发布时间" width="120">
          <template #default="{ row }">{{ (row.published_at || '').slice(0, 10) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/admin/article-edit/${row.id}`)">编辑</el-button>
            <el-button link type="danger" @click="remove(row.id, row.title)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && !articles.length" description="还没有文章，点击右上角新建" />
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

.muted {
  color: #c0c4cc;
}
</style>
