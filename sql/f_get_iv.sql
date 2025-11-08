DELIMITER $$
drop function if exists get_iv$$
CREATE DEFINER=`root`@`localhost` FUNCTION `get_iv`(
	sq_trade_average double(9,3), 
	strike double(9,3),
	option_type varchar(1)) RETURNS double(9,3)
    DETERMINISTIC
BEGIN
  # https://www.ig.com/en/trading-strategies/option-pricing--the-intrinsic-and-time-values-of-options-explain-220111
  if option_type = 'C' then
	RETURN round(sq_trade_average - strike,3);
  else
  	RETURN round(strike - sq_trade_average, 3);
  end if;
END$$
DELIMITER ;