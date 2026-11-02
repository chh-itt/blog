<script setup>
// 前台顶部导航栏
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const user = computed(() => userStore.user)
const isAdmin = computed(() => userStore.isAdmin)

async function handleLogout() {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <router-link to="/" class="logo">
        <el-icon :size="22" color="#409eff"><Promotion /></el-icon>
        <span class="logo-text">智博空间</span>
      </router-link>

      <nav class="nav-links">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/search" class="nav-link">智能搜索</router-link>
        <router-link to="/ai" class="nav-link ai-badge">AI 助手</router-link>
        <router-link v-if="isAdmin" to="/admin" class="nav-link">管理后台</router-link>
      </nav>

      <div class="nav-user">
        <template v-if="isLoggedIn">
          <el-dropdown>
            <span class="user-chip">
              <el-avatar :size="30" :src="user?.avatar || undefined">
                {{ (user?.nickname || user?.username || '?').charAt(0) }}
              </el-avatar>
              <span class="user-name">{{ user?.nickname || user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="router.push('/profile')">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item @click="router.push('/ai')">
                  <el-icon><MagicStick /></el-icon>AI 智能服务
                </el-dropdown-item>
                <el-dropdown-item v-if="isAdmin" @click="router.push('/admin')">
                  <el-icon><Monitor /></el-icon>管理后台
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button text @click="router.push('/login')">登录</el-button>
          <el-button type="primary" @click="router.push('/register')">注册</el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.navbar-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 16px;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #303133;
}

.logo-text {
  background: linear-gradient(90deg, #409eff, #7c5cff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-links {
  display: flex;
  gap: 24px;
  flex: 1;
}

.nav-link {
  color: #606266;
  font-size: 15px;
  transition: color 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active {
  color: #409eff;
}

.ai-badge {
  position: relative;
}

.ai-badge::after {
  content: 'AI';
  position: absolute;
  top: -6px;
  right: -18px;
  font-size: 10px;
  color: #fff;
  background: linear-gradient(90deg, #f56c6c, #e6a23c);
  padding: 1px 5px;
  border-radius: 8px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #303133;
  outline: none;
}

.user-name {
  font-size: 14px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
