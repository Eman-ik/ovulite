const fs = require('fs');
const p = 'd:/Ovulite new/frontend/src/pages/ModelPerformancePage.tsx';
let s = fs.readFileSync(p, 'utf8');
s = s.replace(/import \{ Badge \} from "@\/components\/ui\/badge";\r?\n/, '');
fs.writeFileSync(p, s, 'utf8');
console.log('patched ModelPerformancePage');
