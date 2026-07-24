import { useEffect, useState } from 'react'

import './App.css'
import { apiBaseUrl, fetchHealth } from './api/client'

type BackendStatus = 'checking' | 'online' | 'offline'

const documents = [
  {
    id: 'doc-a',
    filename: 'phase2-test.md',
    type: 'MD',
    uploadedAt: '今天',
    chunks: 1,
    active: true,
  },
  {
    id: 'doc-b',
    filename: 'course-notes.txt',
    type: 'TXT',
    uploadedAt: '示例',
    chunks: 8,
    active: false,
  },
]

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

  useEffect(() => {
    let ignore = false

    async function checkBackend() {
      try {
        await fetchHealth()
        if (!ignore) {
          setBackendStatus('online')
          setBackendStatusMessage('后端已连接')
        }
      } catch {
        if (!ignore) {
          setBackendStatus('offline')
          setBackendStatusMessage('后端未连接')
        }
      }
    }

    void checkBackend()

    return () => {
      ignore = true
    }
  }, [])

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
            <button className="secondary-button" type="button">
              上传
            </button>
          </div>

          <div className="upload-zone" aria-label="文件上传区域">
            <span className="upload-icon" aria-hidden="true">
              +
            </span>
            <div>
              <strong>拖入 PDF、TXT 或 Markdown</strong>
              <p>文件会被切分为可检索片段，并在回答中提供引用来源。</p>
            </div>
          </div>

          <div className="document-list" aria-label="已上传文档">
            {documents.map((document) => (
              <article
                className={document.active ? 'document-row active' : 'document-row'}
                key={document.id}
              >
                <div className="file-type">{document.type}</div>
                <div className="document-meta">
                  <h3>{document.filename}</h3>
                  <p>
                    {document.chunks} 个片段 · {document.uploadedAt}
                  </p>
                </div>
              </article>
            ))}
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
