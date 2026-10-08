<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, ElTree } from 'element-plus'
import {
  categoryTree, createCategory, createGoods, deleteCategory, deleteGoods,
  listGoods, updateCategory, updateGoods, allSuppliers,
} from '@/api/modules'

const loading = ref(false)
const total = ref(0)
const query = reactive({ keyword: '', category_id: undefined as number | undefined, page: 1, page_size: 20 })
const items = ref<any[]>([])
const suppliers = ref<any[]>([])
const treeRef = ref<InstanceType<typeof ElTree>>()
const tree = ref<any[]>([])

const dialog = ref(false)
const editing = ref<any>(null)
const form = reactive({
  name: '', category_id: undefined as number | undefined, unit: '个', spec: '', barcode: '',
  price: 0, supplier_id: undefined as number | undefined, min_stock: 0, max_stock: 0, remark: '',
})

const catDialog = ref(false)
const catEditing = ref<any>(null)
const catForm = reactive({ name: '', sort: 0 })

async function load() {
  loading.value = true
  try {
    const res: any = await listGoods(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadTree() {
  tree.value = await categoryTree()
}

function openCreate() {
  editing.value = null
  Object.assign(form, { name: '', category_id: query.category_id, unit: '个', spec: '', barcode: '', price: 0, supplier_id: undefined, min_stock: 0, max_stock: 0, remark: '' })
  dialog.value = true
}

function openEdit(row: any) {
  editing.value = row
  Object.assign(form, row)
  dialog.value = true
}

async function submit() {
  if (!form.name) {
    ElMessage.warning('请填写商品名称')
    return
  }
  if (editing.value) {
    await updateGoods(editing.value.id, { ...form })
  } else {
    const res: any = await createGoods({ ...form })
    ElMessage.success(`已创建，商品编码：${res.code}`)
  }
  dialog.value = false
  load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确定删除商品「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteGoods(row.id)
  ElMessage.success('已删除')
  load()
}

function onNodeClick(data: any) {
  query.category_id = data.id
  query.page = 1
  load()
}

function openCatCreate() {
  catEditing.value = null
  Object.assign(catForm, { name: '', sort: 0 })
  catDialog.value = true
}

async function submitCat() {
  if (!catForm.name) {
    ElMessage.warning('请填写分类名称')
    return
  }
  if (catEditing.value) {
    await updateCategory(catEditing.value.id, { ...catForm })
  } else {
    await createCategory({ ...catForm, parent_id: query.category_id || 0 })
  }
  ElMessage.success('保存成功')
  catDialog.value = false
  loadTree()
}

async function removeCat(data: any) {
  await ElMessageBox.confirm(`确定删除分类「${data.name}」吗？`, '提示', { type: 'warning' })
  await deleteCategory(data.id)
  ElMessage.success('已删除')
  loadTree()
}

onMounted(() => {
  load()
  loadTree()
  allSuppliers().then((res) => (suppliers.value = res as any[]))
})
</script>

<template>
  <el-card class="page-card" shadow="never">
    <el-row :gutter="16">
      <el-col :span="5">
        <div class="toolbar">
          <strong>商品分类</strong>
          <div class="spacer" />
          <el-button v-permission="'basic:goods:create'" size="small" @click="openCatCreate">新增</el-button>
        </div>
        <el-tree
          ref="treeRef"
          :data="tree"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          default-expand-all
          highlight-current
          @node-click="onNodeClick"
        >
          <template #default="{ data }">
            <span style="display: flex; flex: 1; align-items: center; justify-content: space-between">
              <span>{{ data.name }}</span>
              <span>
                <el-button link size="small" @click.stop="catEditing = data; catForm.name = data.name; catForm.sort = data.sort; catDialog = true">改</el-button>
                <el-button v-permission="'basic:goods:delete'" link size="small" type="danger" @click.stop="removeCat(data)">删</el-button>
              </span>
            </span>
          </template>
        </el-tree>
      </el-col>
      <el-col :span="19">
        <div class="toolbar">
          <el-input v-model="query.keyword" placeholder="编码/名称/条码" style="width: 220px" clearable @keyup.enter="load" />
          <el-button type="primary" @click="query.page = 1; load()">查询</el-button>
          <el-button @click="query.category_id = undefined; load()">全部分类</el-button>
          <div class="spacer" />
          <el-button v-permission="'basic:goods:create'" type="primary" @click="openCreate">新增商品</el-button>
        </div>
        <el-table v-loading="loading" :data="items" border stripe>
          <el-table-column prop="code" label="编码" width="110" />
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="spec" label="规格" min-width="100" />
          <el-table-column prop="unit" label="单位" width="70" />
          <el-table-column prop="price" label="参考价" width="90" />
          <el-table-column prop="barcode" label="条码" width="120" />
          <el-table-column prop="min_stock" label="下限" width="80" />
          <el-table-column prop="max_stock" label="上限" width="80" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status ? 'success' : 'info'">{{ row.status ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button v-permission="'basic:goods:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button v-permission="'basic:goods:delete'" link type="danger" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager"
          layout="total, prev, pager, next" :total="total" @current-change="load" />
      </el-col>
    </el-row>
  </el-card>

  <el-dialog v-model="dialog" :title="editing ? '编辑商品' : '新增商品'" width="560px">
    <el-form label-width="90px">
      <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
      <el-row>
        <el-col :span="12">
          <el-form-item label="分类">
            <el-tree-select v-model="form.category_id" :data="tree" :props="{ label: 'name' }" node-key="id" check-strictly style="width: 100%" clearable />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="规格"><el-input v-model="form.spec" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="条码"><el-input v-model="form.barcode" /></el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="参考价"><el-input-number v-model="form.price" :min="0" :precision="2" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="默认供应商">
            <el-select v-model="form.supplier_id" clearable style="width: 100%">
              <el-option v-for="s in suppliers" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-row>
        <el-col :span="12">
          <el-form-item label="库存下限"><el-input-number v-model="form.min_stock" :min="0" /></el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="库存上限"><el-input-number v-model="form.max_stock" :min="0" /></el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="catDialog" :title="catEditing ? '编辑分类' : '新增分类'" width="380px">
    <el-form label-width="80px">
      <el-form-item label="名称" required><el-input v-model="catForm.name" /></el-form-item>
      <el-form-item label="排序"><el-input-number v-model="catForm.sort" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="catDialog = false">取消</el-button>
      <el-button type="primary" @click="submitCat">保存</el-button>
    </template>
  </el-dialog>
</template>
