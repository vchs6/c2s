"""性能修复不得改变UTF-8跨度、完整盘点或文档事实边界。"""
import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from c2s_skill.algorithm import extract_python_algorithm
from c2s_skill.acquisition import _python_facts
from c2s_skill.fact_query import execute_fact_query
from c2s_skill.inventory import source_fingerprint

class CountingBytes(bytes):
    splits=0
    def splitlines(self,*a,**kw):
        self.splits+=1
        return super().splitlines(*a,**kw)

class ReviewPerformanceTests(unittest.TestCase):
    def test_algorithm_offsets_index_source_once(self):
        src=CountingBytes(('def run(x):\n'+''.join(f' value{i}=x+{i}\n' for i in range(100))+' return value99\n').encode())
        r=extract_python_algorithm(src,'m.py','run')['algorithm']
        self.assertTrue(r['body']['steps']);self.assertLessEqual(src.splits,1)
    def test_facts_offsets_index_source_once_and_preserve_unicode(self):
        src=CountingBytes(('def run():\n'+''.join(f' 名称{i}="中文"\n' for i in range(100))+' return 名称99\n').encode())
        facts=_python_facts('m.py',src,ast.parse(src))
        self.assertLessEqual(src.splits,1)
        self.assertTrue(any('名称99' in f.text for f in facts))
    def test_fingerprint_streams_all_paths_including_dependencies(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'node_modules').mkdir();target=root/'node_modules/large.bin';target.write_bytes(b'x'*1024*1024)
            with patch.object(Path,'read_bytes',side_effect=AssertionError('指纹不应一次读完整文件')):
                first=source_fingerprint(root)
            with target.open('r+b') as f:f.seek(700000);f.write(b'y')
            self.assertNotEqual(first,source_fingerprint(root))
    def test_markdown_fences_do_not_create_entities(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'m.py').write_text('def run():\n return 1\n')
            (root/'README.md').write_text('# Demo\n```markdown\n## Modules\n- fake: example only\n```\n## Modules\n- actual: documented\n')
            r=execute_fact_query(root,{'view':'entity','target':{'kind':'Module'},'detail':'self'})
            self.assertEqual(['actual'],[i['name'] for i in r['items']])
    def test_members_selector_accepts_supported_chinese_and_english_forms(self):
        from c2s_skill.request_selectors import normalize_request
        self.assertEqual(normalize_request('类型A的成员有哪些'), normalize_request('members of 类型A'))
    def test_markdown_comments_do_not_open_fences_or_end_other_comments(self):
        samples = [
            '## Modules\n<!-- first --> <!--\n- fake: still comment\n-->\n- actual: documented\n',
            '<!--\n```\n-->\n## Modules\n- actual: documented\n',
            '## Modules\n~~~markdown\n<!--\n~~~\n- actual: documented\n',
        ]
        for markdown in samples:
            with self.subTest(markdown=markdown), tempfile.TemporaryDirectory() as t:
                root = Path(t); (root/'m.py').write_text('def run():\n return 1\n')
                (root/'README.md').write_text(markdown)
                r = execute_fact_query(root, {'view':'entity', 'target':{'kind':'Module'}, 'detail':'self'})
                self.assertEqual(['actual'], [i['name'] for i in r['items']])
