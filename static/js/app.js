/**
 * TTS OPEN 管理平台 - 前端 JavaScript
 */

// 全局状态
let currentAudioBlob = null;
let currentAudioFormat = 'mp3';
let currentHistoryPlayId = null;
let channelCache = [];
let voicesLoaded = false;

// ─── 认证 ───────────────────────────────────────────────
const SESSION_KEY = 'tts_open_token';

function getToken() {
    return sessionStorage.getItem(SESSION_KEY) || '';
}

function setToken(token) {
    sessionStorage.setItem(SESSION_KEY, token);
}

function clearToken() {
    sessionStorage.removeItem(SESSION_KEY);
}

/** 带认证头的 fetch 封装 */
async function apiFetch(url, options = {}) {
    const headers = {
        ...(options.headers || {}),
        'Authorization': `Bearer ${getToken()}`,
    };
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401) {
        clearToken();
        showLoginModal();
        throw new Error('未授权，请重新登录');
    }
    return resp;
}

function showLoginModal() {
    document.getElementById('login-modal').classList.remove('hidden');
}

function hideLoginModal() {
    document.getElementById('login-modal').classList.add('hidden');
}

async function submitLogin() {
    const password = document.getElementById('login-password').value;
    if (!password) {
        document.getElementById('login-error').textContent = '请输入密码';
        return;
    }
    // 用密码试请求一个需要认证的接口
    try {
        const resp = await fetch('/api/v1/channels', {
            headers: { 'Authorization': `Bearer ${password}` }
        });
        if (resp.status === 401) {
            document.getElementById('login-error').textContent = '密码错误';
            return;
        }
        setToken(password);
        document.getElementById('login-error').textContent = '';
        document.getElementById('login-password').value = '';
        hideLoginModal();
        initApp();
    } catch (e) {
        document.getElementById('login-error').textContent = '登录失败: ' + e.message;
    }
}

// ─── 初始化 ──────────────────────────────────────────────
function initApp() {
    initEventListeners();
    loadChannels();
    loadHistory();
    updateCharCount();
    document.getElementById('app-main').classList.remove('hidden');
    document.getElementById('app-nav').classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    // 回车提交登录
    document.getElementById('login-password').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') submitLogin();
    });

    if (!getToken()) {
        showLoginModal();
        return;
    }
    initApp();
});

function resetHistoryPlayButton(button) {
    if (!button) return;
    button.innerHTML = '<i class="fas fa-play"></i>';
    button.classList.remove('text-emerald-600', 'bg-emerald-50');
    button.classList.add('text-primary');
    button.removeAttribute('data-playing');
}

// 事件监听
function initEventListeners() {
    // 字符计数
    document.getElementById('input-text').addEventListener('input', updateCharCount);
    
    // 渠道选择变化时更新语音列表
    document.getElementById('channel-select').addEventListener('change', function() {
        loadVoices(this.value);
        updateAzureStyleVisibility();
    });

    // 语音选择变化时，若包含风格则显示风格选项
    document.getElementById('voice-select').addEventListener('change', function() {
        syncAzureStyleFromVoice();
    });

    const historyFilter = document.getElementById('history-format-filter');
    if (historyFilter) {
        historyFilter.addEventListener('change', function() {
            loadHistory();
        });
    }
}

// 切换标签页
function switchTab(tabName) {
    // 隐藏所有页面
    document.querySelectorAll('.page-content').forEach(page => {
        page.classList.add('hidden');
    });
    
    // 显示目标页面
    document.getElementById(`page-${tabName}`).classList.remove('hidden');
    
    // 更新标签样式
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-gray-100', 'text-gray-800', 'font-medium');
        btn.classList.add('text-gray-500');
    });

    const activeTab = document.getElementById(`tab-${tabName}`);
    activeTab.classList.remove('text-gray-500');
    activeTab.classList.add('bg-gray-100', 'text-gray-800', 'font-medium');
    
    // 切换到历史记录时刷新（数据量小，无副作用）
    if (tabName === 'history') {
        loadHistory();
    }
}

// 更新字符计数
function updateCharCount() {
    const text = document.getElementById('input-text').value;
    document.getElementById('char-count').textContent = text.length;
}

// 清空文本
function clearText() {
    document.getElementById('input-text').value = '';
    updateCharCount();
}

// 插入示例文本
function insertSampleText() {
    const samples = [
        "你好，这是一个 TTS 语音合成测试。",
        "Hello, this is a text-to-speech synthesis test.",
        "欢迎使用 TTS OPEN 管理平台，支持多种语音合成渠道。",
        "The quick brown fox jumps over the lazy dog.",
        "今天天气真好，适合出去散步。人工智能正在改变我们的生活方式。"
    ];
    const randomSample = samples[Math.floor(Math.random() * samples.length)];
    document.getElementById('input-text').value = randomSample;
    updateCharCount();
}

// 更新语速显示
function updateSpeedDisplay(value) {
    document.getElementById('speed-value').textContent = value + 'x';
}

// 加载渠道列表
async function loadChannels() {
    try {
        const response = await apiFetch('/api/v1/channels');
        const result = await response.json();
        
        if (result.success) {
            channelCache = result.data.items || [];
            updateChannelSelect(channelCache);
            updateChannelsList(channelCache);
            
            // 首次加载时才自动拉取音色列表
            if (!voicesLoaded) {
                const currentChannelId = document.getElementById('channel-select').value;
                if (currentChannelId) {
                    voicesLoaded = true;
                    loadVoices(currentChannelId);
                }
            }
        }
    } catch (error) {
        console.error('加载渠道失败:', error);
        showToast('加载渠道失败', 'error');
    }
}

// 更新渠道选择下拉框
function updateChannelSelect(channels) {
    const select = document.getElementById('channel-select');
    // 清空现有选项
    select.innerHTML = '';
    
    // 找到默认渠道
    let defaultChannelId = null;
    
    channels.forEach(channel => {
        const option = document.createElement('option');
        option.value = channel.id;
        option.textContent = `${channel.name} ${channel.is_default ? '(默认)' : ''}`;
        option.dataset.type = channel.type;
        select.appendChild(option);
        
        if (channel.is_default) {
            defaultChannelId = channel.id;
        }
    });
    
    // 如果有默认渠道，自动选中
    if (defaultChannelId) {
        select.value = defaultChannelId;
    } else if (channels.length > 0) {
        // 否则选中第一个
        select.value = channels[0].id;
    }

    updateAzureStyleVisibility();
}

// 更新渠道列表页面
function updateChannelsList(channels) {
    const container = document.getElementById('channels-list');
    
    if (channels.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500 col-span-full">
                <i class="fas fa-server text-4xl mb-4"></i>
                <p>暂无渠道，请点击添加</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = channels.map(channel => `
        <div class="border border-gray-200 bg-white rounded-lg p-4 hover:border-gray-300 transition">
            <div class="flex items-start justify-between">
                <div class="flex items-start gap-3">
                    <div class="w-8 h-8 rounded-md ${getChannelTypeColor(channel.type)} flex items-center justify-center flex-shrink-0">
                        <i class="fas ${getChannelTypeIcon(channel.type)} text-white text-xs"></i>
                    </div>
                    <div>
                        <div class="flex items-center flex-wrap gap-1.5">
                            <span class="text-sm font-medium text-gray-800">${channel.name}</span>
                            ${channel.is_default ? '<span class="px-1.5 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">默认</span>' : ''}
                            <span class="px-1.5 py-0.5 bg-gray-50 text-gray-400 text-xs rounded border border-gray-100">${channel.type.toUpperCase()}</span>
                        </div>
                        <div class="mt-1 flex items-center gap-2 text-xs text-gray-400">
                            <span>优先级 ${channel.priority}</span>
                            <span>·</span>
                            <span class="${getStatusColor(channel.status)}">${getStatusText(channel.status)}</span>
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-1">
                    <button onclick="testChannel('${channel.id}')"
                            class="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-50 rounded transition"
                            title="测试">
                        <i class="fas fa-plug text-xs"></i>
                    </button>
                    <button onclick="deleteChannel('${channel.id}')"
                            class="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition"
                            title="删除"
                            ${channel.is_default ? 'disabled' : ''}>
                        <i class="fas fa-trash text-xs"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// 获取渠道类型颜色
function getChannelTypeColor(type) {
    const colors = {
        'openai': 'bg-green-500',
        'azure': 'bg-blue-500',
        'google': 'bg-red-500',
        'elevenlabs': 'bg-purple-500',
        'edge': 'bg-cyan-500',
        'custom': 'bg-gray-500',
        'local': 'bg-orange-500',
        'nami': 'bg-yellow-500'
    };
    return colors[type] || 'bg-gray-500';
}

// 获取渠道类型图标
function getChannelTypeIcon(type) {
    const icons = {
        'openai': 'fa-atom',
        'azure': 'fa-cloud',
        'google': 'fa-g',
        'elevenlabs': 'fa-waveform',
        'edge': 'fa-bolt',
        'custom': 'fa-sliders',
        'local': 'fa-house-laptop',
        'nami': 'fa-robot'
    };
    return icons[type] || 'fa-layer-group';
}

// 获取状态颜色
function getStatusColor(status) {
    const colors = {
        'active': 'text-green-600',
        'inactive': 'text-gray-500',
        'error': 'text-red-600'
    };
    return colors[status] || 'text-gray-500';
}

// 获取状态文本
function getStatusText(status) {
    const texts = {
        'active': '活跃',
        'inactive': '停用',
        'error': '错误'
    };
    return texts[status] || status;
}

// 加载语音列表
async function loadVoices(channelId) {
    const select = document.getElementById('voice-select');
    select.innerHTML = '<option value="">加载中...</option>';
    select.disabled = true;

    try {
        const url = channelId ? `/api/v1/voices?channel_id=${channelId}` : '/api/v1/voices';
        const response = await apiFetch(url);
        const result = await response.json();
        
        if (result.voices && result.voices.length > 0) {
            updateVoiceSelect(result.voices);
            syncAzureStyleFromVoice();
        } else {
            select.innerHTML = '<option value="">该渠道暂无可用语音</option>';
            syncAzureStyleFromVoice();
        }
    } catch (error) {
        console.error('加载语音列表失败:', error);
        select.innerHTML = '<option value="">加载失败</option>';
        syncAzureStyleFromVoice();
    } finally {
        select.disabled = false;
    }
}

// 更新语音选择下拉框
function updateVoiceSelect(voices) {
    const select = document.getElementById('voice-select');
    select.innerHTML = voices.map(voice => `
        <option value="${voice.id}">${voice.name} ${voice.description ? '- ' + voice.description : ''}</option>
    `).join('');
}

function getSelectedChannelType() {
    const channelSelect = document.getElementById('channel-select');
    const option = channelSelect?.selectedOptions?.[0];
    return option?.dataset?.type || '';
}

function updateAzureStyleVisibility() {
    const styleWrapper = document.getElementById('azure-style-wrapper');
    const styleSelect = document.getElementById('azure-style-select');

    if (!styleWrapper || !styleSelect) {
        return;
    }

    const channelType = getSelectedChannelType();
    if (channelType === 'azure') {
        styleWrapper.classList.remove('hidden');
    } else {
        styleWrapper.classList.add('hidden');
        styleSelect.value = '';
    }
}

function syncAzureStyleFromVoice() {
    const voiceSelect = document.getElementById('voice-select');
    const styleSelect = document.getElementById('azure-style-select');
    const styleWrapper = document.getElementById('azure-style-wrapper');

    if (!voiceSelect || !styleSelect || !styleWrapper) {
        return;
    }

    const selectedValue = voiceSelect.value || '';
    if (selectedValue.includes('|')) {
        const parts = selectedValue.split('|');
        const styleValue = parts[1] || '';
        styleWrapper.classList.remove('hidden');
        styleSelect.value = styleValue;
    } else {
        updateAzureStyleVisibility();
        if (getSelectedChannelType() !== 'azure') {
            styleSelect.value = '';
        }
    }

    styleSelect.onchange = function() {
        const baseVoiceId = (voiceSelect.value || '').split('|')[0] || '';
        const styleValue = styleSelect.value || '';
        if (!baseVoiceId) {
            return;
        }
        const targetValue = styleValue ? `${baseVoiceId}|${styleValue}` : baseVoiceId;
        const optionExists = !!voiceSelect.querySelector(`option[value="${targetValue}"]`);
        if (optionExists) {
            voiceSelect.value = targetValue;
        }
    };
}

// 试听音频
async function previewAudio() {
    const text = document.getElementById('input-text').value.trim();
    if (!text) {
        showToast('请输入要合成的文本', 'error');
        return;
    }
    
    showAudioLoading(true);
    
    try {
        const voiceSelect = document.getElementById('voice-select');
        const styleSelect = document.getElementById('azure-style-select');
        const channelType = getSelectedChannelType();
        let voiceValue = voiceSelect.value;
        if (channelType === 'azure' && styleSelect && styleSelect.value) {
            const baseVoice = voiceValue.split('|')[0] || voiceValue;
            voiceValue = `${baseVoice}|${styleSelect.value}`;
        }

        const request = {
            text: text,
            voice: voiceValue,
            speed: parseFloat(document.getElementById('speed-slider').value),
            pitch: parseFloat(document.getElementById('pitch-slider').value),
            volume: parseFloat(document.getElementById('volume-slider').value),
            channel_id: document.getElementById('channel-select').value || null,
            response_format: document.getElementById('format-select').value
        };
        
        const response = await apiFetch('/api/v1/audio/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error('生成失败');
        }
        
        const blob = await response.blob();
        currentAudioBlob = blob;
        currentAudioFormat = request.response_format;
        
        playAudio(blob);
        showToast('试听生成成功', 'success');
        
    } catch (error) {
        console.error('试听失败:', error);
        showToast('试听生成失败: ' + error.message, 'error');
    } finally {
        showAudioLoading(false);
    }
}

// 生成音频
async function generateAudio() {
    const text = document.getElementById('input-text').value.trim();
    if (!text) {
        showToast('请输入要合成的文本', 'error');
        return;
    }
    
    showAudioLoading(true);
    
    try {
        const voiceSelect = document.getElementById('voice-select');
        const styleSelect = document.getElementById('azure-style-select');
        const channelType = getSelectedChannelType();
        let voiceValue = voiceSelect.value;
        if (channelType === 'azure' && styleSelect && styleSelect.value) {
            const baseVoice = voiceValue.split('|')[0] || voiceValue;
            voiceValue = `${baseVoice}|${styleSelect.value}`;
        }

        const request = {
            model: 'tts-1',
            input: text,
            voice: voiceValue,
            speed: parseFloat(document.getElementById('speed-slider').value),
            pitch: parseFloat(document.getElementById('pitch-slider').value),
            volume: parseFloat(document.getElementById('volume-slider').value),
            channel_id: document.getElementById('channel-select').value || null,
            response_format: document.getElementById('format-select').value
        };
        
        const response = await apiFetch('/api/v1/audio/speech', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error('生成失败');
        }
        
        const blob = await response.blob();
        currentAudioBlob = blob;
        currentAudioFormat = request.response_format;
        
        playAudio(blob);
        showToast('语音生成成功', 'success');
        
        // 刷新历史记录
        loadHistory();
        
    } catch (error) {
        console.error('生成失败:', error);
        showToast('语音生成失败: ' + error.message, 'error');
    } finally {
        showAudioLoading(false);
    }
}

// 播放音频
function playAudio(blob) {
    const url = URL.createObjectURL(blob);
    const player = document.getElementById('audio-player');
    player.src = url;
    
    document.getElementById('audio-placeholder').classList.add('hidden');
    document.getElementById('audio-loading').classList.add('hidden');
    document.getElementById('audio-player-container').classList.remove('hidden');
    
    player.play();
}

// 显示/隐藏加载状态
function showAudioLoading(show) {
    if (show) {
        document.getElementById('audio-placeholder').classList.add('hidden');
        document.getElementById('audio-player-container').classList.add('hidden');
        document.getElementById('audio-loading').classList.remove('hidden');
    } else {
        document.getElementById('audio-loading').classList.add('hidden');
    }
}

// 下载音频
function downloadAudio() {
    if (!currentAudioBlob) {
        showToast('没有可下载的音频', 'error');
        return;
    }
    
    const url = URL.createObjectURL(currentAudioBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `speech_${Date.now()}.${currentAudioFormat}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('下载开始', 'success');
}

// 加载历史记录
async function loadHistory() {
    try {
        const response = await apiFetch('/api/v1/history?limit=20');
        const result = await response.json();
        
        if (result.success) {
            const filter = document.getElementById('history-format-filter');
            const format = filter ? filter.value : '';
            const data = format
                ? result.data.filter(item => (item.format || '').toLowerCase() === format)
                : result.data;
            updateHistoryList(data);
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

// 更新历史列表
function updateHistoryList(history) {
    const container = document.getElementById('history-list');
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500 col-span-full">
                <i class="fas fa-history text-4xl mb-4"></i>
                <p>暂无历史记录</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.map(item => `
        <div class="border border-gray-200 bg-white rounded-lg p-4 hover:border-gray-300 transition">
            <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-700 line-clamp-2">${item.text}</p>
                    <div class="mt-2 flex flex-wrap items-center gap-1.5">
                        <span class="px-1.5 py-0.5 bg-gray-50 text-gray-500 text-xs rounded border border-gray-100">${item.voice}</span>
                        <span class="px-1.5 py-0.5 bg-gray-50 text-gray-500 text-xs rounded border border-gray-100">${item.format.toUpperCase()}</span>
                        <span class="px-1.5 py-0.5 bg-gray-50 text-gray-500 text-xs rounded border border-gray-100">${item.speed}x</span>
                        <span class="text-xs text-gray-400">${new Date(item.created_at).toLocaleString()}</span>
                    </div>
                </div>
                <button onclick="playHistoryAudio('${item.id}', '${item.format}', this)"
                        class="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-50 rounded transition flex-shrink-0"
                        data-history-id="${item.id}">
                    <i class="fas fa-play text-xs"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// 播放历史音频
async function playHistoryAudio(audioId, format, buttonEl) {
    try {
        const player = document.getElementById('audio-player');
        const isSame = currentHistoryPlayId === audioId;

        if (isSame && buttonEl && buttonEl.getAttribute('data-playing') === 'true') {
            player.pause();
            resetHistoryPlayButton(buttonEl);
            currentHistoryPlayId = null;
            return;
        }

        if (currentHistoryPlayId && currentHistoryPlayId !== audioId) {
            const prevBtn = document.querySelector(`[data-history-id="${currentHistoryPlayId}"]`);
            resetHistoryPlayButton(prevBtn);
        }

        if (buttonEl) {
            buttonEl.innerHTML = '<i class="fas fa-pause"></i>';
            buttonEl.classList.remove('text-primary');
            buttonEl.classList.add('text-emerald-600', 'bg-emerald-50');
            buttonEl.setAttribute('data-playing', 'true');
        }

        currentHistoryPlayId = audioId;

        const response = await apiFetch(`/api/v1/audio/stream/${audioId}`);
        
        if (!response.ok) {
            throw new Error('音频不存在');
        }
        
        const blob = await response.blob();
        currentAudioBlob = blob;
        currentAudioFormat = format;
        
        playAudio(blob);
        showToast('开始播放', 'success');

        player.onended = () => {
            const currentBtn = document.querySelector(`[data-history-id="${audioId}"]`);
            resetHistoryPlayButton(currentBtn);
            currentHistoryPlayId = null;
        };
        player.onpause = () => {
            const currentBtn = document.querySelector(`[data-history-id="${audioId}"]`);
            resetHistoryPlayButton(currentBtn);
            currentHistoryPlayId = null;
        };
        player.onerror = () => {
            const currentBtn = document.querySelector(`[data-history-id="${audioId}"]`);
            resetHistoryPlayButton(currentBtn);
            currentHistoryPlayId = null;
        };
        
    } catch (error) {
        if (buttonEl) {
            resetHistoryPlayButton(buttonEl);
        }
        currentHistoryPlayId = null;
        showToast('播放失败: ' + error.message, 'error');
    }
}

// 清空历史
async function clearHistory() {
    if (!confirm('确定要清空所有历史记录吗？')) {
        return;
    }
    
    try {
        const response = await apiFetch('/api/v1/history', {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('历史记录已清空', 'success');
            loadHistory();
        } else {
            showToast('清空失败: ' + result.message, 'error');
        }
    } catch (error) {
        console.error('清空历史失败:', error);
        showToast('清空失败: ' + error.message, 'error');
    }
}

// 打开添加渠道模态框
function openAddChannelModal() {
    document.getElementById('add-channel-modal').classList.remove('hidden');
}

// 关闭添加渠道模态框
function closeAddChannelModal() {
    document.getElementById('add-channel-modal').classList.add('hidden');
    document.getElementById('add-channel-form').reset();
}

// 提交添加渠道
async function submitAddChannel(event) {
    event.preventDefault();
    
    const request = {
        name: document.getElementById('new-channel-name').value,
        type: document.getElementById('new-channel-type').value,
        base_url: document.getElementById('new-channel-url').value || null,
        api_key: document.getElementById('new-channel-key').value || null,
        priority: parseInt(document.getElementById('new-channel-priority').value) || 0,
        is_default: document.getElementById('new-channel-default').checked,
        config: {}
    };
    
    try {
        const response = await apiFetch('/api/v1/channels', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('渠道添加成功', 'success');
            closeAddChannelModal();
            loadChannels();
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showToast('添加失败: ' + error.message, 'error');
    }
}

// 测试渠道
async function testChannel(channelId) {
    try {
        const response = await apiFetch(`/api/v1/channels/${channelId}/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('连接测试成功', 'success');
        } else {
            showToast('连接测试失败: ' + result.message, 'error');
        }
        
        loadChannels(); // 刷新列表以更新状态
    } catch (error) {
        showToast('测试失败: ' + error.message, 'error');
    }
}

// 删除渠道
async function deleteChannel(channelId) {
    if (!confirm('确定要删除这个渠道吗？')) {
        return;
    }
    
    try {
        const response = await apiFetch(`/api/v1/channels/${channelId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('渠道删除成功', 'success');
            loadChannels();
        } else {
            throw new Error(result.message);
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// 显示 API 文档
function showApiDocs() {
    const docs = `
TTS API 使用说明

1. 语音合成接口
POST /api/v1/audio/speech

请求体：
{
    "model": "tts-1",
    "input": "要合成的文本",
    "voice": "alloy",
    "response_format": "mp3",
    "speed": 1.0,
    "channel_id": "可选，指定渠道"
}

2. 获取语音列表
GET /api/v1/voices

3. 渠道管理
GET    /api/v1/channels      # 获取渠道列表
POST   /api/v1/channels      # 创建渠道
DELETE /api/v1/channels/{id} # 删除渠道
    `;
    
    alert(docs);
}

// Toast 通知
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const msg = document.getElementById('toast-message');
    
    msg.textContent = message;
    
    if (type === 'success') {
        icon.className = 'fas fa-check-circle text-green-500 mr-2';
    } else if (type === 'error') {
        icon.className = 'fas fa-exclamation-circle text-red-500 mr-2';
    } else {
        icon.className = 'fas fa-info-circle text-blue-500 mr-2';
    }
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
