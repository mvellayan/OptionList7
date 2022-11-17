# Data-Collection

## Directory / File / DataStructure organization
    data/
        reference/
            - stock-list.cvs -- list of stocks to manage
            - option-list.csv -- list of options to manage
        status/
            - status.csv: conId, date, count
            - todo.csv: conId, date, durationStr [1 D, 5 D, 30 D, etc]
        quotes/mm/dd/
                status.csv
                sq-BID_ASK-conid.csv
                sq-TRADES-conid.csv
                oq-BID_ASK-conid.csv
                oq-TRADES-conid.csv
    config/
         market-working.csv date ('2022-10-01'), trading-hours (6.5)

## Functions

    1-pull-option-list
        1. for a list of stokcs in the stock-list.json
        1. pull current list of options
        3. loads data/reference/option-list-AAPL.csv
        4. add new optsion & dedups based on conid
        5. saves back to data/reference/option-list-AAPL.csv

    2-update-status.csv
        1. Input Parameter: date 
            - read status.csv
            - if status.csv does not exist:
                - dedup and write back
                - write status.csv in directory
        2. Update status.csv in /status/ directory

    3-plan-tasks 
        1. Input Parameter: Date, stockContract
        2. Pull stock quotes to file (if it doesn't exist) 
        3. Find trading range
        4. Build optionlist 
                +/- 15% of trading range
                +3 weeks
                find how many days history to pull
        5. Output to status/todo.csv file

    4-pull-tasks
        loop over 1 with trading days
            call 2-plan-tasks
            call 4-pull-history
            call 0-update-status

    5-plan-missing-quotes
        1. Input Parameter: Date
        2. Read status.csv, if it doesnt exist, build it 
        3. Build optionlist 
            +/- 15% of trading range
            +3 weeks
            find how many days history to pull
        4. If conId count != 390, put it back on todo
        5. Output to status/todo.csv file

    6-pull-missing-quotes

    0-pull-history-quotes
        1. pass in parameter object
        2. pull quotes from IB 
        3. filter out 9:30 - 16:00 timeframe
        3. Write to files in appropriate directories 
            
