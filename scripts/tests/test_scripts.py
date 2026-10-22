"""Unit tests: python -I -m unittest discover -s scripts/tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_index  # noqa: E402
import convert  # noqa: E402
import validate  # noqa: E402
from common import FIELDS, LICENCE, NOTICE, USE  # noqa: E402


def ln(text, x0=85, x1=510):
    return {"text": text, "x0": x0, "x1": x1}


class ReflowTest(unittest.TestCase):
    def test_wrapped_lines_become_one_paragraph(self):
        lines = [ln("A pena única resulta do cúmulo"), ln("jurídico das penas parcelares.", x1=300)]
        self.assertEqual(convert.reflow(lines, right=510),
                         ["A pena única resulta do cúmulo jurídico das penas parcelares."])

    def test_line_end_hyphen_is_kept_and_joined_without_space(self):
        self.assertEqual(convert.join_lines(["os Estados-", "Membros"]), "os Estados-Membros")
        self.assertEqual(convert.join_lines(["um caso", "novo"]), "um caso novo")

    def test_short_line_with_full_stop_ends_the_paragraph(self):
        lines = [ln("Primeira frase completa.", x1=250), ln("Segunda frase noutro parágrafo.", x1=510)]
        self.assertEqual(len(convert.reflow(lines, right=510)), 2)

    def test_list_marker_starts_a_new_paragraph(self):
        lines = [ln("Questões:", x1=510), ln("1. Qual o tribunal competente?", x1=510),
                 ln("2. E se houver recurso?", x1=510)]
        self.assertEqual(len(convert.reflow(lines, right=510)), 3)

    def test_blank_line_separates_paragraphs_and_whitespace_is_normalised(self):
        lines = [ln("um   dois três"), ln(""), ln("quatro")]
        self.assertEqual(convert.reflow(lines, right=510), ["um dois três", "quatro"])


class RepairTest(unittest.TestCase):
    def test_repair_glyphs_is_opt_in_and_fixes_known_ligatures(self):
        self.assertEqual(convert.repair("arƟgo ﬁlho"), "artigo filho")
        self.assertEqual(convert.clean("arƟgo"), "arƟgo")  # default: text untouched


class CaseHeadingTest(unittest.TestCase):
    def test_case_markers(self):
        for t in ["CASO PRÁTICO", "CASO PRÁTICO 1", "Caso n.º 2", "Caso 1 – Cúmulo de penas",
                  "Hipótese 1:", "Caso prático 3"]:
            self.assertEqual(convert.classify_heading(t), "case", t)

    def test_resolution_markers(self):
        self.assertEqual(convert.classify_heading("Solução do caso 3"), "solution")
        for t in ["QUESTÕES", "ENUNCIADO", "TÓPICOS DE RESOLUÇÃO", "Resolução", "Propostas de solução"]:
            self.assertEqual(convert.classify_heading(t), "part", t)

    def test_running_prose_is_not_a_heading(self):
        for t in ["Caso venha a concluir pela viabilidade da ação oficiosa de investigação",
                  "caso concreto - transferência de competência para o tribunal",
                  "Questões que mais frequentemente se colocam na atividade dos tribunais.",
                  "Resolução da litispendência. Este critério é claramente inspirado"]:
            self.assertIsNone(convert.classify_heading(t), t)

    def test_numbered_depth(self):
        self.assertEqual(convert.numbered_depth("1. Introdução"), 1)
        self.assertEqual(convert.numbered_depth("1.2. Exigência do trânsito"), 2)
        self.assertEqual(convert.numbered_depth("II – O crime de branqueamento"), 1)
        self.assertEqual(convert.numbered_depth("2 – A revogação da liberdade condicional determina a execução."), 0)
        self.assertEqual(convert.numbered_depth("Texto sem número"), 0)


def good_text(**over):
    meta = {"id": "obra-teste-2020", "title": "Obra", "authors": "A", "year": "2020", "area": "penal",
            "publisher": "Centro de Estudos Judiciários", "source": "https://exemplo.pt/a.pdf",
            "page": "https://exemplo.pt/", "licenca": LICENCE, "uso": USE, "text_version": "extraído do PDF",
            "retrieved": "2026-10-22", "pages": "10", "cases": "2", "notice": NOTICE,
            "headings": "3", "toc_entries": "1"}
    meta.update(over)
    head = "\n".join(f"{k}: {v}" if k in ("year", "pages", "cases", "headings", "toc_entries")
                     else f'{k}: "{v}"' for k, v in meta.items() if v is not None)
    body = "# Obra\n\n## Capítulo\n\n### Caso 1\n\n" + ("Texto do caso. " * 100) + "\n"
    return f"---\n{head}\n---\n\n{body}"


class ValidatorTest(unittest.TestCase):
    path = Path("obras/penal/obra-teste-2020.md")

    def test_good_file_passes(self):
        self.assertEqual(validate.check_text(self.path, good_text()), [])

    def test_missing_licence_is_rejected(self):
        errs = validate.check_text(self.path, good_text(licenca="Todos os direitos reservados."))
        self.assertTrue(any("licence" in e for e in errs))

    def test_missing_source_is_rejected(self):
        errs = validate.check_text(self.path, good_text(source=""))
        self.assertTrue(any("source" in e for e in errs))

    def test_missing_field_and_empty_body_are_rejected(self):
        text = good_text().replace('publisher: "Centro de Estudos Judiciários"\n', "")
        self.assertTrue(any("publisher" in e for e in validate.check_text(self.path, text)))
        short = good_text().split("# Obra")[0] + "# Obra\n"
        self.assertTrue(any("body" in e for e in validate.check_text(self.path, short)))

    def test_heading_count_must_match_and_cover_the_toc(self):
        self.assertTrue(any("headings" in e for e in validate.check_text(self.path, good_text(headings="9"))))
        errs = validate.check_text(self.path, good_text(toc_entries="5"))
        self.assertTrue(any("ToC" in e for e in errs))

    def test_id_must_match_file_name_and_area_folder(self):
        errs = validate.check_text(Path("obras/familia/outro.md"), good_text())
        self.assertTrue(any("file name" in e for e in errs) and any("folder" in e for e in errs))

    def test_all_front_matter_fields_are_required(self):
        self.assertIn("licenca", FIELDS)


class IndexTest(unittest.TestCase):
    def works(self, n, area="penal"):
        return [{"id": f"o{i}", "title": f"T|{i}", "authors": "A", "year": str(2000 + i), "area": area,
                 "cases": str(i)} for i in range(n)]

    def test_main_index_has_a_row_per_work_and_escapes_pipes(self):
        text = build_index.build(self.works(3))["indice.md"]
        self.assertEqual(text.count("\n| T|"), 0)
        self.assertEqual(text.count("\n| T"), 4)  # header row plus three works
        self.assertIn("T\\|0", text)
        self.assertIn("(obras/penal/o0.md)", text)

    def test_area_index_only_above_eight_works(self):
        self.assertEqual(list(build_index.build(self.works(8))), ["indice.md"])
        self.assertIn("obras/penal/indice.md", build_index.build(self.works(9)))


if __name__ == "__main__":
    unittest.main()
