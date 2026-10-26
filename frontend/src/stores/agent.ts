// frontend/src/stores/agent.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export const useAgentStore = defineStore('agent', () => {
  const messages = ref<Message[]>([])
  const connected = ref(false)
  const ws = ref<WebSocket | null>(null)

  function connect() {
    if (ws.value) return
    ws.value = new WebSocket('ws://localhost:8000/ws')

    ws.value.onopen = () => { connected.value = true }
    ws.value.onclose = () => { connected.value = false }

    ws.value.onmessage = (evt) => {
      const msg = JSON.parse(evt.data)
      if (msg.type === 'assistant_message') {
        messages.value.push({ role: 'assistant', content: msg.content })
      }
    }
  }

  function send(content: string) {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) return
    messages.value.push({ role: 'user', content })
    ws.value.send(JSON.stringify({ content }))
  }

  return { messages, connected, connect, send }
})