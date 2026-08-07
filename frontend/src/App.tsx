import { useCallback, useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'

import './App.css'
import {
  askQuestion,
  apiBaseUrl,
  deleteDocument,
  exportLocalData,
  fetchChatSessions,
  fetchDocuments,
  fetchEvaluationRuns,
  fetchHealth,
  resetLocalData,
  searchDocuments,
  streamQuestion,
  uploadDocument,
  type ChatSessionSummary,
  type DocumentSummary,
  type EvaluationRunSummary,
  type QueryRewriteMetadata,
  type SourceCitation,
} from './api/client'

type BackendStatus = 'checking' | 'online' | 'offline'
type LoadingStatus = 'idle' | 'loading' | 'success' | 'error'
type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking')
  const [backendStatusMessage, setBackendStatusMessage] = useState('正在检查后端连接')
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [documentStatus, setDocumentStatus] = useState<LoadingStatus>('loading')
  const [documentMessage, setDocumentMessage] = useState('正在加载文档列表')
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null)
  const [uploadStatus, setUploadStatus] = useState<LoadingStatus>('idle')
  const [uploadMessage, setUploadMessage] = useState('支持 PDF、TXT、Markdown 文件')
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([])
  const [evaluationRuns, setEvaluationRuns] = useState<EvaluationRunSummary[]>([])
  const [persistenceStatus, setPersistenceStatus] = useState<LoadingStatus>('idle')
  const [persistenceMessage, setPersistenceMessage] = useState('读取本地持久化数据')
  const [adminActionStatus, setAdminActionStatus] = useState<LoadingStatus>('idle')
  const [adminActionMessage, setAdminActionMessage] = useState('导出或清理本地演示数据')
  const [topK, setTopK] = useState(3)
  const [question, setQuestion] = useState('')
  const [chatStatus, setChatStatus] = useState<LoadingStatus>('idle')
  const [chatMessage, setChatMessage] = useState('输入问题后，将基于已上传文档生成回答')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [answerSources, setAnswerSources] = useState<SourceCitation[]>([])
  const [expandedSourceKeys, setExpandedSourceKeys] = useState<Set<string>>(new Set())
  const [retrievalQuestion, setRetrievalQuestion] = useState('')
  const [retrievalStatus, setRetrievalStatus] = useState<LoadingStatus>('idle')
  const [retrievalMessage, setRetrievalMessage] = useState('输入问题后可查看召回片段')
  const [retrievalResults, setRetrievalResults] = useState<SourceCitation[]>([])
  const [retrievalMetadata, setRetrievalMetadata] = useState<QueryRewriteMetadata | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const conversationRef = useRef<HTMLDivElement>(null)

  const loadDocuments = useCallback(async () => {
    setDocumentStatus('loading')
    setDocumentMessage('正在加载文档列表')

    try {
      const nextDocuments = await fetchDocuments()
      setDocuments(nextDocuments)
      setSelectedDocumentId((currentId) => {
        if (nextDocuments.some((document) => document.id === currentId)) {
          return currentId
        }

        return nextDocuments[0]?.id ?? null
      })
      setDocumentStatus('success')
      setDocumentMessage(
        nextDocuments.length > 0 ? `已加载 ${nextDocuments.length} 个文档` : '还没有上传文档',
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : '文档列表加载失败'
      setDocumentStatus('error')
      setDocumentMessage(message)
    }
  }, [])

  const loadPersistenceData = useCallback(async () => {
    setPersistenceStatus('loading')
    setPersistenceMessage('正在加载本地数据')

    try {
      const [nextChatSessions, nextEvaluationRuns] = await Promise.all([
        fetchChatSessions(),
        fetchEvaluationRuns(),
      ])
      setChatSessions(nextChatSessions)
      setEvaluationRuns(nextEvaluationRuns)
      setPersistenceStatus('success')
      setPersistenceMessage('本地数据已加载')
    } catch {
      setPersistenceStatus('error')
      setPersistenceMessage('持久化数据加载失败')
    }
  }, [])

  useEffect(() => {
    let ignore = false

    async function checkBackend() {
      try {
        await fetchHealth()
        if (!ignore) {
          setBackendStatus('online')
          setBackendStatusMessage('后端已连接')
          void loadDocuments()
          void loadPersistenceData()
        }
      } catch {
        if (!ignore) {
          setBackendStatus('offline')
          setBackendStatusMessage('后端未连接')
          setDocumentStatus('error')
          setDocumentMessage('后端未连接，无法加载文档列表')
        }
      }
    }

    void checkBackend()

    return () => {
      ignore = true
    }
  }, [loadDocuments, loadPersistenceData])

  useEffect(() => {
    const conversation = conversationRef.current
    if (conversation && chatMessages.length > 0) {
      conversation.scrollTop = conversation.scrollHeight
    }
  }, [chatMessage, chatMessages])

  const hasProcessingDocuments = documents.some((document) => document.status === 'uploaded')

  useEffect(() => {
    if (backendStatus !== 'online' || !hasProcessingDocuments) {
      return undefined
    }

    const timer = window.setTimeout(() => {
      void loadDocuments()
    }, 2000)

    return () => window.clearTimeout(timer)
  }, [backendStatus, hasProcessingDocuments, loadDocuments])

  async function handleUploadChange(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget
    const file = input.files?.[0]

    if (!file) {
      return
    }

    setUploadStatus('loading')
    setUploadMessage(`正在上传：${file.name}`)

    try {
      const uploadedDocument = await uploadDocument(file)
      setUploadStatus('success')
      setUploadMessage(`上传已接收：${uploadedDocument.filename}`)
      await loadDocuments()
      setSelectedDocumentId(uploadedDocument.id)
    } catch (error) {
      const message = error instanceof Error ? error.message : '上传失败，请稍后重试'
      setUploadStatus('error')
      setUploadMessage(message)
    } finally {
      input.value = ''
    }
  }

  async function handleDeleteDocument(document: DocumentSummary) {
    setDeletingDocumentId(document.id)
    setDocumentStatus('loading')
    setDocumentMessage(`正在删除：${document.filename}`)

    try {
      await deleteDocument(document.id)
      setDocumentStatus('success')
      setDocumentMessage(`已删除：${document.filename}`)
      await loadDocuments()
    } catch (error) {
      const message = error instanceof Error ? error.message : '删除失败，请稍后重试'
      setDocumentStatus('error')
      setDocumentMessage(message)
    } finally {
      setDeletingDocumentId(null)
    }
  }

  async function handleExportLocalData() {
    setAdminActionStatus('loading')
    setAdminActionMessage('正在导出本地数据')

    try {
      const exportedData = await exportLocalData()
      setAdminActionStatus('success')
      setAdminActionMessage(
        `已导出：${exportedData.documents.length} 个文档，${exportedData.chat_sessions.length} 个问答，${exportedData.evaluation_runs.length} 次评估`,
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出失败，请稍后重试'
      setAdminActionStatus('error')
      setAdminActionMessage(message)
    }
  }

  async function handleResetLocalData() {
    setAdminActionStatus('loading')
    setAdminActionMessage('正在清理问答和评估记录')

    try {
      await resetLocalData({
        reset_chat_history: true,
        reset_evaluations: true,
        reset_documents: false,
      })
      setAdminActionStatus('success')
      setAdminActionMessage('已清理问答和评估记录，文档保留')
      await loadPersistenceData()
    } catch (error) {
      const message = error instanceof Error ? error.message : '清理失败，请稍后重试'
      setAdminActionStatus('error')
      setAdminActionMessage(message)
    }
  }

  async function handleRetrievalSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuestion = retrievalQuestion.trim()
    if (!trimmedQuestion) {
      setRetrievalStatus('error')
      setRetrievalMessage('请输入检索问题')
      return
    }

    setRetrievalStatus('loading')
    setRetrievalMessage('正在检索相关片段')

    try {
      const response = await searchDocuments({ question: trimmedQuestion, top_k: topK })
      setRetrievalResults(response.results)
      setRetrievalMetadata({
        query: response.query,
        retrieval_query: response.retrieval_query,
        query_rewritten: response.query_rewritten,
      })
      setRetrievalStatus('success')
      setRetrievalMessage(
        response.results.length > 0 ? `已召回 ${response.results.length} 个片段` : '没有召回片段',
      )
    } catch (error) {
      const message = error instanceof Error ? error.message : '检索失败，请稍后重试'
      setRetrievalStatus('error')
      setRetrievalMessage(message)
      setRetrievalMetadata(null)
    }
  }

  async function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      setChatStatus('error')
      setChatMessage('请输入问题后再提问')
      return
    }

    setChatStatus('loading')
    setChatMessage('正在检索文档并生成回答')
    const answerId = `answer-${Date.now()}`
    setChatMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `question-${Date.now()}`,
        role: 'user',
        content: trimmedQuestion,
      },
      {
        id: answerId,
        role: 'assistant',
        content: '',
      },
    ])

    try {
      await streamQuestion(
        { question: trimmedQuestion, top_k: topK },
        {
          onToken: (delta) => {
            setChatMessages((currentMessages) =>
              currentMessages.map((message) =>
                message.id === answerId
                  ? {
                      ...message,
                      content: `${message.content}${delta}`,
                    }
                  : message,
              ),
            )
          },
          onSources: (sources) => {
            setAnswerSources(sources)
          },
          onRetrieval: (metadata) => {
            setRetrievalMetadata(metadata)
          },
        },
      )
      setExpandedSourceKeys(new Set())
      setChatStatus('success')
      setChatMessage('回答已生成')
      setQuestion('')
      void loadPersistenceData()
    } catch {
      try {
        const response = await askQuestion({ question: trimmedQuestion, top_k: topK })
        setChatMessages((currentMessages) =>
          currentMessages.map((message) =>
            message.id === answerId
              ? {
                  ...message,
                  content: response.answer,
                }
              : message,
          ),
        )
        setAnswerSources(response.sources)
        setExpandedSourceKeys(new Set())
        setChatStatus('success')
        setChatMessage('回答已生成')
        setQuestion('')
        void loadPersistenceData()
      } catch (fallbackError) {
        setChatMessages((currentMessages) =>
          currentMessages.filter((message) => message.id !== answerId),
        )
        const message = fallbackError instanceof Error ? fallbackError.message : '提问失败，请稍后重试'
        setChatStatus('error')
        setChatMessage(message)
      }
    }
  }

  const canAsk = backendStatus === 'online' && chatStatus !== 'loading'
  const canSearch = backendStatus === 'online' && retrievalStatus !== 'loading'
  const canUseAdminActions = backendStatus === 'online' && adminActionStatus !== 'loading'

  return (
    <main className="app-shell">
      <header className="topbar" aria-label="应用头部">
        <div>
          <p className="eyebrow">本地 RAG 工作台</p>
          <h1>RAG Knowledge Base</h1>
        </div>
        <div
          className={`backend-status ${backendStatus}`}
          title={`API 地址：${apiBaseUrl}`}
          aria-live="polite"
        >
          <span className="status-dot" aria-hidden="true" />
          <span>{backendStatusMessage}</span>
        </div>
      </header>

      <section className="workspace" aria-label="文档问答工作区">
        <aside className="documents-panel" aria-labelledby="documents-title">
          <div className="panel-heading">
            <div>
              <p className="section-label">文档</p>
              <h2 id="documents-title">知识文件</h2>
            </div>
            <button
              className="secondary-button"
              disabled={uploadStatus === 'loading' || backendStatus !== 'online'}
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              上传
            </button>
          </div>

          <label className={`upload-zone ${uploadStatus}`} aria-label="文件上传区域">
            <input
              accept=".pdf,.txt,.md,.markdown,application/pdf,text/plain,text/markdown"
              aria-label="选择文档文件"
              disabled={uploadStatus === 'loading' || backendStatus !== 'online'}
              onChange={(event) => void handleUploadChange(event)}
              ref={fileInputRef}
              type="file"
            />
            <span className="upload-icon" aria-hidden="true">
              +
            </span>
            <div>
              <strong>
                {uploadStatus === 'loading' ? '正在处理文档' : '选择 PDF、TXT 或 Markdown'}
              </strong>
              <p>{uploadMessage}</p>
            </div>
          </label>

          <div className="document-list" aria-label="已上传文档">
            <p className={`document-state ${documentStatus}`}>{documentMessage}</p>
            {hasProcessingDocuments ? (
              <p className="document-processing-note">文档处理中，完成后会自动刷新索引状态。</p>
            ) : null}
            {documents.length > 0
              ? documents.map((document) => (
                  <article
                    className={
                      document.id === selectedDocumentId ? 'document-row active' : 'document-row'
                    }
                    key={document.id}
                    onClick={() => setSelectedDocumentId(document.id)}
                  >
                    <div className="file-type">{document.type.toUpperCase()}</div>
                    <div className="document-meta">
                      <h3>{document.filename}</h3>
                      <span className={`document-status-badge ${document.status}`}>
                        {formatDocumentStatus(document.status)}
                      </span>
                      <p>
                        {document.chunk_count} 个片段 · {document.created_at}
                      </p>
                    </div>
                    <button
                      aria-label={`删除 ${document.filename}`}
                      className="document-delete-button"
                      disabled={deletingDocumentId === document.id || backendStatus !== 'online'}
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleDeleteDocument(document)
                      }}
                      type="button"
                    >
                      {deletingDocumentId === document.id ? '删除中' : '删除'}
                    </button>
                  </article>
                ))
              : null}
          </div>

          <section className="persistence-panel" aria-label="本地持久化数据">
            <div className="persistence-heading">
              <div>
                <p className="section-label">持久化</p>
                <h3>本地数据</h3>
              </div>
              <span className={`persistence-state ${persistenceStatus}`}>{persistenceMessage}</span>
            </div>

            <div className="persistence-actions">
              <button
                disabled={!canUseAdminActions}
                onClick={() => void handleExportLocalData()}
                type="button"
              >
                导出数据
              </button>
              <button
                disabled={!canUseAdminActions}
                onClick={() => void handleResetLocalData()}
                type="button"
              >
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
        </aside>

        <section className="chat-panel" aria-labelledby="chat-title">
          <div className="panel-heading">
            <div>
              <p className="section-label">助手</p>
              <h2 id="chat-title">基于文档提问</h2>
            </div>
            <label className="topk-control">
              <span>Top-K</span>
              <select
                aria-label="Top-K 来源数量"
                disabled={chatStatus === 'loading'}
                onChange={(event) => setTopK(Number(event.currentTarget.value))}
                value={topK}
              >
                <option value="3">3</option>
                <option value="5">5</option>
                <option value="8">8</option>
              </select>
            </label>
          </div>

          <div className="conversation" aria-label="问答记录" ref={conversationRef}>
            {chatMessages.length > 0 ? (
              chatMessages.map((message) => (
                <article
                  className={
                    message.role === 'user' ? 'message user-message' : 'message assistant-message'
                  }
                  key={message.id}
                >
                  <span className="message-role">{message.role === 'user' ? '问题' : '回答'}</span>
                  <p>{message.content}</p>
                </article>
              ))
            ) : (
              <article className="message assistant-message empty-message">
                <span className="message-role">回答</span>
                <p>上传文档后，可以在这里提出问题并查看基于来源的回答。</p>
              </article>
            )}
            <p className={`chat-state ${chatStatus}`} aria-live="polite">
              {chatMessage}
            </p>
          </div>

          <section className="retrieval-panel" aria-label="检索详情">
            <div className="retrieval-heading">
              <h3>检索详情</h3>
              <span>{retrievalResults.length} 个召回片段</span>
            </div>
            <form
              className="retrieval-form"
              aria-label="检索文档片段"
              onSubmit={(event) => void handleRetrievalSubmit(event)}
            >
              <label htmlFor="retrieval-question">检索问题</label>
              <div className="retrieval-input-row">
                <input
                  id="retrieval-question"
                  onChange={(event) => setRetrievalQuestion(event.currentTarget.value)}
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
                        onClick={() => {
                          setExpandedSourceKeys((currentKeys) => {
                            const nextKeys = new Set(currentKeys)
                            if (nextKeys.has(sourceKey)) {
                              nextKeys.delete(sourceKey)
                            } else {
                              nextKeys.add(sourceKey)
                            }
                            return nextKeys
                          })
                        }}
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

          <form className="chat-input" aria-label="提出问题" onSubmit={(event) => void handleChatSubmit(event)}>
            <label htmlFor="question">问题</label>
            <div className="input-row">
              <input
                id="question"
                onChange={(event) => setQuestion(event.currentTarget.value)}
                placeholder="输入一个基于已上传文档的问题"
                value={question}
                type="text"
              />
              <button disabled={!canAsk} type="submit">
                {chatStatus === 'loading' ? '生成中' : '提问'}
              </button>
            </div>
          </form>
        </section>
      </section>
    </main>
  )
}

function formatSourcePreview(content: string) {
  return content
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function getSourceKey(source: SourceCitation, index: number) {
  return `${source.filename}-${source.page}-${source.chunk_index}-${index}`
}

function formatDocumentStatus(status: DocumentSummary['status']) {
  const statusLabels: Record<DocumentSummary['status'], string> = {
    uploaded: '已上传',
    indexed: '已索引',
    failed: '处理失败',
    deleted: '已删除',
  }

  return statusLabels[status]
}

export default App
