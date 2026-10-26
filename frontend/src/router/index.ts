import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/chat', component: ChatView },
  ],
})