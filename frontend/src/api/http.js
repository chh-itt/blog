/*
 * API 请求客户端（axios 封装）
 * - 基础地址：开发环境走 vite 代理 /api，生产可改 VITE_API_BASE
 * - 请求拦截：自动附加 JWT access token
 * - 响应拦截：统一解包 {code, message, data}；401 自动尝试刷新 token
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000,
})

// 请求拦截：附加 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：解包 + 错误处理 + 401 自动刷新
let refreshing = false // 防止并发刷新

http.interceptors.response.use(
  (response) => {
    const body = response.data
    // 统一响应结构 {code, message, data}
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code === 0) return body.data
      return Promise.reject(new Error(body.message || '请求失败'))
    }
    return body
  },
  async (error) => {
    const { response, config } = error
    // 401：尝试用 refresh token 续期后重放请求
    if (response && response.status === 401 && !config._retry) {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh && !refreshing) {
        refreshing = true
        try {
          const res = await axios.post('/api/auth/token/refresh/', { refresh })
          localStorage.setItem('access_token', res.data.access)
          config._retry = true
          return http(config) // 重放原请求
        } catch (e) {
          // 刷新失败：清除凭证回登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_info')
          if (!location.pathname.includes('/login')) {
            location.href = '/login'
          }
        } finally {
          refreshing = false
        }
      }
    }
    const msg =
      response?.data?.message || error.message || '网络错误，请稍后重试'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http
