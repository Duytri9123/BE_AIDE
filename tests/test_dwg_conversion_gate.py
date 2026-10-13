import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from app.services.ingestion.cad_parser import CadParserService
class DwgConversionTests(unittest.TestCase):
 def test_missing_converter_never_scans_binary_dwg(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'drawing.dwg';source.write_bytes(b'AC1032-test')
   with patch('ezdxf.addons.odafc.is_installed',return_value=False),patch.object(CadParserService,'extract_strings_from_dwg') as scan:
    with self.assertRaises(Exception):CadParserService.parse_cad(str(source))
    scan.assert_not_called()
 def test_conversion_produces_valid_dxf_before_parse(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'drawing.dwg';source.write_bytes(b'AC1032-test')
   def convert(src,dest,**kwargs):ezdxf.new('R2018').saveas(dest)
   with patch('ezdxf.addons.odafc.is_installed',return_value=True),patch('ezdxf.addons.odafc.convert',side_effect=convert) as conversion:
    target=CadParserService.prepare_analysis_path(str(source))
    self.assertEqual(Path(target).suffix,'.dxf');ezdxf.readfile(target)
    self.assertEqual(CadParserService.prepare_analysis_path(str(source)),target)
    conversion.assert_called_once()
