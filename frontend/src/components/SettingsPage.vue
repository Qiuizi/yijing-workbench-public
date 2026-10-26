<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'
import type { AIModel, AISettings, AppPreferences } from '../types'
import { isTauri } from '@tauri-apps/api/core'
import { open } from '@tauri-apps/plugin-dialog'
import { DEEPSEEK_PLATFORM_TERMS_URL, DEEPSEEK_PRIVACY_URL, MICROSOFT_PRIVACY_URL, requireAIPrivacyAcknowledgement, WEBVIEW2_PRIVACY_URL } from '../aiPrivacyNotice'
import { version as appVersion } from '../../src-tauri/tauri.conf.json'
import { useAppearance, type Appearance } from '../appearance'
import licenseText from '../../../LICENSE?raw'

const settings = ref<AISettings | null>(null)
const keyInput = ref('')
const models = ref<AIModel[]>([])
const selectedModel = ref('')
const loading = ref(false)
const busy = ref(false)
const connectionMessage = ref('')
const preferences = ref<AppPreferences | null>(null)
const defaultMethod = ref<'coins' | 'manual'>('coins')
const timezone = ref('Asia/Shanghai')
const aiDefaultMode = ref<'classical' | 'najia'>('classical')
const isDesktop = isTauri()
const migrationStatus = ref<{ can_import: boolean; history_count: number; ai_session_count: number; has_settings: boolean } | null>(null)
const importing = ref(false)
const { mode: appearanceMode, setMode: setAppearance } = useAppearance()

function applyAppearance(value: string | number | boolean | undefined) {
  if (value === 'auto' || value === 'light' || value === 'dark') {
    setAppearance(value as Appearance)
  }
}

async function refresh() {
  loading.value = true
  try {
    settings.value = await api.aiSettings()
    preferences.value = await api.preferences()
    defaultMethod.value = preferences.value.default_method
    timezone.value = preferences.value.timezone
    aiDefaultMode.value = preferences.value.ai_default_mode
    if (isDesktop) migrationStatus.value = await api.desktopMigrationStatus()
    selectedModel.value = settings.value.model_id ?? ''
    if (settings.value.api_key_configured) await fetchModels()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取 AI 设置失败。')
  } finally {
    loading.value = false
  }
}

async function importLegacyDatabase() {
  if (!migrationStatus.value?.can_import) {
    ElMessage.warning('桌面版已有记录或设置。为避免覆盖，旧版数据只能导入到空白桌面档案。')
    return
  }
  try {
    const selected = await open({
      multiple: false,
      directory: false,
      title: '选择易经 Web 版 SQLite 数据库',
      filters: [{ name: 'SQLite 数据库', extensions: ['sqlite3', 'sqlite', 'db'] }],
    })
    if (typeof selected !== 'string') return
    await ElMessageBox.confirm(
      '应用会先在桌面版用户数据目录创建备份，再将旧记录复制到空白桌面档案。源数据库不会移动或删除；其中的 DPAPI 密钥只在当前 Windows 用户可验证时才会一并导入。',
      '确认导入旧版数据',
      { confirmButtonText: '备份并导入', cancelButtonText: '取消', type: 'info' },
    )
    importing.value = true
    const result = await api.importDesktopDatabase(selected)
    settings.value = await api.aiSettings()
    preferences.value = await api.preferences()
    defaultMethod.value = preferences.value.default_method
    timezone.value = preferences.value.timezone
    aiDefaultMode.value = preferences.value.ai_default_mode
    selectedModel.value = settings.value.model_id ?? ''
    migrationStatus.value = await api.desktopMigrationStatus()
    ElMessage.success(`已导入 ${result.counts.divinations ?? 0} 条记录。原库未改动，备份已保存至：${result.backup_path}`)
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(error instanceof Error ? error.message : '旧版数据导入失败。')
    }
  } finally {
    importing.value = false
  }
}

async function savePreferences() {
  busy.value = true
  try {
    preferences.value = await api.updatePreferences(defaultMethod.value, timezone.value.trim(), aiDefaultMode.value)
    ElMessage.success('应用偏好已保存。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存应用偏好失败。')
  } finally {
    busy.value = false
  }
}

async function fetchModels(): Promise<boolean> {
  if (!(await requireAIPrivacyAcknowledgement())) return false
  const response = await api.aiModels()
  models.value = response.models
  if (!selectedModel.value && models.value.length) selectedModel.value = models.value[0].id
  return true
}

async function refreshModels() {
  busy.value = true
  try {
    if (await fetchModels()) ElMessage.success('模型列表已刷新。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '刷新模型列表失败。')
  } finally {
    busy.value = false
  }
}

async function saveKey() {
  if (!keyInput.value.trim()) {
    ElMessage.warning('请先输入 DeepSeek API Key。')
    return
  }
  busy.value = true
  try {
    settings.value = await api.updateAiSettings({ api_key: keyInput.value.trim() })
    keyInput.value = ''
    await fetchModels()
    ElMessage.success('API Key 已由本机后端保护并保存。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存 API Key 失败。')
  } finally {
    busy.value = false
  }
}

async function saveModel() {
  if (!selectedModel.value) return
  if (!(await requireAIPrivacyAcknowledgement())) return
  busy.value = true
  try {
    settings.value = await api.updateAiSettings({ model_id: selectedModel.value })
    ElMessage.success('模型设置已保存。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存模型设置失败。')
  } finally {
    busy.value = false
  }
}

async function toggleAI() {
  if (!settings.value) return
  busy.value = true
  try {
    settings.value = await api.updateAiSettings({ ai_enabled: !settings.value.ai_enabled })
    ElMessage.success(settings.value.ai_enabled ? 'AI 辅助解读已启用。' : 'AI 辅助解读已关闭。')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '更新 AI 开关失败。')
  } finally {
    busy.value = false
  }
}

async function testConnection() {
  if (!(await requireAIPrivacyAcknowledgement())) return
  busy.value = true
  connectionMessage.value = ''
  try {
    const result = await api.testAiConnection()
    connectionMessage.value = `连接成功，当前可用模型 ${result.available_models} 个。`
    ElMessage.success(connectionMessage.value)
  } catch (error) {
    connectionMessage.value = error instanceof Error ? error.message : '连接失败。'
    ElMessage.error(connectionMessage.value)
  } finally {
    busy.value = false
  }
}

async function removeKey() {
  try {
    await ElMessageBox.confirm('删除保存在本机的 DeepSeek API Key，并关闭 AI 功能？', '删除 API Key', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    busy.value = true
    await api.deleteAiKey()
    settings.value = await api.aiSettings()
    models.value = []
    selectedModel.value = ''
    ElMessage.success('API Key 已删除。')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '删除 API Key 失败。')
  } finally {
    busy.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section v-loading="loading" class="page-panel panel settings-page" aria-label="设置">
    <div class="section-heading">
      <div><span class="section-index">06</span><h2>设置</h2></div>
      <span v-if="settings" class="settings-state" :class="{ 'settings-state--on': settings.ai_enabled }">{{ settings.ai_enabled ? 'AI 已启用' : 'AI 已关闭' }}</span>
    </div>
    <details class="settings-category" open><summary>基础偏好 <span>起卦方式、时区与默认解读体系</span></summary>
    <section class="settings-group" aria-labelledby="settings-casting-title">
      <div class="settings-group__heading"><span class="settings-group__index">01</span><div><h3 id="settings-casting-title">起卦</h3><p>选择进入起卦页面时默认使用的方式。</p></div></div>
      <div class="settings-field">
        <label for="default-method">默认起卦方式</label>
        <div class="settings-field__row">
          <el-select id="default-method" v-model="defaultMethod" aria-label="默认起卦方式">
            <el-option value="coins" label="三枚铜钱" />
            <el-option value="manual" label="手动输入" />
          </el-select>
        </div>
      </div>
    </section>

    <section class="settings-group" aria-labelledby="settings-calendar-title">
      <div class="settings-group__heading"><span class="settings-group__index">02</span><div><h3 id="settings-calendar-title">历法</h3><p>时间使用明确的 IANA 时区，历法结果及约定保存在历史上下文。</p></div></div>
      <div class="settings-field">
        <label for="default-timezone">默认时区</label>
        <div class="settings-field__row"><el-input id="default-timezone" v-model="timezone" aria-label="默认 IANA 时区" placeholder="如 Asia/Shanghai" /></div>
      </div>
      <details class="settings-calendar-details">
        <summary>查看自动计算与日界约定</summary>
        <div class="settings-calendar-rules__grid">
          <span><strong>历法库</strong>lunar_python 1.4.8 · tzdata 2026.4</span>
          <span><strong>日界</strong>所选 IANA 时区民用日 00:00；23:00–23:59 按当日</span>
          <span><strong>月建</strong>按 UTC+08:00 太阳节气交接</span>
          <span><strong>夏令时</strong>不存在或重复的本地时刻拒绝自动计算</span>
          <span><strong>范围</strong>1901–2100 年；范围外可手动输入干支</span>
          <span><strong>输入方式</strong>排盘时选择自动计算或手动提供日干支、月建</span>
        </div>
      </details>
      <small>当前唯一启用的传统取辞体系：{{ preferences?.ruleset_id ?? 'qiming-tongshi' }} · {{ preferences?.ruleset_version ?? '1.0.0' }}。</small>
    </section>

    <section class="settings-group" aria-labelledby="settings-appearance-title">
      <div class="settings-group__heading"><span class="settings-group__index">03</span><div><h3 id="settings-appearance-title">外观</h3><p>浅色与夜间共用同一套排版；夜间整体字号略收一档。</p></div></div>
      <div class="settings-field">
        <label>主题</label>
        <div class="settings-field__row">
          <el-radio-group :model-value="appearanceMode" @change="applyAppearance">
            <el-radio-button value="auto">跟随系统</el-radio-button>
            <el-radio-button value="light">浅色</el-radio-button>
            <el-radio-button value="dark">夜间</el-radio-button>
          </el-radio-group>
        </div>
        <small>仅保存在本机浏览器存储；不起卦、不联网。</small>
      </div>
    </section>

      <div class="settings-field">
        <label for="ai-default-mode">默认解读体系</label>
        <div class="settings-field__row">
          <el-select id="ai-default-mode" v-model="aiDefaultMode" aria-label="默认 AI 解读体系">
            <el-option value="classical" label="《周易》经文" />
            <el-option value="najia" label="六爻纳甲" />
          </el-select>
        </div>
        <small>偏好保存在本机，AI 请求仍需主动触发。</small>
      </div>
    <div class="settings-preferences-save"><el-button type="primary" :loading="busy" @click="savePreferences">保存默认偏好</el-button></div></details>
    <details class="settings-category"><summary>AI 辅助 <span>启用、连接配置与模型</span></summary>
    <section class="settings-group" aria-labelledby="settings-ai-title">
      <div class="settings-group__heading"><span class="settings-group__index">04</span><div><h3 id="settings-ai-title">AI 辅助</h3><p>模型清单从 DeepSeek 读取；密钥由后端保护，页面不会回显。</p></div><span class="settings-state" :class="{ 'settings-state--on': settings?.api_key_configured }">{{ settings?.api_key_configured ? '密钥已配置' : '未配置' }}</span></div>
      <div class="settings-field">
        <label for="deepseek-key">DeepSeek API Key</label>
        <div class="settings-field__row">
          <el-input id="deepseek-key" v-model="keyInput" type="password" autocomplete="new-password" :placeholder="settings?.api_key_configured ? '已配置；输入新密钥可替换' : '粘贴 DeepSeek API Key'" />
          <el-button type="primary" :loading="busy" @click="saveKey">保存密钥</el-button>
        </div>
        <small>{{ settings?.api_key_configured ? '密钥由 Windows 当前用户 DPAPI 保护，不会显示或写入前端存储；调用 DeepSeek 时会经 HTTPS Bearer 身份验证发送。' : '保存时通过本机回环连接交给后端并用 DPAPI 保护；调用 DeepSeek 时会经 HTTPS Bearer 身份验证发送。' }}</small>
      </div>
      <div class="settings-field">
        <label for="ai-model">当前模型</label>
        <div class="settings-field__row">
          <el-select id="ai-model" v-model="selectedModel" :disabled="!settings?.api_key_configured || !models.length" placeholder="先配置 API Key 并读取模型">
            <el-option v-for="model in models" :key="model.id" :value="model.id" :label="model.id" />
          </el-select>
          <el-button plain :loading="busy" :disabled="!settings?.api_key_configured" @click="refreshModels">刷新模型</el-button>
          <el-button plain :loading="busy" :disabled="!settings?.api_key_configured" @click="testConnection">连接测试</el-button>
          <el-button :loading="busy" :disabled="!selectedModel || selectedModel === settings?.model_id" @click="saveModel">保存模型</el-button>
        </div>
        <small v-if="connectionMessage" class="settings-message" role="status">{{ connectionMessage }}</small>
      </div>
      <div class="settings-field settings-field--toggle">
        <div><label>AI 辅助解读</label><small>关闭后仍可正常起卦、查看传统原文和纳甲排盘。</small></div>
        <el-button :type="settings?.ai_enabled ? 'success' : 'primary'" :loading="busy" :disabled="!settings?.api_key_configured || !settings?.model_id" @click="toggleAI">{{ settings?.ai_enabled ? '已启用 · 点击关闭' : '点击启用' }}</el-button>
      </div>
      <el-button v-if="settings?.api_key_configured" text type="danger" :loading="busy" @click="removeKey">删除本机 API Key</el-button>
      <div class="settings-limit">
        <strong>AI 内容说明</strong>
        <p>AI 输出是现代语言辅助，不是确定的未来判断；重要医疗、法律、财务或安全决定应依据专业意见和现实证据。</p>
      </div>

    </section>

    </details>
    <details class="settings-category"><summary>数据与隐私 <span>本地存储、旧库导入与联网说明</span></summary>
      <div class="settings-limit privacy-notice">
        <strong>本地与联网隐私说明</strong>
        <p>起卦记录、偏好设置和 AI 会话保存在本机 SQLite；这不等于应用绝不联网。关闭 AI 后，铜钱起卦、手动起卦、排盘和本地历史仍可使用。</p>
        <details class="settings-calendar-details">
          <summary>查看 AI、密钥和 WebView2 的数据处理说明</summary>
          <div class="settings-calendar-rules__grid">
            <span><strong>模型清单、连接测试和模型校验</strong>应用向 DeepSeek API 发送 API Key（HTTPS Bearer 身份验证）；这些操作不发送卦象问题或聊天内容。</span>
            <span><strong>AI 对话请求</strong>发送本条消息、起卦问题、起卦方法、卦象/爻值/动爻、所选分析模式及该模式需要的经文取辞或纳甲排盘与规则证据，并附带当前会话的此前消息；不会自动发送其他历史会话或 SQLite 文件。</span>
            <span><strong>目的与结果</strong>上述内容用于向 DeepSeek 请求模型回答。回答和会话历史保存在本机 SQLite；DeepSeek 对 API 请求数据的处理和留存由其适用条款决定，本应用不承诺服务方不会保存。</span>
            <span><strong>API Key</strong>密钥经本机回环连接提交给后端，以 Windows 当前用户 DPAPI 保护后保存在本机 SQLite；调用 DeepSeek 时会通过 HTTPS Bearer 身份验证发送，密钥不会作为提示词内容。</span>
            <span><strong>WebView2 SmartScreen</strong>桌面界面使用 WebView2；应用未关闭默认启用的 Microsoft Defender SmartScreen。SmartScreen 可能向 Microsoft 发送用户信息用于信誉检查。</span>
            <span><strong>WebView2 诊断</strong>可选诊断数据受 Windows“设置 → 隐私和安全性 → 诊断和反馈”控制；Microsoft 说明，必要的可靠性和性能数据仍可能收集。若系统缺少 Evergreen Runtime，安装程序会使用 Microsoft 官方 Bootstrapper 下载运行时。</span>
            <span><strong>DeepSeek 文档</strong><a :href="DEEPSEEK_PRIVACY_URL" target="_blank" rel="noopener noreferrer">隐私政策</a> · <a :href="DEEPSEEK_PLATFORM_TERMS_URL" target="_blank" rel="noopener noreferrer">开放平台条款</a>。DeepSeek 现行通用隐私政策说明，开发者使用开放平台构建的下游应用中终端用户数据的处理不由该通用政策覆盖；请查阅适用的开放平台条款。</span>
            <span><strong>Microsoft 文档</strong><a :href="WEBVIEW2_PRIVACY_URL" target="_blank" rel="noopener noreferrer">WebView2 数据与隐私</a> · <a :href="MICROSOFT_PRIVACY_URL" target="_blank" rel="noopener noreferrer">Microsoft 隐私声明</a>。</span>
          </div>
        </details>
      </div>
    <section v-if="isDesktop" class="settings-group" aria-labelledby="settings-data-title">
      <div class="settings-group__heading"><span class="settings-group__index">05</span><div><h3 id="settings-data-title">本地数据</h3><p>导入会先备份，来源文件保持原位。</p></div></div>
      <div class="settings-field">
        <label>导入 Web 版历史数据</label>
        <div class="settings-field__row">
          <span class="settings-inline-label">{{ migrationStatus?.can_import ? '桌面档案为空，可安全导入' : `当前已有 ${migrationStatus?.history_count ?? 0} 条记录或设置，导入已锁定` }}</span>
          <el-button :loading="importing" :disabled="!migrationStatus?.can_import" @click="importLegacyDatabase">选择 SQLite 文件并导入</el-button>
        </div>
        <small>包含 DPAPI 密钥时，必须由当前 Windows 用户解密；应用不会移动或删除源数据库。</small>
      </div>
    </section>

    </details>
    <details class="settings-category"><summary>关于应用 <span>版本、许可证与典籍来源</span></summary>
    <section class="settings-group settings-about" aria-labelledby="settings-about-title">
      <div class="settings-group__heading"><span class="settings-group__index">06</span><div><h3 id="settings-about-title">关于</h3><p>版本与内容来源</p></div></div>
      <dl class="settings-about__facts">
        <div><dt>当前界面版本</dt><dd>V{{ appVersion }}</dd></div>
        <div><dt>业务逻辑稳定核心</dt><dd>V3.1.4</dd></div>
        <div><dt>典籍资料</dt><dd>《周易》卦辞、爻辞及特殊爻辞按本地数据所列维基文库页面和修订来源收录。</dd></div>
        <div><dt>典籍转录许可</dt><dd>适用独立来源许可，来源页面标注 CC BY-SA 4.0；逐卦来源链接与修订号见数据记录，不适用项目 MIT 许可。</dd></div>
        <div><dt>应用代码许可证</dt><dd>MIT，仅适用于 Qiuizi 有权授权的项目自有代码、自动化测试、构建配置及原创 SVG 与生成图标，不覆盖古籍数据或第三方组件。</dd></div>
        <div><dt>第三方组件许可</dt><dd>各自适用独立许可证，详见随附 THIRD_PARTY_NOTICES.txt。</dd></div>
      </dl>
      <details class="settings-calendar-details">
        <summary>查看项目 LICENSE 全文</summary>
        <pre class="settings-license-text">{{ licenseText }}</pre>
      </details>
    </section>
    </details>
  </section>
</template>
