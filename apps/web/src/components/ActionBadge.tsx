import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export type ActionDirection = 'BUY' | 'SELL' | 'HOLD'

const variantByAction: Record<ActionDirection, 'default' | 'destructive' | 'outline'> = {
  BUY: 'default',
  SELL: 'destructive',
  HOLD: 'outline',
}

export function ActionBadge({
  action,
  className,
  testId,
}: {
  action: ActionDirection
  className?: string
  testId?: string
}) {
  const variant = variantByAction[action]
  return (
    <Badge
      data-action={action}
      data-variant={variant}
      data-testid={testId}
      variant={variant}
      className={cn('font-display tracking-wider', className)}
    >
      {action}
    </Badge>
  )
}
