import unittest

from code_analyzer.analyzer import analyze_source


SAMPLE = r'''
/// Public API docs.
pub fn classify(x: ?i32) !i32 {
    if (x == null) return error.Missing;
    const value = x.?;
    if (value > 10) {
        return 1;
    } else if (value < 0) {
        return -1;
    }
    return 0;
}

fn internal(flag: bool) void {
    // TODO: replace branch table
    if (flag) {
        while (flag) {
            break;
        }
    }
}
'''


class AnalyzerTests(unittest.TestCase):
    def test_detects_functions_and_docs_as_descriptive_evidence(self):
        report = analyze_source(SAMPLE, path="sample.zig")
        self.assertEqual(report["summary"]["functions"], 2)
        self.assertEqual(report["summary"]["public_functions"], 1)
        self.assertEqual(report["summary"]["documented_public_functions"], 1)
        self.assertEqual(report["summary"]["public_api_documentation_coverage"], 1.0)

    def test_complexity_and_semantic_counters(self):
        report = analyze_source(SAMPLE)
        classify = next(f for f in report["functions"] if f["name"] == "classify")
        self.assertGreaterEqual(classify["cyclomatic_complexity"], 4)
        self.assertGreaterEqual(classify["error_paths"], 1)
        self.assertGreaterEqual(classify["optional_operations"], 1)
        self.assertGreaterEqual(classify["return_count"], 4)

    def test_markers_are_comments_only(self):
        report = analyze_source(SAMPLE)
        self.assertEqual(report["summary"]["markers"]["TODO"], 1)

    def test_comments_are_not_a_quality_gate(self):
        report = analyze_source("pub fn exposed() void {}\n")
        rules = {item["rule"] for item in report["findings"]}
        self.assertNotIn("docs.public_api", rules)
        self.assertNotIn("docs.complexity_gap", rules)

    def test_comment_density_is_descriptive(self):
        report = analyze_source("// hello\nconst x = 1;\n")
        self.assertAlmostEqual(report["summary"]["comment_density"], 0.5)

    def test_public_primitive_types_are_portability_findings(self):
        report = analyze_source("pub fn load(id: u64, amount: i32) u32 { return @intCast(id + @as(u64, @intCast(amount))); }\n")
        rules = {item["rule"] for item in report["findings"]}
        self.assertIn("portability.primitive_boundary", rules)
        self.assertIn("portability.low_level_public", rules)
        self.assertGreaterEqual(report["summary"]["primitive_boundary_exposures"], 3)

    def test_semantic_types_do_not_leak_storage_width(self):
        source = "const UserId = struct { value: u64 };\nconst Amount = struct { value: i64 };\npub fn debit(id: UserId, amount: Amount) void { _ = id; _ = amount; }\n"
        report = analyze_source(source)
        rules = {item["rule"] for item in report["findings"]}
        self.assertNotIn("portability.primitive_boundary", rules)
        self.assertEqual(report["summary"]["primitive_boundary_exposures"], 0)


if __name__ == "__main__":
    unittest.main()
