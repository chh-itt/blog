<script setup>
/*
 * 个人中心页
 * - 编辑昵称 / 简介 / 邮箱
 * - 头像：支持上传本地图片或填写图片 URL（留空使用默认首字符头像）
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const form = ref({ nickname: '', bio: '', email: '', avatar: '' })
const uploading = ref(false)
const saving = ref(false)

onMounted(() => {
  const u = userStore.user || {}
  form.value = {
    nickname: u.nickname || '',
    bio: u.bio || '',
    email: u.email || '',
    avatar: u.avatar || '',
  }
})

async function handleSave() {
  saving.value = true
  try {
    const data = await authApi.updateMe({
      nickname: form.value.nickname,
      bio: form.value.bio,
      email: form.value.email,
      avatar: form.value.avatar,
    })
    // 同步更新全局用户状态
    userStore.user = data
    localStorage.setItem('user_info', JSON.stringify(data))
    ElMessage.success('个人资料已保存')
  } catch (e) {
    /* 错误由拦截器提示 */
  } finally {
    saving.value = false
  }
}

/** 上传头像（el-upload 自定义请求） */
async function handleUpload(options) {
  uploading.value = true
  try {
    const res = await authApi.uploadAvatar(options.file)
    form.value.avatar = res.avatar
    ElMessage.success('头像上传成功')
  } catch (e) {
    ElMessage.error('头像上传失败')
  } finally {
    uploading.value = false
    options.onSuccess?.()
  }
}
</script>

<template>
  <div class="profile-page">
    <el-card class="profile-card">
      <template #header>
        <span class="card-title">个人中心</span>
      </template>

      <el-form label-position="top" class="profile-form">
        <!-- 头像区域 -->
        <div class="avatar-block">
          <el-avatar :size="88" :src="form.avatar || undefined" class="avatar-preview">
            {{ (form.nickname || userStore.user?.username || 'U').charAt(0) }}
          </el-avatar>
          <div class="avatar-actions">
            <el-upload :show-file-list="false" accept="image/*" :http-request="handleUpload">
              <el-button type="primary" plain :loading="uploading">上传头像</el-button>
            </el-upload>
            <div class="avatar-tip">支持 jpg/png/gif/webp，不超过 2MB；不上传则使用默认首字符头像</div>
          </div>
        </div>

        <el-form-item label="头像图片 URL（可选）">
          <el-input v-model="form.avatar" placeholder="http(s):// 或 /media/avatars/... 留空使用默认头像" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="显示在文章作者处的名字" maxlength="50" />
        </el-form-item>
        <el-form-item label="个人简介">
          <el-input v-model="form.bio" type="textarea" :rows="4" placeholder="介绍一下自己吧（可选）" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="用于找回密码等（可选）" />
        </el-form-item>

        <el-button type="primary" :loading="saving" @click="handleSave">保存资料</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 640px;
  margin: 32px auto;
  padding: 0 16px;
}

.card-title {
  font-weight: 700;
  font-size: 16px;
}

.avatar-block {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.avatar-preview {
  background: linear-gradient(135deg, #409eff, #7c5cff);
  color: #fff;
  font-size: 32px;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.avatar-tip {
  font-size: 12px;
  color: #909399;
}
</style>
