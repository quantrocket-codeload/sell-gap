# Copyright 2021 QuantRocket LLC - All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import zipline.api as algo
from zipline.pipeline import Pipeline
from zipline.pipeline.factors import AverageDollarVolume, SimpleMovingAverage, ExponentialWeightedMovingStdDev
from zipline.pipeline.data.equity_pricing import EquityPricing
from zipline.pipeline.data.master import SecuritiesMaster
from zipline.finance.execution import MarketOrder, LimitOrder
from zipline.finance.order import ORDER_STATUS
from zipline.finance import slippage, commission
from quantrocket.realtime import collect_market_data
from codeload.sell_gap.pipeline import make_pipeline

def initialize(context):
    """
    Called once at the start of a backtest, and once per day at
    the start of live trading.
    """
    # Attach the pipeline to the algo
    algo.attach_pipeline(make_pipeline(), 'pipeline')

    # Set SPY as benchmark
    algo.set_benchmark(algo.sid("FIBBG000BDTBL9"))

    # identify down gaps immediately after the opening
    algo.schedule_function(
        find_down_gaps,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=1),
    )

    # at 9:40, short stocks that gapped down
    algo.schedule_function(
        short_down_gaps,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=10),
    )

    # close positions 5 minutes before the close
    algo.schedule_function(
        close_positions,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(minutes=5),
    )

    # Set commissions and slippage
    algo.set_commission(
        commission.PerShare(cost=0.0))
    algo.set_slippage(
        slippage.FixedBasisPointsSlippage(
            basis_points=3.0))

def before_trading_start(context, data):
    """
    Called every day before market open. Gathers today's pipeline
    output and initiates real-time data collection (in live trading).
    """
    context.candidates = algo.pipeline_output('pipeline')
    context.assets_to_short = []
    context.target_value_per_position = -50e3

    # Start real-time data collection if we are in live trading
    if algo.get_environment("arena") == "trade":

        # start real-time tick data collection for our candidates...
        sids = [asset.real_sid for asset in context.candidates.index]

        if sids:

            # collect the trade/volume data
            collect_market_data(
                "us-stk-realtime",
                sids=sids,
                until="09:32:00 America/New_York")

            # ...and point Zipline to the derived aggregate db
            # For Interactive Brokers databases:
            algo.set_realtime_db(
                "us-stk-realtime-1min",
                fields={
                    "close": "LastPriceClose",
                    "open": "LastPriceOpen",
                    "high": "LastPriceHigh",
                    "low": "LastPriceLow",
                    "volume": "LastSizeSum"})
            # For Alpaca databases:
            # algo.set_realtime_db(
            #     "us-stk-realtime-1min",
            #     fields={
            #         "close": "MinuteCloseClose",
            #         "open": "MinuteOpenOpen",
            #         "high": "MinuteHighHigh",
            #         "low": "MinuteLowLow",
            #         "volume": "MinuteVolumeSum"})

def find_down_gaps(context, data):
    """
    Identify stocks that gapped down below their moving average.
    """

    if len(context.candidates) == 0:
        return

    today_opens = data.current(context.candidates.index, 'open')
    prior_lows = context.candidates["prior_low"]
    stds = context.candidates["std"]

    # find stocks that opened sufficiently below the prior day's low...
    gapped_down = today_opens < (prior_lows - stds)

    # ...and are now below their moving averages
    are_below_mavg = (today_opens < context.candidates["mavg"])

    assets_to_short = context.candidates[
        gapped_down
        & are_below_mavg
        ]

    # Limit to the top 10 by std
    assets_to_short = assets_to_short.sort_values(
        "std", ascending=False).iloc[:10].index

    context.assets_to_short = assets_to_short

def short_down_gaps(context, data):
    """
    Short the stocks that gapped down.
    """
    for asset in context.assets_to_short:

        # Sell with market order
        algo.order_value(
            asset,
            context.target_value_per_position,
            style=MarketOrder() # for IBKR, specify exchange (e.g. exchange="SMART")
        )

def close_positions(context, data):
    """
    Closes all positions.
    """
    for asset, position in context.portfolio.positions.items():
        algo.order(
            asset,
            -position.amount,
            style=MarketOrder()
        )
