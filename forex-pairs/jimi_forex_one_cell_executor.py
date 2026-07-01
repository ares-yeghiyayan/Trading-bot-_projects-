# ============================================================
# JIMI FOREX ONE-CELL EXECUTOR
# For Jupyter Notebook + MetaTrader 5
# Forex only. Gold/XAUUSD is blocked.
# ============================================================

# Run once if needed:
# !pip install MetaTrader5 pandas

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import re
from IPython.display import display

# ============================================================
# 1) فقط اینجا را از چت من کپی‌پیست کن
# ============================================================

JIMI_COMMANDS = """
[ USDJPY = 162.30 long | SL=161.88 | TP=163.05 | LOT=0.01 | EXP=0 | COMMENT=Jimi_UJ_BuyPullback ]
"""

# ============================================================
# 2) تنظیمات امنیتی
# ============================================================

DRY_RUN = False
# True  = فقط تست می‌کند، چیزی اجرا نمی‌کند
# False = واقعاً حذف/بستن/سفارش‌گذاری انجام می‌دهد

ALLOW_REAL_ACCOUNT = False
# برای حساب واقعی فعلاً False بماند

MAGIC_NUMBER = 260630
MANAGED_MAGIC_NUMBERS = [260630]

# فقط جفت‌ارزها؛ طلا عمداً نیست
ALLOW_SYMBOLS = [
    "GBPUSD",
    "EURUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
]

BLOCK_GOLD_AND_CRYPTO = True

MAX_ORDERS_PER_RUN = 5
MAX_SPREAD_PIPS = 3.0

DEFAULT_LOT = 0.01
DEFAULT_EXPIRY_HOURS = 12

DEVIATION_POINTS = 30

# ============================================================
# 3) Signal reconciliation
# ============================================================

RECONCILE_OLD_SIGNALS = True

DELETE_OPPOSITE_PENDING_ORDERS = True
CLOSE_OPPOSITE_POSITIONS = True

# اگر برای همان نماد قبلاً pending از Jimi وجود داشته باشد،
# آن را حذف می‌کند و سیگنال جدید را جایگزین می‌کند.
REPLACE_EXISTING_PENDING_SAME_SYMBOL = True

# اگر position فعال هم‌جهت وجود داشته باشد،
# سفارش جدید را بلاک می‌کند تا ریسک دوبل نشود.
BLOCK_NEW_ORDER_IF_SAME_SIDE_POSITION_EXISTS = True

ONLY_MANAGE_JIMI_ORDERS = True

# ============================================================
# 4) اتصال به MT5
# ============================================================

if not mt5.initialize():
    raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

account = mt5.account_info()

if account is None:
    raise RuntimeError("No MT5 account detected. Open MT5 and log in first.")

print("Connected to MT5")
print("Account:", account.login)
print("Server:", account.server)
print("Balance:", account.balance)
print("Equity:", account.equity)
print("Currency:", account.currency)
print("Trade Mode:", account.trade_mode)

if account.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL and not ALLOW_REAL_ACCOUNT:
    raise RuntimeError(
        "Real account detected. Blocked for safety. "
        "Keep ALLOW_REAL_ACCOUNT=False unless you fully understand the risk."
    )

# ============================================================
# 5) Helper functions
# ============================================================

SUCCESS_RETCODES = {
    mt5.TRADE_RETCODE_DONE,
    mt5.TRADE_RETCODE_PLACED,
    mt5.TRADE_RETCODE_DONE_PARTIAL,
}


def pip_size(symbol_info):
    # EURUSD 5 digits -> 0.0001
    # USDJPY 3 digits -> 0.01
    if symbol_info.digits in [3, 5]:
        return symbol_info.point * 10
    return symbol_info.point


def clean_line(line):
    line = line.strip()
    line = line.replace("[", "").replace("]", "")
    line = line.replace(",", ".")
    line = re.sub(r"\s+", " ", line)
    return line


def get_value(patterns, text, default=None, required=False, name="value"):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    if required:
        raise ValueError(f"Missing required field: {name} in line: {text}")

    return default


def is_gold_or_crypto(symbol):
    s = symbol.upper()
    blocked_terms = ["XAU", "GOLD", "BTC", "ETH", "SOL", "LTC", "XAG", "SILVER"]
    return any(term in s for term in blocked_terms)


def ensure_allowed_symbol(symbol):
    symbol = symbol.upper()

    if BLOCK_GOLD_AND_CRYPTO and is_gold_or_crypto(symbol):
        raise ValueError(f"{symbol}: blocked. This script is forex only. Use the gold script for XAUUSD.")

    if symbol not in ALLOW_SYMBOLS:
        raise ValueError(f"{symbol}: not in ALLOW_SYMBOLS. Allowed: {ALLOW_SYMBOLS}")

    info = mt5.symbol_info(symbol)

    if info is None:
        raise ValueError(f"{symbol}: symbol not found in MT5.")

    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise ValueError(f"{symbol}: cannot select symbol in MT5.")

    return symbol


def direction_to_side(direction):
    direction = direction.lower()

    if direction in ["long", "buy"]:
        return "BUY"

    if direction in ["short", "sell"]:
        return "SELL"

    raise ValueError(f"Unknown direction: {direction}")


def pending_order_side(order_type):
    buy_types = [
        mt5.ORDER_TYPE_BUY_LIMIT,
        mt5.ORDER_TYPE_BUY_STOP,
    ]

    sell_types = [
        mt5.ORDER_TYPE_SELL_LIMIT,
        mt5.ORDER_TYPE_SELL_STOP,
    ]

    if order_type in buy_types:
        return "BUY"

    if order_type in sell_types:
        return "SELL"

    return None


def position_side(position_type):
    if position_type == mt5.POSITION_TYPE_BUY:
        return "BUY"

    if position_type == mt5.POSITION_TYPE_SELL:
        return "SELL"

    return None


def is_jimi_managed(item):
    comment = getattr(item, "comment", "") or ""
    magic = getattr(item, "magic", None)

    if not ONLY_MANAGE_JIMI_ORDERS:
        return True

    return (
        magic in MANAGED_MAGIC_NUMBERS
        or magic == MAGIC_NUMBER
        or str(comment).lower().startswith("jimi")
        or "jimi" in str(comment).lower()
    )


def normalize_comment(comment):
    comment = str(comment).strip()
    if not comment:
        comment = "Jimi_Forex"
    if "jimi" not in comment.lower():
        comment = "Jimi_" + comment
    return comment[:31]


# ============================================================
# 6) Parse commands
# ============================================================

def parse_jimi_commands(text):
    orders = []

    for raw_line in text.strip().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        line = clean_line(line)

        symbol = get_value(
            [r"^\s*([A-Za-z0-9._-]+)\s*="],
            line,
            required=True,
            name="symbol"
        ).upper()

        symbol = ensure_allowed_symbol(symbol)

        entry_raw = get_value(
            [
                r"=\s*(market|mkt|now|[0-9]+(?:\.[0-9]+)?)",
            ],
            line,
            required=True,
            name="entry_or_market"
        )

        direction = get_value(
            [r"\b(long|buy|short|sell)\b"],
            line,
            required=True,
            name="direction"
        ).lower()

        sl = get_value(
            [r"\bsl\s*=?\s*([0-9]+(?:\.[0-9]+)?)"],
            line,
            required=True,
            name="SL"
        )

        tp = get_value(
            [r"\btp\s*=?\s*([0-9]+(?:\.[0-9]+)?)"],
            line,
            required=True,
            name="TP"
        )

        lot = get_value(
            [
                r"\blot\s*=?\s*([0-9]+(?:\.[0-9]+)?)",
                r"\bvolume\s*=?\s*([0-9]+(?:\.[0-9]+)?)",
            ],
            line,
            default=str(DEFAULT_LOT),
            required=False,
            name="LOT"
        )

        exp = get_value(
            [
                r"\bexp\s*=?\s*([0-9]+(?:\.[0-9]+)?)",
                r"\bexpiry\s*=?\s*([0-9]+(?:\.[0-9]+)?)",
            ],
            line,
            default=str(DEFAULT_EXPIRY_HOURS),
            required=False,
            name="EXP"
        )

        comment = get_value(
            [r"\bcomment\s*=?\s*([A-Za-z0-9_\-]+)"],
            line,
            default="Jimi_Forex",
            required=False,
            name="comment"
        )

        entry_raw_lower = str(entry_raw).lower()

        if entry_raw_lower in ["market", "mkt", "now"]:
            order_kind = "MARKET"
            entry = None
        else:
            order_kind = "PENDING"
            entry = float(entry_raw)

        orders.append({
            "symbol": symbol,
            "order_kind": order_kind,
            "direction": direction,
            "side": direction_to_side(direction),
            "entry": entry,
            "sl": float(sl),
            "tp": float(tp),
            "lot": float(lot),
            "expiry_hours": int(float(exp)),
            "comment": normalize_comment(comment),
            "raw": raw_line,
        })

    return orders


# ============================================================
# 7) Infer type and validate
# ============================================================

def infer_order_type(order):
    symbol = order["symbol"]
    side = order["side"]
    order_kind = order["order_kind"]

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        raise ValueError(f"{symbol}: no tick data")

    if order_kind == "MARKET":
        if side == "BUY":
            return mt5.ORDER_TYPE_BUY, "BUY_MARKET"
        if side == "SELL":
            return mt5.ORDER_TYPE_SELL, "SELL_MARKET"

    entry = order["entry"]

    if side == "BUY":
        if entry < tick.ask:
            return mt5.ORDER_TYPE_BUY_LIMIT, "BUY_LIMIT"
        elif entry > tick.ask:
            return mt5.ORDER_TYPE_BUY_STOP, "BUY_STOP"
        else:
            raise ValueError(f"{symbol}: entry equals current ask. Pending order invalid.")

    if side == "SELL":
        if entry > tick.bid:
            return mt5.ORDER_TYPE_SELL_LIMIT, "SELL_LIMIT"
        elif entry < tick.bid:
            return mt5.ORDER_TYPE_SELL_STOP, "SELL_STOP"
        else:
            raise ValueError(f"{symbol}: entry equals current bid. Pending order invalid.")

    raise ValueError(f"{symbol}: cannot infer order type.")


def get_reference_price_for_validation(order, tick):
    if order["order_kind"] == "MARKET":
        if order["side"] == "BUY":
            return tick.ask
        return tick.bid

    return order["entry"]


def validate_order(order):
    symbol = order["symbol"]

    try:
        ensure_allowed_symbol(symbol)
    except Exception as e:
        return False, str(e)

    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)

    if info is None:
        return False, f"{symbol}: symbol info not found"

    if tick is None:
        return False, f"{symbol}: tick not found"

    pip = pip_size(info)
    spread_pips = (tick.ask - tick.bid) / pip

    if spread_pips > MAX_SPREAD_PIPS:
        return False, f"{symbol}: spread too high: {spread_pips:.2f} pips | max={MAX_SPREAD_PIPS}"

    try:
        order_type, type_text = infer_order_type(order)
        order["type"] = order_type
        order["type_text"] = type_text
    except Exception as e:
        return False, str(e)

    ref_price = get_reference_price_for_validation(order, tick)
    sl = order["sl"]
    tp = order["tp"]
    lot = order["lot"]
    side = order["side"]

    if side == "BUY":
        if not sl < ref_price:
            return False, f"{symbol}: BUY SL must be below reference price"
        if not tp > ref_price:
            return False, f"{symbol}: BUY TP must be above reference price"

    if side == "SELL":
        if not sl > ref_price:
            return False, f"{symbol}: SELL SL must be above reference price"
        if not tp < ref_price:
            return False, f"{symbol}: SELL TP must be below reference price"

    if lot < info.volume_min:
        return False, f"{symbol}: lot below minimum. Lot={lot}, Min={info.volume_min}"

    if lot > info.volume_max:
        return False, f"{symbol}: lot above maximum. Lot={lot}, Max={info.volume_max}"

    step_ratio = lot / info.volume_step
    if abs(step_ratio - round(step_ratio)) > 1e-9:
        return False, f"{symbol}: lot must match broker step {info.volume_step}"

    broker_min_distance = info.trade_stops_level * info.point

    if broker_min_distance > 0:
        if abs(ref_price - sl) < broker_min_distance:
            return False, f"{symbol}: SL violates broker minimum stop distance"

        if abs(ref_price - tp) < broker_min_distance:
            return False, f"{symbol}: TP violates broker minimum stop distance"

        if order["order_kind"] == "PENDING":
            if side == "BUY":
                distance_from_market = abs(order["entry"] - tick.ask)
            else:
                distance_from_market = abs(order["entry"] - tick.bid)

            if distance_from_market < broker_min_distance:
                return False, f"{symbol}: pending entry too close to current price"

    return True, (
        f"{symbol}: OK | {order['type_text']} | "
        f"Bid={tick.bid} Ask={tick.ask} Spread={spread_pips:.2f} pips"
    )


# ============================================================
# 8) Build requests
# ============================================================

def build_pending_request(order):
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": order["symbol"],
        "volume": order["lot"],
        "type": order["type"],
        "price": order["entry"],
        "sl": order["sl"],
        "tp": order["tp"],
        "deviation": DEVIATION_POINTS,
        "magic": MAGIC_NUMBER,
        "comment": order["comment"],
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    if order["expiry_hours"] and order["expiry_hours"] > 0:
        expiration = datetime.now() + timedelta(hours=order["expiry_hours"])
        request["type_time"] = mt5.ORDER_TIME_SPECIFIED
        request["expiration"] = int(expiration.timestamp())
    else:
        request["type_time"] = mt5.ORDER_TIME_GTC

    return request


def build_market_request(order):
    symbol = order["symbol"]
    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        raise RuntimeError(f"{symbol}: no tick data for market order")

    if order["side"] == "BUY":
        price = tick.ask
    else:
        price = tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": order["lot"],
        "type": order["type"],
        "price": price,
        "sl": order["sl"],
        "tp": order["tp"],
        "deviation": DEVIATION_POINTS,
        "magic": MAGIC_NUMBER,
        "comment": order["comment"],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    return request


def build_request(order):
    if order["order_kind"] == "PENDING":
        return build_pending_request(order)

    if order["order_kind"] == "MARKET":
        return build_market_request(order)

    raise RuntimeError(f"Unknown order_kind: {order['order_kind']}")


# ============================================================
# 9) Reconciliation functions
# ============================================================

def delete_pending_order(order):
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": order.ticket,
        "magic": MAGIC_NUMBER,
        "comment": "Jimi_delete_old",
    }

    return mt5.order_send(request)


def send_close_position_with_fallback(request):
    filling_modes = [
        mt5.ORDER_FILLING_RETURN,
        mt5.ORDER_FILLING_IOC,
        mt5.ORDER_FILLING_FOK,
    ]

    last_result = None

    for filling in filling_modes:
        request["type_filling"] = filling
        result = mt5.order_send(request)
        last_result = result

        if result is not None and result.retcode in SUCCESS_RETCODES:
            return result

    return last_result


def close_position(position):
    symbol = position.symbol
    volume = position.volume

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"{symbol}: no tick data for closing position")

    if position.type == mt5.POSITION_TYPE_BUY:
        close_type = mt5.ORDER_TYPE_SELL
        close_price = tick.bid
    elif position.type == mt5.POSITION_TYPE_SELL:
        close_type = mt5.ORDER_TYPE_BUY
        close_price = tick.ask
    else:
        raise RuntimeError(f"{symbol}: unknown position type")

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": close_type,
        "position": position.ticket,
        "price": close_price,
        "deviation": DEVIATION_POINTS,
        "magic": MAGIC_NUMBER,
        "comment": "Jimi_close_opposite",
        "type_time": mt5.ORDER_TIME_GTC,
    }

    return send_close_position_with_fallback(request)


def get_jimi_pending_orders_for_symbol(symbol):
    pending_orders = mt5.orders_get(symbol=symbol)
    if not pending_orders:
        return []

    return [o for o in pending_orders if is_jimi_managed(o)]


def get_jimi_positions_for_symbol(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return []

    return [p for p in positions if is_jimi_managed(p)]


def has_same_side_position(order):
    symbol = order["symbol"]
    new_side = order["side"]

    positions = get_jimi_positions_for_symbol(symbol)

    for p in positions:
        old_side = position_side(p.type)
        if old_side == new_side:
            return True, p

    return False, None


def reconcile_old_signals(new_orders):
    reconciliation_results = []

    for new_order in new_orders:
        symbol = new_order["symbol"]
        new_side = new_order["side"]
        opposite_side = "SELL" if new_side == "BUY" else "BUY"

        # 1) Delete old pending orders for same symbol
        pending_orders = get_jimi_pending_orders_for_symbol(symbol)

        for old_order in pending_orders:
            old_side = pending_order_side(old_order.type)

            should_delete = False
            reason = None

            if REPLACE_EXISTING_PENDING_SAME_SYMBOL:
                should_delete = True
                reason = "replace_same_symbol_pending"

            elif DELETE_OPPOSITE_PENDING_ORDERS and old_side == opposite_side:
                should_delete = True
                reason = "delete_opposite_pending"

            if should_delete:
                if DRY_RUN:
                    reconciliation_results.append({
                        "symbol": symbol,
                        "action": "DRY_DELETE_PENDING",
                        "ticket": old_order.ticket,
                        "old_side": old_side,
                        "new_side": new_side,
                        "reason": reason,
                        "status": "DRY_RUN_ONLY",
                    })
                else:
                    result = delete_pending_order(old_order)
                    reconciliation_results.append({
                        "symbol": symbol,
                        "action": "DELETE_PENDING",
                        "ticket": old_order.ticket,
                        "old_side": old_side,
                        "new_side": new_side,
                        "reason": reason,
                        "retcode": getattr(result, "retcode", None),
                        "message": getattr(result, "comment", None),
                    })

        # 2) Close opposite active positions
        if CLOSE_OPPOSITE_POSITIONS:
            positions = get_jimi_positions_for_symbol(symbol)

            for old_position in positions:
                old_side = position_side(old_position.type)

                if old_side == opposite_side:
                    if DRY_RUN:
                        reconciliation_results.append({
                            "symbol": symbol,
                            "action": "DRY_CLOSE_POSITION",
                            "ticket": old_position.ticket,
                            "old_side": old_side,
                            "new_side": new_side,
                            "volume": old_position.volume,
                            "profit": old_position.profit,
                            "status": "DRY_RUN_ONLY",
                        })
                    else:
                        result = close_position(old_position)
                        reconciliation_results.append({
                            "symbol": symbol,
                            "action": "CLOSE_POSITION",
                            "ticket": old_position.ticket,
                            "old_side": old_side,
                            "new_side": new_side,
                            "volume": old_position.volume,
                            "profit_before_close": old_position.profit,
                            "retcode": getattr(result, "retcode", None),
                            "message": getattr(result, "comment", None),
                        })

    return reconciliation_results


# ============================================================
# 10) Parse
# ============================================================

orders = parse_jimi_commands(JIMI_COMMANDS)

if len(orders) == 0:
    raise RuntimeError("No orders found in JIMI_COMMANDS.")

if len(orders) > MAX_ORDERS_PER_RUN:
    raise RuntimeError(f"Too many orders. Max allowed: {MAX_ORDERS_PER_RUN}")

print("\nParsed Commands:")
display(pd.DataFrame([{
    "symbol": o["symbol"],
    "kind": o["order_kind"],
    "direction": o["direction"],
    "side": o["side"],
    "entry": o["entry"],
    "sl": o["sl"],
    "tp": o["tp"],
    "lot": o["lot"],
    "expiry_hours": o["expiry_hours"],
    "comment": o["comment"],
} for o in orders]))

# ============================================================
# 11) Validate
# ============================================================

validation_rows = []

for o in orders:
    ok, msg = validate_order(o)

    validation_rows.append({
        "symbol": o["symbol"],
        "kind": o["order_kind"],
        "direction": o["direction"],
        "pending_or_market_type": o.get("type_text"),
        "entry": o["entry"],
        "sl": o["sl"],
        "tp": o["tp"],
        "lot": o["lot"],
        "valid": ok,
        "message": msg,
    })

print("\nValidation:")
display(pd.DataFrame(validation_rows))

if not all(row["valid"] for row in validation_rows):
    raise RuntimeError("Validation failed. Fix the blocked order before execution.")

# ============================================================
# 12) Reconcile old signals
# ============================================================

if RECONCILE_OLD_SIGNALS:
    print("\nReconciling Old Signals:")
    reconciliation = reconcile_old_signals(orders)

    if reconciliation:
        display(pd.DataFrame(reconciliation))
    else:
        print("No old opposite/same-symbol Jimi orders found.")

# ============================================================
# 13) Send or Dry Run
# ============================================================

results = []

for o in orders:
    same_side_exists, same_side_position = has_same_side_position(o)

    if same_side_exists and BLOCK_NEW_ORDER_IF_SAME_SIDE_POSITION_EXISTS:
        results.append({
            "symbol": o["symbol"],
            "type": o.get("type_text"),
            "entry": o["entry"],
            "status": "BLOCKED_SAME_SIDE_POSITION_EXISTS",
            "message": (
                f"Same-side active Jimi position already exists. "
                f"Ticket={same_side_position.ticket}, Volume={same_side_position.volume}, "
                f"Profit={same_side_position.profit}"
            ),
        })
        continue

    ok, msg = validate_order(o)

    if not ok:
        results.append({
            "symbol": o["symbol"],
            "type": o.get("type_text"),
            "entry": o["entry"],
            "status": "BLOCKED",
            "message": msg,
        })
        continue

    request = build_request(o)

    if DRY_RUN:
        results.append({
            "symbol": o["symbol"],
            "kind": o["order_kind"],
            "type": o["type_text"],
            "entry": o["entry"],
            "sl": o["sl"],
            "tp": o["tp"],
            "lot": o["lot"],
            "status": "DRY_RUN_ONLY",
            "message": "Valid but not sent because DRY_RUN=True",
        })
    else:
        result = mt5.order_send(request)

        if result is None:
            results.append({
                "symbol": o["symbol"],
                "kind": o["order_kind"],
                "type": o["type_text"],
                "entry": o["entry"],
                "status": "ERROR",
                "message": f"order_send returned None: {mt5.last_error()}",
            })
        else:
            results.append({
                "symbol": o["symbol"],
                "kind": o["order_kind"],
                "type": o["type_text"],
                "entry": o["entry"],
                "status": "SENT" if result.retcode in SUCCESS_RETCODES else "FAILED",
                "retcode": result.retcode,
                "message": result.comment,
                "order_ticket": getattr(result, "order", None),
            })

print("\nExecution Result:")
display(pd.DataFrame(results))

# ============================================================
# 14) Show current Jimi forex pending orders and positions
# ============================================================

print("\nCurrent Jimi Forex Pending Orders:")

pending_rows = []
all_pending = mt5.orders_get()

if all_pending:
    for p in all_pending:
        if p.symbol in ALLOW_SYMBOLS and is_jimi_managed(p):
            pending_rows.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "side": pending_order_side(p.type),
                "type": p.type,
                "volume": p.volume_current,
                "price_open": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "comment": p.comment,
                "magic": p.magic,
                "time_setup": datetime.fromtimestamp(p.time_setup),
            })

display(pd.DataFrame(pending_rows))

print("\nCurrent Jimi Forex Active Positions:")

position_rows = []
all_positions = mt5.positions_get()

if all_positions:
    for p in all_positions:
        if p.symbol in ALLOW_SYMBOLS and is_jimi_managed(p):
            position_rows.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "side": position_side(p.type),
                "volume": p.volume,
                "price_open": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "comment": p.comment,
                "magic": p.magic,
                "time": datetime.fromtimestamp(p.time),
            })

display(pd.DataFrame(position_rows))