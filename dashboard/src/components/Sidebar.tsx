import React, { useState } from 'react';
import { STRATEGIES_DATA } from '../store/useTradeStore';
import { StrategyToggle } from './StrategyToggle';
import { Search, Compass, Sliders, Layers } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState<'All' | 'Arbitrage' | 'Timeframe/Directional' | 'Quant/Derivatives'>('All');

  const filteredStrategies = STRATEGIES_DATA.filter((s) => {
    const matchesSearch = s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          s.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTab = activeTab === 'All' || s.category === activeTab;
    return matchesSearch && matchesTab;
  });

  const categories = [
    { name: 'All', icon: Compass },
    { name: 'Arbitrage', icon: Layers },
    { name: 'Timeframe/Directional', icon: Sliders },
    { name: 'Quant/Derivatives', icon: Layers }
  ] as const;

  return (
    <aside className="w-80 border-r border-gray-800 bg-gray-950 flex flex-col h-full overflow-hidden select-none">
      {/* Top Header */}
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></div>
          <h2 className="text-sm font-bold tracking-widest text-gray-200 uppercase font-mono">Strategy Console</h2>
        </div>
        <span className="text-[10px] bg-gray-850 px-2 py-0.5 rounded border border-gray-700 text-gray-400 font-mono">
          V2.4_HFT
        </span>
      </div>

      {/* Search Input */}
      <div className="p-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search strategies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-900 border border-gray-850 rounded-lg pl-9 pr-4 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-gray-700 transition-all font-mono"
          />
        </div>
      </div>

      {/* Categories Tabs */}
      <div className="px-3 pb-2 border-b border-gray-900 grid grid-cols-4 gap-1">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const isActive = activeTab === cat.name;
          return (
            <button
              key={cat.name}
              onClick={() => setActiveTab(cat.name)}
              title={cat.name}
              className={`flex flex-col items-center gap-1 py-1.5 rounded transition-all border ${
                isActive
                  ? 'bg-gray-900 border-gray-700 text-gray-200'
                  : 'bg-transparent border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="text-[9px] truncate max-w-full font-mono">{cat.name.split('/')[0]}</span>
            </button>
          );
        })}
      </div>

      {/* Strategies List */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {filteredStrategies.length > 0 ? (
          filteredStrategies.map((strat) => (
            <StrategyToggle key={strat.id} strategy={strat} />
          ))
        ) : (
          <div className="text-center py-8 text-gray-600 text-xs font-mono">
            No strategies found.
          </div>
        )}
      </div>
    </aside>
  );
};
