<script setup>
// 注册页
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', nickname: '', email: '', password: '', password2: '' })
const loading = ref(false)

async function handleRegister() {
  const f = form.value
  if (!f.username || !f.password || !f.password2) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (f.password !== f.password2) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  loading.value = true
  try {
    await userStore.register(f)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-title">注册账号</div>
      <div class="auth-sub">加入智博空间，体验 AI 智能服务</div>

      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="登录用户名" size="large" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="展示昵称（可选）" size="large" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="邮箱（可选）" size="large" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" size="large" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.password2" type="password" placeholder="再次输入密码" size="large" show-password @keyup.enter="handleRegister" />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleRegister">
          注 册
        </el-button>
      </el-form>

      <div class="auth-switch">
        已有账号？<router-link to="/login" class="link">去登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eaf3ff 0%, #f3efff 100%);
}

.auth-card {
  width: 420px;
  padding: 16px 24px;
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  color: #1f2d3d;
  margin-bottom: 4px;
}

.auth-sub {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-bottom: 24px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.auth-switch {
  text-align: center;
  margin-top: 16px;
  color: #909399;
  font-size: 14px;
}

.link {
  color: #409eff;
  font-weight: 600;
}
</style>
