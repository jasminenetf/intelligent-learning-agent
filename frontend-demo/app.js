// 智学工坊前端恢复版（精简可运行）
// 目标：恢复基础导航、首页仪表盘、会话中心、课程中心、资源中心、错题本、学习报告与设置页。

const S = {
  apiBase: window.__API_BASE__ || 'http://127.0.0.1:8000',
  token: localStorage.getItem('hermes_token') || '',
  user: null,
  courseId: 5,
  courseName: '人工智能导论',
  courses: [],
  sidebarCollapsed: false,
};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
function esc(s){ return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function api(path, opts={}) {
  const headers = {'Content-Type':'application/json'};
  if (S.token) headers.Authorization = 'Bearer ' + S.token;
  const res = await fetch(S.apiBase.replace(/\/$/,'') + path, { ...opts, headers });
  let data = {};
  try { data = await res.json(); } catch (_) {}
  return { ok: res.ok, status: res.status, data };
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

function setToken(t){
  S.token = t;
  if (t) localStorage.setItem('hermes_token', t);
  else localStorage.removeItem('hermes_token');
  updateTopbar();
}

function updateTopbar(){
  const u = $('#topbar-user');
  const c = $('#topbar-course');
  const b = $('#topbar-badge');
  const sf = $('#sidebar-footer');
  const lo = $('#btn-logout');
  const t = $('#topbar-time');
  if (S.user && u) {
    u.innerHTML = '<span class="topbar-avatar">' + esc((S.user.username||'?')[0].toUpperCase()) + '</span><span>' + esc(S.user.username||'') + '</span>';
    if (lo) lo.style.display = 'inline-flex';
  } else if (u) {
    u.innerHTML = '<button class="btn btn-sm btn-primary" onclick="_loginDemo()">演示登录</button>';
    if (lo) lo.style.display = 'none';
  }
  if (c) c.textContent = S.courseName || '未选择';
  if (b) { b.className = 'topbar-badge ok'; b.textContent = S.token ? '已登录' : '未登录'; }
  if (sf) sf.innerHTML = S.token ? '<span class="status-dot online"></span> 已登录' : '<span class="status-dot offline"></span> 未登录';
  if (t) t.textContent = new Date().toLocaleString('zh-CN', { hour12: false });
}

function navTo(id){
  $$('.page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + id);
  if (pg) pg.classList.add('active');
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  const ni = $('.nav-item[data-page="' + id + '"]');
  if (ni) ni.classList.add('active');

  if (id === 'dashboard') loadDashboard();
  if (id === 'assistant') loadAssistant();
  if (id === 'courses') loadCourses();
  if (id === 'generator') loadGenerator();
  if (id === 'resource-center') loadResourceCenter();
  if (id === 'wrong-book') loadWrongBook();
  if (id === 'learning-report') loadLearningReportPage();
  if (id === 'settings') loadSettings();
  if (id === 'knowledge') loadKnowledgeBase();
  if (id === 'learning-path') loadLearningPath();
  if (id === 'competition') startCompetitionView();
}

window._toggleSidebar = function(){
  S.sidebarCollapsed = !S.sidebarCollapsed;
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('collapsed', S.sidebarCollapsed);
};

window._loginDemo = async function(){
  // 尝试用后端演示接口登录；失败则仅显示本地界面。
  try {
    const r = await api('/api/app/demo-init', { method: 'POST' });
    if (r.ok && r.data && r.data.token) {
      setToken(r.data.token);
      S.user = r.data.user || { username: 'demo' };
      if (r.data.course) {
        S.courseId = r.data.course.id || S.courseId;
        S.courseName = r.data.course.name || S.courseName;
      }
      toast('演示账号已登录', 'success');
      updateTopbar();
      loadDashboard();
      return;
    }
  } catch (_) {}
  S.user = { username: 'demo' };
  setToken('demo-token');
  toast('已进入演示模式', 'success');
  updateTopbar();
  loadDashboard();
};

window._logout = function(){
  S.user = null;
  setToken('');
  toast('已退出登录', 'info');
  navTo('settings');
};

async function bootstrap(){
  updateTopbar();
  try {
    const r = await api('/api/app/bootstrap');
    if (r.ok && r.data) {
      if (Array.isArray(r.data.courses)) S.courses = r.data.courses;
      if (r.data.user && r.data.user.authenticated) {
        S.user = r.data.user;
      }
      if (r.data.selected_course) {
        S.courseId = r.data.selected_course.id || S.courseId;
        S.courseName = r.data.selected_course.name || S.courseName;
      }
      if (r.data.config && r.data.config.deepseek_configured === false) {
        toast('请先配置模型服务', 'info');
      }
      navTo(S.token ? 'dashboard' : 'settings');
      updateTopbar();
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
    const d = dashRes.ok ? (dashRes.data || {}) : {};
    const progressItems = (progressRes.ok && progressRes.data && progressRes.data.items) || [];
    const wrongItems = (wrongRes.ok && wrongRes.data && wrongRes.data.items) || [];
    const bookmarks = (bookmarkRes.ok && bookmarkRes.data && bookmarkRes.data.items) || [];
    const sessions = (sessionsRes.ok && sessionsRes.data && sessionsRes.data.sessions) || [];
    const progress = progressItems[0] || {};
    const completedRate = progress.total_lessons ? Math.round((progress.completed_lessons / progress.total_lessons) * 100) : Math.round((progress.completed_rate || 0) * 100);

    let h = '';
    h += '<div class="dashboard-hero card" style="background:linear-gradient(135deg,var(--primary-bg),#fff);border:1px solid #c7d2fe">';
    h += '<div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-start">';
    h += '<div><div style="font-size:12px;color:var(--primary);font-weight:700;letter-spacing:.04em">学习平台总览</div><h2 style="font-size:24px;margin:6px 0 8px;color:var(--gray-900)">欢迎回来，' + esc((S.user && S.user.username) || '同学') + '</h2><p style="font-size:13px;color:var(--gray-500);max-width:720px">从今天开始，继续学习、复盘错题、查看进度，并生成个性化资源。</p></div>';
    h += '<div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="navTo(\'assistant\')">💬 继续学习</button><button class="btn btn-secondary" onclick="navTo(\'generator\')">⚡ 生成资源</button><button class="btn btn-outline" onclick="navTo(\'learning-report\')">📊 学习报告</button></div>';
    h += '</div></div>';

    h += '<div class="grid grid-3" style="margin-top:12px">';
    h += '<div class="card grid-stat"><div class="val" style="color:var(--primary)">' + esc(S.courseName || '未选择') + '</div><div class="lbl">当前课程</div></div>';
    h += '<div class="card grid-stat"><div class="val" style="color:var(--success)">' + wrongItems.length + '</div><div class="lbl">待复盘错题</div></div>';
    h += '<div class="card grid-stat"><div class="val" style="color:var(--warning)">' + bookmarks.length + '</div><div class="lbl">已收藏资源</div></div>';
    h += '</div>';

    h += '<div class="grid grid-2" style="margin-top:12px">';
    h += '<div class="card"><div class="card-header"><h3>📈 学习概览</h3><span class="topbar-badge ok">实时更新</span></div>';
    h += '<div class="lr-summary"><div class="lr-stat"><span class="lr-stat-value">' + completedRate + '%</span><span class="lr-stat-label">课程进度</span></div><div class="lr-stat"><span class="lr-stat-value">' + (progress.next_recommendation ? 1 : 0) + '</span><span class="lr-stat-label">推荐动作</span></div><div class="lr-stat"><span class="lr-stat-value">' + sessions.length + '</span><span class="lr-stat-label">会话数</span></div></div>';
    h += '<div style="margin-top:12px"><div style="display:flex;justify-content:space-between;font-size:12px;color:var(--gray-500);margin-bottom:6px"><span>课程完成度</span><span>' + completedRate + '%</span></div><div class="gen-progress-bar-wrap"><div class="gen-progress-bar-fill" style="width:' + Math.min(completedRate || 0, 100) + '%"></div></div></div>';
    h += '</div>';
    h += '<div class="card"><div class="card-header"><h3>🗂 今日任务</h3></div><div class="course-card" onclick="navTo(\'assistant\')"><h4>1. 继续最近会话</h4></div><div class="course-card" onclick="navTo(\'generator\')"><h4>2. 生成一份资源</h4></div><div class="course-card" onclick="navTo(\'wrong-book\')"><h4>3. 复盘错题</h4></div></div>';
    h += '<div class="card"><div class="card-header"><h3>💬 近期会话</h3></div>' + (sessions.slice(0,3).map(s => '<div class="course-card"><h4>' + esc(s.title || '学习会话') + '</h4><div class="course-meta"><span>消息 ' + (s.message_count || 0) + '</span></div></div>').join('') || '<div class="empty-state"><div class="empty-icon">💬</div><p>还没有会话</p></div>') + '</div>';
    h += '<div class="card"><div class="card-header"><h3>📚 当前课程与资源</h3></div><p style="font-size:15px;font-weight:700">' + esc(d.course ? d.course.name : S.courseName) + '</p><p style="font-size:12px;color:var(--gray-500)">' + esc(d.course ? (d.course.description || '') : '') + '</p></div>';
    h += '<div class="card"><div class="card-header"><h3>⭐ 收藏与提醒</h3></div>' + (bookmarks.slice(0,4).map(b => '<div class="lr-resource-card"><span class="lr-resource-icon">🔖</span><span>' + esc(b.title || b.resource_id) + '</span></div>').join('') || '<div class="empty-state"><div class="empty-icon">🔖</div><p>暂无收藏</p></div>') + '</div>';
    h += '<div class="card"><div class="card-header"><h3>🧠 学习画像</h3></div><div class="empty-state"><div class="empty-icon">🧠</div><p>画像信息将从后端接口逐步展示</p></div></div>';
    h += '</div>';
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
  if (!S.token) { toast('请先登录', 'info'); return; }
  try {
    const r = await api('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ course_id: S.courseId, title: '新的学习会话' })
    });
    if (r.ok && r.data && r.data.session) {
      try {
        await api('/api/analytics/audit', {
          method: 'POST',
          body: JSON.stringify({ action: 'session_create', target_type: 'session', target_id: String(r.data.session.id), detail: r.data.session.title || '新的学习会话' })
        });
      } catch (_) {}
      if (box) box.innerHTML = '<div class="empty-state"><div class="empty-icon">💬</div><p>新的学习会话已创建</p></div>';
      if (sel) sel.value = String(r.data.session.id);
      toast('新会话已创建', 'success');
      await refreshSessionList();
      return;
    }
  } catch (_) {}
  if (box) box.innerHTML = '<div class="empty-state"><div class="empty-icon">💬</div><p>新的学习会话已准备好</p></div>';
  if (sel) sel.value = '';
  toast('新会话已准备好', 'info');
}

function _startCompetition(){
  const landing = document.getElementById('competition-landing');
  const flow = document.getElementById('competition-flow');
  if (landing) landing.style.display = 'none';
  if (flow) flow.style.display = 'grid';
  toast('已进入 AI 学习演示流程', 'success');
  _runCompetitionDemo();
}

async function _runCompetitionDemo(){
  const chat = document.getElementById('comp-chat-messages');
  const citations = document.getElementById('comp-citations');
  const profile = document.getElementById('comp-profile-text');
  const trace = document.getElementById('comp-agent-trace-content');
  const progress = document.getElementById('comp-progress');
  const progressText = document.getElementById('comp-progress-text');
  const tabs = document.getElementById('comp-workspace-tabs');
  const wsEmpty = document.getElementById('comp-ws-empty');

  if (chat) chat.innerHTML = '<div class="comp-empty-state"><div class="empty-icon">🤖</div><p>正在准备演示数据...</p></div>';
  if (progress) progress.style.display = 'inline-flex';
  if (progressText) progressText.textContent = '0%';

  try {
    const r = await api('/api/app/demo-init', { method: 'POST' });
    if (r.ok && r.data) {
      if (r.data.token) setToken(r.data.token);
      if (r.data.user) S.user = r.data.user;
      if (r.data.course) {
        S.courseId = r.data.course.id || S.courseId;
        S.courseName = r.data.course.name || S.courseName;
      }
      updateTopbar();
      if (chat) chat.innerHTML = [
        '<div class="msg-bubble user"><div class="msg-content">什么是过拟合，怎么在学习中避免？</div></div>',
        '<div class="msg-bubble agent"><div class="msg-content">我会先检索课程资料，再给出带引用的解释，并生成可复习的学习成果。</div></div>'
      ].join('');
      if (citations) citations.innerHTML = '<h4>📚 课程依据</h4><p style="font-size:12px;color:var(--gray-400)">答案来自课程资料检索与校验</p>';
      if (profile) profile.textContent = '偏好：思维导图 / 练习题；基础：待分析；当前课程：' + esc(S.courseName || '未选择');
      if (trace) trace.innerHTML = '<p style="font-size:11px">1. 资料检索完成</p><p style="font-size:11px">2. 学习画像更新</p><p style="font-size:11px">3. 答案生成与校验完成</p>';
      if (progressText) progressText.textContent = '80%';
      if (wsEmpty) wsEmpty.style.display = 'none';
      if (tabs) tabs.classList.add('active');
      navTo('dashboard');
      toast('演示流程已准备好', 'success');
    }
  } catch (e) {
    toast('演示流程启动失败，请稍后重试', 'info');
  }
}

function _toggleAdvanced(){
  const group = document.getElementById('nav-advanced-group');
  const title = document.querySelector('#nav-advanced-toggle span:last-child');
  if (!group) return;
  const show = group.style.display === 'none' || !group.style.display;
  group.style.display = show ? 'block' : 'none';
  if (title) title.textContent = show ? '▴' : '▾';
}

async function loadKnowledgeBase(){
  const el = document.getElementById('page-knowledge');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>课程资料库</h3><button class="btn btn-sm btn-outline" onclick="loadKnowledgeBase()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 正在加载课程资料...</div></div>';
  try {
    const r = await api('/api/app/bootstrap');
    const courses = (r.ok && r.data && Array.isArray(r.data.courses)) ? r.data.courses : [];
    const current = courses.find(c => String(c.id) === String(S.courseId)) || courses[0] || null;
    const courseName = current ? current.name : S.courseName;
    const courseDesc = current ? (current.description || '暂无描述') : '暂无课程资料';
    const chunks = current ? (current.chunks_count || 0) : 0;
    el.innerHTML = '<div class="card"><div class="card-header"><h3>课程资料库</h3><button class="btn btn-sm btn-outline" onclick="loadKnowledgeBase()">🔄 刷新</button></div><div class="course-card"><h4>📘 ' + esc(courseName) + '</h4><div class="course-meta"><span>' + esc(courseDesc) + '</span><span>资料块 ' + chunks + '</span></div></div><div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="navTo(\'assistant\')">去提问</button><button class="btn btn-outline" onclick="navTo(\'courses\')">切换课程</button><button class="btn btn-outline" onclick="navTo(\'resource-center\')">查看资源</button></div><div style="margin-top:12px" class="empty-state"><div class="empty-icon">🧠</div><p>' + (chunks > 0 ? '知识库已接入，可继续提问获取引用答案' : '当前课程暂无知识库，建议先导入课程资料') + '</p></div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">课程资料库加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function loadLearningPath(){
  const el = document.getElementById('page-learning-path');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>学习计划</h3><button class="btn btn-sm btn-outline" onclick="loadLearningPath()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 正在生成学习计划...</div></div>';
  try {
    const r = await api('/api/analytics/progress');
    const progress = (r.ok && r.data.items && r.data.items[0]) || {};
    const weakPoints = Array.isArray(progress.weak_points) ? progress.weak_points : [];
    const steps = [
      '先完成一次提问，确认当前知识点理解情况',
      '进入资源中心，下载或收藏相关资料',
      '完成一轮测验，记录错题',
      '在错题本中追问并加入复习计划',
      '回到学习报告查看完成率与薄弱点'
    ];
    el.innerHTML = '<div class="card"><div class="card-header"><h3>学习计划</h3><button class="btn btn-sm btn-outline" onclick="loadLearningPath()">🔄 刷新</button></div><div class="course-card"><h4>🗺️ 当前学习建议</h4><div class="course-meta"><span>' + esc(progress.next_recommendation || '暂无个性化推荐，先完成一次问答或测验') + '</span></div></div><div style="margin-top:12px">' + steps.map((s, i) => '<div class="course-card"><h4>' + (i + 1) + '. ' + esc(s) + '</h4></div>').join('') + '</div>' + (weakPoints.length ? '<div style="margin-top:12px" class="lr-section"><div class="lr-section-title">薄弱知识点</div><div class="lr-chips">' + weakPoints.map(w => '<span class="lr-chip">' + esc(w) + '</span>').join('') + '</div></div>' : '<div class="empty-state" style="margin-top:12px"><div class="empty-icon">🗺️</div><p>还没有足够的学习数据生成个性化计划</p></div>') + '<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="navTo(\'assistant\')">开始学习</button><button class="btn btn-outline" onclick="navTo(\'wrong-book\')">复盘错题</button><button class="btn btn-outline" onclick="navTo(\'learning-report\')">查看报告</button></div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">学习计划加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

function loadAssistant(){
  const el = document.getElementById('page-assistant');
  if (!el) return;
  el.innerHTML = '<div class="assistant-layout"><div class="chat-panel"><div class="session-bar"><select id="session-select" onchange="onSessionSelect(this.value)"><option value="">— 选择历史会话 —</option></select><button type="button" class="btn btn-sm btn-outline" onclick="createNewSession()">+ 新会话</button></div><div class="chat-messages" id="chat-messages"><div class="empty-state"><div class="empty-icon">💬</div><p>在这里发起提问</p></div></div><div class="chat-input-area"><div class="chat-input-row"><textarea id="chat-input" placeholder="输入你想学习的问题，例如：过拟合和正则化有什么关系？" rows="2"></textarea><button class="btn btn-primary" onclick="sendQuestion()">发送</button></div></div></div><div class="artifacts-panel"><div class="artifacts-tabs"><div class="artifacts-tab active">答案与引用</div></div><div class="artifacts-content"><div class="tab-panel active"><div class="empty-state"><div class="empty-icon">📖</div><p>提问后显示答案、引用、思维导图与测验</p></div></div></div></div><div class="citations-panel"><h4>课程依据</h4><p style="font-size:12px;color:var(--gray-400)">提问后显示引用来源</p></div></div>';
  refreshSessionList();
}

async function loadCourses(){
  const el = document.getElementById('page-courses');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>课程中心</h3></div><div class="loading-block"><span class="spinner"></span> 加载课程中...</div></div>';
  try {
    const r = await api('/api/app/bootstrap');
    const courses = (r.ok && r.data && Array.isArray(r.data.courses)) ? r.data.courses : S.courses;
    if (Array.isArray(courses)) S.courses = courses;
    if (!courses || !courses.length) {
      el.innerHTML = '<div class="card"><div class="card-header"><h3>课程中心</h3></div><div class="empty-state"><div class="empty-icon">📚</div><p>暂无课程</p><p style="font-size:11px;color:var(--gray-400)">后端课程列表加载后会展示在这里</p></div></div>';
      return;
    }
    el.innerHTML = '<div class="card"><div class="card-header"><h3>课程中心</h3><button class="btn btn-sm btn-outline" onclick="loadCourses()">🔄 刷新</button></div>' + courses.map(c => '<div class="course-card'+((c.id===S.courseId)?' selected':'')+'" onclick="S.courseId='+c.id+';S.courseName=\''+esc(c.name||'')+'\';updateTopbar();loadDashboard();loadCourses();"><h4>📘 '+esc(c.name||'未命名课程')+'</h4><div class="course-meta"><span>'+esc(c.description||'暂无描述')+'</span></div></div>').join('') + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">课程中心加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

function loadGenerator(){
  const el = document.getElementById('page-generator');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>资源生成中心</h3><button class="btn btn-sm btn-outline" onclick="loadGenerator()">🔄 刷新</button></div><div class="grid grid-2"><div class="course-card" onclick="navTo(\'assistant\')"><h4>🧠 思维导图</h4><div class="course-meta"><span>进入会话中心，围绕问题生成知识结构</span></div></div><div class="course-card" onclick="navTo(\'assistant\')"><h4>📄 讲义文档</h4><div class="course-meta"><span>进入会话中心，生成课程讲解文本</span></div></div><div class="course-card" onclick="navTo(\'assistant\')"><h4>📝 测验题库</h4><div class="course-meta"><span>进入会话中心，生成练习与错题复盘</span></div></div><div class="course-card" onclick="navTo(\'assistant\')"><h4>📊 PPT 课件</h4><div class="course-meta"><span>进入会话中心，生成可下载演示课件</span></div></div></div><div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary" onclick="navTo(\'assistant\')">从问题生成资源</button><button class="btn btn-outline" onclick="navTo(\'resource-center\')">查看已生成资源</button></div></div>';
}

async function bookmarkResource(resourceId, title){
  try {
    const r = await api('/api/analytics/bookmarks', {
      method: 'POST',
      body: JSON.stringify({ resource_id: resourceId, title: title || '' })
    });
    if (r.ok) {
      try {
        await api('/api/analytics/audit', {
          method: 'POST',
          body: JSON.stringify({ action: 'bookmark_create', target_type: 'resource', target_id: String(resourceId), detail: title || '' })
        });
      } catch (_) {}
      toast('已收藏资源', 'success');
      return true;
    }
  } catch (_) {}
  toast('收藏暂时失败，请稍后重试', 'info');
  return false;
}

async function shareResource(resourceId, title){
  const url = S.apiBase.replace(/\/$/,'') + '/api/resources/download/' + encodeURIComponent(resourceId);
  const text = title ? (title + '：' + url) : url;
  try {
    await api('/api/analytics/audit', {
      method: 'POST',
      body: JSON.stringify({ action: 'resource_share', target_type: 'resource', target_id: String(resourceId), detail: title || '' })
    });
  } catch (_) {}
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function(){ toast('分享链接已复制', 'success'); }).catch(function(){ toast('无法复制链接，请手动复制', 'info'); });
  } else {
    toast('分享链接：' + url, 'info');
  }
}

async function loadResourceCenter(){
  const el = document.getElementById('page-resource-center');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>资源中心</h3></div><div class="loading-block"><span class="spinner"></span> 加载资源中...</div></div>';
  try {
    const [filesRes, sessionsRes, bookmarksRes] = await Promise.all([api('/api/resources/generated'), api('/api/sessions'), api('/api/analytics/bookmarks')]);
    const files = filesRes.ok ? (filesRes.data.files || []) : [];
    const sessions = sessionsRes.ok ? (sessionsRes.data.sessions || []) : [];
    const bookmarks = bookmarksRes.ok ? (bookmarksRes.data.items || []) : [];
    const fileCards = files.length ? files.map(f => '<div class="course-card"><h4>📄 ' + esc(f.original_filename || f.filename || '资源文件') + '</h4><div class="course-meta"><span>大小 ' + Math.round((f.size||0)/1024) + 'KB</span><span>' + esc(f.content_type || 'file') + '</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><a class="btn btn-sm btn-primary" href="' + S.apiBase + '/api/resources/download/' + esc(f.resource_id) + '" target="_blank">下载</a><button class="btn btn-sm btn-outline" onclick="bookmarkResource(\'' + esc(f.resource_id) + '\', \'' + esc(f.original_filename || f.filename || '资源文件') + '\')">收藏</button><button class="btn btn-sm btn-outline" onclick="shareResource(\'' + esc(f.resource_id) + '\', \'' + esc(f.original_filename || f.filename || '资源文件') + '\')">分享</button></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">📦</div><p>暂无生成资源</p><p style="font-size:11px;color:var(--gray-400)">生成思维导图、讲义、测验或 PPT 后会出现在这里</p><div style="margin-top:10px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'generator\')">去生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">先去提问</button></div></div>';
    const bookmarkCards = bookmarks.length ? bookmarks.map(b => '<div class="course-card"><h4>🔖 ' + esc(b.title || b.resource_id || '收藏资源') + '</h4><div class="course-meta"><span>' + esc(b.resource_id || '') + '</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">查看资源</button><button class="btn btn-sm btn-outline" onclick="shareResource(\'' + esc(b.resource_id || '') + '\', \'' + esc(b.title || '收藏资源') + '\')">分享</button></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🔖</div><p>暂无收藏</p><p style="font-size:11px;color:var(--gray-400)">收藏后会在这里集中显示</p></div>';
    const sessionCards = sessions.length ? sessions.slice(0,5).map(s => '<div class="course-card"><h4>💬 ' + esc(s.title || '学习会话') + '</h4><div class="course-meta"><span>消息 ' + (s.message_count || 0) + '</span></div><div style="margin-top:8px"><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">查看会话</button></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">💬</div><p>暂无会话</p><p style="font-size:11px;color:var(--gray-400)">先去提问，系统会在这里保存学习记录</p><div style="margin-top:10px"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">去提问</button></div></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>资源中心</h3><button class="btn btn-sm btn-outline" onclick="loadResourceCenter()">🔄 刷新</button></div><div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px"><button class="btn btn-sm btn-primary" onclick="navTo(\'generator\')">⚡ 去生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">💬 去提问</button><button class="btn btn-sm btn-outline" onclick="navTo(\'learning-report\')">📊 看学习报告</button></div>' + fileCards + '</div><div class="card"><div class="card-header"><h3>收藏资源</h3></div>' + bookmarkCards + '</div><div class="card"><div class="card-header"><h3>最近会话</h3></div>' + sessionCards + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">资源加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function loadWrongBook(){
  const el = document.getElementById('page-wrong-book');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>错题本</h3><button class="btn btn-sm btn-outline" onclick="loadWrongBook()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 加载中...</div></div>';
  try {
    const r = await api('/api/analytics/wrong-book');
    const items = r.ok ? (r.data.items || []) : [];
    const body = items.length ? items.map(it => '<div class="course-card"><h4>🧯 ' + esc(it.knowledge_point || it.topic || '未命名知识点') + '</h4><div class="course-meta"><span>' + esc(it.question_text || '') + '</span></div><div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-outline" onclick="navTo(\'assistant\')">去追问</button><button class="btn btn-sm btn-outline" onclick="toast(\'后续可加入错题解析和收藏\', \'info\')">收藏</button><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">生成复习资源</button><button class="btn btn-sm btn-outline" onclick="joinReviewPlan(\'' + esc(it.knowledge_point || it.topic || '') + '\')">加入复习计划</button></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🧯</div><p>暂无错题</p><p style="font-size:11px;color:var(--gray-400)">做完测验后，错题会自动出现在这里</p><div style="margin-top:10px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">去提问</button><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">去生成资源</button><button class="btn btn-sm btn-outline" onclick="joinReviewPlan(\'\')">加入复习计划</button></div></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>错题本</h3><button class="btn btn-sm btn-outline" onclick="loadWrongBook()">🔄 刷新</button></div>' + body + '</div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">错题本加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function loadLearningReportPage(){
  const el = document.getElementById('lr-standalone');
  if (!el) return;
  el.innerHTML = '<div class="loading-block"><span class="spinner"></span> 加载中...</div>';
  try {
    const [progressRes, wrongRes, bookmarkRes, auditRes] = await Promise.all([
      api('/api/analytics/progress'),
      api('/api/analytics/wrong-book'),
      api('/api/analytics/bookmarks'),
      api('/api/analytics/audit?limit=20')
    ]);
    const progress = (progressRes.ok && progressRes.data.items && progressRes.data.items[0]) || {};
    const wrongItems = (wrongRes.ok && wrongRes.data.items) || [];
    const bookmarks = (bookmarkRes.ok && bookmarkRes.data.items) || [];
    const audits = (auditRes.ok && auditRes.data.items) || [];
    const rate = progress.total_lessons ? Math.round((progress.completed_lessons / progress.total_lessons) * 100) : Math.round((progress.completed_rate || 0) * 100);
    const weakPoints = Array.isArray(progress.weak_points) ? progress.weak_points : [];
    const activityCards = audits.length ? audits.slice(0,5).map(a => '<div class="course-card"><h4>🧾 ' + esc(a.action || '行为记录') + '</h4><div class="course-meta"><span>' + esc(a.detail || '') + '</span></div></div>').join('') : '<div class="empty-state"><div class="empty-icon">🧾</div><p>暂无行为记录</p></div>';
    el.innerHTML = '<div class="card"><div class="card-header"><h3>学习报告</h3><button class="btn btn-sm btn-outline" onclick="loadLearningReportPage()">🔄 刷新</button></div><div class="lr-summary"><div class="lr-stat"><span class="lr-stat-value">' + rate + '%</span><span class="lr-stat-label">完成率</span></div><div class="lr-stat"><span class="lr-stat-value">' + wrongItems.length + '</span><span class="lr-stat-label">错题数</span></div><div class="lr-stat"><span class="lr-stat-value">' + bookmarks.length + '</span><span class="lr-stat-label">收藏数</span></div></div><div class="lr-section"><div class="lr-section-title">学习建议</div><div class="course-card"><h4>' + esc(progress.next_recommendation || '先完成一次问答或测验，系统会给出下一步推荐') + '</h4></div><div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-sm btn-primary" onclick="navTo(\'assistant\')">继续提问</button><button class="btn btn-sm btn-outline" onclick="navTo(\'generator\')">生成资源</button><button class="btn btn-sm btn-outline" onclick="navTo(\'wrong-book\')">复盘错题</button><button class="btn btn-sm btn-outline" onclick="navTo(\'resource-center\')">查看收藏资源</button></div></div>' + (weakPoints.length ? '<div class="lr-section"><div class="lr-section-title">薄弱知识点</div><div class="lr-chips">' + weakPoints.map(w => '<span class="lr-chip">' + esc(w) + '</span>').join('') + '</div></div>' : '') + '<div class="lr-section"><div class="lr-section-title">近期行为</div>' + activityCards + '</div><div class="lr-section"><div class="lr-section-title">学习目标</div><div class="course-card"><h4>建立“提问 - 生成 - 测验 - 复盘 - 推荐”的学习闭环</h4></div></div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">学习报告加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function joinReviewPlan(topic){
  try {
    await api('/api/analytics/audit', {
      method: 'POST',
      body: JSON.stringify({ action: 'review_plan_join', target_type: 'topic', target_id: topic || '', detail: topic || '错题复习' })
    });
  } catch (_) {}
  toast('已加入复习计划', 'success');
}

async function loadSettings(){
  const el = document.getElementById('page-settings');
  if (!el) return;
  el.innerHTML = '<div class="card"><div class="card-header"><h3>账户与设置</h3><button class="btn btn-sm btn-outline" onclick="loadSettings()">🔄 刷新</button></div><div class="loading-block"><span class="spinner"></span> 加载配置中...</div></div>';
  try {
    const r = await api('/api/settings/status');
    const d = (r.ok && r.data) ? r.data : {};
    el.innerHTML = '<div class="grid grid-2"><div class="card"><div class="card-header"><h3>账户与角色</h3></div><div class="form-group"><label>当前用户</label><input readonly value="' + esc((S.user && S.user.username) || '未登录') + '"></div><div class="form-group"><label>当前课程</label><input readonly value="' + esc(S.courseName || '未选择') + '"></div><button class="btn btn-primary" onclick="_loginDemo()">演示登录</button> <button class="btn btn-outline" onclick="_logout()">退出</button></div><div class="card"><div class="card-header"><h3>系统状态</h3></div><div class="lr-section"><div class="lr-section-title">模型与服务</div><div class="course-card"><h4>主模型：' + esc(d.llm_model || '未知') + '</h4><div class="course-meta"><span>提供方：' + esc(d.llm_provider || '未知') + '</span></div></div><div class="course-card"><h4>DeepSeek：' + (d.deepseek_configured ? '已配置' : '未配置') + '</h4><div class="course-meta"><span>Fallback：' + (d.fallback_available ? '可用' : '不可用') + '</span></div></div><div class="course-card"><h4>语义索引：' + (d.embedding_is_mock ? 'Mock' : '已启用') + '</h4><div class="course-meta"><span>Chroma / 检索链路状态将逐步接入</span></div></div></div></div></div>';
  } catch (e) {
    el.innerHTML = '<div class="error-card"><div class="err-title">设置加载失败</div><div class="err-detail">' + esc(e.message || '未知错误') + '</div></div>';
  }
}

async function sendQuestion(){
  const input = document.getElementById('chat-input');
  const msg = input ? input.value.trim() : '';
  if (!msg) return toast('请输入问题', 'info');
  const box = document.getElementById('chat-messages');
  if (box) box.innerHTML += '<div class="msg-bubble user"><div class="msg-content">' + esc(msg) + '</div></div>';
  if (input) input.value = '';

  const typingId = 'typing-' + Date.now();
  if (box) box.innerHTML += '<div class="msg-bubble agent" id="' + typingId + '"><div class="msg-content">正在检索课程资料并生成回答...</div></div>';

  try {
    const payload = { course_id: S.courseId, question: msg, history: [], top_k: 5, session_id: null };
    const r = await api('/api/app/ask', { method: 'POST', body: JSON.stringify(payload) });
    const answer = (r.ok && r.data && (r.data.answer || r.data.content || r.data.result))
      ? (r.data.answer || r.data.content || r.data.result)
      : null;
    const refs = (r.ok && r.data && (r.data.refs || r.data.citations)) ? (r.data.refs || r.data.citations) : [];
    const el = document.getElementById(typingId);
    if (el) {
      el.innerHTML = '<div class="msg-content">' + esc(answer || '已收到问题，当前环境暂未返回正式答案。') + '</div>' + (refs.length ? '<div class="msg-citations">📚 ' + refs.map(x => esc(typeof x === 'string' ? x : (x.source || x.chunk_id || '引用'))).join(' · ') + '</div>' : '');
    }
    if (box) box.scrollTop = box.scrollHeight;
    return;
  } catch (e) {
    const el = document.getElementById(typingId);
    if (el) {
      el.innerHTML = '<div class="msg-content">' + esc('我已经收到你的问题。当前环境下问答服务暂未完全接通，但你可以继续围绕课程资料提问。') + '</div>';
    }
    toast('问答服务暂时不可用，已显示降级回复', 'info');
  }
}

window.navTo = navTo;
window.loadDashboard = loadDashboard;
window.loadResourceCenter = loadResourceCenter;
window.loadLearningReportPage = loadLearningReportPage;
window.loadWrongBook = loadWrongBook;
window.loadSettings = loadSettings;
window.loadCourses = loadCourses;
window.loadAssistant = loadAssistant;
window.loadGenerator = loadGenerator;
window.createNewSession = createNewSession;
window.sendQuestion = sendQuestion;
window._sendQuestion = sendQuestion;
window._quickGenerate = function(type){
  navTo('generator');
  toast('已切换到资源生成中心，请选择：' + type, 'info');
};
window._avatarSpeakAnswer = function(){
  navTo('assistant');
  toast('已切回会话中心，语音讲解功能稍后开放', 'info');
};
window._avatarSpeakPath = function(){
  navTo('learning-path');
  toast('已切换到学习计划页，便于讲解学习路径', 'info');
};
window._avatarStop = function(){ toast('已停止讲解', 'info'); };
window._runFullDemo = function(){
  _startCompetition();
};

function startCompetitionView(){
  _startCompetition();
}

window.addEventListener('DOMContentLoaded', bootstrap);
