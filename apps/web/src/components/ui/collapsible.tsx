import * as React from 'react'

function Collapsible({
  open,
  onOpenChange,
  children,
  className,
}: {
  open: boolean
  onOpenChange: (next: boolean) => void
  children: React.ReactNode
  className?: string
}) {
  return (
    <div data-slot="collapsible" data-state={open ? 'open' : 'closed'} className={className}>
      {React.Children.map(children, (child) =>
        React.isValidElement(child) ? React.cloneElement(child, { open, onOpenChange } as never) : child,
      )}
    </div>
  )
}

function CollapsibleTrigger({
  children,
  className,
  open,
  onOpenChange,
}: {
  children: React.ReactNode
  className?: string
  open?: boolean
  onOpenChange?: (next: boolean) => void
}) {
  return (
    <button type="button" className={className} onClick={() => onOpenChange?.(!open)} aria-expanded={open}>
      {children}
    </button>
  )
}

function CollapsibleContent({
  children,
  className,
  open,
}: {
  children: React.ReactNode
  className?: string
  open?: boolean
}) {
  if (!open) return null
  return <div className={className}>{children}</div>
}

export { Collapsible, CollapsibleContent, CollapsibleTrigger }
