export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export type HealthResponse = {
  status: string
}

export type DocumentSummary = {
  id: string
  filename: string
  type: string
  created_at: string
  chunk_count: number
  status: 'uploaded' | 'indexed' | 'failed' | 'deleted'
}

export type UploadedDocument = DocumentSummary & {
  saved_path: string
  text_length: number
  page_count: number
  pages: Array<{
    page: number
    text: string
  }>
}

export type DeleteDocumentResponse = {
  id: string
  deleted: boolean
}

export type SourceCitation = {
  filename: string
  page: number
  chunk_index: number
  content: string
  score: number
}

export type ChatResponse = {
  answer: string
  sources: SourceCitation[]
  session_id?: string | null
}

export type SearchResponse = {
  query: string
  top_k: number
  results: SourceCitation[]
}

export type ChatSessionSummary = {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export type EvaluationRunSummary = {
  id: string
  created_at: string
  mode: string
  case_count: number
  source_hit_rate: number
  marker_hit_rate: number
  refusal_accuracy: number
  recommendation: string | null
  parameters: Record<string, unknown>
}

export type LocalExportResponse = {
  documents: Array<Record<string, unknown>>
  chat_sessions: Array<Record<string, unknown>>
  evaluation_runs: Array<Record<string, unknown>>
}

export type ResetLocalDataRequest = {
  reset_chat_history: boolean
  reset_evaluations: boolean
  reset_documents: boolean
}

export type ResetLocalDataResponse = ResetLocalDataRequest

type ChatRequest = {
  question: string
  top_k: number
}

type StreamQuestionHandlers = {
  onToken: (delta: string) => void
  onSources: (sources: SourceCitation[]) => void
}

type ApiErrorBody = {
  detail?: unknown
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestJsonOptions = RequestInit & {
  timeoutMs?: number
}

async function requestJson<T>(path: string, init: RequestJsonOptions = {}): Promise<T> {
  const { timeoutMs, signal, ...fetchInit } = init
  const controller = timeoutMs ? new AbortController() : undefined
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), timeoutMs)
    : undefined

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...fetchInit,
      signal: controller?.signal ?? signal,
    })

    if (!response.ok) {
      let message = `请求失败：${response.status}`

      try {
        const errorBody = (await response.json()) as ApiErrorBody
        if (typeof errorBody.detail === 'string') {
          message = errorBody.detail
        }
      } catch {
        // Keep the status-based message when the backend returns a non-JSON error body.
      }

      throw new ApiError(message, response.status)
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请确认后端服务是否已启动。', 0)
    }
    throw error
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
    }
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/health', { timeoutMs: 2500 })
}

export async function uploadDocument(file: File): Promise<UploadedDocument> {
  const formData = new FormData()
  formData.append('file', file)

  return requestJson<UploadedDocument>('/api/documents/upload', {
    method: 'POST',
    body: formData,
  })
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  return requestJson<DocumentSummary[]>('/api/documents')
}

export async function deleteDocument(documentId: string): Promise<DeleteDocumentResponse> {
  return requestJson<DeleteDocumentResponse>(`/api/documents/${documentId}`, {
    method: 'DELETE',
  })
}

export async function searchDocuments(request: ChatRequest): Promise<SearchResponse> {
  return requestJson<SearchResponse>('/api/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
}

export async function askQuestion(request: ChatRequest): Promise<ChatResponse> {
  return requestJson<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
}

export async function fetchChatSessions(): Promise<ChatSessionSummary[]> {
  return requestJson<ChatSessionSummary[]>('/api/chat/sessions')
}

export async function fetchEvaluationRuns(): Promise<EvaluationRunSummary[]> {
  return requestJson<EvaluationRunSummary[]>('/api/evaluations')
}

export async function exportLocalData(): Promise<LocalExportResponse> {
  return requestJson<LocalExportResponse>('/api/admin/export')
}

export async function resetLocalData(
  request: ResetLocalDataRequest,
): Promise<ResetLocalDataResponse> {
  return requestJson<ResetLocalDataResponse>('/api/admin/reset', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
}

export async function streamQuestion(
  request: ChatRequest,
  handlers: StreamQuestionHandlers,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let message = `请求失败：${response.status}`

    try {
      const errorBody = (await response.json()) as ApiErrorBody
      if (typeof errorBody.detail === 'string') {
        message = errorBody.detail
      }
    } catch {
      // Keep the status-based message when the backend returns a non-JSON error body.
    }

    throw new ApiError(message, response.status)
  }

  if (!response.body) {
    throw new ApiError('浏览器不支持流式响应。', 0)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    buffer = parseSseBuffer(buffer, handlers)
  }

  buffer += decoder.decode()
  parseSseBuffer(`${buffer}\n\n`, handlers)
}

function parseSseBuffer(buffer: string, handlers: StreamQuestionHandlers): string {
  const events = buffer.split('\n\n')
  const remaining = events.pop() ?? ''

  for (const eventBlock of events) {
    const eventName = eventBlock
      .split('\n')
      .find((line) => line.startsWith('event: '))
      ?.slice('event: '.length)
      .trim()
    const dataLine = eventBlock.split('\n').find((line) => line.startsWith('data: '))

    if (!eventName || !dataLine) {
      continue
    }

    const data = JSON.parse(dataLine.slice('data: '.length))
    if (eventName === 'token' && typeof data.delta === 'string') {
      handlers.onToken(data.delta)
    }
    if (eventName === 'sources' && Array.isArray(data.sources)) {
      handlers.onSources(data.sources as SourceCitation[])
    }
  }

  return remaining
}
