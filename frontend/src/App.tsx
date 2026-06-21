import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AnalysisPage from './pages/AnalysisPage'
import Dashboard from './pages/Dashboard'
import HoldingsPage from './pages/HoldingsPage'
import ImportPage from './pages/ImportPage'
import SettingsPage from './pages/SettingsPage'
import SignalsPage from './pages/SignalsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="import" element={<ImportPage />} />
          <Route path="holdings" element={<HoldingsPage />} />
          <Route path="signals" element={<SignalsPage />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
