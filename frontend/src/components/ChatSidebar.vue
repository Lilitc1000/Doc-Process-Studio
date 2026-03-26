<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <h2>⚙️ 设置</h2>
    </div>
    
    <div class="sidebar-content">
      <div class="model-selector">
        <label for="model-select">选择模型</label>
        <select
          id="model-select"
          :value="selectedModel"
          @change="$emit('select-model', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="model in models" :key="model" :value="model">
            {{ model }}
          </option>
        </select>
      </div>

      <div class="info-section">
        <h3>💡 提示</h3>
        <ul>
          <li>支持多种文档格式（PDF、Word、Excel、PPT）</li>
          <li>支持自然语言提问</li>
          <li>支持多轮对话</li>
          <li>上传文件后，AI 会自动分析内容</li>
        </ul>
      </div>

      <div class="info-section">
        <h3>📊 状态</h3>
        <p>模型：{{ selectedModel }}</p>
        <p>消息数：{{ messagesCount }}</p>
      </div>
    </div>

    <div class="sidebar-footer">
      <button class="clear-btn" @click="$emit('clear-chat')">
        清空对话
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
defineProps<{
  models: string[];
  selectedModel: string;
  messagesCount: number;
}>();

defineEmits<{
  (e: 'select-model', model: string): void;
  (e: 'clear-chat'): void;
}>();
</script>

<style scoped>
.chat-sidebar {
  width: 280px;
  background: #1e1e1e;
  color: #e0e0e0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #333;
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid #333;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #fff;
}

.sidebar-content {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.model-selector {
  margin-bottom: 2rem;
}

.model-selector label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: #aaa;
}

.model-selector select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #444;
  border-radius: 6px;
  background: #2d2d2d;
  color: #fff;
  font-size: 0.9rem;
  cursor: pointer;
}

.model-selector select:focus {
  outline: none;
  border-color: #007acc;
}

.info-section {
  margin-bottom: 2rem;
}

.info-section h3 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  color: #007acc;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-section ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  color: #bbb;
}

.info-section li {
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.info-section p {
  margin: 0 0 0.5rem 0;
  font-size: 0.85rem;
  color: #bbb;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #333;
}

.clear-btn {
  width: 100%;
  padding: 0.6rem;
  background: #d32f2f;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.2s;
}

.clear-btn:hover {
  background: #b71c1c;
}
</style>
