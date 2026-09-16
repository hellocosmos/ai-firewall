import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import ts from 'typescript';
const root=path.resolve(import.meta.dirname,'../src');
const codes=['en','ko','zh-CN','ja','es','fr'];
const dictionaries=Object.fromEntries(codes.map(code=>[code,JSON.parse(fs.readFileSync(path.join(root,'locales',code+'.json'),'utf8'))]));
const keys=Object.keys(dictionaries.en).sort();
const placeholders=text=>(text.match(/\{\d+\}/g)||[]).sort();
for(const code of codes){
  assert.deepEqual(Object.keys(dictionaries[code]).sort(),keys,`${code}: keys differ`);
  for(const key of keys){
    assert.ok(dictionaries[code][key].trim(),`${code}: empty ${key}`);
    assert.deepEqual(placeholders(dictionaries[code][key]),placeholders(key),`${code}: placeholders ${key}`);
  }
}
for(const name of fs.readdirSync(root).filter(name=>/\.(jsx|js)$/.test(name))){
  const source=fs.readFileSync(path.join(root,name),'utf8');
  assert.ok(!/[\uac00-\ud7af\u3040-\u30ff\u4e00-\u9fff]/u.test(source),`${name}: localized text outside locale data`);
  const ast=ts.createSourceFile(name,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.JSX);
  function visit(node){
    if(ts.isCallExpression(node)&&node.expression.getText(ast)==='t'&&ts.isStringLiteral(node.arguments[0])){
      assert.ok(Object.hasOwn(dictionaries.en,node.arguments[0].text),`${name}: missing ${node.arguments[0].text}`);
    }
    ts.forEachChild(node,visit);
  }
  visit(ast);
}
console.log(`Six locales verified: ${keys.length} keys, placeholders, English source strings.`);
