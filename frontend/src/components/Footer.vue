<script setup>
// 前台页脚
</script>

<template>
  <footer class="footer">
    <div class="footer-inner">
      <p>智博空间 —— 基于 Python Django + Vue3 的个人博客内容管理系统</p>
      <p class="sub">
        技术栈：Django 6.0 · DRF · PostgreSQL 18 + pgvector · Redis · Celery · DeepSeek AI
      </p>
      <p class="sub">创新点：AI 智能内容服务（摘要/标签/写作/RAG问答/审核）· 全文+语义混合检索（RRF融合）</p>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  background: #2c3e50;
  color: #aab8c5;
  margin-top: 40px;
  padding: 28px 16px;
}

.footer-inner {
  max-width: 1100px;
  margin: 0 auto;
  text-align: center;
  font-size: 14px;
  line-height: 1.9;
}

.sub {
  font-size: 12px;
  opacity: 0.8;
}
</style>
