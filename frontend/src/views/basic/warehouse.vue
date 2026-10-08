<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createWarehouse, deleteWarehouse, listWarehouses, updateWarehouse } from '@/api/modules'

const loading = ref(false)
const total = ref(0)
const query = reactive({ keyword: '', page: 1, page_size: 20 })
const items = ref<any[]>([])

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({ code: '', name: '', address: '', contact: '', phone: '', remark: '' })

async function load() {
  loading.value = true
  try {
    const res: any = await listWarehouses(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { code: '', name: '', address: '', contact: '', phone: '', remark: '' })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, { code: row.code, name: row.name, address: row.address, contact: row.contact, phone: row.phone, remark: row.remark })
  dialog.value = true
}

async function submit() {
  if (!form.code || !form.name) {
    ElMessage.warning('请填写编码和名称')
    return
  }
  if (editing.value) {
    await updateWarehouse(editing.value.id, { name: form.name, address: form.address, contact: form.contact, phone: form.phone, remark: form.remark })
  } else {
    await createWarehouse({ ...form })
  }
  ElMessage.success('保存成功')
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确定删除仓库「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteWarehouse(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="编码/名称" style="width: 220px" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="'basic:warehouse:create'" type="primary" @click="openCreate">新增仓库</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="code" label="编码" width="120" />
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column prop="address" label="地址" min-width="180" />
      <el-table-column prop="contact" label="联系人" width="100" />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status ? 'success' : 'danger'">{{ row.status ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-permission="'basic:warehouse:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-permission="'basic:warehouse:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑仓库' : '新增仓库'" width="480px">
    <el-form label-width="80px">
      <el-form-item label="编码" required>
        <el-input v-model="form.code" :disabled="!!editing" placeholder="如 WH02" />
      </el-form-item>
      <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
      <el-form-item label="联系人"><el-input v-model="form.contact" /></el-form-item>
      <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
