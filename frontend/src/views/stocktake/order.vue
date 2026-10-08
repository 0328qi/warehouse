<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  allWarehouses, allZones, cancelStocktake, createStocktake, finishStocktake,
  getStocktake, listStocktakes, recordStocktake,
} from '@/api/modules'

const STATUS: Record<string, any> = { processing: { label: '进行中', type: 'warning' }, finished: { label: '已完成', type: 'success' }, cancelled: { label: '已作废', type: 'info' } }

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const warehouses = ref<any[]>([])
const query = reactive({ status: '', page: 1, page_size: 20 })

const createDialog = ref(false)
const createForm = reactive({ warehouse_id: undefined as number | undefined, zone_id: null as number | null, remark: '' })
const zones = ref<any[]>([])

const detailDialog = ref(false)
const detail = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const res: any = await listStocktakes(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function openCreate() {
  Object.assign(createForm, { warehouse_id: undefined, zone_id: null, remark: '' })
  createDialog.value = true
}

async function onWarehouseChange() {
  createForm.zone_id = null
  zones.value = createForm.warehouse_id ? ((await allZones(createForm.warehouse_id)) as any[]) : []
}

async function submitCreate() {
  if (!createForm.warehouse_id) {
    ElMessage.warning('请选择仓库')
    return
  }
  const order: any = await createStocktake({
    warehouse_id: createForm.warehouse_id,
    zone_id: createForm.zone_id || undefined,
    remark: createForm.remark,
  })
  ElMessage.success(`盘点单已创建：${order.order_no}`)
  createDialog.value = false
  load()
}

async function openDetail(row: any) {
  detail.value = await getStocktake(row.id)
  detailDialog.value = true
}

async function saveRecord(row: any) {
  await recordStocktake(detail.value.id, [{ item_id: row.id, actual_qty: row.actual_qty }])
  ElMessage.success('已录入')
}

async function finish() {
  await ElMessageBox.confirm('确定完成盘点吗？差异将直接调整库存。', '提示', { type: 'warning' })
  const res: any = await finishStocktake(detail.value.id)
  ElMessage.success(`盘点完成，差异 ${res.diff_count} 条已调整库存`)
  detail.value = res
  load()
}

async function cancel(row: any) {
  await ElMessageBox.confirm(`确定作废盘点单 ${row.order_no} 吗？`, '提示', { type: 'warning' })
  await cancelStocktake(row.id)
  ElMessage.success('已作废')
  load()
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  load()
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 130px" @change="load">
        <el-option v-for="(v, k) in STATUS" :key="k" :label="v.label" :value="k" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="'stocktake:order:create'" type="primary" @click="openCreate">新建盘点单</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="order_no" label="单号" width="220" />
      <el-table-column prop="warehouse_name" label="仓库" width="130" />
      <el-table-column prop="zone_name" label="范围" width="120" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS[row.status]?.type">{{ STATUS[row.status]?.label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="item_count" label="明细数" width="90" />
      <el-table-column prop="diff_count" label="差异数" width="90" />
      <el-table-column prop="creator_name" label="创建人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDetail(row)">盘点</el-button>
          <el-button v-if="row.status === 'processing'" v-permission="'stocktake:order:finish'" link type="danger" @click="cancel(row)">作废</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="createDialog" title="新建盘点单" width="460px">
    <el-form label-width="90px">
      <el-form-item label="仓库" required>
        <el-select v-model="createForm.warehouse_id" style="width: 100%" @change="onWarehouseChange">
          <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="盘点范围">
        <el-select v-model="createForm.zone_id" style="width: 100%" clearable placeholder="不选=全仓盘点">
          <el-option v-for="z in zones" :key="z.id" :label="z.name" :value="z.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="createForm.remark" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialog = false">取消</el-button>
      <el-button type="primary" @click="submitCreate">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="detailDialog" :title="`盘点单 ${detail?.order_no || ''}`" width="860px">
    <template v-if="detail">
      <el-descriptions :column="4" border size="small">
        <el-descriptions-item label="仓库">{{ detail.warehouse_name }}</el-descriptions-item>
        <el-descriptions-item label="范围">{{ detail.zone_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ STATUS[detail.status]?.label }}</el-descriptions-item>
        <el-descriptions-item label="差异">{{ detail.diff_count }} 条</el-descriptions-item>
      </el-descriptions>
      <el-table :data="detail.items" border size="small" style="margin-top: 12px">
        <el-table-column prop="goods_code" label="商品编码" width="110" />
        <el-table-column prop="goods_name" label="商品名称" min-width="130" />
        <el-table-column prop="location_code" label="库位" width="130" />
        <el-table-column prop="book_qty" label="账面" width="90" align="right" />
        <el-table-column label="实盘" width="170">
          <template #default="{ row }">
            <el-input-number v-model="row.actual_qty" :min="0" size="small" style="width: 130px"
              :disabled="detail.status !== 'processing'" @change="saveRecord(row)" />
          </template>
        </el-table-column>
        <el-table-column label="差异" width="90" align="right">
          <template #default="{ row }">
            <span v-if="row.actual_qty !== null" :style="{ color: row.actual_qty - row.book_qty !== 0 ? '#e6a23c' : '#909399' }">
              {{ row.actual_qty - row.book_qty }}
            </span>
            <span v-else>未盘</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="detail.status === 'processing'" style="margin-top: 12px; text-align: right">
        <el-button v-permission="'stocktake:order:finish'" type="primary" @click="finish">完成盘点并调整库存</el-button>
      </div>
    </template>
  </el-dialog>
</template>
