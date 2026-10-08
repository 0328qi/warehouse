<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createMenu, deleteMenu, menuTree, updateMenu } from '@/api/modules'

const tree = ref<any[]>([])
const loading = ref(false)

const dialog = ref(false)
const editing = ref<any>(null)
const parentOptions = ref<any[]>([])
const form = reactive({
  parent_id: 0, name: '', type: 'menu', path: '', component: '', perm_code: '', icon: '', sort: 0, visible: true,
})

async function load() {
  loading.value = true
  try {
    tree.value = await menuTree()
    parentOptions.value = [{ id: 0, name: '根目录' }, ...tree.value]
  } finally {
    loading.value = false
  }
}

function openCreate(parentId = 0) {
  editing.value = null
  Object.assign(form, { parent_id: parentId, name: '', type: 'menu', path: '', component: '', perm_code: '', icon: '', sort: 0, visible: true })
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
  if (editing.value) {
    await updateMenu(editing.value.id, { ...form })
  } else {
    await createMenu({ ...form })
  }
  ElMessage.success('保存成功')
  dialog.value = false
  load()
}

async function remove(data: any) {
  await ElMessageBox.confirm(`确定删除「${data.name}」吗？`, '提示', { type: 'warning' })
  await deleteMenu(data.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <el-card class="page-card" shadow="never">
    <div class="toolbar">
      <el-button v-permission="'system:menu:create'" type="primary" @click="openCreate(0)">新增菜单</el-button>
    </div>
    <el-table v-loading="loading" :data="tree" row-key="id" border default-expand-all>
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag :type="row.type === 'dir' ? '' : row.type === 'menu' ? 'success' : 'warning'">
            {{ row.type === 'dir' ? '目录' : row.type === 'menu' ? '页面' : '按钮' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="path" label="路由" min-width="140" />
      <el-table-column prop="component" label="组件" min-width="140" />
      <el-table-column prop="perm_code" label="权限标识" min-width="160" />
      <el-table-column prop="sort" label="排序" width="70" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.type !== 'button'" link type="primary" @click="openCreate(row.id)">添加子项</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-permission="'system:menu:delete'" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑菜单' : '新增菜单'" width="560px">
    <el-form label-width="90px">
      <el-form-item label="上级">
        <el-select v-model="form.parent_id" style="width: 100%">
          <el-option v-for="p in parentOptions" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-row>
        <el-col :span="12">
          <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="类型">
            <el-select v-model="form.type">
              <el-option label="目录" value="dir" />
              <el-option label="页面" value="menu" />
              <el-option label="按钮" value="button" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="路由"><el-input v-model="form.path" placeholder="/basic/goods" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="组件"><el-input v-model="form.component" placeholder="basic/goods" /></el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="权限标识"><el-input v-model="form.perm_code" placeholder="basic:goods:create" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="排序"><el-input-number v-model="form.sort" /></el-form-item>
        </el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
