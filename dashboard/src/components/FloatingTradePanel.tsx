import React from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { Trash2, AlertCircle, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';

export const FloatingTradePanel: React.FC = () => {
  const { activeTrades, closeTrade, closeAllTrades } = useTradeStore();

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(val);
  };

  const formatPercent = (val: number) => {
    const sign = val >= 0 ? '+' : '';
    return `${sign}${val.toFixed(2)}%`;
  };

  return (
    <div className="w-96 border-l border-gray-800 bg-gray-950 flex flex-col h-full overflow-hidden select-none shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-bold tracking-widest text-gray-200 uppercase font-mono">Live Trades</h2>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">
            {activeTrades.length} ACTIVE
          </span>
        </div>
        {activeTrades.length > 0 && (
          <button
            onClick={closeAllTrades}
            className="text-[10px] px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 font-mono transition-all"
          >
            Close All
          </button>
        )}
      </div>

      {/* Trades List */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2.5">
        {activeTrades.length > 0 ? (
          activeTrades.map((trade) => {
            const isProfit = trade.pnlPercent >= 0;
            const priceColor = trade.ohlc.close >= trade.ohlc.open ? 'text-emerald-400' : 'text-rose-400';

            return (
              <div
                key={trade.id}
                className="bg-gray-900 border border-gray-850 rounded-lg p-3 hover:border-gray-700 transition-all font-mono"
              >
                {/* Symbol & Strategy */}
                <div className="flex items-center justify-between pb-2 border-b border-gray-850">
                  <div>
                    <h4 className="text-sm font-bold text-gray-200">{trade.symbol}</h4>
                    <p className="text-[10px] text-gray-500 uppercase mt-0.5">{trade.strategy}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600">{trade.timestamp}</span>
                    <button
                      onClick={() => closeTrade(trade.id)}
                      className="p-1 rounded text-gray-600 hover:text-rose-400 hover:bg-rose-500/10 transition-all"
                      title="Close Trade"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* OHLC Stats */}
                <div className="grid grid-cols-4 gap-1 py-2 text-[10px] text-gray-500 border-b border-gray-850">
                  <div>
                    <span className="block text-[8px] uppercase">Open</span>
                    <span className="text-gray-300">${trade.ohlc.open.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[8px] uppercase">High</span>
                    <span className="text-gray-300">${trade.ohlc.high.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[8px] uppercase">Low</span>
                    <span className="text-gray-300">${trade.ohlc.low.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[8px] uppercase">Close</span>
                    <span className={`font-semibold ${priceColor}`}>${trade.ohlc.close.toFixed(2)}</span>
                  </div>
                </div>

                {/* Entry / Exit / PNL */}
                <div className="pt-2 flex items-center justify-between text-xs">
                  <div>
                    <span className="block text-[8px] text-gray-500 uppercase">Exposure</span>
                    <span className="text-gray-300 font-semibold">{formatCurrency(trade.entryValue)}</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-[8px] text-gray-500 uppercase">PnL</span>
                    <div className="flex items-center gap-1.5 justify-end">
                      {isProfit ? (
                        <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
                      )}
                      <span className={`font-bold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {formatPercent(trade.pnlPercent * 100)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
            <DollarSign className="w-8 h-8 text-gray-700 animate-pulse mb-2" />
            <p className="text-xs text-gray-600 font-mono">NO ACTIVE LIVE TRADES</p>
            <p className="text-[10px] text-gray-700 font-mono mt-1">Activate a strategy and select scope to trade.</p>
          </div>
        )}
      </div>
    </div>
  );
};
