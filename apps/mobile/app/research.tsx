
import { useEffect, useMemo, useState } from 'react';
import ApiScreen, { type RequestSpec } from '../components/ApiScreen';

const API =
  process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000';

type SupportedSymbol = {
  symbol: string;
  name: string;
  instrument_key: string;
};

function parseSupportedSymbols(data: any): SupportedSymbol[] {
  const raw = data?.supported_symbols;

  if (Array.isArray(raw)) {
    return raw
      .filter(
        (item: any) =>
          typeof item?.symbol === 'string' &&
          typeof item?.instrument_key === 'string',
      )
      .map((item: any) => ({
        symbol: item.symbol,
        name: item.name || item.symbol,
        instrument_key: item.instrument_key,
      }));
  }

  if (raw && typeof raw === 'object') {
    return Object.entries(raw)
      .filter(([, value]) => typeof value === 'string')
      .map(([symbol, value]) => ({
        symbol,
        name: symbol,
        instrument_key: value as string,
      }));
  }

  return [];
}

export default function ResearchScreen() {
  const [symbols, setSymbols] = useState<SupportedSymbol[]>([]);
  const [mappingError, setMappingError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadSymbols() {
      try {
        const response = await fetch(`${API}/api/live/status`);

        if (!response.ok) {
          throw new Error(`Live status returned HTTP ${response.status}`);
        }

        const data = await response.json();
        const parsed = parseSupportedSymbols(data);

        if (active) {
          setSymbols(parsed);
          setMappingError(
            parsed.length === 0
              ? 'No supported Upstox instrument mappings were returned.'
              : '',
          );
        }
      } catch (error: unknown) {
        if (active) {
          setMappingError(
            error instanceof Error
              ? error.message
              : 'Unable to load instrument mappings.',
          );
        }
      }
    }

    void loadSymbols();

    return () => {
      active = false;
    };
  }, []);

  const requests = useMemo<RequestSpec[]>(() => {
    const intradayRequest: RequestSpec = {
      label: 'Intraday research',
      path: (symbol) => {
        const match = symbols.find(
          (item) => item.symbol.toUpperCase() === symbol,
        );

        if (!match) {
          throw new Error(
            `No Upstox instrument mapping found for ${symbol}.`,
          );
        }

        return (
          `/api/research/intraday/${encodeURIComponent(match.symbol)}` +
          `?instrument_key=${encodeURIComponent(match.instrument_key)}`
        );
      },
      enabled: (symbol) =>
        symbols.some((item) => item.symbol.toUpperCase() === symbol),
    };

    return [
      {
        label: 'Research status',
        path: () => '/api/research/status',
      },
      {
        label: 'Sentiment API test',
        path: () => '/api/sentiment',
        method: 'POST',
        body: (symbol) => ({
          text: `The research subject is ${symbol}.`,
        }),
      },
      intradayRequest,
    ];
  }, [symbols]);

  return (
    <ApiScreen
      title="Research"
      description={
        'Check research status, test the text-sentiment endpoint, ' +
        'and fetch intraday research using your configured Upstox mapping. ' +
        (mappingError ? `Mapping status: ${mappingError}` : `Instrument mappings loaded: ${symbols.length}.`)
      }
      requests={requests}
    />
  );
}
