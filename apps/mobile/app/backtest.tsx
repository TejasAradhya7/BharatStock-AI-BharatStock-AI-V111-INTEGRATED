import ApiScreen from '../components/ApiScreen';

const requests = [
  { label: 'Backtest results', path: (symbol: string) => `/api/backtest/${symbol}` },
  { label: 'Backtest equity export', path: (symbol: string) => `/api/backtest/${symbol}/equity.csv` },
];

export default function BacktestScreen() {
  return <ApiScreen title="Backtesting" description="Request the configured historical backtest and equity-curve output for a selected symbol." requests={requests} />;
}
