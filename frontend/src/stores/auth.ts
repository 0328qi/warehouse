import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMe, login as loginApi } from '@/api/modules'
import router from '@/router'

export interface UserInfo {
  id: number
  username: string
  nickname: string
  is_super: boolean
  perm_codes: string[]
  menus: any[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('wms_token') || '')
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem('wms_user') || 'null'))
  const perms = ref<string[]>(user.value?.perm_codes || [])

  async function login(username: string, password: string) {
    const res: any = await loginApi({ username, password })
    token.value = res.access_token
    localStorage.setItem('wms_token', token.value)
    await fetchMe()
  }

  async function fetchMe() {
    const info: any = await getMe()
    user.value = info
    perms.value = info.perm_codes || []
    localStorage.setItem('wms_user', JSON.stringify(info))
  }

  function logout() {
    token.value = ''
    user.value = null
    perms.value = []
    localStorage.removeItem('wms_token')
    localStorage.removeItem('wms_user')
    router.push('/login')
  }

  function hasPerm(code: string): boolean {
    if (!code) return true
    if (perms.value.includes('*')) return true
    return perms.value.includes(code)
  }

  return { token, user, perms, login, fetchMe, logout, hasPerm }
})
