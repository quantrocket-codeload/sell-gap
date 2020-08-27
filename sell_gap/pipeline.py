# Copyright 2020 QuantRocket LLC - All Rights Reserved
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

from zipline.pipeline import Pipeline
from zipline.pipeline.factors import AverageDollarVolume, SimpleMovingAverage, ExponentialWeightedMovingStdDev
from zipline.pipeline.data.equity_pricing import EquityPricing
from zipline.pipeline.data.master import SecuritiesMaster

def make_pipeline():
    """
    Create a pipeline with the following rules:

    screen
    - common stocks only
    - must be liquid (top 10% by dollar volume)
    - must be above 20-day moving average
    - must not be too cheap or too expensive

    columns
    - 20-day moving average
    - prior low
    - standard deviation of closing prices
    """
    mavg = SimpleMovingAverage(
        window_length = 20, inputs = [EquityPricing.close])

    are_common_stocks = SecuritiesMaster.usstock_SecurityType2.latest.eq(
        "Common Stock")
    are_liquid = AverageDollarVolume(window_length=30).percentile_between(90, 100)
    are_above_mavg = EquityPricing.close.latest > mavg
    are_not_too_cheap = EquityPricing.close.latest > 10
    are_not_too_expensive = EquityPricing.close.latest < 2000

    pipeline = Pipeline(
        columns = {
            "mavg": mavg,
            "prior_low": EquityPricing.low.latest,
            "std": ExponentialWeightedMovingStdDev(
                inputs=[EquityPricing.close],
                window_length=63,
                decay_rate=0.99)
        },
        screen=(
            are_common_stocks
            & are_liquid
            & are_above_mavg
            & are_not_too_cheap
            & are_not_too_expensive
        )
    )

    return pipeline
