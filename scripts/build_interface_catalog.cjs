// Build-time allowlist: code-owned UI literals, not runtime/page/user text.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ts=require('../frontend/node_modules/typescript');
const strings=new Set();
const add=s=>{if(s.trim()&&/[A-Za-z]/.test(s))strings.add(s.trim());};
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)]);}
for(const file of walk('frontend/src').filter(f=>f.endsWith('.tsx')&&!f.endsWith('InterfaceLanguage.tsx'))){
 const ast=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 function visit(n){
  if(ts.isCallExpression(n)&&['ui','setMessage','setError','setNotice','Error','useState','setCustomValidity'].includes(n.expression.getText(ast))){
   function literals(x){if(ts.isStringLiteral(x)||ts.isNoSubstitutionTemplateLiteral(x))add(x.text);else if(ts.isTemplateExpression(x)){let s=x.head.text;x.templateSpans.forEach((p,i)=>s+=`{${i}}`+p.literal.text);add(s);}else ts.forEachChild(x,literals);}
   if(n.arguments[0])literals(n.arguments[0]);
  }
  // Fixed tuples provide navigation, stages and control labels.
  if(ts.isArrayLiteralExpression(n))for(const child of n.elements)if(ts.isStringLiteral(child)&&!child.text.startsWith('/')&&!child.text.includes('='))add(child.text);
  if(ts.isPropertyAssignment(n)&&['title','label'].includes(n.name.getText(ast))&&ts.isStringLiteral(n.initializer))add(n.initializer.text);
  if(file.endsWith('Kiosk.tsx')&&ts.isStringLiteral(n)&&n.text.includes('. ')&&!n.text.includes('class'))add(n.text);
  ts.forEachChild(n,visit);
 }visit(ast);
}
for(const text of ['Interface language','Title','Language','Source name','Verified source URL','Source record URL','Rights / permission statement','Manuscripts & Letters','From the supplied dataset','Published collection records','Other approved records','All material','Needs Review','Published','Withdrawn','Processing Issues','Certificate of Completion'])add(text);
const catalog=Object.fromEntries([...strings].sort().map(text=>[crypto.createHash('sha256').update(text).digest('hex').slice(0,16),text]));
for(const name of ['backend/app/interface_strings.json','frontend/src/interface-strings.json'])fs.writeFileSync(name,JSON.stringify(catalog,null,2)+'\n');
console.log(`${strings.size} allowlisted interface strings; both catalogs identical.`);
