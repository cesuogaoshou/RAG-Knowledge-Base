import type { ChangeEvent, RefObject } from 'react'

import { formatDocumentStatus } from './formatters'
import type { BackendStatus, DocumentSummary, LoadingStatus } from './types'

type DocumentPanelProps = {
  backendStatus: BackendStatus
  documents: DocumentSummary[]
  documentStatus: LoadingStatus
  documentMessage: string
  selectedDocumentId: string | null
  deletingDocumentId: string | null
  uploadStatus: LoadingStatus
  uploadMessage: string
  hasProcessingDocuments: boolean
  fileInputRef: RefObject<HTMLInputElement | null>
  onUploadChange: (event: ChangeEvent<HTMLInputElement>) => void
  onSelectDocument: (documentId: string) => void
  onDeleteDocument: (document: DocumentSummary) => void
}

export function DocumentPanel({
  backendStatus,
  documents,
  documentStatus,
  documentMessage,
  selectedDocumentId,
  deletingDocumentId,
  uploadStatus,
  uploadMessage,
  hasProcessingDocuments,
  fileInputRef,
  onUploadChange,
  onSelectDocument,
  onDeleteDocument,
}: DocumentPanelProps) {
  return (
    <>
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
          onChange={onUploadChange}
          ref={fileInputRef}
          type="file"
        />
        <span className="upload-icon" aria-hidden="true">
          +
        </span>
        <div>
          <strong>{uploadStatus === 'loading' ? '正在处理文档' : '选择 PDF、TXT 或 Markdown'}</strong>
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
                className={document.id === selectedDocumentId ? 'document-row active' : 'document-row'}
                key={document.id}
                onClick={() => onSelectDocument(document.id)}
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
                    onDeleteDocument(document)
                  }}
                  type="button"
                >
                  {deletingDocumentId === document.id ? '删除中' : '删除'}
                </button>
              </article>
            ))
          : null}
      </div>
    </>
  )
}
