<template>
  <div>
    <section class="hero">
      <h1>让蒲剧，在指尖重新登场</h1>
      <p>基于多模态AIGC的地方传统戏曲数字活化平台 —— 零基础创作戏曲插画、扮相与文案</p>
      <div class="hero-actions">
        <el-button size="large" round @click="$router.push('/create')">
          <el-icon><MagicStick /></el-icon>&nbsp;去创作
        </el-button>
        <el-button size="large" round plain @click="$router.push('/knowledge')">
          逛逛戏曲科普
        </el-button>
      </div>
    </section>

    <div class="gallery-head">
      <el-tabs v-model="kind" @tab-change="load(1)">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane label="戏曲插画" name="image" />
        <el-tab-pane label="扮相转换" name="costume" />
        <el-tab-pane label="短视频" name="video" />
        <el-tab-pane label="戏曲文案" name="text" />
      </el-tabs>
      <span class="total">共 {{ total }} 件作品</span>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && items.length === 0" description="广场上还没有作品，去创作第一件吧">
        <el-button type="primary" @click="$router.push('/create')">立即创作</el-button>
      </el-empty>
      <div class="works-grid">
        <WorkCard v-for="w in items" :key="w.id" :work="w" @deleted="load(page)" />
      </div>
    </div>

    <div class="pager">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'
import WorkCard from '../components/WorkCard.vue'

const kind = ref('')
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)

async function load(p = 1) {
  page.value = p
  loading.value = true
  try {
    const data = await api.listWorks({ kind: kind.value, page: p, page_size: pageSize })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => load(1))
</script>
