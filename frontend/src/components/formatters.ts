import type { DocumentSummary, SourceCitation } from './types'

export function formatSourcePreview(content: string) {
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

export function getSourceKey(source: SourceCitation, index: number) {
  return `${source.filename}-${source.page}-${source.chunk_index}-${index}`
}

export function formatDocumentStatus(status: DocumentSummary['status']) {
  const statusLabels: Record<DocumentSummary['status'], string> = {
    uploaded: '已上传',
    indexed: '已索引',
    failed: '处理失败',
    deleted: '已删除',
  }

  return statusLabels[status]
}
