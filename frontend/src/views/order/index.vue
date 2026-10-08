<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  allCustomers, allLocations, allSuppliers, allWarehouses, cancelInbound, cancelOutbound,
  createInbound, createOutbound, executeInbound, executeOutbound, getInbound, getOutbound,
  listGoods, listInbound, listOutbound,
} from '@/api/modules'

const route = useRoute()
const isInbound = computed(() => route.meta.mode !== 'outbound')
const title = computed(() => (isInbound.value ? '入库单' : '出库单'))

const IN_TYPE_LABELS: Record<string, string> = { purchase: '采购入库', return: '退货入库', other: '其他入库' }
const OUT_TYPE_LABELS: Record<string, string> = { sale: '销售出库', use: '领用出库', other: '其他出库' }
const STATUS_LABELS: Record<string, string> = { draft: '草稿', executed: '已执行', cancelled: '已作废' }
const typeLabels = computed(() => (isInbound.value ? IN_TYPE_LABELS : OUT_TYPE_LABELS))

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const query = reactive({ keyword: '', status: '', type: '', warehouse_id: undefined as number | undefined, page: 1, page_size: 20 })

const warehouses = ref<any[]>([])
const partners = ref<any[]>([])
const goodsOptions = ref<any[]>([])
const locationOptions = ref<any[]>([])

const viewDialog = ref(false)
const viewing = ref<any>(null)

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({
  type: 'purchase',
  warehouse_id: undefined as number | undefined,
  partner_id: undefined as number | undefined,
  remark: '',
  lines: [] as { goods_id?: number; location_id?: number; qty: number }[],
})

const typeOptions = computed(() => Object.entries(typeLabels.value).map(([value, label]) => ({ value, label })))

async function load() {
  loading.value = true
  try {
    const api = isInbound.value ? listInbound : listOutbound
    const res: any = await api(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    type: isInbound.value ? 'purchase' : 'sale',
    warehouse_id: query.warehouse_id,
    partner_id: undefined,
    remark: '',
    lines: [{ goods_id: undefined, location_id: undefined, qty: 1 }],
  })
  dialog.value = true
}

async function openView(row: any) {
  const api = isInbound.value ? getInbound : getOutbound
  viewing.value = await api(row.id)
  viewDialog.value = true
}

function addLine() {
  form.lines.push({ goods_id: undefined, location_id: undefined, qty: 1 })
}

function removeLine(idx: number) {
  form.lines.splice(idx, 1)
}

function onWarehouseChange() {
  locationOptions.value = []
  for (const line of form.lines) line.location_id = undefined
  loadLocations()
}

async function loadLocations() {
  if (!form.warehouse_id) return
  locationOptions.value = (await allLocations({ warehouse_id: form.warehouse_id })) as any[]
}

async function searchGoods(keyword: string) {
  const res: any = await listGoods({ keyword, page_size: 50 })
  goodsOptions.value = res.items
}

async function submit(andExecute: boolean) {
  if (!form.warehouse_id || !form.lines.length) {
    ElMessage.warning('请选择仓库并添加明细')
    return
  }
  if (form.lines.some((l) => !l.goods_id || !l.location_id || l.qty <= 0)) {
    ElMessage.warning('请完善明细（商品/库位/数量）')
    return
  }
  const payload = {
    type: form.type,
    warehouse_id: form.warehouse_id,
    ...(isInbound.value ? { supplier_id: form.partner_id } : { customer_id: form.partner_id }),
    remark: form.remark,
    items: form.lines.map((l) => ({ goods_id: l.goods_id, location_id: l.location_id, qty: l.qty })),
  }
  let order: any
  if (isInbound.value) {
    order = await createInbound(payload)
    if (andExecute) order = await executeInbound(order.id)
  } else {
    order = await createOutbound(payload)
    if (andExecute) order = await executeOutbound(order.id)
  }
  ElMessage.success(andExecute ? `单据已执行：${order.order_no}` : `已保存草稿：${order.order_no}`)
  dialog.value = false
  load()
}

async function execute(row: any) {
  await ElMessageBox.confirm(`确定执行单据 ${row.order_no} 吗？执行后库存立即变动。`, '提示', { type: 'warning' })
  const api = isInbound.value ? executeInbound : executeOutbound
  await api(row.id)
  ElMessage.success('已执行')
  load()
}

async function cancel(row: any) {
  await ElMessageBox.confirm(`确定作废单据 ${row.order_no} 吗？`, '提示', { type: 'warning' })
  const api = isInbound.value ? cancelInbound : cancelOutbound
  await api(row.id)
  ElMessage.success('已作废')
  load()
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  partners.value = (await (isInbound.value ? allSuppliers() : allCustomers())) as any[]
  searchGoods('')
  load()
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="单号" style="width: 200px" clearable @keyup.enter="load" />
      <el-select v-model="query.type" placeholder="类型" clearable style="width: 140px" @change="load">
        <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
      <el-select v-model="query.status" placeholder="状态" clearable style="width: 120px" @change="load">
        <el-option label="草稿" value="draft" />
        <el-option label="已执行" value="executed" />
        <el-option label="已作废" value="cancelled" />
      </el-select>
      <el-select v-model="query.warehouse_id" placeholder="仓库" clearable style="width: 160px" @change="load">
        <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
      </el-select>
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="isInbound ? 'inbound:order:create' : 'outbound:order:create'" type="primary" @click="openCreate">
        新建{{ title }}
      </el-button>
    </div>

    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="order_no" label="单号" width="220" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">{{ typeLabels[row.type] || row.type }}</template>
      </el-table-column>
      <el-table-column prop="warehouse_name" label="仓库" width="120" />
      <el-table-column :prop="isInbound ? 'supplier_name' : 'customer_name'" :label="isInbound ? '供应商' : '客户'" width="130" />
      <el-table-column prop="total_qty" label="总数量" width="90" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'executed' ? 'success' : row.status === 'draft' ? 'warning' : 'info'">
            {{ STATUS_LABELS[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="creator_name" label="创建人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openView(row)">详情</el-button>
          <template v-if="row.status === 'draft'">
            <el-button v-permission="isInbound ? 'inbound:order:execute' : 'outbound:order:execute'" link type="success" @click="execute(row)">执行</el-button>
            <el-button v-permission="isInbound ? 'inbound:order:cancel' : 'outbound:order:cancel'" link type="danger" @click="cancel(row)">作废</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <!-- 新建单据 -->
  <el-dialog v-model="dialog" :title="`新建${title}`" width="860px">
    <el-form inline>
      <el-form-item label="类型" required>
        <el-select v-model="form.type" style="width: 140px">
          <el-option v-for="o in typeOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="仓库" required>
        <el-select v-model="form.warehouse_id" style="width: 180px" @change="onWarehouseChange">
          <el-option v-for="w in warehouses" :key="w.id" :label="`${w.code} ${w.name}`" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item :label="isInbound ? '供应商' : '客户'">
        <el-select v-model="form.partner_id" clearable filterable style="width: 180px">
          <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-table :data="form.lines" border size="small">
      <el-table-column label="商品" min-width="220">
        <template #default="{ row }">
          <el-select v-model="row.goods_id" filterable remote :remote-method="searchGoods" placeholder="搜索商品" style="width: 100%">
            <el-option v-for="g in goodsOptions" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="库位" min-width="160">
        <template #default="{ row }">
          <el-select v-model="row.location_id" filterable placeholder="选择库位" style="width: 100%">
            <el-option v-for="l in locationOptions" :key="l.id" :label="l.code" :value="l.id" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="数量" width="130">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="0.01" style="width: 110px" />
        </template>
      </el-table-column>
      <el-table-column label="" width="70">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeLine($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button style="margin-top: 8px" @click="addLine">+ 添加明细</el-button>

    <el-form inline style="margin-top: 12px">
      <el-form-item label="备注"><el-input v-model="form.remark" style="width: 400px" /></el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button @click="submit(false)">存草稿</el-button>
      <el-button v-permission="isInbound ? 'inbound:order:execute' : 'outbound:order:execute'" type="primary" @click="submit(true)">
        保存并执行
      </el-button>
    </template>
  </el-dialog>

  <!-- 详情 -->
  <el-dialog v-model="viewDialog" title="单据详情" width="760px">
    <template v-if="viewing">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="单号">{{ viewing.order_no }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeLabels[viewing.type] }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ STATUS_LABELS[viewing.status] }}</el-descriptions-item>
        <el-descriptions-item label="仓库">{{ viewing.warehouse_name }}</el-descriptions-item>
        <el-descriptions-item :label="isInbound ? '供应商' : '客户'">{{ isInbound ? viewing.supplier_name : viewing.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="创建人">{{ viewing.creator_name }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="3">{{ viewing.remark }}</el-descriptions-item>
      </el-descriptions>
      <el-table :data="viewing.items" border size="small" style="margin-top: 12px">
        <el-table-column prop="goods_code" label="商品编码" width="110" />
        <el-table-column prop="goods_name" label="商品名称" min-width="140" />
        <el-table-column prop="location_code" label="库位" width="140" />
        <el-table-column prop="qty" label="数量" width="90" />
        <el-table-column prop="remark" label="备注" min-width="100" />
      </el-table>
    </template>
  </el-dialog>
</template>
