"""Live preview quality must assess the surface actually painted by Gradient."""
import copy
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gradient_server_test', ROOT / 'scripts/card_review_server.py')
SERVER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SERVER)


def manifest():
    text = 'Le idee prendono forma.'
    return {'schema_version':'0.4','state':'contenuto_approvato','revision':1,
            'content':{'text':text,'transformation':'AI_GENERATED','evidence_status':'UNVERIFIED','emphasis':'',
                       'styles':[], 'styles_customized':True,'attribution':{'label':'Studio','role':'author'}},
            'direction':'editorial', 'presentation':{'logo_mode':'hidden','graphic_mode':'auto','graphic_variant':'gradient','graphic_seed':42},
            'formats':[{'id':'4x5','width':1440,'height':1800,'lines':[text],'text_scale':.9,'vertical_position':'center'}],
            'brand':{'name':'Test','font':{'family':'Arial'},'colors':{'primary':'#68364F','text':'#68364F','accent':'#E992B0','background':'#E9F6FF'}},
            'source':{},'output':{}}


class GradientEditorTests(unittest.TestCase):
    def test_preview_allows_raw_accent_when_derived_surface_is_legible(self):
        data = manifest()
        previews = SERVER.render_preview(data, ROOT)
        qa = SERVER.preview_quality(data, previews, ROOT)
        self.assertTrue(qa['passed'], qa)
        score = SERVER.preview_score(data, previews, qa)
        self.assertGreater(score['categories']['contrast'], 59)

    def test_score_follows_emitted_stops_not_only_manifest_colours(self):
        data = manifest()
        previews = SERVER.render_preview(data, ROOT)
        qa = SERVER.preview_quality(data, previews, ROOT)
        original = SERVER.preview_score(data, previews, qa)['categories']['contrast']
        altered = copy.deepcopy(previews)
        root = ET.fromstring(altered[0]['svg'])
        for node in root.iter():
            if node.tag.endswith('}stop'):
                node.set('stop-color', data['brand']['colors']['primary'])
        altered[0]['svg'] = ET.tostring(root, encoding='unicode')
        self.assertLess(SERVER.preview_score(data, altered, qa)['categories']['contrast'], original)
        self.assertFalse(SERVER.preview_quality(data, altered, ROOT)['passed'])

    def test_gradient_keeps_outline_minimum_size_guard(self):
        data = manifest()
        data['content']['styles'] = [{'start':0, 'end':len(data['content']['text']), 'type':'outline'}]
        visual = SERVER.pack.proof_manifest_for_format(data, data['formats'][0])
        visual['canvas'] = {'width':1440, 'height':1800}
        svg = SERVER.proof.render_svg(visual, ROOT, 'editorial', font_size_override=20)
        issues = SERVER.inspector.inspect_render(svg, 'editorial', 1440, 1800)
        self.assertIn('outline_too_small', {issue['code'] for issue in issues})
