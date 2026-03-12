## ADDED Requirements

### Requirement: ActionButton primitive
The system SHALL provide an `ActionButton` component in `frontend/components/ui/ActionButton.tsx` accepting props: `label: string`, `onClick: () => void`, `disabled?: boolean`, `isPending?: boolean`, `variant?: 'primary' | 'secondary' | 'danger'`, `style?: CSSProperties`. Default variant is `primary`.

#### Scenario: Renders with label
- **WHEN** `<ActionButton label="Approve" onClick={fn} />` is rendered
- **THEN** a button with text "Approve" is visible

#### Scenario: Disabled state
- **WHEN** `disabled={true}` is passed
- **THEN** the button SHALL be non-interactive and visually dimmed

#### Scenario: Pending state
- **WHEN** `isPending={true}` is passed
- **THEN** the button SHALL show a loading indicator and be non-interactive

### Requirement: SectionCard primitive
The system SHALL provide a `SectionCard` component accepting props: `title: string | ReactNode`, `description?: string`, `children: ReactNode`, `headerExtra?: ReactNode`, `style?: CSSProperties`.

#### Scenario: Renders title and children
- **WHEN** `<SectionCard title="Claims" />` is rendered with children
- **THEN** the title and children are visible within a styled card container

### Requirement: StatusBadge primitive
The system SHALL provide a `StatusBadge` component accepting props: `status: string`, `variant?: 'pending' | 'success' | 'warning' | 'error' | 'auto'`, `style?: CSSProperties`. When `variant='auto'`, the component SHALL infer variant from status string (e.g., "approved" → success, "failed" → error, "draft" → pending).

#### Scenario: Auto variant inference
- **WHEN** `<StatusBadge status="approved" variant="auto" />` is rendered
- **THEN** the badge SHALL display with success styling (green tones)

### Requirement: EmptyState primitive
The system SHALL provide an `EmptyState` component accepting props: `text: string`, `icon?: ReactNode`, `style?: CSSProperties`.

#### Scenario: Renders empty state text
- **WHEN** a list has no items and `<EmptyState text="No claims yet" />` is rendered
- **THEN** the text is visible in a centered, muted style

### Requirement: ConfirmDialog primitive
The system SHALL provide a `ConfirmDialog` component accepting props: `isOpen: boolean`, `title: string`, `message: string`, `onConfirm: () => void`, `onCancel: () => void`, `isPending?: boolean`, `confirmLabel?: string`. The dialog SHALL render as a portal overlay.

#### Scenario: Renders when open
- **WHEN** `isOpen={true}` is passed
- **THEN** a modal overlay with title, message, confirm and cancel buttons is visible

#### Scenario: Hidden when closed
- **WHEN** `isOpen={false}` is passed
- **THEN** no overlay is rendered in the DOM

#### Scenario: Confirm triggers callback
- **WHEN** user clicks the confirm button
- **THEN** `onConfirm` is called
