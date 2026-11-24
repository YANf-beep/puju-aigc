import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../stores/auth'
import KnowledgeView from '../views/KnowledgeView.vue'
import HomeView from '../views/HomeView.vue'
import CreateView from '../views/CreateView.vue'
import MyWorksView from '../views/MyWorksView.vue'
import LoginView from '../views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'knowledge', component: KnowledgeView },       // 首页 = 戏曲科普
    { path: '/gallery', name: 'gallery', component: HomeView },       // 作品广场
    { path: '/create', name: 'create', component: CreateView },
    { path: '/mine', name: 'mine', component: MyWorksView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
