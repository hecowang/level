"""
后台任务模块
用于在后台获取和保存成分股数据及交易数据
"""
import asyncio
import baostock as bs
from app.services.database import (
    save_index_stocks, init_db, get_all_stock_codes,
    save_stock_daily_data, get_stock_data_last_update_date
)
from app.utils.baostock_wrapper import BaoStockWrapper
from typing import Optional, Callable, Any
import logging
from datetime import datetime, timedelta
import pandas as pd
import time

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3  # 最大重试次数
RETRY_DELAY = 2  # 重试延迟（秒）


def retry_on_failure(func: Callable, max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY, *args, **kwargs) -> Any:
    """
    重试装饰器函数，在失败时自动重试
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        *args, **kwargs: 传递给函数的参数
    
    Returns:
        函数执行结果
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (attempt + 1)  # 指数退避
                logger.warning(f"第 {attempt + 1} 次尝试失败: {str(e)}，{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"重试 {max_retries} 次后仍然失败: {str(e)}")
                raise last_exception
    raise last_exception


async def fetch_and_save_hs300():
    """获取并保存沪深300成分股"""
    try:
        logger.info("开始获取沪深300成分股...")
        
        # baostock是同步库，需要在异步环境中运行
        loop = asyncio.get_event_loop()
        
        # 在后台线程中执行同步操作，带重试逻辑
        # 每次重试都会重新创建 BaoStockWrapper（重新登录）
        def fetch_hs300():
            with BaoStockWrapper() as bs_wrapper:
                rs = bs.query_hs300_stocks()
                if rs.error_code != "0":
                    raise Exception(f"查询失败: {rs.error_msg}")
                stocks = []
                fields = rs.fields if hasattr(rs, 'fields') else []
                while (rs.error_code == '0') & rs.next():
                    stocks.append(rs.get_row_data())
                return stocks, fields
        
        # 使用重试逻辑，每次重试都会重新创建 session
        stocks, fields = await loop.run_in_executor(
            None, 
            lambda: retry_on_failure(fetch_hs300)
        )
        
        # 保存到数据库
        await save_index_stocks('hs300', stocks, fields)
        
        logger.info(f"成功保存沪深300成分股，共 {len(stocks)} 只股票")
        return len(stocks)
    except Exception as e:
        logger.error(f"获取沪深300成分股失败: {str(e)}", exc_info=True)
        raise


async def fetch_and_save_zz500():
    """获取并保存中证500成分股"""
    try:
        logger.info("开始获取中证500成分股...")
        
        # baostock是同步库，需要在异步环境中运行
        loop = asyncio.get_event_loop()
        
        # 在后台线程中执行同步操作，带重试逻辑
        def fetch_zz500():
            with BaoStockWrapper() as bs_wrapper:
                rs = bs.query_zz500_stocks()
                if rs.error_code != "0":
                    raise Exception(f"查询失败: {rs.error_msg}")
                stocks = []
                fields = rs.fields if hasattr(rs, 'fields') else []
                while (rs.error_code == '0') & rs.next():
                    stocks.append(rs.get_row_data())
                return stocks, fields
        
        # 使用重试逻辑
        stocks, fields = await loop.run_in_executor(
            None,
            lambda: retry_on_failure(fetch_zz500)
        )
        
        # 保存到数据库
        await save_index_stocks('zz500', stocks, fields)
        
        logger.info(f"成功保存中证500成分股，共 {len(stocks)} 只股票")
        return len(stocks)
    except Exception as e:
        logger.error(f"获取中证500成分股失败: {str(e)}", exc_info=True)
        raise


async def fetch_stock_daily_data(code: str, start_date: str, end_date: str, bs_wrapper: Optional[BaoStockWrapper] = None, max_retries: int = MAX_RETRIES) -> Optional[pd.DataFrame]:
    """
    获取股票日线交易数据，带重试逻辑
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        bs_wrapper: 可选的BaoStockWrapper实例，如果提供则使用它（避免重复login）
        max_retries: 最大重试次数
    
    Returns:
        DataFrame或None
    """
    try:
        if bs_wrapper is not None:
            # 使用提供的wrapper（已登录），带重试逻辑
            def get_data():
                return bs_wrapper.get_stock_data(code, start_date, end_date)
            return retry_on_failure(get_data, max_retries=max_retries)
        else:
            # 自己创建wrapper（向后兼容），带重试逻辑
            def get_data_with_wrapper():
                with BaoStockWrapper() as wrapper:
                    return wrapper.get_stock_data(code, start_date, end_date)
            return retry_on_failure(get_data_with_wrapper, max_retries=max_retries)
    except Exception as e:
        logger.warning(f"获取股票 {code} 数据失败（已重试 {max_retries} 次）: {str(e)}")
        return None


async def fetch_and_save_stock_data(code: str, days: int = 365, bs_wrapper: Optional[BaoStockWrapper] = None):
    """
    获取并保存单只股票过去N天的交易数据
    
    Args:
        code: 股票代码
        days: 过去多少天，默认365天（1年）
        bs_wrapper: 可选的BaoStockWrapper实例，如果提供则使用它（避免重复login）
    """
    try:
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"获取股票 {code} 从 {start_date_str} 到 {end_date_str} 的数据...")
        
        # 获取数据
        df = await fetch_stock_daily_data(code, start_date_str, end_date_str, bs_wrapper)
        
        if df is None or df.empty:
            logger.warning(f"股票 {code} 没有获取到数据")
            return 0
        
        # 转换为字典列表
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        data = df.to_dict('records')
        
        # 保存到数据库
        await save_stock_daily_data(code, data)
        
        logger.info(f"成功保存股票 {code} 的数据，共 {len(data)} 条记录")
        return len(data)
    except Exception as e:
        logger.error(f"保存股票 {code} 数据失败: {str(e)}", exc_info=True)
        return 0


async def fetch_all_index_stocks():
    """获取并保存所有指数成分股"""
    try:
        logger.info("开始获取所有指数成分股...")
        
        # 初始化数据库
        await init_db()
        
        # 并发获取两个指数的数据
        results = await asyncio.gather(
            fetch_and_save_hs300(),
            fetch_and_save_zz500(),
            return_exceptions=True
        )
        
        hs300_count = results[0] if not isinstance(results[0], Exception) else 0
        zz500_count = results[1] if not isinstance(results[1], Exception) else 0
        
        logger.info(f"成分股数据获取完成 - 沪深300: {hs300_count} 只, 中证500: {zz500_count} 只")
        
        return {
            'hs300': hs300_count,
            'zz500': zz500_count
        }
    except Exception as e:
        logger.error(f"获取成分股数据失败: {str(e)}", exc_info=True)
        raise


async def fetch_all_stocks_daily_data(days: int = 365):
    """
    获取并保存所有成分股过去N天的交易数据
    在一个login session中顺序执行所有操作，避免频繁login
    
    Args:
        days: 过去多少天，默认365天（1年）
    """
    try:
        logger.info(f"开始获取所有成分股过去 {days} 天的交易数据...")
        
        # 获取所有股票代码
        codes = await get_all_stock_codes()
        
        if not codes:
            logger.warning("没有找到成分股代码，请先获取成分股列表")
            return
        
        logger.info(f"共找到 {len(codes)} 只股票，开始顺序获取交易数据（单次login）...")
        
        def fetch_data_for_all_codes():
            """获取所有股票的数据，带重试逻辑"""
            all_data = {}  # {code: data_list}
            with BaoStockWrapper() as bs_wrapper:
                for idx, code in enumerate(codes, 1):
                    try:
                        # 计算日期范围
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=days)
                        start_date_str = start_date.strftime('%Y-%m-%d')
                        end_date_str = end_date.strftime('%Y-%m-%d')
                        
                        if idx % 10 == 0 or idx == 1:
                            logger.info(f"获取第 {idx}/{len(codes)} 只股票: {code}...")
                            time.sleep(1)
                        
                        # 获取数据，带重试逻辑
                        def get_stock_data():
                            return bs_wrapper.get_stock_data(code, start_date_str, end_date_str)
                        
                        df = retry_on_failure(get_stock_data, max_retries=MAX_RETRIES)
                        
                        if df is None or df.empty:
                            continue
                        
                        # 转换为字典列表
                        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                        data = df.to_dict('records')
                        all_data[code] = data
                    except Exception as e:
                        logger.warning(f"获取股票 {code} 数据失败（已重试 {MAX_RETRIES} 次）: {str(e)}")
                        continue
            return all_data
        
        # 在后台线程中执行同步操作，获取所有数据
        loop = asyncio.get_event_loop()
        all_data = await loop.run_in_executor(None, fetch_data_for_all_codes)
        
        # 批量保存到数据库
        for code, data in all_data.items():
            await save_stock_daily_data(code, data)
        
        total_saved = sum(len(data) for data in all_data.values())
        logger.info(f"所有股票交易数据获取完成，共保存 {total_saved} 条记录")
        return total_saved
    except Exception as e:
        logger.error(f"获取股票交易数据失败: {str(e)}", exc_info=True)
        raise


async def refresh_daily_data():
    """
    刷新每日数据
    获取所有股票的最新交易数据（只获取缺失的日期）
    在一个login session中顺序执行所有操作，避免频繁login
    """
    try:
        logger.info("开始刷新每日数据...")
        
        # 获取所有股票代码
        codes = await get_all_stock_codes()
        
        if not codes:
            logger.warning("没有找到成分股代码，请先获取成分股列表")
            return
        
        # 计算需要获取的日期范围（最近30天，确保覆盖所有交易日）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"刷新日期范围: {start_date_str} 到 {end_date_str}")
        logger.info(f"共找到 {len(codes)} 只股票，开始顺序刷新（单次login）...")
        
        def fetch_refresh_data_for_all_codes():
            """获取所有股票的最新数据，带重试逻辑"""
            all_data = {}  # {code: data_list}
            with BaoStockWrapper() as bs_wrapper:
                for idx, code in enumerate(codes, 1):
                    try:
                        if idx % 10 == 0 or idx == 1:
                            logger.info(f"刷新第 {idx}/{len(codes)} 只股票: {code}...")
                        
                        # 获取最近30天的数据，带重试逻辑
                        def get_stock_data():
                            return bs_wrapper.get_stock_data(code, start_date_str, end_date_str)
                        
                        df = retry_on_failure(get_stock_data, max_retries=MAX_RETRIES)
                        
                        if df is None or df.empty:
                            continue
                        
                        # 转换为字典列表
                        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
                        data = df.to_dict('records')
                        all_data[code] = data
                    except Exception as e:
                        logger.warning(f"刷新股票 {code} 数据失败（已重试 {MAX_RETRIES} 次）: {str(e)}")
                        continue
            return all_data
        
        # 在后台线程中执行同步操作，获取所有数据
        loop = asyncio.get_event_loop()
        all_data = await loop.run_in_executor(None, fetch_refresh_data_for_all_codes)
        
        # 批量保存到数据库
        for code, data in all_data.items():
            await save_stock_daily_data(code, data)
        
        updated_count = sum(len(data) for data in all_data.values())
        logger.info(f"每日数据刷新完成，更新了 {updated_count} 条记录")
        return updated_count
    except Exception as e:
        logger.error(f"刷新每日数据失败: {str(e)}", exc_info=True)
        raise

