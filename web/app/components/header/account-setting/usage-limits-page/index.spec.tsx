import type { ICurrentWorkspace } from '@/models/common'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAppContext } from '@/context/app-context'
import UsageLimitsPage from './index'

vi.mock('@/context/app-context', () => ({
  useAppContext: vi.fn(),
}))

const mockUseAppContext = vi.mocked(useAppContext)
const mockMutateCurrentWorkspace = vi.fn()

const createWorkspace = (overrides: Partial<ICurrentWorkspace> = {}): ICurrentWorkspace => ({
  id: 'workspace-id',
  name: 'Test Workspace',
  plan: 'basic',
  status: 'normal',
  created_at: 0,
  role: 'owner',
  providers: [],
  trial_credits: 0,
  trial_credits_used: 0,
  next_credit_reset_date: 0,
  max_active_requests: 5,
  ...overrides,
})

const renderUsageLimitsPage = () => {
  return render(<UsageLimitsPage />)
}

describe('UsageLimitsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAppContext.mockReturnValue({
      currentWorkspace: createWorkspace(),
      isCurrentWorkspaceManager: true,
      isValidatingCurrentWorkspace: false,
      mutateCurrentWorkspace: mockMutateCurrentWorkspace,
    } as unknown as ReturnType<typeof useAppContext>)
  })

  // Covers the static usage limit information shown on the page.
  describe('Rendering', () => {
    it('should render the current workspace active request limit as read-only', () => {
      renderUsageLimitsPage()

      expect(screen.getByText('common.usageLimits.requestConcurrency.title')).toBeInTheDocument()
      expect(screen.getByDisplayValue('5')).toBeDisabled()
      expect(screen.queryByRole('button', { name: 'common.operation.save' })).not.toBeInTheDocument()
    })
  })

  // Ensures permissions no longer reveal an editing path on this page.
  describe('Permissions', () => {
    it('should keep the active request limit read-only when the current user can manage the workspace', () => {
      renderUsageLimitsPage()

      expect(screen.getByDisplayValue('5')).toBeDisabled()
      expect(screen.queryByRole('button', { name: 'common.operation.save' })).not.toBeInTheDocument()
    })

    it('should keep the active request limit read-only when the current user cannot manage the workspace', () => {
      mockUseAppContext.mockReturnValue({
        currentWorkspace: createWorkspace({ role: 'normal' }),
        isCurrentWorkspaceManager: false,
        isValidatingCurrentWorkspace: false,
        mutateCurrentWorkspace: mockMutateCurrentWorkspace,
      } as unknown as ReturnType<typeof useAppContext>)

      renderUsageLimitsPage()

      expect(screen.getByDisplayValue('5')).toBeDisabled()
      expect(screen.queryByRole('button', { name: 'common.operation.save' })).not.toBeInTheDocument()
    })
  })

  // Validates display fallback for unset backend values.
  describe('Edge Cases', () => {
    it('should display zero when the workspace active request limit is unset', () => {
      mockUseAppContext.mockReturnValue({
        currentWorkspace: createWorkspace({ max_active_requests: null }),
        isCurrentWorkspaceManager: true,
        isValidatingCurrentWorkspace: false,
        mutateCurrentWorkspace: mockMutateCurrentWorkspace,
      } as unknown as ReturnType<typeof useAppContext>)

      renderUsageLimitsPage()

      expect(screen.getByDisplayValue('0')).toBeDisabled()
      expect(screen.queryByRole('button', { name: 'common.operation.save' })).not.toBeInTheDocument()
    })
  })
})
