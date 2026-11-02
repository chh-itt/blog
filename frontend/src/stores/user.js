/*
 * 用户状态管理（Pinia）
 * 维护登录状态、用户信息，提供登录/登出/刷新
 */
import { defineStore } from 'pinia'
import { authApi } from '../api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    user: JSON.parse(localStorage.getItem('user_info') || 'null'),
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    // 博主标记：is_author=true（由后端超级用户/博主账号决定）
    isAdmin: (state) => !!state.user?.is_author,
  },

  actions: {
    /** 登录成功后保存凭证 */
    setSession({ access, refresh, user }) {
      this.token = access
      this.refreshToken = refresh
      this.user = user
      localStorage.setItem('access_token', access)
      localStorage.setItem('refresh_token', refresh)
      localStorage.setItem('user_info', JSON.stringify(user))
    },

    async login(username, password) {
      const data = await authApi.login({ username, password })
      // 必须先写入 token 再请求 me()，否则 me() 请求不带认证头会 401
      this.setSession({ access: data.access, refresh: data.refresh, user: null })
      const user = await authApi.me().catch(() => null)
      if (user) {
        this.user = user
        localStorage.setItem('user_info', JSON.stringify(user))
      }
      return user
    },

    async register(form) {
      const user = await authApi.register(form)
      return user
    },

    async fetchMe() {
      if (!this.token) return null
      try {
        const user = await authApi.me()
        this.user = user
        localStorage.setItem('user_info', JSON.stringify(user))
        return user
      } catch (e) {
        return null
      }
    },

    async logout() {
      try {
        if (this.refreshToken) await authApi.logout(this.refreshToken)
      } catch (e) {
        /* 忽略黑名单失败 */
      }
      this.token = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_info')
    },
  },
})
