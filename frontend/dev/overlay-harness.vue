<script setup lang="ts">
import { ref } from 'vue'
import {
  ElButton,
  ElCheckbox,
  ElDialog,
  ElDrawer,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElRadioButton,
  ElRadioGroup,
  ElSelect,
} from 'element-plus'

const dialogOpen = ref(false)
const drawerOpen = ref(false)
const model = ref('qian')
const radio = ref('coins')
const checked = ref(true)

function openMessageBox() {
  ElMessageBox.confirm(
    '删除“接下来三个月，是否应该把精力集中在当前这个项目上？”这条起卦记录？',
    '删除历史记录',
    { confirmButtonText: '删除', cancelButtonText: '保留', type: 'warning' },
  ).catch(() => {})
}

function openMessage(kind: 'success' | 'warning' | 'error') {
  const text = {
    success: '起卦完成，已保存到历史记录。',
    warning: '先写下要占问的问题。',
    error: '导出 Markdown 失败：磁盘不可写。',
  }[kind]
  ElMessage[kind](text)
}
</script>

<template>
  <main class="harness">
    <h1>Element Plus 浮层自检</h1>
    <p class="harness__hint">仅用于深浅主题验收，不进入产品构建。</p>

    <section class="harness__row">
      <button id="btn-dialog" class="probe" @click="dialogOpen = true">打开 el-dialog</button>
      <button id="btn-drawer" class="probe" @click="drawerOpen = true">打开 el-drawer</button>
      <button id="btn-messagebox" class="probe" @click="openMessageBox">打开 el-message-box</button>
      <button id="btn-message-ok" class="probe" @click="openMessage('success')">成功提示</button>
      <button id="btn-message-warn" class="probe" @click="openMessage('warning')">警示提示</button>
      <button id="btn-message-error" class="probe" @click="openMessage('error')">失败提示</button>
    </section>

    <section class="harness__row">
      <el-select id="probe-select" v-model="model" placeholder="选择会话" style="width: 220px">
        <el-option value="qian" label="乾为天 · 2026-10-24" />
        <el-option value="kun" label="坤为地 · 2026-10-24" />
        <el-option value="tun" label="水雷屯 · 2026-10-25" />
      </el-select>
      <el-input id="probe-input" placeholder="输入一件具体想思考的事……" style="width: 240px" />
      <el-button id="probe-focus" type="primary">可聚焦按钮</el-button>
    </section>

    <section class="harness__row">
      <el-radio-group v-model="radio">
        <el-radio-button value="coins">铜钱起卦</el-radio-button>
        <el-radio-button value="manual">手动输入</el-radio-button>
      </el-radio-group>
      <el-checkbox id="probe-checkbox" v-model="checked">启用 AI 辅助</el-checkbox>
      <el-button disabled>禁用按钮</el-button>
      <el-select model-value="" placeholder="已禁用的选择器" disabled style="width: 190px">
        <el-option value="x" label="不可选" />
      </el-select>
    </section>

    <el-dialog id="probe-dialog" v-model="dialogOpen" title="起卦记录" width="420px">
      <p>删除后不可恢复。若要保留，请选择“保留”。</p>
      <p class="harness__muted">这是 dialog 的正文，用来核对暗色下的文字与表面层级。</p>
      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" @click="dialogOpen = false">确认</el-button>
      </template>
    </el-dialog>

    <el-drawer id="probe-drawer" v-model="drawerOpen" title="历史记录" size="360px">
      <p>抽屉里的正文同样需要在暗色下可读。</p>
      <el-button type="primary">查看详情</el-button>
    </el-drawer>
  </main>
</template>

<style scoped>
.harness {
  padding: 24px 28px;
  display: grid;
  gap: 18px;
  max-width: 900px;
}
.harness h1 {
  margin: 0;
  font-size: 22px;
  color: var(--text-primary);
}
.harness__hint {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}
.harness__row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.harness__muted {
  color: var(--text-secondary);
}
.probe {
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text-primary);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.probe:hover {
  border-color: var(--accent-line);
  color: var(--accent);
}
</style>
