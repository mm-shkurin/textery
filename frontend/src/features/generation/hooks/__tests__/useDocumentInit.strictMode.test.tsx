import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import { ManualEditor } from '../../components/ManualEditor'
import * as documentApi from '../../api/documentApi'

vi.mock('../../api/documentApi')

// The guard for defect B's caller half, and the only test that can be.
//
// documentApi's contract tests pin that createDocument FORWARDS the key it is handed. They say
// nothing about where it comes from — so they pass unchanged against a caller that mints a new
// key on every effect run, which is exactly the bug. Making `idempotencyKey` a required
// parameter closes the keyless call site structurally, but nothing stops `crypto.randomUUID()`
// being written inline at the call.
//
// Verified by mutation, not assumed: replacing `idempotencyKeyRef.current` with
// `crypto.randomUUID()` in useDocumentInit passes the ENTIRE suite (190 passed, 0 failures)
// without this file. That is what makes this test load-bearing rather than decorative.
//
// StrictMode is not a contrivance here: main.tsx:7 wraps the real app in it, so the double
// invoke is what every dev mount actually does. useDocumentInit's `cancelled` flag suppresses
// the second run's setState but NOT its fetch, so the POST genuinely fires twice. One key makes
// those a request and its replay (documents_create.yaml's 200 branch); two keys make them two
// documents.
describe('useDocumentInit under StrictMode', () => {
  it('sends one idempotency key for one mount, even though the effect runs twice', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue({
      documentId: 'doc-1',
      status: 'draft',
      version: 7,
    })

    render(
      <StrictMode>
        <ManualEditor documentType="doklad" documentTypeLabel="Доклад" onBack={vi.fn()} />
      </StrictMode>,
    )

    await waitFor(() => {
      expect(documentApi.createDocument).toHaveBeenCalled()
    })

    // Asserted relationally, not as a count: whether React double-invokes depends on the build,
    // so pinning "exactly 2 calls" would make this test about React's dev behaviour rather than
    // about ours. What must hold either way is that EVERY call for this one mount carries the
    // SAME key — true for one call, and the whole point for two.
    const keys = vi.mocked(documentApi.createDocument).mock.calls.map(([, key]) => key)
    expect(new Set(keys).size).toBe(1)
    expect(keys[0]).toBeTruthy()
  })
})
