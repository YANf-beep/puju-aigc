<template>
  <div class="layout">
    <header class="topbar">
      <div class="topbar-inner">
        <router-link to="/" class="brand">
          <span class="brand-logo">🎭</span>
          <span class="brand-name">蒲韵<span class="brand-sub">· 蒲剧数字活化平台</span></span>
        </router-link>
        <nav class="nav">
          <router-link to="/">戏曲科普</router-link>
          <router-link to="/gallery">作品广场</router-link>
          <router-link to="/create">AI创作台</router-link>
          <router-link to="/mine">我的作品</router-link>
        </nav>
        <div class="user-area">
          <!-- 任务中心：进行中任务徽标，跨页面跟踪 -->
          <el-badge :value="taskCenter.activeCount" :hidden="taskCenter.activeCount === 0" class="task-badge">
            <el-button text circle @click="taskCenter.open()" title="创作任务中心">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>

          <el-dropdown v-if="auth.isLoggedIn" @command="onCommand">
            <span class="user-chip">
              <el-icon><User /></el-icon>
              {{ auth.user?.nickname || auth.user?.phone }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="mine">我的作品</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button v-else type="primary" round @click="$router.push('/login')">
            登录 / 注册
          </el-button>
        </div>
      </div>
    </header>

    <main class="page">
      <router-view />
    </main>

    <footer class="footer">
      蒲剧数字活化平台 · 毕业设计作品 ｜ 平台生成内容均为AI生成并已添加标识 ｜ 素材仅用于学术研究
    </footer>

    <!-- 任务中心抽屉：刷新/关页/重启后任务仍在 -->
    <el-drawer v-model="drawerVisible" title="创作任务中心" size="420px" @open="taskCenter.refresh()">
      <div class="tc-head">
        <span class="tc-tip">任务已持久化：可关闭页面，完成后在此保存到作品广场</span>
        <el-button size="small" text type="info" @click="taskCenter.clearFinished()">清除已完成</el-button>
      </div>
      <div v-if="taskCenter.tasks.length === 0" class="tc-empty">
        暂无任务，去 <router-link to="/create" @click="taskCenter.close()">AI创作台</router-link> 提交第一个创作吧
      </div>
      <div v-for="t in taskCenter.tasks" :key="t.task_id" class="tc-item">
        <div class="tc-row">
          <span class="tc-kind">{{ t.kind_label }}</span>
          <el-tag :type="statusType(t.status)" size="small">{{ statusText(t.status) }}</el-tag>
          <span class="tc-time">{{ formatDate(t.created_at) }}</span>
        </div>
        <div class="tc-prompt" :title="t.prompt">{{ t.prompt }}</div>

        <template v-if="t.status === 'succeeded'">
          <div class="tc-media">
            <video v-if="videoItem(t)" :src="videoItem(t).url" controls preload="metadata"></video>
            <el-image
              v-else-if="imageItem(t)"
              :src="imageItem(t).url"
              fit="cover"
              :preview-src-list="[imageItem(t).url]"
              preview-teleported
            />
            <div v-else-if="t.text" class="tc-text">{{ t.text.slice(0, 80) }}…</div>
          </div>
          <el-button size="small" type="primary" plain :disabled="savedIds.has(t.task_id)" @click="saveFromCenter(t)">
            {{ savedIds.has(t.task_id) ? '已保存' : '保存到作品广场' }}
          </el-button>
        </template>
        <div v-else-if="t.status === 'failed'" class="tc-error">{{ t.error }}</div>
        <div v-else class="tc-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          {{ t.kind === 'video' ? '视频生成中，通常需要2~5分钟，可以离开此页' : '生成中…' }}
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from './api'
import { auth } from './stores/auth'
import { taskCenter } from './stores/tasks'
import { formatDate } from './utils'

const router = useRouter()
const savedIds = reactive(new Set())

const drawerVisible = computed({
  get: () => taskCenter.drawer,
  set: (v) => (v ? taskCenter.open() : taskCenter.close()),
})

onMounted(() => {
  taskCenter.startPolling()
})

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/')
  } else {
    router.push('/' + cmd)
  }
}

function statusText(s) {
  return { pending: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[s] || s
}
function statusType(s) {
  return { pending: 'info', running: 'warning', succeeded: 'success', failed: 'danger' }[s] || 'info'
}
function imageItem(t) {
  return (t.items || []).find((i) => i.type === 'image')
}
function videoItem(t) {
  return (t.items || []).find((i) => i.type === 'video')
}

async function saveFromCenter(t) {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录再保存作品')
    router.push({ path: '/login', query: { redirect: '/create' } })
    return
  }
  let title
  try {
    const { value } = await ElMessageBox.prompt('给作品起个名字（可选）', '保存到作品广场', {
      inputValue: `${t.kind_label} · ${new Date().toLocaleDateString('zh-CN')}`,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    title = value
  } catch {
    return
  }
  try {
    await api.saveWork({ task_id: t.task_id, title })
    savedIds.add(t.task_id)
    ElMessage.success('已保存到作品广场')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>
