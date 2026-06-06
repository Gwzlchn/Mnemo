import { ref } from 'vue'

class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API ${status}: ${body}`)
  }
}

const authToken = ref(localStorage.getItem('auth_token') || '')
const needsLogin = ref(!authToken.value && !!import.meta.env.PROD)

export function setToken(token: string) {
  authToken.value = token
  localStorage.setItem('auth_token', token)
  needsLogin.value = false
}

export function clearToken() {
  authToken.value = ''
  localStorage.removeItem('auth_token')
  needsLogin.value = true
}

export function useAuth() {
  return { authToken, needsLogin, setToken, clearToken }
}

export function useApi() {
  async function request<T>(method: string, path: string, body?: any): Promise<T> {
    const headers: Record<string, string> = {}
    if (authToken.value) {
      headers['Authorization'] = `Bearer ${authToken.value}`
    }
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const resp = await fetch(path, {
      method,
      headers,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    })

    if (resp.status === 401) {
      clearToken()
      throw new ApiError(401, 'unauthorized')
    }
    if (!resp.ok) {
      throw new ApiError(resp.status, await resp.text())
    }
    if (resp.status === 204) return null as T
    return resp.json()
  }

  async function getText(path: string): Promise<string> {
    const headers: Record<string, string> = {}
    if (authToken.value) {
      headers['Authorization'] = `Bearer ${authToken.value}`
    }
    const resp = await fetch(path, { headers })
    if (resp.status === 401) {
      clearToken()
      throw new ApiError(401, 'unauthorized')
    }
    if (!resp.ok) throw new ApiError(resp.status, await resp.text())
    return resp.text()
  }

  return {
    get: <T>(path: string) => request<T>('GET', path),
    post: <T>(path: string, body?: any) => request<T>('POST', path, body),
    put: <T>(path: string, body?: any) => request<T>('PUT', path, body),
    del: (path: string) => request<void>('DELETE', path),
    upload: <T>(path: string, formData: FormData) => request<T>('POST', path, formData),
    getText,
  }
}
