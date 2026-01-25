"""
数据库操作模块
使用SQLite存储成分股数据
"""
import aiosqlite
import os
from typing import List, Dict, Optional
from datetime import datetime

# 数据库文件路径，保存在app目录下
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "stock_index.db")


async def init_db():
    """初始化数据库，创建表"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 创建成分股表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS index_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_type TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                update_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(index_type, code)
            )
        """)
        
        # 如果表已存在但没有name列，则添加该列（数据库迁移）
        try:
            await db.execute("ALTER TABLE index_stocks ADD COLUMN name TEXT")
        except Exception:
            # 列已存在，忽略错误
            pass
        
        # 创建股票交易数据表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_daily_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                adjustflag TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(code, date)
            )
        """)
        
        # 创建索引以提高查询性能
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_index_type ON index_stocks(index_type)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_code ON index_stocks(code)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_daily_data(code)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_daily_data(date)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_code_date ON stock_daily_data(code, date)
        """)
        
        await db.commit()


async def save_index_stocks(index_type: str, stocks: List[List[str]], fields: List[str]):
    """
    保存成分股数据到数据库
    
    Args:
        index_type: 指数类型，'hs300' 或 'zz500'
        stocks: 股票数据列表，每个元素是一个字段值列表
        fields: 字段名列表
    """
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 先删除该指数的旧数据
        await db.execute(
            "DELETE FROM index_stocks WHERE index_type = ?",
            (index_type,)
        )
        
        # 插入新数据
        # 通常baostock返回的字段顺序是：code, code_name, date等
        # 我们需要找到code、code_name和update_date字段的位置
        code_idx = fields.index('code') if 'code' in fields else 0
        
        # 尝试多种可能的股票名称字段名
        name_idx = None
        for name_field in ['code_name', 'name', 'stock_name']:
            if name_field in fields:
                name_idx = fields.index(name_field)
                break
        
        # 尝试多种可能的日期字段名
        update_date_idx = None
        for date_field in ['updateDate', 'date', 'update_date']:
            if date_field in fields:
                update_date_idx = fields.index(date_field)
                break
        
        for stock in stocks:
            code = stock[code_idx] if code_idx < len(stock) else None
            name = stock[name_idx] if name_idx is not None and name_idx < len(stock) else None
            update_date = stock[update_date_idx] if update_date_idx is not None and update_date_idx < len(stock) else None
            
            if code:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO index_stocks 
                    (index_type, code, name, update_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (index_type, code, name, update_date, now, now)
                )
        
        await db.commit()


async def get_index_stocks(index_type: str) -> List[Dict]:
    """
    从数据库获取成分股列表
    
    Args:
        index_type: 指数类型，'hs300' 或 'zz500'
    
    Returns:
        成分股列表
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT code, name, update_date, updated_at FROM index_stocks WHERE index_type = ?",
            (index_type,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_stock_name(code: str) -> Optional[str]:
    """
    根据股票代码获取股票名称
    
    Args:
        code: 股票代码
    
    Returns:
        股票名称，如果未找到则返回None
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT name FROM index_stocks WHERE code = ? LIMIT 1",
            (code,)
        ) as cursor:
            row = await cursor.fetchone()
            return row['name'] if row and row['name'] else None


async def get_stock_count(index_type: str) -> int:
    """获取指定指数的成分股数量"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) as count FROM index_stocks WHERE index_type = ?",
            (index_type,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0


async def get_all_stock_codes() -> List[str]:
    """获取所有成分股的股票代码列表"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT DISTINCT code FROM index_stocks"
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]


async def get_all_stock_codes_with_name() -> List[Dict]:
    """获取所有成分股的股票代码和名称"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT DISTINCT code, name FROM index_stocks ORDER BY code"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_stock_codes_with_date() -> List[Dict]:
    """获取所有成分股的股票代码和更新日期"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT DISTINCT index_type, code, name, update_date FROM index_stocks ORDER BY index_type, code"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def get_all_stock_data() -> List[Dict]:
    """获取所有成分股的股票数据列表"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM index_stocks"
        ) as cursor:
            rows = await cursor.fetchall()
            return rows



async def save_stock_daily_data(code: str, data: List[Dict]):
    """
    保存股票日线交易数据到数据库
    
    Args:
        code: 股票代码
        data: 交易数据列表，每个元素包含 date, open, high, low, close, volume, amount, adjustflag
    """
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        for record in data:
            await db.execute("""
                INSERT OR REPLACE INTO stock_daily_data
                (code, date, open, high, low, close, volume, amount, adjustflag, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                code,
                record.get('date'),
                record.get('open'),
                record.get('high'),
                record.get('low'),
                record.get('close'),
                record.get('volume'),
                record.get('amount'),
                record.get('adjustflag'),
                now,
                now
            ))
        
        await db.commit()


async def get_stock_data_last_update_date(code: str) -> Optional[str]:
    """获取指定股票数据的最后更新日期"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT MAX(date) as last_date FROM stock_daily_data WHERE code = ?",
            (code,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None


async def get_stock_daily_data_from_db(
    code: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> List[Dict]:
    """
    从数据库获取股票日线交易数据
    
    Args:
        code: 股票代码
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
    
    Returns:
        交易数据列表
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if start_date and end_date:
            async with db.execute(
                """
                SELECT code, date, open, high, low, close, volume, amount, adjustflag
                FROM stock_daily_data 
                WHERE code = ? AND date >= ? AND date <= ?
                ORDER BY date ASC
                """,
                (code, start_date, end_date)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        elif start_date:
            async with db.execute(
                """
                SELECT code, date, open, high, low, close, volume, amount, adjustflag
                FROM stock_daily_data 
                WHERE code = ? AND date >= ?
                ORDER BY date ASC
                """,
                (code, start_date)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        elif end_date:
            async with db.execute(
                """
                SELECT code, date, open, high, low, close, volume, amount, adjustflag
                FROM stock_daily_data 
                WHERE code = ? AND date <= ?
                ORDER BY date ASC
                """,
                (code, end_date)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        else:
            async with db.execute(
                """
                SELECT code, date, open, high, low, close, volume, amount, adjustflag
                FROM stock_daily_data 
                WHERE code = ?
                ORDER BY date ASC
                """,
                (code,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

