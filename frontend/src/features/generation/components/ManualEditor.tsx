interface ManualEditorProps {
  documentTypeLabel: string
}

export function ManualEditor({ documentTypeLabel }: ManualEditorProps) {
  return (
    <div data-testid="manual-editor">
      <div data-testid="editor-breadcrumb">{documentTypeLabel} · Ручной режим</div>
    </div>
  )
}
