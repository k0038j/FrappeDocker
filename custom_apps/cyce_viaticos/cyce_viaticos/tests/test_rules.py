import unittest
from datetime import date
from decimal import Decimal

from cyce_viaticos.rules import allocate_adjustments, evaluate_attendance


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
