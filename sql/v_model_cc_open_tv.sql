CREATE 
    ALGORITHM = UNDEFINED 
    DEFINER = `root`@`localhost` 
    SQL SECURITY DEFINER
VIEW `model_cc_open_tv` AS
    SELECT 
        `ml`.`id` AS `model_id`,
        `ml`.`open_tv` AS `model_op_tv`,
        `ml`.`close_tv` AS `model_cl_tv`,
        `ol`.`con_id` AS `con_id`,
        `ol`.`local_symbol` AS `local_symbol`,
        `ol`.`expiry` AS `expiry`,
        (TO_DAYS(`ol`.`expiry`) - TO_DAYS(`sq`.`quote_date`)) AS `days_remaining`,
        `ol`.`strike` AS `strike`,
        `sq`.`quote_date` AS `op_quote_date`,
        `sq`.`trade_average` AS `op_sq_trade_avg`,
        `oq`.`bid_avg` AS `op_oq_bid_avg`,
        `oq`.`ask_avg` AS `op_oq_ask_avg`,
        GET_IV(`sq`.`trade_average`, `ol`.`strike`) AS `op_iv`,
        GET_TV(`sq`.`trade_average`,
                `ol`.`strike`,
                `oq`.`bid_avg`) AS `op_tv`
    FROM
        (((`stock_quote` `sq`
        JOIN `option_quote` `oq`)
        JOIN `option_list` `ol`)
        JOIN `model` `ml`)
    WHERE
        ((`oq`.`con_id` = `ol`.`con_id`)
            AND (`ol`.`option_type` = 'C')
            AND (`sq`.`quote_date` = `oq`.`quote_date`)
            AND (GET_TV(`sq`.`ask_avg`,
                `oq`.`bid_avg`,
                `ol`.`strike`) >= `ml`.`open_tv`)
            AND (GET_TV(`sq`.`trade_average`,
                `ol`.`strike`,
                `oq`.`bid_avg`) >= `ml`.`open_tv`))
    ORDER BY `sq`.`quote_date` , `oq`.`quote_date` , `ml`.`id` , `oq`.`con_id`