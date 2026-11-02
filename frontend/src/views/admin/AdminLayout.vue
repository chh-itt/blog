<script setup>
// 管理后台布局：侧边菜单 + 内容区
import { useRouter } from 'vue-router'
import { useUserStore } from '../../stores/user'

const router = useRouter()
const userStore = useUserStore()

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <div class="admin-logo">智博空间 · 管理后台</div>
      <el-menu router :default-active="$route.path" class="admin-menu">
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataAnalysis /></el-icon>数据统计面板
        </el-menu-item>
        <el-menu-item index="/admin/articles">
          <el-icon><Document /></el-icon>文章管理
        </el-menu-item>
        <el-menu-item index="/admin/comments">
          <el-icon><ChatDotRound /></el-icon>评论审核
        </el-menu-item>
        <el-menu-item index="/admin/settings">
          <el-icon><Setting /></el-icon>系统设置
        </el-menu-item>
        <el-menu-item index="/">
          <el-icon><Back /></el-icon>返回前台
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <span class="header-title">内容管理系统</span>
        <div class="header-right">
          <el-button text @click="router.push('/ai')">
            <el-icon><MagicStick /></el-icon>AI 服务
          </el-button>
          <el-dropdown @command="(cmd) => cmd === 'logout' && handleLogout()">
            <span class="admin-user">
              <el-avatar :size="28" :src="userStore.user?.avatar || undefined">
                {{ (userStore.user?.nickname || 'A').charAt(0) }}
              </el-avatar>
              {{ userStore.user?.nickname || userStore.user?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.admin-aside {
  background: #2c3e50;
  color: #fff;
}

.admin-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 15px;
}

.admin-menu {
  border-right: none;
  background: transparent;
}

.admin-menu :deep(.el-menu-item) {
  color: #b8c4ce;
}

.admin-menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.admin-menu :deep(.el-menu-item.is-active) {
  background: #409eff;
  color: #fff;
}

.admin-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
  color: #303133;
}

.admin-main {
  background: #f5f7fa;
}
</style>
