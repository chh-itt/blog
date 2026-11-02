/*
 * 路由配置
 * 前台公开页面 + AI 功能 + 管理后台
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/article/:id', name: 'article', component: () => import('../views/ArticleView.vue') },
  { path: '/search', name: 'search', component: () => import('../views/SearchView.vue') },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  { path: '/register', name: 'register', component: () => import('../views/RegisterView.vue') },
  // AI 智能内容服务（创新点1）
  { path: '/ai', name: 'ai', component: () => import('../views/AIView.vue'), meta: { requiresAuth: true } },
  // 个人中心（资料编辑 + 头像）
  { path: '/profile', name: 'profile', component: () => import('../views/ProfileView.vue'), meta: { requiresAuth: true } },
  // 管理后台
  {
    path: '/admin',
    component: () => import('../views/admin/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('../views/admin/DashboardView.vue') },
      { path: 'articles', name: 'admin-articles', component: () => import('../views/admin/ArticleManageView.vue') },
      { path: 'article-edit/:id?', name: 'admin-article-edit', component: () => import('../views/admin/ArticleEditView.vue') },
      { path: 'comments', name: 'admin-comments', component: () => import('../views/admin/CommentManageView.vue') },
      { path: 'settings', name: 'admin-settings', component: () => import('../views/admin/SettingsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// 路由守卫：登录/管理员权限校验
router.beforeEach((to) => {
  const store = useUserStore()
  if (to.meta.requiresAuth && !store.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin) {
    if (!store.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
    if (!store.user?.is_author) return { path: '/' }
  }
  return true
})

export default router
