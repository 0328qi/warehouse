import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/login/index.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      redirect: '/dashboard',
      children: [
        { path: 'dashboard', component: () => import('@/views/dashboard/index.vue'), meta: { title: '看板' } },
        { path: 'basic/warehouse', component: () => import('@/views/basic/warehouse.vue'), meta: { title: '仓库管理' } },
        { path: 'basic/location', component: () => import('@/views/basic/location.vue'), meta: { title: '库区库位' } },
        { path: 'basic/goods', component: () => import('@/views/basic/goods.vue'), meta: { title: '商品管理' } },
        { path: 'basic/partner', component: () => import('@/views/basic/partner.vue'), meta: { title: '供应商/客户' } },
        { path: 'inbound/order', component: () => import('@/views/order/index.vue'), meta: { title: '入库单', mode: 'inbound' } },
        { path: 'outbound/order', component: () => import('@/views/order/index.vue'), meta: { title: '出库单', mode: 'outbound' } },
        { path: 'inventory/balance', component: () => import('@/views/inventory/balance.vue'), meta: { title: '库存查询' } },
        { path: 'inventory/move', component: () => import('@/views/inventory/move.vue'), meta: { title: '移库' } },
        { path: 'inventory/transfer', component: () => import('@/views/inventory/transfer.vue'), meta: { title: '调拨单' } },
        { path: 'inventory/transaction', component: () => import('@/views/inventory/transaction.vue'), meta: { title: '库存流水' } },
        { path: 'inventory/warning', component: () => import('@/views/inventory/warning.vue'), meta: { title: '库存预警' } },
        { path: 'stocktake/order', component: () => import('@/views/stocktake/order.vue'), meta: { title: '盘点单' } },
        { path: 'system/user', component: () => import('@/views/system/user.vue'), meta: { title: '用户管理' } },
        { path: 'system/role', component: () => import('@/views/system/role.vue'), meta: { title: '角色管理' } },
        { path: 'system/menu', component: () => import('@/views/system/menu.vue'), meta: { title: '菜单管理' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
  ],
})

router.beforeEach((to) => {
  const store = useAuthStore()
  if (!to.meta.public && !store.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
})

export default router
