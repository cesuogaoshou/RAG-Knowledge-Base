import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import App from './App'

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
})
