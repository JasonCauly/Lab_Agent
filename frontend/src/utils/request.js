import axios from 'axios'
import { getAuthVersion, getToken, logout } from './auth'
import router from '@/router'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000 // 30s
})

const handleUnauthorized = (config, message) => {
  // 旧会话的请求失败，不能使重新登录后的会话失效。
  if (config?._authVersion !== getAuthVersion()) return
  const token = getToken()
  if (token && config.headers?.Authorization !== `Bearer ${token}`) return
  ElMessage.error(message)
  if (token) {
    logout()
    router.replace('/login')
  }
}

// 请求的拦截器的配置
service.interceptors.request.use(
  (config) => {
    const token = getToken()
    config._authVersion = getAuthVersion()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// 返回的拦截器配置
service.interceptors.response.use(
  (res) => {
    const data = res.data
    console.log('response:', res)
    if (data.code === 401) {
      handleUnauthorized(res.config, data.message || '登录已过期，请重新登录')
      return Promise.reject(data)
    }
    if (data.code !== 200) {
      ElMessage.error(data.message || '请求失败')
    }
    return data
  },
  (err) => {
    if (err.response) {
      const httpStatusCode = err.response.status
      if (httpStatusCode === 401) {
        handleUnauthorized(err.config, err.response.data?.message || '登录已过期，请重新登录')
      } else {
        ElMessage.error(err.response.data?.message || '请求失败')
      }
    } else {
      ElMessage.error('网络异常，请检查后端服务')
    }
    return Promise.reject(err)
  }
)

export default service
