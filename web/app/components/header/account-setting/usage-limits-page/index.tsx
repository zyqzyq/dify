'use client'

import { useTranslation } from 'react-i18next'
import Input from '@/app/components/base/input'
import { useAppContext } from '@/context/app-context'

const UsageLimitsPage = () => {
  const { t } = useTranslation()
  const { currentWorkspace } = useAppContext()
  const maxActiveRequests = String(currentWorkspace.max_active_requests ?? 0)

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
        disabled
        placeholder={t('usageLimits.maxActiveRequests.placeholder', { ns: 'common' })}
        wrapperClassName="max-w-[280px]"
      />
      <div className="body-xs-regular mt-2 text-text-tertiary">
        {t('usageLimits.maxActiveRequests.tip', { ns: 'common' })}
      </div>
    </div>
  )
}

export default UsageLimitsPage
