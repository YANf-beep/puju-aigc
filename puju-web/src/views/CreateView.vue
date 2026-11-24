<template>
  <div>
    <div class="create-head">
      <h2>AI 创作台</h2>
      <p>双层提示词机制：领域模板保证剧种专业度 · 自由描述释放你的创意 ｜ 任务已持久化，可同时提交多个创作，关闭页面也不丢失</p>
    </div>

    <el-tabs v-model="tab" class="create-tabs">
      <!-- ================= 插画生成 ================= -->
      <el-tab-pane label="🖼 戏曲插画" name="image">
        <div class="create-grid">
          <el-card class="card-shadow" header="创作参数">
            <div class="layer-title">第一层 · 领域模板</div>
            <el-form label-position="top">
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="行当">
                    <el-select v-model="imgForm.role">
                      <el-option v-for="v in tpl.roles" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="服饰">
                    <el-select v-model="imgForm.costume">
                      <el-option v-for="v in tpl.costumes" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="场景">
                    <el-select v-model="imgForm.scene">
                      <el-option v-for="v in tpl.scenes" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="神态">
                    <el-select v-model="imgForm.mood">
                      <el-option v-for="v in tpl.moods" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="layer-title">第二层 · 自由描述（创作者自设细节）</div>
              <el-input v-model="imgForm.free_text" type="textarea" :rows="3" maxlength="200" show-word-limit
                placeholder="例：手持马鞭做勒马式，目光炯炯，戏台楹联隐约可见" />
              <el-row :gutter="12" style="margin-top: 12px">
                <el-col :span="12">
                  <el-form-item label="尺寸">
                    <el-select v-model="imgForm.size">
                      <el-option v-for="s in tpl.sizes" :key="s" :label="s" :value="s" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="生成数量">
                    <el-slider v-model="imgForm.n" :min="1" :max="4" show-stops />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-button type="primary" size="large" class="gen-btn" :loading="imgLoading" @click="genImage">
                {{ imgLoading ? '生成中，请稍候…' : '🎨 生成戏曲插画' }}
              </el-button>
            </el-form>
          </el-card>

          <el-card class="card-shadow">
            <template #header>
              <div class="result-head">
                <span>生成结果</span>
                <el-tag v-if="imgStatus" :type="statusType(imgStatus)" size="small">{{ statusText(imgStatus) }}</el-tag>
              </div>
            </template>
            <div v-if="imgError" class="error-box">{{ imgError }}</div>
            <div v-if="imgItems.length" class="img-grid">
              <div v-for="(it, i) in imgItems" :key="i" class="img-item">
                <el-image :src="it.url" fit="contain" :preview-src-list="[it.url]" preview-teleported />
              </div>
            </div>
            <el-empty v-else-if="!imgLoading && !imgError" description="选择参数后点击生成" :image-size="80" />
            <div v-if="imgItems.length" class="save-bar">
              <el-input v-model="imgTitle" placeholder="给作品起个名字（可选）" style="max-width: 260px" />
              <el-button type="primary" plain :disabled="imgSaved" @click="saveWork('img')">
                {{ imgSaved ? '✓ 已保存到广场' : '保存到作品广场' }}
              </el-button>
            </div>
            <el-collapse v-if="imgPrompt" class="prompt-collapse">
              <el-collapse-item title="查看最终提示词（双层提示词机制）" name="p"><code>{{ imgPrompt }}</code></el-collapse-item>
            </el-collapse>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ================= 扮相转换 ================= -->
      <el-tab-pane label="👤 照片扮相转换" name="costume">
        <div class="create-grid">
          <el-card class="card-shadow" header="上传与参数">
            <el-upload drag class="cos-upload" :auto-upload="false" :limit="1" accept="image/*"
              :on-change="onFileChange" :on-remove="() => (cosFile = null)"
              :on-exceed="() => ElMessage.warning('只能上传一张照片，请先移除')">
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽照片到此处，或 <em>点击上传</em></div>
              <template #tip>
                <div class="el-upload__tip">jpg / png；转换将保留人物面部特征与姿态</div>
              </template>
            </el-upload>
            <el-form label-position="top" style="margin-top: 8px">
              <el-form-item label="目标行当">
                <el-select v-model="cosForm.role">
                  <el-option v-for="v in tpl.roles" :key="v" :label="v" :value="v" />
                </el-select>
              </el-form-item>
              <el-form-item label="补充细节（可选）">
                <el-input v-model="cosForm.free_text" placeholder="例：红色大靠，叉腰立正式" />
              </el-form-item>
              <el-button type="primary" size="large" class="gen-btn" :loading="cosLoading" :disabled="!cosFile" @click="genCostume">
                {{ cosLoading ? '转换中，请稍候…' : '🎭 生成扮相' }}
              </el-button>
            </el-form>
          </el-card>

          <el-card class="card-shadow">
            <template #header>
              <div class="result-head">
                <span>转换结果</span>
                <el-tag v-if="cosStatus" :type="statusType(cosStatus)" size="small">{{ statusText(cosStatus) }}</el-tag>
              </div>
            </template>
            <div v-if="cosError" class="error-box">{{ cosError }}</div>
            <div v-if="cosItems.length || originalUrl" class="compare-grid">
              <div class="col"><el-image v-if="originalUrl" :src="originalUrl" fit="contain" /></div>
              <div class="col">
                <el-image v-if="cosItems.length" :src="cosItems[0].url" fit="contain"
                  :preview-src-list="[cosItems[0].url]" preview-teleported />
              </div>
            </div>
            <el-empty v-else-if="!cosLoading && !cosError" description="上传照片后点击生成，编辑前 / 编辑后将在此对比展示" :image-size="80" />
            <div v-if="cosItems.length" class="save-bar">
              <el-input v-model="cosTitle" placeholder="给作品起个名字（可选）" style="max-width: 260px" />
              <el-button type="primary" plain :disabled="cosSaved" @click="saveWork('cos')">
                {{ cosSaved ? '✓ 已保存到广场' : '保存到作品广场' }}
              </el-button>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ================= 短视频生成 ================= -->
      <el-tab-pane label="🎬 短视频生成" name="video">
        <div class="create-grid">
          <el-card class="card-shadow" header="创作参数">
            <div class="layer-title">第一层 · 领域模板</div>
            <el-form label-position="top">
              <el-row :gutter="12">
                <el-col :span="12">
                  <el-form-item label="行当">
                    <el-select v-model="vidForm.role">
                      <el-option v-for="v in tpl.roles" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="服饰">
                    <el-select v-model="vidForm.costume">
                      <el-option v-for="v in tpl.costumes" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="场景">
                    <el-select v-model="vidForm.scene">
                      <el-option v-for="v in tpl.scenes" :key="v" :label="v" :value="v" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="时长">
                    <el-radio-group v-model="vidForm.duration">
                      <el-radio-button :value="5">5秒</el-radio-button>
                      <el-radio-button :value="10">10秒</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="layer-title">第二层 · 动态描述（画面怎么动）</div>
              <el-input v-model="vidForm.free_text" type="textarea" :rows="3" maxlength="200" show-word-limit
                placeholder="例：演员缓步登台亮相，甩袖转身，靠旗猎猎作响，最后定格亮相" />
              <el-form-item label="分辨率" style="margin-top: 12px">
                <el-radio-group v-model="vidForm.resolution">
                  <el-radio-button value="720p">720p（便宜）</el-radio-button>
                  <el-radio-button value="1080p">1080p</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="首帧参考图（可选，图生视频）">
                <el-upload :auto-upload="false" :limit="1" accept="image/*" :show-file-list="true"
                  :on-change="onVidFrameChange" :on-remove="() => (vidFrame = null)">
                  <el-button>选择图片（≤5MB）</el-button>
                  <template #tip>
                    <div class="el-upload__tip">以该图为视频首帧；不选则纯文生视频</div>
                  </template>
                </el-upload>
              </el-form-item>
              <el-button type="primary" size="large" class="gen-btn" :loading="vidLoading" @click="genVideo">
                {{ vidLoading ? '生成中…' : '🎬 生成短视频' }}
              </el-button>
              <div class="vid-tip">视频生成通常需要 2~5 分钟；提交后可以离开此页，到右上角「任务中心」查看进度。</div>
            </el-form>
          </el-card>

          <el-card class="card-shadow">
            <template #header>
              <div class="result-head">
                <span>生成结果</span>
                <el-tag v-if="vidStatus" :type="statusType(vidStatus)" size="small">{{ statusText(vidStatus) }}</el-tag>
              </div>
            </template>
            <div v-if="vidError" class="error-box">{{ vidError }}</div>
            <div v-if="vidVideoUrl" class="vid-result">
              <video :src="vidVideoUrl" controls preload="metadata"></video>
            </div>
            <div v-else-if="vidStatus === 'running' || vidStatus === 'pending'" class="vid-waiting">
              <el-icon class="is-loading" :size="28"><Loading /></el-icon>
              <p>视频生成中（预计2~5分钟），可离开此页<br/>进度也可在右上角「任务中心」查看</p>
            </div>
            <el-empty v-else-if="!vidLoading && !vidError" description="设置参数后点击生成" :image-size="80" />
            <div v-if="vidVideoUrl" class="save-bar">
              <el-input v-model="vidTitle" placeholder="给作品起个名字（可选）" style="max-width: 260px" />
              <el-button type="primary" plain :disabled="vidSaved" @click="saveWork('vid')">
                {{ vidSaved ? '✓ 已保存到广场' : '保存到作品广场' }}
              </el-button>
            </div>
            <el-collapse v-if="vidPrompt" class="prompt-collapse">
              <el-collapse-item title="查看最终提示词（双层提示词机制）" name="p"><code>{{ vidPrompt }}</code></el-collapse-item>
            </el-collapse>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ================= 文案生成 ================= -->
      <el-tab-pane label="✍ 戏曲文案" name="text">
        <div class="create-grid">
          <el-card class="card-shadow" header="创作参数">
            <el-form label-position="top">
              <el-form-item label="主题">
                <el-input v-model="txtForm.subject" placeholder="例：蒲剧《挂画》的艺术特色" />
              </el-form-item>
              <el-form-item label="文体">
                <el-select v-model="txtForm.style">
                  <el-option v-for="v in tpl.copy_styles" :key="v" :label="v" :value="v" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-switch v-model="txtForm.use_rag" active-text="启用领域知识库检索（RAG）" />
              </el-form-item>
              <el-button type="primary" size="large" class="gen-btn" :loading="txtLoading"
                :disabled="!txtForm.subject.trim()" @click="genText">
                {{ txtLoading ? '生成中，请稍候…' : '✍️ 生成文案' }}
              </el-button>
            </el-form>
            <el-collapse v-if="knowledgeUsed.length" class="prompt-collapse">
              <el-collapse-item :title="`📚 检索到 ${knowledgeUsed.length} 条领域知识（已注入提示词）`" name="k">
                <p v-for="(k, i) in knowledgeUsed" :key="i" class="kn-snippet">{{ k }}</p>
              </el-collapse-item>
            </el-collapse>
          </el-card>

          <el-card class="card-shadow">
            <template #header>
              <div class="result-head">
                <span>生成结果</span>
                <el-tag v-if="txtStatus" :type="statusType(txtStatus)" size="small">{{ statusText(txtStatus) }}</el-tag>
              </div>
            </template>
            <div v-if="txtError" class="error-box">{{ txtError }}</div>
            <div v-if="txtResult" class="text-result">{{ txtResult }}</div>
            <el-empty v-else-if="!txtLoading && !txtError" description="输入主题后点击生成" :image-size="80" />
            <div v-if="txtResult" class="save-bar">
              <el-button @click="copyText"><el-icon><CopyDocument /></el-icon>&nbsp;复制文案</el-button>
              <el-input v-model="txtTitle" placeholder="作品名（可选）" style="max-width: 220px" />
              <el-button type="primary" plain :disabled="txtSaved" @click="saveWork('txt')">
                {{ txtSaved ? '✓ 已保存到广场' : '保存到作品广场' }}
              </el-button>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { auth } from '../stores/auth'
import { taskCenter } from '../stores/tasks'
import { pollTask } from '../utils'

const router = useRouter()
const tab = ref('image')

const tpl = reactive({
  roles: ['生', '旦', '净', '丑'],
  costumes: ['蟒袍', '靠甲', '褶子', '女帔', '箭衣'],
  scenes: ['舞台', '古戏台', '写意', '乡野社戏'],
  moods: ['威武', '柔美', '诙谐', '悲怆'],
  copy_styles: ['科普短文', '唱词文案', '剧目介绍', '宣传文案'],
  sizes: ['2K', '4K'],
})

onMounted(async () => {
  try {
    const data = await api.templates()
    Object.assign(tpl, data)
  } catch {
    /* 下发失败时使用默认值 */
  }
})

function statusText(s) {
  return { pending: '排队中', running: '生成中', succeeded: '已完成', failed: '失败' }[s] || s
}
function statusType(s) {
  return { pending: 'info', running: 'warning', succeeded: 'success', failed: 'danger' }[s] || 'info'
}

// ---------- 插画 ----------
const imgForm = reactive({ role: '净', costume: '蟒袍', scene: '舞台', mood: '威武', free_text: '', size: '2K', n: 1 })
const imgLoading = ref(false)
const imgError = ref('')
const imgItems = ref([])
const imgStatus = ref('')
const imgTaskId = ref('')
const imgPrompt = ref('')
const imgTitle = ref('')
const imgSaved = ref(false)

async function genImage() {
  imgLoading.value = true
  imgError.value = ''
  imgItems.value = []
  imgSaved.value = false
  try {
    const resp = await api.generateImage({ ...imgForm })
    imgTaskId.value = resp.task_id
    imgPrompt.value = resp.prompt
    imgStatus.value = 'pending'
    taskCenter.rememberTask(resp.task_id)
    const task = await pollTask(api.getTask, resp.task_id)
    imgStatus.value = task.status
    if (task.status === 'failed') throw new Error(task.error || '生成失败')
    imgItems.value = (task.items || []).filter((i) => i.type === 'image')
  } catch (e) {
    imgError.value = e.message
    imgStatus.value = 'failed'
  } finally {
    imgLoading.value = false
  }
}

// ---------- 扮相 ----------
const cosFile = ref(null)
const originalUrl = ref('')
const cosForm = reactive({ role: '净', free_text: '' })
const cosLoading = ref(false)
const cosError = ref('')
const cosItems = ref([])
const cosStatus = ref('')
const cosTaskId = ref('')
const cosTitle = ref('')
const cosSaved = ref(false)

function onFileChange(uploadFile) {
  cosFile.value = uploadFile.raw
  if (originalUrl.value) URL.revokeObjectURL(originalUrl.value)
  originalUrl.value = URL.createObjectURL(uploadFile.raw)
}

async function genCostume() {
  if (!cosFile.value) return
  cosLoading.value = true
  cosError.value = ''
  cosItems.value = []
  cosSaved.value = false
  try {
    const form = new FormData()
    form.append('image', cosFile.value)
    form.append('role', cosForm.role)
    form.append('free_text', cosForm.free_text)
    const resp = await api.generateCostume(form)
    cosTaskId.value = resp.task_id
    cosStatus.value = 'pending'
    taskCenter.rememberTask(resp.task_id)
    const task = await pollTask(api.getTask, resp.task_id)
    cosStatus.value = task.status
    if (task.status === 'failed') throw new Error(task.error || '转换失败')
    cosItems.value = (task.items || []).filter((i) => i.type === 'image')
  } catch (e) {
    cosError.value = e.message
    cosStatus.value = 'failed'
  } finally {
    cosLoading.value = false
  }
}

// ---------- 短视频 ----------
const vidForm = reactive({ role: '净', costume: '靠甲', scene: '舞台', free_text: '', duration: 10, resolution: '720p' })
const vidFrame = ref(null) // { raw, b64 }
const vidLoading = ref(false)
const vidError = ref('')
const vidStatus = ref('')
const vidTaskId = ref('')
const vidPrompt = ref('')
const vidTitle = ref('')
const vidSaved = ref(false)
const vidVideoUrl = ref('')

function onVidFrameChange(uploadFile) {
  const raw = uploadFile.raw
  if (raw.size > 5 * 1024 * 1024) {
    ElMessage.warning('首帧图请控制在5MB以内')
    vidFrame.value = null
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const b64 = String(reader.result).split(',')[1] || ''
    vidFrame.value = { raw, b64 }
  }
  reader.readAsDataURL(raw)
}

async function genVideo() {
  vidLoading.value = true
  vidError.value = ''
  vidVideoUrl.value = ''
  vidSaved.value = false
  try {
    const payload = { ...vidForm }
    if (vidFrame.value) payload.first_frame_b64 = vidFrame.value.b64
    const resp = await api.generateVideo(payload)
    vidTaskId.value = resp.task_id
    vidPrompt.value = resp.prompt
    vidStatus.value = 'pending'
    taskCenter.rememberTask(resp.task_id)
    ElMessage({ message: '视频任务已提交，可离开此页，稍后在右上角任务中心查看', type: 'success', duration: 4000 })
    const task = await pollTask(api.getTask, resp.task_id, { interval: 5000, timeout: 600000 })
    vidStatus.value = task.status
    if (task.status === 'failed') throw new Error(task.error || '生成失败')
    const video = (task.items || []).find((i) => i.type === 'video')
    vidVideoUrl.value = video ? video.url : ''
    if (!vidVideoUrl.value) throw new Error('未取得视频文件')
  } catch (e) {
    vidError.value = e.message
    vidStatus.value = 'failed'
  } finally {
    vidLoading.value = false
  }
}

// ---------- 文案 ----------
const txtForm = reactive({ subject: '', style: '科普短文', use_rag: true })
const txtLoading = ref(false)
const txtError = ref('')
const txtResult = ref('')
const txtStatus = ref('')
const txtTaskId = ref('')
const txtTitle = ref('')
const txtSaved = ref(false)
const knowledgeUsed = ref([])

async function genText() {
  txtLoading.value = true
  txtError.value = ''
  txtResult.value = ''
  txtSaved.value = false
  knowledgeUsed.value = []
  try {
    const resp = await api.generateText({ ...txtForm })
    txtTaskId.value = resp.task_id
    knowledgeUsed.value = resp.knowledge_used || []
    txtStatus.value = 'pending'
    taskCenter.rememberTask(resp.task_id)
    const task = await pollTask(api.getTask, resp.task_id)
    txtStatus.value = task.status
    if (task.status === 'failed') throw new Error(task.error || '生成失败')
    txtResult.value = task.text || ''
  } catch (e) {
    txtError.value = e.message
    txtStatus.value = 'failed'
  } finally {
    txtLoading.value = false
  }
}

async function copyText() {
  try {
    await navigator.clipboard.writeText(txtResult.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}

// ---------- 保存作品（需登录） ----------
async function saveWork(which) {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录再保存作品')
    router.push({ path: '/login', query: { redirect: '/create' } })
    return
  }
  const conf = {
    img: { taskId: imgTaskId, title: imgTitle, saved: imgSaved },
    cos: { taskId: cosTaskId, title: cosTitle, saved: cosSaved },
    vid: { taskId: vidTaskId, title: vidTitle, saved: vidSaved },
    txt: { taskId: txtTaskId, title: txtTitle, saved: txtSaved },
  }[which]
  if (!conf.taskId.value) return
  try {
    await api.saveWork({ task_id: conf.taskId.value, title: conf.title.value })
    conf.saved.value = true
    ElMessage.success('已保存到作品广场')
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>

<style scoped>
.kn-snippet {
  margin: 0 0 8px;
  font-size: 13px;
  color: #5c5248;
  line-height: 1.7;
  border-left: 3px solid var(--el-color-primary-light-5);
  padding-left: 10px;
}
.vid-tip {
  margin-top: 10px;
  font-size: 12.5px;
  color: #9c8f85;
  line-height: 1.6;
}
.vid-result video {
  width: 100%;
  max-height: 460px;
  border-radius: 10px;
  background: #000;
}
.vid-waiting {
  padding: 60px 0;
  text-align: center;
  color: #9c8f85;
}
.vid-waiting p { margin-top: 12px; font-size: 13px; line-height: 1.8; }
</style>
