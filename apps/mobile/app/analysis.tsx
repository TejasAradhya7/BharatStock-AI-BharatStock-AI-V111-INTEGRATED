import ApiScreen from '../components/ApiScreen';

const requests = [
  { label: 'AI prediction', path: (symbol: string) => `/api/predict/${symbol}` },
  { label: 'Market history and indicators', path: (symbol: string) => `/api/market/${symbol}?period=1y` },
  { label: 'Chart data', path: (symbol: string) => `/api/chart/${symbol}` },
];

export default function AnalysisScreen() {
  return <ApiScreen title="Analysis" description="Run the existing backend prediction, market-history, and chart endpoints for a selected symbol." requests={requests} />;
}
