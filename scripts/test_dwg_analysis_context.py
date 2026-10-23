import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ezdxf
from app.services.ingestion.cad_parser import CadParserService
from app.services.ingestion.document_context import DocumentContextService


class DwgContextTests(unittest.TestCase):
    def test_repeated_analysis_reuses_geometry_without_sharing_mutable_results(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';drawing=ezdxf.new()
            drawing.modelspace().add_line((0,0),(10,20));drawing.saveas(path)
            with patch('app.services.ingestion.cad_parser.ezdxf.readfile',wraps=ezdxf.readfile) as read:
                first=CadParserService.parse_dxf(str(path))
                first.texts.append({'text':'caller mutation'})
                second=CadParserService.parse_dxf(str(path))
                self.assertEqual(read.call_count,1)
                self.assertEqual(second.texts,[])
                drawing.modelspace().add_text('changed');drawing.saveas(path)
                changed=CadParserService.parse_dxf(str(path))
                self.assertEqual(read.call_count,2)
                self.assertEqual(changed.texts[0]['text'],'changed')

    def test_dwg_is_converted_before_preflight_reads_spatial_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.dwg';source.write_bytes(b'AC1032fixture')
            converted=Path(folder)/'converted.dxf'
            drawing=ezdxf.new();drawing.modelspace().add_text('MCCB 3P 200A 85kA',dxfattribs={'insert':(10,20)})
            drawing.saveas(converted)
            with patch.object(CadParserService,'prepare_analysis_path',return_value=str(converted)) as prepare:
                context=DocumentContextService.extract(SimpleNamespace(filename=source.name,file_path=str(source)))
            prepare.assert_called_once_with(str(source))
            self.assertIn('MCCB 3P 200A 85kA',context['text'])
            self.assertIn('X=10 Y=20',context['text'])
            self.assertEqual(context['filename'],'source.dwg')

    def test_converter_unavailable_has_actionable_context_error(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source.dwg';source.write_bytes(b'AC1032fixture')
            with patch.object(CadParserService,'prepare_analysis_path',side_effect=ValueError('Missing DWG converter')):
                context=DocumentContextService.extract(SimpleNamespace(filename=source.name,file_path=str(source)))
            self.assertEqual(context['text'],'')
            self.assertIn('Missing DWG converter',context['read_error'])


if __name__=='__main__':unittest.main()
