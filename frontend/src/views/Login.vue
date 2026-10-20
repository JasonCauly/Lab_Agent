<template>
  <div class="login-container">
    <div class="login-box">
      <h1 style="font-size: 28px">实验室预约系统</h1>
      <div style="margin-top: 5px; margin-bottom: 30px">基于Agent智能预约系统</div>
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-width="0px"
        style="width: 100%"
        @submit.prevent="login"
      >
        <el-form-item prop="username">
          <el-input
            size="large"
            v-model="form.username"
            placeholder="请输入账号"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            type="password"
            size="large"
            v-model="form.password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <div>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            native-type="submit"
            :loading="loadingValue"
            >登 录</el-button
          >
          <div style="text-align: right; margin-top: 20px; padding-right: 15px">
            还没有账号？请<router-link style="color: var(--el-color-primary)" to="/register"
              >注册</router-link
            >
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'
const router = useRouter()
const { saveLoginData } = useUser()

const formRef = ref()

const rules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' }
    // { min: 3, max: 20, message: '账号长度在3到20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
    // { min: 6, max: 20, message: '密码长度在6到20个字符之间', trigger: 'blur' }
  ]
}

const form = reactive({
  username: '',
  password: ''
})

const loadingValue = ref(false)

const login = async () => {
  if (loadingValue.value) return
  loadingValue.value = true
  try {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
    const res = await loginApi(form)
    if (res.code === 200) {
      saveLoginData(res.data)
      try {
        const failure = await router.replace('/manager/home')
        if (router.currentRoute.value.path === '/manager/home') {
          ElMessage.success('登录成功')
        } else {
          console.error('登录后跳转首页未完成:', failure)
          ElMessage.error('首页跳转未完成，请重试')
        }
      } catch (error) {
        console.error('登录后加载首页失败:', error)
        ElMessage.error('首页加载失败，请刷新页面后重试')
      }
    }
  } catch {
    // 登录请求失败时由请求拦截器提示错误。
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.login-box {
  width: 380px;
  border-radius: 8px;
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  text-align: center;
}
</style>
