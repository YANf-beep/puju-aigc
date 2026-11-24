<template>
  <div>
    <div class="create-head">
      <h2>我的作品</h2>
      <p>你保存到作品广场的全部创作</p>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!loading && items.length === 0" description="还没有保存过作品，去创作台生成一件吧">
        <el-button type="primary" @click="$router.push('/create')">去创作</el-button>
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

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)

async function load(p = 1) {
  page.value = p
  loading.value = true
  try {
    const data = await api.listWorks({ page: p, page_size: pageSize, mine: true })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(() => load(1))
</script>
