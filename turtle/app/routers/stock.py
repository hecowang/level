"""
FastAPI应用主文件
提供股票数据查询服务和MCP协议支持
"""
import baostock as bs
import pandas as pd
import asyncio

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from app.utils.logger import logger
from app.utils.baostock_wrapper import BaoStockWrapper
from fastapi import FastAPI, HTTPException, Query, APIRouter

from app.services.background_tasks import (
    fetch_all_index_stocks, 
    fetch_all_stocks_daily_data,
    refresh_daily_data
)
from app.services.database import (
    init_db, get_index_stocks, get_stock_count,
    get_stock_data_last_update_date, get_stock_daily_data_from_db,
    get_stock_name
)
from app.services.search_gold import run_search_gold_task
from app.services.search_macd_gold import run_search_macd_gold_task
from app.services import sma

router = APIRouter(
    prefix="/stock",
    tags=["stock"]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    在启动时初始化数据库并启动后台任务
    """
    # 启动时执行
    logger.info("应用启动中...")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
    
    # 启动后台任务
    async def initial_background_task():
        """初始后台任务：获取成分股列表和历史数据"""
        try:
            # 先获取成分股列表
            await fetch_all_index_stocks()
            # 然后获取所有股票过去1年的交易数据
            await fetch_all_stocks_daily_data(days=365)
        except Exception as e:
            logger.error(f"初始后台任务执行失败: {str(e)}", exc_info=True)
    
    # 定时刷新任务
    async def daily_refresh_task():
        """每天刷新数据任务，每天20点执行"""
        while True:
            try:
                # 计算到下一个20点的时间
                now = datetime.now()
                target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
                
                # 如果今天已经过了20点，就等到明天20点
                if now >= target_time:
                    target_time = target_time + timedelta(days=1)
                
                wait_seconds = (target_time - now).total_seconds()
                
                logger.info(f"等待到 {target_time.strftime('%Y-%m-%d %H:%M:%S')} 执行每日刷新任务（{wait_seconds/3600:.1f} 小时后）...")
                await asyncio.sleep(wait_seconds)
                
                logger.info("开始执行每日数据刷新...")
                # 先刷新成分股列表（可能发生变化）
                await fetch_all_index_stocks()
                # 然后刷新交易数据
                await refresh_daily_data()
                logger.info("每日数据刷新完成")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"每日刷新任务执行失败: {str(e)}", exc_info=True)
                # 出错后等待1小时再重试
                await asyncio.sleep(3600)
    
    # 在后台运行初始任务，不阻塞应用启动
    initial_task = asyncio.create_task(initial_background_task())
    # 启动每日刷新任务
    daily_task = asyncio.create_task(daily_refresh_task())
    
    yield
    
    # 关闭时执行
    logger.info("应用关闭中...")
    initial_task.cancel()
    daily_task.cancel()
    try:
        await initial_task
    except asyncio.CancelledError:
        pass
    try:
        await daily_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="股票数据查询服务",
    description="提供股票数据查询服务和MCP协议支持",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== 数据模型 ====================

class StockQueryRequest(BaseModel):
    """股票查询请求模型"""
    code: str = Field(..., description="股票代码，例如：sh.600000")
    start_date: str = Field(..., description="开始日期，格式：YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期，格式：YYYY-MM-DD")


class SMABacktestRequest(BaseModel):
    """SMA回测请求模型"""
    code: str = Field(..., description="股票代码，例如：sh.600000")
    sma1: Optional[int] = Field(None, description="短期均线周期，默认5", ge=1, le=100)
    sma2: Optional[int] = Field(None, description="长期均线周期，默认10", ge=1, le=100)
    hold_days: Optional[int] = Field(None, description="持有天数，默认21", ge=1, le=365)


class SMABacktestResponse(BaseModel):
    """SMA回测响应模型"""
    code: str
    success: bool
    message: str
    avg_profit: float = Field(..., description="平均收益")
    avg_profit_ratio: float = Field(..., description="平均收益率")
    win_prob: float = Field(..., description="胜率")
    data_count: int = Field(..., description="使用的数据条数")
    sma1: int = Field(..., description="使用的短期均线周期")
    sma2: int = Field(..., description="使用的长期均线周期")
    hold_days: int = Field(..., description="使用的持有天数")


class SMATrendResponse(BaseModel):
    """SMA趋势响应模型"""
    code: str
    name: Optional[str] = Field(None, description="股票名称")
    success: bool
    message: str
    is_upward_trend: bool = Field(..., description="是否处于上升趋势")
    current_price: float = Field(..., description="当前收盘价")
    sma5: float = Field(..., description="5日均线值")
    sma10: float = Field(..., description="10日均线值")
    sma5_trend: str = Field(..., description="SMA5趋势：上升/下降/持平")
    sma10_trend: str = Field(..., description="SMA10趋势：上升/下降/持平")
    golden_cross: bool = Field(..., description="是否处于金叉状态（SMA5在SMA10之上）")
    price_above_sma5: bool = Field(..., description="价格是否在SMA5之上")
    price_above_sma10: bool = Field(..., description="价格是否在SMA10之上")


class StockDataResponse(BaseModel):
    """股票数据响应模型"""
    code: str
    start_date: str
    end_date: str
    data: List[Dict[str, Any]]
    count: int
    source: Optional[str] = "api"


class StockIndicatorsResponse(BaseModel):
    """股票指标响应模型"""
    code: str
    name: Optional[str] = Field(None, description="股票名称")
    success: bool
    message: str
    close: float = Field(..., description="最新收盘价")
    high_20: float = Field(..., description="20日最高价")
    high_55: float = Field(..., description="55日最高价")
    low_10: float = Field(..., description="10日最低价")
    low_20: float = Field(..., description="20日最低价")
    atr_20: float = Field(..., description="20日ATR（平均真实波幅）")


class MCPTool(BaseModel):
    """MCP工具定义"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolCallRequest(BaseModel):
    """MCP工具调用请求"""
    name: str
    arguments: Dict[str, Any]


class MCPToolCallResponse(BaseModel):
    """MCP工具调用响应"""
    content: List[Dict[str, Any]]
    isError: bool = False


# ==================== 股票数据查询API ====================

@router.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票数据查询服务",
        "version": "1.0.0",
        "endpoints": {
            "数据查询": {
                "get_stock_data": "GET /api/data",
                "post_stock_data": "POST /api/data",
                "get_stock_data_from_db": "GET /api/data/db",
                "get_stock_data_recent": "GET /api/data/recent",
                "get_stock_indicators": "GET /api/indicators"
            },
            "成分股列表": {
                "get_hs300_stocks": "GET /api/list/hs300",
                "get_zz500_stocks": "GET /api/list/zz500",
                "get_hs300_stocks_from_db": "GET /api/list/hs300/db",
                "get_zz500_stocks_from_db": "GET /api/list/zz500/db"
            },
            "数据刷新": {
                "refresh_daily_data": "POST /api/refresh/daily-data"
            },
            "选股任务": {
                "search_sma_gold": "POST /api/search/sma-gold",
                "search_macd_gold": "POST /api/search/macd-gold"
            },
            "回测": {
                "sma_backtest": "POST /api/sma/backtest",
                "check_sma_trend": "GET /api/sma/trend"
            },
            "MCP协议": {
                "list_mcp_tools": "GET /mcp/v1/tools",
                "call_mcp_tool": "POST /mcp/v1/tools/call",
                "list_mcp_resources": "GET /mcp/v1/resources",
                "list_mcp_prompts": "GET /mcp/v1/prompts"
            }
        }
    }


@router.get("/api/data", response_model=StockDataResponse)
async def get_stock_data(
    code: str = Query(..., description="股票代码，例如：sh.600000"),
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD")
):
    """
    从 baostock 获取股票历史K线数据
    
    Args:
        code: 股票代码，例如：sh.600000（上海）或 sz.000001（深圳）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
    
    Returns:
        股票历史K线数据
    """
    try:
        with BaoStockWrapper() as bs_wrapper:
            df = bs_wrapper.get_stock_data(code, start_date, end_date)
            
            # 转换为字典列表
            data = df.to_dict('records')
            # 将日期转换为字符串
            for record in data:
                if 'date' in record and pd.notna(record['date']):
                    record['date'] = record['date'].strftime('%Y-%m-%d')
            
            return StockDataResponse(
                code=code,
                start_date=start_date,
                end_date=end_date,
                data=data,
                count=len(data),
                source="baostock"
            )
    except Exception as e:
        logger.error(f"从 baostock 获取股票数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取股票数据失败: {str(e)}")


@router.post("/api/data", response_model=StockDataResponse)
async def get_stock_data_post(request: StockQueryRequest):
    """
    通过POST方式获取股票历史K线数据
    """
    return await get_stock_data(
        code=request.code,
        start_date=request.start_date,
        end_date=request.end_date
    )


@router.get("/api/indicators", response_model=StockIndicatorsResponse)
async def get_stock_indicators(
    code: str = Query(..., description="股票代码，例如：sh.600000")
):
    """
    获取股票技术指标
    
    返回以下指标：
    - close: 最新收盘价
    - high_20: 20日最高价
    - high_55: 55日最高价
    - low_10: 10日最低价
    - low_20: 20日最低价
    - atr_20: 20日ATR（平均真实波幅）
    
    Args:
        code: 股票代码，例如：sh.600000（上海）或 sz.000001（深圳）
    
    Returns:
        股票技术指标数据
    """
    try:
        # 计算需要获取的数据范围（至少需要55天来计算high_55）
        end_date = datetime.today()
        start_date = end_date - timedelta(days=120)  # 多获取几天以确保有足够数据
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # 从数据库获取股票数据
        stock_data = await get_stock_daily_data_from_db(code, start_date_str, end_date_str)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(stock_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 确保数值列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if len(df) < 55:
            raise HTTPException(
                status_code=400, 
                detail=f"数据不足，需要至少55天数据，当前只有 {len(df)} 天"
            )
        
        # 获取最新收盘价
        close = float(df['close'].iloc[-1])
        
        # 计算最高价和最低价
        high_20 = float(df['high'].tail(20).max())
        high_55 = float(df['high'].tail(55).max())
        low_10 = float(df['low'].tail(10).min())
        low_20 = float(df['low'].tail(20).min())
        
        # 计算ATR（平均真实波幅）
        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['prev_close'])
        df['tr3'] = abs(df['low'] - df['prev_close'])
        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # 计算20日ATR（使用简单移动平均）
        atr_20 = float(df['true_range'].tail(20).mean())
        
        # 获取股票名称
        stock_name = await get_stock_name(code)
        
        return StockIndicatorsResponse(
            code=code,
            name=stock_name,
            success=True,
            message="获取成功",
            close=close,
            high_20=high_20,
            high_55=high_55,
            low_10=low_10,
            low_20=low_20,
            atr_20=atr_20
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票 {code} 指标失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取股票指标失败: {str(e)}")


@router.get("/api/list/hs300")
async def get_hs300_stocks():
    """获取沪深300成分股列表"""
    try:
        data = await get_index_stocks('hs300')
        bs.login()
        rs = bs.query_hs300_stocks()
        
        if rs.error_code != "0":
            bs.logout()
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        stocks = []
        while (rs.error_code == '0') & rs.next():
            stocks.append(rs.get_row_data())
        
        bs.logout()
        
        return {
            "count": len(stocks),
            "stocks": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取沪深300成分股失败: {str(e)}")


@router.get("/api/list/zz500")
async def get_zz500_stocks():
    """获取中证500成分股列表"""
    try:
        bs.login()
        rs = bs.query_zz500_stocks()
        
        if rs.error_code != "0":
            bs.logout()
            raise HTTPException(status_code=500, detail=f"查询失败: {rs.error_msg}")
        
        stocks = []
        while (rs.error_code == '0') & rs.next():
            stocks.append(rs.get_row_data())
        
        bs.logout()
        
        return {
            "count": len(stocks),
            "stocks": stocks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取中证500成分股失败: {str(e)}")


@router.get("/api/list/hs300/db")
async def get_hs300_stocks_from_db():
    """从数据库获取沪深300成分股列表"""
    try:
        stocks = await get_index_stocks('hs300')
        count = await get_stock_count('hs300')
        return {
            "count": count,
            "stocks": stocks,
            "source": "database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从数据库获取沪深300成分股失败: {str(e)}")


@router.get("/api/list/zz500/db")
async def get_zz500_stocks_from_db():
    """从数据库获取中证500成分股列表"""
    try:
        stocks = await get_index_stocks('zz500')
        count = await get_stock_count('zz500')
        return {
            "count": count,
            "stocks": stocks,
            "source": "database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从数据库获取中证500成分股失败: {str(e)}")


@router.get("/api/data/db", response_model=StockDataResponse)
async def get_stock_data_from_db(
    code: str = Query(..., description="股票代码，例如：sh.600000"),
    start_date: str = Query(..., description="开始日期，格式：YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期，格式：YYYY-MM-DD")
):
    """
    从数据库获取股票历史K线数据
    
    Args:
        code: 股票代码，例如：sh.600000（上海）或 sz.000001（深圳）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
    
    Returns:
        股票历史K线数据
    """
    try:
        data = await get_stock_daily_data_from_db(code, start_date, end_date)
        
        return StockDataResponse(
            code=code,
            start_date=start_date,
            end_date=end_date,
            data=data,
            count=len(data),
            source="database"
        )
    except Exception as e:
        logger.error(f"从数据库获取股票数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"从数据库获取股票数据失败: {str(e)}")


@router.get("/api/data/recent", response_model=StockDataResponse)
async def get_stock_data_recent(
    code: str = Query(..., description="股票代码，例如：sh.600000"),
    last_days: int = Query(7, description="获取最近N天的数据，默认为7天", ge=1, le=365)
):
    """
    从数据库获取股票最近N天的K线数据
    
    Args:
        code: 股票代码，例如：sh.600000（上海）或 sz.000001（深圳）
        last_days: 获取最近N天的数据，默认为7天，范围1-365天
    
    Returns:
        股票最近N天的K线数据
    """
    try:
        # 计算日期范围
        end_date = datetime.today()
        start_date = end_date - timedelta(days=last_days)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # 从数据库获取数据
        data = await get_stock_daily_data_from_db(code, start_date_str, end_date_str)
        
        return StockDataResponse(
            code=code,
            start_date=start_date_str,
            end_date=end_date_str,
            data=data,
            count=len(data),
            source="database"
        )
    except Exception as e:
        logger.error(f"从数据库获取股票最近{last_days}天数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"从数据库获取股票最近{last_days}天数据失败: {str(e)}")


# ==================== MCP协议支持 ====================

@router.get("/mcp/v1/tools", response_model=List[MCPTool])
async def list_mcp_tools():
    """
    列出所有可用的MCP工具
    """
    tools = [
        {
            "name": "get_stock_data",
            "description": "获取指定股票在指定时间段内的历史K线数据",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "股票代码，例如：sh.600000（上海）或 sz.000001（深圳）"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式：YYYY-MM-DD"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式：YYYY-MM-DD"
                    }
                },
                "required": ["code", "start_date", "end_date"]
            }
        },
        {
            "name": "get_hs300_stocks",
            "description": "获取沪深300成分股列表",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "get_zz500_stocks",
            "description": "获取中证500成分股列表",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    ]
    return tools


@router.post("/mcp/v1/tools/call", response_model=MCPToolCallResponse)
async def call_mcp_tool(request: MCPToolCallRequest):
    """
    调用MCP工具
    """
    try:
        if request.name == "get_stock_data":
            if "code" not in request.arguments or "start_date" not in request.arguments or "end_date" not in request.arguments:
                return MCPToolCallResponse(
                    content=[{"type": "text", "text": "缺少必需参数：code, start_date, end_date"}],
                    isError=True
                )
            
            result = await get_stock_data(
                code=request.arguments["code"],
                start_date=request.arguments["start_date"],
                end_date=request.arguments["end_date"]
            )
            
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"成功获取股票 {result.code} 的数据，共 {result.count} 条记录。\n数据：{result.model_dump_json()}"
                }]
            )
        
        elif request.name == "get_hs300_stocks":
            result = await get_hs300_stocks()
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"成功获取沪深300成分股，共 {result['count']} 只股票。\n数据：{str(result)}"
                }]
            )
        
        elif request.name == "get_zz500_stocks":
            result = await get_zz500_stocks()
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"成功获取中证500成分股，共 {result['count']} 只股票。\n数据：{str(result)}"
                }]
            )
        
        else:
            return MCPToolCallResponse(
                content=[{"type": "text", "text": f"未知的工具：{request.name}"}],
                isError=True
            )
    
    except Exception as e:
        return MCPToolCallResponse(
            content=[{"type": "text", "text": f"调用工具失败：{str(e)}"}],
            isError=True
        )


@router.get("/mcp/v1/resources")
async def list_mcp_resources():
    """
    列出所有可用的MCP资源
    """
    return {
        "resources": [
            {
                "uri": "stock://hs300",
                "name": "沪深300成分股",
                "description": "沪深300指数成分股列表",
                "mimeType": "application/json"
            },
            {
                "uri": "stock://zz500",
                "name": "中证500成分股",
                "description": "中证500指数成分股列表",
                "mimeType": "application/json"
            }
        ]
    }


@router.get("/mcp/v1/prompts")
async def list_mcp_prompts():
    """
    列出所有可用的MCP提示词
    """
    return {
        "prompts": [
            {
                "name": "stock_analysis",
                "description": "分析股票数据的提示词模板",
                "arguments": [
                    {
                        "name": "code",
                        "description": "股票代码",
                        "required": True
                    },
                    {
                        "name": "start_date",
                        "description": "开始日期",
                        "required": True
                    },
                    {
                        "name": "end_date",
                        "description": "结束日期",
                        "required": True
                    }
                ]
            }
        ]
    }


# ==================== 数据刷新接口 ====================

@router.post("/api/refresh/daily-data")
async def refresh_daily_data_api():
    """
    手动执行每日数据刷新任务
    
    该接口会执行以下操作：
    1. 刷新成分股列表（可能发生变化）
    2. 刷新所有股票的最新交易数据（只获取缺失的日期）
    
    Returns:
        刷新任务执行结果
    """
    try:
        logger.info("手动触发每日数据刷新任务...")
        
        # 先刷新成分股列表（可能发生变化）
        await fetch_all_index_stocks()
        # 然后刷新交易数据
        await refresh_daily_data()
        
        logger.info("每日数据刷新任务执行完成")
        
        return {
            "success": True,
            "message": "每日数据刷新任务执行成功",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"每日数据刷新任务执行失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"每日数据刷新任务执行失败: {str(e)}")


# ==================== 选股任务接口 ====================

@router.post("/api/search/sma-gold")
async def run_search_gold():
    """
    执行选股任务（金叉策略）
    
    该接口会执行以下操作：
    1. 检测沪深300和中证500成分股中的金叉信号
    2. 对符合条件的股票进行回测分析
    3. 筛选出收益率和胜率符合条件的股票
    4. 发送邮件通知结果
    
    Returns:
        选股结果列表，每个结果包含：股票代码、名称、平均收益、平均收益率、胜率
    """
    try:
        logger.info("开始执行选股任务...")
        content = await run_search_gold_task()
        logger.info("选股任务执行完成")
        
        return {
            "success": True,
            "message": "选股任务执行成功",
            "count": len(content) if content else 0,
            "results": [
                {
                    "code": item[0],
                    "name": item[1],
                    "平均收益": item[2],
                    "平均收益率": item[3],
                    "胜率": item[4]
                }
                for item in content
            ] if content else []
        }
    except Exception as e:
        logger.error(f"选股任务执行失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"选股任务执行失败: {str(e)}")


@router.post("/api/search/macd-gold")
async def run_search_macd_gold():
    """
    执行MACD选股任务（MACD金叉策略）
    
    该接口会执行以下操作：
    1. 检测沪深300和中证500成分股中的MACD金叉信号
    2. 对符合条件的股票进行MACD策略回测分析
    3. 筛选出收益率和胜率符合条件的股票
    4. 发送邮件通知结果
    
    Returns:
        选股结果列表，每个结果包含：股票代码、名称、平均收益、平均收益率、胜率
    """
    try:
        logger.info("开始执行MACD选股任务...")
        content = await run_search_macd_gold_task()
        logger.info("MACD选股任务执行完成")
        
        return {
            "success": True,
            "message": "MACD选股任务执行成功",
            "count": len(content) if content else 0,
            "results": [
                {
                    "code": item[0],
                    "name": item[1],
                    "平均收益": item[2],
                    "平均收益率": item[3],
                    "胜率": item[4],
                    "金叉日期": item[5]
                }
                for item in content
            ] if content else []
        }
    except Exception as e:
        logger.error(f"MACD选股任务执行失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"MACD选股任务执行失败: {str(e)}")


# ==================== SMA回测接口 ====================

@router.post("/api/sma/backtest", response_model=SMABacktestResponse)
async def sma_backtest(request: SMABacktestRequest):
    """
    SMA策略回测接口
    
    对指定股票进行SMA（简单移动平均）策略回测分析。
    使用过去一年的数据进行回测。
    
    Args:
        request: 包含股票代码的请求对象
    
    Returns:
        SMA回测结果，包括平均收益、平均收益率、胜率等
    """
    try:
        code = request.code
        logger.info(f"开始对股票 {code} 进行SMA回测...")
        
        # 计算日期范围（过去一年）
        end_date = datetime.today()
        start_date = end_date - timedelta(days=365)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # 从 baostock 获取股票交易数据
        try:
            with BaoStockWrapper() as bs_wrapper:
                data = bs_wrapper.get_stock_data(code, start_date_str, end_date_str)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"从 baostock 获取股票 {code} 数据失败: {str(e)}"
            )
        
        if data is None or data.empty:
            raise HTTPException(
                status_code=404, 
                detail=f"股票 {code} 在 {start_date_str} 到 {end_date_str} 期间没有交易数据"
            )
        
        # 检查数据是否足够
        if len(data) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"股票 {code} 的数据量不足（需要至少10条，实际{len(data)}条）"
            )
        
        # 获取策略参数（如果未提供则使用默认值）
        sma1 = request.sma1 if request.sma1 is not None else 5
        sma2 = request.sma2 if request.sma2 is not None else 10
        hold_days = request.hold_days if request.hold_days is not None else 21
        
        # 验证参数合理性
        if sma1 >= sma2:
            raise HTTPException(
                status_code=400,
                detail=f"参数错误: sma1 ({sma1}) 必须小于 sma2 ({sma2})"
            )
        
        # 构建策略参数
        strategy_args = {
            'sma1': sma1,
            'sma2': sma2,
            'hold_days': hold_days
        }
        
        # 运行SMA回测策略
        avg_profit, avg_profit_ratio, win_prob = sma.runstrat(data, args=strategy_args)
        
        logger.info(
            f"SMA回测完成 - 股票: {code}, "
            f"SMA({sma1},{sma2}), 持有{hold_days}天, "
            f"平均收益: {avg_profit:.2f}, "
            f"平均收益率: {avg_profit_ratio:.4f}, "
            f"胜率: {win_prob:.4f}"
        )
        
        return SMABacktestResponse(
            code=code,
            success=True,
            message="SMA回测完成",
            avg_profit=round(avg_profit, 2),
            avg_profit_ratio=round(avg_profit_ratio, 4),
            win_prob=round(win_prob, 4),
            data_count=len(data),
            sma1=sma1,
            sma2=sma2,
            hold_days=hold_days
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SMA回测失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SMA回测失败: {str(e)}")


@router.get("/api/sma/trend", response_model=SMATrendResponse)
async def check_sma_trend(
    code: str = Query(..., description="股票代码，例如：sh.600000")
):
    """
    检查股票SMA是否处于上升趋势
    
    该接口会分析股票的SMA趋势，判断是否处于上升趋势。
    判断标准包括：
    1. SMA5是否在SMA10之上（金叉状态）
    2. SMA5和SMA10是否在上升
    3. 价格是否在SMA之上
    
    Args:
        code: 股票代码，例如：sh.600000（上海）或 sz.000001（深圳）
    
    Returns:
        SMA趋势分析结果
    """
    try:
        logger.info(f"开始检查股票 {code} 的SMA趋势...")
        
        # 计算日期范围（至少需要10天数据来计算SMA10）
        end_date = datetime.today()
        start_date = end_date - timedelta(days=60)  # 多获取几天以确保有足够数据
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        # 从数据库获取股票数据
        stock_data = await get_stock_daily_data_from_db(code, start_date_str, end_date_str)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail=f"未找到股票 {code} 的数据")
        
        # 转换为DataFrame
        df = pd.DataFrame(stock_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # 确保数值列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if len(df) < 10:
            raise HTTPException(
                status_code=400, 
                detail=f"数据不足，需要至少10天数据，当前只有 {len(df)} 天"
            )
        
        # 计算SMA5和SMA10
        df['SMA5'] = df['close'].rolling(window=5).mean()
        df['SMA10'] = df['close'].rolling(window=10).mean()
        
        # 获取最新数据
        latest = df.iloc[-1]
        prev_5 = df.iloc[-6] if len(df) >= 6 else df.iloc[-1]  # 5天前
        prev_10 = df.iloc[-11] if len(df) >= 11 else df.iloc[-1]  # 10天前
        
        current_price = float(latest['close'])
        sma5_current = float(latest['SMA5'])
        sma10_current = float(latest['SMA10'])
        
        # 判断SMA5趋势
        sma5_prev = float(prev_5['SMA5']) if pd.notna(prev_5['SMA5']) else sma5_current
        if sma5_current > sma5_prev * 1.001:  # 允许0.1%的误差
            sma5_trend = "上升"
        elif sma5_current < sma5_prev * 0.999:
            sma5_trend = "下降"
        else:
            sma5_trend = "持平"
        
        # 判断SMA10趋势
        sma10_prev = float(prev_10['SMA10']) if pd.notna(prev_10['SMA10']) else sma10_current
        if sma10_current > sma10_prev * 1.001:
            sma10_trend = "上升"
        elif sma10_current < sma10_prev * 0.999:
            sma10_trend = "下降"
        else:
            sma10_trend = "持平"
        
        # 判断是否金叉（SMA5在SMA10之上）
        golden_cross = sma5_current > sma10_current
        
        # 判断价格是否在SMA之上
        price_above_sma5 = current_price > sma5_current
        price_above_sma10 = current_price > sma10_current
        
        # 综合判断是否处于上升趋势
        # 上升趋势的条件：金叉 + SMA5上升 + 价格在SMA5之上
        is_upward_trend = golden_cross and sma5_trend == "上升" and price_above_sma5
        
        # 获取股票名称
        stock_name = await get_stock_name(code)
        
        logger.info(
            f"SMA趋势检查完成 - 股票: {code}, "
            f"上升趋势: {is_upward_trend}, "
            f"SMA5: {sma5_current:.2f}, SMA10: {sma10_current:.2f}, "
            f"金叉: {golden_cross}"
        )
        
        return SMATrendResponse(
            code=code,
            name=stock_name,
            success=True,
            message="SMA趋势检查完成",
            is_upward_trend=is_upward_trend,
            current_price=round(current_price, 2),
            sma5=round(sma5_current, 2),
            sma10=round(sma10_current, 2),
            sma5_trend=sma5_trend,
            sma10_trend=sma10_trend,
            golden_cross=golden_cross,
            price_above_sma5=price_above_sma5,
            price_above_sma10=price_above_sma10
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查股票 {code} SMA趋势失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查SMA趋势失败: {str(e)}")
