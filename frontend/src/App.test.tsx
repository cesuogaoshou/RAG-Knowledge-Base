/// <reference types="node" />

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import App from './App'

const appCss = readFileSync(resolve('src/App.css'), 'utf8')

const makeJsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  })

describe('App document workflow', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  test('loads and renders documents from the backend', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([
          {
            id: 'doc-1',
            filename: 'uploaded-notes.md',
            type: 'md',
            created_at: '2026-07-24 10:20:00',
            chunk_count: 4,
            status: 'indexed',
          },
        ])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('uploaded-notes.md')).toBeTruthy()
    expect(screen.getByText('4 个片段 · 2026-07-24 10:20:00')).toBeTruthy()
    expect(screen.getByText('已索引')).toBeTruthy()
  })

  test('uploads a selected document and refreshes the document list', async () => {
    let uploadFinished = false
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents/upload') && init?.method === 'POST') {
        uploadFinished = true
        return makeJsonResponse({
          id: 'doc-2',
          filename: 'rag-guide.txt',
          type: 'txt',
          created_at: '2026-07-24 10:22:00',
          saved_path: 'backend/data/uploads/rag-guide.txt',
          text_length: 120,
          page_count: 1,
          chunk_count: 2,
          status: 'uploaded',
          pages: [{ page: 1, text: 'RAG guide' }],
        })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse(
          uploadFinished
            ? [
                {
                  id: 'doc-2',
                  filename: 'rag-guide.txt',
                  type: 'txt',
                  created_at: '2026-07-24 10:22:00',
                  chunk_count: 2,
                  status: 'indexed',
                },
              ]
            : [],
        )
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    const fileInput = screen.getByLabelText('选择文档文件')
    await userEvent.upload(
      fileInput,
      new File(['RAG guide'], 'rag-guide.txt', { type: 'text/plain' }),
    )

    expect(await screen.findByText('上传已接收：rag-guide.txt')).toBeTruthy()
    expect(await screen.findByText('rag-guide.txt')).toBeTruthy()
    expect(screen.getByText('2 个片段 · 2026-07-24 10:22:00')).toBeTruthy()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/documents/upload'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  test('refreshes uploaded documents until they become indexed', async () => {
    let listCalls = 0
    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        listCalls += 1
        return makeJsonResponse([
          {
            id: 'doc-async',
            filename: 'async-notes.txt',
            type: 'txt',
            created_at: '2026-08-04T10:00:00Z',
            chunk_count: listCalls >= 2 ? 3 : 0,
            status: listCalls >= 2 ? 'indexed' : 'uploaded',
          },
        ])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('已上传')).toBeTruthy()
    expect(screen.getByText('文档处理中，完成后会自动刷新索引状态。')).toBeTruthy()
    expect(await screen.findByText('已索引', undefined, { timeout: 3500 })).toBeTruthy()
  }, 8000)

  test('deletes a document and refreshes the document list', async () => {
    let deleted = false
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents/doc-2') && init?.method === 'DELETE') {
        deleted = true
        return makeJsonResponse({ id: 'doc-2', deleted: true })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse(
          deleted
            ? []
            : [
                {
                  id: 'doc-2',
                  filename: 'rag-guide.txt',
                  type: 'txt',
                  created_at: '2026-07-24 10:22:00',
                  chunk_count: 2,
                },
              ],
        )
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('rag-guide.txt')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: '删除 rag-guide.txt' }))

    expect(await screen.findByText('还没有上传文档')).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/documents/doc-2'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  test('shows a delete error and keeps the document when deletion fails', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents/doc-2') && init?.method === 'DELETE') {
        return makeJsonResponse({ detail: 'Document not found.' }, 404)
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([
          {
            id: 'doc-2',
            filename: 'rag-guide.txt',
            type: 'txt',
            created_at: '2026-07-24 10:22:00',
            chunk_count: 2,
          },
        ])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('rag-guide.txt')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: '删除 rag-guide.txt' }))

    expect(await screen.findByText('Document not found.')).toBeTruthy()
    expect(screen.getByText('rag-guide.txt')).toBeTruthy()
  })

  test('shows an upload error when the backend rejects the selected file', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents/upload') && init?.method === 'POST') {
        return makeJsonResponse({ detail: '仅支持 PDF、TXT 或 Markdown 文件' }, 400)
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    const fileInput = screen.getByLabelText('选择文档文件')
    await userEvent.upload(
      fileInput,
      new File(['bad file'], 'bad-upload.txt', { type: 'text/plain' }),
    )

    expect(await screen.findByText('仅支持 PDF、TXT 或 Markdown 文件')).toBeTruthy()
    expect(screen.getByText('还没有上传文档')).toBeTruthy()
  })
})

describe('App chat workflow', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  test('submits a question with the selected Top-K and renders the answer with sources', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([
          {
            id: 'doc-1',
            filename: 'rag-notes.md',
            type: 'md',
            created_at: '2026-07-24 10:20:00',
            chunk_count: 4,
          },
        ])
      }

      if (url.endsWith('/api/chat') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({
          question: 'RAG 的回答来源如何展示？',
          top_k: 5,
        })

        return makeJsonResponse({
          answer: '前端会展示模型回答，并在下方列出检索命中的来源片段。',
          sources: [
            {
              filename: 'rag-notes.md',
              page: 2,
              chunk_index: 3,
              content: '回答来源来自后端返回的 sources 数组。',
              score: 0.8123,
            },
            {
              filename: 'rag-notes.md',
              page: 2,
              chunk_index: 3,
              content: '后端可能返回重复 chunk，前端仍应稳定渲染。',
              score: 0.8123,
            },
          ],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    await userEvent.selectOptions(screen.getByLabelText('Top-K 来源数量'), '5')
    await userEvent.type(screen.getByLabelText('问题'), 'RAG 的回答来源如何展示？')
    await userEvent.click(screen.getByRole('button', { name: '提问' }))

    expect(await screen.findByText('前端会展示模型回答，并在下方列出检索命中的来源片段。')).toBeTruthy()
    expect(screen.getAllByText('rag-notes.md').length).toBeGreaterThan(0)
    expect(screen.getAllByText('第 2 页 · 相似度 0.812')).toHaveLength(2)
    expect(screen.getByText('回答来源来自后端返回的 sources 数组。')).toBeTruthy()
    expect(screen.getByText('后端可能返回重复 chunk，前端仍应稳定渲染。')).toBeTruthy()
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('Encountered two children with the same key'),
      expect.anything(),
    )

    consoleErrorSpy.mockRestore()
  })

  test('streams a chat answer and renders sources when the stream completes', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/chat/stream') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({
          question: 'streaming demo',
          top_k: 3,
        })

        const encoder = new TextEncoder()
        return new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(encoder.encode('event: token\ndata: {"delta":"第一段"}\n\n'))
              controller.enqueue(encoder.encode('event: token\ndata: {"delta":"第二段"}\n\n'))
              controller.enqueue(
                encoder.encode(
                  'event: sources\ndata: {"sources":[{"filename":"rag.md","page":1,"chunk_index":0,"content":"stream source","score":0.91}]}\n\n',
                ),
              )
              controller.enqueue(encoder.encode('event: done\ndata: {}\n\n'))
              controller.close()
            },
          }),
          {
            status: 200,
            headers: {
              'Content-Type': 'text/event-stream',
            },
          },
        )
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith('/api/documents'))).toBe(
        true,
      )
    })

    const questionInput = document.querySelector<HTMLInputElement>('#question')
    expect(questionInput).toBeTruthy()
    await userEvent.type(questionInput as HTMLInputElement, 'streaming demo')

    const submitButton = questionInput
      ?.closest('form')
      ?.querySelector<HTMLButtonElement>('button[type="submit"]')
    expect(submitButton).toBeTruthy()
    await userEvent.click(submitButton as HTMLButtonElement)

    expect(await screen.findByText('第一段第二段')).toBeTruthy()
    expect(screen.getByText('rag.md')).toBeTruthy()
    expect(screen.getByText('stream source')).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/chat/stream'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  test('shows a chat error message when the backend rejects the request', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/chat') && init?.method === 'POST') {
        return makeJsonResponse({ detail: '请先上传文档后再提问' }, 400)
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    await userEvent.type(screen.getByLabelText('问题'), '现在可以提问吗？')
    await userEvent.click(screen.getByRole('button', { name: '提问' }))

    expect(await screen.findByText('请先上传文档后再提问')).toBeTruthy()
  })

  test('renders markdown-heavy source snippets as plain text previews', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/chat') && init?.method === 'POST') {
        return makeJsonResponse({
          answer: 'MEMORY.md 记录项目状态和操作规则。',
          sources: [
            {
              filename: 'MEMORY.md',
              page: 1,
              chunk_index: 0,
              content: '# Project Memory\n\n- **Operating Rules**: update `AGENTS.md` after changes.',
              score: 0.8123,
            },
          ],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    await userEvent.type(screen.getByLabelText('问题'), 'memory讲了什么')
    await userEvent.click(screen.getByRole('button', { name: '提问' }))

    expect(
      await screen.findByText('Project Memory Operating Rules: update AGENTS.md after changes.'),
    ).toBeTruthy()
    expect(screen.queryByText(/# Project Memory/)).toBeNull()
    expect(screen.queryByText(/\*\*Operating Rules\*\*/)).toBeNull()
    expect(screen.queryByText(/`AGENTS\.md`/)).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: '展开 MEMORY.md 第 1 页 Chunk 0' }))

    expect(screen.getByText('Chunk 0 · 第 1 页 · 相似度 0.812')).toBeTruthy()
    expect(screen.getByText(/# Project Memory/)).toBeTruthy()
    expect(screen.getByText(/\*\*Operating Rules\*\*/)).toBeTruthy()
    expect(screen.getByText(/`AGENTS\.md`/)).toBeTruthy()
  })

  test('runs a retrieval debug search and renders chunk details', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([
          {
            id: 'doc-1',
            filename: 'rag-notes.md',
            type: 'md',
            created_at: '2026-07-24 10:20:00',
            chunk_count: 4,
          },
        ])
      }

      if (url.endsWith('/api/search') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({
          question: 'RAG 如何工作？',
          top_k: 5,
        })

        return makeJsonResponse({
          query: 'RAG 如何工作？',
          top_k: 5,
          results: [
            {
              filename: 'rag-notes.md',
              page: 2,
              chunk_index: 3,
              content: '回答前先召回相关片段。',
              score: 0.8123,
            },
          ],
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    await userEvent.selectOptions(screen.getByLabelText('Top-K 来源数量'), '5')
    await userEvent.type(screen.getByLabelText('检索问题'), 'RAG 如何工作？')
    await userEvent.click(screen.getByRole('button', { name: '检索' }))

    expect(await screen.findByText('Chunk 3 · 第 2 页 · 相似度 0.812')).toBeTruthy()
    expect(screen.getAllByText('rag-notes.md').length).toBeGreaterThan(1)
    expect(screen.getByText('回答前先召回相关片段。')).toBeTruthy()
  })

  test('shows a retrieval debug error when search fails', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/search') && init?.method === 'POST') {
        return makeJsonResponse({ detail: '检索失败，请稍后重试' }, 500)
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('后端已连接')).toBeTruthy()

    await userEvent.type(screen.getByLabelText('检索问题'), 'RAG 如何工作？')
    await userEvent.click(screen.getByRole('button', { name: '检索' }))

    expect(await screen.findByText('检索失败，请稍后重试')).toBeTruthy()
  })
})

describe('App persistence workflow', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  test('renders saved chat sessions and evaluation summaries', async () => {
    vi.mocked(fetch).mockImplementation(async (input) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/chat/sessions')) {
        return makeJsonResponse([
          {
            id: 'session-1',
            title: 'RAG 的回答来源如何展示？',
            created_at: '2026-08-07T10:00:00Z',
            updated_at: '2026-08-07T10:01:00Z',
            message_count: 2,
          },
        ])
      }

      if (url.endsWith('/api/evaluations')) {
        return makeJsonResponse([
          {
            id: 'eval-1',
            created_at: '2026-08-07T10:02:00Z',
            mode: 'baseline',
            case_count: 15,
            source_hit_rate: 1,
            marker_hit_rate: 1,
            refusal_accuracy: 1,
            recommendation: null,
            parameters: { top_k: 3 },
          },
        ])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('最近问答')).toBeTruthy()
    expect(await screen.findByText('RAG 的回答来源如何展示？')).toBeTruthy()
    expect(screen.getByText('2 条消息')).toBeTruthy()
    expect(screen.getByText('评估记录')).toBeTruthy()
    expect(screen.getByText('baseline · 15 cases')).toBeTruthy()
    expect(screen.getAllByText('命中 1.00')).toHaveLength(1)
  })

  test('exports and safely resets local persisted data', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/chat/sessions')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/evaluations')) {
        return makeJsonResponse([])
      }

      if (url.endsWith('/api/admin/export')) {
        return makeJsonResponse({
          documents: [{ id: 'doc-1' }],
          chat_sessions: [{ id: 'session-1' }],
          evaluation_runs: [{ id: 'eval-1' }],
        })
      }

      if (url.endsWith('/api/admin/reset') && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toEqual({
          reset_chat_history: true,
          reset_evaluations: true,
          reset_documents: false,
        })
        return makeJsonResponse({
          reset_chat_history: true,
          reset_evaluations: true,
          reset_documents: false,
        })
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('本地数据')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: '导出数据' }))

    expect(await screen.findByText('已导出：1 个文档，1 个问答，1 次评估')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: '安全清理' }))

    expect(await screen.findByText('已清理问答和评估记录，文档保留')).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/reset'),
      expect.objectContaining({ method: 'POST' }),
    )
  })
})

describe('App layout constraints', () => {
  test('keeps the initial empty conversation aligned to the top', async () => {
    const originalScrollHeight = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'scrollHeight',
    )

    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
      configurable: true,
      get() {
        return this.getAttribute('aria-label') === '问答记录' ? 500 : 0
      },
    })

    vi.stubGlobal('fetch', vi.fn())
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockImplementation(async (input) => {
      const url = String(input)

      if (url.endsWith('/health')) {
        return makeJsonResponse({ status: 'ok', service: 'rag-knowledge-base-api' })
      }

      if (url.endsWith('/api/documents')) {
        return makeJsonResponse([])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    try {
      render(<App />)

      expect(await screen.findByText('后端已连接')).toBeTruthy()
      expect(screen.getByLabelText('问答记录').scrollTop).toBe(0)
    } finally {
      cleanup()
      vi.restoreAllMocks()
      vi.unstubAllGlobals()

      if (originalScrollHeight) {
        Object.defineProperty(HTMLElement.prototype, 'scrollHeight', originalScrollHeight)
      } else {
        delete (HTMLElement.prototype as { scrollHeight?: number }).scrollHeight
      }
    }
  })

  test('keeps the workspace fixed to the viewport with internal scroll regions', () => {
    expect(appCss).toContain('height: 100dvh;')
    expect(appCss).toContain('overflow: hidden;')
    expect(appCss).toContain('grid-template-rows: auto minmax(0, 1fr);')
    expect(appCss).toContain('grid-template-rows: auto auto minmax(0, 1fr) auto;')
    expect(appCss).toContain(
      'grid-template-rows: auto minmax(0, 0.82fr) minmax(150px, 0.32fr) minmax(100px, 0.26fr) auto;',
    )
    expect(appCss).toContain('grid-template-rows: auto auto auto minmax(0, 1fr);')
    expect(appCss).toContain('.chat-panel > .panel-heading')
    expect(appCss).not.toMatch(/\.conversation\s*{[^}]*align-content:\s*end;/s)
  })
})
