#
#  name: option_pull_status_summary.sql
#		show last 30 days 
select c.quote_date, c.expiry, group_concat( distinct concat(c.strike,  ' (', c.calls, "/", p.calls, ')' ) order by c.strike) 
from 
  (select date(quote_date) quote_date, ol.expiry, ol.strike, ol.option_type, format(count(*), 0) calls
	from option_quote oq, option_list ol where oq.con_id = ol.con_id 
	and option_type = 'C'
	group by date(quote_date), ol.expiry, ol.strike, ol.option_type) c
left join 
  (select date(quote_date) quote_date, ol.expiry, ol.strike, ol.option_type, format(count(*), 0) calls
	from option_quote oq, option_list ol where oq.con_id = ol.con_id 
	and option_type = 'P'
	group by date(quote_date), ol.expiry, ol.strike, ol.option_type) p
on ( c.quote_date = p.quote_date and c.expiry = p.expiry and c.strike = p.strike)
where c.quote_date > CURDATE() - INTERVAL 30 DAY 
group by c.quote_date, c.expiry