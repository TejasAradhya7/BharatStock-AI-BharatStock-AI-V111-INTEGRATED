
import { Tabs } from 'expo-router';
import {
  Activity,
  BriefcaseBusiness,
  History,
  House,
  Newspaper,
} from 'lucide-react-native';
import { Platform } from 'react-native';

const bg = '#0a101b';
const muted = '#91a0b5';
const accent = '#25b887';

export default function Layout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: bg },
        tabBarStyle: {
          backgroundColor: '#101a29',
          borderTopColor: '#223148',
          height: Platform.OS === 'android' ? 66 : 82,
          paddingTop: 7,
          paddingBottom: Platform.OS === 'android' ? 8 : 22,
        },
        tabBarActiveTintColor: accent,
        tabBarInactiveTintColor: muted,
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '700',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, size }) => (
            <House color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="analysis"
        options={{
          title: 'Analysis',
          tabBarIcon: ({ color, size }) => (
            <Activity color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="risk"
        options={{
          title: 'Risk',
          tabBarIcon: ({ color, size }) => (
            <BriefcaseBusiness color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="backtest"
        options={{
          title: 'Backtest',
          tabBarIcon: ({ color, size }) => (
            <History color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="research"
        options={{
          title: 'Research',
          tabBarIcon: ({ color, size }) => (
            <Newspaper color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
