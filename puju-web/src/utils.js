/** 通用工具 */

/** 任务结果 → 可显示的图片src（外链或base64） */
export function resultImageSrc(r) {
  if (!r) return ''
  if (r.url) return r.url
  if (r.image_base64) return `data:image/png;base64,${r.image_base64}`
  return ''
}

export function formatDate(s) {
  if (!s) return ''
  return new Date(s).toLocaleString('zh-CN', { hour12: false })
}

/** 轮询生成任务，直到 succeeded / failed / 超时 */
export async function pollTask(getTask, taskId, { interval = 1500, timeout = 120000 } = {}) {
  const start = Date.now()
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const task = await getTask(taskId)
    if (task.status === 'succeeded' || task.status === 'failed') return task
    if (Date.now() - start > timeout) throw new Error('生成超时，请稍后重试')
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
}
