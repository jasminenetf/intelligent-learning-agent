// @ts-check
const { test, expect } = require('@playwright/test');

const API = process.env.E2E_API_BASE || 'http://127.0.0.1:8010';

async function ensureLoggedIn(page) {
  await page.goto('/');
  await page.waitForTimeout(800);
  const user = 'e2e_' + Date.now();
  const password = 'e2e_pass_123';
  await page.request.post(API + '/api/auth/register', {
    data: { username: user, password },
  });
  const login = await page.request.post(API + '/api/auth/login', {
    data: { username: user, password },
  });
  expect(login.ok()).toBeTruthy();
  const body = await login.json();
  const token = body.access_token;
  await page.evaluate((t) => {
    localStorage.setItem('hermes_token', t);
    window.location.reload();
  }, token);
  await page.waitForTimeout(1200);
}

test('homepage loads without JS errors', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('/');
  await expect(page.locator('.logo-text')).toContainText('智学工坊');
  expect(errors.join(' ')).not.toMatch(/undefined|\[object Object\]/);
});

test('settings page shows LLM config', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('settings'));
  await page.waitForTimeout(600);
  await expect(page.locator('#llm-provider')).toBeVisible();
  await expect(page.locator('text=推理引擎配置')).toBeVisible();
});

test('assistant demo question renders agent bubble', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('assistant'));
  await page.waitForTimeout(500);
  const input = page.locator('#chat-input');
  await input.fill('我不懂函数极限，讲清定义、常见误区，并给一个例题。我基础比较差。');
  await page.locator('button:has-text("发送")').click();
  await page.waitForTimeout(10000);
  const agentBubble = page.locator('#chat-messages .msg-bubble.agent').last();
  await expect(agentBubble).toBeVisible();
  const text = await agentBubble.innerText();
  expect(text.length).toBeGreaterThan(5);
  expect(text).not.toContain('Failed to fetch');
  expect(text).not.toContain('undefined');
});

test('citations panel shows content or empty state', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('assistant'));
  await page.waitForTimeout(500);
  await page.locator('#chat-input').fill('函数极限和左右极限有什么关系？');
  await page.locator('button:has-text("发送")').click();
  await page.waitForTimeout(10000);
  const panel = page.locator('#citations-panel');
  await expect(panel).toContainText('课程依据');
  const panelText = await panel.innerText();
  expect(
    panelText.includes('课程片段') ||
    panelText.includes('未检索到课程片段') ||
    panelText.includes('chunk')
  ).toBeTruthy();
});

test('agent collaboration panel visible after ask', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('assistant'));
  await page.waitForTimeout(500);
  await page.locator('#chat-input').fill('请用高数上教材解释无穷小和函数极限的关系');
  await page.locator('button:has-text("发送")').click();
  const viz = page.locator('#agent-viz');
  await expect(viz).toContainText('学习助手协作');
  await expect(viz).toContainText(/TutorAgent|InformerAgent|VerifierAgent|协作轨迹/, { timeout: 20000 });
});

test('one-click demo fills question and triggers flow', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('assistant'));
  await page.waitForTimeout(500);
  await page.locator('button:has-text("一键演示")').click();
  await page.waitForTimeout(12000);
  await expect(page.locator('#chat-messages .msg-bubble.user').last()).toContainText('函数极限');
  const agentBubble = page.locator('#chat-messages .msg-bubble.agent').last();
  await expect(agentBubble).toBeVisible();
});

test('unauthenticated bootstrap opens assistant or settings', async ({ page }) => {
  await page.goto('/');
  await page.waitForTimeout(1500);
  const assistantActive = await page.locator('#page-assistant').evaluate(el => el.classList.contains('active'));
  const settingsActive = await page.locator('#page-settings').evaluate(el => el.classList.contains('active'));
  expect(assistantActive || settingsActive).toBeTruthy();
});

test('mindmap quick button updates artifact panel', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('assistant'));
  await page.waitForTimeout(800);
  await page.locator('#chat-input').fill('函数极限的定义');
  await page.locator('button:has-text("生成思维导图")').click();
  await page.waitForTimeout(20000);
  const panel = page.locator('#artifact-mindmap');
  await expect(panel).toBeVisible();
  const panelText = await panel.innerText();
  expect(panelText).not.toContain('Failed to fetch');
  expect(panelText).not.toContain('undefined');
  const hasContent =
    (await page.locator('#artifact-mindmap .mermaid').count()) > 0 ||
    (await page.locator('#artifact-mindmap #mermaid-host').count()) > 0 ||
    panelText.includes('知识结构') ||
    (!panelText.includes('生成失败') && !panelText.includes('提问后生成或点击快捷按钮'));
  expect(hasContent).toBeTruthy();
});

test('knowledge base page loads upload or permission hint', async ({ page }) => {
  await ensureLoggedIn(page);
  await page.evaluate(() => window.navTo('knowledge'));
  await page.waitForTimeout(800);
  const upload = page.locator('#kb-upload-input');
  const permission = page.locator('text=教师或管理员');
  const uploadVisible = await upload.isVisible().catch(() => false);
  const permissionVisible = await permission.isVisible().catch(() => false);
  expect(uploadVisible || permissionVisible).toBeTruthy();
});
