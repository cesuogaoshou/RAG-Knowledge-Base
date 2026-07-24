import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react'

import './App.css'
import {
  apiBaseUrl,
  fetchDocuments,
  fetchHealth,
  uploadDocument,
  type DocumentSummary,
} from './api/client'

type BackendStatus = 'checking' | 'online' | 'offline'
type LoadingStatus = 'idle' | 'loading' | 'success' | 'error'

const sources = [
  {
    filename: 'phase2-test.md',
    page: 1,
    score: '0.84',
    excerpt:
      'RAG 会先检索相关文档片段，再把这些上下文交给模型生成有依据的回答。',
  },
  {
    filename: 'course-notes.txt',
    page: 1,
    score: '0.72',
    excerpt:
      '后端会把解析后的文本片段和元数据存入 ChromaDB，方便后续问题进行语义检索。',
  },
]

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking')
  const [backendStatusMessage, setBackendStatusMessage] = useState('正在检查后端连接')
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [documentStatus, setDocumentStatus] = useState<LoadingStatus>('loading')
  const [documentMessage, setDocumentMessage] = useState('正在加载文档列表')
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)
  const [uploadStatus, setUploadStatus] = useState<LoadingStatus>('idle')
  const [uploadMessage, setUploadMessage] = useState('支持 PDF、TXT、Markdown 文件')
  const fileInputRef = useRef<HTMLInputElement>(null)

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
              <select defaultValue="3" aria-label="Top-K 来源数量">
                <option value="3">3</option>
                <option value="5">5</option>
                <option value="8">8</option>
              </select>
            </label>
          </div>

          <div className="conversation" aria-label="问答记录">
            <article className="message user-message">
              <span className="message-role">问题</span>
              <p>这个项目是如何实现文档问答的？</p>
            </article>
            <article className="message assistant-message">
              <span className="message-role">回答</span>
              <p>
                这个项目会上传私有文档，将文本切分成片段，把向量存入 ChromaDB，
                再根据问题检索最相关的片段，并调用 DeepSeek Chat 生成带来源引用的回答。
              </p>
            </article>
          </div>

          <section className="sources-panel" aria-label="回答来源">
            <div className="sources-heading">
              <h3>引用来源</h3>
              <span>{sources.length} 个匹配片段</span>
            </div>
            <div className="source-list">
              {sources.map((source) => (
                <article className="source-card" key={`${source.filename}-${source.score}`}>
                  <div className="source-meta">
                    <strong>{source.filename}</strong>
                    <span>
                      第 {source.page} 页 · 相似度 {source.score}
                    </span>
                  </div>
                  <p>{source.excerpt}</p>
                </article>
              ))}
            </div>
          </section>

          <form className="chat-input" aria-label="提出问题">
            <label htmlFor="question">问题</label>
            <div className="input-row">
              <input
                id="question"
                placeholder="输入一个基于已上传文档的问题"
                type="text"
              />
              <button type="submit">提问</button>
            </div>
          </form>
        </section>
      </section>
    </main>
  )
}

export default App
