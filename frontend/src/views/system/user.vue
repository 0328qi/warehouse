<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { allRoles, allWarehouses, createUser, deleteUser, listUsers, updateUser } from '@/api/modules'

const loading = ref(false)
const total = ref(0)
const items = ref<any[]>([])
const roles = ref<any[]>([])
const warehouses = ref<any[]>([])
const query = reactive({ keyword: '', page: 1, page_size: 20 })

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({
  username: '', password: '', nickname: '', phone: '', email: '', is_active: true,
  role_ids: [] as number[], warehouse_ids: [] as number[],
})

async function load() {
  loading.value = true
  try {
    const res: any = await listUsers(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { username: '', password: '', nickname: '', phone: '', email: '', is_active: true, role_ids: [], warehouse_ids: [] })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, {
    username: row.username, password: '', nickname: row.nickname, phone: row.phone, email: row.email,
    is_active: row.is_active, role_ids: row.roles.map((r: any) => r.id), warehouse_ids: row.warehouse_ids,
  })
  dialog.value = true
}

async function submit() {
  if (!editing.value && (!form.username || !form.password)) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  if (editing.value) {
    await updateUser(editing.value.id, { ...form })
  } else {
    await createUser({ ...form })
  }
  ElMessage.success('保存成功')
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(async () => {
  load()
  roles.value = (await allRoles()) as any[]
  warehouses.value = (await allWarehouses()) as any[]
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-input v-model="query.keyword" placeholder="用户名/昵称" style="width: 220px" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
      <div class="spacer" />
      <el-button v-permission="'system:user:create'" type="primary" @click="openCreate">新增用户</el-button>
    </div>
    <el-table v-loading="loading" :data="items" border stripe>
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="nickname" label="昵称" width="130" />
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column label="角色" min-width="140">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r.id" size="small" style="margin-right: 4px">{{ r.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="可管仓库" min-width="140">
        <template #default="{ row }">{{ row.warehouse_ids.length || '全部（超管）' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-permission="'system:user:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-permission="'system:user:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
      layout="total, prev, pager, next" :total="total" @current-change="load" />
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑用户' : '新增用户'" width="520px">
    <el-form label-width="90px">
      <el-form-item label="用户名" required>
        <el-input v-model="form.username" :disabled="!!editing" />
      </el-form-item>
      <el-form-item :label="editing ? '重置密码' : '密码'" :required="!editing">
        <el-input v-model="form.password" type="password" show-password :placeholder="editing ? '留空则不修改' : ''" />
      </el-form-item>
      <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
      <el-form-item label="电话"><el-input v-model="form.phone" /></el-form-item>
      <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="form.role_ids" multiple style="width: 100%">
          <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="可管仓库">
        <el-select v-model="form.warehouse_ids" multiple style="width: 100%" placeholder="不选=无仓库数据权限">
          <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-switch v-model="form.is_active" active-text="正常" inactive-text="禁用" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
