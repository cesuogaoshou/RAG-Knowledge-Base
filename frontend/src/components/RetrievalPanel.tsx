import type { FormEvent } from 'react'

import type { LoadingStatus, QueryRewriteMetadata, SourceCitation } from './types'

type RetrievalPanelProps = {
  retrievalQuestion: string
  retrievalStatus: LoadingStatus
  retrievalMessage: string
  retrievalResults: SourceCitation[]
  retrievalMetadata: QueryRewriteMetadata | null
  canSearch: boolean
  onRetrievalQuestionChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function RetrievalPanel({
  retrievalQuestion,
  retrievalStatus,
  retrievalMessage,
  retrievalResults,
  retrievalMetadata,
  canSearch,
  onRetrievalQuestionChange,
  onSubmit,
}: RetrievalPanelProps) {
  return (
    <section className="retrieval-panel" aria-label="检索详情">
      <div className="retrieval-heading">
        <h3>检索详情</h3>
        <span>{retrievalResults.length} 个召回片段</span>
      </div>
      <form className="retrieval-form" aria-label="检索文档片段" onSubmit={onSubmit}>
        <label htmlFor="retrieval-question">检索问题</label>
        <div className="retrieval-input-row">
          <input
            id="retrieval-question"
            onChange={(event) => onRetrievalQuestionChange(event.currentTarget.value)}
            placeholder="输入问题查看召回片段"
            type="text"
            value={retrievalQuestion}
          />
          <button disabled={!canSearch} type="submit">
            {retrievalStatus === 'loading' ? '检索中' : '检索'}
          </button>
        </div>
      </form>
      <p className={`retrieval-state ${retrievalStatus}`} aria-live="polite">
        {retrievalMessage}
      </p>
      {retrievalMetadata ? (
        <div className="retrieval-query-debug" aria-label="检索问题改写状态">
          <span>{retrievalMetadata.query_rewritten ? '已改写为' : '检索问题未改写'}</span>
          <p>{retrievalMetadata.retrieval_query}</p>
        </div>
      ) : null}
      <div className="retrieval-list">
        {retrievalResults.length > 0
          ? retrievalResults.map((result, index) => (
              <article
                className="retrieval-card"
                key={`${result.filename}-${result.page}-${result.chunk_index}-${index}`}
              >
                <div className="source-meta">
                  <strong>{result.filename}</strong>
                  <span>
                    Chunk {result.chunk_index} · 第 {result.page} 页 · 相似度{' '}
                    {result.score.toFixed(3)}
                  </span>
                </div>
                <p>{result.content}</p>
              </article>
            ))
          : null}
      </div>
    </section>
  )
}
