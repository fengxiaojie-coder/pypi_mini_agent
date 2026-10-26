<template>
  <div class="chat">
    <div class="messages">
      <div v-for="(m, i) in store.messages" :key="i" :class="['msg', m.role]">
        <strong>{{ m.role === 'user' ? '你' : 'Agent' }}:</strong>
        <span>{{ m.content }}</span>
      </div>
    </div>
    <div class="input">
      <input v-model="input" @keyup.enter="submit" placeholder="输入消息..." :disabled="!store.connected" />
      <button @click="submit" :disabled="!store.connected">发送</button>
    </div>
    <p v-if="!store.connected" class="warn">未连接后端</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAgentStore } from '../stores/agent'

const store = useAgentStore()
const input = ref('')

onMounted(() => store.connect())

function submit() {
  if (!input.value.trim()) return
  store.send(input.value.trim())
  input.value = ''
}
</script>

<style scoped>
.chat { max-width: 800px; margin: 20px auto; font-family: sans-serif; }
.messages { min-height: 400px; border: 1px solid #ddd; padding: 12px; margin-bottom: 10px; overflow-y: auto; }
.msg { margin: 8px 0; padding: 8px; border-radius: 6px; }
.msg.user { background: #e3f2fd; }
.msg.assistant { background: #f5f5f5; }
.input { display: flex; gap: 8px; }
.input input { flex: 1; padding: 8px; }
.warn { color: red; }
</style>