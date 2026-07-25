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
}

export type SearchResponse = {
  query: string
  top_k: number
  results: SourceCitation[]
}

type ChatRequest = {
  question: string
  top_k: number
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
