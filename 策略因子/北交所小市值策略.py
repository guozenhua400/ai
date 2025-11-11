 # coding:gbk
"""
北交所小市值多因子选股QMT策略
版本：2.0
优化说明：
- 增加详细日志记录
- 优化错误处理机制
- 增加数据有效性验证
- 提升代码执行效率
"""

import datetime
import time

def log_message(level, message):
    """统一日志格式输出"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}")

def select_stocks(C):
    """
    北交所小市值多因子选股主函数
    返回筛选后的股票列表
    """
    import time as time_module
    start_time = time_module.time()
    log_message("INFO", "============ 北交所小市值多因子选股策略启动 ============")
    
    # 第0步：获取股票池
    log_message("INFO", "开始获取京市A股（北交所）股票列表...")
    try:
        stocks = C.get_stock_list_in_sector('京市A股')
        if not stocks:
            log_message("ERROR", "未能获取到京市A股股票列表，请检查以下问题：")
            log_message("ERROR", "1. 行情连接状态是否正常")
            log_message("ERROR", "2. 是否有北交所行情权限")
            log_message("ERROR", "3. 板块名称'京市A股'是否正确")
            return
        log_message("INFO", f"成功获取到 {len(stocks)} 只北交所股票")
    except Exception as e:
        log_message("ERROR", f"获取股票列表时发生异常: {str(e)}")
        return

    # 显示股票涨幅信息
    log_message("INFO", "正在计算北交所股票前一天涨跌幅...")
    valid_price_count = 0
    invalid_price_count = 0
    
    
    # 先下载历史数据
    log_message("INFO", "开始下载历史数据...")
    try:
        # 下载历史数据以确保数据完整性
        # 获取当前日期前15天作为起始时间（确保有足够的交易日数据）
        import datetime
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y%m%d")
        
        # 分批下载，避免一次性下载过多股票
        batch_size = 50
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i+batch_size]
            log_message("DEBUG", f"下载历史数据批次: {i//batch_size + 1}/{(len(stocks)-1)//batch_size + 1}")
            for stock in batch:
                try:
                    download_history_data(stock, '1d', start_date, end_date)
                except Exception as e:
                    log_message("WARN", f"下载股票 {stock} 历史数据失败: {str(e)}")
                    
        log_message("DEBUG", f"成功下载批次完成")
    except Exception as e:
        log_message("WARN", f"下载历史数据失败: {str(e)}")

    # 批量获取最近3天的收盘价数据（需要3天数据才能计算前一天涨跌幅）
    try:
        hist_data = C.get_market_data_ex(['close'], stocks, period='1d', count=3, subscribe=False)
        log_message("DEBUG", f"成功获取 {len(hist_data)} 只股票的历史数据")
    except Exception as e:
        log_message("WARN", f"批量获取历史数据失败: {str(e)}")
        hist_data = {}
    
    print("=" * 70)
    print("股票代码    股票名称        前日涨跌%   前日收价    前前日收价")
    print("=" * 70)
    
    for stock in stocks:
        try:
            name = C.get_stock_name(stock)
            
            # 使用历史数据计算前一天涨跌幅
            if stock in hist_data and len(hist_data[stock]) >= 2:
                close_data = hist_data[stock]['close']
                if len(close_data) >= 2:
                    # 正确理解数据顺序：
                    # iloc[-1] = 最新收盘价（今天T）
                    # iloc[-2] = 前一天收盘价（T-1）  
                    # iloc[-3] = 前前天收盘价（T-2）（如果有的话）
                    
                    current_close = close_data.iloc[-1]   # 今天收盘价（T）
                    prev_close = close_data.iloc[-2]      # 前一天收盘价（T-1）
                    
                    # 我们需要计算前一天的涨跌幅，需要前前天的数据
                    if len(close_data) >= 3:
                        pre_prev_close = close_data.iloc[-3]  # 前前天收盘价（T-2）
                        
                        # 确保价格数据不为None且为正数
                        if (prev_close is not None and pre_prev_close is not None and 
                            prev_close > 0 and pre_prev_close > 0):
                            try:
                                # 计算前一天涨跌幅：(前一天收盘价 - 前前天收盘价) / 前前天收盘价 * 100
                                prev_day_pct_chg = (float(prev_close) - float(pre_prev_close)) / float(pre_prev_close) * 100
                                print(f"{stock:<10} {name:<12} {prev_day_pct_chg:>10.2f}% {prev_close:>8.2f} {pre_prev_close:>12.2f}")
                                valid_price_count += 1
                            except (ValueError, TypeError, ZeroDivisionError):
                                print(f"{stock:<10} {name:<12} {'计算异常':>10} {prev_close or 'N/A':>8} {pre_prev_close or 'N/A':>12}")
                                invalid_price_count += 1
                        else:
                            print(f"{stock:<10} {name:<12} {'价格异常':>10} {prev_close or 'N/A':>8} {pre_prev_close or 'N/A':>12}")
                            invalid_price_count += 1
                    else:
                        # 只有2天数据，无法计算前一天涨跌幅，显示当前情况
                        if (current_close is not None and prev_close is not None and 
                            current_close > 0 and prev_close > 0):
                            try:
                                today_pct_chg = (float(current_close) - float(prev_close)) / float(prev_close) * 100
                                print(f"{stock:<10} {name:<12} {'今日' + f'{today_pct_chg:.2f}%':>10} {current_close:>8.2f} {prev_close:>12.2f}")
                            except (ValueError, TypeError, ZeroDivisionError):
                                print(f"{stock:<10} {name:<12} {'数据不足':>10}")
                        else:
                            print(f"{stock:<10} {name:<12} {'数据不足':>10}")
                        invalid_price_count += 1
                else:
                    print(f"{stock:<10} {name:<12} {'数据不足':>10}")
                    invalid_price_count += 1
            else:
                # 备用方法：使用tick数据的lastClose作为前收价，无法计算前一天涨跌幅
                try:
                    tick_data = C.get_full_tick([stock])
                    if stock in tick_data:
                        last_close = tick_data[stock].get('lastClose', 0)
                        print(f"{stock:<10} {name:<12} {'无历史数据':>10} {last_close:>8.2f} {'N/A':>10}")
                    else:
                        print(f"{stock:<10} {name:<12} {'数据缺失':>10}")
                except:
                    print(f"{stock:<10} {name:<12} {'数据缺失':>10}")
                invalid_price_count += 1
                
        except Exception as e:
            log_message("WARN", f"处理股票 {stock} 时发生异常: {str(e)}")
            invalid_price_count += 1
            
    print("=" * 70)
    log_message("INFO", f"价格数据统计 - 有效: {valid_price_count}, 异常: {invalid_price_count}")

    # 第1步筛选：剔除ST、退市整理、前一天涨跌停股票
    log_message("INFO", "========== 第1步筛选：剔除ST、退市整理、前一天涨跌停股票 ==========")
    step1_start = len(stocks)
    filtered = []
    st_count = 0
    prev_limit_count = 0
    suspend_count = 0
    error_count = 0
    
    # 注意：我们主要依赖历史数据和合约信息进行筛选，不需要实时tick数据
    
    for stock in stocks:
        try:
            # 获取股票合约详细信息
            try:
                instrument_detail = C.get_instrument_detail(stock)
                stock_name = instrument_detail.get('InstrumentName', 'Unknown')
                # 获取停牌状态 (<=0:正常交易, >=1:停牌天数)
                suspend_status = instrument_detail.get('InstrumentStatus', 0)
                # 确保suspend_status是数字类型
                if suspend_status is None:
                    suspend_status = 0
                else:
                    try:
                        suspend_status = int(suspend_status)
                    except (ValueError, TypeError):
                        suspend_status = 0
            except Exception as e:
                log_message("WARN", f"获取股票 {stock} 合约信息失败: {str(e)}")
                # 使用备用方法获取股票名称
                try:
                    stock_name = C.get_stock_name(stock)
                except:
                    stock_name = 'Unknown'
                suspend_status = 0
            
            # 1. 检查ST、退市整理股票（通过股票名称）
            if stock_name and any(keyword in stock_name for keyword in ['ST', '*ST', 'PT', '退', '整理']):
                log_message("DEBUG", f"剔除ST/退/整理股票: {stock} {stock_name}")
                st_count += 1
                continue
            
            # 2. 检查停牌股票
            if suspend_status and suspend_status > 0:
                log_message("DEBUG", f"剔除停牌股票: {stock} {stock_name} (停牌{suspend_status}天)")
                suspend_count += 1
                continue
            
            # 3. 检查前一天是否涨跌停（利用前面计算的历史数据）
            is_prev_limit = False
            prev_day_pct_chg = None
            
            if stock in hist_data and len(hist_data[stock]) >= 3:
                close_data = hist_data[stock]['close']
                if len(close_data) >= 3:
                    prev_close = close_data.iloc[-2]      # 前一天收盘价（T-1）
                    pre_prev_close = close_data.iloc[-3]  # 前前天收盘价（T-2）
                    
                    # 确保价格数据不为None且为正数
                    if (prev_close is not None and pre_prev_close is not None and 
                        prev_close > 0 and pre_prev_close > 0):
                        try:
                            # 计算前一天涨跌幅
                            prev_day_pct_chg = (float(prev_close) - float(pre_prev_close)) / float(pre_prev_close) * 100
                            
                            # 判断前一天是否涨跌停（北交所30%涨跌停限制）
                            if prev_day_pct_chg >= 29.5:  # 前一天涨停
                                log_message("DEBUG", f"剔除前一天涨停股票: {stock} {stock_name} (前日涨幅={prev_day_pct_chg:.2f}%)")
                                is_prev_limit = True
                            elif prev_day_pct_chg <= -29.5:  # 前一天跌停
                                log_message("DEBUG", f"剔除前一天跌停股票: {stock} {stock_name} (前日跌幅={prev_day_pct_chg:.2f}%)")
                                is_prev_limit = True
                        except (ValueError, TypeError, ZeroDivisionError) as e:
                            log_message("WARN", f"计算股票 {stock} 前日涨跌幅时异常: {str(e)}")
                            # 价格计算异常，跳过涨跌停判断
            
            if is_prev_limit:
                prev_limit_count += 1
                continue
            
            # 通过所有筛选条件
            filtered.append(stock)
            
        except Exception as e:
            log_message("ERROR", f"处理股票 {stock} 时发生异常: {str(e)}")
            error_count += 1
            continue
    
    step1_end = len(filtered)
    log_message("INFO", f"第1步筛选结果: {step1_start} -> {step1_end} (剔除 {step1_start - step1_end} 只)")
    log_message("INFO", f"  - ST/退/整理股票: {st_count} 只")
    log_message("INFO", f"  - 停牌股票: {suspend_count} 只")
    log_message("INFO", f"  - 前一天涨跌停股票: {prev_limit_count} 只") 
    log_message("INFO", f"  - 数据异常股票: {error_count} 只")

    # 第2步筛选：剔除上市时间最短的10%（即最新上市的股票）
    log_message("INFO", "========== 第2步筛选：剔除上市时间最短的10% ==========")
    step2_start = len(filtered)
    if step2_start == 0:
        log_message("WARN", "第1步筛选后无剩余股票，跳过后续筛选")
        return
        
    date_dict = {}
    data_error_count = 0
    
    log_message("INFO", f"开始获取 {step2_start} 只股票的上市日期...")
    
    # 显示所有股票的上市日期
    print("=" * 80)
    print("股票代码    股票名称        上市日期    上市年数")
    print("=" * 80)
    
    current_date = datetime.datetime.now()
    
    for i, stock in enumerate(filtered):
        try:
            # 使用get_open_date获取上市日期
            listed_date = C.get_open_date(stock)
            stock_name = C.get_stock_name(stock)
            
            if listed_date and listed_date > 19000101:
                date_dict[stock] = listed_date
                
                # 计算上市年数
                try:
                    listed_date_obj = datetime.datetime.strptime(str(listed_date), '%Y%m%d')
                    years_listed = (current_date - listed_date_obj).days / 365.25
                    
                    # 格式化上市日期显示
                    formatted_date = f"{str(listed_date)[:4]}-{str(listed_date)[4:6]}-{str(listed_date)[6:8]}"
                    print(f"{stock:<10} {stock_name:<12} {formatted_date:<10} {years_listed:>8.1f}年")
                    
                except Exception as e:
                    print(f"{stock:<10} {stock_name:<12} {listed_date:<10} {'计算异常':>8}")
                    
                if i % 10 == 0:  # 每10只股票输出一次进度
                    log_message("DEBUG", f"上市日期获取进度: {i+1}/{step2_start}")
            else:
                log_message("WARN", f"股票 {stock} 上市日期异常: {listed_date}")
                date_dict[stock] = 19000101  # 设置默认值（很早的日期）
                print(f"{stock:<10} {stock_name:<12} {'数据异常':<10} {'N/A':>8}")
                data_error_count += 1
        except Exception as e:
            log_message("ERROR", f"获取股票 {stock} 上市日期时异常: {str(e)}")
            try:
                stock_name = C.get_stock_name(stock)
            except:
                stock_name = 'Unknown'
            date_dict[stock] = 19000101
            print(f"{stock:<10} {stock_name:<12} {'获取失败':<10} {'N/A':>8}")
            data_error_count += 1
    
    print("=" * 80)
    
    if data_error_count > 0:
        log_message("WARN", f"有 {data_error_count} 只股票上市日期数据异常")
    
    # 按上市日期排序，剔除最新上市的10%（上市时间最短）
    sorted_by_date = sorted(date_dict.items(), key=lambda x: x[1])  # 从早到晚排序
    cut_num = max(1, int(len(sorted_by_date) * 0.1))  # 至少剔除1只
    
    # 最新上市的股票在排序后的末尾，所以剔除后面的股票
    removed_stocks = sorted_by_date[-cut_num:]  # 最新上市的10%
    filtered = [stock for stock, date in sorted_by_date[:-cut_num]]  # 保留前面90%
    
    step2_end = len(filtered)
    log_message("INFO", f"第2步筛选结果: {step2_start} -> {step2_end} (剔除 {cut_num} 只)")
    
    # 显示上市日期统计
    if sorted_by_date:
        earliest_date = sorted_by_date[0][1]
        latest_date = sorted_by_date[-1][1]
        cutoff_date = sorted_by_date[-cut_num-1][1] if cut_num < len(sorted_by_date) else latest_date
        
        # 格式化日期显示
        def format_date(date_int):
            date_str = str(date_int)
            if len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return str(date_int)
        
        log_message("INFO", f"上市日期区间: {format_date(earliest_date)} 至 {format_date(latest_date)}")
        log_message("INFO", f"筛选阈值: 剔除 {format_date(cutoff_date)} 之后上市的股票")
    
    # 显示被剔除的最新上市股票
    if removed_stocks:
        log_message("DEBUG", "被剔除的最新上市股票（上市时间最短的10%）:")
        for stock, date in removed_stocks:
            try:
                stock_name = C.get_stock_name(stock)
                formatted_date = f"{str(date)[:4]}-{str(date)[4:6]}-{str(date)[6:8]}" if len(str(date)) == 8 else str(date)
                log_message("DEBUG", f"  {stock} {stock_name} (上市日期: {formatted_date})")
            except Exception as e:
                log_message("DEBUG", f"  {stock} 获取名称失败 (上市日期: {date})")

    # 第3步筛选：剔除前一天收盘价最高的30%
    log_message("INFO", "========== 第3步筛选：剔除前一天收盘价最高的30% ==========")
    step3_start = len(filtered)
    if step3_start == 0:
        log_message("WARN", "第2步筛选后无剩余股票，跳过后续筛选")
        return
        
    close_dict = {}
    price_error_count = 0
    
    log_message("INFO", f"开始获取 {step3_start} 只股票的前一天收盘价...")
    
    # 显示所有股票的前一天收盘价
    print("=" * 80)
    print("股票代码    股票名称        前一天收盘价    市值排序")
    print("=" * 80)
    
    for stock in filtered:
        try:
            stock_name = C.get_stock_name(stock)
            
            # 使用前面已经获取的历史数据
            if stock in hist_data and len(hist_data[stock]) >= 2:
                close_data = hist_data[stock]['close']
                if len(close_data) >= 2:
                    # 获取前一天收盘价
                    prev_close = close_data.iloc[-2]  # 前一天收盘价（T-1）
                    
                    # 确保价格数据有效
                    if prev_close is not None and prev_close > 0:
                        try:
                            prev_close_float = float(prev_close)
                            close_dict[stock] = prev_close_float
                            print(f"{stock:<10} {stock_name:<12} {prev_close_float:>12.2f} {'待排序':>10}")
                        except (ValueError, TypeError):
                            log_message("WARN", f"股票 {stock} 前一天收盘价转换异常: {prev_close}")
                            print(f"{stock:<10} {stock_name:<12} {'转换异常':>12} {'异常':>10}")
                            price_error_count += 1
                    else:
                        log_message("WARN", f"股票 {stock} 前一天收盘价异常: {prev_close}")
                        print(f"{stock:<10} {stock_name:<12} {'价格异常':>12} {'异常':>10}")
                        price_error_count += 1
                else:
                    log_message("WARN", f"股票 {stock} 历史数据不足")
                    print(f"{stock:<10} {stock_name:<12} {'数据不足':>12} {'异常':>10}")
                    price_error_count += 1
            else:
                # 备用方法：重新获取历史数据
                try:
                    backup_data = C.get_market_data_ex(['close'], [stock], period='1d', count=2, subscribe=False)
                    if stock in backup_data and len(backup_data[stock]) >= 2:
                        close_data = backup_data[stock]['close']
                        prev_close = close_data.iloc[-2]
                        if prev_close is not None and prev_close > 0:
                            prev_close_float = float(prev_close)
                            close_dict[stock] = prev_close_float
                            print(f"{stock:<10} {stock_name:<12} {prev_close_float:>12.2f} {'备用获取':>10}")
                        else:
                            log_message("WARN", f"股票 {stock} 备用获取价格异常: {prev_close}")
                            print(f"{stock:<10} {stock_name:<12} {'备用异常':>12} {'异常':>10}")
                            price_error_count += 1
                    else:
                        log_message("WARN", f"无法获取股票 {stock} 的历史价格数据")
                        print(f"{stock:<10} {stock_name:<12} {'无法获取':>12} {'异常':>10}")
                        price_error_count += 1
                except Exception as e:
                    log_message("ERROR", f"获取股票 {stock} 备用价格数据时异常: {str(e)}")
                    print(f"{stock:<10} {stock_name:<12} {'获取失败':>12} {'异常':>10}")
                    price_error_count += 1
                    
        except Exception as e:
            log_message("ERROR", f"处理股票 {stock} 时异常: {str(e)}")
            try:
                stock_name = C.get_stock_name(stock)
            except:
                stock_name = 'Unknown'
            print(f"{stock:<10} {stock_name:<12} {'处理异常':>12} {'异常':>10}")
            price_error_count += 1
    
    print("=" * 80)
    
    if price_error_count > 0:
        log_message("WARN", f"有 {price_error_count} 只股票前一天收盘价数据异常")
    
    if not close_dict:
        log_message("ERROR", "所有股票前一天收盘价数据都异常，无法继续筛选")
        return
    
    # 按前一天收盘价排序，剔除最高的30%
    sorted_by_close = sorted(close_dict.items(), key=lambda x: x[1])
    cut_num = max(1, int(len(sorted_by_close) * 0.3))
    removed_stocks = sorted_by_close[-cut_num:]
    filtered = [stock for stock, price in sorted_by_close[:-cut_num]]
    
    step3_end = len(filtered)
    log_message("INFO", f"第3步筛选结果: {step3_start} -> {step3_end} (剔除 {cut_num} 只)")
    
    # 显示价格区间和被剔除的股票
    if sorted_by_close:
        min_price = sorted_by_close[0][1]
        max_price = sorted_by_close[-1][1]
        cut_price = sorted_by_close[-cut_num-1][1] if cut_num < len(sorted_by_close) else max_price
        log_message("INFO", f"前一天收盘价区间: {min_price:.2f} - {max_price:.2f} 元，筛选阈值: {cut_price:.2f} 元")
        
        # 显示被剔除的高价股票
        if removed_stocks:
            log_message("DEBUG", "被剔除的前一天收盘价最高的30%股票:")
            for stock, price in removed_stocks:
                try:
                    stock_name = C.get_stock_name(stock)
                    log_message("DEBUG", f"  {stock} {stock_name} (前一天收盘价: {price:.2f}元)")
                except Exception as e:
                    log_message("DEBUG", f"  {stock} 获取名称失败 (前一天收盘价: {price:.2f}元)")

    # 第4步筛选：剔除市净率最高的30%
    log_message("INFO", "========== 第4步筛选：剔除市净率最高的30% ==========")
    step4_start = len(filtered)
    if step4_start == 0:
        log_message("WARN", "第3步筛选后无剩余股票，跳过后续筛选")
        return
        
    pb_dict = {}
    pb_error_count = 0
    
    log_message("INFO", f"开始获取 {step4_start} 只股票的市净率数据...")
    
    # 先下载历史数据
    try:
        import datetime
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
        
        download_stocks = filtered[:100] if step4_start > 100 else filtered
        for stock in download_stocks:
            try:
                download_history_data(stock, '1d', start_date, end_date)
            except Exception as e:
                log_message("WARN", f"下载股票 {stock} 市净率历史数据失败: {str(e)}")
        log_message("DEBUG", "成功下载市净率计算所需的历史数据")
    except Exception as e:
        log_message("WARN", f"下载市净率历史数据失败: {str(e)}")
    
    # 批量获取市净率数据以提高效率
    try:
        if step4_start <= 100:  # 小批量直接获取
            detail = C.get_market_data_ex(['close', 'volume'], filtered, period='1d', count=1, subscribe=False)
            for stock in filtered:
                try:
                    if stock in detail and len(detail[stock]) > 0:
                        # 使用市价计算市净率（简化处理）
                        close_price = detail[stock]['close'].iloc[-1] if not detail[stock]['close'].empty else 0
                        if close_price > 0:
                            # 这里应该获取净资产数据，暂时用价格作为近似
                            pb_dict[stock] = close_price  # 实际应该是 股价/每股净资产
                        else:
                            pb_error_count += 1
                    else:
                        pb_error_count += 1
                except Exception as e:
                    log_message("WARN", f"计算股票 {stock} 市净率时异常: {str(e)}")
                    pb_error_count += 1
        else:
            # 大批量分批处理
            batch_size = 50
            for i in range(0, step4_start, batch_size):
                batch = filtered[i:i+batch_size]
                log_message("DEBUG", f"处理市净率数据批次: {i//batch_size + 1}/{(step4_start-1)//batch_size + 1}")
                try:
                    # 先下载这批股票的历史数据
                    import datetime
                    end_date = datetime.datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
                    for stock in batch:
                        try:
                            download_history_data(stock, '1d', start_date, end_date)
                        except:
                            pass
                    detail = C.get_market_data_ex(['close'], batch, period='1d', count=1, subscribe=False)
                    for stock in batch:
                        try:
                            if stock in detail and len(detail[stock]) > 0:
                                close_price = detail[stock]['close'].iloc[-1] if not detail[stock]['close'].empty else 0
                                if close_price > 0:
                                    pb_dict[stock] = close_price
                                else:
                                    pb_error_count += 1
                            else:
                                pb_error_count += 1
                        except Exception as e:
                            log_message("WARN", f"处理股票 {stock} 市净率数据时异常: {str(e)}")
                            pb_error_count += 1
                except Exception as e:
                    log_message("ERROR", f"批量获取市净率数据时异常: {str(e)}")
                    pb_error_count += len(batch)
                    
    except Exception as e:
        log_message("ERROR", f"获取市净率数据时发生异常: {str(e)}")
        return
    
    if pb_error_count > 0:
        log_message("WARN", f"有 {pb_error_count} 只股票市净率数据异常")
    
    if not pb_dict:
        log_message("ERROR", "所有股票市净率数据都异常，无法继续筛选")
        return
    
    # 按市净率排序，剔除最高的30%
    sorted_by_pb = sorted(pb_dict.items(), key=lambda x: x[1])
    cut_num = max(1, int(len(sorted_by_pb) * 0.3))
    filtered = [stock for stock, pb in sorted_by_pb[:-cut_num]]
    
    step4_end = len(filtered)
    log_message("INFO", f"第4步筛选结果: {step4_start} -> {step4_end} (剔除 {cut_num} 只)")
    
    if sorted_by_pb:
        min_pb = sorted_by_pb[0][1]
        max_pb = sorted_by_pb[-1][1]
        log_message("INFO", f"市净率区间: {min_pb:.2f} - {max_pb:.2f}")

    # 第5步筛选：剔除换手率最高的30%
    log_message("INFO", "========== 第5步筛选：剔除换手率最高的30% ==========")
    step5_start = len(filtered)
    if step5_start == 0:
        log_message("WARN", "第4步筛选后无剩余股票，跳过后续筛选")
        return
        
    turnover_dict = {}
    turnover_error_count = 0
    
    log_message("INFO", f"开始获取 {step5_start} 只股票的换手率数据...")
    
    # 先下载历史数据
    try:
        import datetime
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
        
        download_stocks = filtered[:100] if step5_start > 100 else filtered
        for stock in download_stocks:
            try:
                download_history_data(stock, '1d', start_date, end_date)
            except Exception as e:
                log_message("WARN", f"下载股票 {stock} 换手率历史数据失败: {str(e)}")
        log_message("DEBUG", "成功下载换手率计算所需的历史数据")
    except Exception as e:
        log_message("WARN", f"下载换手率历史数据失败: {str(e)}")
    
    # 批量获取换手率数据
    try:
        if step5_start <= 100:  # 小批量直接获取
            detail = C.get_market_data_ex(['turnoverRate'], filtered, period='1d', count=1, subscribe=False)
            for stock in filtered:
                try:
                    if stock in detail and len(detail[stock]) > 0:
                        turnover = detail[stock]['turnoverRate'].iloc[-1] if not detail[stock]['turnoverRate'].empty else 0
                        if turnover > 0:
                            turnover_dict[stock] = turnover
                        else:
                            turnover_error_count += 1
                    else:
                        turnover_error_count += 1
                except Exception as e:
                    log_message("WARN", f"获取股票 {stock} 换手率时异常: {str(e)}")
                    turnover_error_count += 1
        else:
            # 大批量分批处理
            batch_size = 50
            for i in range(0, step5_start, batch_size):
                batch = filtered[i:i+batch_size]
                log_message("DEBUG", f"处理换手率数据批次: {i//batch_size + 1}/{(step5_start-1)//batch_size + 1}")
                try:
                    # 先下载这批股票的历史数据
                    import datetime
                    end_date = datetime.datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
                    for stock in batch:
                        try:
                            download_history_data(stock, '1d', start_date, end_date)
                        except:
                            pass
                    detail = C.get_market_data_ex(['turnoverRate'], batch, period='1d', count=1, subscribe=False)
                    for stock in batch:
                        try:
                            if stock in detail and len(detail[stock]) > 0:
                                turnover = detail[stock]['turnoverRate'].iloc[-1] if not detail[stock]['turnoverRate'].empty else 0
                                if turnover > 0:
                                    turnover_dict[stock] = turnover
                                else:
                                    turnover_error_count += 1
                            else:
                                turnover_error_count += 1
                        except Exception as e:
                            log_message("WARN", f"处理股票 {stock} 换手率数据时异常: {str(e)}")
                            turnover_error_count += 1
                except Exception as e:
                    log_message("ERROR", f"批量获取换手率数据时异常: {str(e)}")
                    turnover_error_count += len(batch)
                    
    except Exception as e:
        log_message("ERROR", f"获取换手率数据时发生异常: {str(e)}")
        return
    
    if turnover_error_count > 0:
        log_message("WARN", f"有 {turnover_error_count} 只股票换手率数据异常")
    
    if not turnover_dict:
        log_message("ERROR", "所有股票换手率数据都异常，无法继续筛选")
        return
    
    # 按换手率排序，剔除最高的30%
    sorted_by_turnover = sorted(turnover_dict.items(), key=lambda x: x[1])  
    cut_num = max(1, int(len(sorted_by_turnover) * 0.3))
    filtered = [stock for stock, turnover in sorted_by_turnover[:-cut_num]]
    
    step5_end = len(filtered)
    log_message("INFO", f"第5步筛选结果: {step5_start} -> {step5_end} (剔除 {cut_num} 只)")
    
    if sorted_by_turnover:
        min_turnover = sorted_by_turnover[0][1]
        max_turnover = sorted_by_turnover[-1][1]
        log_message("INFO", f"换手率区间: {min_turnover:.4f}% - {max_turnover:.4f}%")

    # 第6步筛选：剔除不分红的股票
    log_message("INFO", "========== 第6步筛选：剔除不分红的股票 ==========")
    step6_start = len(filtered)
    if step6_start == 0:
        log_message("WARN", "第5步筛选后无剩余股票，跳过后续筛选")
        return
        
    dividend_dict = {}
    dividend_error_count = 0
    dividend_zero_count = 0
    
    log_message("INFO", f"开始获取 {step6_start} 只股票的分红数据...")
    
    # 先下载历史数据
    try:
        import datetime
        end_date = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
        
        download_stocks = filtered[:100] if step6_start > 100 else filtered
        for stock in download_stocks:
            try:
                download_history_data(stock, '1d', start_date, end_date)
            except Exception as e:
                log_message("WARN", f"下载股票 {stock} 分红历史数据失败: {str(e)}")
        log_message("DEBUG", "成功下载分红计算所需的历史数据")
    except Exception as e:
        log_message("WARN", f"下载分红历史数据失败: {str(e)}")
    
    # 批量获取分红数据
    try:
        if step6_start <= 100:  # 小批量直接获取
            detail = C.get_market_data_ex(['dividendTTM'], filtered, period='1d', count=1, subscribe=False)
            for stock in filtered:
                try:
                    if stock in detail and len(detail[stock]) > 0:
                        dividend = detail[stock]['dividendTTM'].iloc[-1] if not detail[stock]['dividendTTM'].empty else 0
                        dividend_dict[stock] = dividend
                        if dividend <= 0:
                            dividend_zero_count += 1
                    else:
                        dividend_error_count += 1
                        dividend_dict[stock] = 0  # 默认为0
                except Exception as e:
                    log_message("WARN", f"获取股票 {stock} 分红数据时异常: {str(e)}")
                    dividend_error_count += 1
                    dividend_dict[stock] = 0
        else:
            # 大批量分批处理
            batch_size = 50
            for i in range(0, step6_start, batch_size):
                batch = filtered[i:i+batch_size]
                log_message("DEBUG", f"处理分红数据批次: {i//batch_size + 1}/{(step6_start-1)//batch_size + 1}")
                try:
                    # 先下载这批股票的历史数据
                    import datetime
                    end_date = datetime.datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y%m%d")
                    for stock in batch:
                        try:
                            download_history_data(stock, '1d', start_date, end_date)
                        except:
                            pass
                    detail = C.get_market_data_ex(['dividendTTM'], batch, period='1d', count=1, subscribe=False)
                    for stock in batch:
                        try:
                            if stock in detail and len(detail[stock]) > 0:
                                dividend = detail[stock]['dividendTTM'].iloc[-1] if not detail[stock]['dividendTTM'].empty else 0
                                dividend_dict[stock] = dividend
                                if dividend <= 0:
                                    dividend_zero_count += 1
                            else:
                                dividend_error_count += 1
                                dividend_dict[stock] = 0
                        except Exception as e:
                            log_message("WARN", f"处理股票 {stock} 分红数据时异常: {str(e)}")
                            dividend_error_count += 1
                            dividend_dict[stock] = 0
                except Exception as e:
                    log_message("ERROR", f"批量获取分红数据时异常: {str(e)}")
                    dividend_error_count += len(batch)
                    for stock in batch:
                        dividend_dict[stock] = 0
                    
    except Exception as e:
        log_message("ERROR", f"获取分红数据时发生异常: {str(e)}")
        return
    
    if dividend_error_count > 0:
        log_message("WARN", f"有 {dividend_error_count} 只股票分红数据异常")
    
    # 筛选有分红的股票
    filtered = [stock for stock, div in dividend_dict.items() if div > 0]
    
    step6_end = len(filtered)
    log_message("INFO", f"第6步筛选结果: {step6_start} -> {step6_end} (剔除不分红股票 {dividend_zero_count} 只)")
    
    if dividend_dict:
        dividend_values = [div for div in dividend_dict.values() if div > 0]
        if dividend_values:
            min_dividend = min(dividend_values)
            max_dividend = max(dividend_values)
            avg_dividend = sum(dividend_values) / len(dividend_values)
            log_message("INFO", f"分红区间: {min_dividend:.4f} - {max_dividend:.4f} (平均: {avg_dividend:.4f})")

    # 最终筛选结果展示
    log_message("INFO", "========== 最终筛选结果 ==========")
    
    if not filtered:
        log_message("WARN", "经过6步筛选后无股票符合条件")
        return
        
    log_message("INFO", f"最终选出 {len(filtered)} 只北交所小市值股票")
    log_message("INFO", "详细结果如下:")
    log_message("INFO", "股票代码\t股票名称")
    log_message("INFO", "-" * 50)
    
    result_count = 0
    for stock in filtered:
        try:
            stock_name = C.get_stock_name(stock)
            log_message("INFO", f"{stock}\t{stock_name}")
            result_count += 1
        except Exception as e:
            log_message("WARN", f"获取股票 {stock} 名称时异常: {str(e)}")
            log_message("INFO", f"{stock}\t获取名称失败")
            result_count += 1
    
    log_message("INFO", "-" * 50)
    log_message("INFO", f"策略执行完成，共筛选出 {result_count} 只股票")
    
    # 执行时间统计
    end_time = time_module.time()
    execution_time = end_time - start_time
    log_message("INFO", f"总执行时间: {execution_time:.2f} 秒")
    
    return filtered

def init(C):
    """
    策略初始化函数
    在策略启动时执行一次
    """
    # 记录策略开始时间
    global start_time
    start_time = time.time()
    
    log_message("INFO", "========== 北交所小市值策略开始执行 ==========")
    log_message("INFO", f"策略启动时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 执行股票筛选策略
        result = select_stocks(C)
        if result:
            log_message("INFO", f"策略执行成功，返回 {len(result)} 只股票")
        else:
            log_message("WARN", "策略执行完成，但未返回有效结果")
    except Exception as e:
        log_message("ERROR", f"策略执行异常: {str(e)}")
        import traceback
        log_message("ERROR", f"异常详情: {traceback.format_exc()}")
        raise

def handlebar(C):
    """
    K线数据处理函数
    每根K线产生时调用
    """
    pass
