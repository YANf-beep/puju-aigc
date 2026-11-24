/** 用户登录态（简单响应式存储 + localStorage 持久化） */
import { reactive } from 'vue'

const state = reactive({
  token: localStorage.getItem('puju_token') || '',
  user: JSON.parse(localStorage.getItem('puju_user') || 'null'),
})

export const auth = {
  get token() { return state.token },
  get user() { return state.user },
  get isLoggedIn() { return !!state.token },
  setAuth(token, user) {
    state.token = token
    state.user = user
    localStorage.setItem('puju_token', token)
    localStorage.setItem('puju_user', JSON.stringify(user))
  },
  logout() {
    state.token = ''
    state.user = null
    localStorage.removeItem('puju_token')
    localStorage.removeItem('puju_user')
  },
}
