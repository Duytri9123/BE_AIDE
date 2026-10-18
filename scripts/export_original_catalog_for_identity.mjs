// Read-only conversion for geometry/source-label correspondence.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root=path.resolve(import.meta.dirname,'..');
const pkg=path.resolve(root,'../AIDE/node_modules/.pnpm/@mlightcad+libredwg-web@0.7.9/node_modules/@mlightcad/libredwg-web');
const {LibreDwg,createModule}=await import(pathToFileURL(path.join(pkg,'dist/libredwg-web.js')));
const wasm=await createModule({wasmBinary:fs.readFileSync(path.join(pkg,'wasm/libredwg-web.wasm')),print:()=>{},printErr:()=>{}});
const lib=LibreDwg.createByWasmInstance(wasm);
const source=fs.readFileSync(path.join(root,'data/CatalogTB/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'));
const result=lib.dwg_write_dxf(source.buffer.slice(source.byteOffset,source.byteOffset+source.byteLength));
if(!result)throw Error('Original library could not be exported to DXF');
fs.writeFileSync(path.join(root,'outputs/original-catalog-identity.dxf'),result);
console.log(JSON.stringify({bytes:result.length,source_modified:false}));
