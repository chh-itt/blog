/*
 * 业务 API 封装：按模块划分，供页面调用
 */
import http from './http'

// ---------------- 认证 & 用户 ----------------
export const authApi = {
  login: (data) => http.post('/auth/token/', data),
  register: (data) => http.post('/users/register/', data),
  refresh: (refresh) => http.post('/auth/token/refresh/', { refresh }),
  logout: (refresh) => http.post('/auth/token/blacklist/', { refresh }),
  me: () => http.get('/users/me/'),
  updateMe: (data) => http.patch('/users/me/', data),
  // 头像上传（multipart）
  uploadAvatar: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/users/avatar/', form)
  },
}

// ---------------- 文章 ----------------
export const blogApi = {
  // 公开接口
  listArticles: (params) => http.get('/blog/articles/', { params }),
  getArticle: (id) => http.get(`/blog/articles/${id}/`),
  categories: () => http.get('/blog/categories/'),
  tags: () => http.get('/blog/tags/'),
  // AI 标签自动入库（不存在则创建，返回 id 列表）
  ensureTags: (names) => http.post('/blog/tags/ensure/', { names }),
  // AI/手动分类入库（同名复用，否则建为顶层，返回 id）
  ensureCategory: (name) => http.post('/blog/categories/ensure/', { name }),
  comments: (articleId, params) =>
    http.get(`/blog/articles/${articleId}/comments/`, { params }),
  // 混合检索（创新点2）
  search: (q) => http.get('/blog/search/', { params: { q } }),
  related: (articleId) => http.get(`/blog/articles/${articleId}/related/`),
  // 作者管理
  myArticles: () => http.get('/blog/my/articles/'),
  // 我的单篇文章详情（含草稿与正文，编辑页加载用）
  myArticle: (id) => http.get(`/blog/my/articles/${id}/`),
  createArticle: (data) => http.post('/blog/author/articles/', data),
  updateArticle: (id, data) => http.patch(`/blog/author/articles/${id}/`, data),
  deleteArticle: (id) => http.delete(`/blog/author/articles/${id}/`),
  // 评论
  postComment: (articleId, data) =>
    http.post(`/blog/articles/${articleId}/comments/`, data),
  pendingComments: () => http.get('/blog/comments/moderate/'),
  moderateComment: (id, action) =>
    http.post('/blog/comments/moderate/', { id, action }),
  autoModerate: (id) => http.post('/blog/comments/auto-moderate/', { id }),
}

// ---------------- AI 功能（创新点1） ----------------
export const aigcApi = {
  summary: (data) => http.post('/aigc/summary/', data),
  tags: (data) => http.post('/aigc/tags/', data),
  writer: (data) => http.post('/aigc/writer/', data),
  qa: (data) => http.post('/aigc/qa/', data),
  moderate: (data) => http.post('/aigc/moderate/', data),
  // AI 自动分类（优先复用现有分类，无合适才新建）
  classify: (data) => http.post('/aigc/classify/', data),
}

// ---------------- 统计面板 ----------------
export const statsApi = {
  overview: () => http.get('/stats/overview/'),
  trend: (days = 14) => http.get('/stats/trend/', { params: { days } }),
  categories: () => http.get('/stats/categories/'),
  hotArticles: () => http.get('/stats/hot-articles/'),
}

// ---------------- 系统配置（博主设置页） ----------------
export const sysconfApi = {
  getConfig: () => http.get('/sysconf/config/'),
  updateConfig: (data) => http.put('/sysconf/config/', data),
}
