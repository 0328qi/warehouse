<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createRole, deleteRole, listRoles, menuTree, updateRole } from '@/api/modules'

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const menus = ref<any[]>([])
const query = reactive({ page: 1, page_size: 50 })

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({ name: '', code: '', remark: '', menu_ids: [] as number[] })

async function load() {
  loading.value = true
  try {
    const res: any = await listRoles(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', code: '', remark: '', menu_ids: [] })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, { name: row.name, code: row.code, remark: row.remark, menu_ids: row.menu_ids })
  dialog.value = true
}

async function submit() {
  if (!form.name || !form.code) {
    ElMessage.warning('请填写名称和编码')
    return
  }
  if (editing.value) {
    await updateRole(editing.value.id, { name: form.name, remark: form.remark, menu_ids: form.menu_ids })
  } else {
    await createRole({ ...form })
  }
  ElMessage.success('保存成功')
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确定删除角色「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteRole(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(() => {
  load()
  menuTree().then((res) => (menus.value = res as any[]))
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <div class="spacer" />
      <el-button v-permission="'system:role:create'" type="primary" @click="openCreate">新增角色</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="name" label="角色名称" width="160" />
      <el-table-column prop="code" label="编码" width="140" />
      <el-table-column prop="remark" label="备注" min-width="160" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-permission="'system:role:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-permission="'system:role:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑角色' : '新增角色'" width="520px">
    <el-form label-width="90px">
      <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="编码" required>
        <el-input v-model="form.code" :disabled="!!editing" placeholder="如 warehouse_keeper" />
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" /></el-form-item>
      <el-form-item label="菜单权限">
        <el-tree
          ref="menuTreeRef"
          :data="menus"
          show-checkbox
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          :default-checked-keys="form.menu_ids"
          style="width: 100%; max-height: 320px; overflow: auto; border: 1px solid #eee; padding: 6px"
          @check="(_: any, info: any) => (form.menu_ids = [...info.checkedKeys, ...info.halfCheckedKeys])"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
