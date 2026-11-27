"""Maintenance safety checks; no database connection or destructive fixtures."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_academic_data import simplify_value, sample_changes, write_durable_json


class CleanupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.convert = lambda s: s.translate(str.maketrans("學會張級業", "学会张级业"))

    def test_backup_is_exact_utf8_bytes_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "backup.json"
            write_durable_json(path, {"name": "张晨", "text": "第一行\n第二行"})
            import json
            self.assertEqual(path.read_bytes(), json.dumps(
                {"name": "张晨", "text": "第一行\n第二行"}, ensure_ascii=False, default=str, indent=2
            ).encode("utf-8"))
            with self.assertRaises(FileExistsError):
                write_durable_json(path, {})

    def test_visible_text_changes_without_changing_urls_or_html_attributes(self):
        value = '<a href="https://example.com/學會">學會</a> https://example.com/學會?q=張'
        self.assertEqual(
            simplify_value(value, self.convert),
            '<a href="https://example.com/學會">学会</a> https://example.com/學會?q=張',
        )

    def test_json_keys_and_machine_values_are_preserved(self):
        self.assertEqual(
            simplify_value({"學號": ["張", {"field_會": "學會"}], "image": "/storage/學會.png"}, self.convert),
            {"學號": ["张", {"field_會": "学会"}], "image": "/storage/學會.png"},
        )

    def test_unknown_org_layout_is_rejected_before_mutation(self):
        with self.assertRaises(ValueError):
            sample_changes([{"id": 1, "name": "真实学校", "type": "school", "parent_id": None}])

    def test_only_known_legacy_structure_is_repurposed(self):
        rows = [dict(id=i, name=name, type=kind, parent_id=parent, entry_year=None)
                for i, name, kind, parent in [
                    (1,"校友商會","school",None), (2,"科技與創新分會","college",1),
                    (3,"企業服務分會","college",1), (4,"AI 與軟件系","department",2),
                    (5,"跨境電商系","department",2), (6,"財稅法務系","department",3),
                    (7,"品牌市場系","department",3), (8,"AI 工具班","class",4),
                    (9,"SaaS 創業班","class",4), (10,"品牌出海班","class",5),
                    (11,"企業財稅班","class",6), (12,"增長營銷班","class",7),
                ]]
        updates, majors = sample_changes(rows)
        self.assertEqual(set(updates), set(range(1, 13)))
        self.assertEqual(len(majors), 4)
        self.assertEqual(updates[8]["entry_year"], updates[10]["entry_year"])
        self.assertNotEqual(updates[8]["entry_year"], updates[9]["entry_year"])
        self.assertEqual(updates[8]["major_key"], updates[9]["major_key"])
        rows[7]["name"] = "真实班级"
        with self.assertRaises(ValueError):
            sample_changes(rows)


if __name__ == "__main__":
    unittest.main()
