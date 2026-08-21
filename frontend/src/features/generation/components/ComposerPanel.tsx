import { useCallback, useState } from 'react'
import { Composer, MAX_TOPIC_LENGTH } from './Composer'
import { EMPTY_PARAMETERS, type GenerationParameters } from '../utils/generationParameters'
import type { DocumentType } from '../../../shared/domain/documentTypes'

interface ComposerPanelProps {
  topicLabel: string
  documentType: DocumentType
  onSubmit: (topic: string, parameters: GenerationParameters) => void
}

/**
 * The draft — what the user has typed but not yet sent — and the composer that edits it.
 *
 * The jury's remark: every character typed into the topic field changed state in the workspace
 * container and repainted it and all of its children. The draft belonged to a component that also
 * renders the document area, the header and the status badge, so the cheapest possible event in
 * the app — one keystroke — was also one of the most expensive renders.
 *
 * Owning the draft here draws the re-render boundary around the two fields that actually change.
 * The workspace above learns about the draft exactly once, when it is sent.
 */
export function ComposerPanel({ topicLabel, documentType, onSubmit }: ComposerPanelProps) {
  const [topic, setTopic] = useState('')
  const [parameters, setParameters] = useState<GenerationParameters>(EMPTY_PARAMETERS)

  const send = useCallback(() => {
    // Trimmed and capped here rather than in the parent: this is where the raw input lives, and
    // the parent should never see a value the composer would not have allowed.
    const trimmed = topic.trim().slice(0, MAX_TOPIC_LENGTH)
    if (trimmed) onSubmit(trimmed, parameters)
  }, [topic, parameters, onSubmit])

  return (
    <Composer
      topicLabel={topicLabel}
      documentType={documentType}
      topic={topic}
      parameters={parameters}
      setParameters={setParameters}
      setTopic={setTopic}
      onSend={send}
    />
  )
}
