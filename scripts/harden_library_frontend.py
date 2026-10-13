from pathlib import Path
root = Path(__file__).resolve().parents[2]
p = root / 'AIDE/packages/cad-viewer-example/src/components/dashboard/EquipmentLibraryPage.vue'
s = p.read_text(encoding='utf-8')
s = s.replace('Bảng giá thiết bị điện 2026, thông số nguồn và bản vẽ CAD có đối chiếu.', 'Thông tin thiết bị và bản vẽ CAD từ thư viện nguồn.')
s = s.replace('<span v-else class="source-pill">', '<span v-else-if="accessGranted" class="source-pill">', 1)
s = s.replace('<div class="catalog-layout">', '''<section v-if="locked" class="state filters">
        <h2>Thư viện dành cho gói trả phí</h2>
        <p>Gói Free chưa được xem thông tin hoặc tải bản vẽ của thư viện.</p>
        <router-link class="download" to="/pricing">Xem các gói sử dụng</router-link>
      </section>
      <div v-else class="catalog-layout">''', 1)
s = s.replace("const loading = ref(false)", "const locked = ref(false), accessGranted = ref(false)\nconst loading = ref(false)", 1)
s = s.replace("  try {\n    const { data } = await client.get('/equipment-library/browse'", """  try {
    if (!accessGranted.value) {
      const access = (await client.get('/library-access')).data
      locked.value = !access.full_access
      if (locked.value) { items.value = []; return }
      accessGranted.value = true
    }
    const { data } = await client.get('/equipment-library/browse'""", 1)
s = s.replace("} catch (e: any) { if (current === version) error.value", "} catch (e: any) { if (e?.response?.status === 403) { locked.value = true; accessGranted.value = false; items.value = []; detailOpen.value = false } else if (current === version) error.value", 1)
s = s.replace('            <img class="drawing-source-image" :src="`/equipment-library/${detail.catalog_id}/drawing-source`" alt="Bản vẽ nguồn vùng NIÊN KÊ" />', '            <CadThumb :url="`/equipment-library/${detail.catalog_id}/drawing-source`" alt="Bản vẽ nguồn" />')
p.write_text(s, encoding='utf-8')
p = root / 'AIDE/packages/cad-viewer/src/util/catalogProjection.ts'
s = p.read_text(encoding='utf-8').replace("import catalog from '../data/equipment_catalog.json'\n", '')
start = s.index('function normalizeStr(')
end = s.index('export function resolveCatalogRecord', start)
s = s[:start] + s[end:]
start = s.index('  const rawBrand =')
end = s.index('  const w = positive(input.w', start)
s = s[:start] + '  // Dimensions must come from the authorized server response or the project.\n' + s[end:]
p.write_text(s, encoding='utf-8')
p = root / 'AIDE/packages/cad-viewer/src/component/ribbon/MlRibbonDeviceAccessoryGallery.vue'
s = p.read_text(encoding='utf-8').replace("import equipmentCatalogJson from '../../data/equipment_catalog.json'", "const equipmentCatalogJson = ref<{ brands?: string[]; items?: any[] }>({})")
s = s.replace('(equipmentCatalogJson as any)', 'equipmentCatalogJson.value')
s = s.replace('const brands = equipmentCatalogJson.value.brands || [\n', 'const brands = computed(() => equipmentCatalogJson.value.brands || [\n')
s = s.replace("'LS (standard)', 'LS (premium)', 'Schneider Electric', 'ABB', 'Mitsubishi', 'Chint', 'EMIC', 'Samwha'\n]", "'LS (standard)', 'LS (premium)', 'Schneider Electric', 'ABB', 'Mitsubishi', 'Chint', 'EMIC', 'Samwha'\n])")
s = s.replace("    const response = await catalogTbFetch('/cad-library/catalog-tb')", "    equipmentCatalogJson.value = await (await catalogTbFetch('/equipment-library/projection-catalog')).json()\n    const response = await catalogTbFetch('/cad-library/catalog-tb')")
p.write_text(s, encoding='utf-8')
p = root / 'AIDE/packages/cad-viewer-example/vite.config.ts'
s = p.read_text(encoding='utf-8').replace("host: '0.0.0.0'", "host: '127.0.0.1'").replace('allowedHosts: true', "allowedHosts: ['localhost', 'elquote.top', '.elquote.top']")
s = s.replace('      fs: {', "      fs: {\n        deny: ['**/.env', '**/.env.*', '**/.git/**', '**/equipment_catalog.json', '**/*.sqlite', '**/CatalogTB/**'],")
s = s.replace("      minify: true,", "      minify: true,\n      sourcemap: false,")
p.write_text(s, encoding='utf-8')
