<template>
  <el-card class="work-card card-shadow" :body-style="{ padding: '0' }">
    <div class="work-media">
      <video
        v-if="work.media_type === 'video'"
        :src="work.url"
        class="work-video"
        controls
        preload="metadata"
      ></video>
      <el-image
        v-else-if="work.kind !== 'text'"
        :src="work.url"
        fit="cover"
        lazy
        :preview-src-list="[work.url]"
        preview-teleported
        class="work-img"
      />
      <div v-else class="work-text">{{ work.text }}</div>
      <span class="ai-badge">AI生成</span>
      <el-tag class="kind-tag" size="small" effect="dark">{{ work.kind_label }}</el-tag>
    </div>

    <div class="work-info">
      <div class="work-title">{{ work.title }}</div>
      <div class="work-meta">
        <span>@{{ work.username }}</span><span class="dot">·</span>
        <span>{{ formatDate(work.created_at) }}</span>
      </div>
      <div class="work-foot">
        <el-tooltip :content="work.prompt || '（无提示词）'" placement="top" :show-after="200">
          <span class="prompt-ellipsis">提示词：{{ work.prompt }}</span>
        </el-tooltip>
        <div>
          <el-button size="small" text :type="work.liked ? 'danger' : ''" @click="like">
            <el-icon style="vertical-align: -2px">
              <StarFilled v-if="work.liked" /><Star v-else />
            </el-icon>
            {{ work.like_count }}
          </el-button>
          <el-button v-if="isMine" size="small" text type="danger" @click="remove">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
import { auth } from '../stores/auth'
import { formatDate } from '../utils'

const props = defineProps({
  work: { type: Object, required: true },
})
const emit = defineEmits(['deleted'])

const isMine = computed(() => auth.user && props.work.username === (auth.user.nickname || auth.user.phone))

async function like() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('登录后即可点赞')
    return
  }
  try {
    const r = await api.likeWork(props.work.id)
    props.work.liked = r.liked
    props.work.like_count = r.like_count
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function remove() {
  try {
    await ElMessageBox.confirm(`确定删除作品「${props.work.title}」吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await api.deleteWork(props.work.id)
    ElMessage.success('已删除')
    emit('deleted')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>
