<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { allWarehouses, exportInventory, listBalances } from '@/api/modules'

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const warehouses = ref<any[]>([])
const query = reactive({ keyword: '', warehouse_id: undefined as number | undefined, page: 1, page_size: 20 })

async function load() {
  loading.value = true
  try {
    const res: any = await listBalances(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function download() {
  const blob: any = await exportInventory()
  const url = URL.createObjectURL(new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = '库存报表.xlsx'
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('已导出')
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  load()
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="商品编码/名称" style="width: 220px" clearable @keyup.enter="load" />
      <el-select v-model="query.warehouse_id" placeholder="全部仓库" clearable style="width: 180px" @change="load">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="'inventory:balance:list'" @click="download">导出 Excel</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="goods_code" label="商品编码" width="110" />
      <el-table-column prop="goods_name" label="商品名称" min-width="150" />
      <el-table-column prop="unit" label="单位" width="70" />
      <el-table-column prop="warehouse_name" label="仓库" width="130" />
      <el-table-column prop="location_code" label="库位" width="140" />
      <el-table-column prop="qty" label="库存数量" width="110" align="right" />
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>
</template>
