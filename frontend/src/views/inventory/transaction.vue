<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { allWarehouses, exportTransactions, listTransactions } from '@/api/modules'

const BIZ_LABELS: Record<string, string> = {
  purchase_in: '采购入库', return_in: '退货入库', other_in: '其他入库',
  sale_out: '销售出库', use_out: '领用出库', other_out: '其他出库',
  move: '移库', transfer_in: '调拨入库', transfer_out: '调拨出库', stocktake: '盘点调整',
}

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const warehouses = ref<any[]>([])
const query = reactive({
  order_no: '', biz_type: '', warehouse_id: undefined as number | undefined, page: 1, page_size: 20,
})

async function load() {
  loading.value = true
  try {
    const res: any = await listTransactions(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function download() {
  const blob: any = await exportTransactions()
  const url = URL.createObjectURL(new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = '库存流水.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  load()
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.order_no" placeholder="单号" style="width: 200px" clearable @keyup.enter="load" />
      <el-select v-model="query.biz_type" placeholder="业务类型" clearable style="width: 150px" @change="load">
        <el-option v-for="(label, key) in BIZ_LABELS" :key="key" :label="label" :value="key" />
      </el-select>
      <el-select v-model="query.warehouse_id" placeholder="仓库" clearable style="width: 160px" @change="load">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button @click="download">导出 Excel</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column prop="order_no" label="单号" width="220" />
      <el-table-column label="业务类型" width="110">
        <template #default="{ row }">{{ BIZ_LABELS[row.biz_type] || row.biz_type }}</template>
      </el-table-column>
      <el-table-column prop="goods_code" label="商品编码" width="100" />
      <el-table-column prop="goods_name" label="商品名称" min-width="130" />
      <el-table-column prop="warehouse_name" label="仓库" width="110" />
      <el-table-column prop="location_code" label="库位" width="130" />
      <el-table-column label="变动" width="90" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.qty > 0 ? '#67c23a' : '#f56c6c' }">{{ row.qty > 0 ? '+' : '' }}{{ row.qty }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="before_qty" label="变动前" width="90" align="right" />
      <el-table-column prop="after_qty" label="变动后" width="90" align="right" />
      <el-table-column prop="operator_name" label="操作人" width="100" />
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>
</template>
