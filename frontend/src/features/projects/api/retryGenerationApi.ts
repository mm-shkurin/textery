import { send } from '../../../shared/api/send'
import type { TextStyle } from '../../../shared/textStyles'

/**
 * What a user re-chooses at the moment of a retry.
 *
 * An object rather than two more positional parameters: `retryGeneration(id, key, style, volume)`
 * reads the same at every call site whether or not the last two are the right way round, and the
 * next override added makes that worse. It is the lesson `GenerationParameters` records for the
 * composer, applied before this signature grows a third field rather than after.
 *
 * Every field optional, and an omitted field means «keep what the failed run used» — never
 * «clear it». Neither the register nor the length has an empty state a user would ask for.
 */
export interface RetryOverrides {
  textStyle?: TextStyle
  volumePages?: number
}

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
 * The body carries at most the two fields in `RetryOverrides` — «перегенерировать в другом стиле»
 * and «изменить объём». Every other parameter is copied from the stored source row, so a client
 * cannot bind an owner, a status or a document link even by accident.
 *
 * A field the caller did not name is OMITTED from the body rather than sent as null: an explicit
 * null is a client saying "clear this", which would silently strip the register off a generation
 * that had one. A plain «Повторить» therefore sends no body at all, exactly as before these
 * overrides existed.
 */
export async function retryGeneration(
  generationId: string,
  idempotencyKey: string,
  overrides: RetryOverrides = {},
): Promise<RetryResponse> {
  const body: Record<string, unknown> = {}
  if (overrides.textStyle) body.text_style = overrides.textStyle
  // `!== undefined`, not truthiness: 0 is not a length this picker can produce, but a truthiness
  // test here is the kind that starts dropping a legitimate value the day the range changes.
  if (overrides.volumePages !== undefined) body.volume_pages = overrides.volumePages

  return await send<RetryResponse>(
    `/api/v1/generations/${generationId}/retry`,
    {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      ...(Object.keys(body).length > 0 ? { body } : {}),
    },
    RETRY_FAILURE_FALLBACK,
  )
}
