import copy
import unittest

from graph_engine.account_analytics import build_account_analytics


class AccountAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            {"step": 1, "amount": 10.0, "name_orig": "A", "name_dest": "B"},
            {"step": 2, "amount": 30.0, "name_orig": "C", "name_dest": "A"},
            {"step": 4, "amount": 20.0, "name_orig": "B", "name_dest": "A"},
            {"step": 5, "amount": 1000.0, "name_orig": "A", "name_dest": "D"},
            {"step": 6, "amount": 9999.0, "name_orig": "F", "name_dest": "A"},
        ]

    def test_directional_totals_and_manual_expected_values(self):
        result = build_account_analytics(self.transactions, "A", 4)

        self.assertEqual(result["inbound_transaction_count"], 2)
        self.assertEqual(result["outbound_transaction_count"], 1)
        self.assertEqual(result["inbound_amount_total"], 50.0)
        self.assertEqual(result["outbound_amount_total"], 10.0)
        self.assertAlmostEqual(result["average_transaction_amount"], 20.0)
        self.assertEqual(result["inbound_to_outbound_amount_ratio"], 5.0)
        self.assertEqual(result["total_turnover"], 60.0)

    def test_trailing_window_boundaries_and_cutoff_inclusion(self):
        result = build_account_analytics(
            self.transactions, "A", 4, window_steps=(1, 2, 7)
        )
        self.assertEqual(result["trailing_windows"]["1"], {
            "window_size_steps": 1,
            "start_step_exclusive": 3,
            "end_step_inclusive": 4,
            "transaction_count": 1,
            "amount_total": 20.0,
            "inbound_transaction_count": 1,
            "inbound_amount_total": 20.0,
            "outbound_transaction_count": 0,
            "outbound_amount_total": 0.0,
        })
        self.assertEqual(result["trailing_windows"]["2"]["transaction_count"], 1)
        self.assertEqual(result["trailing_windows"]["7"]["transaction_count"], 3)
        self.assertEqual(result["cutoff_step"], 4)

    def test_future_transactions_do_not_affect_analytics(self):
        result = build_account_analytics(self.transactions, "A", 4)
        without_future = build_account_analytics(self.transactions[:3], "A", 4)
        self.assertEqual(result, without_future)

    def test_counterparty_shares_hhi_and_dominant_share(self):
        result = build_account_analytics(self.transactions, "A", 4)
        inbound = result["inbound_counterparty_concentration"]
        outbound = result["outbound_counterparty_concentration"]

        self.assertEqual(inbound["counterparty_count"], 2)
        self.assertEqual(inbound["transaction_shares"], {"B": 0.5, "C": 0.5})
        self.assertEqual(inbound["amount_shares"], {"B": 0.4, "C": 0.6})
        self.assertAlmostEqual(inbound["transaction_hhi"], 0.5)
        self.assertAlmostEqual(inbound["amount_hhi"], 0.52)
        self.assertEqual(inbound["dominant_transaction_share"], 0.5)
        self.assertAlmostEqual(inbound["dominant_amount_share"], 0.6)
        self.assertEqual(outbound["transaction_shares"], {"B": 1.0})
        self.assertEqual(outbound["amount_shares"], {"B": 1.0})
        self.assertEqual(outbound["transaction_hhi"], 1.0)
        self.assertEqual(outbound["amount_hhi"], 1.0)
        self.assertEqual(outbound["dominant_amount_share"], 1.0)

    def test_empty_account_has_zero_totals_and_undefined_ratios(self):
        result = build_account_analytics([], "A", 4)
        self.assertEqual(result["inbound_transaction_count"], 0)
        self.assertEqual(result["outbound_transaction_count"], 0)
        self.assertEqual(result["inbound_amount_total"], 0.0)
        self.assertEqual(result["outbound_amount_total"], 0.0)
        self.assertIsNone(result["average_transaction_amount"])
        self.assertIsNone(result["inbound_to_outbound_amount_ratio"])
        self.assertIsNone(result["first_activity_step"])
        self.assertIsNone(result["activity_span_steps"])
        self.assertIsNone(result["mean_distinct_activity_step_gap"])
        for direction in (
            "inbound_counterparty_concentration",
            "outbound_counterparty_concentration",
        ):
            self.assertEqual(result[direction]["counterparty_count"], 0)
            self.assertIsNone(result[direction]["transaction_hhi"])
            self.assertIsNone(result[direction]["amount_hhi"])
            self.assertIsNone(result[direction]["dominant_amount_share"])

    def test_single_counterparty_concentration(self):
        result = build_account_analytics(
            [
                {"step": 1, "amount": 2, "name_orig": "B", "name_dest": "A"},
                {"step": 2, "amount": 3, "name_orig": "B", "name_dest": "A"},
            ],
            "A",
            2,
        )
        inbound = result["inbound_counterparty_concentration"]
        self.assertEqual(inbound["counterparty_count"], 1)
        self.assertEqual(inbound["transaction_shares"], {"B": 1.0})
        self.assertEqual(inbound["amount_shares"], {"B": 1.0})
        self.assertEqual(inbound["transaction_hhi"], 1.0)
        self.assertEqual(inbound["amount_hhi"], 1.0)

    def test_invalid_or_missing_inputs_raise_value_error(self):
        invalid_cases = [
            ([{"amount": 2, "name_orig": "A", "name_dest": "B"}], 2),
            ([{"step": 1, "amount": float("nan"), "name_orig": "A", "name_dest": "B"}], 2),
            ([{"step": 1, "amount": -1, "name_orig": "A", "name_dest": "B"}], 2),
            ([{"step": 1, "amount": 2, "name_orig": "", "name_dest": "B"}], 2),
            ([{"step": 1, "amount": 2, "name_orig": "A"}], 2),
        ]
        for transactions, cutoff in invalid_cases:
            with self.subTest(transactions=transactions):
                with self.assertRaises(ValueError):
                    build_account_analytics(transactions, "A", cutoff)

        with self.assertRaises(ValueError):
            build_account_analytics([], "A", 1, window_steps=(0,))

    def test_large_integer_cutoff_and_window_are_validated_without_float_conversion(self):
        large_integer = 10 ** 1000

        cutoff_result = build_account_analytics([], "A", large_integer, window_steps=(1,))
        self.assertEqual(cutoff_result["cutoff_step"], large_integer)

        window_result = build_account_analytics([], "A", 1, window_steps=(large_integer,))
        self.assertEqual(window_result["window_sizes_steps"], [large_integer])
        self.assertEqual(
            window_result["trailing_windows"][str(large_integer)]["start_step_exclusive"],
            1 - large_integer,
        )

    def test_future_row_payload_is_not_examined(self):
        result = build_account_analytics(
            [
                {"step": 1, "amount": 2, "name_orig": "B", "name_dest": "A"},
                {"step": 3},
            ],
            "A",
            2,
        )
        self.assertEqual(result["inbound_transaction_count"], 1)

    def test_deterministic_output_across_runs_and_input_order(self):
        expected = build_account_analytics(self.transactions, "A", 4)
        self.assertEqual(expected, build_account_analytics(self.transactions, "A", 4))
        self.assertEqual(
            expected,
            build_account_analytics(list(reversed(self.transactions)), "A", 4),
        )

    def test_input_is_not_mutated(self):
        original = copy.deepcopy(self.transactions)
        build_account_analytics(self.transactions, "A", 4)
        self.assertEqual(self.transactions, original)

    def test_activity_gaps_use_distinct_steps_without_inventing_order(self):
        result = build_account_analytics(
            [
                {"step": 1, "amount": 1, "name_orig": "A", "name_dest": "B"},
                {"step": 1, "amount": 2, "name_orig": "C", "name_dest": "A"},
                {"step": 4, "amount": 3, "name_orig": "A", "name_dest": "D"},
            ],
            "A",
            4,
        )
        self.assertEqual(result["first_activity_step"], 1)
        self.assertEqual(result["last_activity_step"], 4)
        self.assertEqual(result["activity_span_steps"], 3)
        self.assertEqual(result["distinct_activity_step_gap_count"], 1)
        self.assertEqual(result["mean_distinct_activity_step_gap"], 3.0)
        self.assertEqual(result["max_distinct_activity_step_gap"], 3)

    def test_zero_amount_counterparty_has_undefined_amount_shares(self):
        result = build_account_analytics(
            [{"step": 1, "amount": 0, "name_orig": "B", "name_dest": "A"}],
            "A",
            1,
        )
        concentration = result["inbound_counterparty_concentration"]
        self.assertEqual(concentration["transaction_hhi"], 1.0)
        self.assertEqual(concentration["amount_shares"], {"B": None})
        self.assertIsNone(concentration["amount_hhi"])
        self.assertIsNone(concentration["dominant_amount_share"])

    def test_paysim_aliases_and_self_transfer_semantics(self):
        result = build_account_analytics(
            [
                {"step": 2, "amount": 7, "nameOrig": "A", "nameDest": "A"},
                {"step": 2, "amount": 5, "nameOrig": "B", "nameDest": "A"},
            ],
            "A",
            2,
        )
        self.assertEqual(result["inbound_transaction_count"], 2)
        self.assertEqual(result["outbound_transaction_count"], 1)
        self.assertEqual(result["inbound_amount_total"], 12.0)
        self.assertEqual(result["outbound_amount_total"], 7.0)
        self.assertEqual(result["average_transaction_amount"], 6.0)
        self.assertEqual(result["total_turnover"], 12.0)
        self.assertEqual(
            result["inbound_counterparty_concentration"]["transaction_shares"],
            {"B": 1.0},
        )
        self.assertEqual(
            result["outbound_counterparty_concentration"]["counterparty_count"],
            0,
        )

    def test_zero_denominator_ratio_is_null_with_inbound_activity(self):
        result = build_account_analytics(
            [{"step": 1, "amount": 5, "name_orig": "B", "name_dest": "A"}],
            "A",
            1,
        )
        self.assertEqual(result["inbound_amount_total"], 5.0)
        self.assertEqual(result["outbound_amount_total"], 0.0)
        self.assertIsNone(result["inbound_to_outbound_amount_ratio"])

    def test_non_finite_derived_ratio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ratio is not finite"):
            build_account_analytics(
                [
                    {"step": 1, "amount": 1e308, "name_orig": "B", "name_dest": "A"},
                    {"step": 1, "amount": 1e-308, "name_orig": "A", "name_dest": "C"},
                ],
                "A",
                1,
            )


if __name__ == "__main__":
    unittest.main()
