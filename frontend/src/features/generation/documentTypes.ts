export type DocumentType = 'doklad' | 'essay' | 'sochinenie' | 'referat'

export interface DocumentTypeOption {
  id: DocumentType
  name: string
  available: boolean
}

export const DOCUMENT_TYPES: DocumentTypeOption[] = [
  { id: 'doklad', name: 'Доклад', available: true },
  { id: 'essay', name: 'Эссе', available: false },
  { id: 'sochinenie', name: 'Сочинение', available: false },
  { id: 'referat', name: 'Реферат', available: false },
]

export const DEFAULT_DOCUMENT_TYPE: DocumentType = 'doklad'
