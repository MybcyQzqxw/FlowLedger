"""Shared constants for FlowLedger."""

APP_NAME = "FlowLedger"
WINDOW_TITLE = "FlowLedger - 银行进账截图提取"
WINDOW_MIN_SIZE = (820, 760)
THUMBNAIL_SIZE = 48

DEFAULT_EXCEL_PATH = r"D:\mine\！文件\报销\！银行卡\银行卡.xlsx"
DEFAULT_TARGET_DIR = r"D:\mine\！文件\报销\！银行卡\截图"

HEADERS = (
    "交易时间",
    "付款方名称",
    "付款方账号",
    "交易类型",
    "交易渠道",
    "具体信息",
    "收入金额",
    "备注",
)

TIME_FORMAT = "yyyy-mm-dd hh:mm:ss"
AMOUNT_FORMAT = "#,##0.00"
COLUMN_WIDTHS = (21, 18, 20, 12, 14, 20, 16, 30)
TOTAL_LABEL = "金额总计"
