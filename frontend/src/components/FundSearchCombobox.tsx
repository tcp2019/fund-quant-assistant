import { useEffect, useState } from 'react'
import { searchFunds } from '../api/client'
import type { FundSearchResult } from '../types'

interface FundSearchComboboxProps {
  onSelect: (result: FundSearchResult) => void
  placeholder?: string
}

export default function FundSearchCombobox({
  onSelect,
  placeholder = '搜索基金代码或名称…',
}: FundSearchComboboxProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FundSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < 2) {
      setResults([])
      setError(null)
      return
    }

    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await searchFunds(trimmed)
        setResults(data.results)
      } catch (err) {
        setResults([])
        setError(err instanceof Error ? err.message : '搜索失败')
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => window.clearTimeout(timer)
  }, [query])

  return (
    <div className="space-y-2">
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        className="w-full min-w-[12rem] rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
      />
      {loading ? <p className="text-xs text-slate-500">搜索中…</p> : null}
      {error ? <p className="text-xs text-rose-600">{error}</p> : null}
      {results.length > 0 ? (
        <ul className="max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-white text-sm shadow-sm">
          {results.map((result) => (
            <li key={result.fund_code}>
              <button
                type="button"
                onClick={() => {
                  onSelect(result)
                  setQuery('')
                  setResults([])
                }}
                className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
              >
                <span>
                  <span className="font-medium text-slate-900">{result.fund_name}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{result.fund_type}</span>
                </span>
                <span className="font-mono text-xs text-slate-600">{result.fund_code}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
