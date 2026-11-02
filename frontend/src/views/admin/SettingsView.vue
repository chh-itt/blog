<script setup>
/*
 * 系统设置页（仅博主）
 * 运行时配置 DeepSeek / Embedding 的 API Key 等，无需修改 .env 文件
 * - 敏感项（API Key）从后端返回时已脱敏（如 sk-****abcd）
 * - 保存时：未改动的敏感项不提交，避免把脱敏值覆盖真实 Key
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { sysconfApi } from '../../api'

const list = ref([])
const form = ref({})
const loading = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await sysconfApi.getConfig()
    list.value = data
    form.value = {}
    data.forEach((item) => {
      form.value[item.key] = item.value
    })
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  const payload = {}
  let dirty = false
  list.value.forEach((item) => {
    const cur = (form.value[item.key] || '').trim()
    if (item.is_secret) {
      // 敏感项：未修改（仍是脱敏值）则不提交；清空或输入新值才提交
      if (cur === '') {
        payload[item.key] = ''
        dirty = true
      } else if (cur !== item.value) {
        payload[item.key] = cur
        dirty = true
      }
    } else if (cur !== item.value) {
      payload[item.key] = cur
      dirty = true
    }
  })
  if (!dirty) {
    ElMessage.info('没有需要保存的修改')
    return
  }
  saving.value = true
  try {
    await sysconfApi.updateConfig(payload)
    ElMessage.success('系统配置已保存')
    await load()
  } catch (e) {
    /* 错误由拦截器提示 */
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="settings-page">
    <el-card>
      <template #header>
        <div class="settings-header">
          <span class="card-title">系统设置 · AI 服务配置</span>
          <el-button type="primary" :loading="saving" @click="handleSave">保存配置</el-button>
        </div>
      </template>

      <el-alert
        title="在这里填写 API Key 后无需重启服务即可生效；敏感项仅显示脱敏值。留空某敏感项表示使用 backend/.env 中的默认值。"
        type="info"
        :closable="false"
        class="settings-tip"
      />

      <el-skeleton v-if="loading" :rows="6" animated />

      <div v-else class="config-list">
        <div v-for="item in list" :key="item.key" class="config-row">
          <div class="config-meta">
            <div class="config-key">
              {{ item.key }}
              <el-tag v-if="item.is_secret" size="small" type="warning">敏感项</el-tag>
            </div>
            <div class="config-desc">{{ item.description }}</div>
          </div>
          <el-input
            v-model="form[item.key]"
            :type="item.is_secret ? 'password' : 'text'"
            :show-password="item.is_secret"
            placeholder="留空使用默认值"
            class="config-input"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-weight: 700;
  font-size: 16px;
}

.settings-tip {
  margin-bottom: 20px;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 24px;
}

.config-meta {
  width: 320px;
  flex-shrink: 0;
}

.config-key {
  font-weight: 600;
  font-family: 'Consolas', monospace;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.config-input {
  flex: 1;
}
</style>
