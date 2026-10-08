<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const store = useAuthStore()

// 由后端菜单树过滤出可见目录/页面，构建侧边栏
const menuItems = computed(() => {
  const menus = store.user?.menus || []
  const visible = menus.filter((m: any) => m.type === 'dir' || m.type === 'menu')
  const tops = visible.filter((m: any) => !m.parent_id)
  return tops
    .map((top: any) => ({
      ...top,
      children: visible.filter((m: any) => m.parent_id === top.id),
    }))
    .filter((top: any) => top.children.length > 0 || top.path)
    .sort((a: any, b: any) => a.sort - b.sort)
})

// 后端菜单没有 parent 关联 path，需要手动把子菜单 path 映射：菜单树 parent_id 对应 id
// 上面 children 过滤已经按 id 处理，此处仅为类型安全

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => (route.meta.title as string) || '')

async function handleLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  store.logout()
  ElMessage.success('已退出')
}
</script>

<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon size="24"><Box /></el-icon>
        <span>仓储管理系统</span>
      </div>
      <el-scrollbar>
        <el-menu :default-active="activeMenu" router background-color="#001529" text-color="#bfcbd9"
          active-text-color="#409eff" style="border-right: none">
          <template v-for="top in menuItems" :key="top.id">
            <el-sub-menu v-if="top.children.length" :index="String(top.id)">
              <template #title>
                <el-icon v-if="top.icon"><component :is="top.icon" /></el-icon>
                <span>{{ top.name }}</span>
              </template>
              <el-menu-item v-for="child in top.children" :key="child.id" :index="child.path">
                {{ child.name }}
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="top.path">
              <el-icon v-if="top.icon"><component :is="top.icon" /></el-icon>
              <span>{{ top.name }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="title">{{ pageTitle }}</div>
        <div class="right">
          <el-dropdown>
            <span class="user">
              <el-icon><UserFilled /></el-icon>
              {{ store.user?.nickname || store.user?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main style="padding: 0; background: #f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.aside {
  background: #001529;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  height: 56px;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.user {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
</style>
