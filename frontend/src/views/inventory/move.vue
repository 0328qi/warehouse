<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { allLocations, allWarehouses, listBalances, moveStock } from '@/api/modules'

const warehouses = ref<any[]>([])
const fromLocs = ref<any[]>([])
const toLocs = ref<any[]>([])
const goodsOptions = ref<any[]>([])
const balances = ref<any[]>([])
const submitting = ref(false)

const form = reactive({
  goods_id: undefined as number | undefined,
  from_location_id: undefined as number | undefined,
  to_location_id: undefined as number | undefined,
  qty: 1,
})

async function onFromLocChange() {
  balances.value = []
  form.qty = 1
  if (!form.from_location_id || !form.goods_id) return
  const res: any = await listBalances({ goods_id: form.goods_id, location_id: form.from_location_id, page_size: 1 })
  balances.value = res.items
}

async function onGoodsChange() {
  form.from_location_id = undefined
  form.to_location_id = undefined
  balances.value = []
}

async function loadFromLocs() {
  if (!warehouses.value.length) return
  fromLocs.value = (await allLocations({ warehouse_id: warehouses.value[0].id })) as any[]
  toLocs.value = fromLocs.value
}

async function submit() {
  if (!form.goods_id || !form.from_location_id || !form.to_location_id || form.qty <= 0) {
    ElMessage.warning('请完善移库信息')
    return
  }
  if (form.from_location_id === form.to_location_id) {
    ElMessage.warning('源库位与目标库位相同')
    return
  }
  submitting.value = true
  try {
    const res: any = await moveStock({ ...form })
    ElMessage.success(`移库成功：${res.order_no}`)
    onFromLocChange()
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  warehouses.value = (await allWarehouses()) as any[]
  await loadFromLocs()
  // 加载全部有货商品作为选项（简化：拉取前 100 条）
  const res: any = await listBalances({ page_size: 100 })
  const seen = new Set()
  goodsOptions.value = res.items.filter((b: any) => {
    if (seen.has(b.goods_id)) return false
    seen.add(b.goods_id)
    return true
  }).map((b: any) => ({ id: b.goods_id, code: b.goods_code, name: b.goods_name, unit: b.unit }))
})
</script>

<template>
  <el-card class="page-card" shadow="never" style="max-width: 640px">
    <el-form label-width="100px">
      <el-form-item label="商品" required>
        <el-select v-model="form.goods_id" filterable placeholder="选择商品" style="width: 100%" @change="onGoodsChange">
          <el-option v-for="g in goodsOptions" :key="g.id" :label="`${g.code} ${g.name}`" :value="g.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="源库位" required>
        <el-select v-model="form.from_location_id" filterable placeholder="选择源库位" style="width: 100%" @change="onFromLocChange">
          <el-option v-for="l in fromLocs" :key="l.id" :label="l.code" :value="l.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="balances.length" label="可用库存">
        <el-tag type="info">{{ balances[0].qty }} {{ balances[0].unit }}</el-tag>
      </el-form-item>
      <el-form-item label="目标库位" required>
        <el-select v-model="form.to_location_id" filterable placeholder="选择目标库位" style="width: 100%">
          <el-option v-for="l in toLocs" :key="l.id" :label="l.code" :value="l.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="移库数量" required>
        <el-input-number v-model="form.qty" :min="0.01" />
      </el-form-item>
      <el-form-item>
        <el-button v-permission="'inventory:move'" type="primary" :loading="submitting" @click="submit">执行移库</el-button>
      </el-form-item>
    </el-form>
    <el-alert type="info" :closable="false" title="提示：跨仓库调拨请在「调拨单」页面操作，移库仅限同一仓库内。" />
  </el-card>
</template>
