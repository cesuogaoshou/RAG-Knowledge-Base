import { useCallback, useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'

import './App.css'
import {
  askQuestion,
  apiBaseUrl,
  fetchDocuments,
  fetchHealth,
  uploadDocument,
  type DocumentSummary,
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
  const [uploadStatus, setUploadStatus] = useState<LoadingStatus>('idle')
  const [uploadMessage, setUploadMessage] = useState('支持 PDF、TXT、Markdown 文件')
  const [topK, setTopK] = useState(3)
  const [question, setQuestion] = useState('')
  const [chatStatus, setChatStatus] = useState<LoadingStatus>('idle')
  const [chatMessage, setChatMessage] = useState('输入问题后，将基于已上传文档生成回答')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [answerSources, setAnswerSources] = useState<SourceCitation[]>([])
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

  useEffect(() => {
    let ignore = false

    async function checkBackend() {
      try {
        await fetchHealth()
        if (!ignore) {
          setBackendStatus('online')
          setBackendStatusMessage('后端已连接')
          void loadDocuments()
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
  }, [loadDocuments])

  useEffect(() => {
    const conversation = conversationRef.current
    if (conversation && chatMessages.length > 0) {
      conversation.scrollTop = conversation.scrollHeight
    }
  }, [chatMessage, chatMessages])

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
      setUploadMessage(`上传完成：${uploadedDocument.filename}`)
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
    setChatMessages((currentMessages) => [
      ...currentMessages,
      {
        id: `question-${Date.now()}`,
        role: 'user',
        content: trimmedQuestion,
      },
    ])

    try {
      const response = await askQuestion({ question: trimmedQuestion, top_k: topK })
      setChatMessages((currentMessages) => [
        ...currentMessages,
        {
          id: `answer-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
        },
      ])
      setAnswerSources(response.sources)
      setChatStatus('success')
      setChatMessage('回答已生成')
      setQuestion('')
    } catch (error) {
      const message = error instanceof Error ? error.message : '提问失败，请稍后重试'
      setChatStatus('error')
      setChatMessage(message)
    }
  }

  const canAsk = backendStatus === 'online' && chatStatus !== 'loading'

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
                      <p>
                        {document.chunk_count} 个片段 · {document.created_at}
                      </p>
                    </div>
                  </article>
                ))
              : null}
          </div>
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

          <section className="sources-panel" aria-label="回答来源">
            <div className="sources-heading">
              <h3>引用来源</h3>
              <span>{answerSources.length} 个匹配片段</span>
            </div>
            <div className="source-list">
              {answerSources.length > 0 ? (
                answerSources.map((source, index) => (
                  <article
                    className="source-card"
                    key={`${source.filename}-${source.page}-${source.chunk_index}-${index}`}
                  >
                    <div className="source-meta">
                      <strong>{source.filename}</strong>
                      <span>
                        第 {source.page} 页 · 相似度 {source.score.toFixed(3)}
                      </span>
                    </div>
                    <p>{formatSourcePreview(source.content)}</p>
                  </article>
                ))
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

export default App
