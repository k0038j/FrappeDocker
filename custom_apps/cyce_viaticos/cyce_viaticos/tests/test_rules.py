import unittest
from datetime import date
from decimal import Decimal

from cyce_viaticos.rules import allocate_adjustments, build_inclusive_date_range, evaluate_attendance


class ViaticPeriodTest(unittest.TestCase):
	def test_date_range_includes_both_boundaries(self):
		dates = build_inclusive_date_range(date(2026, 9, 13), date(2026, 9, 15))
		self.assertEqual(
			dates,
			(date(2026, 9, 13), date(2026, 9, 14), date(2026, 9, 15)),
		)

	def test_end_date_cannot_precede_start_date(self):
		with self.assertRaisesRegex(ValueError, "end_before_start"):
			build_inclusive_date_range(date(2026, 9, 15), date(2026, 9, 13))

	def test_date_range_is_limited_to_one_year_and_one_day(self):
		with self.assertRaisesRegex(ValueError, "period_too_long"):
			build_inclusive_date_range(date(2026, 1, 1), date(2027, 1, 2))


class AttendanceRulesTest(unittest.TestCase):
	def test_present_is_eligible(self):
		decision = evaluate_attendance("Reposición", "Present", date(2026, 9, 12), date(2026, 9, 12))
		self.assertTrue(decision.eligible)
		self.assertFalse(decision.provisional)

	def test_half_day_never_generates_viatic(self):
		decision = evaluate_attendance("Adelantado", "Half Day", date(2026, 9, 13), date(2026, 9, 12))
		self.assertFalse(decision.eligible)
		self.assertEqual(decision.label, "Medio día")

	def test_future_advance_without_attendance_is_provisional(self):
		decision = evaluate_attendance("Adelantado", None, date(2026, 9, 13), date(2026, 9, 12))
		self.assertTrue(decision.eligible)
		self.assertTrue(decision.provisional)

	def test_past_advance_without_attendance_is_not_eligible(self):
		decision = evaluate_attendance("Adelantado", None, date(2026, 9, 11), date(2026, 9, 12))
		self.assertFalse(decision.eligible)


class AdjustmentAllocationTest(unittest.TestCase):
	def test_oldest_adjustments_reduce_days_in_order(self):
		allocation = allocate_adjustments(
			[Decimal("100.00"), Decimal("80.00")],
			[Decimal("120.00"), Decimal("100.00")],
		)
		self.assertEqual(allocation.applications, (Decimal("120.00"), Decimal("60.00")))
		self.assertEqual(allocation.day_deductions, (Decimal("100.00"), Decimal("80.00")))
		self.assertEqual(allocation.net_day_amounts, (Decimal("0.00"), Decimal("0.00")))

	def test_adjustment_never_exceeds_payable_amount(self):
		allocation = allocate_adjustments([Decimal("75.00")], [Decimal("200.00")])
		self.assertEqual(allocation.applications, (Decimal("75.00"),))
		self.assertEqual(allocation.net_day_amounts, (Decimal("0.00"),))


if __name__ == "__main__":
	unittest.main()
