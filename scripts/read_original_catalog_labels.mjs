// Read the original DWG in a separate process; never open or save an AutoCAD session.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..');
const pkg=path.resolve(root,'../AIDE/node_modules/.pnpm/@mlightcad+libredwg-web@0.7.9/node_modules/@mlightcad/libredwg-web');
const {LibreDwg,createModule,Dwg_File_Type}=await import(pathToFileURL(path.join(pkg,'dist/libredwg-web.js')));
const wasm=await createModule({wasmBinary:fs.readFileSync(path.join(pkg,'wasm/libredwg-web.wasm')),print:()=>{},printErr:()=>{}});
const lib=LibreDwg.createByWasmInstance(wasm);
const input=path.join(root,'data/CatalogTB/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg');
const bytes=fs.readFileSync(input);
console.log('Reading original catalog DWG labels and attributes...');
const ptr=lib.dwg_read_data(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),Dwg_File_Type.DWG);
if(!ptr)throw Error('DWG reader returned no database');
const db=lib.convert(ptr);
// The bundled converter computes ATTDEF.default_value then drops it from its
// return value. Read that field from the DWG rather than treating it as blank.
function label(e){
  let text=e.text;
  if(e.type==='ATTDEF'){
    const object=lib.dwg_resolve_handle_silent(ptr,BigInt('0x'+e.handle));
    if(object){const tio=lib.dwg_object_to_entity_tio(object);text=lib.dwg_dynapi_entity_data(tio,'default_value')}
  }
  return {type:e.type,handle:e.handle,text,tag:e.tag,name:e.name,attributes:(e.attribs||[]).map(label),insertionPoint:e.insertionPoint,startPoint:e.startPoint};
}
function labels(entities){return entities.filter(e=>['TEXT','MTEXT','ATTRIB','ATTDEF','INSERT'].includes(e.type)).map(label)}
const result={source:input,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),
  modelspace:labels(db.entities),blocks:db.tables.BLOCK_RECORD.entries.map(b=>({name:b.name,handle:b.handle,labels:labels(b.entities)}))};
fs.writeFileSync(path.join(root,'outputs/original-catalog-labels.json'),JSON.stringify(result));
lib.dwg_free(ptr);
console.log(JSON.stringify({blocks:result.blocks.length,modelspaceLabels:result.modelspace.length}));
