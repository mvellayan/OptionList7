# Planed to do

1. Current Inventory 
- Read all .csv files and group by 
  - security
  - date
  - count(*)
  - Data caching format:			
 
| Security | Date | Type | Count |
| -- | -- | -- | -- |
| AAPL  221216C00035000 | 3-Nov | BID_ASK |  390 |

- not sure if needed: write/read table 

2. Process CONTRACT for a date-range
- pull quote history
- pull option list history
- find trade range
- list options to pull
- see what you don't have, going back 30 days
- schedule those to be pulled 

3. Data Goal have minute history by stock, option for 1 year

4. Processing Goal, Simulate Entry Exit tiggers:
    - Entry:
      - Days to expire: range(1..15)
      - Calls From: 1up, 2up, 1 down, 2 down 
      - TV%: 0-0.5%, 0.5-1.0%, 1.0-1.5, 1.5-2.0, 2.0-2.5, 2.5+
    - Exit:
      - TV%: 0-0.5%, 0.5-1.0%, 1.0-1.5, 1.5-2.0, 2.0-2.5, 2.5+
      - IV%: 0-0.5%, 0.5-1.0%, 1.0-1.5, 1.5-2.0, 2.0-2.5, 2.5+
5. 