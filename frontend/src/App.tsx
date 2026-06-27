import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import {
  LegacyAnalysisRedirect,
  LegacyOpportunitiesRedirect,
  LegacySignalsRedirect,
} from './components/LegacyRedirects'
import Layout from './components/Layout'
import AdvicePage from './pages/AdvicePage'
import Dashboard from './pages/Dashboard'
import HoldingsPage from './pages/HoldingsPage'
import ImportPage from './pages/ImportPage'
import InsightsPage from './pages/InsightsPage'
import SettingsPage from './pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="advice" element={<AdvicePage />} />
            <Route path="holdings" element={<HoldingsPage />} />
            <Route path="insights" element={<InsightsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="signals" element={<LegacySignalsRedirect />} />
            <Route path="opportunities" element={<LegacyOpportunitiesRedirect />} />
            <Route path="analysis" element={<LegacyAnalysisRedirect />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
