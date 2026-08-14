import type {
  ChatSessionSummary,
  DocumentSummary,
  EvaluationRunSummary,
  QueryRewriteMetadata,
  SourceCitation,
} from '../api/client'

export type BackendStatus = 'checking' | 'online' | 'offline'
export type LoadingStatus = 'idle' | 'loading' | 'success' | 'error'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export type {
  ChatSessionSummary,
  DocumentSummary,
  EvaluationRunSummary,
  QueryRewriteMetadata,
  SourceCitation,
}
