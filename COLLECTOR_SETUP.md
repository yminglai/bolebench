# 后台收集器：5 分钟设置（Google Apps Script → Google Sheet）

1. 开 https://script.google.com → New project
2. 粘贴以下代码（整个替换 Code.gs）：

```javascript
function doPost(e) {
  const p = JSON.parse(e.postData.contents);
  const ss = SpreadsheetApp.openById(SHEET_ID());
  const sh = ss.getSheetByName('responses') || ss.insertSheet('responses');
  if (sh.getLastRow() === 0) {
    sh.appendRow(['timestamp','who','tier','score','version','item_id','choice','conf','sec','flipped','both_below_baseline']);
  }
  const t = new Date();
  for (const r of p.responses) {
    sh.appendRow([t, p.who || 'anon', p.tier || '', p.score, p.v, r.id, r.choice, r.conf, r.sec, r.flipped, r.bb]);
  }
  return ContentService.createTextOutput('ok');
}
function SHEET_ID() { return 'PASTE_YOUR_SHEET_ID'; }
```

3. 建一个空白 Google Sheet，把 URL 里 /d/ 后面那串 ID 填进 SHEET_ID
4. Deploy → New deployment → type: Web app → Execute as: **Me** → Who has access: **Anyone** → Deploy
5. 复制生成的 Web app URL（https://script.google.com/macros/s/.../exec），发给我
6. 我把 URL 填进 6 个 quiz 页面的 COLLECT_URL 常量并重新推送——之后每份完成的问卷自动落表，一行一题

在此之前网站照常可用：提交走 CSV 下载（现有兜底），不阻塞发放。
