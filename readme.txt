Tested on Python 3.9
requires plotly

Reads and graphs PGE Electricity downloaded stats.

 Login to PGE
 Click on ENERGY USEAGE DETAILS
 Scroll down to [Green Button] Download my data
 Select 'Export usage for a range of days' 
 You can select up to one year. CSV
 Unzip and keep the electricity CSV file

If you change code, To run unit tests run `python unit/test_01.py`

usage: graph_pge.py [-h] [--start-date START_DATE] [--end-date END_DATE] filename {1,2,3,4,5,6,7,8}
graph_pge.py: error: the following arguments are required: filename, graph_type
(base) zsolts-Mac-Pro:pge zsolt$ python graph_pge.py -h
usage: graph_pge.py [-h] [--start-date START_DATE] [--end-date END_DATE] filename {1,2,3,4,5,6,7,8}

Process PG&E CSV file
  1 Trend kWh  Total Month By Weekday
  2 Trend kWh  Average Month By Weekday
  3 Trend kWh  Average Weekday By Month
  4 Trend kWh  Average Hour By Weekday
  5 Trend Cost Average Hour By Weekday
  6 Trend Calcuated Rate  Average Month By Weekday
  7 kWh use Daily
  8 Cost Daily

positional arguments:
  filename              Path to the CSV file to process
  {1,2,3,4,5,6,7,8}     select one choice described in the above description

optional arguments:
  -h, --help            show this help message and exit
  --start-date START_DATE
                        Start date (YYYY-MM-DD)
  --end-date END_DATE   End date (YYYY-MM-DD)

Example run:
python graph_pge.py unit/test_data.csv 7