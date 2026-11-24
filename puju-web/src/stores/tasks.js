/** 任务中心状态（持久化任务的全局跟踪）：
 *  任务在后端落库，浏览器只记 task_id 列表（localStorage），
 *  刷新/关页/重启后回来仍能看到进行中的任务与已完成的结果。 */
import { computed, reactive } from 'vue'
import api from '../api'

const KEY = 'puju_task_ids'

function localIds() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

function rememberId(id) {
  const ids = localIds()
  if (!ids.includes(id)) {
    ids.unshift(id)
    localStorage.setItem(KEY, JSON.stringify(ids.slice(0, 100)))
  }
}

async function refresh() {
  try {
    const data = await api.listTasks(localIds())
    state.tasks = data.items
    state.loaded = true
  } catch {
    /* 网络异常时静默，下轮重试 */
  }
}

const state = reactive({
  tasks: [],
  loaded: false,
  drawer: false,
  timer: null,
})

export const taskCenter = reactive({
  tasks: computed(() => state.tasks),
  drawer: computed(() => state.drawer),
  activeCount: computed(
    () => state.tasks.filter((t) => t.status === 'pending' || t.status === 'running').length
  ),
  /** 提交任务后调用：记入本浏览器并稍后刷新列表 */
  rememberTask(id) {
    rememberId(id)
    setTimeout(() => refresh(), 800)
  },
  async open() {
    state.drawer = true
    await refresh()
  },
  close() {
    state.drawer = false
  },
  /** 清除已完成任务的本地记录（后端任务仍在，登录后仍可见） */
  clearFinished() {
    const remain = state.tasks
      .filter((t) => t.status === 'pending' || t.status === 'running')
      .map((t) => t.task_id)
    localStorage.setItem(KEY, JSON.stringify(remain))
    refresh()
  },
  /** 有进行中任务或面板打开时轮询（App.vue 挂载时调用一次） */
  startPolling() {
    if (state.timer) return
    state.timer = setInterval(async () => {
      const hasActive = state.tasks.some((t) => t.status === 'pending' || t.status === 'running')
      if (hasActive || state.drawer || !state.loaded) await refresh()
    }, 5000)
    refresh()
  },
  refresh,
})
