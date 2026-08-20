import { send } from '../../../shared/api/send'
import type { TextStyle } from '../../../shared/textStyles'

export const RETRY_FAILURE_FALLBACK = 'Не удалось повторить генерацию'

// What the server says when the row is no longer in a state that can be retried — it completed,
// or the sweep is already re-running it. Not an error to apologise for: the feed is simply out of
// date, so the caller refreshes rather than offering the button again.
export const NOT_RETRYABLE_CODE = 'NOT_RETRYABLE'
export const RETRY_LIMIT_CODE = 'RETRY_LIMIT_REACHED'

interface RetryResponse {
  id: string
  status: string
}

/**
 * «Повторить» — re-run a failed generation.
 *
 * The `Idempotency-Key` is minted per CLICK and passed in by the caller rather than generated
 * here: a key created inside this function would be new on every call, so a retry after a lost
 * response would start a second generation — the one thing the header exists to prevent.
 *
 * The body carries at most ONE field, and only for «перегенерировать в другом стиле». Every other
 * parameter is copied from the stored source row, so a client cannot bind an owner, a status or a
 * document link even by accident — the register is the one thing the user genuinely re-chooses at
 * the moment of the retry, which is why it is the one thing the body may name.
 *
 * A plain «Повторить» sends NO body at all rather than `{text_style: null}`: an explicit null is a
 * client saying "clear the style", which would silently strip the register off a generation that
 * had one.
 */
export async function retryGeneration(
  generationId: string,
  idempotencyKey: string,
  textStyle?: TextStyle,
): Promise<RetryResponse> {
  return await send<RetryResponse>(
    `/api/v1/generations/${generationId}/retry`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      ...(textStyle ? { body: { text_style: textStyle } } : {}),
    },
    RETRY_FAILURE_FALLBACK,
  )
}
