DELIMITER $$
drop function if exists get_exp_mins$$
CREATE DEFINER=`root`@`localhost` FUNCTION `get_exp_mins`(
	start_date datetime,
	end_date datetime) RETURNS int
    NO SQL
    DETERMINISTIC
BEGIN
	declare start_eof, new_date datetime;
    declare start_mins, max_days, ctr, days int;
    declare new_date_str varchar(10);

	# not validating start/end date for performance reasons.
	set end_date = STR_TO_DATE(concat(date_format(end_date,'%Y%m%d'), ' 16:00'),'%Y%m%d %H:%i');
    #insert into logs (log) values (concat_ws(' ', 'Params (start_date, end_date)', start_date, end_date));

	if start_date >= end_date then
		return 0;
    end if;

    set start_eof = STR_TO_DATE(concat(date_format(start_date,'%Y%m%d'), ' 16:00'),'%Y%m%d %H:%i');
	# insert into logs (log) values (concat_ws(' ', 'start_eof', start_eof));

	if dayname(start_date)  in ('Saturday', 'Sunday') then
		set start_mins = 0;
    else
		set start_mins = round(TIME_TO_SEC(TIMEDIFF(start_eof, start_date))/60,0);
	end if;
    #insert into logs (log) values (concat_ws(' ', 'start_mins', start_mins));

	set max_days = TIMESTAMPDIFF(DAY, start_date, end_date);
    #insert into logs (log) values (concat_ws(' ', 'max_days', max_days));

	set ctr = 0;
	set days = 0;
	while (ctr < max_days) do

        set new_date =  date_add(start_date, INTERVAL (ctr+1) DAY);
        set new_date_str =  date_format(new_date,'%Y%m%d');
        #insert into logs (log) values (concat_ws(' ', '  new_date', new_date, 'new_date_str',new_date_str, ' dow:' , dayname(new_date) ));

		if dayname(new_date) in ('Saturday', 'Sunday') then
			set days = days + 0;
            #insert into logs (log) values (concat_ws(' ', ' Dropping dow:' , dayname(new_date) ));
		elseif new_date_str in (
			'20220101','20220117','2022022','20220415','20220530','20220620','20220704','20220905','20221124','20221225',
			'20230101','20230116','20230220','20230407','20230529','20230619','2023070','20230904','20231123','20231225',
			'20240101','20240115','20240219','20240329','20240527','20240619','20240704','20240902','20241128','20241225') then
            #insert into logs (log) values (concat_ws(' ', ' Dropping Holiday:' , new_date_str, dayname(new_date) ));
			set days = days + 0;
        else
			set days = days + 1;
		end if;
		set ctr = ctr + 1;
	end while;
    return days * 390 + start_mins;
end$$
DELIMITER ;