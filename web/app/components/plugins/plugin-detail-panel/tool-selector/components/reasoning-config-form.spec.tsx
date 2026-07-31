import type { ReasoningConfigValue } from '../utils/show-on'
import type { ToolFormSchema } from '@/app/components/tools/utils/to-form-schema'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { FormTypeEnum } from '@/app/components/header/account-setting/model-provider-page/declarations'
import { VarType as VarKindType } from '@/app/components/workflow/nodes/tool/types'
import ReasoningConfigForm from './reasoning-config-form'

function reasoningSchema(overrides: Partial<ToolFormSchema>): ToolFormSchema {
  return {
    name: overrides.variable ?? 'field',
    variable: 'field',
    label: { en_US: 'Label', zh_Hans: 'Label' },
    human_description: { en_US: '', zh_Hans: '' },
    type: FormTypeEnum.checkbox,
    _type: 'boolean',
    form: 'llm',
    required: false,
    llm_description: '',
    multiple: false,
    default: 'false',
    show_on: [],
    ...overrides,
  } as ToolFormSchema
}

describe('ReasoningConfigForm show_on visibility', () => {
  it('should apply min and max to llm number parameters and ignore out-of-range changes', () => {
    const onChange = vi.fn()
    const countSchema = reasoningSchema({
      variable: 'count',
      name: 'count',
      label: { en_US: 'COUNT_ROW', zh_Hans: 'COUNT_ROW' },
      type: FormTypeEnum.textNumber,
      _type: 'number',
      default: '5',
      min: 1,
      max: 10,
    })
    const value: ReasoningConfigValue = {
      count: { auto: 0, value: { type: VarKindType.constant, value: 5 } },
    }

    render(
      <ReasoningConfigForm
        value={value}
        onChange={onChange}
        schemas={[countSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    const input = screen.getByRole('spinbutton')
    expect(input).toHaveAttribute('min', '1')
    expect(input).toHaveAttribute('max', '10')

    fireEvent.change(input, { target: { value: '11' } })
    expect(onChange).not.toHaveBeenCalled()

    fireEvent.change(input, { target: { value: '7' } })
    expect(onChange).toHaveBeenCalledWith({
      count: { auto: 0, value: { type: VarKindType.constant, value: '7' } },
    })
  })

  it('should omit dependent parameter rows until sibling conditions match', () => {
    const modeSchema = reasoningSchema({
      variable: 'mode',
      name: 'mode',
      label: { en_US: 'MODE_ROW', zh_Hans: 'MODE_ROW' },
      default: 'false',
    })
    const extraSchema = reasoningSchema({
      variable: 'extra',
      name: 'extra',
      label: { en_US: 'EXTRA_ROW', zh_Hans: 'EXTRA_ROW' },
      default: 'fallback',
      show_on: [{ variable: 'mode', value: 'true' }],
    })

    const hiddenValue: ReasoningConfigValue = {
      mode: { auto: 0, value: { type: VarKindType.constant, value: false } },
      extra: { auto: 0, value: { type: VarKindType.constant, value: 'should-hide' } },
    }

    const { rerender } = render(
      <ReasoningConfigForm
        value={hiddenValue}
        onChange={vi.fn()}
        schemas={[modeSchema, extraSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    expect(screen.queryByText('EXTRA_ROW')).toBeNull()

    rerender(
      <ReasoningConfigForm
        value={{
          mode: { auto: 0, value: { type: VarKindType.constant, value: true } },
          extra: hiddenValue.extra,
        }}
        onChange={vi.fn()}
        schemas={[modeSchema, extraSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    expect(screen.getByText('EXTRA_ROW')).toBeInTheDocument()
  })

  it('should reset dependent parameter when reset_on_change sibling changes while row stays visible', async () => {
    const onChange = vi.fn()
    const modeSchema = reasoningSchema({
      variable: 'mode',
      name: 'mode',
      label: { en_US: 'MODE_ROW', zh_Hans: 'MODE_ROW' },
      default: 'false',
    })
    const extraSchema = reasoningSchema({
      variable: 'extra',
      name: 'extra',
      label: { en_US: 'EXTRA_ROW', zh_Hans: 'EXTRA_ROW' },
      default: 'true',
      reset_on_change: ['mode'],
    })
    const initialValue: ReasoningConfigValue = {
      mode: { auto: 0, value: { type: VarKindType.constant, value: false } },
      extra: { auto: 0, value: { type: VarKindType.constant, value: false } },
    }

    const { rerender } = render(
      <ReasoningConfigForm
        value={initialValue}
        onChange={onChange}
        schemas={[modeSchema, extraSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    rerender(
      <ReasoningConfigForm
        value={{
          mode: { auto: 0, value: { type: VarKindType.constant, value: true } },
          extra: initialValue.extra,
        }}
        onChange={onChange}
        schemas={[modeSchema, extraSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    await waitFor(() => {
      expect(onChange).toHaveBeenCalled()
    })
    const patched = onChange.mock.calls.at(-1)?.[0] as ReasoningConfigValue
    expect(patched.extra).toEqual({
      auto: 0,
      value: {
        type: VarKindType.constant,
        value: true,
      },
    })
  })

  it('should clear dynamic-tree-select values when reset_on_change sibling changes', async () => {
    const onChange = vi.fn()
    const categorySchema = reasoningSchema({
      variable: 'category',
      name: 'category',
      label: { en_US: 'CATEGORY_ROW', zh_Hans: 'CATEGORY_ROW' },
      default: 'false',
    })
    const channelSchema = reasoningSchema({
      variable: 'channel',
      name: 'channel',
      type: FormTypeEnum.dynamicTreeSelect,
      _type: 'dynamic-tree-select',
      label: { en_US: 'CHANNEL_ROW', zh_Hans: 'CHANNEL_ROW' },
      default: undefined,
      reset_on_change: ['category'],
    })
    const initialValue: ReasoningConfigValue = {
      category: { auto: 0, value: { type: VarKindType.constant, value: false } },
      channel: { auto: 0, value: { type: VarKindType.constant, value: ['old-channel'] } },
    }

    const { rerender } = render(
      <ReasoningConfigForm
        value={initialValue}
        onChange={onChange}
        schemas={[categorySchema, channelSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    rerender(
      <ReasoningConfigForm
        value={{
          category: { auto: 0, value: { type: VarKindType.constant, value: true } },
          channel: initialValue.channel,
        }}
        onChange={onChange}
        schemas={[categorySchema, channelSchema]}
        nodeOutputVars={[]}
        availableNodes={[]}
        nodeId="node-1"
      />,
    )

    await waitFor(() => {
      expect(onChange).toHaveBeenCalled()
    })
    const patched = onChange.mock.calls.at(-1)?.[0] as ReasoningConfigValue
    expect(patched.channel).toEqual({
      auto: 0,
      value: {
        type: VarKindType.constant,
        value: [],
      },
    })
  })
})
