// import request from '@/utils/request'
import { getToken } from '@/utils/auth'

// export function chatApi(data) {
//   return request({
//     url: '/api/ai/chat',
//     method: 'post',
//     data,
//     timeout: 60000
//   })
// }

export async function chatStreamApi(data, onEvent) {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  const token = getToken()

  const res = await fetch(`${baseUrl}/api/ai/chat/stream`, {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(data)
  })

  if (res.status === 401) {
    throw new Error('登录已失效，请重新登录')
  }

  if (!res.ok || !res.body) {
    throw new Error('流式接口请求失败')
  }
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('text/event-stream')) {
    throw new Error('流式接口返回异常')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')

  const dispatchEvent = (chunk) => {
    const data = chunk
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
      .trim()

    if (!data || data === '[DONE]') return

    let event
    try {
      event = JSON.parse(data)
    } catch {
      throw new Error('流式回复格式错误，请重试')
    }
    onEvent(event)
  }

  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })

      // 每次收到数据就处理完整事件，保留跨网络数据块的残余内容。
      const chunks = buffer.split(/\r?\n\r?\n/)
      buffer = chunks.pop()
      for (const chunk of chunks) dispatchEvent(chunk)

      if (done) {
        if (buffer.trim()) dispatchEvent(buffer)
        break
      }
    }
  } finally {
    reader.releaseLock()
  }
}
