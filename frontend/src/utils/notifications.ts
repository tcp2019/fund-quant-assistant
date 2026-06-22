const STORAGE_KEY = 'fund-quant.notificationsEnabled'
const SNAPSHOT_KEY = 'fund-quant.lastNotifiedSnapshotId'

export type NotificationPermissionState = NotificationPermission | 'unsupported'

export interface DesktopNotificationPayload {
  title: string
  body: string
}

export interface DesktopNotificationResult {
  apiCalled: boolean
  shown: boolean
  errorMessage?: string
}

export function getNotificationsEnabled(): boolean {
  return localStorage.getItem(STORAGE_KEY) === 'true'
}

export function setNotificationsEnabled(enabled: boolean) {
  localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false')
}

export function notificationsSupported(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window
}

export function getNotificationPermission(): NotificationPermissionState {
  if (!notificationsSupported()) {
    return 'unsupported'
  }
  return Notification.permission
}

export function permissionStatusLabel(permission: NotificationPermissionState): string {
  switch (permission) {
    case 'granted':
      return '已允许'
    case 'denied':
      return '已拒绝'
    case 'default':
      return '尚未授权'
    default:
      return '不支持'
  }
}

export function permissionRecoveryHint(permission: NotificationPermissionState): string | null {
  if (permission !== 'denied') {
    return null
  }
  return (
    '通知权限已被浏览器拒绝，无法再次弹出授权框。请在浏览器站点设置中将本页通知改为「允许」：' +
    'Chrome / Edge → 地址栏左侧锁图标 → 网站设置 → 通知；' +
    'Safari → 设置 → 网站 → 通知 → 找到 localhost 并允许。' +
    '修改后刷新本页再试。'
  )
}

export function systemNotificationVisibilityHint(): string {
  return (
    '若浏览器权限已是「已允许」但仍看不到横幅，通常是 macOS 系统设置拦截：' +
    '系统设置 → 通知 → 选择你正在使用的浏览器（Chrome / Safari / Edge）→ 开启「允许通知」，' +
    '并将提醒样式设为「横幅」或「提醒」而非「无」。' +
    '部分情况下通知只会进入通知中心（点屏幕右上角日期/时间查看），不会弹出横幅。'
  )
}

export function permissionErrorMessage(permission: NotificationPermissionState): string {
  if (permission === 'unsupported') {
    return '当前浏览器不支持通知 API'
  }
  if (permission === 'denied') {
    return permissionRecoveryHint('denied') ?? '浏览器未授予通知权限'
  }
  if (permission === 'default') {
    return '尚未授权通知权限，请点击「授权并开启」并在浏览器弹窗中选择允许'
  }
  return '浏览器未授予通知权限'
}

/** Must be called from a direct click handler (user gesture). */
export async function requestNotificationPermission(): Promise<NotificationPermissionState> {
  if (!notificationsSupported()) {
    return 'unsupported'
  }
  if (Notification.permission === 'granted') {
    return 'granted'
  }
  if (Notification.permission === 'denied') {
    return 'denied'
  }
  return Notification.requestPermission()
}

export async function enableNotificationsWithPermission(): Promise<NotificationPermissionState> {
  const permission = await requestNotificationPermission()
  if (permission === 'granted') {
    setNotificationsEnabled(true)
  }
  return permission
}

export function showDesktopNotification(
  payload: DesktopNotificationPayload,
  options?: NotificationOptions,
): Promise<DesktopNotificationResult> {
  const permission = getNotificationPermission()
  if (permission !== 'granted') {
    return Promise.resolve({
      apiCalled: false,
      shown: false,
      errorMessage: permissionErrorMessage(permission),
    })
  }

  return new Promise((resolve) => {
    let settled = false
    const finish = (result: DesktopNotificationResult) => {
      if (settled) {
        return
      }
      settled = true
      resolve(result)
    }

    try {
      const notification = new Notification(payload.title, {
        body: payload.body,
        requireInteraction: true,
        silent: false,
        tag: `fund-quant-${Date.now()}`,
        ...options,
      })

      notification.onshow = () => {
        finish({ apiCalled: true, shown: true })
      }

      notification.onerror = () => {
        finish({
          apiCalled: true,
          shown: false,
          errorMessage: '浏览器创建通知失败，请检查系统与浏览器的通知设置',
        })
      }

      notification.onclick = () => {
        window.focus()
        notification.close()
      }

      window.setTimeout(() => {
        finish({
          apiCalled: true,
          shown: false,
          errorMessage:
            '通知 API 已调用，但未检测到横幅展示。请到 macOS 通知中心查看，或按下方说明调整系统提醒样式。',
        })
      }, 2000)
    } catch (error) {
      finish({
        apiCalled: true,
        shown: false,
        errorMessage: error instanceof Error ? error.message : '创建通知失败',
      })
    }
  })
}

export async function showTestNotification(): Promise<DesktopNotificationResult> {
  return showDesktopNotification({
    title: '基金量化助手',
    body: '通知功能已开启。强买卖信号将在数据同步后出现提醒。',
  })
}

interface StrongSignalSummary {
  snapshotId: number
  addCount: number
  reduceCount: number
}

export function maybeNotifyStrongSignals(summary: StrongSignalSummary) {
  if (!getNotificationsEnabled() || !notificationsSupported()) {
    return
  }
  if (Notification.permission !== 'granted') {
    return
  }

  const lastNotified = localStorage.getItem(SNAPSHOT_KEY)
  if (lastNotified === String(summary.snapshotId)) {
    return
  }

  const total = summary.addCount + summary.reduceCount
  if (total === 0) {
    return
  }

  const parts: string[] = []
  if (summary.addCount > 0) {
    parts.push(`${summary.addCount} 条增配`)
  }
  if (summary.reduceCount > 0) {
    parts.push(`${summary.reduceCount} 条减仓`)
  }

  void showDesktopNotification({
    title: '基金量化助手',
    body: `同步完成，${parts.join(' / ')}强信号待查看`,
  })

  localStorage.setItem(SNAPSHOT_KEY, String(summary.snapshotId))
}

export function summarizeStrongSignals(
  snapshotId: number | null,
  signals: Array<{ strength: number; signal_type: string }>,
): StrongSignalSummary | null {
  if (snapshotId === null) {
    return null
  }

  let addCount = 0
  let reduceCount = 0
  for (const signal of signals) {
    if (signal.strength < 4) {
      continue
    }
    if (signal.signal_type === 'add') {
      addCount += 1
    } else if (signal.signal_type === 'reduce') {
      reduceCount += 1
    }
  }

  return { snapshotId, addCount, reduceCount }
}

/** Keep UI preference aligned with actual browser permission. */
export function syncNotificationPreferenceWithPermission(): NotificationPermissionState {
  const permission = getNotificationPermission()
  if (permission !== 'granted' && getNotificationsEnabled()) {
    setNotificationsEnabled(false)
  }
  return permission
}
