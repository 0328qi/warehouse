<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { dashboardStats } from '@/api/modules'

const stats = ref<any>({})
const trendRef = ref<HTMLElement>()

onMounted(async () => {
  stats.value = await dashboardStats()
  if (trendRef.value) {
    const chart = echarts.init(trendRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['入库', '出库'] },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: stats.value.trend.map((t: any) => t.date.slice(5)) },
      yAxis: { type: 'value' },
      series: [
        { name: '入库', type: 'line', smooth: true, data: stats.value.trend.map((t: any) => t.in), itemStyle: { color: '#67c23a' } },
        { name: '出库', type: 'line', smooth: true, data: stats.value.trend.map((t: any) => t.out), itemStyle: { color: '#f56c6c' } },
      ],
    })
    window.addEventListener('resize', () => chart.resize())
  }
})
</script>

<template>
  <div style="padding: 12px">
    <el-row :gutter="12">
      <el-col :span="6">
        <el-card>
          <el-statistic title="库存总量" :value="stats.total_qty || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="今日入库" :value="stats.today_in || 0" style="--el-statistic-content-color: #67c23a" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="今日出库" :value="stats.today_out || 0" style="--el-statistic-content-color: #f56c6c" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <el-statistic title="库存预警" :value="stats.warning_count || 0" style="--el-statistic-content-color: #e6a23c" />
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="12" style="margin-top: 12px">
      <el-col :span="16">
        <el-card header="近 7 天出入库趋势">
          <div ref="trendRef" style="height: 320px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card header="概况">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="商品总数">{{ stats.goods_count || 0 }}</el-descriptions-item>
            <el-descriptions-item label="有货库位数">{{ stats.sku_locations || 0 }}</el-descriptions-item>
            <el-descriptions-item label="进行中盘点">{{ stats.processing_stocktakes || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
