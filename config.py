import os
from dotenv import load_dotenv
import logging

load_dotenv()

SYMBOL = 'BNB/USDT'
INITIAL_GRID = 1.0
FLIP_THRESHOLD = lambda grid_size, volatility: (grid_size / TradingConfig.get_flip_threshold_ratio(volatility)) / 100  # 根据波动率动态计算阈值
POSITION_SCALE_FACTOR = 0.2  # 仓位调整系数（20%）
MIN_TRADE_AMOUNT = 20.0  # 新下限
MIN_POSITION_PERCENT = 0.05  # 最小交易比例（总资产的5%）
MAX_POSITION_PERCENT = 0.15  # 最大交易比例（总资产的15%）
COOLDOWN = 60
SAFETY_MARGIN = 0.95
MAX_DRAWDOWN = -0.15
DAILY_LOSS_LIMIT = -0.05
MAX_POSITION_RATIO = 0.9  # 最大仓位比例 (90%)，保留10%底仓
MIN_POSITION_RATIO = 0.1  # 最小仓位比例 (10%)，底仓
AUTO_ADJUST_BASE_PRICE = False  # 自动调整基准价开关，默认关闭
PUSHPLUS_TOKEN = os.getenv('PUSHPLUS_TOKEN')
PUSHPLUS_TIMEOUT = 5  # PushPlus请求超时时间（秒）
LOG_LEVEL = logging.INFO  # 设置为INFO减少调试日志
DEBUG_MODE = False  # 设置为True时显示详细日志
API_TIMEOUT = 10000  # API超时时间（毫秒）
RECV_WINDOW = 5000  # 接收窗口时间（毫秒）
RISK_CHECK_INTERVAL = 300  # 5分钟检查一次风控
try:
    INITIAL_BASE_PRICE = float(os.getenv('INITIAL_BASE_PRICE', 0))
except ValueError:
    INITIAL_BASE_PRICE = 0
    logging.warning("无效的INITIAL_BASE_PRICE配置，已重置为0")
MAX_RETRIES = 5  # 最大重试次数
RISK_FACTOR = 0.1    # 风险系数（10%）
VOLATILITY_WINDOW = 24  # 波动率计算周期（小时）

# 从环境变量读取初始本金，如果未设置或无效，默认为0
try:
    INITIAL_PRINCIPAL = float(os.getenv('INITIAL_PRINCIPAL', 0))
    if INITIAL_PRINCIPAL <= 0:
        logging.warning("INITIAL_PRINCIPAL 必须为正数，已重置为0")
        INITIAL_PRINCIPAL = 0
except ValueError:
    INITIAL_PRINCIPAL = 0
    logging.warning("无效的INITIAL_PRINCIPAL配置，已重置为0")

class TradingConfig:
    RISK_PARAMS = {
        'max_drawdown': MAX_DRAWDOWN,
        'daily_loss_limit': DAILY_LOSS_LIMIT,
        'position_limit': MAX_POSITION_RATIO
    }
    
    # 添加动态翻转阈值配置
    FLIP_THRESHOLD_PARAMS = {
        'ranges': [
            {'range': [0, 0.20], 'buy_ratio': 6.0, 'sell_ratio': 9.0},    # 波动率 0-20%，买入阈值比例7.0，卖出阈值比例9.0
            {'range': [0.20, 0.40], 'buy_ratio': 5.0, 'sell_ratio': 8.0},  # 波动率 20-40%，买入阈值比例6.0，卖出阈值比例8.0
            {'range': [0.40, 0.60], 'buy_ratio': 4.0, 'sell_ratio': 7.0},  # 波动率 40-60%，买入阈值比例5.0，卖出阈值比例7.0
            {'range': [0.60, 0.80], 'buy_ratio': 5.0, 'sell_ratio': 6.0},  # 波动率 60-80%，买入阈值比例4.0，卖出阈值比例6.0
            {'range': [0.80, 1.00], 'buy_ratio': 2.0, 'sell_ratio': 5.0},  # 波动率 80-100%，买入阈值比例3.0，卖出阈值比例5.0
            {'range': [1.00, 1.20], 'buy_ratio': 1.0, 'sell_ratio': 4.0},  # 波动率 100-120%，买入阈值比例2.0，卖出阈值比例4.0
            {'range': [1.20, 999], 'buy_ratio': 0.8, 'sell_ratio': 3.0}    # 波动率 >120%，买入阈值比例1.0，卖出阈值比例3.0
        ],
        'default_buy_ratio': 5.0,  # 默认买入阈值比例
        'default_sell_ratio': 8.0  # 默认卖出阈值比例
    }
    
    @classmethod
    def get_flip_threshold_ratio(cls, volatility, side='buy'):
        """
        根据波动率和交易类型获取对应的翻转阈值比例
        :param volatility: 当前波动率
        :param side: 交易方向，'buy' 或 'sell'
        :return: 对应的阈值比例
        """
        ratio_key = f'{side}_ratio'
        default_ratio = cls.FLIP_THRESHOLD_PARAMS[f'default_{ratio_key}']
        
        for range_config in cls.FLIP_THRESHOLD_PARAMS['ranges']:
            if range_config['range'][0] <= volatility < range_config['range'][1]:
                return range_config[ratio_key]
        return default_ratio
    
    GRID_PARAMS = {
        'initial': INITIAL_GRID,
        'min': 0.8,
        'max': 4.0,
        'volatility_threshold': {
            'ranges': [
                {'range': [0, 0.20], 'grid': 0.8},     # 波动率 0-20%，网格0.8%
                {'range': [0.20, 0.40], 'grid': 1.0},  # 波动率 20-40%，网格1.0%（从1.5%改为1.0%）
                {'range': [0.40, 0.60], 'grid': 1.4},  # 波动率 40-60%，网格1.5%（从2.0%改为1.5%）
                {'range': [0.60, 0.80], 'grid': 1.8},  # 波动率 60-80%，网格2.0%（从2.5%改为1.8%）
                {'range': [0.80, 1.00], 'grid': 2.5},  # 波动率 80-100%，网格2.5%（从3.0%改为2.5%）
                {'range': [1.00, 1.20], 'grid': 3.0},  # 波动率 100-120%，网格3.0%（从3.5%改为3.0%）
                {'range': [1.20, 999], 'grid': 3.5}    # 波动率 >120%，网格3.5%（从4.0%改为3.5%）
            ]
        }
    }
        # --- 新增：动态时间间隔参数 ---
    DYNAMIC_INTERVAL_PARAMS = {
        # 定义波动率区间与对应调整间隔（小时）的映射关系
        'volatility_to_interval_hours': [
            # 格式: {'range': [最低波动率(含), 最高波动率(不含)], 'interval_hours': 对应的小时间隔}
            {'range': [0, 0.20], 'interval_hours': 1.0},    # 波动率 < 0.20 时，间隔 1 小时
            {'range': [0.20, 0.40], 'interval_hours': 0.5},   # 波动率 0.20 到 0.40 时，间隔30分钟
            {'range': [0.40, 0.80], 'interval_hours': 0.25},   # 波动率 0.40 到 0.80 时，间隔15分钟
            {'range': [0.80, 999], 'interval_hours': 0.125},   # 波动率 >=0.80 ，间隔7.5分钟
        ],
        # 定义一个默认间隔，以防波动率计算失败或未匹配到任何区间
        'default_interval_hours': 1.0
    }
    
    SYMBOL = SYMBOL
    INITIAL_BASE_PRICE = INITIAL_BASE_PRICE
    RISK_CHECK_INTERVAL = RISK_CHECK_INTERVAL
    MAX_RETRIES = MAX_RETRIES
    RISK_FACTOR = RISK_FACTOR
    BASE_AMOUNT = 50.0  # 恢复原始基础金额（可调整）
    MIN_TRADE_AMOUNT = MIN_TRADE_AMOUNT
    MAX_POSITION_RATIO = MAX_POSITION_RATIO
    MIN_POSITION_RATIO = MIN_POSITION_RATIO
    VOLATILITY_WINDOW = VOLATILITY_WINDOW
    INITIAL_GRID = INITIAL_GRID
    POSITION_SCALE_FACTOR = POSITION_SCALE_FACTOR
    COOLDOWN = COOLDOWN
    SAFETY_MARGIN = SAFETY_MARGIN
    API_TIMEOUT = API_TIMEOUT
    RECV_WINDOW = RECV_WINDOW
    MIN_POSITION_PERCENT = MIN_POSITION_PERCENT
    MAX_POSITION_PERCENT = MAX_POSITION_PERCENT
    # 添加初始本金到类属性
    INITIAL_PRINCIPAL = INITIAL_PRINCIPAL
    # 添加自动调整基准价开关
    AUTO_ADJUST_BASE_PRICE = AUTO_ADJUST_BASE_PRICE

    def __init__(self):
        # 添加配置验证
        if self.MIN_POSITION_RATIO >= self.MAX_POSITION_RATIO:
            raise ValueError("底仓比例不能大于或等于最大仓位比例")
        
        if self.GRID_PARAMS['min'] > self.GRID_PARAMS['max']:
            raise ValueError("网格最小值不能大于最大值")
        
        # 这里不再需要 self.SYMBOL = SYMBOL 等重复赋值语句
        # 也不再需要 self.RISK_PARAMS = {...} 和 self.GRID_PARAMS = {...} 的重复定义
        
    # Removed unused update methods (update_risk_params, update_grid_params, 
    # update_symbol, update_initial_base_price, update_risk_check_interval, 
    # update_max_retries, update_risk_factor, update_base_amount, 
    # update_min_trade_amount, update_max_position_ratio, 
    # update_min_position_ratio, update_all)

    # Removed unused validate_config method
# End of class definition 
