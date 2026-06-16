import type { ICurrentWorkspace } from '@/models/common'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastContext } from '@/app/components/base/toast'
import { useAppContext } from '@/context/app-context'
import { updateWorkspaceSettings } from '@/service/common'
import UsageLimitsPage from './index'

vi.mock('@/context/app-context', () => ({
  useAppContext: vi.fn(),
}))

vi.mock('@/service/common', () => ({
  updateWorkspaceSettings: vi.fn(),
}))

const mockUseAppContext = vi.mocked(useAppContext)
const mockUpdateWorkspaceSettings = vi.mocked(updateWorkspaceSettings)
const mockNotify = vi.fn()
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
  return render(
    <ToastContext.Provider value={{ notify: mockNotify, close: vi.fn() }}>
      <UsageLimitsPage />
    </ToastContext.Provider>,
  )
}

describe('UsageLimitsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUpdateWorkspaceSettings.mockResolvedValue({
      result: 'success',
      tenant: createWorkspace(),
    })
    mockUseAppContext.mockReturnValue({
      currentWorkspace: createWorkspace(),
      isCurrentWorkspaceManager: true,
      isValidatingCurrentWorkspace: false,
      mutateCurrentWorkspace: mockMutateCurrentWorkspace,
    } as unknown as ReturnType<typeof useAppContext>)
  })

  describe('Rendering', () => {
    it('should render the current workspace active request limit', () => {
      renderUsageLimitsPage()

      expect(screen.getByText('common.usageLimits.requestConcurrency.title')).toBeInTheDocument()
      expect(screen.getByDisplayValue('5')).toBeInTheDocument()
    })
  })

  describe('Permissions', () => {
    it('should disable editing when the current user cannot manage the workspace', () => {
      mockUseAppContext.mockReturnValue({
        currentWorkspace: createWorkspace({ role: 'normal' }),
        isCurrentWorkspaceManager: false,
        isValidatingCurrentWorkspace: false,
        mutateCurrentWorkspace: mockMutateCurrentWorkspace,
      } as unknown as ReturnType<typeof useAppContext>)

      renderUsageLimitsPage()

      expect(screen.getByDisplayValue('5')).toBeDisabled()
      expect(screen.getByRole('button', { name: 'common.operation.save' })).toBeDisabled()
    })
  })

  describe('Saving', () => {
    it('should save max active requests with the current workspace name', async () => {
      renderUsageLimitsPage()

      fireEvent.change(screen.getByDisplayValue('5'), { target: { value: '12' } })
      fireEvent.click(screen.getByRole('button', { name: 'common.operation.save' }))

      await waitFor(() => {
        expect(mockUpdateWorkspaceSettings).toHaveBeenCalledWith({
          name: 'Test Workspace',
          max_active_requests: 12,
        })
      })
      expect(mockMutateCurrentWorkspace).toHaveBeenCalled()
      expect(mockNotify).toHaveBeenCalledWith({
        type: 'success',
        message: 'common.actionMsg.modifiedSuccessfully',
      })
    })

    it('should reject negative values before saving', () => {
      renderUsageLimitsPage()

      fireEvent.change(screen.getByDisplayValue('5'), { target: { value: '-1' } })

      expect(screen.getByRole('button', { name: 'common.operation.save' })).toBeDisabled()
      expect(mockUpdateWorkspaceSettings).not.toHaveBeenCalled()
    })
  })
})
