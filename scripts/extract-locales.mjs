// Extract public UI wording, never environment files, credentials or conversations.
import ts from '../apps/web/node_modules/typescript/lib/typescript.js';
import fs from 'node:fs';
import path from 'node:path';
const root = process.cwd();
const base = path.join(root, 'apps/orchestrator/src/locales');
fs.mkdirSync(base, { recursive: true });
const keys = new Set();
const collect = value => {
  const text = value.replace(/\s+/g, ' ').trim();
  if (text && /[a-zA-Z]/.test(text) && !text.includes('https://') && !text.includes('SELECT ') && !text.includes('CREATE ') && text.length < 1600) keys.add(text);
};
for (const app of ['web', 'moderator-dashboard']) {
  const source = ts.createSourceFile('page.tsx', fs.readFileSync(`apps/${app}/app/page.tsx`, 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const walk = node => {
    if (ts.isJsxText(node)) collect(node.text);
    if (ts.isStringLiteral(node)) {
      const parent = node.parent;
      if (ts.isJsxAttribute(parent)) {
        if (['title', 'aria-label', 'placeholder'].includes(parent.name.text)) collect(node.text);
      } else if (!ts.isImportDeclaration(parent) && (node.text.includes(' ') || /^[A-Z]/.test(node.text) || ['queued','in_progress','resolved','routine','critical','normal','official','community','unverified','verified','stale','phone','website','email','in-person','sms'].includes(node.text))) collect(node.text);
    }
    ts.forEachChild(node, walk);
  };
  walk(source);
}
const french = ts.createSourceFile('localization.tsx', fs.readFileSync('apps/web/app/localization.tsx', 'utf8'), ts.ScriptTarget.Latest, true);
let existing = {};
const visit = node => {
  if (ts.isVariableDeclaration(node) && node.name.getText() === 'french' && ts.isObjectLiteralExpression(node.initializer)) {
    for (const p of node.initializer.properties) if (ts.isPropertyAssignment(p) && ts.isStringLiteral(p.name) && ts.isStringLiteral(p.initializer)) { existing[p.name.text] = p.initializer.text; collect(p.name.text); }
  }
  ts.forEachChild(node, visit);
};
visit(french);
if (Object.keys(existing).length) fs.writeFileSync(path.join(base, 'fr.json'), JSON.stringify(existing, null, 2));
const runtime = JSON.parse(fs.readFileSync(path.join(base, 'runtime.json'), 'utf8'));
for (const text of Object.values(runtime)) collect(text);
for (const row of JSON.parse(fs.readFileSync('apps/orchestrator/src/extra_referrals.json', 'utf8'))) for (const key of ['title','notes','hours']) collect(row[key]);
for (const text of ['Some text remains in English. Full translation is unavailable right now.', 'Translation wording needs native-speaker review.', 'Preparing translations…', 'Language', 'Sources:', 'Contact checked', 'Last checked', 'Needs re-checking before you rely on it.', 'Checked', 'Visit', 'Human support request', 'Response time is not guaranteed.', 'organisations | Confirm availability directly. Listings do not imply a partnership.', 'Multilingual support', 'Choose your language for the interface and new AI replies.', 'Automatic translation can make mistakes. Verify important information with the service.', 'Original text', 'Translate reply', 'Translation unavailable. The original reply is shown.', 'Reviewed source text (original language):']) collect(text);
const previous = fs.existsSync(path.join(base, 'en.json')) ? JSON.parse(fs.readFileSync(path.join(base, 'en.json'), 'utf8')) : {};
const combined = {...previous,...Object.fromEntries([...keys].sort().map(k=>[k,k]))};
for (const technical of ['.modal button, .modal a, .modal input','Content-Type','DELETE','GET','PATCH','POST','PUT','data:','event: expired','nav-item active','use client']) delete combined[technical];
fs.writeFileSync(path.join(base, 'en.json'), JSON.stringify(combined, null, 2));
console.log(`${keys.size} public translation keys extracted`);
