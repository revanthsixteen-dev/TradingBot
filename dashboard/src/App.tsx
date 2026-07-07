import { useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChartArea } from './components/ChartArea';
import { FloatingTradePanel } from './components/FloatingTradePanel';
import { useTradeStore } from './store/useTradeStore';

function App() {
  const { updateTradesMock } = useTradeStore();

  // Trigger WebSocket real-time mock data updates every 1 second
  useEffect(() => {
    const timer = setInterval(() => {
      updateTradesMock();
    }, 1000);
    return () => clearInterval(timer);
  }, [updateTradesMock]);

  return (
    <div className="flex h-screen w-screen bg-gray-950 overflow-hidden font-sans select-none text-gray-100 antialiased">
      {/* 3-Column Layout */}
      <Sidebar />
      <ChartArea />
      <FloatingTradePanel />
    </div>
  );
}

export default App;
