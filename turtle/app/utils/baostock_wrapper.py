import baostock as bs
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class BaoStockWrapper:
    def __enter__(self):
        lg = bs.login()
        # print("bs login status: ", lg.error_code, lg.error_msg)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            bs.logout()
        except Exception as e:
            # logout 失败不影响主流程，只记录警告
            logger.warning(f"logout 失败: {str(e)}")

    def get_stock_data(self, code, start_date, end_date):
        rs = bs.query_history_k_data_plus(code,
            "date,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start_date, 
            end_date=end_date,
            frequency="d", 
            adjustflag="3")

        if rs is None:
            raise Exception("rs is None")
        if rs.error_code != "0":
            print("error code: ", rs.error_code)
            raise Exception(rs.error_msg)

        # 获取具体的信息
        result_list = []
        while (rs.error_code == '0') & rs.next():
            # 分页查询，将每页信息合并在一起
            result_list.append(rs.get_row_data())
        result = pd.DataFrame(result_list, columns=rs.fields)

        result['date'] = pd.to_datetime(result['date'])
        result['open'] = pd.to_numeric(result['open'])
        result['high'] = pd.to_numeric(result['high'])
        result['low'] = pd.to_numeric(result['low'])
        result['close'] = pd.to_numeric(result['close'])
        result['volume'] = pd.to_numeric(result['volume'])
        result['amount'] = pd.to_numeric(result['amount'])

        return result