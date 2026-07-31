import type { ReactElement } from 'react'
import type { FormRefObject, FormSchema } from '@/app/components/base/form/types'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FormTypeEnum } from '@/app/components/base/form/types'
import BaseForm from './base-form'

const createNumberSchema = (overrides?: Partial<FormSchema>): FormSchema => ({
  name: 'count',
  label: 'Count',
  type: FormTypeEnum.textNumber,
  required: false,
  min: 1,
  max: 10,
  ...overrides,
})

const renderWithQueryClient = (ui: ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  )
}

describe('BaseForm number input', () => {
  it('should apply min and max attributes from form schema', () => {
    renderWithQueryClient(
      <BaseForm
        formSchemas={[createNumberSchema()]}
        defaultValues={{ count: 5 }}
      />,
    )

    const input = screen.getByRole('spinbutton')
    expect(input).toHaveAttribute('min', '1')
    expect(input).toHaveAttribute('max', '10')
  })

  it('should ignore number changes outside schema min and max', async () => {
    const onChange = vi.fn()
    let formRef: FormRefObject | null = null

    renderWithQueryClient(
      <BaseForm
        ref={(ref) => {
          formRef = ref
        }}
        formSchemas={[createNumberSchema()]}
        defaultValues={{ count: 5 }}
        onChange={onChange}
      />,
    )

    const input = screen.getByRole('spinbutton')
    fireEvent.change(input, { target: { value: '11' } })
    expect(onChange).not.toHaveBeenCalled()
    await waitFor(() => {
      expect(formRef?.getFormValues({ needCheckValidatedValues: false }).values.count).toBe(5)
    })

    fireEvent.change(input, { target: { value: '7' } })
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('count', '7')
      expect(formRef?.getFormValues({ needCheckValidatedValues: false }).values.count).toBe('7')
    })
  })
})
