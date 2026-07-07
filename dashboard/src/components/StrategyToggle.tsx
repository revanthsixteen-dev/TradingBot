import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTradeStore, type Strategy } from '../store/useTradeStore';
import { Play, Square, ChevronDown } from 'lucide-react';

interface StrategyToggleProps {
  strategy: Strategy;
}

export const StrategyToggle: React.FC<StrategyToggleProps> = ({ strategy }) => {
  const {
    activeStrategies,
    assetScopes,
    toggleStrategy,
    setAssetScope,
    addMockTrade
  } = useTradeStore();

  const [isOpen, setIsOpen] = useState(false);

  const isOn = !!activeStrategies[strategy.id];
  const selectedScope = assetScopes[strategy.id];

  const handleToggle = () => {
    toggleStrategy(strategy.id);
    if (!isOn) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  };

  const handleScopeSelect = (scope: 'single' | 'top10' | 'multiple') => {
    setAssetScope(strategy.id, scope);
    addMockTrade(strategy.id, strategy.name, scope);
    setIsOpen(false);
  };

  const scopeLabelMap = {
    single: 'Single Asset',
    top10: 'Top 10 Assets',
    multiple: 'Multi-Assets'
  };

  return (
    <div className="border border-gray-800 bg-gray-900/60 rounded-lg p-3 transition-all duration-300 hover:border-gray-700">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0 pr-2">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-gray-200 truncate">{strategy.name}</h4>
            {isOn && selectedScope && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse font-mono">
                TRADING
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 truncate mt-0.5">{strategy.description}</p>
        </div>

        <div className="flex items-center gap-2">
          {isOn && (
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="p-1 rounded bg-gray-850 border border-gray-700 hover:bg-gray-800 text-gray-400 transition-colors"
            >
              <ChevronDown className={`w-4 h-4 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>
          )}

          <button
            onClick={handleToggle}
            className={`relative flex items-center justify-center p-1.5 rounded-lg border transition-all duration-300 ${
              isOn
                ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20'
                : 'bg-gray-850 border-gray-700 text-gray-400 hover:bg-gray-800'
            }`}
          >
            {isOn ? <Square className="w-4 h-4 fill-emerald-400/20" /> : <Play className="w-4 h-4 fill-gray-400/20" />}
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {isOn && (isOpen || !selectedScope) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden mt-3"
          >
            <div className="pt-2 border-t border-gray-800 flex flex-col gap-1.5">
              <span className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">Select Execution Scope:</span>
              <div className="grid grid-cols-3 gap-1.5">
                {(['single', 'top10', 'multiple'] as const).map((scope) => (
                  <button
                    key={scope}
                    onClick={() => handleScopeSelect(scope)}
                    className={`text-[10px] py-1.5 px-1 rounded font-mono border text-center transition-all ${
                      selectedScope === scope
                        ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                        : 'bg-gray-850 border-gray-850 text-gray-400 hover:border-gray-700 hover:text-gray-200'
                    }`}
                  >
                    {scopeLabelMap[scope]}
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {isOn && selectedScope && !isOpen && (
        <div className="mt-2 text-[10px] font-mono text-gray-500 flex items-center gap-1.5 bg-gray-950/40 p-1.5 rounded">
          <span className="w-1 h-1 rounded-full bg-emerald-400"></span>
          <span>Target Scope: <span className="text-gray-300">{scopeLabelMap[selectedScope]}</span></span>
        </div>
      )}
    </div>
  );
};
