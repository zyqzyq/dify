'use client'

import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { useToastContext } from '@/app/components/base/toast'
import { useAppContext } from '@/context/app-context'
import { updateWorkspaceSettings } from '@/service/common'

const UsageLimitsPage = () => {
  const { t } = useTranslation()
  const { notify } = useToastContext()
  const {
    currentWorkspace,
    isCurrentWorkspaceManager,
    isValidatingCurrentWorkspace,
    mutateCurrentWorkspace,
  } = useAppContext()
  const initialMaxActiveRequests = useMemo(
    () => String(currentWorkspace.max_active_requests ?? 0),
    [currentWorkspace.max_active_requests],
  )
  const [maxActiveRequests, setMaxActiveRequests] = useState(initialMaxActiveRequests)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    // eslint-disable-next-line react-hooks-extra/no-direct-set-state-in-use-effect
    setMaxActiveRequests(initialMaxActiveRequests)
  }, [initialMaxActiveRequests])

  const normalizedValue = maxActiveRequests.trim()
  const parsedValue = normalizedValue === '' ? Number.NaN : Number(normalizedValue)
  const isValidValue = Number.isInteger(parsedValue) && parsedValue >= 0
  const hasChanges = normalizedValue !== initialMaxActiveRequests
  const canSave = isCurrentWorkspaceManager && isValidValue && hasChanges && !isSaving && !isValidatingCurrentWorkspace

  const handleSave = async () => {
    if (!canSave)
      return

    try {
      setIsSaving(true)
      await updateWorkspaceSettings({
        name: currentWorkspace.name,
        max_active_requests: parsedValue,
      })
      notify({ type: 'success', message: t('actionMsg.modifiedSuccessfully', { ns: 'common' }) })
      mutateCurrentWorkspace()
    }
    catch {
      notify({ type: 'error', message: t('actionMsg.modifiedUnsuccessfully', { ns: 'common' }) })
    }
    finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-[640px]">
      <div className="mb-6">
        <div className="system-md-semibold text-text-primary">
          {t('usageLimits.requestConcurrency.title', { ns: 'common' })}
        </div>
        <div className="system-sm-regular mt-1 text-text-tertiary">
          {t('usageLimits.requestConcurrency.description', { ns: 'common' })}
        </div>
      </div>

      <div className="mb-2 text-sm font-medium leading-5 text-text-primary">
        {t('usageLimits.maxActiveRequests.label', { ns: 'common' })}
      </div>
      <Input
        type="number"
        min={0}
        step={1}
        value={maxActiveRequests}
        disabled={!isCurrentWorkspaceManager || isSaving}
        destructive={normalizedValue !== '' && !isValidValue}
        placeholder={t('usageLimits.maxActiveRequests.placeholder', { ns: 'common' })}
        wrapperClassName="max-w-[280px]"
        onChange={e => setMaxActiveRequests(e.target.value)}
      />
      <div className="body-xs-regular mt-2 text-text-tertiary">
        {t('usageLimits.maxActiveRequests.tip', { ns: 'common' })}
      </div>

      <div className="mt-6 flex justify-end">
        <Button
          size="large"
          variant="primary"
          disabled={!canSave}
          loading={isSaving}
          onClick={handleSave}
        >
          {t('operation.save', { ns: 'common' })}
        </Button>
      </div>
    </div>
  )
}

export default UsageLimitsPage
