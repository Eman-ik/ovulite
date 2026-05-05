const fs = require('fs');
const p = 'd:/Ovulite new/frontend/src/pages/ReportsExportPage.tsx';
let s = fs.readFileSync(p, 'utf8');
s = s.replace(/import\s+\{\s*Select\s*\}\s+from\s+"@\/components\/ui\/select";\r?\n/, '');
s = s.replace(/import\s+\{[\s\S]*?\}\s+from\s+"lucide-react";/, 'import { Download, FileText } from "lucide-react";');
fs.writeFileSync(p, s, 'utf8');
console.log('patched ReportsExportPage');
