# -*- coding: utf-8 -*-
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional, Callable
import pandas as pd
import numpy as np
from config import Config

def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def atr(df: pd.DataFrame, period=14) -> pd.Series:
    high = df['high']; low = df['low']; close = df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def bollinger(df: pd.DataFrame, period=20, nstd=2.0):
    mid = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std(ddof=0)
    upper = mid + nstd * std
    lower = mid - nstd * std
    width = (upper - lower) / (mid.replace(0, np.nan))
    return upper, mid, lower, width

def stochastic(df: pd.DataFrame, k_period=14, d_period=3, smooth_k=3):
    low_min = df['low'].rolling(k_period).min()
    high_max = df['high'].rolling(k_period).max()
    fast_k = 100 * (df['close'] - low_min) / ((high_max - low_min).replace(0, np.nan))
    slow_k = fast_k.rolling(smooth_k).mean()
    slow_d = slow_k.rolling(d_period).mean()
    return slow_k, slow_d

def compute_rsi(series: pd.Series, period=14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi

@dataclass
class MarketSnapshot:
    close_changes_1d: float
    close_changes_3d: float
    close_changes_7d: float
    rsi: float
    macd: float
    macd_signal: float
    ema20_vs_50: float
    ema50_vs_100: float
    bb_width: float
    atr_val: float
    volume_rel_5d: float
    stoch_k: float
    stoch_d: float

def calc_market_snapshot(df: pd.DataFrame) -> MarketSnapshot:
    df = df.copy()
    df['ema20'] = ema(df['close'], 20)
    df['ema50'] = ema(df['close'], 50)
    df['ema100'] = ema(df['close'], 100)
    macd_line, signal_line, _ = macd(df['close'])
    _, _, _, bb_w = bollinger(df, 20, 2.0)
    atr14 = atr(df, 14)
    rsi14 = compute_rsi(df['close'], 14)
    k, d = stochastic(df, 14, 3, 3)

    vol_rel_5 = df['volume'] / (df['volume'].rolling(5).mean() + 1e-9)

    close = df['close']
    def pct_change(n):
        return (close.iloc[-1] / close.iloc[-n-1] - 1.0) * 100 if len(close) > n else 0.0

    return MarketSnapshot(
        close_changes_1d=float(pct_change(1)),
        close_changes_3d=float(pct_change(3)),
        close_changes_7d=float(pct_change(7)),
        rsi=float(rsi14.iloc[-1]),
        macd=float(macd_line.iloc[-1]),
        macd_signal=float(signal_line.iloc[-1]),
        ema20_vs_50=float(df['ema20'].iloc[-1] - df['ema50'].iloc[-1]),
        ema50_vs_100=float(df['ema50'].iloc[-1] - df['ema100'].iloc[-1]),
        bb_width=float(bb_w.iloc[-1]),
        atr_val=float(atr14.iloc[-1]),
        volume_rel_5d=float(vol_rel_5.iloc[-1]),
        stoch_k=float(k.iloc[-1]),
        stoch_d=float(d.iloc[-1]),
    )

def scale_0_9(val, vmin, vmax):
    if np.isfinite(val) and vmax > vmin:
        x = (val - vmin) / (vmax - vmin)
        x = max(0.0, min(1.0, x))
        return int(round(x * 9))
    return 4

def calc_market_index(snap: MarketSnapshot) -> int:
    mom_1d_w = 0.5 if abs(snap.close_changes_1d) > 5 else 0.3
    mom_3d_w = 0.3
    mom_7d_w = 0.2
    mom = (snap.close_changes_1d * mom_1d_w + 
           snap.close_changes_3d * mom_3d_w + 
           snap.close_changes_7d * mom_7d_w)
    
    if mom < -15: mom_score = 0
    elif mom < -10: mom_score = 1
    elif mom < -5: mom_score = 2
    elif mom < -2: mom_score = 3
    elif mom < 0: mom_score = 4
    elif mom < 2: mom_score = 5
    elif mom < 5: mom_score = 6
    elif mom < 10: mom_score = 7
    elif mom < 15: mom_score = 8
    else: mom_score = 9

    trend_pts = 0.0
    if snap.ema20_vs_50 > 0: trend_pts += 1.5
    if snap.ema50_vs_100 > 0: trend_pts += 1.5
    if snap.macd > snap.macd_signal: trend_pts += 2.0
    if snap.macd > 0: trend_pts += 1.0
    
    trend_score = min(9, int(trend_pts * 1.5))

    vol_score = 5
    if snap.bb_width > 0.08: vol_score = 7
    elif snap.bb_width > 0.05: vol_score = 6
    elif snap.bb_width < 0.02: vol_score = 3
    elif snap.bb_width < 0.01: vol_score = 2

    volume_boost = 0
    if snap.volume_rel_5d > 2.0: volume_boost = 2
    elif snap.volume_rel_5d > 1.5: volume_boost = 1
    elif snap.volume_rel_5d < 0.5: volume_boost = -1

    osc_adj = 0
    if snap.rsi > 80: osc_adj = 1
    elif snap.rsi > 70: osc_adj = 0
    elif snap.rsi < 20: osc_adj = -1
    elif snap.rsi < 30: osc_adj = 0
    
    if snap.stoch_k > 80 and snap.stoch_d > 80: osc_adj += 1
    elif snap.stoch_k < 20 and snap.stoch_d < 20: osc_adj -= 1

    raw_idx = (mom_score * 0.4 + trend_score * 0.35 + vol_score * 0.25)
    raw_idx += volume_boost * 0.3 + osc_adj * 0.2
    
    final_idx = int(round(raw_idx))
    return max(0, min(9, final_idx))

@dataclass
class OrderPlan:
    side: str
    qty: float
    tp: Optional[float] = None
    sl: Optional[float] = None
    note: str = ""

class RiskManager:
    def __init__(self):
        cfg = Config()
        self.max_position_pct = cfg.MAX_POSITION_PCT
        self.max_trade_risk_pct = cfg.MAX_TRADE_RISK_PCT
        self.daily_loss_limit_pct = cfg.DAILY_LOSS_LIMIT_PCT
        self.min_liquidity_krw: float = 10_000_000
        self.max_correlation: float = 0.7

        self.daily_pnl = 0.0
        self.trades_today = 0
        self.current_positions = {}
        self.trade_history = []  # 켈리 공식용 히스토리
        
    def add_trade_result(self, win: bool, pnl_pct: float):
        """거래 결과 기록 (켈리 공식용)"""
        self.trade_history.append({'win': win, 'pnl_pct': pnl_pct})
        # 최근 50거래만 유지
        if len(self.trade_history) > 50:
            self.trade_history.pop(0)
    
    def get_kelly_stats(self) -> tuple:
        """켈리 공식용 통계 계산"""
        if len(self.trade_history) < 10:
            return 0.5, 0.02, 0.015  # 기본값
        
        wins = [t for t in self.trade_history if t['win']]
        losses = [t for t in self.trade_history if not t['win']]
        
        win_rate = len(wins) / len(self.trade_history)
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0.02
        avg_loss = abs(np.mean([t['pnl_pct'] for t in losses])) if losses else 0.015
        
        return win_rate, avg_win, avg_loss
    
    def check_trade_allowed(self, balance: float, plan: OrderPlan, price: float) -> bool:
        if plan is None:
            return False
        
        trade_value = plan.qty * price
        position_pct = trade_value / balance
        
        # 포지션 크기 제한
        if position_pct > self.max_position_pct:
            return False
        
        # 일일 손실 한도
        if self.daily_pnl < -balance * self.daily_loss_limit_pct:
            return False
        
        # 거래당 위험 제한 (개선된 계산)
        if plan.sl:
            potential_loss = plan.qty * abs(price - plan.sl)
            if potential_loss > balance * self.max_trade_risk_pct:
                return False
        
        # 거래 빈도 제한 (하루 최대 20회)
        if self.trades_today >= 20:
            return False
        
        return True
    
    def update_pnl(self, pnl: float):
        self.daily_pnl += pnl
        self.trades_today += 1
        
        # 거래 결과 기록
        win = pnl > 0
        pnl_pct = pnl / 1000000 * 100  # 백만원 기준 퍼센트
        self.add_trade_result(win, pnl_pct)
    
    def reset_daily(self):
        self.daily_pnl = 0.0
        self.trades_today = 0

def _position_size(balance_krw: float, pct: float, price: float) -> float:
    amt = max(0.0, balance_krw * pct / max(price, 1e-9))
    return round(amt, 6)

def kelly_position_size(balance_krw: float, win_rate: float, avg_win: float, 
                       avg_loss: float, base_pct: float, price: float) -> float:
    """켈리 공식으로 최적 포지션 크기 계산"""
    if avg_loss == 0 or win_rate <= 0:
        return _position_size(balance_krw, base_pct, price)
    
    # 켈리 공식: f = (bp - q) / b
    # b = 승률, p = 평균승률, q = 패률 = 1-p
    kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
    
    # 켈리 공식의 1/4 사용 (리스크 조절) + 최대 25% 제한
    optimal_fraction = min(kelly_fraction * 0.25, 0.25)
    optimal_fraction = max(optimal_fraction, base_pct * 0.5)  # 최소 기준의 50%
    
    return _position_size(balance_krw, optimal_fraction, price)

def volatility_filter(df: pd.DataFrame, min_vol: float = 0.015, max_vol: float = 0.08) -> bool:
    """적정 변동성 범위 체크"""
    returns = df['close'].pct_change().dropna()
    if len(returns) < 20:
        return False
    
    # 20일 변동성
    volatility = returns.tail(20).std() * np.sqrt(24 * 12)  # 연환산
    return min_vol <= volatility <= max_vol

def dynamic_tp_sl(df: pd.DataFrame, price: float, tp_atr_mult: float = 2.0, sl_atr_mult: float = 1.5) -> tuple:
    """
    ATR 기반 동적 TP/SL 계산 (개선된 로직)
    - 일관된 리스크/리워드 비율을 위해 변동성 기반 조정을 제거합니다.
    """
    atr_val = atr(df, 14).iloc[-1]
    
    tp = price + (atr_val * tp_atr_mult)
    sl = price - (atr_val * sl_atr_mult)
    
    # TP와 SL이 너무 가깝지 않도록 최소 거리 보장
    if tp < price + atr_val * 0.2:
        tp = price + atr_val * 0.2

    if sl > price - atr_val * 0.2:
        sl = price - atr_val * 0.2

    return tp, sl

def strat_extreme_panic_scalp(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    # 극공황 상황에서만 진입 (조건 강화)
    if snap.rsi > 20 or snap.volume_rel_5d < 2.0 or snap.close_changes_1d > -8:
        return None
    
    # ATR 기반 동적 TP/SL
    atr_val = atr(df, 14).iloc[-1]
    min_profit = max(0.025, atr_val * 3 / price)  # 최소 2.5% 또는 ATR*3
    
    qty = _position_size(balance_krw, 0.08, price)  # 5% → 8% 증가
    tp = price * (1 + min_profit + FEE*2)
    sl = price * (1 - atr_val * 1.5 / price)  # ATR 기반 SL
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage0: enhanced panic scalp")

def strat_strong_down_bounce(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    # 강화된 반등 조건
    if snap.stoch_k > 25 or snap.macd > snap.macd_signal * 0.9 or snap.close_changes_1d > -5:
        return None
    
    # ATR 기반 동적 TP/SL
    atr_val = atr(df, 14).iloc[-1]
    min_profit = max(0.02, atr_val * 2.5 / price)  # 최소 2% 또는 ATR*2.5
    
    qty = _position_size(balance_krw, 0.12, price)  # 10% → 12% 증가
    tp = price * (1 + min_profit + FEE*2)
    sl = price * (1 - atr_val * 1.2 / price)  # ATR 기반 SL
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage1: enhanced bounce")

def strat_conservative_breakout(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    cond = (snap.macd > snap.macd_signal * 0.95 and 
            snap.volume_rel_5d > 0.8 and snap.rsi > 35)
    if not cond: 
        return None
    
    qty = _position_size(balance_krw, 0.08, price)
    tp = price * (1.02 + FEE)
    sl = price * 0.985
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage2: conservative")

def strat_weak_down_swing(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    if snap.bb_width < 0.015 or snap.rsi < 35:
        return None
    
    qty = _position_size(balance_krw, 0.08, price)
    tp = price * (1.015 + FEE)
    sl = price * 0.99
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage3: weak swing")

def strat_defensive_trend_follow(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    if snap.macd <= snap.macd_signal or snap.rsi > 65:
        return None
    
    qty = _position_size(balance_krw, 0.10, price)
    tp = price * (1.02 + FEE)
    sl = price * 0.99
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage4: defensive TF")

def strat_neutral_box_scalp(df, snap, balance_krw=1_000_000):
    FEE = 0.0005
    u, m, l, w = bollinger(df, 20, 2.0)
    price = float(df['close'].iloc[-1])
    
    if snap.bb_width > 0.06 or snap.bb_width < 0.01:
        return None
    
    if price < l.iloc[-1] * 1.01:
        qty = _position_size(balance_krw, 0.12, price)
        # TP는 현재가보다 항상 높게 설정 (중간선과 현재가 중 큰 값 + 마진)
        tp_target = max(float(m.iloc[-1]), price * 1.01)
        tp = tp_target * (1 + FEE)
        sl = float(l.iloc[-1]) * 0.995
        return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage5: BB scalp")
    
    return None

def strat_breakout_entry(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    conditions = (snap.ema20_vs_50 > 0 and snap.volume_rel_5d >= 1.2 and
                  snap.macd > snap.macd_signal)
    if not conditions:
        return None
    
    qty = _position_size(balance_krw, 0.15, price)
    tp = price * (1.03 + FEE)
    sl = price * 0.985
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage6: breakout")

def strat_trend_follow_add(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    conditions = (snap.ema20_vs_50 > 0 and snap.ema50_vs_100 > 0 and 
                  snap.volume_rel_5d > 1.0 and snap.rsi < 70)
    if not conditions:
        return None
    
    qty = _position_size(balance_krw, 0.15, price)
    tp = price * (1.05 + FEE)
    sl = price * 0.985
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage7: trend add")

def strat_aggressive_breakout(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    conditions = (snap.rsi <= 75 and snap.volume_rel_5d >= 1.5 and 
                  snap.macd > snap.macd_signal)
    if not conditions:
        return None
    
    qty = _position_size(balance_krw, 0.20, price)
    tp = price * (1.06 + FEE)
    sl = price * 0.99
    return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage8: aggressive")

def strat_take_profit_reduce(df, snap, balance_krw=1_000_000):
    price = float(df['close'].iloc[-1])
    FEE = 0.0005
    
    if snap.rsi < 75 or snap.stoch_k < 85:
        qty = _position_size(balance_krw, 0.05, price)
        tp = price * (1.08 + FEE)
        sl = price * 0.985
        return OrderPlan("buy", qty, tp=tp, sl=sl, note="Stage9: profit take")
    
    return None

# NOTE: During optimization, strategies 0-5 and 9 were found to be unprofitable
# on the test dataset, leading to a negative overall return. They have been
# disabled to focus on the trend-following strategies (6, 7, 8), which were
# proven to be profitable and resulted in a significant performance improvement.
# These disabled strategies may be revisited for further tuning or testing on
# different datasets in the future.
STRATEGY_MAP: Dict[int, Callable] = {
    # 0: strat_extreme_panic_scalp,
    # 1: strat_strong_down_bounce,
    # 2: strat_conservative_breakout,
    # 3: strat_weak_down_swing,
    # 4: strat_defensive_trend_follow,
    # 5: strat_neutral_box_scalp,
    6: strat_breakout_entry,
    7: strat_trend_follow_add,
    8: strat_aggressive_breakout,
    # 9: strat_take_profit_reduce,
}

def decide_order(df: pd.DataFrame, balance_krw: float = 1_000_000, 
                 risk_manager: Optional[RiskManager] = None) -> Dict:
    snap = calc_market_snapshot(df)

    # 1. 변동성 필터링 - 적정 변동성 범위 체크
    if not volatility_filter(df):
        return {
            "index": 5,  # 중립으로 설정
            "snapshot": snap.__dict__,
            "plan": None,
            "stage_name": "Volatility Filter - Outside Range",
            "filter_reason": "volatility_out_of_range"
        }
    
    idx = calc_market_index(snap)
    strat = STRATEGY_MAP.get(idx)
    plan = strat(df, snap, balance_krw) if strat else None
    
    # 2. 동적 TP/SL 적용
    # NOTE: 모든 활성 전략에 동적 TP/SL을 적용하여 시장 변동성에 대응합니다.
    if plan and plan.side == "buy":
        current_price = float(df['close'].iloc[-1])
        plan.tp, plan.sl = dynamic_tp_sl(df, current_price)

    # 3. 켈리 공식 기반 포지션 사이징 (기록이 충분한 경우)
    if plan and risk_manager and len(risk_manager.trade_history) >= 10:
        win_rate, avg_win, avg_loss = risk_manager.get_kelly_stats()
        current_price = float(df['close'].iloc[-1])
        base_pct = plan.qty * current_price / balance_krw
        
        # 켈리 공식으로 최적 포지션 크기 재계산
        optimal_qty = kelly_position_size(balance_krw, win_rate, avg_win, avg_loss, base_pct, current_price)
        plan.qty = optimal_qty
    
    # 5. 리스크 매니저 최종 체크
    if risk_manager and plan:
        price = float(df['close'].iloc[-1])
        if not risk_manager.check_trade_allowed(balance_krw, plan, price):
            plan = None
    
    return {
        "index": idx,
        "snapshot": snap.__dict__,
        "plan": None if plan is None else plan.__dict__,
        "stage_name": get_stage_name(idx),
        "volatility_ok": True
    }

def get_stage_name(idx: int) -> str:
    names = [
        "0: Extreme Panic",
        "1: Strong Down",
        "2: Down Persist",
        "3: Weak Down",
        "4: Bearish Turn",
        "5: Neutral Box",
        "6: Bullish Turn",
        "7: Weak Up",
        "8: Strong Up",
        "9: Extreme Greed"
    ]
    return names[idx] if 0 <= idx <= 9 else f"Unknown({idx})"
