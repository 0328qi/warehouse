<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  allWarehouses, allLocations, cancelTransfer, createTransfer, executeTransfer,
  getTransfer, listTransfers,
} from '@/api/modules'

const STATUS: Record<string, string> = { draft: '草稿', executed: '已执行', cancelled: '已作废' }

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const warehouses = ref<any[]>([])
const query = reactive({ keyword: '', status: '', page: 1, page_size: 20 })

const dialog = ref(false)
const viewDialog = ref(false)
const viewing = ref<any>(null)
const warehousesMap = ref<Record<number, string>>({})
const locOptions = reactive<Record<number, any[]>>({})

const form = reactive({
  from_warehouse_id: undefined as number | undefined,
  to_warehouse_id: undefined as number | undefined,
  remark: '',
  lines: [] as { goods_id?: number; from_location_id?: number; to_location_id?: number; qty: number }[],
})

const goodsOptions = ref<any[]>([])

async function load() {
  loading.value = true
  try {
    const res: any = await listTransfers(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function openView(row: any) {
  viewing.value = await getTransfer(row.id)
  viewDialog.value = true
}

function openCreate() {
  Object.assign(form, { from_warehouse_id: undefined, to_warehouse_id: undefined, remark: '', lines: [{}] })
  dialog.value = true
}

function addLine() {
  form.lines.push({ goods_id: undefined, from_location_id: undefined, to_location_id: undefined, qty: 1 })
}

async function loadLocs(warehouseId: number) {
  if (!locOptions[warehouseId]) {
    locOptions[warehouseId] = (await allLocations({ warehouse_id: warehouseId })) as any[]
  }
  return locOptions[warehouseId]
}

async function submit() {
  if (!form.from_warehouse_id || !form.to_warehouse_id || !form.lines.length) {
    ElMessage.warning('请选择源/目标仓库并添加明细')
    return
  }
  if (form.lines.some((l) => !l.goods_id || !l.from_location_id || !l.to_location_id || l.qty <= 0)) {
    ElMessage.warning('请完善明细')
    return
  }
  const order: any = await createTransfer({
    from_warehouse_id: form.from_warehouse_id,
    to_warehouse_id: form.to_warehouse_id,
    remark: form.remark,
    items: form.lines,
  })
  await ElMessageBox.confirm(`调拨单 ${order.order_no} 已创建，立即执行吗？`, '提示', { type: 'warning' })
  await executeTransfer(order.id)
  ElMessage.success('调拨已执行')
  dialog.value = false
  load()
}

async function execute(row: any) {
  await ElMessageBox.confirm(`确定执行调拨单 ${row.order_no} 吗？`, '提示', { type: 'warning' })
  await executeTransfer(row.id)
  ElMessage.success('已执行')
  load()
}

async function cancel(row: any) {
  await ElMessageBox.confirm(`确定作废调拨单 ${row.order_no} 吗？`, '提示', { type: 'warning' })
  await cancelTransfer(row.id)
  ElMessage.success('已作废')
  load()
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  warehouses.value.forEach((w) => (warehousesMap.value[w.id] = w.name))
  load()
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="单号" style="width: 200px" clearable @keyup.enter="load" />
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="load">
        <el-option v-for="(label, key) in STATUS" :key="key" :label="label" :value="key" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="'inventory:transfer:create'" type="primary" @click="openCreate">新建调拨单</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="order_no" label="单号" width="220" />
      <el-table-column prop="from_warehouse_name" label="源仓库" width="130" />
      <el-table-column prop="to_warehouse_name" label="目标仓库" width="130" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'executed' ? 'success' : row.status === 'draft' ? 'warning' : 'info'">{{ STATUS[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="creator_name" label="创建人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openView(row)">详情</el-button>
          <template v-if="row.status === 'draft'">
            <el-button v-permission="'inventory:transfer:execute'" link type="success" @click="execute(row)">执行</el-button>
            <el-button v-permission="'inventory:transfer:cancel'" link type="danger" @click="cancel(row)">作废</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="dialog" title="新建调拨单" width="900px">
    <el-form inline>
      <el-form-item label="源仓库" required>
        <el-select v-model="form.from_warehouse_id" style="width: 180px">
          <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="目标仓库" required>
        <el-select v-model="form.to_warehouse_id" style="width: 180px">
          <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <el-table :data="form.lines" border size="small">
      <el-table-column label="商品ID" width="110">
        <template #default="{ row }"><el-input-number v-model="row.goods_id" :min="1" controls-position="right" style="width: 90px" /></template>
      </el-table-column>
      <el-table-column label="源库位" min-width="150">
        <template #default="{ row }">
          <el-select v-model="row.from_location_id" filterable style="width: 100%" @visible-change="(v: boolean) => v && form.from_warehouse_id && loadLocs(form.from_warehouse_id)">
            <el-option v-for="l in locOptions[form.from_warehouse_id!] || []" :key="l.id" :label="l.code" :value="l.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="目标库位" min-width="150">
        <template #default="{ row }">
          <el-select v-model="row.to_location_id" filterable style="width: 100%" @visible-change="(v: boolean) => v && form.to_warehouse_id && loadLocs(form.to_warehouse_id)">
            <el-option v-for="l in locOptions[form.to_warehouse_id!] || []" :key="l.id" :label="l.code" :value="l.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="130">
        <template #default="{ row }"><el-input-number v-model="row.qty" :min="0.01" style="width: 110px" /></template>
      </el-table-column>
      <el-table-column label="" width="70">
        <template #default="{ $index }"><el-button link type="danger" @click="form.lines.splice($index, 1)">删除</el-button></template>
      </el-table-column>
    </el-table>
    <el-button style="margin-top: 8px" @click="addLine">+ 添加明细</el-button>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">创建并执行</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="viewDialog" title="调拨单详情" width="760px">
    <template v-if="viewing">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="单号">{{ viewing.order_no }}</el-descriptions-item>
        <el-descriptions-item label="源仓库">{{ viewing.from_warehouse_name }}</el-descriptions-item>
        <el-descriptions-item label="目标仓库">{{ viewing.to_warehouse_name }}</el-descriptions-item>
      </el-descriptions>
      <el-table :data="viewing.items" border size="small" style="margin-top: 12px">
        <el-table-column prop="goods_code" label="商品编码" width="110" />
        <el-table-column prop="goods_name" label="商品名称" min-width="130" />
        <el-table-column prop="from_location_code" label="源库位" width="130" />
        <el-table-column prop="to_location_code" label="目标库位" width="130" />
        <el-table-column prop="qty" label="数量" width="90" />
      </el-table>
    </template>
  </el-dialog>
</template>
