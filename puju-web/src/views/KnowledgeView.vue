<template>
  <div>
    <!-- 顶部：轮播封面 + 平台入口 -->
    <section class="kn-hero card-shadow">
      <el-carousel height="340px" :interval="4500" arrow="hover" indicator-position="none">
        <el-carousel-item v-for="e in heroEntries" :key="`h${e.id}`">
          <div class="kn-hero-slide" :class="{ 'no-cover': !e.cover }" @click="openEntry(e)">
            <img v-if="e.cover" :src="e.cover" class="kn-hero-img" alt="" />
            <div v-else class="kn-hero-fallback"><span>{{ e.title.charAt(0) }}</span></div>
            <div class="kn-hero-caption">
              <h3>{{ e.title }}</h3>
              <p>{{ e.text.slice(0, 60) }}…</p>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
      <div class="kn-hero-cta">
        <h2>让蒲剧，在指尖重新登场</h2>
        <p>基于多模态AIGC的地方传统戏曲数字活化平台</p>
        <div>
          <el-button type="primary" size="large" round @click="$router.push('/create')">
            <el-icon><MagicStick /></el-icon>&nbsp;用AI创作蒲剧作品
          </el-button>
          <el-button size="large" round plain @click="$router.push('/gallery')">逛逛作品广场</el-button>
        </div>
      </div>
    </section>

    <!-- 搜索 -->
    <div class="kn-toolbar">
      <h2>戏曲科普知识库</h2>
      <el-input
        v-model="q"
        placeholder="搜索：脸谱 / 唱腔 / 名家 / 剧目…"
        clearable
        style="max-width: 380px"
        @keyup.enter="load"
        @clear="load"
      >
        <template #append>
          <el-button @click="load"><el-icon><Search /></el-icon></el-button>
        </template>
      </el-input>
    </div>

    <!-- 知识卡片：封面 + 文案 + 视频 -->
    <div v-loading="loading">
      <el-row :gutter="18">
        <el-col v-for="e in entries" :key="e.id" :xs="24" :sm="12" :md="8" :lg="6">
          <el-card class="kn-card card-shadow" :body-style="{ padding: '0' }">
            <div class="kn-cover" @click="openEntry(e)">
              <img v-if="e.cover" :src="e.cover" alt="" />
              <div v-else class="kn-cover-fallback"><span>{{ e.title.charAt(0) }}</span></div>
              <el-tag v-if="e.video" class="kn-video-tag" effect="dark" size="small">📺 视频</el-tag>
            </div>
            <div class="kn-body">
              <h3>{{ e.title }}</h3>
              <p>{{ e.text }}</p>
              <div class="kn-actions">
                <el-button size="small" type="primary" text @click="watch(e)">
                  {{ e.video ? '▶ 播放视频' : '▶ B站看相关视频' }}
                </el-button>
                <el-upload
                  :auto-upload="false"
                  :show-file-list="false"
                  accept="image/*,video/mp4"
                  :on-change="(f) => uploadMedia(e, f)"
                >
                  <el-button size="small" text type="info">⬆ 上传素材</el-button>
                </el-upload>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!loading && entries.length === 0" description="没有找到相关知识，换个关键词试试" />
    </div>

    <!-- 视频播放弹窗 -->
    <el-dialog v-model="videoVisible" :title="playingEntry?.title" width="680px" destroy-on-close>
      <video
        v-if="playingEntry?.video"
        :src="playingEntry.video"
        controls
        autoplay
        style="width: 100%; border-radius: 8px; background: #000"
      ></video>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const q = ref('')
const entries = ref([])
const loading = ref(false)
const videoVisible = ref(false)
const playingEntry = ref(null)

const heroEntries = computed(() => entries.value.slice(0, 6))

async function load() {
  loading.value = true
  try {
    const data = await api.knowledge(q.value)
    entries.value = data.items
  } finally {
    loading.value = false
  }
}

function openEntry(e) {
  if (e.video) {
    playingEntry.value = e
    videoVisible.value = true
  } else if (e.video_link) {
    window.open(e.video_link, '_blank')
  }
}

function watch(e) {
  if (e.video) {
    playingEntry.value = e
    videoVisible.value = true
  } else if (e.video_link) {
    window.open(e.video_link, '_blank')
  }
}

async function uploadMedia(entry, uploadFile) {
  if (!uploadFile?.raw) return
  try {
    await api.uploadKnowledgeMedia(entry.id, uploadFile.raw)
    ElMessage.success(`已为「${entry.title}」更新素材`)
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.kn-toolbar { display: flex; align-items: center; justify-content: space-between; margin: 22px 0 16px; flex-wrap: wrap; gap: 10px; }
.kn-toolbar h2 { margin: 0; }

.kn-card { margin-bottom: 18px; overflow: hidden; }
.kn-cover { position: relative; height: 150px; background: #f1e8df; overflow: hidden; cursor: pointer; }
.kn-cover img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.35s; }
.kn-cover:hover img { transform: scale(1.06); }
.kn-cover-fallback {
  width: 100%; height: 100%;
  background: linear-gradient(135deg, #8f2f25, #b23a2e 60%, #c8552f);
  display: flex; align-items: center; justify-content: center;
}
.kn-cover-fallback span { color: rgba(255,255,255,0.85); font-size: 56px; font-family: 'Kaiti SC', 'KaiTi', serif; }
.kn-video-tag { position: absolute; right: 8px; top: 8px; }
.kn-body { padding: 12px 14px 10px; }
.kn-body h3 { margin: 0 0 6px; font-size: 15px; color: var(--el-color-primary); }
.kn-body p {
  margin: 0; font-size: 12.5px; color: #5c5248; line-height: 1.7;
  height: 63px; overflow: hidden; display: -webkit-box;
  -webkit-line-clamp: 3; -webkit-box-orient: vertical;
}
.kn-actions { display: flex; justify-content: space-between; margin-top: 8px; border-top: 1px dashed #eee2d8; padding-top: 6px; }
</style>
