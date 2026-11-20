import ApiScreen from '../components/ApiScreen';

const requests = [
  { label: 'Risk metrics', path: (symbol: string) => `/api/risk/${symbol}` },
  { label: 'Stress test', path: (symbol: string) => `/api/stress/${symbol}` },
  { label: 'Trade history', path: (_symbol: string) => '/api/trades' },
];

export default function RiskScreen() {
  return <ApiScreen title="Portfolio & Risk" description="Inspect backend risk metrics, stress-test output, and recorded trades. Position sizing may require additional inputs in the API documentation." requests={requests} />;
}
