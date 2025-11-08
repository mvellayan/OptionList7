DELIMITER $$
drop function if exists get_tv$$
CREATE DEFINER=`root`@`localhost` FUNCTION `get_tv`(
	sq_trade_average double,
	strike double,
    oq_bid_avg double,
    oq_ask_avg double,
	option_type varchar(1),
    transaction_type varchar(10)) RETURNS double
    DETERMINISTIC
BEGIN
  declare iv, tv double;
  set iv = greatest(0.0, get_iv(sq_trade_average, strike, option_type));
  # https://www.ig.com/en/trading-strategies/option-pricing--the-intrinsic-and-time-values-of-options-explain-220111
  # TV = premium - IV
  if transaction_type = 'OPEN' then 
     set tv = oq_bid_avg - iv;
  elseif transaction_type = 'CLOSE' then
	 set tv = oq_ask_avg - iv;
  else
	set tv = 1/0;
  end if;
  RETURN round(tv,3);
END$$
DELIMITER ;