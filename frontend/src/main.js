import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import NavBar from './components/NavBar.vue'
import Footer from './components/Footer.vue'
import './style.css'

const app = createApp(App)

// 注册 Pinia + 路由 + Element Plus（中文语言包）
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 全局注册通用布局组件
app.component('NavBar', NavBar)
app.component('Footer', Footer)

// 全局注册图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
