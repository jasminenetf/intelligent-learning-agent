// 智学工坊前端恢复版（精简可运行）
// 目标：恢复基础导航、首页仪表盘、会话中心、课程中心、资源中心、错题本、学习报告与设置页。

const S = {
  apiBase: window.__API_BASE__ || 'http://127.0.0.1:8010',
  token: '',
  user: null,
  courseId: 1,
  courseName: '高等数学上册',
  courses: [],
  sidebarCollapsed: false,
  resourceJobId: null,
  resourceJobTrace: [],
  pendingStudyPlan: null,
  pendingStudyTopic: '',
  currentQuiz: null,
  generatorPrefill: null,
  lastAnswer: '',
  lastQuestion: '',
  lastTopic: '',
  speechUtterance: null,
  useStreamAsk: true,
  resourceCenterQuery: '',
  resourceCenterSort: 'newest',
  resourceCenterType: 'all',
  currentResourcePackage: null,
  llmProvider: '',
  llmModel: '',
  autoArtifactTopicKey: '',
  autoArtifactRunning: false,
  mermaidZoom: 1.35,
  mermaidFitMode: false,
  currentProfile: null,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
function esc(s){ return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function jsAttrArg(s){ return JSON.stringify(String(s ?? '')).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function _parseJsonList(raw){
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map(String);
  try {
    const d = JSON.parse(raw);
    return Array.isArray(d) ? d.map(String) : [];
  } catch (_) {
    return String(raw).trim() ? [String(raw)] : [];
  }
}

function _stageLabel(stage){
  const map = {
    foundation: '基础夯实',
    consolidating: '基础巩固',
    practice: '强化练习',
    review: '错题复盘',
    advanced: '进阶拓展',
  };
  return map[stage] || stage || '基础巩固';
}

const _ARTIFACT_TAB_MAP = {
  mindmap: 'mindmap',
  quiz: 'quiz',
  lecture_doc: 'lecture',
  ppt: 'ppt',
  study_plan: 'study_plan',
  reading: 'lecture',
  video_script: 'lecture',
};

const RESOURCE_LABELS = {
  mindmap: '思维导图',
  quiz: '练习题',
  lecture_doc: '学习讲义',
  ppt: 'PPT课件',
  study_plan: '学习路径',
  reading: '拓展阅读',
  video_script: '视频脚本',
};

function resourceLabel(type){
  return RESOURCE_LABELS[type] || type || '学习资源';
}

function _currentLearningTopic(fallback){
  const input = document.getElementById('chat-input');
  const typed = input ? input.value.trim() : '';
  return typed || S.lastTopic || S.lastQuestion || fallback || '当前学习主题';
}

function _stripJsonFence(raw){
  return String(raw || '').trim()
    .replace(/^```(?:json|mermaid|markdown)?\s*/i, '')
    .replace(/\s*```$/i, '')
    .trim();
}

function _parseMaybeJson(raw){
  if (!raw) return null;
  if (typeof raw === 'object') return raw;
  const text = _stripJsonFence(raw);
  try { return JSON.parse(text); } catch (_) {}
  const start = Math.min.apply(null, ['{', '['].map(ch => {
    const i = text.indexOf(ch);
    return i < 0 ? Number.POSITIVE_INFINITY : i;
  }));
  if (!Number.isFinite(start)) return null;
  const endObj = Math.max(text.lastIndexOf('}'), text.lastIndexOf(']'));
  if (endObj <= start) return null;
  try { return JSON.parse(text.slice(start, endObj + 1)); } catch (_) { return null; }
}

function _mindmapJsonToMermaid(data, topic){
  const rootTitle = (data && (data.title || data.label || data.name)) || topic || '学习主题';
  const roots = Array.isArray(data && data.nodes) ? data.nodes : (Array.isArray(data && data.children) ? data.children : []);
  const lines = ['mindmap', '  root((' + String(rootTitle).replace(/[()]/g, '') + '))'];
  function walk(node, depth){
    if (!node || depth > 5) return;
    const label = String(node.label || node.title || node.name || node.text || '').trim();
    if (label) lines.push('  '.repeat(depth + 1) + label.replace(/[:：\n\r\t]/g, ' ').slice(0, 36));
    const children = Array.isArray(node.children) ? node.children : (Array.isArray(node.nodes) ? node.nodes : []);
    children.slice(0, 8).forEach(child => walk(child, depth + 1));
  }
  roots.slice(0, 8).forEach(node => walk(node, 1));
  if (lines.length <= 2) {
    lines.push('    核心概念', '    关键方法', '    常见误区', '    练习与复盘');
  }
  return lines.join('\n');
}

function _normalizeMermaid(raw, topic){
  if (!raw) return _mindmapJsonToMermaid({ title: topic }, topic);
  if (typeof raw === 'object') return _mindmapJsonToMermaid(raw, topic);
  const text = _stripJsonFence(raw);
  if (/^(mindmap|graph\s|flowchart\s|sequenceDiagram|classDiagram)/i.test(text)) return text;
  const parsed = _parseMaybeJson(text);
  if (parsed) return _mindmapJsonToMermaid(parsed, topic);
  const lines = text.split(/\n+/).map(s => s.trim()).filter(Boolean).slice(0, 10);
  return ['mindmap', '  root((' + (topic || '学习主题') + '))'].concat(lines.map(s => '    ' + s.replace(/^[-*#\d.\s]+/, '').slice(0, 36))).join('\n');
}

function _answerToIndex(answer, options){
  if (typeof answer === 'number' && Number.isFinite(answer)) {
    if (answer >= 0 && answer < options.length) return answer;
    if (answer >= 1 && answer <= options.length) return answer - 1;
  }
  const raw = String(answer ?? '').trim();
  if (!raw) return 0;
  const letter = raw.match(/^[A-Da-d]/);
  if (letter) return Math.max(0, Math.min(letter[0].toUpperCase().charCodeAt(0) - 65, Math.max(options.length - 1, 0)));
  const num = raw.match(/\d+/);
  if (num) {
    const n = Number(num[0]);
    if (n >= 0 && n < options.length) return n;
    if (n >= 1 && n <= options.length) return n - 1;
  }
  const idx = options.findIndex(o => String(o).trim() === raw || raw.includes(String(o).trim()));
  return idx >= 0 ? idx : 0;
}

function _normalizeQuizItems(data, topic){
  let source = data;
  if (source && source.content) source = _parseMaybeJson(source.content) || source.content;
  if (typeof source === 'string') source = _parseMaybeJson(source) || source;
  let items = [];
  if (Array.isArray(source)) items = source;
  else if (source && Array.isArray(source.items)) items = source.items;
  else if (source && Array.isArray(source.questions)) items = source.questions;
  else if (source && source.raw_json) items = _normalizeQuizItems(source.raw_json, topic);
  if (!Array.isArray(items)) items = [];
  return items.map(function(it, idx){
    const q = it || {};
    let options = q.options || q.choices || q.answers || [];
    if (!Array.isArray(options)) options = String(options).split(/[;；\n]/).filter(Boolean);
    options = options.map(function(o){
      if (typeof o === 'object') return String(o.text || o.label || o.value || '');
      return String(o || '').replace(/^[A-Da-d][.、:：]\s*/, '');
    }).filter(Boolean);
    if (options.length < 2) options = ['正确', '错误'];
    const answer = _answerToIndex(q.answer ?? q.correct_answer ?? q.correct ?? q.correctIndex, options);
    return {
      question: q.question || q.title || q.stem || ('关于「' + (topic || '当前主题') + '」的练习题 ' + (idx + 1)),
      options,
      answer,
      knowledge_point: q.knowledge_point || q.knowledgePoint || topic || '当前主题',
      explanation: q.explanation || q.analysis || q.reason || '',
    };
  }).filter(it => it.question && it.options.length >= 2);
}

async function api(path, opts={}) {
  const headers = {'Content-Type':'application/json'};
  if (S.token) headers.Authorization = 'Bearer ' + S.token;
  const res = await fetch(S.apiBase.replace(/\/$/,'') + path, { ...opts, headers });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  return { ok: res.ok, status: res.status, data };
}

function unwrapApi(res) {
  if (!res || res.data == null) return {};
  const d = res.data;
  if (d && d.ok === true && d.data !== undefined) return d.data;
  return d;
}

async function downloadAuthFile(path, filename) {
  if (!path) return toast('下载地址无效', 'info');
  let url = String(path);
  if (!url.startsWith('http')) {
    url = S.apiBase.replace(/\/$/, '') + (url.startsWith('/') ? url : '/' + url);
  }
  toast('正在下载…', 'info');
  try {
    const headers = {};
    if (S.token) headers.Authorization = 'Bearer ' + S.token;
    const res = await fetch(url, { headers });
    if (!res.ok) {
      toast('下载失败（' + res.status + '）', 'info');
      return;
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = filename || 'download.md';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
    toast('下载已开始', 'success');
  } catch (e) {
    toast(e.message || '下载失败', 'info');
  }
}

function bindSidebarNav() {
  $$('.nav-item[data-page]').forEach(function(el) {
    el.addEventListener('click', function() { navTo(el.dataset.page); });
  });
}

function _resourceDownloadBtn(resourceId, downloadUrl, filename) {
  const path = downloadUrl || (resourceId ? '/api/resources/download/' + encodeURIComponent(resourceId) : '');
  if (!path) return '';
  const fname = filename || 'download.md';
  return '<button type="button" class="btn btn-sm btn-primary" onclick="downloadAuthFile(' + jsAttrArg(path) + ', ' + jsAttrArg(fname) + ')">下载</button>';
}

function _resourceFileExt(type) {
  return ['lecture_doc', 'mindmap', 'quiz', 'ppt', 'study_plan', 'reading', 'video_script'].includes(type) ? '.md' : '.txt';
}

function _showPageError(el, title, detail) {
  if (!el) return;
  el.innerHTML = '<div class="error-card"><div class="err-title">' + esc(title || '加载失败') + '</div><div class="err-detail">' + esc(detail || '未知错误') + '</div></div>';
}


function _showAskError(typingId, detail) {
  const el = document.getElementById(typingId);
  if (el) {
    el.innerHTML = '<div class="error-card" style="margin:0;padding:10px"><div class="err-title">问答失败</div><div class="err-detail">' + esc(detail || '请检查模型配置或后端服务') + '</div></div>';
  }
}

let toastTimer;
function toast(msg, type='info'){
  const el = document.getElementById('toast');
  if (!el) return alert(msg);
  el.textContent = msg;
  el.className = 'toast ' + type;
  el.style.display = 'block';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.style.display = 'none'; }, 3500);
}

window.addEventListener('error', function(event){
  const msg = event && event.message ? String(event.message) : '';
  if (msg && / is not defined|Unexpected token|Invalid or unexpected token|Cannot read/.test(msg)) {
    toast('操作失败，请刷新页面后重试', 'info');
  }
});

window.addEventListener('unhandledrejection', function(event){
  const reason = event && event.reason ? String(event.reason.message || event.reason) : '';
  if (reason) toast('操作失败：' + reason.slice(0, 60), 'info');
});

function setToken(t){
  S.token = '';
  localStorage.removeItem('hermes_token');
  updateTopbar();
}

function updateTopbar(){
  const u = $('#topbar-user');
  const c = $('#topbar-course');
  const b = $('#topbar-badge');
  const sf = $('#sidebar-footer');
  const lo = $('#btn-logout');
  const t = $('#topbar-time');
  if (u) u.innerHTML = '<button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">直接提问</button>';
  if (lo) lo.style.display = 'none';
  if (c) c.textContent = S.courseName || '未选择';
  if (b) {
    b.className = 'topbar-badge ok';
    if (S.llmProvider === 'spark') b.textContent = 'Spark';
    else if (S.llmProvider === 'deepseek') b.textContent = 'DeepSeek';
    else if (S.llmProvider === 'mock') b.textContent = 'Mock';
    else b.textContent = '免登录';
  }
  if (sf) sf.innerHTML = '<span class="status-dot online"></span> 免登录可用';
  if (t) t.textContent = new Date().toLocaleString('zh-CN', { hour12: false });
}

const PAGE_LOADERS = {
  dashboard: loadDashboard,
  assistant: loadAssistant,
  courses: loadCourses,
  generator: loadGenerator,
  'resource-center': loadResourceCenter,
  'wrong-book': loadWrongBook,
  'learning-report': loadLearningReportPage,
  settings: loadSettings,
  knowledge: loadKnowledgeBase,
  'learning-path': loadLearningPath,
  profile: loadProfileCenter,
};

function navTo(id){
  $$('.page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + id);
  if (pg) pg.classList.add('active');
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  const ni = $('.nav-item[data-page="' + id + '"]');
  if (ni) ni.classList.add('active');

  const loader = PAGE_LOADERS[id];
  if (loader) loader();
}

window._toggleSidebar = function(){
  S.sidebarCollapsed = !S.sidebarCollapsed;
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('collapsed', S.sidebarCollapsed);
};

window._toggleAdvanced = function(){
  const group = document.getElementById('nav-advanced-group');
  if (!group) return;
  const show = group.style.display === 'none' || !group.style.display;
  group.style.display = show ? 'block' : 'none';
};

window._loginDemo = async function(){
  navTo('assistant');
  toast('已进入免登录提问模式', 'info');
};

window._logout = function(){
  updateTopbar();
  toast('已刷新状态', 'info');
};

async function bootstrap(){
  bindSidebarNav();
  updateTopbar();
  if (window.mermaid && mermaid.initialize) {
    mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
  }
  try {
    const st = await api('/api/settings/status');
    if (st.ok && st.data) {
      S.llmProvider = st.data.llm_provider || '';
      S.llmModel = st.data.llm_model || '';
    }
  } catch (_) {}
  try {
    const r = await api('/api/app/bootstrap');
    const payload = unwrapApi(r);
    if (r.ok && payload) {
      if (Array.isArray(payload.courses)) S.courses = payload.courses;
      if (payload.user && payload.user.authenticated) {
        S.user = payload.user;
      }
      if (payload.selected_course) {
        S.courseId = payload.selected_course.id || S.courseId;
        S.courseName = payload.selected_course.name || S.courseName;
      }
      if (payload.config && payload.config.llm_configured === false) {
        toast('请先配置模型服务', 'info');
      }
      updateTopbar();
      const step = payload.next_step || 'start_learning';
      if (step === 'configure_key') {
        navTo('settings');
      } else if (step === 'create_course') {
        navTo('courses');
      } else {
        navTo('assistant');
      }
      return;
    }
  } catch (_) {}
  navTo('settings');
}

async function loadDashboard(){
  const el = document.getElementById('page-dashboard');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 正在加载仪表盘...</div>';
  try {
    const [dashRes, progressRes, wrongRes, bookmarkRes, sessionsRes] = await Promise.all([
      api('/api/app/dashboard?course_id=' + S.courseId),
      api('/api/analytics/progress'),
      api('/api/analytics/wrong-book'),
      api('/api/analytics/bookmarks'),
      api('/api/sessions')
    ]);
    const d = dashRes.ok ? unwrapApi(dashRes) : {};
    const progressItems = (progressRes.ok && progressRes.data && progressRes.data.items) || [];
    const wrongItems = (wrongRes.ok && wrongRes.data && wrongRes.data.items) || [];
    const bookmarks = (bookmarkRes.ok && bookmarkRes.data && bookmarkRes.data.items) || [];
    const sessions = (sessionsRes.ok && sessionsRes.data && sessionsRes.data.sessions) || [];
    const progress = progressItems[0] || {};
    const completedRate = progress.total_lessons ? Math.round((progress.completed_lessons / progress.total_lessons) * 100) : Math.round((progress.completed_rate || 0) * 100);

    const recommended = progress.next_recommendation || '先完成一次提问，系统将自动生成个性化建议。';
    const loopSteps = [
      ['建立画像', '根据对话、测验和行为持续更新学习画像', 'profile'],
      ['课程问答', '基于课程资料进行 RAG 问答并提供引用', 'assistant'],
      ['生成资源', '一键生成讲义、导图、题库、PPT、阅读、脚本', 'generator'],
      ['完成测验', '通过练习题检验知识掌握情况', 'assistant'],
      ['复盘错题', '把错题同步到错题本和学习报告', 'wrong-book'],
      ['优化路径', '根据掌握度与画像持续调整推荐', 'learning-report']
    ];
    const profileSummary = d.profile_summary || {};
    const packageSummary = d.resource_package || {};
    const packageItems = Array.isArray(packageSummary.items) ? packageSummary.items : [];
    if (packageSummary.title) S.currentResourcePackage = packageSummary;
    const weakPointList = (d.weak_points || profileSummary.weak_points || progress.weak_points || wrongItems.map(function(w){ return w.knowledge_point || w.topic; })).filter(Boolean).slice(0, 6);
    const weeklySummary = {
      sessions: sessions.length,
      wrong: wrongItems.length,
      bookmarks: bookmarks.length,
      progress: completedRate,
    };
    const activityItems = [];
    if (sessions.length) activityItems.push({ title: '最近会话', value: sessions[0].title || '学习会话', link: 'assistant' });
    if (wrongItems.length) activityItems.push({ title: '最近错题', value: wrongItems[0].knowledge_point || wrongItems[0].topic || '待复盘知识点', link: 'wrong-book' });
    if (bookmarks.length) activityItems.push({ title: '最近收藏', value: bookmarks[0].title || bookmarks[0].resource_id || '收藏资源', link: 'resource-center' });

    let h = '';
    h += '<div class="card"><div class="card-header"><h3>学习工作台</h3><span class="topbar-badge ok">实时状态</span></div>';
    h += '<div class="course-card"><h4>高校课程个性化学习资源多智能体生成平台</h4><div class="course-meta"><span>围绕课程资料构建画像、可信问答、资源包、测验复盘和学习报告闭环</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">开始可信问答</button><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">生成资源包</button><button class="btn btn-sm btn-outline" onclick="navTo(\'learning-report\')">查看学习效果</button></div></div>';
    h += '<div class="course-card" style="cursor:pointer;margin-top:8px" onclick="navTo(\'courses\')"><h4>📘 当前课程：' + esc(d.course ? d.course.name : S.courseName) + '</h4><div class="course-meta"><span>' + esc(d.course ? (d.course.description || '暂无课程简介') : '请先创建或选择课程') + '</span></div></div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>学习闭环流程卡</h3></div><div class="lr-chips">' + loopSteps.map(function(s, i){ return '<span class="lr-chip"><strong>' + (i + 1) + '.</strong> ' + esc(s[0]) + '</span>'; }).join('') + '</div><div style="margin-top:10px;display:grid;gap:8px">' + loopSteps.map(function(s, i){ return '<div class="course-card" onclick="navTo(\'' + s[2] + '\')"><h4>' + (i + 1) + '. ' + esc(s[0]) + '</h4><div class="course-meta"><span>' + esc(s[1]) + '</span></div></div>'; }).join('') + '</div></div>';
    h += '<div class="grid grid-3" style="margin-top:12px">';
    h += '<div class="card grid-stat" onclick="navTo(\'learning-report\')" style="cursor:pointer"><div class="val" style="color:var(--primary)">' + completedRate + '%</div><div class="lbl">课程进度</div></div>';
    h += '<div class="card grid-stat" onclick="navTo(\'wrong-book\')" style="cursor:pointer"><div class="val" style="color:var(--success)">' + wrongItems.length + '</div><div class="lbl">待复盘错题</div></div>';
    h += '<div class="card grid-stat" onclick="navTo(\'resource-center\')" style="cursor:pointer"><div class="val" style="color:var(--warning)">' + bookmarks.length + '</div><div class="lbl">已收藏资源</div></div>';
    h += '</div>';
    h += '<div class="grid grid-2" style="margin-top:12px">';
    h += '<div class="card"><div class="card-header"><h3>薄弱点提醒</h3></div>' + (weakPointList.length ? weakPointList.map(function(w){ const wArg = jsAttrArg(w); return '<div class="course-card"><h4>' + esc(w) + '</h4><div class="course-meta"><span>建议生成讲义、导图和巩固练习</span></div><div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(&quot;lecture_doc&quot;, ' + wArg + ')">讲义</button><button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(&quot;mindmap&quot;, ' + wArg + ')">导图</button><button class="btn btn-sm btn-primary" onclick="loadArtifactPreview(&quot;quiz&quot;, ' + wArg + ')">练习</button></div></div>'; }).join('') : '<div class="empty-state"><div class="empty-icon">🎯</div><p>暂无明确薄弱点，完成一次问答或测验后自动识别</p></div>') + '</div>';
    h += '<div class="card"><div class="card-header"><h3>本周学习摘要</h3></div><div class="grid grid-2"><div class="course-card"><h4>' + weeklySummary.sessions + '</h4><div class="course-meta"><span>学习会话</span></div></div><div class="course-card"><h4>' + weeklySummary.wrong + '</h4><div class="course-meta"><span>待复盘错题</span></div></div><div class="course-card"><h4>' + weeklySummary.bookmarks + '</h4><div class="course-meta"><span>收藏资源</span></div></div><div class="course-card"><h4>' + weeklySummary.progress + '%</h4><div class="course-meta"><span>课程进度</span></div></div></div></div>';
    h += '</div>';
    h += '<div class="grid grid-2" style="margin-top:12px">';
    h += '<div class="card"><div class="card-header"><h3>今日任务</h3></div><div class="course-card" onclick="navTo(\'assistant\')"><h4>1. 继续最近会话</h4><div class="course-meta"><span>完成一次提问，系统将自动更新学习状态</span></div></div><div class="course-card" onclick="navTo(\'wrong-book\')"><h4>2. 复盘错题</h4><div class="course-meta"><span>优先处理当前薄弱点</span></div></div><div class="course-card" onclick="navTo(\'generator\')"><h4>3. 生成学习资源</h4><div class="course-meta"><span>讲义、导图、题库按需生成</span></div></div></div>';
    h += '<div class="card"><div class="card-header"><h3>智能推荐</h3></div><div class="course-card"><h4>下一步建议</h4><div class="course-meta"><span>' + esc(recommended) + '</span></div></div>' + (profileSummary.learning_goal ? '<div class="course-card" style="margin-top:8px"><h4>当前画像摘要</h4><div class="course-meta"><span>目标：' + esc(profileSummary.learning_goal) + '</span><span>基础：' + esc(profileSummary.knowledge_level || '待识别') + '</span></div></div>' : '') + (packageSummary.title ? '<div class="course-card" style="margin-top:8px"><h4>最近资源包</h4><div class="course-meta"><span>' + esc(packageSummary.title) + '</span><span>' + (packageSummary.item_count || 0) + ' 项资源</span><span>校验 ' + Math.round((packageSummary.grounding_score || 0) * 100) + '%</span></div>' + (packageItems.length ? '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">' + packageItems.slice(0,4).map(function(it){ return '<span class="lr-chip">' + esc((it.type || 'item') + ' · ' + (it.title || '资源')) + '</span>'; }).join('') + '</div>' : '') + '</div>' : '') + (activityItems.length ? '<div style="margin-top:12px">' + activityItems.map(a => '<div class="course-card" style="cursor:pointer" onclick="navTo(\'' + a.link + '\')"><h4>' + esc(a.title) + '</h4><div class="course-meta"><span>' + esc(a.value) + '</span></div></div>').join('') + '</div>' : '<div class="empty-state" style="margin-top:12px"><div class="empty-icon">🧭</div><p>完成一次提问后，系统会自动生成个性化推荐</p></div>') + '</div>';
    h += '</div>';
    h += '<div class="card"><div class="card-header"><h3>最近活动</h3></div>' + (activityItems.length ? activityItems.map(a => '<div class="course-card" style="cursor:pointer" onclick="navTo(\'' + a.link + '\')"><h4>' + esc(a.title) + '</h4><div class="course-meta"><span>' + esc(a.value) + '</span></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🕘</div><p>暂无活动，先去提问或上传资料开始学习</p></div>') + '</div>';
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">首页加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div><div class="err-actions"><button class="btn btn-sm btn-primary" onclick="loadDashboard()">重试</button></div></div>';
  }
}

async function refreshSessionList(){
  const sel = document.getElementById('session-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">加载会话中...</option>';
  try {
    const r = await api('/api/sessions?course_id=' + S.courseId);
    const sessions = (r.ok && r.data && Array.isArray(r.data.sessions)) ? r.data.sessions : [];
    if (!sessions.length) {
      sel.innerHTML = '<option value="">— 还没有历史会话 —</option>';
      return;
    }
    sel.innerHTML = '<option value="">— 选择历史会话 —</option>' + sessions.map(s => '<option value="' + esc(s.id) + '">' + esc(s.title || '学习会话') + ' (' + (s.message_count || 0) + ')</option>').join('');
  } catch (e) {
    sel.innerHTML = '<option value="">— 会话加载失败 —</option>';
  }
}

async function loadAssistant(){
  await refreshSessionList();
  _initArtifactTabs();
  const box = document.getElementById('chat-messages');
  if (box) {
    const hasContent = box.querySelector('.msg-bubble, .loading-block, .empty-state, .error-card');
    if (!hasContent) {
      box.innerHTML = '<div class="msg-bubble agent"><div class="msg-content">你好，我是智学工坊学习助手。告诉我你正在学什么、哪里不理解，我会结合课程资料解答，并推荐讲义、导图、练习等下一步学习资源。</div></div>';
    }
  }
  const sidebar = document.getElementById('assistant-sidebars');
  if (sidebar && !sidebar.dataset.ready) {
    sidebar.dataset.ready = '1';
    sidebar.innerHTML = '<div class="card"><div class="card-header"><h3>学习闭环导航</h3></div><div class="course-card"><h4>1. 建立画像</h4><div class="course-meta"><span>通过对话与测验持续更新你的学习状态</span></div></div><div class="course-card"><h4>2. 课程问答</h4><div class="course-meta"><span>基于课程资料和引用回答问题</span></div></div><div class="course-card"><h4>3. 生成资源</h4><div class="course-meta"><span>一键生成讲义、导图、题库、PPT、阅读、脚本</span></div></div><div class="course-card"><h4>4. 完成测验</h4><div class="course-meta"><span>用题目检验理解并写入掌握度</span></div></div><div class="course-card"><h4>5. 复盘错题</h4><div class="course-meta"><span>错题会自动回流到学习报告和复习路径</span></div></div></div>' +
      '<div class="card" id="resource-package-panel" style="margin-top:12px"><div class="card-header"><h3>个性化学习资源包</h3></div><div class="empty-state"><div class="empty-icon">📦</div><p>完成一次问答或生成资源后，这里会汇总为完整资源包</p></div></div>';
  }
}

function _initArtifactTabs(){
  const tabs = document.getElementById('artifacts-tabs');
  if (!tabs || tabs.dataset.inited) return;
  tabs.dataset.inited = '1';
  const items = [
    ['mindmap', '思维导图'],
    ['quiz', '练习题'],
    ['lecture', '讲义'],
    ['ppt', 'PPT'],
    ['study_plan', '学习路径'],
  ];
  tabs.innerHTML = items.map((x, i) =>
    '<button type="button" class="artifact-tab' + (i === 0 ? ' active' : '') + '" onclick="_switchArtifactTab(\'' + x[0] + '\', this)">' + esc(x[1]) + '</button>'
  ).join('');
  _switchArtifactTab('mindmap', tabs.querySelector('.artifact-tab'));
}

window._switchArtifactTab = function(panelId, btn){
  document.querySelectorAll('.artifact-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  document.querySelectorAll('#artifacts-content .tab-panel').forEach(p => { p.style.display = 'none'; });
  const panel = document.getElementById('artifact-' + panelId);
  if (panel) panel.style.display = 'block';
};

function _renderAskSidebar(data){
  const refs = data.citations || [];
  const citePanel = document.getElementById('citations-panel');
  if (citePanel) {
    const grounding = data.grounding || {};
    const safety = data.content_safety || {};
    const groundingScore = data.grounding_score !== undefined && data.grounding_score !== null ? Math.round(Number(data.grounding_score) * 100) : null;
    const unsupported = Array.isArray(grounding.unsupported_claims) ? grounding.unsupported_claims : [];
    citePanel.innerHTML = '<h4>📚 课程依据</h4>' +
      (groundingScore !== null ? '<div class="course-meta"><span>引用覆盖率 ' + groundingScore + '%</span><span>风险等级 ' + esc(grounding.risk_level || 'low') + '</span></div>' : '') +
      (grounding.message ? '<div class="course-meta"><span>' + esc(grounding.message) + '</span></div>' : '') +
      (safety && (safety.safe !== undefined) ? '<div class="course-meta"><span>内容安全 ' + (safety.safe ? '通过' : '需注意') + '</span><span>' + esc((safety.risk_flags || []).join(' · ') || '无风险标记') + '</span></div>' : '') +
      (unsupported.length ? '<div class="course-card" style="margin-top:6px"><h4 style="font-size:12px">无依据提示</h4><div class="course-meta"><span>' + esc(unsupported.join(' · ')) + '</span></div></div>' : '') +
      (refs.length ? refs.map(x => {
        const label = typeof x === 'string' ? x : (x.source || x.chunk_id || '课程片段');
        const page = (x && x.page_number) ? ' p.' + x.page_number : '';
        const snippet = x && (x.content || x.snippet) ? '<p style="font-size:12px;color:var(--gray-500);margin-top:4px">' + esc(String(x.content || x.snippet).slice(0, 96)) + '</p>' : '';
        return '<div class="course-card" style="margin-top:6px"><div class="course-meta"><span>课程片段 ' + esc(String(label) + page) + '</span></div>' + snippet + '</div>';
      }).join('') : '<p style="font-size:12px;color:var(--gray-400)">本次回答未检索到课程片段</p>') +
      '<div style="margin-top:8px"><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">生成学习资源</button></div>' +
      '<div style="margin-top:12px" id="agent-viz"><h4>🤖 学习助手协作</h4><p style="font-size:11px;color:var(--gray-400)">协作轨迹将在问答后显示</p></div>';
  }
  const agentViz = document.getElementById('agent-viz');
  const traces = data.agent_traces || [];
  if (agentViz) {
    const scoreLine = data.verifier_score !== undefined && data.verifier_score !== null
      ? '<div class="course-meta"><span>校验置信度 ' + Math.round(Number(data.verifier_score) * 100) + '%</span><span>grounding ' + (data.grounding_score !== undefined ? Math.round(Number(data.grounding_score) * 100) + '%' : '—') + '</span></div>'
      : '';
    const normalizedTraces = traces.map(function(t, idx){
      return {
        name: t.agent || t.agent_name || t.name || ('agent-' + (idx + 1)),
        status: t.status || 'completed',
        summary: t.message || t.summary || t.detail || '',
        duration: t.latency_ms || t.duration_ms || t.ms || null,
        step: t.step || t.phase || '',
      };
    });
    agentViz.innerHTML = '<h4>🤖 学习助手协作</h4>' + scoreLine + (normalizedTraces.length
      ? '<div style="display:grid;gap:8px">' + normalizedTraces.map(function(t, idx){ return '<div class="course-card"><h4 style="font-size:12px">' + (idx + 1) + '. ' + esc(t.name) + '</h4><div class="course-meta"><span>' + esc(t.status) + '</span>' + (t.step ? '<span>' + esc(t.step) + '</span>' : '') + (t.duration !== null && t.duration !== undefined ? '<span>' + esc(String(t.duration)) + 'ms</span>' : '') + '</div><div class="course-meta"><span>' + esc(t.summary || '已完成') + '</span></div></div>'; }).join('') + '</div>'
      : '<p style="font-size:11px;color:var(--gray-400)">协作轨迹将在问答后显示</p>');
  }
  const profileMini = document.getElementById('profile-mini');
  const sp = data.student_profile || {};
  if (profileMini) {
    const mastery = data.mastery_overview || {};
    const masteryLine = mastery.avg_mastery !== undefined ? '<div class="course-meta"><span>平均掌握度 ' + Math.round(Number(mastery.avg_mastery || 0) * 100) + '%</span><span>强项 ' + esc((mastery.strong_points || []).slice(0,2).join(' · ') || '暂无') + '</span></div>' : '';
    if (sp.knowledge_level || sp.learning_goal || masteryLine) {
      const weak = _parseJsonList(sp.weak_points).slice(0, 3).join(' · ') || '待识别';
      const prefs = _parseJsonList(sp.resource_preference).slice(0, 4).map(resourceLabel).join(' · ') || '待识别';
      profileMini.innerHTML = '<h4>🎓 学习画像</h4>' +
        '<div class="profile-mini-grid">' +
          '<span>基础：' + esc(sp.knowledge_level || '—') + '</span>' +
          '<span>目标：' + esc(sp.learning_goal || '—') + '</span>' +
          '<span>风格：' + esc(sp.cognitive_style || '—') + '</span>' +
          '<span>薄弱：' + esc(weak) + '</span>' +
          '<span>偏好：' + esc(prefs) + '</span>' +
          '<span>信心：' + esc(sp.emotion_tendency || '—') + '</span>' +
        '</div>' +
        '<div class="course-meta" style="margin-top:6px"><span>证据：' + esc((sp.raw_evidence || '').slice(0, 42) || '最近对话与测验行为') + '</span><span>置信度 ' + Math.round(Number(sp.profile_confidence || 0) * 100) + '%</span></div>' +
        masteryLine + '<button class="btn btn-sm btn-outline" style="margin-top:6px" onclick="navTo(\'profile\')">查看画像中心</button>';
    }
  }
  const packagePanel = document.getElementById('resource-package-panel');
  if (packagePanel && data.resource_package) {
    const rp = data.resource_package;
    const items = Array.isArray(rp.items) ? rp.items : [];
    packagePanel.innerHTML = '<h4>📦 个性化学习资源包</h4><div class="course-meta"><span>' + esc(rp.title || rp.topic || '资源包') + '</span><span>资源 ' + (rp.item_count || 0) + ' 项</span><span>智能体 ' + (rp.agent_count || 0) + ' 个</span></div>' +
      '<div class="course-meta"><span>grounding ' + Math.round(Number(rp.grounding_score || 0) * 100) + '%</span><span>风险 ' + esc(rp.risk_level || 'low') + '</span><span>安全 ' + ((rp.content_safe !== false) ? '通过' : '需注意') + '</span></div>' +
      (rp.summary ? '<div class="course-meta"><span>' + esc(rp.summary) + '</span></div>' : '') +
      (items.length ? '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">' + items.map(it => '<span class="lr-chip">' + esc((it.type || 'item') + ' · ' + (it.title || '资源')) + '</span>').join('') + '</div>' : '') +
      '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="showResourcePackageDetail()">查看详情</button><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">查看资源中心</button><button class="btn btn-sm btn-outline" onclick="quickGenerateFromChat(&quot;study_plan&quot;, ' + jsAttrArg(rp.topic || rp.title || '') + ')">生成学习路径</button></div>';
    S.currentResourcePackage = rp;
  }
}

window.showResourcePackageDetail = function(){
  const rp = S.currentResourcePackage;
  if (!rp) {
    toast('暂无可查看的资源包，请先提问或生成资源', 'info');
    navTo('generator');
    return;
  }
  navTo('resource-center');
  setTimeout(function(){
    const host = document.getElementById('resource-package-detail-host');
    if (!host) return;
    host.innerHTML = _resourcePackageDetailHtml(rp);
    host.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 120);
};

function _resourcePackageDetailHtml(rp){
  const items = Array.isArray(rp.items) ? rp.items : [];
  const topic = rp.topic || rp.title || '当前学习主题';
  const steps = items.length ? items.map(function(it, i){ return '<div class="course-card"><h4>' + (i + 1) + '. ' + esc(it.title || it.type || '学习资源') + '</h4><div class="course-meta"><span>' + esc(it.type || 'resource') + '</span><span>' + esc(it.reason || it.usage || '用于当前主题的个性化学习') + '</span></div><div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="quickGenerateFromChat(' + jsAttrArg(it.type || 'lecture_doc') + ', ' + jsAttrArg(topic) + ')">打开/生成</button></div></div>'; }).join('') : '<div class="empty-state"><div class="empty-icon">📦</div><p>资源包暂无资源项</p></div>';
  return '<div class="card"><div class="card-header"><h3>📦 个性化资源包详情</h3><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">继续生成</button></div>' +
    '<div class="course-card"><h4>' + esc(rp.title || topic) + '</h4><div class="course-meta"><span>主题 ' + esc(topic) + '</span><span>资源 ' + (rp.item_count || items.length) + ' 项</span><span>智能体 ' + (rp.agent_count || 0) + ' 个</span></div>' +
    '<div class="course-meta"><span>grounding ' + Math.round(Number(rp.grounding_score || 0) * 100) + '%</span><span>风险 ' + esc(rp.risk_level || 'low') + '</span><span>安全 ' + ((rp.content_safe !== false) ? '通过' : '需注意') + '</span></div>' +
    (rp.summary ? '<p style="font-size:13px;line-height:1.7;color:var(--gray-600);margin-top:8px">' + esc(rp.summary) + '</p>' : '') + '</div>' +
    '<div class="grid grid-2"><div class="card"><div class="card-header"><h3>推荐学习顺序</h3></div>' + steps + '</div>' +
    '<div class="card"><div class="card-header"><h3>适配说明</h3></div><div class="course-card"><h4>画像适配</h4><div class="course-meta"><span>根据问答内容、学习画像、掌握度和课程资料生成</span></div></div><div class="course-card"><h4>可信校验</h4><div class="course-meta"><span>引用覆盖率、风险等级、内容安全共同决定资源包质量提示</span></div></div><div class="course-card"><h4>下一步</h4><div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="quickGenerateFromChat(&quot;study_plan&quot;, ' + jsAttrArg(topic) + ')">生成学习路径</button><button class="btn btn-sm btn-outline" onclick="navTo(\'learning-report\')">查看学习报告</button></div></div></div></div></div>';
}

function _renderResourceSuggestions(suggestions, question){
  if (!suggestions || !suggestions.length) return '';
  const topic = JSON.stringify(question || '');
  return '<div class="msg-suggestions" style="margin-top:10px;padding-top:8px;border-top:1px solid var(--gray-200)">' +
    '<div style="font-size:11px;color:var(--gray-500);margin-bottom:6px">推荐下一步资源</div>' +
    '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
    suggestions.map(s =>
      '<button type="button" class="btn btn-sm btn-outline" onclick="loadArtifactPreview(' + jsAttrArg(s.type) + ', ' + jsAttrArg(question) + ')" title="' + esc(s.reason || '') + '">⚡ ' + esc(s.title || s.type) + '</button>'
    ).join('') +
    '</div></div>';
}

function _activateArtifactTab(type){
  const tabId = _ARTIFACT_TAB_MAP[type] || type;
  const tabs = document.getElementById('artifacts-tabs');
  let btn = null;
  if (tabs) {
    tabs.querySelectorAll('.artifact-tab').forEach(function(b){
      const oc = b.getAttribute('onclick') || '';
      if (oc.indexOf("'" + tabId + "'") >= 0) btn = b;
    });
  }
  _switchArtifactTab(tabId, btn);
}

function _applyMermaidZoom(){
  const host = document.getElementById('mermaid-host');
  if (!host) return;
  const svg = host.querySelector('svg');
  if (!svg) return;
  const viewBox = svg.viewBox && svg.viewBox.baseVal;
  const naturalW = viewBox && viewBox.width ? viewBox.width : (svg.getBBox ? svg.getBBox().width : 1100);
  const naturalH = viewBox && viewBox.height ? viewBox.height : (svg.getBBox ? svg.getBBox().height : 900);
  let targetW;
  if (S.mermaidFitMode) {
    const fitW = Math.max(260, (host.clientWidth || 900) - 36);
    const fitH = Math.max(260, (host.clientHeight || 620) - 36);
    const scale = Math.max(0.18, Math.min(fitW / naturalW, fitH / naturalH, 1.6));
    targetW = Math.max(240, Math.round(naturalW * scale));
  } else {
    const zoom = Math.max(0.25, Math.min(2.6, Number(S.mermaidZoom || 1.1)));
    targetW = Math.max(260, Math.round(naturalW * zoom));
  }
  svg.style.maxWidth = 'none';
  svg.style.minWidth = '0';
  svg.style.width = targetW + 'px';
  svg.style.height = 'auto';
  svg.style.display = 'block';
  host.scrollLeft = S.mermaidFitMode ? 0 : host.scrollLeft;
  host.scrollTop = S.mermaidFitMode ? 0 : host.scrollTop;
}

function _zoomMermaid(delta){
  if (S.mermaidFitMode) {
    const host = document.getElementById('mermaid-host');
    const svg = host && host.querySelector('svg');
    if (svg) {
      const viewBox = svg.viewBox && svg.viewBox.baseVal;
      const naturalW = viewBox && viewBox.width ? viewBox.width : (svg.getBBox ? svg.getBBox().width : 1100);
      const renderedW = svg.getBoundingClientRect().width || naturalW;
      S.mermaidZoom = renderedW / naturalW;
    }
  }
  S.mermaidFitMode = false;
  S.mermaidZoom = Math.max(0.25, Math.min(2.6, Number(S.mermaidZoom || 1.1) + delta));
  _applyMermaidZoom();
}

function _resetMermaidZoom(){
  S.mermaidFitMode = false;
  S.mermaidZoom = 1.1;
  _applyMermaidZoom();
}

function _fitMermaidToView(){
  S.mermaidFitMode = true;
  _applyMermaidZoom();
}

function _mindmapTreeFromMermaid(code, title){
  const text = String(code || '');
  const labels = [];
  text.split(/\n+/).forEach(function(line){
    const m = line.match(/\["([^"]+)"\]/) || line.match(/\(([^()]+)\)/);
    if (m && m[1]) {
      const label = m[1].replace(/^\d+\s*/, '').trim();
      if (label && !labels.includes(label)) labels.push(label);
    }
  });
  const root = labels.shift() || title || '知识结构';
  const buckets = [
    { title: '教材定位', summary: '先找到这个知识点在《高数上.pdf》中的章节位置', children: [] },
    { title: '核心定义', summary: '把口语理解转换成教材定义和条件', children: [] },
    { title: '解题流程', summary: '把定义变成可执行步骤', children: [] },
    { title: '常见误区', summary: '做错题时先回到条件和概念', children: [] },
    { title: '巩固路径', summary: '讲义、结构图、练习和错题复盘形成闭环', children: [] },
  ];
  labels.forEach(function(label, idx){
    buckets[Math.min(buckets.length - 1, Math.floor(idx / 3))].children.push(label);
  });
  return { title: root, nodes: buckets.filter(function(x){ return x.children.length || x.summary; }) };
}

function _renderMindmapTreePanel(el, data, title){
  if (!el) return;
  const tree = (data && data.tree) || _mindmapTreeFromMermaid(data && (data.mermaid || data.content), title);
  const mermaidCode = (data && (data.mermaid || data.content)) || '';
  const nodes = Array.isArray(tree.nodes) ? tree.nodes : [];
  const nodeHtml = nodes.map(function(node, idx){
    const children = Array.isArray(node.children) ? node.children : [];
    return '<details class="mindmap-tree-card" open>' +
      '<summary><span class="mm-order">' + (idx + 1) + '</span><span><strong>' + esc(node.title || node.label || '知识模块') + '</strong>' +
      (node.summary ? '<small>' + esc(node.summary) + '</small>' : '') + '</span></summary>' +
      (children.length ? '<ul>' + children.map(function(child){ return '<li>' + esc(typeof child === 'object' ? (child.title || child.label || child.summary || '') : child) + '</li>'; }).join('') + '</ul>' : '') +
    '</details>';
  }).join('');
  el.innerHTML =
    '<div class="mindmap-product mindmap-readable-product">' +
      '<div class="mindmap-toolbar">' +
        '<div class="mt-title-area"><div class="mt-title">' + esc(title || tree.title || '知识结构图') + '</div><div class="mt-subtitle">可折叠知识树，优先保证看得清；Mermaid 原图作为备份查看</div></div>' +
        '<div class="mt-actions">' +
          '<span class="mindmap-status-tag generated">已生成</span>' +
          '<button type="button" class="btn btn-sm btn-outline" onclick="_toggleMindmapFullscreen()">全屏/退出</button>' +
          '<button type="button" class="btn btn-sm btn-outline" onclick="_toggleMermaidBackup()">Mermaid备份</button>' +
        '</div>' +
      '</div>' +
      '<div class="mindmap-tree-readable">' +
        '<div class="mindmap-root-card"><h4>' + esc(tree.title || title || '当前知识点') + '</h4><p>' + esc(tree.subtitle || '按学习顺序展开：教材定位、核心定义、解题流程、常见误区、复盘路径。') + '</p></div>' +
        (nodeHtml || '<div class="empty-state"><p>暂无结构内容</p></div>') +
      '</div>' +
      '<div class="mindmap-backup" id="mindmap-backup" style="display:none"><pre class="mermaid-fallback">' + esc(mermaidCode || '暂无 Mermaid 备份') + '</pre></div>' +
      '<div class="mindmap-info-bar"><span class="mi-item"><span class="mi-dot"></span>默认显示可读知识树</span><span class="mi-item">点击模块可折叠，适合答辩和实际学习</span></div>' +
    '</div>';
}

window._toggleMindmapFullscreen = function(){
  const box = document.querySelector('.mindmap-readable-product');
  if (box) box.classList.toggle('mindmap-fullscreen');
};

window._toggleMermaidBackup = function(){
  const box = document.getElementById('mindmap-backup');
  if (box) box.style.display = box.style.display === 'none' ? 'block' : 'none';
};

function _renderMermaidPanel(el, code, title){
  if (!el) return;
  el.innerHTML =
    '<div class="mindmap-product">' +
      '<div class="mindmap-toolbar">' +
        '<div class="mt-title-area"><div class="mt-title">' + esc(title || '知识结构图') + '</div><div class="mt-subtitle">已按学习顺序展开，可横向/纵向滚动查看细节</div></div>' +
        '<div class="mt-actions">' +
          '<span class="mindmap-status-tag generated">已生成</span>' +
          '<button type="button" class="btn btn-sm btn-primary" onclick="_fitMermaidToView()">全图</button>' +
          '<button type="button" class="btn btn-sm btn-outline" onclick="_zoomMermaid(0.18)">放大</button>' +
          '<button type="button" class="btn btn-sm btn-outline" onclick="_zoomMermaid(-0.18)">缩小</button>' +
          '<button type="button" class="btn btn-sm btn-outline" onclick="_resetMermaidZoom()">重置</button>' +
        '</div>' +
      '</div>' +
      '<div class="mindmap-canvas-wrap readable" id="mermaid-host"></div>' +
      '<div class="mindmap-info-bar"><span class="mi-item"><span class="mi-dot"></span>导图默认放大显示</span><span class="mi-item">滚动鼠标或拖动滚动条查看完整结构</span></div>' +
    '</div>';
  const host = document.getElementById('mermaid-host');
  if (!host) return;
  S.mermaidFitMode = true;
  const node = document.createElement('div');
  node.className = 'mermaid';
  node.textContent = code || 'graph TD\n  A[暂无导图]';
  host.appendChild(node);
  if (window.mermaid && mermaid.run) {
    mermaid.run({ nodes: [node] }).then(function(){
      setTimeout(_applyMermaidZoom, 30);
    }).catch(function(){
      host.innerHTML = '<pre class="mermaid-fallback">' + esc(code || '暂无导图') + '</pre>';
    });
  }
}

function _renderStudyPlanPanel(el, d, topic){
  if (!el) return;
  const plan = d.study_plan || d.plan && { steps: d.plan } || d || {};
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  const summary = plan.profile_summary || '基于最近提问、教材章节、画像和错题动态生成。';
  el.innerHTML = '<div class="course-card"><h4>' + esc(plan.title || ((topic || '当前主题') + ' · 学习路径')) + '</h4><div class="course-meta"><span>' + esc(summary) + '</span></div>' +
    (plan.next_action ? '<div class="course-meta" style="margin-top:6px"><span>下一步：' + esc(plan.next_action) + '</span></div>' : '') +
    '<div style="margin-top:8px">' + _resourceDownloadBtn(null, d.download_url, (plan.title || topic || '学习路径') + '.md').replace('>下载<', '>下载路径<') + '</div></div>' +
    (steps.length ? steps.map(function(s, i){
      const types = Array.isArray(s.resource_types) ? s.resource_types : [];
      const btns = types.slice(0, 4).map(function(t){ return '<button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(' + jsAttrArg(t) + ', ' + jsAttrArg(s.title || topic || '') + ')">生成' + esc(resourceLabel(t)) + '</button>'; }).join('');
      return '<div class="course-card plan-card-enhanced"><h4>步骤 ' + esc(String(s.order || i + 1)) + ' · ' + esc(s.title || '学习步骤') + '</h4>' +
        '<p style="font-size:13px;line-height:1.75;color:var(--gray-700);margin:8px 0">' + esc(s.description || '') + '</p>' +
        '<div class="course-meta"><span>为什么：' + esc(s.reason || '根据最近问题和画像推荐') + '</span></div>' +
        '<div class="course-meta" style="margin-top:6px"><span>预计 ' + esc(String(s.estimated_minutes || 15)) + ' 分钟</span><span>资源：' + esc(types.map(resourceLabel).join(' / ') || '讲义 / 导图 / 练习') + '</span></div>' +
        (s.practice ? '<div class="course-meta" style="margin-top:6px"><span>练习：' + esc(s.practice) + '</span></div>' : '') +
        (s.check_standard ? '<div class="course-meta" style="margin-top:6px"><span>检验标准：' + esc(s.check_standard) + '</span></div>' : '') +
        (btns ? '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' + btns + '</div>' : '') +
      '</div>';
    }).join('') : '<div class="empty-state"><p>暂无学习路径</p></div>');
}

function _renderQuizPanel(el, items, topic){
  if (!el) return;
  const quizItems = _normalizeQuizItems(items, topic);
  if (!quizItems.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><p>暂无练习题</p><button class="btn btn-sm btn-outline" style="margin-top:8px" onclick="loadArtifactPreview(&quot;quiz&quot;, ' + jsAttrArg(topic || _currentLearningTopic()) + ')">重新生成</button></div>';
    return;
  }
  S.currentQuiz = { topic: topic || '', items: quizItems };
  el.innerHTML = quizItems.map((it, idx) => {
    const opts = (it.options || []).map((o, oi) =>
      '<label style="display:block;margin:4px 0"><input type="radio" name="quiz-' + idx + '" value="' + oi + '"> ' + esc(o) + '</label>'
    ).join('');
    return '<div class="course-card" data-quiz-idx="' + idx + '"><h4>Q' + (idx + 1) + '. ' + esc(it.question || '') + '</h4>' + opts +
      '<div class="course-meta"><span>知识点 ' + esc(it.knowledge_point || topic || '当前主题') + '</span><span>提交后自动写入掌握度</span></div>' +
      '<div class="quiz-inline-feedback" id="quiz-feedback-' + idx + '"></div>' +
      '<button class="btn btn-sm btn-primary" style="margin-top:8px" onclick="submitQuizAnswer(' + idx + ')">提交本题</button></div>';
  }).join('');
}

function _renderQuizFeedback(idx, item, selectedIdx, isCorrect){
  const el = document.getElementById('quiz-feedback-' + idx);
  if (!el) return;
  const opts = item.options || [];
  const correctIdx = Number(item.answer || 0);
  const selectedText = opts[selectedIdx] || '未选择';
  const correctText = opts[correctIdx] || '正确选项';
  const title = isCorrect ? '答对了，但也要确认你真的理解' : '这题选错了，先在这里讲清楚';
  const why = item.explanation || '这道题考察的是概念本身和适用条件，不是只看答案形式。';
  const fix = isCorrect
    ? '继续做下一题；如果能用自己的话解释为什么其他选项错，说明真正掌握。'
    : '先把正确选项读一遍，再回到题干找关键词：题目问的是“核心含义/关键步骤/常见错误”中的哪一种。错因通常不是记忆问题，而是没有先判断条件。';
  el.innerHTML =
    '<div class="' + (isCorrect ? 'quiz-feedback show correct-fb' : 'quiz-feedback show wrong-fb') + '" style="display:block;margin-top:10px">' +
      '<div style="font-weight:700;margin-bottom:6px">' + esc(title) + '</div>' +
      '<div style="line-height:1.7"><strong>你的选择：</strong>' + esc(selectedText) + '</div>' +
      '<div style="line-height:1.7"><strong>正确答案：</strong>' + esc(correctText) + '</div>' +
      '<div style="line-height:1.7;margin-top:6px"><strong>为什么：</strong>' + esc(why) + '</div>' +
      '<div style="line-height:1.7;margin-top:6px"><strong>怎么补：</strong>' + esc(fix) + '</div>' +
      '<div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
        '<button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(&quot;lecture_doc&quot;, ' + jsAttrArg(item.knowledge_point || S.currentQuiz.topic || _currentLearningTopic()) + ')">看详细讲义</button>' +
        '<button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(&quot;mindmap&quot;, ' + jsAttrArg(item.knowledge_point || S.currentQuiz.topic || _currentLearningTopic()) + ')">看知识结构</button>' +
        '<button class="btn btn-sm btn-outline" onclick="navTo(&quot;wrong-book&quot;)">稍后去错题本</button>' +
      '</div>' +
    '</div>';
}

function _renderPptPanel(el, d){
  if (!el) return;
  const title = d.title || 'PPT课件';
  const slideCount = d.slide_count || (Array.isArray(d.slides) ? d.slides.length : '?');
  const slides = Array.isArray(d.slides) ? d.slides.slice(0, 8) : [];
  el.innerHTML = '<div class="course-card"><h4>' + esc(title) + '</h4><div class="course-meta"><span>共 ' + esc(String(slideCount)) + ' 页</span><span>教学版文字课件</span><span>含讲稿 / 板书 / 检查问题</span></div><div style="margin-top:8px">' + _resourceDownloadBtn(null, d.download_url, title + '.md').replace('>下载<', '>下载教学稿<') + '</div></div>' +
    (slides.length ? slides.map(function(s, i){
      const bullets = (s.bullets || s.points || []).map(function(x){ return '- ' + x; }).join('\n');
      const board = (s.board_work || []).map(function(x){ return '- ' + x; }).join('\n');
      const text = [
        s.student_problem ? '学生卡点：' + s.student_problem : '',
        bullets ? '本页要教会学生：\n' + bullets : (s.content || ''),
        (s.teacher_script || s.speaker_notes) ? '老师讲法：' + (s.teacher_script || s.speaker_notes) : '',
        board ? '板书/演示步骤：\n' + board : '',
        s.check_question ? '课堂检查问题：' + s.check_question : '',
      ].filter(Boolean).join('\n\n');
      return '<div class="course-card"><h4>📊 第 ' + (i + 1) + ' 页：' + esc(s.title || s.heading || '课件页') + '</h4><div style="white-space:pre-wrap;font-size:13px;line-height:1.75;margin-top:8px">' + esc(text) + '</div></div>';
    }).join('') : '<div class="course-card"><h4>教学稿已生成</h4><div class="course-meta"><span>点击下载按钮获取 Markdown 版本</span></div></div>');
}

function _renderTextResourcePanel(el, d, type){
  if (!el) return;
  const content = typeof d.content === 'object' ? JSON.stringify(d.content, null, 2) : (d.content || '内容生成完成');
  const title = d.title || (type === 'reading' ? '拓展阅读' : (type === 'video_script' ? '视频脚本' : '学习讲义'));
  if (type === 'video_script') {
    const scenes = content.split(/\n\s*\n|(?=镜头\s*\d+)|(?=场景\s*\d+)|(?=分镜\s*\d+)|(?=Scene\s*\d+)/i).map(s => s.trim()).filter(Boolean).slice(0, 8);
    el.innerHTML = '<div class="course-card"><h4>' + esc(title) + '</h4><div class="course-meta"><span>视频脚本分镜</span><span>' + scenes.length + ' 个片段</span><span>适合录制讲解视频</span></div></div>' +
      (scenes.length ? scenes.map(function(s, i){ return '<div class="course-card"><h4>🎬 分镜 ' + (i + 1) + '</h4><div class="course-meta"><span>建议时长 30-60 秒</span><span>画面 + 旁白</span></div><div style="white-space:pre-wrap;font-size:13px;line-height:1.65;margin-top:8px">' + esc(s) + '</div></div>'; }).join('') : '<div class="course-card"><div style="white-space:pre-wrap;font-size:13px;line-height:1.65">' + esc(content) + '</div></div>');
    return;
  }
  const sections = String(content).split(/\n{2,}/).map(s => s.trim()).filter(Boolean).slice(0, 14);
  if (type === 'reading') {
    el.innerHTML = '<div class="course-card"><h4>' + esc(title) + '</h4><div class="course-meta"><span>拓展阅读</span><span>适合课后深化</span><span>可加入资源包</span></div></div>' +
      sections.map(function(s, i){ return '<div class="course-card"><h4>' + esc(/^#{1,4}\s+/.test(s) ? s.replace(/^#{1,4}\s+/, '') : ('阅读片段 ' + (i + 1))) + '</h4><div style="white-space:pre-wrap;font-size:13px;line-height:1.7;margin-top:8px">' + esc(/^#{1,4}\s+/.test(s) ? '' : s) + '</div></div>'; }).join('');
    return;
  }
  el.innerHTML = '<div class="course-card"><h4>' + esc(title) + '</h4><div class="course-meta"><span>Markdown 讲义</span><span>可用于复习与做题前预习</span><span>结构化卡片</span></div></div>' +
    sections.map(function(s, i){
      const isHeading = /^#{1,4}\s+/.test(s);
      return '<div class="course-card"><h4>' + esc(isHeading ? s.replace(/^#{1,4}\s+/, '') : ('讲义模块 ' + (i + 1))) + '</h4><div style="white-space:pre-wrap;font-size:13px;line-height:1.7;margin-top:8px">' + esc(isHeading ? '' : s) + '</div></div>';
    }).join('');
}

async function submitQuizAnswer(idx){
  const quiz = S.currentQuiz;
  if (!quiz || !quiz.items || !quiz.items[idx]) return toast('题目不存在', 'info');
  const item = quiz.items[idx];
  const picked = document.querySelector('input[name="quiz-' + idx + '"]:checked');
  if (!picked) return toast('请先选择答案', 'info');
  const selectedIdx = Number(picked.value);
  const isCorrect = selectedIdx === Number(item.answer);
  const selectedText = (item.options || [])[selectedIdx] || String(selectedIdx);
  const correctText = (item.options || [])[Number(item.answer)] || String(item.answer);
  try {
    const r = await api('/api/app/quiz/submit', {
      method: 'POST',
      body: JSON.stringify({
        course_id: S.courseId,
        topic: item.knowledge_point || quiz.topic || _currentLearningTopic(),
        question_text: item.question || '',
        selected_answer: selectedText,
        correct_answer: correctText,
        is_correct: isCorrect,
        knowledge_point: item.knowledge_point || quiz.topic || _currentLearningTopic(),
        explanation: item.explanation || '',
      }),
    });
    if (r.ok) {
      _renderQuizFeedback(idx, item, selectedIdx, isCorrect);
      toast(isCorrect ? '回答正确，画像已更新' : '已记录错题，先看本题解析', isCorrect ? 'success' : 'info');
      return;
    }
    toast('作答记录失败', 'info');
  } catch (e) {
    toast(e.message || '作答记录失败', 'info');
  }
}

async function loadArtifactPreview(type, topic){
  topic = topic || _currentLearningTopic();
  const assistantPage = document.getElementById('page-assistant');
  if (!assistantPage || !assistantPage.classList.contains('active')) {
    navTo('assistant');
    await new Promise(function(resolve){ setTimeout(resolve, 120); });
  }
  const tabId = _ARTIFACT_TAB_MAP[type] || type;
  const panel = document.getElementById('artifact-' + tabId);
  if (!panel) {
    navTo('generator');
    setTimeout(function(){ quickGenerateFromChat(type, topic); }, 80);
    return;
  }
  _initArtifactTabs();
  _activateArtifactTab(type);
  panel.innerHTML = '<div class="loading-block"><span class="spinner"></span> 正在生成' + esc(resourceLabel(type)) + '...</div>';
  try {
    const r = await api('/api/app/generate', {
      method: 'POST',
      body: JSON.stringify({ course_id: S.courseId, resource_type: type, topic: topic || '当前学习主题' }),
    });
    const d = r.ok ? unwrapApi(r) : {};
    if (!r.ok) {
      panel.innerHTML = '<div class="error-card"><div class="err-title">生成失败</div><div class="err-detail">' + esc((r.data && r.data.detail) || (r.data && r.data.message) || '请求失败') + '</div></div>';
      toast('资源生成失败', 'info');
      return;
    }
    if (type === 'mindmap') {
      _renderMindmapTreePanel(panel, d, d.title || (topic + ' · 思维导图'));
    } else if (type === 'quiz') {
      _renderQuizPanel(panel, d.items || d.raw_json || d.content || d, topic);
    } else if (type === 'ppt') {
      _renderPptPanel(panel, d);
    } else if (type === 'study_plan') {
      S.pendingStudyPlan = d.study_plan || null;
      S.pendingStudyTopic = topic || '';
      _renderStudyPlanPanel(panel, d, topic);
    } else {
      _renderTextResourcePanel(panel, d, type);
    }
    toast('资源已加载到预览区', 'success');
  } catch (e) {
    panel.innerHTML = '<div class="error-card"><div class="err-title">生成失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function autoGenerateStudyArtifacts(topic, suggestions){
  topic = topic || _currentLearningTopic();
  const key = String(topic || '').trim();
  if (!key || S.autoArtifactRunning || S.autoArtifactTopicKey === key) return;
  S.autoArtifactRunning = true;
  S.autoArtifactTopicKey = key;
  const wanted = ['mindmap', 'quiz', 'lecture_doc', 'study_plan', 'ppt'];
  toast('正在自动生成导图、练习题、讲义、学习路径和PPT文字稿...', 'info');
  try {
    for (const type of wanted) {
      try {
        await loadArtifactPreview(type, topic);
      } catch (_) {}
    }
    _activateArtifactTab('mindmap');
    toast('配套导图、练习题、讲义、学习路径和PPT文字稿已生成', 'success');
  } finally {
    S.autoArtifactRunning = false;
  }
}

window.quickGenerateFromChat = function(type, topic){
  topic = topic || _currentLearningTopic();
  if (['mindmap', 'quiz', 'lecture_doc', 'ppt', 'study_plan', 'reading', 'video_script'].includes(type)) {
    const assistantPage = document.getElementById('page-assistant');
    if (assistantPage && assistantPage.classList.contains('active')) {
      loadArtifactPreview(type, topic);
      return;
    }
  }
  if (type === 'study_plan') {
    S.pendingStudyTopic = topic || '';
    navTo('learning-path');
    return;
  }
  S.generatorPrefill = {
    topic: topic || '',
    types: type ? [type] : ['lecture_doc', 'mindmap', 'quiz'],
    autoGenerate: Boolean(topic && type),
  };
  navTo('generator');
  setTimeout(function(){
    if (S.generatorPrefill && S.generatorPrefill.autoGenerate) generateResources();
    else toast('已切换到资源生成，请填写主题后生成', 'info');
  }, 120);
};

async function onSessionSelect(value){
  if (!value) return;
  const box = document.getElementById('chat-messages');
  if (!box) return;
  box.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载会话中...</div>';
  try {
    const r = await api('/api/sessions/' + value);
    const msgs = (r.ok && r.data && Array.isArray(r.data.messages)) ? r.data.messages : [];
    if (!msgs.length) {
      box.innerHTML = '<div class="empty-state"><div class="empty-icon">💬</div><p>该会话暂无消息</p></div>';
      return;
    }
    box.innerHTML = msgs.map(m => '<div class="msg-bubble ' + (m.role === 'user' ? 'user' : 'agent') + '"><div class="msg-content">' + esc(m.content || '') + '</div></div>').join('');
    box.scrollTop = box.scrollHeight;
  } catch (e) {
    box.innerHTML = '<div class="error-card"><div class="err-title">会话加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function createNewSession(){
  const box = document.getElementById('chat-messages');
  const sel = document.getElementById('session-select');
  try {
    const r = await api('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ course_id: S.courseId, title: '新的学习会话' })
    });
    if (r.ok && r.data && r.data.session) {
      try {
        await api('/api/analytics/audit', {
          method: 'POST',
          body: JSON.stringify({ action: 'session_create', target_type: 'session', target_id: String(r.data.session.id), detail: r.data.session.title || '' })
        });
      } catch (_) {}
      toast('会话已创建', 'success');
      if (sel) await refreshSessionList();
      if (box) box.innerHTML = '<div class="msg-bubble agent"><div class="msg-content">新会话已创建，可以开始提问。</div></div>';
      return;
    }
    toast('创建会话失败', 'info');
  } catch (e) {
    toast(e.message || '创建会话失败', 'info');
  }
}

function _getSelectedResourceTypes(){
  return Array.from(document.querySelectorAll('.resource-type-cb:checked')).map(el => el.value);
}

function renderResourceTrace(trace){
  const el = document.getElementById('resource-trace-list');
  if (!el) return;
  if (!trace || !trace.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">🧭</div><p>等待生成任务</p></div>';
    return;
  }
  const statusLabel = {
    queued: '排队中', planning: '规划中', retrieving: '检索中', generating: '生成中', verifying: '校验中', saving: '保存中', completed: '已完成', failed: '失败', running: '进行中'
  };
  el.innerHTML = trace.map(function(t, idx){
    const status = t.status || t.phase || 'running';
    const agent = t.agent || t.agent_name || t.name || ('ResourceAgent-' + (idx + 1));
    const message = t.message || t.summary || t.detail || '正在推进资源生成流程';
    const duration = t.latency_ms || t.duration_ms || t.ms;
    return '<div class="course-card"><h4>' + esc((idx + 1) + '. ' + agent) + '</h4><div class="course-meta"><span>' + esc(statusLabel[status] || status) + '</span>' + (duration ? '<span>' + esc(String(duration)) + 'ms</span>' : '') + '</div><div class="course-meta"><span>' + esc(message) + '</span></div></div>';
  }).join('');
}

function _defaultResourceTrace(types){
  const count = Array.isArray(types) ? types.length : 0;
  return [
    { agent: 'Planner Agent', status: 'planning', message: '分析学习主题、目标、难度和资源类型' },
    { agent: 'Retriever Agent', status: 'retrieving', message: '检索课程资料，为资源生成提供依据' },
    { agent: 'Profile Agent', status: 'running', message: '读取学习画像与掌握度，适配个人学习状态' },
    { agent: 'Generator Agent', status: 'generating', message: '生成 ' + count + ' 类个性化学习资源' },
    { agent: 'Verifier Agent', status: 'verifying', message: '校验引用覆盖率、内容安全与质量分' },
    { agent: 'ResourceBuilder Agent', status: 'saving', message: '聚合资源包并写入资源中心' },
  ];
}

function renderResourceJobResults(resources){
  const el = document.getElementById('resource-result-list');
  if (!el) return;
  if (!resources || !resources.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📦</div><p>暂无生成结果</p></div>';
    return;
  }
  el.innerHTML = resources.map(r => {
    const type = _resourceTypeOf(r);
    const title = r.title || resourceLabel(type);
    const fname = title + _resourceFileExt(type);
    const auditMeta = '<div class="course-meta"><span>Provider ' + esc(r.provider || r.generated_by || 'mock_curriculum') + '</span><span>Model ' + esc(r.model || 'mock_curriculum') + '</span><span>Fallback ' + esc(String(!!r.fallback_used)) + '</span><span>RAG ' + esc(String(!!r.used_rag)) + '</span><span>画像 ' + esc(String(!!r.used_profile)) + '</span><span>引用片段 ' + esc(String((r.context_chunks || r.evidence || []).length || 0)) + '</span></div>';
    return '<div class="course-card"><h4>' + esc(title) + '</h4><div class="course-meta"><span>' + esc(resourceLabel(type)) + '</span><span>质量 ' + esc(String(r.quality_score || '—')) + '</span></div>' + auditMeta +
      (r.question ? '<p style="font-size:12px;color:var(--gray-500);margin-top:6px">问题：' + esc(r.question) + '</p>' : '') +
      '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">' +
      _resourceDownloadBtn(r.resource_id, r.download_url, fname) +
      '<button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">去资源中心</button></div></div>';
  }).join('');
}

async function pollResourceJob(jobId){
  if (!jobId) return;
  const maxTries = 40;
  let tries = 0;
  const timer = setInterval(async () => {
    tries += 1;
    try {
      const r = await api('/api/resources/generate/' + encodeURIComponent(jobId));
      if (!r.ok || !r.data) return;
      const d = unwrapApi(r);
      S.resourceJobTrace = d.agent_trace || [];
      renderResourceTrace(S.resourceJobTrace);
      if (d.status === 'completed') {
        clearInterval(timer);
        const result = d.result || {};
        renderResourceJobResults(result.resources || []);
        toast('资源生成完成', 'success');
        return;
      }
      if (d.status === 'failed') {
        clearInterval(timer);
        toast(d.error_message || '资源生成失败', 'info');
      }
    } catch (_) {}
    if (tries >= maxTries) clearInterval(timer);
  }, 1200);
}

async function generateResources(){
  const topicEl = document.getElementById('resource-topic');
  const topic = topicEl ? topicEl.value.trim() : '';
  if (!topic) return toast('请输入学习主题', 'info');
  const types = _getSelectedResourceTypes();
  if (!types.length) return toast('请至少选择一种资源类型', 'info');
  const goalEl = document.getElementById('resource-goal');
  const diffEl = document.getElementById('resource-difficulty');
  renderResourceTrace(_defaultResourceTrace(types));
  try {
    const r = await api('/api/resources/generate', {
      method: 'POST',
      body: JSON.stringify({
        course_id: S.courseId,
        topic,
        resource_types: types,
        difficulty: diffEl ? diffEl.value : 'auto',
        goal: goalEl ? goalEl.value.trim() : '',
      }),
    });
    const payload = unwrapApi(r);
    if (r.ok && payload) {
      S.resourceJobId = payload.job_id;
      S.resourceJobTrace = payload.agent_trace || [];
      renderResourceTrace(S.resourceJobTrace);
      if (payload.resources && payload.resources.length) {
        renderResourceJobResults(payload.resources);
        toast('资源生成完成', 'success');
        return;
      }
      if (payload.job_id && payload.status === 'running') {
        pollResourceJob(payload.job_id);
        return;
      }
      toast('资源生成完成', 'success');
      return;
    }
    toast((r.data && r.data.error) || '资源生成失败', 'info');
  } catch (e) {
    toast(e.message || '资源生成失败', 'info');
  }
}

async function loadGenerator(){
  const el = document.getElementById('page-generator');
  if (!el) return;
  const prefill = S.generatorPrefill || {};
  el.innerHTML = '<div class="grid grid-2">' +
    '<div class="card"><div class="card-header"><h3>多智能体资源生成</h3></div>' +
    '<div class="form-group"><label>当前课程</label><input readonly value="' + esc(S.courseName || '') + '"></div>' +
    '<div class="form-group"><label>学习主题</label><input id="resource-topic" class="input" placeholder="例如：函数极限的定义、左右极限、无穷小与连续" value="' + esc(prefill.topic || '') + '"></div>' +
    '<div class="form-group"><label>学习目标</label><input id="resource-goal" class="input" placeholder="例如：期末复习 / 考研强化"></div>' +
    '<div class="form-group"><label>难度</label><select id="resource-difficulty" class="input"><option value="auto">自动</option><option value="easy">简单</option><option value="medium">中等</option><option value="hard">困难</option></select></div>' +
    '<div class="form-group"><label>资源类型</label><div class="resource-type-grid">' +
      ['lecture_doc:讲义','mindmap:思维导图','quiz:题库','ppt:PPT','reading:拓展阅读','video_script:视频脚本'].map(x => {
        const p = x.split(':');
        const selectedTypes = prefill.types || ['lecture_doc','mindmap','quiz'];
        return '<label><input class="resource-type-cb" type="checkbox" value="' + p[0] + '"' + (selectedTypes.includes(p[0]) ? ' checked' : '') + '> ' + esc(p[1]) + '</label>';
      }).join('') +
    '</div></div>' +
    '<button class="btn btn-primary" onclick="generateResources()">开始生成</button>' +
    '<p style="font-size:11px;color:var(--gray-400);margin-top:8px">系统将按 Planner → Retriever → Generator → Verifier 协作生成个性化资源包。</p></div>' +
    '<div class="card"><div class="card-header"><h3>生成过程</h3></div><div id="resource-trace-list" class="trace-list"><div class="empty-state"><div class="empty-icon">🧭</div><p>等待生成任务</p></div></div></div></div>' +
    '<div class="card" style="margin-top:12px"><div class="card-header"><h3>生成结果</h3><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">去资源中心</button></div><div id="resource-result-list"></div></div>';
}

function _resourceStats(files, bookmarks){
  const totalSize = files.reduce((sum, f) => sum + (Number(f.size) || 0), 0);
  return '<div class="grid grid-3" style="margin-bottom:12px"><div class="card grid-stat"><div class="val" style="color:var(--primary)">' + files.length + '</div><div class="lbl">资源数量</div></div><div class="card grid-stat"><div class="val" style="color:var(--success)">' + Math.round(totalSize / 1024) + 'KB</div><div class="lbl">资源总大小</div></div><div class="card grid-stat"><div class="val" style="color:var(--warning)">' + bookmarks.length + '</div><div class="lbl">收藏数量</div></div></div>';
}

function _resourcePackageOverview(files){
  if (!files.length) return '<div class="empty-state"><div class="empty-icon">📦</div><p>暂无资源包概览</p></div>';
  const grouped = {};
  files.forEach(function(f){
    const t = _resourceTypeOf(f);
    grouped[t] = (grouped[t] || 0) + 1;
  });
  const order = ['lecture_doc','mindmap','quiz','ppt','reading','video_script','file'];
  const labels = { lecture_doc: '讲义', mindmap: '思维导图', quiz: '练习题', ppt: 'PPT', reading: '拓展阅读', video_script: '视频脚本', file: '其他资源' };
  return '<div class="card" style="margin-bottom:12px"><div class="card-header"><h3>📦 资源包概览</h3></div><div class="course-meta" style="margin-bottom:8px"><span>已将当前资源聚合为可学习的资源包视图</span></div><div style="display:flex;gap:8px;flex-wrap:wrap">' + order.filter(function(k){ return grouped[k]; }).map(function(k){ return '<span class="lr-chip">' + esc(labels[k]) + ' ' + grouped[k] + '</span>'; }).join('') + '</div></div>';
}

function _resourceToolbar(filter, query, sort, typeFilter){
  const tabs = [
    { id: 'all', label: '全部' },
    { id: 'file', label: '文件' },
    { id: 'bookmark', label: '收藏' },
    { id: 'session', label: '会话' }
  ];
  return '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;align-items:center">' +
    '<input id="resource-search" class="input" style="min-width:220px;max-width:320px;flex:1" placeholder="搜索资源名称、类型或状态" value="' + esc(query || '') + '" onkeydown="if(event.key===\'Enter\'){loadResourceCenter(\'' + filter + '\', this.value, document.getElementById(\'resource-sort\') ? document.getElementById(\'resource-sort\').value : \'newest\', document.getElementById(\'resource-type-filter\') ? document.getElementById(\'resource-type-filter\').value : \'all\')}" />' +
    '<select id="resource-sort" class="input" style="min-width:130px;max-width:180px" onchange="loadResourceCenter(\'' + filter + '\', document.getElementById(\'resource-search\') ? document.getElementById(\'resource-search\').value : \'\', this.value, document.getElementById(\'resource-type-filter\') ? document.getElementById(\'resource-type-filter\').value : \'all\')">' +
      '<option value="newest"' + (sort === 'newest' ? ' selected' : '') + '>按最新</option>' +
      '<option value="oldest"' + (sort === 'oldest' ? ' selected' : '') + '>按最早</option>' +
      '<option value="name"' + (sort === 'name' ? ' selected' : '') + '>按名称</option>' +
      '<option value="size"' + (sort === 'size' ? ' selected' : '') + '>按大小</option>' +
    '</select>' +
    '<select id="resource-type-filter" class="input" style="min-width:130px;max-width:180px" onchange="loadResourceCenter(\'' + filter + '\', document.getElementById(\'resource-search\') ? document.getElementById(\'resource-search\').value : \'\', document.getElementById(\'resource-sort\') ? document.getElementById(\'resource-sort\').value : \'newest\', this.value)">' +
      ['all:全部类型','lecture_doc:讲义','mindmap:思维导图','quiz:练习题','ppt:PPT','reading:拓展阅读','video_script:视频脚本'].map(x => {
        const p = x.split(':');
        return '<option value="' + p[0] + '"' + (typeFilter === p[0] ? ' selected' : '') + '>' + esc(p[1]) + '</option>';
      }).join('') +
    '</select>' +
    tabs.map(t => '<button class="btn btn-sm ' + (filter === t.id ? 'btn-primary' : 'btn-outline') + '" onclick="loadResourceCenter(\'' + t.id + '\', document.getElementById(\'resource-search\') ? document.getElementById(\'resource-search\').value : \'\', document.getElementById(\'resource-sort\') ? document.getElementById(\'resource-sort\').value : \'newest\', document.getElementById(\'resource-type-filter\') ? document.getElementById(\'resource-type-filter\').value : \'all\')">' + esc(t.label) + '</button>').join('') +
  '</div>';
}

function _resourceTags(activeType){
  const tags = [
    ['lecture_doc', '讲义'], ['mindmap', '思维导图'], ['quiz', '练习题'], ['ppt', 'PPT'], ['reading', '拓展阅读'], ['video_script', '视频脚本']
  ];
  return '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">' + tags.map(t => '<button class="btn btn-sm ' + (activeType === t[0] ? 'btn-primary' : 'btn-outline') + '" onclick="loadResourceCenter(\'file\', document.getElementById(\'resource-search\') ? document.getElementById(\'resource-search\').value : \'\', document.getElementById(\'resource-sort\') ? document.getElementById(\'resource-sort\').value : \'newest\', \'' + t[0] + '\')">' + esc(t[1]) + '</button>').join('') + '</div>';
}

function _resourceTypeOf(file){
  const hay = [file.resource_type, file.type, file.label, file.title, file.content_type, file.original_filename, file.filename].filter(Boolean).join(' ').toLowerCase();
  if (/mindmap|导图|脑图|mermaid/.test(hay)) return 'mindmap';
  if (/quiz|题|练习|test/.test(hay)) return 'quiz';
  if (/ppt|presentation|slide|课件/.test(hay)) return 'ppt';
  if (/study_plan|学习路径|路径|计划/.test(hay)) return 'study_plan';
  if (/reading|阅读|拓展/.test(hay)) return 'reading';
  if (/video|script|视频|脚本/.test(hay)) return 'video_script';
  if (/lecture|doc|讲义|笔记|markdown|pdf/.test(hay)) return 'lecture_doc';
  return 'file';
}

function _resourceFileCards(files){
  if (!files.length) {
    return '<div class="empty-state"><div class="empty-icon">📦</div><p>当前没有已生成的资源</p><p style="font-size:11px;color:var(--gray-400)">生成讲义、导图、测验、PPT 或案例后，这里会显示资源列表</p><div style="margin-top:10px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'generator\')">去生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">先去提问</button></div></div>';
  }
  return files.map(f => {
    const type = _resourceTypeOf(f);
    const label = f.label || resourceLabel(type);
    const origin = f.title || f.original_filename || f.filename || label || '学习资源';
    const course = f.course_name || f.course_title || '';
    const createdAt = f.created_at || f.updated_at || '';
    const icon = { lecture_doc: '📘', mindmap: '🧠', quiz: '📝', ppt: '📊', reading: '📚', video_script: '🎬', study_plan: '🗺️', file: '📄' }[type] || '📄';
    const meta = [];
    meta.push('<span>大小 ' + Math.round((f.size||0)/1024) + 'KB</span>');
    meta.push('<span>' + esc(label) + '</span>');
    meta.push('<span>' + esc(f.status === 'completed' ? '已生成' : (f.status || '可用')) + '</span>');
    if (course) meta.push('<span>课程 ' + esc(course) + '</span>');
    if (createdAt) meta.push('<span>' + esc(String(createdAt).slice(0, 19).replace('T', ' ')) + '</span>');
    meta.push('<span>Provider ' + esc(f.provider || f.generated_by || 'mock_curriculum') + '</span>');
    meta.push('<span>Fallback ' + esc(String(!!f.fallback_used)) + '</span>');
    meta.push('<span>RAG ' + esc(String(!!f.used_rag)) + '</span>');
    meta.push('<span>画像 ' + esc(String(!!f.used_profile)) + '</span>');
    meta.push('<span>引用片段 ' + esc(String((f.context_chunks || f.evidence || []).length || 0)) + '</span>');
    const rid = esc(f.resource_id);
    const oname = esc(origin);
    return '<div class="course-card"><h4>' + icon + ' ' + oname + '</h4><div class="course-meta">' + meta.join('') + '</div>' +
      (f.question ? '<p style="font-size:12px;color:var(--gray-500);margin-top:6px">问题：' + esc(f.question) + '</p>' : '') +
      '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">' +
      _resourceDownloadBtn(f.resource_id, f.download_url, origin + _resourceFileExt(type)) +
      '<button class="btn btn-sm btn-outline" onclick="bookmarkResource(' + jsAttrArg(rid) + ', ' + jsAttrArg(oname) + ')">收藏</button><button class="btn btn-sm btn-outline" onclick="shareResource(' + jsAttrArg(rid) + ', ' + jsAttrArg(oname) + ')">分享</button></div></div>';
  }).join('');
}

function _resourceBookmarkCards(bookmarks){
  if (!bookmarks.length) {
    return '<div class="empty-state"><div class="empty-icon">🔖</div><p>暂无收藏资源</p><p style="font-size:11px;color:var(--gray-400)">收藏后会在这里集中展示</p></div>';
  }
  return bookmarks.map(b => {
    const title = esc(b.title || b.resource_id || '收藏资源');
    const rid = esc(b.resource_id || '');
    return '<div class="course-card"><h4>🔖 ' + title + '</h4><div class="course-meta"><span>' + rid + '</span><span>收藏项</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">查看资源</button><button class="btn btn-sm btn-outline" onclick="shareResource(' + jsAttrArg(rid) + ', ' + jsAttrArg(title) + ')">分享</button></div></div>';
  }).join('');
}

function _resourceSessionCards(sessions){
  if (!sessions.length) {
    return '<div class="empty-state"><div class="empty-icon">💬</div><p>暂无会话</p><p style="font-size:11px;color:var(--gray-400)">先去提问，系统会在这里保存学习记录</p><div style="margin-top:10px"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">去提问</button></div></div>';
  }
  return sessions.slice(0,5).map(s => '<div class="course-card"><h4>💬 ' + esc(s.title || '学习会话') + '</h4><div class="course-meta"><span>消息 ' + (s.message_count || 0) + '</span><span>会话</span></div><div style="margin-top:8px"><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">查看会话</button></div></div>').join('');
}

async function loadResourceCenter(filter = 'all', queryArg, sortArg, typeArg){
  const el = document.getElementById('page-resource-center');
  if (!el) return;
  if (queryArg !== undefined && queryArg !== null) S.resourceCenterQuery = String(queryArg);
  if (sortArg) S.resourceCenterSort = sortArg;
  if (typeArg) S.resourceCenterType = typeArg;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>资源中心</h3></div><div class="loading-block"><span class="spinner"></span> 加载资源中...</div></div>';
  try {
    const [filesRes, sessionsRes, bookmarksRes] = await Promise.all([
      api('/api/resources/generated'),
      api('/api/sessions'),
      api('/api/analytics/bookmarks')
    ]);
    const query = (S.resourceCenterQuery || '').trim().toLowerCase();
    const sort = S.resourceCenterSort || 'newest';
    const typeFilter = S.resourceCenterType || 'all';
    const filesRaw = filesRes.ok ? ((filesRes.data && filesRes.data.files) || filesRes.files || []) : [];
    const sessions = sessionsRes.ok ? (sessionsRes.data.sessions || []) : [];
    const bookmarks = bookmarksRes.ok ? (bookmarksRes.data.items || []) : [];
    let files = filesRaw.slice();
    if (query) {
      files = files.filter(f => {
        const hay = [f.title, f.label, f.type, f.resource_type, f.original_filename, f.filename, f.content_type, f.status, f.course_name, f.course_title].filter(Boolean).join(' ').toLowerCase();
        return hay.includes(query);
      });
    }
    if (typeFilter !== 'all') {
      files = files.filter(f => _resourceTypeOf(f) === typeFilter);
    }
    files.sort((a, b) => {
      if (sort === 'name') return String(a.title || a.original_filename || a.filename || '').localeCompare(String(b.title || b.original_filename || b.filename || ''), 'zh-Hans-CN');
      if (sort === 'size') return (Number(b.size) || 0) - (Number(a.size) || 0);
      const ta = new Date(a.created_at || a.updated_at || 0).getTime();
      const tb = new Date(b.created_at || b.updated_at || 0).getTime();
      return sort === 'oldest' ? ta - tb : tb - ta;
    });
    const stats = _resourceStats(files, bookmarks);
    const toolbar = _resourceToolbar(filter, query, sort, typeFilter);
    const tags = _resourceTags(typeFilter);
    const resourceFiles = _resourceFileCards(files);
    const bookmarkCards = _resourceBookmarkCards(bookmarks);
    const sessionCards = _resourceSessionCards(sessions);
    const packageOverview = _resourcePackageOverview(files);
    const sections = [];
    if (filter === 'all' || filter === 'file') sections.push('<div class="card"><div class="card-header"><h3>资源列表</h3></div>' + resourceFiles + '</div>');
    if (filter === 'all' || filter === 'bookmark') sections.push('<div class="card"><div class="card-header"><h3>收藏资源</h3></div>' + bookmarkCards + '</div>');
    if (filter === 'all' || filter === 'session') sections.push('<div class="card"><div class="card-header"><h3>最近会话</h3></div>' + sessionCards + '</div>');
    el.innerHTML = '<div class="card"><div class="card-header"><h3>资源中心</h3><button class="btn btn-sm btn-outline" onclick="loadResourceCenter(\'' + filter + '\')">🔄 刷新</button></div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px"><button class="btn btn-sm btn-primary" onclick="navTo(\'generator\')">⚡ 去生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">💬 去提问</button><button class="btn btn-sm btn-outline" onclick="navTo(\'learning-report\')">📊 看学习报告</button></div>' + stats + packageOverview + toolbar + tags + '</div><div id="resource-package-detail-host" style="margin-bottom:12px">' + (S.currentResourcePackage ? _resourcePackageDetailHtml(S.currentResourcePackage) : '') + '</div>' + sections.join('');
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">资源加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function loadWrongBook(){
  const el = document.getElementById('page-wrong-book');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>错题本</h3><button class="btn btn-sm btn-outline" onclick="loadWrongBook()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 加载中...</div></div>';
  try {
    const [wrongRes, reportRes] = await Promise.all([
      api('/api/analytics/wrong-book'),
      api('/api/app/learning-report?course_id=' + S.courseId)
    ]);
    const items = wrongRes.ok ? (wrongRes.data.items || []) : [];
    const report = reportRes.ok ? unwrapApi(reportRes) : {};
    const masteryItems = report.mastery_items || [];
    const masteryMap = {};
    masteryItems.forEach(function(m){ masteryMap[m.knowledge_point] = m; });
    const body = items.length ? items.map(it => {
      const kp = it.knowledge_point || it.topic || '未命名知识点';
      const questionText = it.question_text || it.question || '';
      const kpArg = jsAttrArg(kp);
      const questionArg = jsAttrArg(questionText);
      const mastery = masteryMap[kp] || {};
      const masteryScore = mastery.mastery_score !== undefined ? Math.round(Number(mastery.mastery_score || 0) * 100) : null;
      const actions = (it.review_actions || []).map(a =>
        '<button class="btn btn-sm btn-outline" onclick="joinReviewPlan(' + kpArg + ', ' + jsAttrArg((a.resource_types || [])[0] || 'lecture_doc') + ')">' + esc(a.title || '复习') + '</button>'
      ).join('');
      return '<div class="course-card"><h4>🧯 ' + esc(kp) + '</h4><div class="course-meta"><span>' + esc(questionText) + '</span></div>' +
        (masteryScore !== null ? '<div style="height:8px;background:var(--gray-200);border-radius:999px;overflow:hidden;margin-top:8px"><div style="height:100%;width:' + masteryScore + '%;background:linear-gradient(90deg,var(--warning),var(--primary))"></div></div><div class="course-meta" style="margin-top:6px"><span>当前掌握度 ' + masteryScore + '%</span><span>' + esc(mastery.recommended_action || '建议复盘并完成巩固练习') + '</span></div>' : '<div class="course-meta"><span>掌握度待测</span><span>完成一次练习后自动更新</span></div>') +
        (it.explanation ? '<div class="course-meta"><span>解析：' + esc(it.explanation) + '</span></div>' : '') +
        '<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="askWrongBookTopic(' + kpArg + ', ' + questionArg + ')">去追问</button>' +
        '<button class="btn btn-sm btn-outline" onclick="generateWrongBookResource(&quot;lecture_doc&quot;, ' + kpArg + ')">复习讲义</button>' +
        '<button class="btn btn-sm btn-outline" onclick="generateWrongBookResource(&quot;quiz&quot;, ' + kpArg + ')">巩固练习</button>' +
        '<button class="btn btn-sm btn-outline" onclick="generateWrongBookResource(&quot;mindmap&quot;, ' + kpArg + ')">知识结构图</button>' +
        actions +
        '<button class="btn btn-sm btn-primary" onclick="generateWrongBookReviewPath(' + kpArg + ')">生成复习路径</button></div></div>';
    }).join('') : '<div class="empty-state"><div class="empty-icon">🧯</div><p>暂无错题</p><p style="font-size:11px;color:var(--gray-400)">做完测验后，错题会自动出现在这里</p><div style="margin-top:10px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">去提问</button><button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(\'quiz\', \'当前主题\')">去做练习</button></div></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>错题本</h3><button class="btn btn-sm btn-outline" onclick="loadWrongBook()">🔄 刷新</button></div>' + body + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">错题本加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

function askWrongBookTopic(topic, questionText){
  const kp = (topic || '错题复盘').trim();
  S.lastTopic = kp;
  S.lastQuestion = questionText || kp;
  navTo('assistant');
  setTimeout(function(){
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = '请针对我的错题知识点「' + kp + '」讲清楚定义、常见误区，并给一个例题。';
      input.focus();
    }
    toast('已带入错题追问，可直接发送', 'success');
  }, 120);
}

async function generateWrongBookResource(type, topic){
  const kp = (topic || '错题复盘').trim();
  S.lastTopic = kp;
  toast('正在生成：' + resourceLabel(type), 'info');
  await loadArtifactPreview(type, kp);
}

async function generateWrongBookReviewPath(topic){
  const kp = (topic || '错题复盘').trim();
  toast('正在生成复习路径...', 'info');
  await joinReviewPlan(kp, 'study_plan');
}

function _learningReportInsights(report, wrongItems, bookmarks, audits, masteryItems, accuracy, rate){
  const avgMastery = Math.round(((report.mastery_overview || {}).avg_mastery || 0) * 100);
  const high = masteryItems.filter(m => Number(m.mastery_score || 0) >= 0.75).length;
  const mid = masteryItems.filter(m => Number(m.mastery_score || 0) >= 0.45 && Number(m.mastery_score || 0) < 0.75).length;
  const low = masteryItems.filter(m => Number(m.mastery_score || 0) < 0.45).length;
  const wrongMap = {};
  wrongItems.forEach(function(w){
    const k = w.knowledge_point || w.topic || '未归类';
    wrongMap[k] = (wrongMap[k] || 0) + 1;
  });
  const wrongBars = Object.keys(wrongMap).slice(0, 6).map(function(k){
    const n = wrongMap[k];
    const width = Math.min(100, n * 24);
    return '<div class="course-card"><h4>' + esc(k) + '</h4><div style="height:8px;background:var(--gray-200);border-radius:999px;overflow:hidden"><div style="height:100%;width:' + width + '%;background:var(--warning)"></div></div><div class="course-meta" style="margin-top:6px"><span>错题 ' + n + ' 道</span></div></div>';
  }).join('') || '<div class="empty-state"><div class="empty-icon">🧯</div><p>暂无错题分布</p></div>';
  const trend = [Math.max(0, rate - 12), Math.max(0, rate - 6), rate, accuracy !== null ? accuracy : avgMastery].map(function(v, i){
    const h = Math.max(8, Math.min(100, Number(v) || 0));
    return '<div style="flex:1;text-align:center"><div style="height:92px;display:flex;align-items:end;justify-content:center"><div style="width:22px;height:' + h + '%;border-radius:999px;background:linear-gradient(180deg,var(--primary),var(--success))"></div></div><div style="font-size:11px;color:var(--gray-500);margin-top:4px">' + ['起点','上次','当前','测验'][i] + '</div></div>';
  }).join('');
  return '<div class="lr-section"><div class="lr-section-title">学习效果趋势</div><div class="grid grid-2">' +
    '<div class="course-card"><h4>正确率 / 完成率趋势</h4><div style="display:flex;gap:8px;align-items:end;margin-top:8px">' + trend + '</div><div class="course-meta" style="margin-top:8px"><span>当前完成率 ' + rate + '%</span><span>测验正确率 ' + (accuracy !== null ? accuracy + '%' : '待测') + '</span></div></div>' +
    '<div class="course-card"><h4>掌握度分布</h4><div class="lr-chips" style="margin-top:8px"><span class="lr-chip">高掌握 ' + high + '</span><span class="lr-chip">中等 ' + mid + '</span><span class="lr-chip">需复盘 ' + low + '</span></div><div class="course-meta" style="margin-top:8px"><span>平均掌握度 ' + avgMastery + '%</span><span>资源收藏 ' + bookmarks.length + '</span></div></div>' +
    '</div></div>' +
    '<div class="lr-section"><div class="lr-section-title">错题与资源使用</div><div class="grid grid-2"><div>' + wrongBars + '</div><div class="course-card"><h4>本周学习摘要</h4><div class="course-meta"><span>行为记录 ' + audits.length + ' 条</span><span>收藏资源 ' + bookmarks.length + ' 个</span><span>待复盘错题 ' + wrongItems.length + ' 道</span></div><p style="font-size:13px;line-height:1.7;color:var(--gray-600);margin-top:8px">建议优先复盘低掌握度知识点，再生成讲义、导图和巩固练习，最后回到学习报告查看掌握度变化。</p></div></div></div>';
}

async function loadLearningReportPage(){
  const el = document.getElementById('lr-standalone');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载中...</div>';
  try {
    const [progressRes, wrongRes, bookmarkRes, auditRes, reportRes] = await Promise.all([
      api('/api/analytics/progress'),
      api('/api/analytics/wrong-book'),
      api('/api/analytics/bookmarks'),
      api('/api/analytics/audit?limit=20'),
      api('/api/app/learning-report?course_id=' + S.courseId)
    ]);
    const progress = (progressRes.ok && progressRes.data.items && progressRes.data.items[0]) || {};
    const wrongItems = (wrongRes.ok && wrongRes.data.items) || [];
    const bookmarks = (bookmarkRes.ok && bookmarkRes.data.items) || [];
    const audits = (auditRes.ok && auditRes.data.items) || [];
    const report = reportRes.ok ? unwrapApi(reportRes) : {};
    const rate = progress.total_lessons ? Math.round((progress.completed_lessons / progress.total_lessons) * 100) : Math.round((progress.completed_rate || 0) * 100);
    const weakPoints = (report.weak_points && report.weak_points.length) ? report.weak_points : (Array.isArray(progress.weak_points) ? progress.weak_points : []);
    const nextActions = report.next_actions || [];
    const profileSummary = report.profile_summary || {};
    const accuracy = report.accuracy !== undefined ? Math.round((report.accuracy || 0) * 100) : null;
    const masteryOverview = report.mastery_overview || {};
    const masteryItems = report.mastery_items || [];
    const activityCards = audits.length ? audits.slice(0,5).map(a => '<div class="course-card"><h4>🧾 ' + esc(a.action || '行为记录') + '</h4><div class="course-meta"><span>' + esc(a.detail || '') + '</span></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🧾</div><p>暂无行为记录</p></div>';
    const actionCards = nextActions.length ? nextActions.map(a =>
      '<div class="course-card"><h4>' + esc(a.title || '下一步') + '</h4><div class="course-meta"><span>' + esc(a.detail || '') + '</span></div><div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">' +
      ((a.resource_types || []).map(t => '<button class="btn btn-sm btn-outline" onclick="quickGenerateFromChat(' + jsAttrArg(t) + ', ' + jsAttrArg(weakPoints[0] || '当前主题') + ')">生成 ' + esc(resourceLabel(t)) + '</button>').join('')) +
      '</div></div>'
    ).join('') : '<div class="course-card"><h4>' + esc(progress.next_recommendation || '先完成一次问答或测验，系统会给出下一步推荐') + '</h4></div>';
    const masterySection = masteryItems.length ? '<div class="lr-section"><div class="lr-section-title">知识点掌握度</div><div style="display:grid;gap:8px">' + masteryItems.slice(0,8).map(function(m){
      const score = Math.max(0, Math.min(100, Math.round((m.mastery_score || 0) * 100)));
      return '<div class="course-card"><h4>' + esc(m.knowledge_point || '知识点') + '</h4><div style="height:8px;background:var(--gray-200);border-radius:999px;overflow:hidden"><div style="height:100%;width:' + score + '%;background:linear-gradient(90deg,var(--primary),var(--success))"></div></div><div class="course-meta" style="margin-top:6px"><span>掌握度 ' + score + '%</span><span>' + esc(m.recommended_action || '') + '</span></div></div>';
    }).join('') + '</div><div class="course-meta" style="margin-top:8px"><span>平均掌握度 ' + Math.round((masteryOverview.avg_mastery || 0) * 100) + '%</span></div></div>' : '';
    const insightSection = _learningReportInsights(report, wrongItems, bookmarks, audits, masteryItems, accuracy, rate);
    el.innerHTML = '<div class="card"><div class="card-header"><h3>学习报告</h3><button class="btn btn-sm btn-outline" onclick="loadLearningReportPage()">🔄 刷新</button></div>' +
      '<div class="lr-summary">' +
      '<div class="lr-stat"><span class="lr-stat-value">' + rate + '%</span><span class="lr-stat-label">完成率</span></div>' +
      '<div class="lr-stat"><span class="lr-stat-value">' + wrongItems.length + '</span><span class="lr-stat-label">错题数</span></div>' +
      '<div class="lr-stat"><span class="lr-stat-value">' + bookmarks.length + '</span><span class="lr-stat-label">收藏数</span></div>' +
      (accuracy !== null ? '<div class="lr-stat"><span class="lr-stat-value">' + accuracy + '%</span><span class="lr-stat-label">测验正确率</span></div>' : '') +
      '<div class="lr-stat"><span class="lr-stat-value">' + Math.round((masteryOverview.avg_mastery || 0) * 100) + '%</span><span class="lr-stat-label">平均掌握度</span></div>' +
      '</div>' +
      '<div class="lr-section"><div class="lr-section-title">画像驱动建议</div>' + actionCards +
      '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">继续提问</button><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'wrong-book\')">复盘错题</button><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">查看收藏资源</button></div></div>' +
      insightSection +
      masterySection +
      (weakPoints.length ? '<div class="lr-section"><div class="lr-section-title">薄弱知识点</div><div class="lr-chips">' + weakPoints.map(w => '<span class="lr-chip">' + esc(w) + '</span>').join('') + '</div></div>' : '') +
      '<div class="lr-section"><div class="lr-section-title">近期行为</div>' + activityCards + '</div>' +
      '<div class="lr-section"><div class="lr-section-title">学习目标</div><div class="course-card"><h4>' + esc(profileSummary.learning_goal || '建立“提问 - 生成 - 测验 - 复盘 - 推荐”的学习闭环') + '</h4><div class="course-meta"><span>基础水平 ' + esc(profileSummary.knowledge_level || '待识别') + '</span></div></div></div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">学习报告加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function joinReviewPlan(topic, resourceType){
  const kp = (topic || '').trim() || '错题复习';
  try {
    const r = await api('/api/analytics/review-plan', {
      method: 'POST',
      body: JSON.stringify({
        course_id: S.courseId,
        topic: kp,
        knowledge_points: [kp],
      }),
    });
    if (r.ok && r.data) {
      const planPayload = unwrapApi(r);
      const rawPlan = planPayload.study_plan || r.data.study_plan || planPayload.plan || r.data.plan || null;
      S.pendingStudyPlan = Array.isArray(rawPlan) ? { title: kp + ' · 复习路径', steps: rawPlan } : rawPlan;
      S.pendingStudyTopic = kp;
      toast('复习路径已生成', 'success');
      if (resourceType && resourceType !== 'study_plan') {
        navTo('assistant');
        loadArtifactPreview(resourceType, kp);
        return;
      }
      navTo('learning-path');
      return;
    }
    toast((r.data && r.data.detail) || '复习计划生成失败', 'info');
  } catch (e) {
    toast(e.message || '复习计划生成失败', 'info');
  }
}

async function loadSettings(){
  const el = document.getElementById('page-settings');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>账户与设置</h3><button class="btn btn-sm btn-outline" onclick="loadSettings()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 加载配置中...</div></div>';
  try {
    const r = await api('/api/settings/status');
    const d = (r.ok && r.data) ? r.data : {};
    S.llmProvider = d.llm_provider || S.llmProvider;
    S.llmModel = d.llm_model || S.llmModel;
    updateTopbar();
    const sparkDefaults = _providerDefaults('spark');
    const deepseekDefaults = _providerDefaults('deepseek');
    const sparkReady = d.spark_configured ? '已配置' : '未配置';
    const deepseekReady = d.deepseek_configured ? '已配置' : '未配置';
    const llmPanel =
      '<div class="form-group"><label>科大讯飞 API Key / APIPassword</label><input id="spark-api-key" class="input" type="password" placeholder="直接填入科大讯飞 APIPassword"></div>' +
      '<div class="form-group"><label>科大讯飞 API 入口</label><input id="spark-base-url" class="input" value="' + esc(d.spark_base_url_configured ? (d.spark_base_url || sparkDefaults.base_url) : sparkDefaults.base_url) + '" placeholder="例如 https://spark-api-open.xf-yun.com/v1"></div>' +
      '<div class="form-group"><label>科大讯飞 模型名称</label><input id="spark-model" class="input" value="' + esc(d.spark_model || sparkDefaults.model) + '"></div>' +
      '<div class="form-group"><label>超时(秒)</label><input id="spark-timeout" class="input" type="number" min="5" max="300" value="60"></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px"><button class="btn btn-primary" onclick="_saveLlmProvider(\'spark\')">保存科大讯飞配置</button><button class="btn btn-outline" onclick="_testLlmProvider(\'spark\')">测试科大讯飞连接</button></div>' +
      '<p id="spark-test-result" style="font-size:11px;color:var(--gray-400);margin-top:-6px;margin-bottom:16px">可直接填写科大讯飞 API；密钥不会回显。</p>' +
      '<div class="form-group"><label>DeepSeek API Key</label><input id="deepseek-api-key" class="input" type="password" placeholder="输入 DeepSeek API Key"></div>' +
      '<div class="form-group"><label>DeepSeek Base URL</label><input id="deepseek-base-url" class="input" value="' + esc(deepseekDefaults.base_url) + '"></div>' +
      '<div class="form-group"><label>DeepSeek 模型名称</label><input id="deepseek-model" class="input" value="' + esc(d.llm_model || deepseekDefaults.model) + '"></div>' +
      '<div class="form-group"><label>DeepSeek 超时(秒)</label><input id="deepseek-timeout" class="input" type="number" min="5" max="300" value="60"></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="_saveLlmProvider(\'deepseek\')">保存 DeepSeek 配置</button><button class="btn btn-outline" onclick="_testLlmProvider(\'deepseek\')">测试 DeepSeek 连接</button></div>' +
      '<p id="deepseek-test-result" style="font-size:11px;color:var(--gray-400);margin-top:8px">可修改 DeepSeek 连接配置；密钥不会回显。</p>';
    el.innerHTML =
      '<div class="grid grid-2">' +
      '<div class="card"><div class="card-header"><h3>账户与设置</h3></div>' +
      '<div class="form-group"><label>当前用户</label><input readonly value="管理员"></div>' +
      '<div class="form-group"><label>当前课程</label><input readonly value="' + esc(S.courseName || '未选择') + '"></div>' +
      '<div class="form-group"><label>权限状态</label><input readonly value="已开放全部设置"></div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="navTo(\'dashboard\')">进入系统</button><button class="btn btn-outline" onclick="loadSettings()">刷新状态</button></div></div>' +
      '<div class="card"><div class="card-header"><h3>推理引擎配置</h3></div>' +
      '<div class="course-card"><h4>当前：<span id="llm-provider">' + esc(d.llm_provider || '未配置') + '</span></h4><div class="course-meta"><span>模型 ' + esc(d.llm_model || '未知') + '</span><span>' + (d.is_mock ? '本地演示兜底 Mock' : '在线模型链路') + '</span></div><div class="course-meta"><span>星火：' + sparkReady + '</span><span>DeepSeek：' + deepseekReady + '</span><span>Fallback：' + esc(d.fallback_provider || 'mock') + '</span></div></div>' + llmPanel + '</div></div>' +
      '<div class="card" style="margin-top:12px"><div class="card-header"><h3>系统状态</h3></div>' +
      '<div class="grid grid-3"><div class="card grid-stat"><div class="val">' + (d.spark_configured ? '✓' : '—') + '</div><div class="lbl">Spark</div></div>' +
      '<div class="card grid-stat"><div class="val">' + (d.deepseek_configured ? '✓' : '—') + '</div><div class="lbl">DeepSeek</div></div>' +
      '<div class="card grid-stat"><div class="val">' + (d.fallback_available ? '✓' : '—') + '</div><div class="lbl">Fallback</div></div></div>' +
      '<div class="grid grid-3" style="margin-top:12px"><div class="card grid-stat"><div class="val">' + esc(String(d.chunks_count || 0)) + '</div><div class="lbl">知识片段</div></div>' +
      '<div class="card grid-stat"><div class="val">' + esc(String(d.vector_count || 0)) + '</div><div class="lbl">Chroma 向量</div></div>' +
      '<div class="card grid-stat"><div class="val">' + esc(d.knowledge_base_status || 'unknown') + '</div><div class="lbl">知识库状态</div></div></div>' +
      '<div class="course-card" style="margin-top:12px"><h4>问答模式</h4><div class="course-meta"><span>SSE 流式 ' + (S.useStreamAsk ? '已开启' : '已关闭') + '</span><span>课程：' + esc(d.course_name || S.courseName || '高等数学上册') + '</span><span>Embedding：' + esc(d.embedding_provider || 'hash_mock') + '</span></div>' +
      '<p style="font-size:12px;color:var(--danger);margin-top:8px">' + esc(d.embedding_note || 'hash_mock 仅用于流程验证，不代表真实语义向量效果') + '</p></div></div>';
  } catch (e) {
    _showPageError(el, '设置加载失败', e.message || '未知错误');
  }
}

function _providerDefaults(provider){
  return provider === 'spark'
    ? { base_url: 'https://spark-api-open.xf-yun.com/v1', model: 'generalv3.5' }
    : { base_url: 'https://api.deepseek.com', model: 'deepseek-v4-pro' };
}

async function _saveLlmProvider(provider){
  const apiKey = (document.getElementById(provider + '-api-key') || {}).value || '';
  const baseUrl = (document.getElementById(provider + '-base-url') || {}).value || '';
  const model = (document.getElementById(provider + '-model') || {}).value || '';
  const timeoutEl = document.getElementById(provider + '-timeout');
  const timeoutSeconds = Number((timeoutEl && timeoutEl.value) || 60) || 60;
  if (!apiKey.trim()) return toast('请填写 ' + (provider === 'spark' ? 'APIPassword' : 'API Key'), 'info');
  try {
    const r = await api('/api/settings/llm', {
      method: 'POST',
      body: JSON.stringify({ provider, api_key: apiKey.trim(), base_url: baseUrl.trim(), model: model.trim(), timeout_seconds: timeoutSeconds }),
    });
    if (r.ok && r.data && r.data.ok !== false) {
      toast((provider === 'spark' ? '讯飞星火' : 'DeepSeek') + ' 配置已保存', 'success');
      loadSettings();
      return;
    }
    toast((r.data && r.data.detail) || '保存失败', 'info');
  } catch (e) {
    toast(e.message || '保存失败', 'info');
  }
}

async function _testLlmProvider(provider){
  const model = (document.getElementById(provider + '-model') || {}).value || '';
  const resultEl = document.getElementById(provider + '-test-result');
  if (resultEl) resultEl.textContent = '正在测试连接...';
  try {
    const r = await api('/api/settings/test-llm', {
      method: 'POST',
      body: JSON.stringify({ provider, model, message: '你好，请用一句话确认连接成功' }),
    });
    const d = (r.ok && r.data) ? r.data : {};
    if (d.ok) {
      if (resultEl) resultEl.textContent = '连接成功 · ' + esc(d.provider || '') + ' · ' + esc(d.model || '') + ' · ' + Math.round(d.latency_ms || 0) + 'ms';
      toast((provider === 'spark' ? '讯飞星火' : 'DeepSeek') + ' 连接测试成功', 'success');
      S.llmProvider = d.provider || provider;
      S.llmModel = d.model || model;
      updateTopbar();
      return;
    }
    if (resultEl) resultEl.textContent = esc(d.message || d.error || '连接失败');
    toast(d.message || '连接失败', 'info');
  } catch (e) {
    if (resultEl) resultEl.textContent = esc(e.message || '连接失败');
    toast(e.message || '连接失败', 'info');
  }
}

function _finishAskResponse(el, msg, d, box){
  const answer = d.answer || d.content || d.result || '';
  const refs = d.refs || d.citations || [];
  const suggestions = d.resource_suggestions || [];
  const topicFromPackage = d.resource_package && (d.resource_package.topic || d.resource_package.title);
  S.lastQuestion = msg || S.lastQuestion || '';
  S.lastTopic = msg || topicFromPackage || S.lastTopic || '';
  S.lastAnswer = answer;
  S.pendingStudyTopic = S.lastTopic;
  S.pendingStudyPlan = null;
  if (d.student_profile && typeof d.student_profile === 'object') {
    S.currentProfile = d.student_profile;
  }
  if (el) {
    el.innerHTML = '<div class="msg-content">' + esc(answer || '已收到问题，当前环境暂未返回正式答案。') + '</div>' +
      (refs.length ? '<div class="msg-citations">📚 ' + refs.map(x => esc(typeof x === 'string' ? x : (x.source || x.chunk_id || '引用'))).join(' · ') + '</div>' : '') +
      _renderResourceSuggestions(suggestions, msg);
  }
  _renderAskSidebar(d);
  if (d.profile_delta || d.student_profile) {
    const profileHint = d.student_profile || d.profile_delta || {};
    toast('学习画像已根据本轮对话自动更新：' + (profileHint.last_topic || profileHint.learning_goal || profileHint.knowledge_level || '已识别新状态'), 'success');
  }
  const statusEl = document.getElementById('avatar-status-text');
  if (statusEl) {
    statusEl.textContent = (d.provider ? '模型 ' + d.provider : '讲解就绪') + ' · 可点击「讲解回答」';
  }
  const artifacts = d.generated_artifacts || {};
  if (artifacts.ready_for_generation && artifacts.suggestions && artifacts.suggestions.length) {
    setTimeout(function(){
      autoGenerateStudyArtifacts(msg || topicFromPackage || S.lastTopic, artifacts.suggestions);
    }, 120);
  }
  if (box) box.scrollTop = box.scrollHeight;
}

async function streamAsk(payload, onToken){
  const headers = { 'Content-Type': 'application/json' };
  if (S.token) headers.Authorization = 'Bearer ' + S.token;
  const res = await fetch(S.apiBase.replace(/\/$/, '') + '/api/app/ask/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = 'stream failed';
    try {
      const err = await res.json();
      detail = err.detail || err.error || detail;
    } catch (_) {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (!res.body) throw new Error('stream body unavailable');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let meta = {};
  let doneData = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      if (!block.trim()) continue;
      let eventName = 'message';
      let dataStr = '';
      block.split('\n').forEach(function(line){
        if (line.indexOf('event:') === 0) eventName = line.slice(6).trim();
        else if (line.indexOf('data:') === 0) dataStr += line.slice(5).trim();
      });
      if (!dataStr) continue;
      const parsed = JSON.parse(dataStr);
      if (eventName === 'meta') {
        meta = parsed;
        _renderAskSidebar({
          citations: parsed.citations || [],
          agent_traces: parsed.agent_traces || [],
          provider: parsed.provider,
          model: parsed.model,
        });
      } else if (eventName === 'token') {
        if (onToken) onToken(parsed.token || '');
      } else if (eventName === 'done') {
        doneData = parsed;
      } else if (eventName === 'error') {
        throw new Error(parsed.error || 'stream error');
      }
    }
  }
  return Object.assign({}, doneData || {}, {
    citations: (doneData && doneData.citations) || meta.citations || [],
    provider: (doneData && doneData.provider) || meta.provider,
    model: (doneData && doneData.model) || meta.model,
    agent_traces: (doneData && doneData.agent_traces) || meta.agent_traces || [],
    verifier_score: doneData && doneData.verifier_score,
    student_profile: (doneData && doneData.student_profile) || {},
    generated_artifacts: (doneData && doneData.generated_artifacts) || {},
  });
}

async function sendQuestion(){
  const input = document.getElementById('chat-input');
  const msg = input ? input.value.trim() : '';
  if (!msg) return toast('请输入问题', 'info');
  S.lastQuestion = msg;
  S.lastTopic = msg;
  const box = document.getElementById('chat-messages');
  if (box) box.innerHTML += '<div class="msg-bubble user"><div class="msg-content">' + esc(msg) + '</div></div>';
  if (input) input.value = '';

  const typingId = 'typing-' + Date.now();
  if (box) box.innerHTML += '<div class="msg-bubble agent" id="' + typingId + '"><div class="msg-content">正在检索课程资料并生成回答...</div></div>';

  const sessionSelect = document.getElementById('session-select');
  const sessionId = sessionSelect && sessionSelect.value ? Number(sessionSelect.value) : null;
  const payload = { course_id: S.courseId, question: msg, top_k: 5, session_id: sessionId };

  if (S.useStreamAsk) {
    try {
      let full = '';
      const d = await streamAsk(payload, function(token){
        full += token;
        const ce = document.querySelector('#' + typingId + ' .msg-content');
        if (ce) ce.textContent = full || '正在生成回答...';
        if (box) box.scrollTop = box.scrollHeight;
      });
      d.answer = d.answer || full;
      if (!d.answer) {
        _showAskError(typingId, '后端未返回有效答案，请稍后重试');
        return;
      }
      _finishAskResponse(document.getElementById(typingId), msg, d, box);
      return;
    } catch (streamErr) {
      const ce = document.querySelector('#' + typingId + ' .msg-content');
      if (ce) ce.textContent = '流式回答不可用，正在切换标准模式...';
    }
  }

  try {
    const r = await api('/api/app/ask', { method: 'POST', body: JSON.stringify(payload) });
    if (!r.ok) {
      const detail = (r.data && (r.data.detail || r.data.message)) || ('HTTP ' + r.status);
      _showAskError(typingId, typeof detail === 'string' ? detail : JSON.stringify(detail));
      toast('问答请求失败，请检查后端服务或模型配置', 'info');
      return;
    }
    const d = unwrapApi(r);
    if (!d.answer) {
      _showAskError(typingId, '后端未返回有效答案，请稍后重试');
      return;
    }
    _finishAskResponse(document.getElementById(typingId), msg, d, box);
    return;
  } catch (e) {
    _showAskError(typingId, e.message || '网络错误');
    toast('问答服务暂时不可用', 'info');
  }
}

function _speakText(text, label){
  if (!text || !text.trim()) return toast('暂无可讲解内容', 'info');
  if (!window.speechSynthesis) return toast('当前浏览器不支持语音讲解', 'info');
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text.slice(0, 1500));
  utter.lang = 'zh-CN';
  utter.rate = 0.95;
  S.speechUtterance = utter;
  const statusEl = document.getElementById('avatar-status-text');
  if (statusEl) statusEl.textContent = '正在讲解' + (label ? '：' + label : '') + '...';
  utter.onend = function(){
    if (statusEl) statusEl.textContent = '讲解完成，可再次播放';
  };
  utter.onerror = function(){
    if (statusEl) statusEl.textContent = '讲解失败，请重试';
  };
  window.speechSynthesis.speak(utter);
}

function _profileSnapshotText(profile){
  if (!profile) return '尚未提取画像';
  const bits = [];
  if (profile.profile_version) bits.push('版本 ' + profile.profile_version);
  if (profile.profile_source) bits.push('来源 ' + profile.profile_source);
  if (profile.profile_confidence !== undefined && profile.profile_confidence !== null) bits.push('置信度 ' + Math.round((Number(profile.profile_confidence) || 0) * 100) + '%');
  return bits.join(' · ') || '尚未提取画像';
}

function _unwrapProfilePayload(res){
  const d = unwrapApi(res);
  if (d && d.profile && typeof d.profile === 'object') return d.profile;
  return d || {};
}

async function loadProfileCenter(){
  const el = document.getElementById('page-profile');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载学习画像中...</div>';
  try {
    const [profileRes, historyRes] = await Promise.all([
      api('/api/profiles/current'),
      api('/api/profiles/history')
    ]);
    const profile = profileRes.ok ? _unwrapProfilePayload(profileRes) : {};
    const history = historyRes.ok ? unwrapApi(historyRes) : {};
    S.currentProfile = profile;
    const weakPoints = _parseJsonList(profile.weak_points);
    const prefs = _parseJsonList(profile.resource_preference);
    const versions = history.versions || [];
    const changes = history.change_logs || [];
    const cards = [
      ['知识基础', profile.knowledge_level || '未识别', '决定讲解深度和例题难度'],
      ['学习目标', profile.learning_goal || '未识别', '用于规划资源包和学习路径'],
      ['认知风格', profile.cognitive_style || '未识别', '决定图解、推导、案例或练习优先级'],
      ['内容偏好', prefs.join(' · ') || '暂无', '用于推荐讲义、导图、题库、PPT、阅读或视频脚本'],
      ['薄弱点', weakPoints.join(' · ') || '暂无', '用于错题复盘和专项资源生成'],
      ['学习节奏', profile.pace_preference || 'moderate', '用于控制学习路径节奏和复习频率'],
      ['学习历史', versions.length + ' 个画像版本 / ' + changes.length + ' 条变化', '来自对话、测验、错题和学习行为'],
      ['情绪信心', profile.emotion_tendency || profile.confidence_level || '待识别', '用于调整鼓励、提示和辅导方式'],
    ];
    let h = '';
    h += '<div class="card"><div class="card-header"><h3>学习画像中心</h3><button class="btn btn-sm btn-outline" onclick="loadProfileCenter()">🔄 刷新</button></div>';
    h += '<div class="course-card"><h4>画像概览</h4><div class="course-meta"><span>' + esc(_profileSnapshotText(profile)) + '</span><span>确认状态 ' + esc(profile.profile_source || 'dialogue') + '</span><span>版本 #' + esc(String(profile.profile_version || 1)) + '</span></div></div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>六维学习画像</h3></div><div class="grid grid-2">' + cards.map(c => '<div class="course-card"><h4>' + esc(c[0]) + '</h4><div class="course-meta"><span>' + esc(c[1]) + '</span></div><p style="font-size:12px;line-height:1.6;color:var(--gray-500);margin-top:6px">' + esc(c[2]) + '</p></div>').join('') + '</div></div>';
    h += '<div class="grid grid-2" style="margin-top:12px">';
    h += '<div class="card"><div class="card-header"><h3>画像如何参与生成</h3></div><div class="course-card"><h4>问答适配</h4><div class="course-meta"><span>根据知识基础和认知风格调整回答深度</span></div></div><div class="course-card"><h4>资源包适配</h4><div class="course-meta"><span>根据内容偏好和薄弱点选择资源类型</span></div></div><div class="course-card"><h4>学习路径适配</h4><div class="course-meta"><span>根据学习节奏和掌握度安排复习顺序</span></div></div></div>';
    h += '<div class="card"><div class="card-header"><h3>画像操作</h3></div><div class="course-card"><h4>自动对话构建</h4><div class="course-meta"><span>通过自然语言提取并持续修正画像</span></div></div><div class="course-card"><h4>历史版本</h4><div class="course-meta"><span>' + esc(String(versions.length)) + ' 个版本</span></div></div><div class="course-card"><h4>变更日志</h4><div class="course-meta"><span>' + esc(String(changes.length)) + ' 条变化记录</span></div></div></div>';
    h += '</div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>对话式画像构建</h3></div>';
    h += '<div class="form-group"><label>用自然语言描述你的专业、目标、偏好与薄弱点</label><textarea id="profile-dialogue-input" class="input" rows="4" placeholder="例如：我是计算机专业，准备考研，基础一般，喜欢看思维导图和例题，导数和线性代数比较薄弱"></textarea></div>';
    h += '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="extractProfileFromDialogue()">从对话更新画像</button><button class="btn btn-outline" onclick="confirmProfile()">确认当前画像</button><button class="btn btn-outline" onclick="navTo(\'assistant\')">去会话中心</button></div></div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>系统判断依据</h3></div>';
    h += (changes.length ? changes.slice(0, 8).map(c => '<div class="course-card"><h4>' + esc(c.field_name) + '</h4><div class="course-meta"><span>' + esc(c.old_value || '—') + ' → ' + esc(c.new_value || '—') + '</span></div><div class="course-meta"><span>' + esc(c.reason || '') + '</span><span>来源 ' + esc(c.source_type || '') + '</span></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">💡</div><p>暂无解释记录，发起对话或学习行为后会自动生成</p></div>') + '</div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>历史版本</h3></div>' + (versions.length ? versions.map(v => '<div class="course-card"><h4>版本 #' + esc(v.version) + '</h4><div class="course-meta"><span>' + esc(v.trigger_source || 'dialogue') + '</span><span>置信度 ' + esc(String(v.confidence || 0)) + '</span></div><div style="margin-top:6px"><button class="btn btn-sm btn-outline" onclick="restoreProfileVersion(' + jsAttrArg(v.id) + ')">回滚到此版本</button></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🕰️</div><p>暂无历史版本</p></div>') + '</div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>学习建议</h3></div><div class="course-card"><h4>下一步动作</h4><div class="course-meta"><span>去会话中心提问、完成一次测验、再回到画像中心确认变化</span></div></div></div>';
    h += '<div class="card" style="margin-top:12px"><div class="card-header"><h3>变更日志</h3></div>' + (changes.length ? changes.map(c => '<div class="course-card"><h4>' + esc(c.field_name) + '</h4><div class="course-meta"><span>' + esc(c.old_value || '—') + '</span><span>→</span><span>' + esc(c.new_value || '—') + '</span></div><div class="course-meta"><span>' + esc(c.reason || '') + '</span></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🧾</div><p>暂无变更日志</p></div>') + '</div>';
    el.innerHTML = h;
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">画像加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function extractProfileFromDialogue(){
  const el = document.getElementById('profile-dialogue-input');
  const message = el ? el.value.trim() : '';
  if (!message) return toast('请先输入描述', 'info');
  try {
    const r = await api('/api/profiles/me/extract', { method: 'POST', body: JSON.stringify({ message }) });
    if (r.ok) {
      toast('画像已从对话更新', 'success');
      loadProfileCenter();
      return;
    }
    toast((r.data && r.data.detail) || '画像更新失败', 'info');
  } catch (e) {
    toast(e.message || '画像更新失败', 'info');
  }
}

async function confirmProfile(){
  try {
    const r = await api('/api/profiles/me/confirm', { method: 'POST', body: JSON.stringify({}) });
    if (r.ok) {
      toast('已确认当前画像', 'success');
      loadProfileCenter();
      return;
    }
    toast('确认失败', 'info');
  } catch (e) {
    toast(e.message || '确认失败', 'info');
  }
}

async function loadCourses(){
  const el = document.getElementById('page-courses');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载课程中...</div>';
  try {
    const r = await api('/api/courses');
    const courses = r.ok ? (Array.isArray(r.data) ? r.data : []) : (S.courses || []);
    if (!courses.length && S.courses.length) courses.push(...S.courses);
    S.courses = courses;
    const body = courses.length ? courses.map(c => {
      const cid = c.id;
      const active = cid === S.courseId;
      return '<div class="course-card"><h4>📘 ' + esc(c.name || '未命名课程') + (active ? ' <span class="topbar-badge ok">当前</span>' : '') + '</h4><div class="course-meta"><span>' + esc(c.description || '暂无简介') + '</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm ' + (active ? 'btn-outline' : 'btn-primary') + '" onclick="selectCourse(' + jsAttrArg(cid) + ', ' + jsAttrArg(c.name || '') + ')">' + (active ? '已选中' : '切换到此课程') + '</button></div></div>';
    }).join('') : '<div class="empty-state"><div class="empty-icon">📘</div><p>暂无课程</p><p style="font-size:11px;color:var(--gray-400)">教师账户可创建课程并上传资料</p></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>课程中心</h3><button class="btn btn-sm btn-outline" onclick="loadCourses()">🔄 刷新</button><button class="btn btn-sm btn-primary" onclick="createCoursePrompt()">+ 新建课程</button></div>' + body + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">课程加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

function selectCourse(id, name){
  S.courseId = Number(id) || S.courseId;
  S.courseName = name || S.courseName;
  updateTopbar();
  toast('已切换到课程：' + (name || id), 'success');
  loadCourses();
}

async function createCoursePrompt(){
  const name = window.prompt('请输入课程名称');
  if (!name || !name.trim()) return;
  const description = window.prompt('请输入课程简介（可选）') || '';
  try {
    const r = await api('/api/courses', { method: 'POST', body: JSON.stringify({ name: name.trim(), description: description.trim() }) });
    if (r.ok && r.data) {
      toast('课程创建成功', 'success');
      loadCourses();
      return;
    }
    toast((r.data && r.data.detail) || '创建失败，请检查后端服务', 'info');
  } catch (e) {
    toast(e.message || '创建失败', 'info');
  }
}

async function loadKnowledgeBase(){
  const el = document.getElementById('page-knowledge');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载知识库中...</div>';
  try {
    const [dashRes, filesRes] = await Promise.all([
      api('/api/app/dashboard?course_id=' + S.courseId),
      api('/api/courses/' + S.courseId + '/files')
    ]);
    const dash = dashRes.ok ? unwrapApi(dashRes) : {};
    const kb = dash.knowledge_base || {};
    const files = filesRes.ok ? (Array.isArray(filesRes.data) ? filesRes.data : []) : [];
    const uploadBlock = '<div class="form-group"><label>支持 PDF / Word / TXT / PPT</label><input id="kb-upload-input" type="file" accept=".pdf,.doc,.docx,.txt,.ppt,.pptx" onchange="uploadCourseFile(this)"></div><p style="font-size:11px;color:var(--gray-400)">上传后系统会自动解析、切片并写入 ChromaDB 向量库。</p><button class="btn btn-sm btn-outline" style="margin-top:8px" onclick="buildCourseIndex()">🔍 重建向量索引</button>';
    const fileCards = files.length ? files.map(f =>
      '<div class="course-card"><h4>📄 ' + esc(f.original_filename || '文件') + '</h4><div class="course-meta"><span>状态 ' + esc(f.status || 'unknown') + '</span><span>' + esc(f.content_type || '') + '</span></div></div>'
    ).join('') : '<div class="empty-state"><div class="empty-icon">📚</div><p>暂无课程文件</p><p style="font-size:11px;color:var(--gray-400)">上传 PDF/PPT/Word 后将自动切片入库</p></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>知识库 · ' + esc(S.courseName || '') + '</h3><button class="btn btn-sm btn-outline" onclick="loadKnowledgeBase()">🔄 刷新</button></div>' +
      '<div class="grid grid-3" style="margin-bottom:12px"><div class="card grid-stat"><div class="val" style="color:var(--primary)">' + esc(String(kb.chunks_count || 0)) + '</div><div class="lbl">知识片段</div></div><div class="card grid-stat"><div class="val" style="color:var(--success)">' + esc(String(kb.vector_count || 0)) + '</div><div class="lbl">向量索引</div></div><div class="card grid-stat"><div class="val" style="color:var(--warning)">' + esc(kb.status || 'unknown') + '</div><div class="lbl">库状态</div></div></div>' +
      '<div class="card" style="margin-bottom:12px"><div class="card-header"><h3>上传课程资料</h3></div>' + uploadBlock + '</div>' +
      '<div class="card"><div class="card-header"><h3>课程文件</h3></div>' + fileCards + '</div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">知识库加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function _pollKnowledgeBaseChunks(maxTries){
  for (let i = 0; i < maxTries; i++) {
    await new Promise(function(resolve){ setTimeout(resolve, 1500); });
    try {
      const dash = await api('/api/app/dashboard?course_id=' + S.courseId);
      const kb = dash.ok ? (unwrapApi(dash).knowledge_base || {}) : {};
      const chunks = Number(kb.chunks_count || 0);
      const vectors = Number(kb.vector_count || 0);
      if (chunks > 0 && vectors > 0) {
        loadKnowledgeBase();
        toast('知识库已更新：' + chunks + ' 片段 · ' + vectors + ' 向量', 'success');
        return;
      }
      if (chunks > 0 && i >= maxTries - 1) {
        loadKnowledgeBase();
        toast('切片已入库（' + chunks + '），向量索引可能仍在构建', 'info');
        return;
      }
    } catch (_) {}
  }
  loadKnowledgeBase();
}

async function buildCourseIndex(){
  toast('正在构建 ChromaDB 向量索引...', 'info');
  try {
    const r = await api('/api/rag/courses/' + S.courseId + '/build', { method: 'POST' });
    if (r.ok && r.data) {
      toast('向量索引已更新：' + (r.data.indexed_chunks || 0) + ' 条', 'success');
      loadKnowledgeBase();
      return;
    }
    toast((r.data && r.data.detail) || '构建失败，请检查后端服务', 'info');
  } catch (e) {
    toast(e.message || '构建失败', 'info');
  }
}

async function uploadCourseFile(inputEl){
  const file = inputEl && inputEl.files && inputEl.files[0];
  if (!file) return;
  toast('正在上传并解析：' + file.name, 'info');
  try {
    const headers = {};
    if (S.token) headers.Authorization = 'Bearer ' + S.token;
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(S.apiBase.replace(/\/$/, '') + '/api/courses/' + S.courseId + '/files', {
      method: 'POST',
      headers,
      body: fd,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    if (res.ok) {
      const indexed = Number(data.indexed_chunks || 0);
      const chunks = Number(data.chunks || 0);
      toast('上传成功' + (chunks ? '，切片 ' + chunks + ' 条' : '') + (indexed ? '，已向量化 ' + indexed + ' 条' : '，知识库正在更新'), 'success');
      _pollKnowledgeBaseChunks(6);
      return;
    }
    toast(data.detail || data.message || '上传失败，请检查后端服务', 'info');
  } catch (e) {
    toast(e.message || '上传失败', 'info');
  } finally {
    if (inputEl) inputEl.value = '';
  }
}

async function loadLearningPath(){
  const el = document.getElementById('page-learning-path');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载学习路径中...</div>';
  const topic = S.pendingStudyTopic || S.lastTopic || S.lastQuestion || (document.getElementById('chat-input') || {}).value?.trim() || '当前学习主题';
  try {
    let plan = S.pendingStudyPlan || {};
    if (!plan || !plan.steps) {
      const r = await api('/api/app/generate', {
        method: 'POST',
        body: JSON.stringify({ course_id: S.courseId, resource_type: 'study_plan', topic })
      });
      const d = r.ok ? unwrapApi(r) : {};
      plan = d.study_plan || {};
      S.pendingStudyPlan = plan;
    }
    const steps = Array.isArray(plan.steps) ? plan.steps : [];
    const body = steps.length ? steps.map(function(s, i){
      const stepTopic = s.topic || s.title || s.name || topic;
      const types = Array.isArray(s.resource_types) && s.resource_types.length ? s.resource_types : ['lecture_doc', 'mindmap', 'quiz'];
      const resourceBtns = types.slice(0, 4).map(function(t){
        return '<button class="btn btn-sm btn-outline" onclick="loadArtifactPreview(' + jsAttrArg(t) + ', ' + jsAttrArg(stepTopic) + ')">生成' + esc(resourceLabel(t)) + '</button>';
      }).join('');
      return '<div class="course-card">' +
        '<h4>步骤 ' + esc(String(s.order || i + 1)) + ' · ' + esc(stepTopic) + '</h4>' +
        '<p style="font-size:13px;line-height:1.75;color:var(--gray-700);margin:8px 0">' + esc(s.description || s.detail || '') + '</p>' +
        '<div class="course-meta"><span>为什么学：' + esc(s.reason || '根据最近提问和画像推荐') + '</span></div>' +
        '<div class="course-meta" style="margin-top:6px"><span>预计 ' + esc(String(s.estimated_minutes || 15)) + ' 分钟</span><span>资料：' + esc(types.map(resourceLabel).join(' / ')) + '</span></div>' +
        (s.practice ? '<div class="course-meta" style="margin-top:6px"><span>练习任务：' + esc(s.practice) + '</span></div>' : '') +
        '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' + resourceBtns + '</div></div>';
    }).join('') : '<div class="empty-state"><div class="empty-icon">🗺️</div><p>暂无学习路径</p><p style="font-size:11px;color:var(--gray-400)">先在会话中心提问，或从错题本生成复习路径</p><button class="btn btn-sm btn-primary" style="margin-top:10px" onclick="navTo(\'assistant\')">去提问</button></div>';
    const summary = plan.profile_summary || (S.currentProfile && S.currentProfile.learning_goal) || '会根据最近问题、画像、错题和资源偏好实时生成';
    const recommended = Array.isArray(plan.recommended_topics) && plan.recommended_topics.length
      ? '<div class="lr-chips" style="margin:10px 0">' + plan.recommended_topics.map(function(t){ return '<span class="lr-chip">' + esc(t) + '</span>'; }).join('') + '</div>'
      : '';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>学习路径 · ' + esc(plan.title || topic) + '</h3><button class="btn btn-sm btn-outline" onclick="S.pendingStudyPlan=null;loadLearningPath()">🔄 重新生成</button></div>' +
      '<div class="course-card"><h4>个性化依据</h4><div class="course-meta"><span>' + esc(summary) + '</span></div>' + recommended + (plan.next_action ? '<div class="course-meta"><span>下一步：' + esc(plan.next_action) + '</span></div>' : '') + '</div>' +
      body + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">学习路径加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function bookmarkResource(resourceId, title){
  if (!resourceId) return toast('资源 ID 无效', 'info');
  try {
    const r = await api('/api/analytics/bookmarks', {
      method: 'POST',
      body: JSON.stringify({ resource_id: resourceId, title: title || resourceId })
    });
    if (r.ok) {
      toast('已收藏', 'success');
      return;
    }
    toast((r.data && r.data.detail) || '收藏失败', 'info');
  } catch (e) {
    toast(e.message || '收藏失败', 'info');
  }
}

async function shareResource(resourceId, title){
  toast('可在资源中心点击「下载」获取文件', 'info');
}

async function restoreProfileVersion(versionId){
  if (!versionId) return;
  try {
    const r = await api('/api/profiles/history/' + versionId + '/restore', { method: 'POST' });
    if (r.ok) {
      toast('画像已回滚', 'success');
      loadProfileCenter();
      return;
    }
    toast((r.data && r.data.detail) || '回滚失败', 'info');
  } catch (e) {
    toast(e.message || '回滚失败', 'info');
  }
}

window.navTo = navTo;
window.loadDashboard = loadDashboard;
window.loadResourceCenter = loadResourceCenter;
window.loadLearningReportPage = loadLearningReportPage;
window.loadWrongBook = loadWrongBook;
window.askWrongBookTopic = askWrongBookTopic;
window.generateWrongBookResource = generateWrongBookResource;
window.generateWrongBookReviewPath = generateWrongBookReviewPath;
globalThis.askWrongBookTopic = askWrongBookTopic;
globalThis.generateWrongBookResource = generateWrongBookResource;
globalThis.generateWrongBookReviewPath = generateWrongBookReviewPath;
window.loadSettings = loadSettings;
window.loadProfileCenter = loadProfileCenter;
window.restoreProfileVersion = restoreProfileVersion;
window.uploadCourseFile = uploadCourseFile;
window.loadCourses = loadCourses;
window.selectCourse = selectCourse;
window.createCoursePrompt = createCoursePrompt;
window.loadKnowledgeBase = loadKnowledgeBase;
window.buildCourseIndex = buildCourseIndex;
window.loadLearningPath = loadLearningPath;
window.bookmarkResource = bookmarkResource;
window.shareResource = shareResource;
window.onSessionSelect = onSessionSelect;
window.loadAssistant = loadAssistant;
window.quickGenerateFromChat = quickGenerateFromChat;
window.loadArtifactPreview = loadArtifactPreview;
window._zoomMermaid = _zoomMermaid;
window._resetMermaidZoom = _resetMermaidZoom;
window._fitMermaidToView = _fitMermaidToView;
window.downloadAuthFile = downloadAuthFile;
window.submitQuizAnswer = submitQuizAnswer;
window.joinReviewPlan = joinReviewPlan;
window.loadGenerator = loadGenerator;
window.generateResources = generateResources;
window.extractProfileFromDialogue = extractProfileFromDialogue;
window.confirmProfile = confirmProfile;
window.createNewSession = createNewSession;
window.sendQuestion = sendQuestion;
window._sendQuestion = sendQuestion;
window._quickGenerate = function(type){
  quickGenerateFromChat(type, _currentLearningTopic());
};
window._runOneClickDemo = async function(){
  navTo('assistant');
  const input = document.getElementById('chat-input');
  const question = '我不懂函数极限，讲清定义、常见误区，并给一个例题。我基础比较差。';
  if (input) input.value = question;
  toast('一键演示：正在按函数极限问题跑完整学习闭环', 'info');
  await sendQuestion();
};
window._avatarSpeakAnswer = function(){
  if (!S.lastAnswer) {
    const lastAgent = document.querySelector('#chat-messages .msg-bubble.agent:last-child .msg-content');
    if (lastAgent) S.lastAnswer = lastAgent.textContent || '';
  }
  if (!S.lastAnswer) {
    navTo('assistant');
    return toast('请先在会话中心提问并获得回答', 'info');
  }
  _speakText(S.lastAnswer, '最新回答');
};
window._avatarSpeakPath = function(){
  const steps = document.querySelectorAll('#page-learning-path .course-card h4');
  const text = steps.length
    ? Array.from(steps).map(function(n){ return n.textContent; }).join('。')
    : '请先在学习路径页生成个性化复习步骤。';
  _speakText(text, '学习路径');
};
window._avatarStop = function(){
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  const statusEl = document.getElementById('avatar-status-text');
  if (statusEl) statusEl.textContent = '已停止讲解';
  toast('已停止讲解', 'info');
};
function startCompetitionView(){
  navTo('assistant');
}

window.addEventListener('DOMContentLoaded', bootstrap);
