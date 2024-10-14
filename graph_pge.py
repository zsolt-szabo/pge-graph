import copy
import csv
import argparse
import datetime

import plotly.graph_objects as px

weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class WarnMesg:
    def __init__(self, silent=False):
        self.msg = None
        self.silent = silent

    # Allow for testing
    def warn(self, msg):
        self.msg = msg
        if self.silent is False:
            print(msg)

class _StartEndDates:
    def __init__(self, start=None, end=None):
        if start is None:
            start = datetime.datetime.strptime("1960-01-01", "%Y-%m-%d")
            start_str = "Not Set"
        else:
            start_str = start
            start = datetime.datetime.strptime(start, "%Y-%m-%d")
        if end is None:
            end = datetime.datetime.now() + datetime.timedelta(days=365)
            end_str = "Not Set"
        else:
            end_str = end
            end = datetime.datetime.strptime(end, "%Y-%m-%d")
        self.start = start
        self.end = end
        self.start_str = "Start Date: " + start_str
        self.end_str = "End: Date" + end_str

    def date_in_range(self, date):
        if date >= self.start and date <= self.end:
            return True
        else:
            return False


def _read_csv(filename, skip_first_line_count=0):
    # Expected Columns:    TYPE, DATE, START TIME, END TIME, USAGE (kWh), COST, NOTES
    #  We also add a CALCULATED RATE column which will cause rows to be deleted when PGE gives a cost of $0
    with open(filename, "r") as file:
        for _ in range(skip_first_line_count):
            file.readline()
        reader = csv.DictReader(file)
        data = list(reader)
    assert (
        "DATE" in data[0]
    ), f"we expect the first {skip_first_line_count} rows in the '{filename}' to not include data, please check"
    bad_data = []
    for i, row in enumerate(data):
        cost = float(row["COST"].replace("$", ""))
        row["COST"] = cost
        if cost != 0:
            row["CALCULATED RATE"] = cost / float(row["USAGE (kWh)"])
        else:  # PGE giving away electricity?  I.. Don't.. Think.. so.
            bad_data.append(i)
    # Pull out the bad rows
    bad_data.reverse()
    for i in bad_data:
        del data[i]
    return data


def _data_by_month_week(data: list[csv.DictReader], startend: _StartEndDates, metric="USAGE (kWh)", warnobj=None):
    # Convert 'Date' to datetime and extract weekday and month
    if warnobj is None:
        warnobj = WarnMesg()
    plotable = {}
    for row in data:
        date = datetime.datetime.strptime(row["DATE"], "%Y-%m-%d")
        year = date.strftime("%y")
        if startend.date_in_range(date):
            month = plotable.setdefault(year + " " + date.strftime("%b"), {})
            weekday_data = month.setdefault(date.strftime("%a"), [0, 0])  # List of [sum, count]
            weekday_data[0] += float(row[metric])
            weekday_data[1] += 1

    # We should see at least 4 Mondays full of 24 hour times allow for a couple of missrepresented rows
    expected = 24 * 4 - 3
    for date in plotable:
        for weekday in plotable[date]:
            if plotable[date][weekday][1] < expected:
                warnobj.warn(
                    "\nWARNING:Edge case for {d} possibly not enough data for ({w}, {s}). We expected {e}  Consider pruning the month using --start-date or  --end-date".format(
                        d=date, w=weekday, s=plotable[date][weekday][1], e=expected
                    )
                )
                break
            else:
                continue
            break  # If the if statement breaks we land here and break all the way out
    return plotable


def _data_by_week_hour(data: list[csv.DictReader], startend: _StartEndDates, metric="USAGE (kWh)", warnobj=None):
    if warnobj is None:
        warnobj = WarnMesg()
    plotable = {}
    hours = set()
    for row in data:
        date = datetime.datetime.strptime(row["DATE"], "%Y-%m-%d")
        if startend.date_in_range(date):
            weekday = plotable.setdefault(date.strftime("%a"), {})
            hour = row["START TIME"].zfill(5)
            hours.add(hour)
            hour_data = weekday.setdefault(hour, [0, 0])  # List of [sum, count]
            hour_data[0] += float(row[metric])
            hour_data[1] += 1
    hours = list(hours)
    hours.sort()
    expected = 4
    for weekday in plotable:
        for hour in plotable[weekday]:
            if plotable[weekday][hour][1] < expected:
                warnobj.warn(
                    "\nWARNING:Edge case for {w}.  We should have at least one months data for each week. Consider adjusting the month using --start-date or  --end-date".format(
                        w=weekday, h=hour, c=plotable[weekday][hour][1], e=expected
                    )
                )
                break
            else:
                continue
            break  # If the if statement breaks we land here and break all the way out
    return plotable, hours


def _data_by_each_day(data: list[csv.DictReader], startend: _StartEndDates, metric="USAGE (kWh)"):
    """returns dict of keys type(date) values tuple(StringDate, metric)"""
    # Convert 'Date' to datetime and extract weekday and month
    plotable = {}
    for row in data:
        date = datetime.datetime.strptime(row["DATE"], "%Y-%m-%d")
        year = date.strftime("%y")
        if startend.date_in_range(date):
            metric_total = plotable.setdefault(date, (row["DATE"], 0))[1]
            # We get data over 24 hours so add it up
            plotable[date] = (row["DATE"], float(row[metric]) + metric_total)
    return plotable


def _get_weekdays(plotable):
    # If dataset is small, it is possible we will miss weekdays so remove
    wkdays = copy.copy(weekdays)
    deletes = []
    for i, day in enumerate(weekdays):
        if day not in plotable:
            deletes.append(i)
    deletes.reverse()
    for i in deletes:
        del wkdays[i]
    return wkdays


# ##############  Start Plots ########################


def plot_trend_month_kwh_tot_grouped_by_weekday(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    plotable = _data_by_month_week(data, start_end_dates)
    pdata = []
    for month in plotable:
        y = []
        for weekday in _get_weekdays(plotable[month]):
            if weekday in plotable[month]:
                totkwh = plotable[month][weekday][0]
                y.append(totkwh)
        pdata.append(px.Bar(name=month, x=_get_weekdays(plotable[month]), y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = (
        f"plot_trend_month_kwh_tot_grouped_by_weekday <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    )
    plot.update_layout(xaxis_title="month grouped by weekday", yaxis_title="Total kWh Used")
    plot.show()


def plot_trend_month_kwh_avg_grouped_by_weekday(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    plotable = _data_by_month_week(data, start_end_dates)
    pdata = []
    for month in plotable:
        y = []
        for weekday in _get_weekdays(plotable[month]):
            if weekday in plotable[month]:
                totkwh = plotable[month][weekday][0]
                totdays = plotable[month][weekday][1]
                y.append(totkwh / totdays * 24)  # 24 hours in the day
        pdata.append(px.Bar(name=month, x=_get_weekdays(plotable[month]), y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = (
        f"plot_trend_month_kwh_avg_grouped_by_weekday <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    )
    plot.update_layout(xaxis_title="month grouped by weekday", yaxis_title="Avg kWh Used")
    plot.show()


def plot_trend_weekday_kwh_avg_grouped_by_month(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    # Convert 'Date' to datetime and extract weekday and month
    plotable = _data_by_month_week(data, start_end_dates)
    pdata = []
    for weekday in weekdays:
        y = []
        months = list(plotable.keys())
        for month in plotable:
            if weekday in plotable[month]:
                totkwh = plotable[month][weekday][0]
                totdays = plotable[month][weekday][1]
                y.append(totkwh / totdays * 24)  # 24 hours in the day
        pdata.append(px.Bar(name=weekday, x=months, y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = (
        f"plot_trend_weekday_kwh_avg_grouped_by_month <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    )
    plot.update_layout(xaxis_title="Weekday grouped by month", yaxis_title="Avg kWh Used")
    plot.show()


def plot_trend_hour_kwh_avg_grouped_by_weekday(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    plotable, hours = _data_by_week_hour(data, start_end_dates)
    pdata = []
    for hour in hours:
        y = []
        for weekday in _get_weekdays(plotable):
            if weekday in plotable:
                totkwh = plotable[weekday][hour][0]
                totdays = plotable[weekday][hour][1]
                y.append(totkwh / totdays)
        pdata.append(px.Bar(name=hour, x=weekdays, y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = (
        f"plot_trend_hour_kwh_avg_grouped_by_weekday <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    )
    plot.update_layout(xaxis_title="Hour grouped by weekday", yaxis_title="Avg kWh Used")
    plot.show()


def plot_trend_hour_cost_avg_grouped_by_weekday(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    # Convert 'Date' to datetime and extract weekday and month
    plotable, hours = _data_by_week_hour(data, start_end_dates, "COST")
    pdata = []
    for hour in hours:
        y = []
        for weekday in _get_weekdays(plotable):
            totkwh = plotable[weekday][hour][0]
            totdays = plotable[weekday][hour][1]
            y.append(totkwh / totdays)
        pdata.append(px.Bar(name=hour, x=weekdays, y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = (
        f"plot_trend_hour_cost_avg_grouped_by_weekday <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    )
    plot.update_layout(xaxis_title="Hour grouped by weekday", yaxis_title="Avg Cost $")
    plot.show()


def plot_trend_calculated_rate_avg_grouped_by_weekday(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    # Convert 'Date' to datetime and extract weekday and month
    plotable, hours = _data_by_week_hour(data, start_end_dates, "CALCULATED RATE")
    pdata = []
    for hour in hours:
        y = []
        for weekday in _get_weekdays(plotable):
            totkwh = plotable[weekday][hour][0]
            totdays = plotable[weekday][hour][1]
            y.append(totkwh / totdays)
        pdata.append(px.Bar(name=hour, x=weekdays, y=y))
    plot = px.Figure(data=pdata)
    plot.layout.title = f"plot_trend_calculated_rate_avg_grouped_by_weekday <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    plot.update_layout(xaxis_title="Timeslot for day of week", yaxis_title="Rate Avg Dollars per kWh")
    plot.show()


def plot_kwh_grouped_by_day(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    plotable = _data_by_each_day(data, start_end_dates)
    y = []
    x = []
    for date, vals in plotable.items():
        x.append(date)
        y.append(vals[1])
    bar = px.Bar(x=x, y=y)
    plot = px.Figure(data=bar)
    plot.layout.title = f"plot_kwh_grouped_by_day <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    plot.update_layout(xaxis_title="Day", yaxis_title="Avg kWh Used")
    plot.show()


def plot_cost_grouped_by_day(data: list[csv.DictReader], start_end_dates: _StartEndDates, fname=None):
    plotable = _data_by_each_day(data, start_end_dates, "COST")
    y = []
    x = []
    for date, vals in plotable.items():
        x.append(date)
        y.append(vals[1])
    bar = px.Bar(x=x, y=y)
    plot = px.Figure(data=bar)
    plot.layout.title = f"plot_cost_grouped_by_day <br> {start_end_dates.start_str}    {start_end_dates.end_str} <br> Filename: {fname}"
    plot.update_layout(xaxis_title="Day", yaxis_title="Cost")
    plot.show()


def main():
    desc = ("Process PG&E CSV file\n" +
            "  1 Trend kWh  Total Month By Weekday\n" +
            "  2 Trend kWh  Average Month By Weekday\n" +
            "  3 Trend kWh  Average Weekday By Month\n" +
            "  4 Trend kWh  Average Hour By Weekday\n" +
            "  5 Trend Cost Average Hour By Weekday\n" +
            "  6 Trend Calcuated Rate  Average Month By Weekday\n" +
            "  7 kWh use Daily\n" +
            "  8 Cost Daily\n")
    parser = argparse.ArgumentParser(description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("filename", help="Path to the CSV file to process")
    parser.add_argument("graph_type", choices=["1", "2", "3", "4", "5", "6", "7", "8"],
                         help="select one choice described in the above description")
    parser.add_argument("--start-date", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    filename = args.filename
    data = _read_csv(filename, skip_first_line_count=6)

    start_end_dates = _StartEndDates(args.start_date, args.end_date)
    if args.graph_type == "1":
        plot_trend_month_kwh_tot_grouped_by_weekday(data, start_end_dates, filename)
    if args.graph_type == "2":    
        plot_trend_month_kwh_avg_grouped_by_weekday(data, start_end_dates, filename)
    if args.graph_type == "3":
        plot_trend_weekday_kwh_avg_grouped_by_month(data, start_end_dates, filename)
    if args.graph_type == "4":  
        plot_trend_hour_kwh_avg_grouped_by_weekday(data, start_end_dates, filename)
    if args.graph_type == "5":
        plot_trend_hour_cost_avg_grouped_by_weekday(data, start_end_dates, filename)
    if args.graph_type == "6":
        plot_trend_calculated_rate_avg_grouped_by_weekday(data, start_end_dates, filename)
    if args.graph_type == "7":
        plot_kwh_grouped_by_day(data, start_end_dates, filename)
    if args.graph_type == "8":
        plot_cost_grouped_by_day(data, start_end_dates, filename)


if __name__ == "__main__":
    main()
