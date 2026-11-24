<template>
  <div class="login-wrap">
    <el-card class="login-card card-shadow">
      <h2>🎭 欢迎来到蒲韵</h2>

      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" placeholder="请输入11位手机号" maxlength="11" :prefix-icon="Iphone" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" type="password" show-password placeholder="至少6位" :prefix-icon="Lock" />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
              登 录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form ref="formRef" :model="form" :rules="registerRules" label-position="top" @keyup.enter="submit">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model="form.phone" placeholder="请输入11位手机号" maxlength="11" :prefix-icon="Iphone" />
            </el-form-item>
            <el-form-item label="昵称（可选）" prop="nickname">
              <el-input v-model="form.nickname" placeholder="不填则默认「戏迷+尾号」" maxlength="20" />
            </el-form-item>
            <el-form-item label="密码" prop="password">
              <el-input v-model="form.password" type="password" show-password placeholder="至少6位" :prefix-icon="Lock" />
            </el-form-item>
            <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
              注 册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <p class="login-tip">登录后可保存作品到广场、点赞与互动</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Lock } from '@element-plus/icons-vue'
import api from '../api'
import { auth } from '../stores/auth'

const route = useRoute()
const router = useRouter()

const mode = ref('login')
const formRef = ref()
const loading = ref(false)
const form = reactive({ phone: '', password: '', nickname: '' })

const phoneRule = [
  { required: true, message: '请输入手机号', trigger: 'blur' },
  { pattern: /^1\d{10}$/, message: '请输入正确的11位手机号', trigger: 'blur' },
]
const rules = {
  phone: phoneRule,
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '至少 6 位', trigger: 'blur' },
  ],
}
const registerRules = {
  ...rules,
  nickname: [{ max: 20, message: '昵称最多20个字符', trigger: 'blur' }],
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const payload = { phone: form.phone.trim(), password: form.password }
    if (mode.value === 'register') {
      payload.nickname = form.nickname.trim()
    }
    const fn = mode.value === 'login' ? api.login : api.register
    const data = await fn(payload)
    auth.setAuth(data.token, data.user)
    ElMessage.success(mode.value === 'login' ? '欢迎回来！' : '注册成功，欢迎加入！')
    router.push(String(route.query.redirect || '/'))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-tip {
  text-align: center;
  color: #9c8f85;
  font-size: 12px;
  margin: 14px 0 0;
}
</style>
