<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { listWarnings } from '@/api/modules'

const loading = ref(false)
const items = ref<any[]>([])

async function load() {
  loading.value = true
  try {
    const res: any = await listWarnings({})
    items.value = res.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-button type="primary" @click="load">刷新</el-button>
      <span style="color: #909399; font-size: 13px">低于下限为缺货预警，高于上限为积压预警（上下限在商品管理中设置）</span>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="code" label="商品编码" width="120" />
      <el-table-column prop="name" label="商品名称" min-width="160" />
      <el-table-column prop="unit" label="单位" width="70" />
      <el-table-column prop="total_qty" label="当前库存" width="110" align="right" />
      <el-table-column label="预警类型" width="120">
        <template #default="{ row }">
          <el-tag :type="row.type === 'low' ? 'danger' : 'warning'">{{ row.type === 'low' ? '低于下限' : '高于上限' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="threshold" label="阈值" width="100" align="right" />
    </el-table>
  </el-card>
</template>
