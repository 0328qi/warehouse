<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  allWarehouses, batchCreateLocations, createLocation, createZone, deleteLocation, deleteZone,
  listLocations, listZones, updateLocation, updateZone,
} from '@/api/modules'

const activeTab = ref('zone')
const warehouses = ref<any[]>([])
const whId = ref<number>()
const loading = ref(false)

// ---- 库区 ----
const zones = ref<any[]>([])
const zoneDialog = ref(false)
const zoneForm = reactive({ code: '', name: '', type: 'storage', remark: '' })
const zoneTypes: Record<string, string> = { receiving: '收货区', storage: '存储区', picking: '拣货区', returns: '退货区', other: '其他' }

async function loadZones() {
  if (!whId.value) return
  loading.value = true
  try {
    const res: any = await listZones({ warehouse_id: whId.value, page: 1, page_size: 100 })
    zones.value = res.items
  } finally {
    loading.value = false
  }
}

async function submitZone() {
  if (!zoneForm.code || !zoneForm.name) {
    ElMessage.warning('请填写编码和名称')
    return
  }
  await createZone({ ...zoneForm, warehouse_id: whId.value })
  ElMessage.success('已创建')
  zoneDialog.value = false
  Object.assign(zoneForm, { code: '', name: '', type: 'storage', remark: '' })
  loadZones()
}

async function removeZone(row: any) {
  await ElMessageBox.confirm(`确定删除库区「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteZone(row.id)
  ElMessage.success('已删除')
  loadZones()
}

// ---- 库位 ----
const locs = ref<any[]>([])
const locTotal = ref(0)
const locQuery = reactive({ warehouse_id: undefined as number | undefined, zone_id: undefined as number | undefined, keyword: '', page: 1, page_size: 20 })
const locDialog = ref(false)
const batchDialog = ref(false)
const locForm = reactive({ zone_id: undefined as number | undefined, code: '' })
const batchForm = reactive({ zone_id: undefined as number | undefined, prefix: '', rows: 3, cols: 5 })

async function loadLocs() {
  if (!whId.value) return
  loading.value = true
  try {
    const res: any = await listLocations({ ...locQuery, warehouse_id: whId.value })
    locs.value = res.items
    locTotal.value = res.total
  } finally {
    loading.value = false
  }
}

async function submitLoc() {
  if (!locForm.zone_id || !locForm.code) {
    ElMessage.warning('请选择库区并填写编码')
    return
  }
  await createLocation({ warehouse_id: whId.value, zone_id: locForm.zone_id, code: locForm.code })
  ElMessage.success('已创建')
  locDialog.value = false
  loadLocs()
}

async function submitBatch() {
  if (!batchForm.zone_id || !batchForm.prefix || batchForm.rows < 1 || batchForm.cols < 1) {
    ElMessage.warning('请完整填写批量生成参数')
    return
  }
  const res: any = await batchCreateLocations({ warehouse_id: whId.value, ...batchForm })
  ElMessage.success(res.message)
  batchDialog.value = false
  loadLocs()
}

async function removeLoc(row: any) {
  await ElMessageBox.confirm(`确定删除库位「${row.code}」吗？`, '提示', { type: 'warning' })
  await deleteLocation(row.id)
  ElMessage.success('已删除')
  loadLocs()
}

function onWhChange() {
  zones.value = []
  locs.value = []
  locQuery.zone_id = undefined
  loadZones()
  loadLocs()
}

async function toggleLoc(row: any) {
  await updateLocation(row.id, { status: !row.status, remark: row.remark })
  row.status = !row.status
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  if (warehouses.value.length) {
    whId.value = warehouses.value[0].id
    onWhChange()
  }
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <span>仓库：</span>
      <el-select v-model="whId" style="width: 200px" @change="onWhChange">
        <el-option v-for="w in warehouses" :key="w.id" :label="`${w.code} ${w.name}`" :value="w.id" />
      </el-select>
      <div class="spacer" />
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="库区管理" name="zone">
        <div class="toolbar">
          <el-button v-permission="'basic:zone:create'" type="primary" :disabled="!whId" @click="zoneDialog = true">新增库区</el-button>
        </div>
        <el-table v-loading="loading" :data="zones" border stripe>
          <el-table-column prop="code" label="编码" width="140" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">{{ zoneTypes[row.type] || row.type }}</template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="140" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-permission="'basic:zone:delete'" link type="danger" @click="removeZone(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="库位管理" name="location">
        <div class="toolbar">
          <el-select v-model="locQuery.zone_id" placeholder="全部库区" clearable style="width: 160px" @change="loadLocs">
            <el-option v-for="z in zones" :key="z.id" :label="z.name" :value="z.id" />
          </el-select>
          <el-input v-model="locQuery.keyword" placeholder="库位编码" style="width: 180px" clearable @keyup.enter="loadLocs" />
          <el-button type="primary" @click="loadLocs">查询</el-button>
          <div class="spacer" />
          <el-button v-permission="'basic:location:create'" :disabled="!whId" @click="locDialog = true">单个新增</el-button>
          <el-button v-permission="'basic:location:create'" type="primary" :disabled="!whId" @click="batchDialog = true">批量生成</el-button>
        </div>
        <el-table v-loading="loading" :data="locs" border stripe>
          <el-table-column prop="code" label="库位编码" min-width="140" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status ? 'success' : 'info'">{{ row.status ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="140" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button v-permission="'basic:location:update'" link type="primary" @click="toggleLoc(row)">
                {{ row.status ? '停用' : '启用' }}
              </el-button>
              <el-button v-permission="'basic:location:delete'" link type="danger" @click="removeLoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-model:current-page="locQuery.page" v-model:page-size="locQuery.page_size" class="pager"
          layout="total, prev, pager, next" :total="locTotal" @current-change="loadLocs" />
      </el-tab-pane>
    </el-tabs>
  </el-card>

  <el-dialog v-model="zoneDialog" title="新增库区" width="440px">
    <el-form label-width="80px">
      <el-form-item label="编码" required><el-input v-model="zoneForm.code" placeholder="如 STORE" /></el-form-item>
      <el-form-item label="名称" required><el-input v-model="zoneForm.name" /></el-form-item>
      <el-form-item label="类型">
        <el-select v-model="zoneForm.type">
          <el-option v-for="(label, key) in zoneTypes" :key="key" :label="label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="zoneForm.remark" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="zoneDialog = false">取消</el-button>
      <el-button type="primary" @click="submitZone">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="locDialog" title="新增库位" width="440px">
    <el-form label-width="80px">
      <el-form-item label="库区" required>
        <el-select v-model="locForm.zone_id" style="width: 100%">
          <el-option v-for="z in zones" :key="z.id" :label="z.name" :value="z.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="编码" required><el-input v-model="locForm.code" placeholder="如 STORE-01-01" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="locDialog = false">取消</el-button>
      <el-button type="primary" @click="submitLoc">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="batchDialog" title="批量生成库位" width="460px">
    <el-form label-width="100px">
      <el-form-item label="所属库区" required>
        <el-select v-model="batchForm.zone_id" style="width: 100%">
          <el-option v-for="z in zones" :key="z.id" :label="z.name" :value="z.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="编码前缀" required>
        <el-input v-model="batchForm.prefix" placeholder="如 STORE，生成 STORE-01-01 格式" />
      </el-form-item>
      <el-form-item label="行数" required><el-input-number v-model="batchForm.rows" :min="1" :max="100" /></el-form-item>
      <el-form-item label="列数" required><el-input-number v-model="batchForm.cols" :min="1" :max="100" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="batchDialog = false">取消</el-button>
      <el-button type="primary" @click="submitBatch">生成</el-button>
    </template>
  </el-dialog>
</template>
