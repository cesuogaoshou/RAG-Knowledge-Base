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
} from './api/client'
import { ChatPanel } from './components/ChatPanel'
import { DocumentPanel } from './components/DocumentPanel'
import { PersistencePanel } from './components/PersistencePanel'
import type {
  BackendStatus,
  ChatMessage,
  ChatSessionSummary,
  DocumentSummary,
  EvaluationRunSummary,
  LoadingStatus,
  QueryRewriteMetadata,
  SourceCitation,
} from './components/types'

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

  function handleToggleSource(sourceKey: string) {
    setExpandedSourceKeys((currentKeys) => {
      const nextKeys = new Set(currentKeys)
      if (nextKeys.has(sourceKey)) {
        nextKeys.delete(sourceKey)
      } else {
        nextKeys.add(sourceKey)
      }
      return nextKeys
    })
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
          <DocumentPanel
            backendStatus={backendStatus}
            deletingDocumentId={deletingDocumentId}
            documentMessage={documentMessage}
            documentStatus={documentStatus}
            documents={documents}
            fileInputRef={fileInputRef}
            hasProcessingDocuments={hasProcessingDocuments}
            onDeleteDocument={(document) => void handleDeleteDocument(document)}
            onSelectDocument={setSelectedDocumentId}
            onUploadChange={(event) => void handleUploadChange(event)}
            selectedDocumentId={selectedDocumentId}
            uploadMessage={uploadMessage}
            uploadStatus={uploadStatus}
          />
          <PersistencePanel
            adminActionMessage={adminActionMessage}
            adminActionStatus={adminActionStatus}
            canUseAdminActions={canUseAdminActions}
            chatSessions={chatSessions}
            evaluationRuns={evaluationRuns}
            onExportLocalData={() => void handleExportLocalData()}
            onResetLocalData={() => void handleResetLocalData()}
            persistenceMessage={persistenceMessage}
            persistenceStatus={persistenceStatus}
          />
        </aside>

        <ChatPanel
          answerSources={answerSources}
          canAsk={canAsk}
          canSearch={canSearch}
          chatMessage={chatMessage}
          chatMessages={chatMessages}
          chatStatus={chatStatus}
          conversationRef={conversationRef}
          expandedSourceKeys={expandedSourceKeys}
          onChatSubmit={(event) => void handleChatSubmit(event)}
          onQuestionChange={setQuestion}
          onRetrievalQuestionChange={setRetrievalQuestion}
          onRetrievalSubmit={(event) => void handleRetrievalSubmit(event)}
          onToggleSource={handleToggleSource}
          onTopKChange={setTopK}
          question={question}
          retrievalMessage={retrievalMessage}
          retrievalMetadata={retrievalMetadata}
          retrievalQuestion={retrievalQuestion}
          retrievalResults={retrievalResults}
          retrievalStatus={retrievalStatus}
          topK={topK}
        />
      </section>
    </main>
  )
}

export default App
