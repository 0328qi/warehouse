import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** 按钮级权限指令：v-permission="'basic:goods:create'"，无权限时移除元素 */
export const permission: Directive<HTMLElement, string> = {
  mounted(el, binding) {
    const store = useAuthStore()
    if (binding.value && !store.hasPerm(binding.value)) {
      el.parentNode?.removeChild(el)
    }
  },
}
