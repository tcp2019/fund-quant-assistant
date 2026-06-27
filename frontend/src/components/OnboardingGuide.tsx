import { Link } from 'react-router-dom'

const STORAGE_KEY = 'fund-quant-onboarded'

export default function OnboardingGuide() {
  const isOnboarded = localStorage.getItem(STORAGE_KEY) === 'true'

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, 'true')
    window.location.reload()
  }

  if (isOnboarded) return null

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-8">
      <h2 className="text-xl font-semibold text-indigo-900">欢迎使用基金量化助手</h2>
      <p className="mt-2 text-indigo-700">按照以下 3 步开始使用：</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-2xl">1️⃣</div>
          <h3 className="mt-2 font-medium text-slate-900">导入持仓</h3>
          <p className="mt-1 text-sm text-slate-500">截图上传或手动录入基金持仓</p>
          <Link to="/import" className="mt-2 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-800">
            去导入 →
          </Link>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-2xl">2️⃣</div>
          <h3 className="mt-2 font-medium text-slate-900">同步数据</h3>
          <p className="mt-1 text-sm text-slate-500">拉取净值、排名等公开数据</p>
          <Link to="/settings" className="mt-2 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-800">
            去设置 →
          </Link>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <div className="text-2xl">3️⃣</div>
          <h3 className="mt-2 font-medium text-slate-900">查看信号</h3>
          <p className="mt-1 text-sm text-slate-500">系统自动生成买卖建议</p>
          <Link to="/signals" className="mt-2 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-800">
            去查看 →
          </Link>
        </div>
      </div>
      <button
        onClick={dismiss}
        className="mt-4 text-sm text-indigo-500 hover:text-indigo-700"
      >
        不再显示
      </button>
    </div>
  )
}
