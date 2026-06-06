/** @type {import('@playwright/test').PlaywrightTestConfig} */
module.exports = {
  testDir: '.',
  timeout: 60000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
  reporter: [['list'], ['html', { open: 'never' }]],
};
