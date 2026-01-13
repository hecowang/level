

def stock_board(code: str) -> str:
    code = code.split(".")[1]
    if code.startswith(("688", "689")):
        return "科创板"
    if code.startswith("300"):
        return "创业板"
    if code.startswith(("600", "601", "603", "605")):
        return "沪市主板"
    if code.startswith(("000", "001", "002")):
        return "深市主板"
    return "未知"

def is_main_board(code: str) -> bool:
    board = stock_board(code)
    return board in ["沪市主板", "深市主板"]