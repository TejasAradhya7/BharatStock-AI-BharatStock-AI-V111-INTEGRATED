import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

const API =
  process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export type RequestSpec = {
  label: string;
  path: (symbol: string) => string;
  method?: 'GET' | 'POST';
  body?: (symbol: string) => unknown;
  enabled?: (symbol: string) => boolean;
};

type Result = {
  label: string;
  ok: boolean;
  status?: number;
  data?: unknown;
  body: string;
  contentType?: string;
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

function humanize(key: string) {
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value: unknown, key = ''): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    if (/confidence|accuracy|probability|return pct|drawdown pct|volatility pct|exposure pct|change pct|importance/i.test(key)) {
      const pctKeys = /return pct|drawdown pct|volatility pct|exposure pct|change pct/i.test(key);
      const n = pctKeys ? value : value * 100;
      return `${n.toFixed(2)}%`;
    }
    return Number.isInteger(value)
      ? value.toLocaleString('en-IN')
      : value.toLocaleString('en-IN', { maximumFractionDigits: 4 });
  }
  if (typeof value === 'string') return value.replaceAll('_', ' ');
  return '';
}

function isMetric(key: string, value: unknown) {
  return typeof value === 'number' && !/timestamp|epoch|id$/i.test(key);
}

function Field({ label, value }: { label: string; value: unknown }) {
  const shown = formatValue(value, label);
  return (
    <View style={s.field}>
      <Text style={s.fieldLabel}>{humanize(label)}</Text>
      <Text selectable style={s.fieldValue}>{shown || '—'}</Text>
    </View>
  );
}

function DataView({
  value,
  label,
  depth = 0,
}: {
  value: unknown;
  label?: string;
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <View style={s.empty}>
          <Text style={s.emptyTitle}>{label ? humanize(label) : 'Results'}</Text>
          <Text style={s.muted}>No records available yet.</Text>
        </View>
      );
    }

    const visibleItems = expanded || value.length <= 3 ? value : value.slice(0, 3);
    return (
      <View style={depth === 0 ? undefined : s.nestedSection}>
        {label ? <Text style={s.sectionTitle}>{humanize(label)} <Text style={s.count}>({value.length})</Text></Text> : null}
        {visibleItems.map((item, index) => (
          <View key={`${label || 'item'}-${index}`} style={s.itemCard}>
            {isRecord(item) ? (
              <DataView value={item} depth={depth + 1} />
            ) : (
              <Text selectable style={s.fieldValue}>{formatValue(item)}</Text>
            )}
          </View>
        ))}
        {value.length > 3 ? (
          <Pressable
            onPress={() => setExpanded((current) => !current)}
            style={s.expandButton}
            accessibilityRole="button"
          >
            <Text style={s.expandButtonText}>
              {expanded ? 'Show less' : `Show all ${value.length} records`}
            </Text>
          </Pressable>
        ) : null}
      </View>
    );
  }

  if (isRecord(value)) {
    const entries = Object.entries(value);
    const metrics = entries.filter(([key, item]) => isMetric(key, item));
    const details = entries.filter(([key, item]) => !isMetric(key, item));

    return (
      <View>
        {metrics.length > 0 && (
          <View style={s.metricGrid}>
            {metrics.map(([key, item]) => (
              <View key={key} style={s.metricCard}>
                <Text style={s.metricLabel}>{humanize(key)}</Text>
                <Text selectable style={s.metricValue}>{formatValue(item, key)}</Text>
              </View>
            ))}
          </View>
        )}
        {details.map(([key, item]) => {
          if (Array.isArray(item)) {
            return <DataView key={key} value={item} label={key} depth={depth + 1} />;
          }
          if (isRecord(item)) {
            return (
              <View key={key} style={s.nestedSection}>
                <Text style={s.sectionTitle}>{humanize(key)}</Text>
                <DataView value={item} depth={depth + 1} />
              </View>
            );
          }
          return <Field key={key} label={key} value={item} />;
        })}
      </View>
    );
  }

  return (
    <View style={s.field}>
      {label ? <Text style={s.fieldLabel}>{humanize(label)}</Text> : null}
      <Text selectable style={s.fieldValue}>{formatValue(value)}</Text>
    </View>
  );
}

function CsvView({ text }: { text: string }) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean).slice(0, 12);
  if (lines.length < 2) return <Text selectable style={s.plainText}>{text || '(Empty response)'}</Text>;
  const rows = lines.map((line) => line.split(',').map((cell) => cell.trim().replace(/^"|"$/g, '')));
  return (
    <ScrollView horizontal>
      <View>
        {rows.map((row, ri) => (
          <View key={`row-${ri}`} style={[s.csvRow, ri === 0 && s.csvHeader]}>
            {row.map((cell, ci) => (
              <Text key={`cell-${ri}-${ci}`} style={[s.csvCell, ri === 0 && s.csvHeaderText]} numberOfLines={2}>
                {cell}
              </Text>
            ))}
          </View>
        ))}
        {text.trim().split(/\r?\n/).filter(Boolean).length > 12 ? (
          <Text style={s.muted}>Preview limited to the first 12 rows.</Text>
        ) : null}
      </View>
    </ScrollView>
  );
}

export default function ApiScreen({
  title,
  description,
  requests,
}: {
  title: string;
  description: string;
  requests: RequestSpec[];
}) {
  const [symbol, setSymbol] = useState('^NSEI');
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Result[]>([]);

  const refresh = useCallback(async () => {
    const selectedSymbol = symbol.trim().toUpperCase();
    if (!selectedSymbol) {
      setResults([{ label: 'Input validation', ok: false, body: 'Enter a market symbol before refreshing.' }]);
      return;
    }

    setBusy(true);
    try {
      const next: Result[] = [];
      for (const req of requests) {
        if (req.enabled && !req.enabled(selectedSymbol)) {
          next.push({
            label: req.label,
            ok: false,
            body: 'Not available for this symbol. Check that the symbol has a configured instrument mapping.',
          });
          continue;
        }

        try {
          const method = req.method || 'GET';
          const path = req.path(selectedSymbol);
          const response = await fetch(`${API}${path}`, {
            method,
            headers: {
              Accept: 'application/json, text/csv, text/plain',
              ...(method === 'POST' ? { 'Content-Type': 'application/json' } : {}),
            },
            ...(method === 'POST'
              ? { body: JSON.stringify(req.body ? req.body(selectedSymbol) : {}) }
              : {}),
          });
          const raw = await response.text();
          const contentType = response.headers.get('content-type') || '';
          let data: unknown = undefined;
          let body = raw || '(Empty response)';
          try {
            data = JSON.parse(raw);
          } catch {
            // Non-JSON responses, such as CSV exports, are rendered separately.
          }
          next.push({
            label: req.label,
            ok: response.ok,
            status: response.status,
            data,
            body,
            contentType,
          });
        } catch (error: unknown) {
          next.push({
            label: req.label,
            ok: false,
            body: error instanceof Error ? error.message : 'Network request failed.',
          });
        }
      }
      setResults(next);
    } finally {
      setBusy(false);
    }
  }, [requests, symbol]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <ScrollView style={s.page} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
      <Text style={s.eyebrow}>BHARATSTOCK AI</Text>
      <Text style={s.title}>{title}</Text>
      <Text style={s.description}>{description}</Text>

      <View style={s.searchRow}>
        <TextInput
          value={symbol}
          onChangeText={setSymbol}
          autoCapitalize="characters"
          autoCorrect={false}
          placeholder="^NSEI or RELIANCE.NS"
          placeholderTextColor="#8190a6"
          style={s.input}
          returnKeyType="search"
          onSubmitEditing={() => void refresh()}
        />
        <Pressable onPress={() => void refresh()} disabled={busy} style={[s.button, busy && s.buttonDisabled]}>
          <Text style={s.buttonText}>{busy ? 'Loading…' : 'Refresh'}</Text>
        </Pressable>
      </View>

      {busy && <ActivityIndicator color="#25b887" style={{ marginVertical: 12 }} />}

      {results.map((item, i) => (
        <View key={`${item.label}-${i}`} style={s.card}>
          <View style={s.resultHeader}>
            <Text style={s.cardTitle}>{item.label}</Text>
            <Text style={[s.status, { color: item.ok ? '#5ee2ae' : '#fb7185' }]}>
              {item.status !== undefined ? `${item.status} · ` : ''}{item.ok ? 'SUCCESS' : 'CHECK'}
            </Text>
          </View>
          {item.data !== undefined ? (
            <DataView value={item.data} />
          ) : item.contentType?.includes('csv') || (item.body.includes(',') && item.body.includes('\n') && !item.body.startsWith('{')) ? (
            <CsvView text={item.body} />
          ) : (
            <Text selectable style={s.plainText}>{item.body}</Text>
          )}
        </View>
      ))}

      <Text style={s.foot}>
        Data comes from your configured backend. A successful request does not guarantee sufficient data or accurate predictions. For educational research only; not investment advice.
      </Text>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#0a101b' },
  content: { padding: 18, paddingTop: 30, paddingBottom: 36 },
  eyebrow: { color: '#7c91ad', fontSize: 10, letterSpacing: 1.8, fontWeight: '800' },
  title: { color: '#edf4ff', fontSize: 28, fontWeight: '800', marginTop: 8 },
  description: { color: '#91a0b5', fontSize: 13, lineHeight: 20, marginTop: 8, marginBottom: 18 },
  searchRow: { flexDirection: 'row', gap: 8, marginBottom: 14 },
  input: { flex: 1, minWidth: 0, backgroundColor: '#111b2b', borderColor: '#29394f', borderWidth: 1, borderRadius: 10, padding: 12, color: '#edf4ff' },
  button: { backgroundColor: '#25b887', borderRadius: 10, paddingHorizontal: 14, justifyContent: 'center', alignItems: 'center', minHeight: 44 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#06271e', fontWeight: '800' },
  card: { backgroundColor: '#101a29', borderColor: '#223148', borderWidth: 1, borderRadius: 13, padding: 14, marginBottom: 12 },
  resultHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 12 },
  cardTitle: { color: '#dce8f8', fontSize: 14, fontWeight: '800', flex: 1 },
  status: { fontSize: 10, fontWeight: '800' },
  metricGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 8 },
  metricCard: { width: '48%', flexGrow: 1, minWidth: 115, backgroundColor: '#0b1523', borderColor: '#26364b', borderWidth: 1, borderRadius: 10, padding: 11 },
  metricLabel: { color: '#8fa2bb', fontSize: 10, lineHeight: 14, textTransform: 'uppercase', letterSpacing: 0.5 },
  metricValue: { color: '#edf4ff', fontSize: 17, fontWeight: '800', marginTop: 6 },
  field: { borderBottomWidth: 1, borderBottomColor: '#223148', paddingVertical: 9, gap: 4 },
  fieldLabel: { color: '#8fa2bb', fontSize: 10, letterSpacing: 0.6, textTransform: 'uppercase' },
  fieldValue: { color: '#cbd8e9', fontSize: 13, lineHeight: 19 },
  sectionTitle: { color: '#dce8f8', fontSize: 13, fontWeight: '800', marginTop: 12, marginBottom: 8 },
  count: { color: '#7e8fa7', fontWeight: '600' },
  nestedSection: { marginTop: 8, paddingTop: 4, borderTopWidth: 1, borderTopColor: '#223148' },
  itemCard: { backgroundColor: '#0b1523', borderColor: '#26364b', borderWidth: 1, borderRadius: 9, padding: 10, marginBottom: 7 },
  empty: { backgroundColor: '#0b1523', borderRadius: 9, padding: 12, marginVertical: 6 },
  emptyTitle: { color: '#dce8f8', fontWeight: '700', marginBottom: 4 },
  muted: { color: '#8fa2bb', fontSize: 11, marginTop: 5 },
  plainText: { color: '#cbd8e9', fontSize: 12, lineHeight: 18 },
  csvRow: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: '#26364b' },
  csvHeader: { backgroundColor: '#172437' },
  csvCell: { color: '#cbd8e9', minWidth: 95, maxWidth: 170, padding: 8, fontSize: 10 },
  csvHeaderText: { color: '#edf4ff', fontWeight: '800' },
  expandButton: {
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: '#2b4059',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 3,
    marginBottom: 8,
  },
  expandButtonText: { color: '#5ee2ae', fontSize: 12, fontWeight: '800' },
  foot: { color: '#7e8fa7', fontSize: 11, lineHeight: 18, marginTop: 4 },
});
