import time
import unittest

from paper_graph import blocks as blocks_mod
from paper_graph import check as check_mod
from paper_graph.check import check, parse_graph, render

from .helpers import blocks, graph, node


def run(g, b=None, pdf_sha=None):
    bl, errs = blocks_mod.parse(b if b is not None else blocks())
    assert not errs, errs
    parsed, diags = parse_graph(g)
    return check(parsed, bl, pdf_sha, diags)


def codes(report, level=None):
    return sorted(d.code for d in report.diags if level is None or d.level == level)


class Valid(unittest.TestCase):
    def test_toy_graph_passes(self):
        r = run(graph())
        self.assertEqual(codes(r), [], render(r, "toy"))
        self.assertEqual(r.stats["anchors_ok"], 5)
        self.assertEqual((r.stats["tiers"], r.stats["depth"]), (2, 2))

    def test_quote_survives_hyphenation_ligature_and_column_break(self):
        g = graph()
        node(g, "idea")["anchors"] = [
            {"page": 2, "quote": "uses a single fixed projection"},  # chữ ghép ﬁ trong bài
            {"page": 2, "quote": "and the end of this sentence continues in the next column"},  # vắt qua hai cột
        ]
        r = run(g)
        self.assertEqual(codes(r), [], render(r, "toy"))


class Anchors(unittest.TestCase):
    def test_fabricated_quote(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "we prove the widget is optimal for all inputs"}]
        r = run(g)
        self.assertEqual(codes(r), ["PG201"])

    def test_quote_on_another_page_names_that_page(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 2, "quote": "processes all tokens at once"}]
        r = run(g)
        self.assertEqual(codes(r), ["PG201"])
        self.assertIn("tr.1", r.diags[0].hint)

    def test_near_miss_gets_closest_hint(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "We propose the flat widgets, which process all tokens"}]
        r = run(g)
        self.assertEqual(codes(r), ["PG201"])
        self.assertIn("gần nhất", r.diags[0].hint)

    def test_numbers_and_comparisons_must_match(self):  # review: 28.4 từng khớp 284, p < khớp p >
        for bad in ["The flat widget reaches 284 BLEU (p < 0.05)", "The flat widget reaches 28.4 BLEU (p > 0.05)",
                    "with a loss change of 3.2 points over", "of −3.2 points over 100000 steps"]:
            g = graph()
            node(g, "idea")["anchors"] = [{"page": 2, "quote": bad}]
            self.assertEqual(codes(run(g)), ["PG201"], bad)
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 2, "quote": "reaches 28.4 BLEU (p<0.05) with a loss change of -3.2"}]
        self.assertEqual(codes(run(g)), [])

    def test_quote_must_start_and_end_on_word_and_number_boundaries(self):  # review 2: V1
        for bad in ["The flat widget reaches 28.4 BLEU (p < 0.0",   # dừng giữa số
                    "The flat widget reaches 2",                      # dừng giữa 28.4
                    "8.4 BLEU (p < 0.05) with a loss",                # bắt đầu giữa số
                    "3.2 points over 100,000 steps",                  # bỏ mất dấu âm của −3.2
                    "possible to train with a rate",                  # mảnh của "impossible"
                    "with 2-3 layers at 80.5 recall"]:                # bỏ mất % dính với 80.5
            g = graph()
            node(g, "idea")["anchors"] = [{"page": 2, "quote": bad}]
            self.assertEqual(codes(run(g)), ["PG201"], bad)

    def test_signs_exponents_and_ranges(self):  # review 2: V2, V4
        for bad in ["train with a rate of 1e5 or with", "rate of 1e-5 or with 23 layers"]:
            g = graph()
            node(g, "idea")["anchors"] = [{"page": 2, "quote": bad}]
            self.assertEqual(codes(run(g)), ["PG201"], bad)
        g = graph()
        node(g, "idea")["anchors"] = [
            {"page": 2, "quote": "a loss change of − 3.2 points"},  # khoảng trắng sau dấu âm khác bài: vẫn khớp
            {"page": 2, "quote": "It is impossible to train with a rate of 1e-5 or with 2-3 layers at 80.5% recall"}]
        self.assertEqual(codes(run(g)), [])

    def test_block_given_matches_any_occurrence(self):  # review: chỉ xét lần xuất hiện đầu
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "processes all tokens at once", "block": "p1-b3"}]
        self.assertEqual(codes(run(g)), [])

    def test_short_quote_is_an_error(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "flat widget"}]
        self.assertEqual(codes(run(g)), ["PG202"])

    def test_both_length_rules_apply_separately(self):  # review 2: mỗi điều kiện có test riêng
        for bad in ["a b c d e", "internationalization considerations matter"]:  # đủ từ thiếu chữ; đủ chữ thiếu từ
            g = graph()
            node(g, "idea")["anchors"] = [{"page": 1, "quote": bad}]
            self.assertEqual(codes(run(g)), ["PG202"], bad)

    def test_page_out_of_range(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 9, "quote": "processes all tokens at once"}]
        self.assertEqual(codes(run(g)), ["PG204"])

    def test_wrong_block(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "processes all tokens at once", "block": "p1-b1"}]
        r = run(g)
        self.assertEqual(codes(r), ["PG205"])
        self.assertIn("p1-b2", r.diags[0].hint)

    def test_unknown_block(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 1, "quote": "processes all tokens at once", "block": "p1-b9"}]
        self.assertEqual(codes(run(g)), ["PG205"])

    def test_paper_node_without_anchor(self):
        g = graph()
        node(g, "idea")["anchors"] = []
        self.assertEqual(codes(run(g)), ["PG200"])

    def test_inference_node_without_anchor_is_a_warning(self):
        g = graph()
        node(g, "idea").update(anchors=[], basis="inference")
        self.assertEqual(codes(run(g)), ["PG208"])

    def test_missing_figure(self):
        g = graph()
        node(g, "result")["figure"] = "p2-f9"
        self.assertEqual(codes(run(g)), ["PG207"])

    def test_scanned_page_is_unverified_not_passed(self):
        g = graph()
        node(g, "idea")["anchors"] = [{"page": 3, "quote": "text that only exists on the scan"}]
        r = run(g)
        self.assertEqual(codes(r), ["PG210"])
        self.assertEqual(r.stats["anchors_unverified"], 1)

    def test_sha_mismatch_with_blocks_blocks_anchor_checks(self):  # TM-3
        g = graph()
        g["paper"]["sha256"] = "b" * 64
        r = run(g)
        self.assertEqual(codes(r), ["PG206"])
        self.assertEqual(r.stats["anchors_ok"], 0)

    def test_sha_mismatch_with_pdf(self):  # TM-3
        self.assertEqual(codes(run(graph(), pdf_sha="c" * 64)), ["PG206"])

    def test_no_blocks(self):
        parsed, diags = parse_graph(graph())
        r = check(parsed, None, None, diags)
        self.assertIn("PG211", codes(r))
        self.assertEqual(r.stats["anchors_unverified"], 5)


class Structure(unittest.TestCase):
    def test_bad_ids_rejected(self):  # TM-5: id đi vào DOM và URL
        for bad in ["a b", "<x>", 'a"b', "", "x" * 65, 3]:
            g = graph()
            g["nodes"].append({"id": bad, "parent": None, "kind": "limit", "label": "x"})
            self.assertIn("PG103", codes(run(g)), bad)

    def test_bad_ids_in_every_id_field(self):  # TM-5
        bad = "x<script>"
        cases = [
            lambda g: node(g, "idea").update(parent=bad),
            lambda g: node(g, "idea").update(figure=bad),
            lambda g: node(g, "idea")["anchors"][0].update(block=bad),
            lambda g: g["edges"][0].update({"from": bad}),
            lambda g: g["edges"][0].update(to=bad),
            lambda g: g["groups"].append({"id": bad, "parent": None, "label": "n", "members": ["idea"]}),
            lambda g: g["groups"].append({"id": "g1", "parent": None, "label": "n", "members": [bad]}),
        ]
        for k, fn in enumerate(cases):
            g = graph()
            fn(g)
            self.assertIn("PG103", codes(run(g)), k)

    def test_wrong_types_are_diagnostics_not_crashes(self):  # review: TypeError unhashable
        g = graph()
        node(g, "idea").update(kind=["x"], basis={"a": 1}, status=[1], label=5, anchors=[{"page": [1], "quote": 3}])
        g["edges"][0].update(kind=["flow"])
        g["edges"][2].update(strength=["strong"])
        r = run(g)
        self.assertTrue(set(codes(r)) >= {"PG101", "PG102"})

    def test_caps(self):  # TM-1
        g = graph()
        g["nodes"] += [{"id": f"n{i}", "parent": None, "kind": "context", "label": "x", "basis": "inference"}
                       for i in range(check_mod.MAX_NODES)]
        node(g, "idea")["anchors"] *= check_mod.MAX_ANCHORS + 1
        r = run(g)
        self.assertEqual(codes(r, "error").count("PG111"), 2)
        self.assertEqual(r.stats["nodes"], check_mod.MAX_NODES)

    def test_long_parent_chain_is_linear(self):  # review: O(n³) với chuỗi parent dài
        g = graph()
        n = check_mod.MAX_NODES - 10
        g["nodes"] += [{"id": f"c{i}", "parent": f"c{i - 1}" if i else "idea", "kind": "step", "label": "x",
                        "basis": "inference"} for i in range(n)]
        t = time.perf_counter()
        r = run(g)
        self.assertLess(time.perf_counter() - t, 2.0)
        self.assertEqual(r.stats["depth"], n + 1)

    def test_duplicate_id(self):
        g = graph()
        g["nodes"].append(dict(node(g, "idea")))
        self.assertIn("PG104", codes(run(g)))

    def test_unknown_kind_and_field(self):
        g = graph()
        node(g, "idea").update(kind="vibe", anchor=[])
        self.assertEqual(codes(run(g)), ["PG102", "PG110"])

    def test_parent_missing_and_cycle(self):
        g = graph()
        node(g, "r.claim")["parent"] = "nope"
        self.assertIn("PG105", codes(run(g)))
        g = graph()
        node(g, "result")["parent"] = "r.claim"
        self.assertIn("PG105", codes(run(g)))

    def test_dangling_and_cross_tier_edges(self):
        g = graph()
        g["edges"].append({"from": "idea", "to": "ghost", "kind": "flow"})
        g["edges"].append({"from": "idea", "to": "r.claim", "kind": "flow"})
        self.assertEqual(codes(run(g)), ["PG106", "PG107"])

    def test_supports_needs_strength(self):
        g = graph()
        del g["edges"][2]["strength"]
        self.assertIn("PG102", codes(run(g)))

    def test_group_rules(self):
        g = graph()
        g["groups"] = [{"id": "g1", "parent": None, "label": "nhóm", "members": ["idea", "r.claim", "ghost"]},
                       {"id": "g2", "parent": None, "label": "nhóm 2", "members": ["idea"]}]
        self.assertEqual(codes(run(g)), ["PG108", "PG108", "PG108"])

    def test_wrong_version(self):
        g = graph()
        g["version"] = 2
        self.assertEqual(codes(run(g)), ["PG109"])

    def test_root_not_a_dict(self):
        parsed, diags = parse_graph([])
        self.assertIsNone(parsed)
        self.assertEqual([d.code for d in diags], ["PG101"])


class Tiers(unittest.TestCase):
    def test_more_than_nine_in_a_tier(self):
        g = graph()
        for i in range(7):
            g["nodes"].append({"id": f"x{i}", "parent": None, "kind": "context", "label": "x", "basis": "inference",
                               "anchors": [{"page": 1, "quote": "processes all tokens at once"}]})
            g["edges"].append({"from": "idea", "to": f"x{i}", "kind": "relates"})
        self.assertIn("PG300", codes(run(g), "error"))

    def test_empty_graph(self):
        g = graph()
        g["nodes"], g["edges"] = [], []
        self.assertEqual(codes(run(g)), ["PG301"])

    def test_all_nodes_in_a_parent_cycle_still_leaves_a_root(self):
        g = graph()
        node(g, "problem")["parent"] = "idea"
        node(g, "idea")["parent"] = "problem"
        r = run(g)
        self.assertEqual(codes(r, "error").count("PG105"), 1)
        self.assertNotIn("PG301", codes(r))

    def test_single_child_isolated_long_label(self):
        g = graph()
        g["nodes"] = [n for n in g["nodes"] if n["id"] != "r.fig"]
        g["edges"] = g["edges"][:2]
        g["nodes"].append({"id": "lonely", "parent": None, "kind": "limit", "label": "y" * 70,
                           "anchors": [{"page": 1, "quote": "processes all tokens at once"}]})
        self.assertEqual(codes(run(g)), ["PG302", "PG303", "PG304", "PG305"])

    def test_evidence_not_used_and_supports_direction(self):
        g = graph()
        g["edges"][2] = {"from": "r.claim", "to": "r.fig", "kind": "supports", "strength": "weak"}
        self.assertEqual(codes(run(g)), ["PG305", "PG306", "PG307"])


if __name__ == "__main__":
    unittest.main()
