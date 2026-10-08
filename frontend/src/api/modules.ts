import request from './index'

// ==== 认证 ====
export const login = (data: { username: string; password: string }) =>
  request.post('/auth/login', data)
export const getMe = () => request.get('/auth/me')

// ==== 系统管理 ====
export const listUsers = (params: any) => request.get('/system/users', { params })
export const createUser = (data: any) => request.post('/system/users', data)
export const updateUser = (id: number, data: any) => request.put(`/system/users/${id}`, data)
export const deleteUser = (id: number) => request.delete(`/system/users/${id}`)
export const listRoles = (params: any) => request.get('/system/roles', { params })
export const allRoles = () => request.get('/system/roles/all')
export const createRole = (data: any) => request.post('/system/roles', data)
export const updateRole = (id: number, data: any) => request.put(`/system/roles/${id}`, data)
export const deleteRole = (id: number) => request.delete(`/system/roles/${id}`)
export const menuTree = () => request.get('/system/menus/tree')
export const createMenu = (data: any) => request.post('/system/menus', data)
export const updateMenu = (id: number, data: any) => request.put(`/system/menus/${id}`, data)
export const deleteMenu = (id: number) => request.delete(`/system/menus/${id}`)

// ==== 基础数据 ====
export const listWarehouses = (params: any) => request.get('/basic/warehouses', { params })
export const allWarehouses = () => request.get('/basic/warehouses/all')
export const createWarehouse = (data: any) => request.post('/basic/warehouses', data)
export const updateWarehouse = (id: number, data: any) => request.put(`/basic/warehouses/${id}`, data)
export const deleteWarehouse = (id: number) => request.delete(`/basic/warehouses/${id}`)

export const listZones = (params: any) => request.get('/basic/zones', { params })
export const allZones = (warehouseId: number) => request.get('/basic/zones/all', { params: { warehouse_id: warehouseId } })
export const createZone = (data: any) => request.post('/basic/zones', data)
export const updateZone = (id: number, data: any) => request.put(`/basic/zones/${id}`, data)
export const deleteZone = (id: number) => request.delete(`/basic/zones/${id}`)

export const listLocations = (params: any) => request.get('/basic/locations', { params })
export const allLocations = (params: any) => request.get('/basic/locations/all', { params })
export const createLocation = (data: any) => request.post('/basic/locations', data)
export const batchCreateLocations = (data: any) => request.post('/basic/locations/batch', data)
export const updateLocation = (id: number, data: any) => request.put(`/basic/locations/${id}`, data)
export const deleteLocation = (id: number) => request.delete(`/basic/locations/${id}`)

export const categoryTree = () => request.get('/basic/goods-categories/tree')
export const createCategory = (data: any) => request.post('/basic/goods-categories', data)
export const updateCategory = (id: number, data: any) => request.put(`/basic/goods-categories/${id}`, data)
export const deleteCategory = (id: number) => request.delete(`/basic/goods-categories/${id}`)

export const listGoods = (params: any) => request.get('/basic/goods', { params })
export const createGoods = (data: any) => request.post('/basic/goods', data)
export const updateGoods = (id: number, data: any) => request.put(`/basic/goods/${id}`, data)
export const deleteGoods = (id: number) => request.delete(`/basic/goods/${id}`)

export const listSuppliers = (params: any) => request.get('/basic/suppliers', { params })
export const allSuppliers = () => request.get('/basic/suppliers/all')
export const createSupplier = (data: any) => request.post('/basic/suppliers', data)
export const updateSupplier = (id: number, data: any) => request.put(`/basic/suppliers/${id}`, data)
export const deleteSupplier = (id: number) => request.delete(`/basic/suppliers/${id}`)

export const listCustomers = (params: any) => request.get('/basic/customers', { params })
export const allCustomers = () => request.get('/basic/customers/all')
export const createCustomer = (data: any) => request.post('/basic/customers', data)
export const updateCustomer = (id: number, data: any) => request.put(`/basic/customers/${id}`, data)
export const deleteCustomer = (id: number) => request.delete(`/basic/customers/${id}`)

// ==== 出入库 ====
export const listInbound = (params: any) => request.get('/inbound/orders', { params })
export const getInbound = (id: number) => request.get(`/inbound/orders/${id}`)
export const createInbound = (data: any) => request.post('/inbound/orders', data)
export const updateInbound = (id: number, data: any) => request.put(`/inbound/orders/${id}`, data)
export const executeInbound = (id: number) => request.post(`/inbound/orders/${id}/execute`)
export const cancelInbound = (id: number) => request.post(`/inbound/orders/${id}/cancel`)

export const listOutbound = (params: any) => request.get('/outbound/orders', { params })
export const getOutbound = (id: number) => request.get(`/outbound/orders/${id}`)
export const createOutbound = (data: any) => request.post('/outbound/orders', data)
export const updateOutbound = (id: number, data: any) => request.put(`/outbound/orders/${id}`, data)
export const executeOutbound = (id: number) => request.post(`/outbound/orders/${id}/execute`)
export const cancelOutbound = (id: number) => request.post(`/outbound/orders/${id}/cancel`)

// ==== 库存 ====
export const listBalances = (params: any) => request.get('/inventory/balances', { params })
export const listTransactions = (params: any) => request.get('/inventory/transactions', { params })
export const moveStock = (data: any) => request.post('/inventory/move', data)
export const listWarnings = (params: any) => request.get('/inventory/warnings', { params })

export const listTransfers = (params: any) => request.get('/transfer/orders', { params })
export const getTransfer = (id: number) => request.get(`/transfer/orders/${id}`)
export const createTransfer = (data: any) => request.post('/transfer/orders', data)
export const executeTransfer = (id: number) => request.post(`/transfer/orders/${id}/execute`)
export const cancelTransfer = (id: number) => request.post(`/transfer/orders/${id}/cancel`)

// ==== 盘点 ====
export const listStocktakes = (params: any) => request.get('/stocktake/orders', { params })
export const getStocktake = (id: number) => request.get(`/stocktake/orders/${id}`)
export const createStocktake = (data: any) => request.post('/stocktake/orders', data)
export const recordStocktake = (id: number, records: any[]) => request.post(`/stocktake/orders/${id}/record`, records)
export const finishStocktake = (id: number) => request.post(`/stocktake/orders/${id}/finish`)
export const cancelStocktake = (id: number) => request.post(`/stocktake/orders/${id}/cancel`)

// ==== 看板 / 导出 ====
export const dashboardStats = () => request.get('/dashboard/stats')
export const exportInventory = () => request.get('/export/inventory', { responseType: 'blob' })
export const exportTransactions = () => request.get('/export/transactions', { responseType: 'blob' })
