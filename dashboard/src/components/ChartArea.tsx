import React, { useState, useEffect } from 'react';
import { useTradeStore } from '../store/useTradeStore';
import { Activity, ShieldAlert, Cpu, Zap } from 'lucide-react';

export const ChartArea: React.FC = () => {
  const { activeTrades } = useTradeStore();
  const [points, setPoints] = useState<number[]>([150, 151, 149, 152, 153, 151, 154, 152, 155, 157, 156, 159, 158]);
  const [latency, setLatency] = useState(245);
  const [throughput, setThroughput] = useState(48200);

  // Keep mock rolling chart moving
  useEffect(() => {
    const timer = setInterval(() => {
      setPoints((prev) => {
        const nextPrice = prev[prev.length - 1] + (Math.random() - 0.5) * 4;
        const newPoints = [...prev.slice(1), nextPrice];
        return newPoints;
      });
      setLatency(Math.floor(210 + Math.random() * 60));
      setThroughput(Math.floor(45000 + Math.random() * 5000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const minVal = Math.min(...points);
  const maxVal = Math.max(...points);
  const range = maxVal - minVal || 1;

  const width = 600;
  const height = 280;

  const svgPoints = points
    .map((val, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((val - minVal) / range) * (height - 40) - 20;
      return `${x},${y}`;
    })
    .join(' ');

  const telemetry = [
    { name: 'Execution Latency', value: `${latency} ns`, icon: Zap, color: 'text-amber-400' },
    { name: 'Pre-Trade Risk', value: 'CLEARED', icon: ShieldAlert, color: 'text-emerald-400' },
    { name: 'Throughput', value: `${throughput.toLocaleString()} tx/s`, icon: Cpu, color: 'text-blue-400' },
    { name: 'FIX / DMA Session', value: 'ONLINE', icon: Activity, color: 'text-emerald-400' }
  ];

  return (
    <div className="flex-1 bg-gray-950 flex flex-col h-full overflow-hidden select-none p-4 gap-4">
      {/* Telemetry Row */}
      <div className="grid grid-cols-4 gap-3">
        {telemetry.map((t, idx) => {
          const Icon = t.icon;
          return (
            <div key={idx} className="bg-gray-900 border border-gray-850 rounded-lg p-3 flex items-center justify-between font-mono">
              <div>
                <span className="text-[9px] text-gray-500 uppercase tracking-wider block">{t.name}</span>
                <span className="text-sm font-bold text-gray-200 mt-1 block">{t.value}</span>
              </div>
              <Icon className={`w-5 h-5 ${t.color}`} />
            </div>
          );
        })}
      </div>

      {/* Main Terminal Chart Panel */}
      <div className="flex-1 bg-gray-900 border border-gray-850 rounded-lg p-4 flex flex-col relative">
        <div className="flex items-center justify-between pb-3 border-b border-gray-850">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-bold text-gray-200 font-mono">HFT_FEED_TELEMETRY (rolling 1s interval)</span>
          </div>
          <span className="text-[10px] text-gray-500 font-mono">Z-SCORE SPREAD SENSOR</span>
        </div>

        {/* Rolling SVG Chart */}
        <div className="flex-1 flex items-center justify-center relative mt-4">
          <svg className="w-full h-full max-h-72 overflow-visible" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
            {/* Grid lines */}
            {[0.25, 0.5, 0.75].map((ratio, i) => (
              <line
                key={i}
                x1="0"
                y1={height * ratio}
                x2={width}
                y2={height * ratio}
                className="stroke-gray-850"
                strokeDasharray="4 4"
              />
            ))}
            
            {/* Gradient Fill */}
            <defs>
              <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d={`M 0,${height} L ${svgPoints} L ${width},${height} Z`}
              fill="url(#chart-grad)"
            />

            {/* Line Path */}
            <polyline
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
              points={svgPoints}
            />

            {/* Price Marker dots */}
            {points.map((val, index) => {
              const x = (index / (points.length - 1)) * width;
              const y = height - ((val - minVal) / range) * (height - 40) - 20;
              const isLast = index === points.length - 1;
              return isLast ? (
                <g key={index}>
                  <circle cx={x} cy={y} r="5" className="fill-blue-500 animate-ping" />
                  <circle cx={x} cy={y} r="3" className="fill-blue-400" />
                </g>
              ) : null;
            })}
          </svg>
        </div>

        {/* Console Logs Mock Panel */}
        <div className="h-40 border-t border-gray-850 mt-4 pt-3 flex flex-col font-mono">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">DMA Router Logs:</span>
          <div className="flex-1 bg-gray-950/65 rounded p-2.5 overflow-y-auto text-[10px] text-gray-400 flex flex-col gap-1 select-text">
            <div>[OK] <span className="text-gray-500">15:42:01.082</span> Outgoing FIX session message 35=D (NewOrderSingle) accepted.</div>
            <div>[OK] <span className="text-gray-500">15:42:01.082</span> Pre-Routing check completed. Leverage: 1.25x. Margin: cleared.</div>
            {activeTrades.length > 0 ? (
              activeTrades.map((t, idx) => (
                <div key={idx} className="text-emerald-400">
                  [FILL] <span className="text-gray-500">{t.timestamp}</span> Executed order {t.symbol} for strategy {t.strategy}. Cost: {t.entryValue.toLocaleString()}.
                </div>
              ))
            ) : (
              <div className="text-gray-600">[IDLE] Awaiting strategy placement triggers...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
