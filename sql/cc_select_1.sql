select o.model_id, o.model_op_tv, o.model_cl_tv, o.con_id, o.local_symbol, o.expiry, o.days_remaining d, o.strike, 
o.op_quote_date,  op_sq_trade_avg, o.op_oq_ask_avg, o.op_oq_bid_avg, op_iv, o.op_tv,
sq.quote_date cl_quote_date,  sq.trade_average cl_sq_trade_avg, oq.ask_avg cl_oq_ask_avg, oq.bid_avg cl_oq_bid_avg,
		GET_IV(`sq`.trade_average, `o`.`strike`) AS `cl_iv`,
        GET_TV(`sq`.trade_average, `o`.`strike`, `oq`.`bid_avg`) AS `cl_tv`,
		(TO_DAYS(`sq`.`quote_date`) - TO_DAYS(`o`.`op_quote_date`)) AS `delta_days`,
		round(GET_IV(`sq`.trade_average, `o`.`strike`) - op_iv,3) AS `delta_iv`,
        round(GET_TV(`sq`.trade_average, `o`.`strike`, `oq`.`bid_avg`) - op_tv,3) AS `delta_tv`,
        round(sq.trade_average - op_sq_trade_avg,3)  AS `delta_stock`,
        round(sq.trade_average - op_sq_trade_avg,3) + oq.bid_avg - o.op_oq_ask_avg delta         
from model_cc_open_tv o, stock_quote sq, option_quote oq
where o.op_quote_date between '2022-11-10 09:00:00' and '2022-11-10 17:00:00'
and model_id = 1
and sq.quote_date > o.op_quote_date
and sq.quote_date = oq.quote_date
and oq.con_id = o.con_id 
and GET_TV(`sq`.trade_average, `o`.`strike`, `oq`.`bid_avg`) < model_cl_tv
and o.op_tv >= model_op_tv and model_cl_tv <= GET_TV(`sq`.trade_average, `o`.`strike`, `oq`.`bid_avg`)
order by sq.quote_date
