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
          },
        ])
      }

      throw new Error(`Unexpected request: ${url}`)
    })

    render(<App />)

    expect(await screen.findByText('uploaded-notes.md')).toBeTruthy()
    expect(screen.getByText('4 个片段 · 2026-07-24 10:20:00')).toBeTruthy()
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

    expect(await screen.findByText('上传完成：rag-guide.txt')).toBeTruthy()
    expect(await screen.findByText('rag-guide.txt')).toBeTruthy()
    expect(screen.getByText('2 个片段 · 2026-07-24 10:22:00')).toBeTruthy()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/documents/upload'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
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
    expect(appCss).toContain('grid-template-rows: auto auto minmax(0, 1fr);')
    expect(appCss).toContain('grid-template-rows: auto minmax(0, 1fr) minmax(118px, 0.36fr) auto;')
    expect(appCss).toContain('.chat-panel > .panel-heading')
    expect(appCss).not.toMatch(/\.conversation\s*{[^}]*align-content:\s*end;/s)
  })
})
