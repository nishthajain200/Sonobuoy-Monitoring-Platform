import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import {
  AppBar, Toolbar, Typography, Drawer, List, ListItemButton, ListItemIcon,
  ListItemText, Box, Divider
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Sensors, CloudUpload, GraphicEq, BarChart,
  Gradient, MyLocation, CompareArrows, Map, Timeline, Description, PlayCircle
} from '@mui/icons-material';

import Dashboard from './pages/Dashboard';
import SonobuoyManagement from './pages/SonobuoyManagement';
import DataIngestion from './pages/DataIngestion';
import WaveformViewer from './pages/WaveformViewer';
import FFTAnalysis from './pages/FFTAnalysis';
import LofargramViewer from './pages/LofargramViewer';
import BearingView from './pages/BearingView';
import MultiSonobuoyAnalysis from './pages/MultiSonobuoyAnalysis';
import TacticalMap from './pages/TacticalMap';
import MissionTimeline from './pages/MissionTimeline';
import Reports from './pages/Reports';
import LivePlayback from './pages/LivePlayback';

const DRAWER_WIDTH = 240;

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1565c0' },
    secondary: { main: '#ff6f00' },
    background: { default: '#f5f5f5' },
  },
});

const navItems = [
  { path: '/', label: 'Dashboard', icon: <DashboardIcon /> },
  { path: '/sonobuoys', label: 'Sonobuoy Management', icon: <Sensors /> },
  { path: '/ingestion', label: 'Data Ingestion', icon: <CloudUpload /> },
  { path: '/waveform', label: 'Waveform Viewer', icon: <GraphicEq /> },
  { path: '/fft', label: 'FFT Analysis', icon: <BarChart /> },
  { path: '/lofargram', label: 'LOFARgram Viewer', icon: <Gradient /> },
  { path: '/bearing', label: 'Bearing / Polar View', icon: <MyLocation /> },
  { path: '/multi-analysis', label: 'Multi-Sonobuoy', icon: <CompareArrows /> },
  { path: '/tactical-map', label: 'Tactical Map', icon: <Map /> },
  { path: '/timeline', label: 'Mission Timeline', icon: <Timeline /> },
  { path: '/playback', label: 'Live Playback', icon: <PlayCircle /> },
  { path: '/reports', label: 'Reports', icon: <Description /> },
];

const NavDrawer: React.FC = () => {
  const location = useLocation();
  return (
    <Drawer variant="permanent" sx={{
      width: DRAWER_WIDTH, flexShrink: 0,
      '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
    }}>
      <Toolbar />
      <Divider />
      <List>
        {navItems.map(item => (
          <ListItemButton key={item.path} component={Link} to={item.path}
            selected={location.pathname === item.path}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
};

const App: React.FC = () => (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <BrowserRouter>
      <Box sx={{ display: 'flex' }}>
        <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
          <Toolbar>
            <Sensors sx={{ mr: 1 }} />
            <Typography variant="h6" noWrap>
              Sonobuoy Acoustic Analysis System
            </Typography>
          </Toolbar>
        </AppBar>

        <NavDrawer />

        <Box component="main" sx={{ flexGrow: 1, p: 0, mt: 8 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sonobuoys" element={<SonobuoyManagement />} />
            <Route path="/ingestion" element={<DataIngestion />} />
            <Route path="/waveform" element={<WaveformViewer />} />
            <Route path="/fft" element={<FFTAnalysis />} />
            <Route path="/lofargram" element={<LofargramViewer />} />
            <Route path="/bearing" element={<BearingView />} />
            <Route path="/multi-analysis" element={<MultiSonobuoyAnalysis />} />
            <Route path="/tactical-map" element={<TacticalMap />} />
            <Route path="/timeline" element={<MissionTimeline />} />
            <Route path="/playback" element={<LivePlayback />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </Box>
      </Box>
    </BrowserRouter>
  </ThemeProvider>
);

export default App;
