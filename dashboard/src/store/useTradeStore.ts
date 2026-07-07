import { create } from 'zustand';

export interface OHLC {
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  ohlc: OHLC;
  entryValue: number;
  exitValue: number;
  pnlPercent: number;
  timestamp: string;
}

export interface Strategy {
  id: string;
  name: string;
  category: 'Arbitrage' | 'Timeframe/Directional' | 'Quant/Derivatives';
  description: string;
}

interface TradeStore {
  activeStrategies: Record<string, boolean>;
  assetScopes: Record<string, 'single' | 'top10' | 'multiple'>;
  activeTrades: Trade[];
  toggleStrategy: (strategyId: string) => void;
  setAssetScope: (strategyId: string, scope: 'single' | 'top10' | 'multiple') => void;
  closeAllTrades: () => void;
  closeTrade: (tradeId: string) => void;
  addMockTrade: (strategyId: string, strategyName: string, scope: 'single' | 'top10' | 'multiple') => void;
  updateTradesMock: () => void;
}

// Full 32 strategies definitions array
export const STRATEGIES_DATA: Strategy[] = [
  { id: '1', name: 'Exchange Arbitrage', category: 'Arbitrage', description: 'Cross-exchange bid-ask spread loop' },
  { id: '2', name: 'Cash and Future Arbitrage', category: 'Arbitrage', description: 'Futures basis rate convergence' },
  { id: '3', name: 'Index Arbitrage', category: 'Arbitrage', description: 'Index ETF vs basket component values' },
  { id: '4', name: 'Options Arbitrage', category: 'Arbitrage', description: 'Put-Call parity parity checks' },
  { id: '5', name: 'Interest Rate Arbitrage', category: 'Arbitrage', description: 'Forex forward covered loop' },
  { id: '6', name: 'Yield Curve Arbitrage', category: 'Arbitrage', description: 'Treasury spread curve mispricings' },
  { id: '7', name: 'Stock vs ADR Arbitrage', category: 'Arbitrage', description: 'Cross-border ADR conversion spreads' },
  { id: '8', name: 'Commodity Arbitrage', category: 'Arbitrage', description: 'Calendar spreads on future expirations' },
  { id: '9', name: 'Statistical Arbitrage', category: 'Arbitrage', description: 'Pairs cointegration z-score mean-reversion' },
  { id: '10', name: 'Triangular Arbitrage', category: 'Arbitrage', description: 'Crypto cross-pair trading loops' },
  { id: '11', name: 'ETF vs Stock Arbitrage', category: 'Arbitrage', description: 'Premium vs Net Asset Value' },
  
  { id: '12', name: 'Scalping', category: 'Timeframe/Directional', description: 'Order book bid/ask depth imbalance' },
  { id: '13', name: 'Day Trading', category: 'Timeframe/Directional', description: 'Intraday VWAP deviations' },
  { id: '14', name: 'Swing Trading', category: 'Timeframe/Directional', description: 'MACD multi-day swings' },
  { id: '15', name: 'Position Trading', category: 'Timeframe/Directional', description: 'EMA 50/200 Golden Cross' },
  { id: '16', name: 'Trend Trading', category: 'Timeframe/Directional', description: 'Donchian channel breakouts' },
  { id: '17', name: 'Breakout Trading', category: 'Timeframe/Directional', description: 'Volatility expansion bands' },
  { id: '18', name: 'Range Trading', category: 'Timeframe/Directional', description: 'Bollinger & RSI oscillation limit trade' },
  { id: '19', name: 'News Trading', category: 'Timeframe/Directional', description: 'NLP news headline sentiment spike' },
  { id: '20', name: 'Momentum Trading', category: 'Timeframe/Directional', description: 'Relative strength momentum' },
  { id: '21', name: 'Carry Trading', category: 'Timeframe/Directional', description: 'Forex interest swap yields' },
  
  { id: '22', name: 'HFT Market Making', category: 'Quant/Derivatives', description: 'Avellaneda-Stoikov order book quotes' },
  { id: '23', name: 'Grid Trading', category: 'Quant/Derivatives', description: 'Incremental grids of limits' },
  { id: '24', name: 'Earnings Trading', category: 'Quant/Derivatives', description: 'Earnings report volatility crushes' },
  { id: '25', name: 'Pair Trading', category: 'Quant/Derivatives', description: 'Statistical spread pairings' },
  { id: '26', name: 'Options Trading', category: 'Quant/Derivatives', description: 'Delta-neutral option hedging' },
  { id: '27', name: 'Futures Trading', category: 'Quant/Derivatives', description: 'Contango roll yield capture' },
  { id: '28', name: 'ETF Trading', category: 'Quant/Derivatives', description: 'Relative strength sector rotation' },
  { id: '29', name: 'Martingale', category: 'Quant/Derivatives', description: 'Capped risk multiplication loop' },
  { id: '30', name: 'ICT / SMC', category: 'Quant/Derivatives', description: 'Fair Value Gaps and sweeps' },
  { id: '31', name: 'Algorithmic Trading', category: 'Quant/Derivatives', description: 'TWAP / VWAP execution slices' },
  { id: '32', name: 'Quantitative Trading', category: 'Quant/Derivatives', description: 'Multi-factor quantitative linear alpha' }
];

const TICKERS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'EUR-USD', 'AAPL', 'NVDA', 'TSLA', 'GC=F'];

export const useTradeStore = create<TradeStore>((set) => ({
  activeStrategies: {},
  assetScopes: {},
  activeTrades: [],

  toggleStrategy: (strategyId) => set((state) => {
    const isCurrentlyOn = !!state.activeStrategies[strategyId];
    const newActive = { ...state.activeStrategies, [strategyId]: !isCurrentlyOn };
    
    // Clean up trade logs if toggled off
    let newTrades = state.activeTrades;
    if (isCurrentlyOn) {
      const strategyName = STRATEGIES_DATA.find(s => s.id === strategyId)?.name;
      newTrades = state.activeTrades.filter(t => t.strategy !== strategyName);
    }
    
    return {
      activeStrategies: newActive,
      activeTrades: newTrades
    };
  }),

  setAssetScope: (strategyId, scope) => set((state) => ({
    assetScopes: { ...state.assetScopes, [strategyId]: scope }
  })),

  closeAllTrades: () => set({ activeTrades: [] }),

  closeTrade: (tradeId) => set((state) => ({
    activeTrades: state.activeTrades.filter((t) => t.id !== tradeId)
  })),

  addMockTrade: (strategyId, strategyName, scope) => set((state) => {
    // Generate new trades based on the selected scope
    const count = scope === 'single' ? 1 : scope === 'top10' ? 3 : 5;
    const newTrades: Trade[] = [];

    for (let i = 0; i < count; i++) {
      const symbol = TICKERS[Math.floor(Math.random() * TICKERS.length)];
      const basePrice = symbol.includes('USD') && !symbol.includes('-') ? 1.09 : symbol.includes('USD') ? 3500.0 : 180.0;
      
      const open = basePrice * (1 + (Math.random() - 0.5) * 0.02);
      const high = open * (1 + Math.random() * 0.015);
      const low = open * (1 - Math.random() * 0.015);
      const close = open * (1 + (Math.random() - 0.5) * 0.01);
      
      const entryValue = Math.floor(Math.random() * 9 + 1) * 10000; // $10k to $90k
      
      newTrades.push({
        id: `${strategyId}-${symbol}-${Date.now()}-${i}`,
        symbol,
        strategy: strategyName,
        ohlc: { open, high, low, close },
        entryValue,
        exitValue: entryValue,
        pnlPercent: 0.0,
        timestamp: new Date().toLocaleTimeString()
      });
    }

    return {
      activeTrades: [...state.activeTrades, ...newTrades]
    };
  }),

  updateTradesMock: () => set((state) => {
    // Simulate real-time price updates for active trades
    const updated = state.activeTrades.map((t) => {
      const pnlChange = (Math.random() - 0.5) * 0.005; // -0.25% to +0.25% swing
      const newPnl = t.pnlPercent + pnlChange;
      const exitValue = t.entryValue * (1 + newPnl);

      
      const currentClose = t.ohlc.close * (1 + pnlChange * 0.5);
      const currentHigh = Math.max(t.ohlc.high, currentClose);
      const currentLow = Math.min(t.ohlc.low, currentClose);

      return {
        ...t,
        ohlc: {
          ...t.ohlc,
          high: currentHigh,
          low: currentLow,
          close: currentClose
        },
        exitValue,
        pnlPercent: newPnl
      };
    });

    return { activeTrades: updated };
  })
}));
