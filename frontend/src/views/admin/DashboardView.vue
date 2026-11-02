<script setup>
// 数据统计面板：ECharts 可视化（总览卡片 + 趋势折线 + 分类饼图 + 热门榜单）
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { statsApi } from '../../api'

const overview = ref(null)
const trendData = ref([])
const catData = ref([])
const hotList = ref([])
const loading = ref(true)

let trendChart = null
let pieChart = null

function initCharts() {
  // 趋势折线图
  const trendEl = document.getElementById('trend-chart')
  if (trendEl) {
    trendChart = echarts.init(trendEl)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      // 图例固定到顶部，给左右纵轴的名称文字留出空间
      legend: { data: ['访问量', '发文数'], top: 8 },
      grid: { left: 70, right: 70, top: 50, bottom: 30 },
      xAxis: {
        type: 'category',
        data: trendData.value.map((d) => d.date.slice(5)), // MM-DD
      },
      yAxis: [
        {
          type: 'value',
          name: '访问量',
          // 名称显示在纵轴中部，避免与图例/底部重叠
          nameLocation: 'middle',
          nameGap: 45,
          nameTextStyle: { fontSize: 12 },
        },
        {
          type: 'value',
          name: '发文数',
          nameLocation: 'middle',
          nameGap: 45,
          nameTextStyle: { fontSize: 12 },
        },
      ],
      series: [
        {
          name: '访问量',
          type: 'line',
          smooth: true,
          areaStyle: { opacity: 0.15 },
          data: trendData.value.map((d) => d.views),
          itemStyle: { color: '#409eff' },
        },
        {
          name: '发文数',
          type: 'bar',
          yAxisIndex: 1,
          data: trendData.value.map((d) => d.articles),
          itemStyle: { color: '#67c23a' },
        },
      ],
    })
  }

  // 分类占比饼图
  const pieEl = document.getElementById('pie-chart')
  if (pieEl) {
    pieChart = echarts.init(pieEl)
    pieChart.setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          name: '文章分类',
          type: 'pie',
          radius: ['35%', '65%'],
          center: ['50%', '45%'],
          data: catData.value.map((c) => ({ name: c.name, value: c.count })),
          label: { formatter: '{b}: {c}' },
        },
      ],
    })
  }
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

async function load() {
  loading.value = true
  try {
    overview.value = await statsApi.overview()
    trendData.value = await statsApi.trend(14)
    catData.value = await statsApi.categories()
    hotList.value = await statsApi.hotArticles()
    // 等待 DOM 渲染完成后再初始化图表
    setTimeout(initCharts, 100)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<template>
  <div v-loading="loading">
    <!-- 总览卡片 -->
    <el-row :gutter="16" class="cards-row">
      <el-col :span="4" v-for="card in [
        { label: '文章总数', value: overview?.article_count, icon: 'Document', color: '#409eff' },
        { label: '评论总数', value: overview?.comment_count, icon: 'ChatDotRound', color: '#67c23a' },
        { label: '用户总数', value: overview?.user_count, icon: 'User', color: '#e6a23c' },
        { label: '总访问量', value: overview?.visit_count, icon: 'View', color: '#f56c6c' },
        { label: '文章浏览量', value: overview?.total_views, icon: 'DataLine', color: '#7c5cff' },
        { label: '待审评论', value: overview?.pending_comment_count, icon: 'Bell', color: '#f56c6c' },
      ]" :key="card.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" :style="{ background: card.color + '1a', color: card.color }">
            <el-icon :size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ card.value ?? 0 }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 + 饼图 -->
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header><b>近 14 天访问趋势</b></template>
          <div id="trend-chart" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><b>文章分类分布</b></template>
          <div id="pie-chart" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 热门文章 TOP10 -->
    <el-card class="hot-card">
      <template #header><b>热门文章 TOP10（按浏览量）</b></template>
      <el-table :data="hotList" stripe>
        <el-table-column type="index" label="排名" width="70" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="views" label="浏览量" width="120" sortable />
        <el-table-column prop="likes" label="点赞" width="100" sortable />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.cards-row {
  margin-bottom: 16px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #1f2d3d;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.hot-card {
  margin-top: 16px;
}
</style>
