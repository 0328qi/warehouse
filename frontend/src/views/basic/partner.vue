<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCustomer, createSupplier, deleteCustomer, deleteSupplier, listCustomers,
  listSuppliers, updateCustomer, updateSupplier,
} from '@/api/modules'

const activeTab = ref('supplier')
const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const query = reactive({ keyword: '', page: 1, page_size: 20 })

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({ name: '', contact: '', phone: '', address: '', remark: '' })

async function load() {
  loading.value = true
  try {
    const api = activeTab.value === 'supplier' ? listSuppliers : listCustomers
    const res: any = await api(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', contact: '', phone: '', address: '', remark: '' })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, row)
  dialog.value = true
}

async function submit() {
  if (!form.name) {
    ElMessage.warning('请填写名称')
    return
  }
  const isSupplier = activeTab.value === 'supplier'
  const create = isSupplier ? createSupplier : createCustomer
  const update = isSupplier ? updateSupplier : updateCustomer
  if (editing.value) {
    await update(editing.value.id, { ...form })
  } else {
    const res: any = await create({ ...form })
    ElMessage.success(`已创建，编码：${res.code}`)
  }
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确定删除「${row.name}」吗？`, '提示', { type: 'warning' })
  const del = activeTab.value === 'supplier' ? deleteSupplier : deleteCustomer
  await del(row.id)
  ElMessage.success('已删除')
  load()
}

function onTabChange() {
  query.page = 1
  load()
}

onMounted(load)
</script>

<template>
  <el-card class="page-card" shadow="never">
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="供应商" name="supplier" />
      <el-tab-pane label="客户" name="customer" />
    </el-tabs>
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="编码/名称" style="width: 220px" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="activeTab === 'supplier' ? 'basic:supplier:create' : 'basic:customer:create'" type="primary" @click="openCreate">
        新增{{ activeTab === 'supplier' ? '供应商' : '客户' }}
      </el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="code" label="编码" width="120" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="contact" label="联系人" width="110" />
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column prop="address" label="地址" min-width="180" />
      <el-table-column prop="remark" label="备注" min-width="120" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-permission="activeTab === 'supplier' ? 'basic:supplier:update' : 'basic:customer:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-permission="activeTab === 'supplier' ? 'basic:supplier:delete' : 'basic:customer:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑' : '新增'" width="460px">
    <el-form label-width="80px">
      <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="联系人"><el-input v-model="form.contact" /></el-form-item>
      <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="地址"><el-input v-model="form.address" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
