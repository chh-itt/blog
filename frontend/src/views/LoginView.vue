<script setup>
// 登录页
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    ElMessage.success('登录成功，欢迎回来！')
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误提示由拦截器处理 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <div class="auth-title">登录智博空间</div>
      <div class="auth-sub">基于 Django + JWT 的安全认证</div>

      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" :prefix-icon="'User'" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="'Lock'"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>

      <div class="auth-switch">
        还没有账号？<router-link to="/register" class="link">立即注册</router-link>
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
  width: 400px;
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
