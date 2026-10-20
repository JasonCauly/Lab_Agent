// 存储token、用户信息, 获取token、用户信息, 删除token、用户信息
const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'
let authVersion = 0

export function getAuthVersion() {
  return authVersion
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
  authVersion++
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  authVersion++
}

export function getUserInfo() {
  const str = localStorage.getItem(USER_KEY)
  if (!str) return null

  try {
    return JSON.parse(str)
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export function setUserInfo(userInfo) {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

// 登出
export function logout() {
  removeToken()
  removeUserInfo()
}
