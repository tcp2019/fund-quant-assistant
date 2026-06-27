import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AnalysisPage from './pages/AnalysisPage'
import Dashboard from './pages/Dashboard'
import HoldingsPage from './pages/HoldingsPage'
import ImportPage from './pages/ImportPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import SettingsPage from './pages/SettingsPage'
import SignalsPage from './pages/SignalsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
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
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="holdings" element={<HoldingsPage />} />
            <Route path="signals" element={<SignalsPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
