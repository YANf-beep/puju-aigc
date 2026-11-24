/** 后端 API 封装（全部走 /api，开发经 vite 代理，生产与后端同源） */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { auth } from '../stores/auth'

const http = axios.create({ baseURL: '/api', timeout: 60000 })

http.interceptors.request.use((cfg) => {
  if (auth.token) cfg.headers.Authorization = `Bearer ${auth.token}`
  return cfg
})

http.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const raw = err.response?.data?.detail || err.message || '请求失败'
    const msg = typeof raw === 'string' ? raw : JSON.stringify(raw)
    if (err.response?.status === 401 && auth.isLoggedIn) {
      auth.logout()
      ElMessage.error('登录已过期，请重新登录')
    }
    return Promise.reject(new Error(msg))
  }
)

export default {
  // ---- 模板选项（双层提示词第一层的取值，由后端统一下发） ----
  templates: () => http.get('/templates').then((r) => r.data),

  // ---- 生成任务（提交即返回，结果走任务中心轮询） ----
  generateImage: (data) => http.post('/generate/image', data).then((r) => r.data),
  generateCostume: (form) =>
    http.post('/generate/costume', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data),
  generateText: (data) => http.post('/generate/text', data).then((r) => r.data),
  generateVideo: (data) => http.post('/generate/video', data).then((r) => r.data),
  getTask: (id) => http.get(`/tasks/${id}`).then((r) => r.data),
  listTasks: (ids) => http.post('/tasks/list', { ids }).then((r) => r.data),

  // ---- 作品 ----
  listWorks: (params) => http.get('/works', { params }).then((r) => r.data),
  saveWork: (data) => http.post('/works', data).then((r) => r.data),
  likeWork: (id) => http.post(`/works/${id}/like`).then((r) => r.data),
  deleteWork: (id) => http.delete(`/works/${id}`).then((r) => r.data),

  // ---- 知识库（富媒体） ----
  knowledge: (q) => http.get('/knowledge', { params: { q } }).then((r) => r.data),
  uploadKnowledgeMedia: (entryId, file) => {
    const form = new FormData()
    form.append('file', file)
    return http
      .post(`/knowledge/${entryId}/media`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
      .then((r) => r.data)
  },

  // ---- 认证（手机号） ----
  register: (d) => http.post('/auth/register', d).then((r) => r.data),
  login: (d) => http.post('/auth/login', d).then((r) => r.data),
}
