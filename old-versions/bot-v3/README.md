# Binance-Futures-Trading-Bot [![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=Check%20out%20this%20free%20Binance%20Trading%20Bot%20I%20found%20on%20Github%20&url=https://github.com/conor19w/Binance-Futures-Trading-Bot&hashtags=Trading,Bot,Trading_Bot,Cryptocurrency_Trading_Bot,Crypto,Bitcoin,Ethereum,Cryptocurrency,Binance,DOGE,dogecoin) #
## Technical Analysis driven Crypto Trading bot on Binance Futures 📈 ₿ 🚀 
[__Join My public Discord Server__](https://discord.gg/jBu6thyP66) __&__ [__Follow The Twitter__](https://twitter.com/futures_bot)
* Comes with 11 pre-built strategies found in [TradingStrats.py](https://github.com/conor19w/Binance-Futures-Trading-Bot/blob/main/TradingStrats.py)
* See Documentation below to implement your TA strategies. (currently working on new documentation)
* If you enjoy the repo please share it around to friends & tweet about it using the tweet button above 😃   
or [Buy me a Coffee](https://www.buymeacoffee.com/conor19w)  

# This Bot currently only works on windows OS, in future I hope to support linux but I don't have the time right now
___
#### This Bot utilizes: ####
* [python-Binance](https://python-binance.readthedocs.io/en/latest/) Client to execute orders and pull data from Binance
* [ta](https://technical-analysis-library-in-python.readthedocs.io/en/latest/) library for Technical indicators
* [plotly](https://plotly.com/graphing-libraries/) for generating interactive Trade graphs.  
* [tabulate](https://pypi.org/project/tabulate/) for logging trades in a table format
* [colorlog](https://pypi.org/project/colorlog/) for adding colour to logs
___
##### Important for live trading on windows: #####  
[Set up windows to sync time once a day](https://www.makeuseof.com/tag/synchronise-computer-time-internet-custom-schedule-windows-7/#:~:text=Go%20to%20%3E%20Start%20and%20type,on%20the%20right%20hand%20side) if you don't do this binance will eventually reject orders with a timestamp error.
___
#### Creating Custom Strategies: ####
__Strategies are implemented in TradingStrats.py as functions and then referenced in Bot_Class.Bot.make_decision()__
* `Make_decision()` must return `Trade_Direction, stop_loss_val, take_profit_val` for the strategy to work properly
* You might draw inspiration for a strategy from one of the samples in __TradingStrats.py__  
Docs are being updated currently for the new bot  
[Create Custom Strategies](docs/Custom_Strategies.pdf)  
[Create Custom TP/SL functions](docs/Custom_TP_SL_functions.pdf)
---
## Binance Setup ##
* Create a [Binance Account](https://accounts.binance.com/en/register?ref=BKR8BMMP) (This link uses my referral which gives you 5% kickback on trades & would be greatly appreciated)
* __Enable Two-factor Authentication in the security section to keep your crypto safe.__
* Create a new API key under the API Management section.
*  [✓] Read Info [✓] Enable Trading [✓] Enable Futures [X] Enable Withdrawals
* Fill in your api keys into api_secret and api_key in __live_trading_config.py__
---
### Running the live trading bot ###
__Run strategies at your own risk I am not responsible for your trading decisions, futures are risky and proper risk management should be adhered to at all times, always have a stoploss__
```commandline
python3 live_trading.py
```
___
## Settings are in __live_trading_config.py__ ##
* Trade a single position at a time by setting `max_number_of_positions = 1`, to trade multiple coins just increment this value.
* `leverage` and `order_size` should be changed according to your preference
* `symbols_to_trade[]` is a list of the symbols you wish to trade, If you wish to trade all symbols set `trade_all_symbols = True`.
* __Trailing stop: set `use_trailing_stop = True` and change `trailing_stop_callback` to suit your strategy to use the trailing stop 
(Min val .001 i.e .1%, Max 5 i.e. 5%). The trailing stop will be placed when the take profit value margin of increase/decrease is reached from your strategy__.
* To close a trade based off a condition check_close_pos() must return a close_pos flag. (Not functioning currently, this needs updated for new bot)
* `trading_strategy` is the name of the strategy you want to use, see below for adding your own custom strategies.
* There are 11 default strategies to choose from: `StochRSIMACD, tripleEMAStochasticRSIATR, tripleEMA, breakout, stochBB, goldenCross,
candle_wick, fibMACD, EMA_cross, heikin_ashi_ema2 & heikin_ashi_ema`
* TP_SL_choice is the type of take profit and stop loss you want to use valid choices are: `USDT, %, x (ATR), x (Swing High/Low) level 1,
x (Swing High/Low) level 2, x (Swing High/Low) level 3, x (Swing Close) level 1, x (Swing Close) level 2, x (Swing Close) level 3`
* `SL_mult` and `TP_mult` are multipliers for the `TP_SL_choice`  
__Example:__  
TP_SL_choice = 'USDT'  
SL_mult = 1  
TP_mult = 2  
This configuration will set TP and SL values at $1 loss and $2 gain respectively  
* Choose the `interval` you want to trade, valid intervals are: `1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d`.


___
### YouTube Channels with Strategy Ideas: ###
[__Quantopian Lectures__](https://www.youtube.com/playlist?list=PLRFLF1OxMm_UL7WUWM31iynp0jMVf_vLW) | [__Silicon Trader__](https://www.youtube.com/channel/UCVRGsC6JVsB8F6HE_xjLyJg) | [__Trade Pro__](https://www.youtube.com/channel/UCrXjzUN6EtlyhaaAerbPfkQ) | [__Strategy Testing__](https://www.youtube.com/c/TradingStrategyTesting) | [__Trading Journal__](https://www.youtube.com/c/TradingJournal1) |  [__The Moving Average__](https://www.youtube.com/channel/UCYFQzaZyTUzY-Tiytyv3HhA)  

---
## TO-DO List: ##
[Trello Board](https://trello.com/invite/b/iagTNiv0/80cc1828bdac439ed813cc54c9698c06/github-bot)

---
# Contact me [![Tweet](https://img.shields.io/twitter/url/http/shields.io.svg?style=social)](https://twitter.com/intent/tweet?text=Check%20out%20this%20free%20Binance%20Trading%20Bot%20I%20found%20on%20Github%20&url=https://github.com/conor19w/Binance-Futures-Trading-Bot&hashtags=Trading,Bot,Trading_Bot,Cryptocurrency_Trading_Bot,Crypto,Bitcoin,Ethereum,Cryptocurrency,Binance,DOGE,dogecoin) #
* Prioritise your [Trello](https://trello.com/invite/b/iagTNiv0/80cc1828bdac439ed813cc54c9698c06/github-bot) ticket with a [one time payment](https://github.com/sponsors/conor19w)  
* Get Custom Strategies made to your specifications by reaching out to me on discord for a quote price.
* If you have any queries about anything, or need me to explain any blocks of code please reach out to me on [Discord](https://discord.gg/jBu6thyP66).
* If you have any suggestions or requests please reach out to me as well.
[__Join My public Discord Server__](https://discord.gg/jBu6thyP66) __&__ [__Follow The Twitter__](https://twitter.com/futures_bot)

