const PREVIEW_CONFIG = {
  'FREE-7DAY': '完整免費產品已開放：Day 1–7、Hint Ladder、解析與五能力 checkpoint 都可直接使用。',
  'P1-30DAY': '將公開封面、目錄、Day 1 與一個中段完整任務。',
  'P2-DEBUG': '將公開 2 個完整 Bug Case，含錯誤版、最小測資與修正版。',
  'P3-CONCEPT': '將公開 2 組程式識讀題與完整錯誤選項解析。',
  'P3-INTERMEDIATE': '將公開 2 題原創實作題、Hint Ladder 與完整解析。',
  'P3-ADVANCED': '將公開 1 題進階實作與一份 Optimization Lab 樣張。',
  'P4-SPRINT': '將公開 Day 1、Day 7 與考前檢查表樣張。',
  'P4-MOCK': '將公開題型樣張與 1 題完整解析；不公開整份模擬試卷。',
  'P5-POSTEXAM': '將公開考後復盤表與一個 7 日修復計畫範例。',
  'P6-GITHUB': '將公開 README 模板、repository 結構與完成品範例頁。',
  'P7-PORTFOLIO': '將公開證據整理頁、反思模板與一份完成樣張。',
  'P8-AI-CODING': '將公開需求拆解、Git 工作流與專題交付樣張。',
};

const PREVIEW_LINKS = {
  'FREE-7DAY': './free-7day.html',
  // 'P1-30DAY': './previews/p1-30day.html',
};

function makePreview(code, description) {
  const box = document.createElement('div');
  box.className = 'product-preview';
  box.dataset.previewFor = code;

  const copy = document.createElement('div');
  copy.className = 'product-preview-copy';
  const label = document.createElement('span');
  label.className = 'product-preview-label';
  label.textContent = code === 'FREE-7DAY' ? '完整免費產品' : '免費預覽';
  const text = document.createElement('p');
  text.textContent = description;
  copy.append(label, text);

  const href = PREVIEW_LINKS[code];
  let action;
  if (href) {
    action = document.createElement('a');
    action.className = 'product-preview-action';
    action.href = href;
    action.textContent = code === 'FREE-7DAY' ? '開始 Day 1 →' : '查看預覽 →';
  } else {
    action = document.createElement('span');
    action.className = 'product-preview-action is-pending';
    action.textContent = '預覽準備中';
    action.setAttribute('aria-label', `${code} 預覽準備中`);
  }

  box.append(copy, action);
  return box;
}

function activateFreeSevenDay(card) {
  const status = card.querySelector('.product-status');
  if (status) {
    status.textContent = '已開放';
    status.classList.add('is-available');
  }
  const pending = card.querySelector('.product-disabled');
  if (pending) {
    const action = document.createElement('a');
    action.className = 'product-live-action';
    action.href = './free-7day.html';
    action.textContent = '開始免費訓練 →';
    pending.replaceWith(action);
  }
}

export function initProductLibrary() {
  const shell = document.querySelector('.product-library-shell');
  if (!shell) return;

  const hero = shell.querySelector('.library-hero h1');
  if (hero) hero.textContent = '更短的進步路徑。';

  const eyebrow = shell.querySelector('.library-hero .eyebrow');
  if (eyebrow) eyebrow.textContent = 'Product Library · 不是更多教材';

  const catalogStatus = shell.querySelector('.library-status-note strong');
  if (catalogStatus) catalogStatus.textContent = 'FREE-7DAY 已開放 · 其餘內容準備中';

  for (const card of shell.querySelectorAll('.product-card')) {
    const code = card.querySelector('.product-code')?.textContent?.trim();
    if (!code) continue;
    if (code === 'FREE-7DAY') activateFreeSevenDay(card);
    if (card.querySelector('.product-preview') || !PREVIEW_CONFIG[code]) continue;
    const foot = card.querySelector('.product-card-foot');
    const preview = makePreview(code, PREVIEW_CONFIG[code]);
    if (foot) foot.before(preview);
    else card.append(preview);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initProductLibrary, { once: true });
} else {
  initProductLibrary();
}
