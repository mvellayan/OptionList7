# Covered Call Models

## Models
    1. The table MODEL lists entry/exit TV, entry/Exit IVs
    2. view MODEL_CC_ENTRY lists all possible buy/entries
            Model		
                model_id	entry_tv	exit_tv  entry_iv	exit_iv
    	        2.5	        2           2
            Option				
                con_id	    local_symbol	        expiry	    days_remaining	strike
                536593700	AAPL  221118C0015000	11/18/22	1.58	        150
            Open								
                o_quote_date	o_sq_trade_avg	o_sq_bid_avg   o_sq_ask_avg	  o_oq_trade_avg	 o_oq_bid_avg   o_oq_ask_avg	 o_iv	  o_tv
                11/16/22 10:00	148.247	        148.244	       148.259	      1.188	             1.18	        1.196	        -1.741	  2.921
            
    3. ... list all trades.  Add these columns; this will be a table

            Close
                c_quote_date	c_sq_trade_avg	c_sq_bid_avg   c_sq_ask_avg   c_oq_trade_avg	c_oq_bid_avg	c_oq_ask_avg	c_iv	  c_tv
                11/16/22 10:00	148.247	        148.244	       148.259	      1.188	            1.18	        1.196	        -1.741	  2.921
            Analysis						
                delta_hours	    delta_days	   delta_tv 	delta_iv	  ret_amt	ret_pct	    ret_yrly_pct


### File/ Directory Description

    \ref-data\
        model-name.csv; for each id (1..500) assigned modeler name (john smith, ...)
        model-generator
        model-list.csv		list of models with entry & exit criteria

    \1-build-model-list.py
        loads/replace model_name into mysql table
        reads ref-data and creates pouplates 
            model-list.csv 
            model_list mysql table
    
    
    \2-create_open_entries.sql (start_date, end_date)
            loops through each minute stock quote
                loops through each option quote
                    add entries to cc_trades (model_no, open_stock_id, open_option_id)
    
    
    \2-create_close_entries.sql (start_date, end_date)
            cc_trades where close_stock_id is null
            update close_stock_id, close_option_id
                exit reasons:
                    - exit trigggers hit (exit_tv, exit_iv)
                    - time up
    


    