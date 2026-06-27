import { Navigate, useSearchParams } from 'react-router-dom'

export function LegacyOpportunitiesRedirect() {
  const [searchParams] = useSearchParams()
  if (searchParams.get('tab') === 'themes') {
    return <Navigate to="/insights?tab=themes" replace />
  }
  return <Navigate to="/advice" replace />
}

export function LegacySignalsRedirect() {
  return <Navigate to="/advice?tab=all" replace />
}

export function LegacyAnalysisRedirect() {
  return <Navigate to="/insights" replace />
}
