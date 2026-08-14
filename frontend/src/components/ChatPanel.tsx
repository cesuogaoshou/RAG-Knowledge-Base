import type { FormEvent, RefObject } from 'react'

import { RetrievalPanel } from './RetrievalPanel'
import { SourcesPanel } from './SourcesPanel'
import type { ChatMessage, LoadingStatus, QueryRewriteMetadata, SourceCitation } from './types'

type ChatPanelProps = {
  topK: number
  question: string
  chatStatus: LoadingStatus
  chatMessage: string
  chatMessages: ChatMessage[]
  answerSources: SourceCitation[]
  expandedSourceKeys: Set<string>
  retrievalQuestion: string
  retrievalStatus: LoadingStatus
  retrievalMessage: string
  retrievalResults: SourceCitation[]
  retrievalMetadata: QueryRewriteMetadata | null
  canAsk: boolean
  canSearch: boolean
  conversationRef: RefObject<HTMLDivElement | null>
  onTopKChange: (value: number) => void
  onQuestionChange: (value: string) => void
  onChatSubmit: (event: FormEvent<HTMLFormElement>) => void
  onRetrievalQuestionChange: (value: string) => void
  onRetrievalSubmit: (event: FormEvent<HTMLFormElement>) => void
  onToggleSource: (sourceKey: string) => void
}

export function ChatPanel({
  topK,
  question,
  chatStatus,
  chatMessage,
  chatMessages,
  answerSources,
  expandedSourceKeys,
  retrievalQuestion,
  retrievalStatus,
  retrievalMessage,
  retrievalResults,
  retrievalMetadata,
  canAsk,
  canSearch,
  conversationRef,
  onTopKChange,
  onQuestionChange,
  onChatSubmit,
  onRetrievalQuestionChange,
  onRetrievalSubmit,
  onToggleSource,
}: ChatPanelProps) {
  return (
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
            onChange={(event) => onTopKChange(Number(event.currentTarget.value))}
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
              className={message.role === 'user' ? 'message user-message' : 'message assistant-message'}
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

      <RetrievalPanel
        canSearch={canSearch}
        onRetrievalQuestionChange={onRetrievalQuestionChange}
        onSubmit={onRetrievalSubmit}
        retrievalMessage={retrievalMessage}
        retrievalMetadata={retrievalMetadata}
        retrievalQuestion={retrievalQuestion}
        retrievalResults={retrievalResults}
        retrievalStatus={retrievalStatus}
      />

      <SourcesPanel
        answerSources={answerSources}
        expandedSourceKeys={expandedSourceKeys}
        onToggleSource={onToggleSource}
      />

      <form className="chat-input" aria-label="提出问题" onSubmit={onChatSubmit}>
        <label htmlFor="question">问题</label>
        <div className="input-row">
          <input
            id="question"
            onChange={(event) => onQuestionChange(event.currentTarget.value)}
            placeholder="输入一个基于已上传文档的问题"
            type="text"
            value={question}
          />
          <button disabled={!canAsk} type="submit">
            {chatStatus === 'loading' ? '生成中' : '提问'}
          </button>
        </div>
      </form>
    </section>
  )
}
