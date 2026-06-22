import { Link } from 'react-router-dom'
import type { ActionItem, OpportunitiesOut } from '../types'
import { formatSignalAmount } from '../utils/signalDisplay'

interface ActionSummaryCardsProps {
  data: OpportunitiesOut | null
}

interface CardConfig {
  key: 'sell' | 'add_holding' | 'explore'
  title: string
  emoji: string
  tone: 'sell' | 'buy' | 'explore'
  emptyText: string
  getItems: (data: OpportunitiesOut) => ActionItem[]
}

const CARD_CONFIGS: CardConfig[] = [
  {
    key: 'sell',
    title: '建议卖出',
    emoji: '🔴',
    tone: 'sell',
    emptyText: '暂无卖出建议',
    getItems: (data) => data.sell_actions,
  },
  {
    key: 'add_holding',
    title: '持仓增配',
    emoji: '🟢',
    tone: 'buy',
    emptyText: '暂无增配建议',
    getItems: (data) => data.buy_actions,
  },
  {
    key: 'explore',
    title: '可考虑新买',
    emoji: '🔵',
    tone: 'explore',
    emptyText: '暂无大类缺口或热点交叉机会',
    getItems: (data) => data.explore_actions,
  },
]

const TONE_STYLES = {
  sell: 'border-rose-200',
  buy: 'border-emerald-200',
  explore: 'border-sky-200',
}

function actionTitle(item: ActionItem) {
  if (item.fund_code) {
    return item.fund_name ?? item.fund_code
  }
  return item.category_label ?? item.category ?? '大类配置'
}

export default function ActionSummaryCards({ data }: ActionSummaryCardsProps) {
  if (!data || data.snapshot_id === null) {
    return (
      <section className="rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center">
        <h3 className="text-base font-semibold text-slate-900">今日行动</h3>
        <p className="mt-2 text-sm text-slate-500">导入持仓并同步后查看机会</p>
        <Link
          to="/import"
          className="mt-4 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </section>
    )
  }

  const totalActions =
    data.sell_actions.length + data.buy_actions.length + data.explore_actions.length

  if (totalActions === 0) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">今日行动</h3>
        <p className="mt-2 text-sm text-slate-500">暂无明确行动，组合配置较为均衡</p>
        <Link
          to="/opportunities?tab=actions"
          className="mt-4 inline-flex text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          查看机会详情 →
        </Link>
      </section>
    )
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-900">今日行动</h3>
          <p className="mt-1 text-sm text-slate-500">
            快照 #{data.snapshot_id}
            {data.data_as_of_date ? ` · 净值截至 ${data.data_as_of_date}` : ''}
          </p>
        </div>
        <Link
          to="/opportunities?tab=actions"
          className="text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          查看全部 →
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {CARD_CONFIGS.map((config) => {
          const items = config.getItems(data).slice(0, 3)
          return (
            <div
              key={config.key}
              className={`rounded-xl border bg-white p-4 shadow-sm ${TONE_STYLES[config.tone]}`}
            >
              <h4 className="font-medium text-slate-900">
                <span aria-hidden="true">{config.emoji} </span>
                {config.title}
              </h4>
              {items.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">{config.emptyText}</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {items.map((item, index) => (
                    <li
                      key={`${config.key}-${item.signal_id ?? item.fund_code ?? index}`}
                      className="flex items-start justify-between gap-2 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium text-slate-900">
                          {actionTitle(item)}
                        </p>
                        {item.reason_summary ? (
                          <p className="truncate text-xs text-slate-500">{item.reason_summary}</p>
                        ) : null}
                      </div>
                      {item.suggested_amount !== 0 ? (
                        <span className="shrink-0 tabular-nums text-slate-700">
                          {formatSignalAmount(item.suggested_amount)}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
