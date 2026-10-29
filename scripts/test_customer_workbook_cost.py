import unittest
from app.services.bom.customer_workbook_cost import calculate_design_cost
from app.services.ai.procurement_review import build_quotation_rows, assembly_requirements, apply_design_costs


class CustomerWorkbookCosts(unittest.TestCase):
    def test_missing_design_does_not_return_sample_prices(self):
        self.assertEqual(calculate_design_cost({})['status'],'needs_design')

    def test_invalid_dimensions_and_bar_counts_do_not_start_excel(self):
        for payload in ({'enclosure':{'height_mm':800}},
                        {'busbar_segments':[dict(width_mm=30,thickness_mm=5,length_mm=-10,quantity=3)]},
                        {'busbar_segments':[dict(width_mm=30,thickness_mm=5,length_mm=1000,quantity=1.5)]}):
            with self.subTest(payload=payload),self.assertRaises(ValueError):calculate_design_cost(payload)

    def test_design_bom_is_not_a_customer_quotation(self):
        devices=[dict(category='MCB',name='MCB nhánh L1',spec='1P 10A',quantity=1,panel_code='P',section='Đầu ra',notes='Phân tích dài cho thiết kế'),
                 dict(category='MCB',name='MCB nhánh L2',spec='1P 10A',quantity=2,panel_code='P',section='Đầu ra')]
        design=assembly_requirements(devices,include_cad_references=False)
        self.assertIn('DIN',{r['code'] for r in design})
        quote=build_quotation_rows(devices,{},refresh_prices=False)
        packages=[r for r in quote if r.get('commercial_package')]
        self.assertEqual([r['package_code'] for r in packages],['ENCLOSURE','BUSBAR','MATERIALS','LABOR'])
        self.assertFalse(any('Rail DIN' in r['name'] or 'Máng dây' in r['name'] for r in quote))
        items=[r for r in quote if r.get('category')=='MCB']
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['quantity'],3)
        self.assertEqual(items[0]['notes'],'')
        self.assertTrue(all(r.get('quantity')==1 for r in packages))

    def test_only_totals_from_calculation_enter_matching_panel(self):
        rows=build_quotation_rows([dict(category='MCB',name='MCB',spec='1P10A',quantity=1,panel_code='P')],{},refresh_prices=False)
        updated=apply_design_costs(rows,{'status':'calculated','enclosure':{'unit_price':950000},'busbar':{'unit_price':805500}},'P')
        self.assertEqual(next(r for r in updated if r.get('package_code')=='ENCLOSURE')['unit_price'],950000)
        self.assertEqual(next(r for r in updated if r.get('package_code')=='BUSBAR')['unit_price'],805500)
        self.assertIsNone(next(r for r in rows if r.get('package_code')=='ENCLOSURE')['unit_price'])
        self.assertTrue(all(r.get('unit_price') is None for r in apply_design_costs(rows,{'status':'needs_design'},'P') if r.get('commercial_package')))

    def test_source_fabrication_parts_do_not_duplicate_commercial_packages(self):
        devices=[dict(category='ENCLOSURE',name='Vỏ tủ',spec='700x500x250 X1.5mm',quantity=2,panel_code='P'),
                 dict(category='DIN_RAIL',name='Rail DIN',quantity=4,panel_code='P')]
        rows=build_quotation_rows(devices,{},refresh_prices=False)
        self.assertEqual(len([r for r in rows if r.get('row_type')=='item']),4)
        self.assertFalse(any(r.get('category') in {'ENCLOSURE','DIN_RAIL'} for r in rows))
        self.assertEqual(devices[0]['quantity'],2)


if __name__=='__main__':unittest.main()
