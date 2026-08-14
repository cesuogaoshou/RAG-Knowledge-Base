import type { ChatSessionSummary, EvaluationRunSummary, LoadingStatus } from './types'

type PersistencePanelProps = {
  chatSessions: ChatSessionSummary[]
  evaluationRuns: EvaluationRunSummary[]
  persistenceStatus: LoadingStatus
  persistenceMessage: string
  adminActionStatus: LoadingStatus
  adminActionMessage: string
  canUseAdminActions: boolean
  onExportLocalData: () => void
  onResetLocalData: () => void
}

export function PersistencePanel({
  chatSessions,
  evaluationRuns,
  persistenceStatus,
  persistenceMessage,
  adminActionStatus,
  adminActionMessage,
  canUseAdminActions,
  onExportLocalData,
  onResetLocalData,
}: PersistencePanelProps) {
  return (
    <section className="persistence-panel" aria-label="本地持久化数据">
      <div className="persistence-heading">
        <div>
          <p className="section-label">持久化</p>
          <h3>本地数据</h3>
        </div>
        <span className={`persistence-state ${persistenceStatus}`}>{persistenceMessage}</span>
      </div>

      <div className="persistence-actions">
        <button disabled={!canUseAdminActions} onClick={onExportLocalData} type="button">
          导出数据
        </button>
        <button disabled={!canUseAdminActions} onClick={onResetLocalData} type="button">
          安全清理
        </button>
      </div>
      <p className={`admin-state ${adminActionStatus}`} aria-live="polite">
        {adminActionMessage}
      </p>

      <div className="persistence-grid">
        <section className="persistence-group" aria-label="最近问答">
          <h4>最近问答</h4>
          {chatSessions.length > 0 ? (
            chatSessions.slice(0, 3).map((session) => (
              <article className="persistence-row" key={session.id}>
                <strong>{session.title}</strong>
                <span>{session.message_count} 条消息</span>
              </article>
            ))
          ) : (
            <p>暂无问答记录</p>
          )}
        </section>

        <section className="persistence-group" aria-label="评估记录">
          <h4>评估记录</h4>
          {evaluationRuns.length > 0 ? (
            evaluationRuns.slice(0, 3).map((run) => (
              <article className="persistence-row evaluation-row" key={run.id}>
                <strong>
                  {run.mode} · {run.case_count} cases
                </strong>
                <span>命中 {run.source_hit_rate.toFixed(2)}</span>
                <span>证据 {run.marker_hit_rate.toFixed(2)}</span>
                <span>拒答 {run.refusal_accuracy.toFixed(2)}</span>
              </article>
            ))
          ) : (
            <p>暂无评估记录</p>
          )}
        </section>
      </div>
    </section>
  )
}
