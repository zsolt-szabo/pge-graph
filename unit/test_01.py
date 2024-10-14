import datetime
import unittest
import sys

required_paths = ["."]
for each_path in required_paths:
    sys.path.append(each_path)
import graph_pge as g


class TestData:
    def __init__(self):
        self.data = g._read_csv("unit/test_data.csv", skip_first_line_count=6)
        self.start_end_dates_good = g._StartEndDates("2023-11-01", "2023-11-30")
        self.start_end_dates_missing_weekday = g._StartEndDates("2023-11-01", "2023-11-05")
        self.created_data = {}


class GraphFunctionTests(unittest.TestCase):
    # data_by_month_week
    def test_01_good_dates_no_warn_kwh_month_week(self):
        w = g.WarnMesg(silent=True)
        t.created_data["test_01_good_dates_no_warn_kwh_month_week"] = g._data_by_month_week(
            t.data, t.start_end_dates_good, warnobj=w
        )
        assert w.msg is None, "We should not get a warning with good data"

    def test_02_return_all_weeks(self):
        found_weeks = ()
        data = t.created_data["test_01_good_dates_no_warn_kwh_month_week"]
        for month in data:
            assert g._get_weekdays(data[month]) == g.weekdays, "We expect good data to return all days of the week"
            break

    def test_03_specific_datapoint_kwh_month_week(self):
        data = t.created_data["test_01_good_dates_no_warn_kwh_month_week"]
        assert data["23 Nov"]["Fri"][0] == 52.48, "We expect to have this total KWH on Friday"

    def test_04_good_dates_no_warn_cost_month_week(self):
        w = g.WarnMesg(silent=True)
        t.created_data["test_04_good_dates_no_warn_cost_month_week"] = g._data_by_month_week(
            t.data, t.start_end_dates_good, metric="COST", warnobj=w
        )
        assert w.msg is None, "We should not get a warning with good data"

    def test_05_specific_datapoint_kwh(self):
        data = t.created_data["test_04_good_dates_no_warn_cost_month_week"]
        assert (
            round(data["23 Nov"]["Fri"][0], 2) == 18.71
        ), "We expect to have this total COST on Friday (Might be OS sensitive test)"

    # data_by_week_hour
    def test_06_good_dates_warn_cost_week_hour(self):
        w = g.WarnMesg(silent=True)
        t.created_data["test_06_good_dates_warn_cost_week_hour"] = g._data_by_week_hour(
            t.data, t.start_end_dates_good, metric="COST", warnobj=w
        )
        msg = "\nWARNING:Edge case for Fri.  We should have at least one months data for each week. Consider adjusting the month using --start-date or  --end-date"
        assert w.msg == msg, "This 'good data' is actually zero on one Friday and thus we expect an WARNING message"

    def test_07_specific_datapoint_kwh_week_hour(self):
        data = t.created_data["test_06_good_dates_warn_cost_week_hour"][0]
        assert (
            round(data["Sat"]["00:00"][0], 2) == 1.24
        ), "We expect to have this total COST on Friday (Might be OS sensitive test)"

    def test_08_good_dates_each_day(self):
        t.created_data["test_08_good_dates_each_day"] = g._data_by_each_day(
            t.data, t.start_end_dates_good
        )
        datecheck = datetime.datetime(2023, 11, 14, 0, 0)
        data = t.created_data["test_08_good_dates_each_day"]
        assert data[datecheck][1] == 18.87, 'We expect to see 18.87 KWH on this date'

    def test_09_bad_dates_warn_kwh_month_week(self):
        w = g.WarnMesg(silent=True)
        t.created_data["test_09_bad_dates_warn_kwh_month_week"] = g._data_by_month_week(
            t.data, t.start_end_dates_missing_weekday, warnobj=w
        )
        msg = "\nWARNING:Edge case for 23 Nov possibly not enough data for (Wed, 24). We expected 93  Consider pruning the month using --start-date or  --end-date"
        assert w.msg == msg, "We should  get a warning with less than a months data"

if __name__ == "__main__":
    t = TestData()
    print("=" * 80)
    print("=" * 40, "      BEGIN TESTING")
    print("=" * 80)
    unittest.main()
