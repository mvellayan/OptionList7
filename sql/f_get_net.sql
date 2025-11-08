DELIMITER $$
drop function if exists get_net$$
CREATE DEFINER=`root`@`localhost` FUNCTION `get_net`(
	l_op_sq_bid double, l_op_sq_ask double, l_op_oq_bid double, l_op_oq_ask double,
    l_cl_sq_bid double, l_cl_sq_ask double, l_cl_oq_bid double, l_cl_oq_ask double,
    net_type varchar(10)) RETURNS double
    NO SQL
    DETERMINISTIC
BEGIN
  DECLARE r_net double;
  # https://www.ig.com/en/trading-strategies/option-pricing--the-intrinsic-and-time-values-of-options-explain-220111

  if net_type = 'NET' then
     set r_net = (- l_op_sq_ask + l_op_oq_bid + l_cl_sq_bid - l_cl_oq_ask);
  elseif net_type = 'STK' then
     set r_net = (- l_op_sq_ask + l_cl_sq_bid );
  elseif net_type = 'OPT' then
     set r_net = (l_op_oq_bid - l_cl_oq_ask);
  else
	set r_net = null;
  end if;
  RETURN round(r_net,3);
END$$
DELIMITER ;