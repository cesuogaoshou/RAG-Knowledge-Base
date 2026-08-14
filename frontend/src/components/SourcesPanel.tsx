import { formatSourcePreview, getSourceKey } from './formatters'
import type { SourceCitation } from './types'

type SourcesPanelProps = {
  answerSources: SourceCitation[]
  expandedSourceKeys: Set<string>
  onToggleSource: (sourceKey: string) => void
}

export function SourcesPanel({
  answerSources,
  expandedSourceKeys,
  onToggleSource,
}: SourcesPanelProps) {
  return (
    <section className="sources-panel" aria-label="回答来源">
      <div className="sources-heading">
        <h3>引用来源</h3>
        <span>{answerSources.length} 个匹配片段</span>
      </div>
      <div className="source-list">
        {answerSources.length > 0 ? (
          answerSources.map((source, index) => {
            const sourceKey = getSourceKey(source, index)
            const isExpanded = expandedSourceKeys.has(sourceKey)

            return (
              <article className="source-card" key={sourceKey}>
                <div className="source-meta">
                  <strong>{source.filename}</strong>
                  <span>
                    第 {source.page} 页 · 相似度 {source.score.toFixed(3)}
                  </span>
                </div>
                <p>{formatSourcePreview(source.content)}</p>
                <button
                  aria-expanded={isExpanded}
                  aria-label={`${isExpanded ? '收起' : '展开'} ${source.filename} 第 ${
                    source.page
                  } 页 Chunk ${source.chunk_index}`}
                  className="source-expand-button"
                  onClick={() => onToggleSource(sourceKey)}
                  type="button"
                >
                  {isExpanded ? '收起片段' : '展开片段'}
                </button>
                {isExpanded ? (
                  <div className="source-detail">
                    <span>
                      Chunk {source.chunk_index} · 第 {source.page} 页 · 相似度{' '}
                      {source.score.toFixed(3)}
                    </span>
                    <p>{source.content}</p>
                  </div>
                ) : null}
              </article>
            )
          })
        ) : (
          <p className="source-empty">完成一次提问后，这里会显示后端返回的来源片段。</p>
        )}
      </div>
    </section>
  )
}
