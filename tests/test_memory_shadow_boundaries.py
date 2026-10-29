"""Budget-edge regression against the production Session Context Planner."""
import unittest

from test_memory_retrieval import ROOT, candidate, load, memory


class ShadowBudgetBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = load(ROOT / "assets/core/engineering-specs/spec_router.py",
                          "retrieval_boundary_router")

    def test_oversize_proposal_pointer_falls_back_without_blocking_baseline(self):
        c = candidate(relation="background", content="Short.")
        result = memory.shadow_context(self.router, [c], budget_bytes=10)
        self.assertEqual(result["effective_context"], "Short.")
        self.assertEqual(result["proposal"], result["baseline"])
        self.assertEqual(result["proposal_status"], "baseline_fallback")
        self.assertEqual(result["proposal_warning"], "PROPOSAL_POINTERS_EXCEED_BUDGET")
        self.assertEqual(result["byte_delta"], 0)


if __name__ == "__main__":
    unittest.main()
