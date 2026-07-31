import type { ToolParameter } from '../types'
import { describe, expect, it } from 'vitest'
import { getDynamicOptionsResetKey, serializeResourceVarInputsForDynamicOptions } from '@/app/components/workflow/nodes/_base/components/form-input-item.helpers'
import { VarKindType } from '@/app/components/workflow/nodes/_base/types'
import { flattenToolSettingStoredEntry, getPlainValue, toolParametersToFormSchemas } from './to-form-schema'

describe('toolParametersToFormSchemas', () => {
  it('should passthrough parameter-level and option-level show_on from plugin definitions', () => {
    const parameters: ToolParameter[] = [
      {
        name: 'mode',
        label: { en_US: 'Mode', zh_Hans: 'Mode' },
        human_description: { en_US: '', zh_Hans: '' },
        type: 'string',
        form: 'llm',
        llm_description: '',
        required: false,
        multiple: false,
        default: '',
      },
      {
        name: 'extra',
        label: { en_US: 'Extra', zh_Hans: 'Extra' },
        human_description: { en_US: '', zh_Hans: '' },
        type: 'string',
        form: 'llm',
        llm_description: '',
        required: false,
        multiple: false,
        default: '',
        show_on: [{ variable: 'mode', value: 'pro' }],
        reset_on_change: ['mode'],
        options: [
          {
            label: { en_US: 'Opt', zh_Hans: 'Opt' },
            value: 'opt-a',
            show_on: [{ variable: 'mode', value: 'pro' }],
          },
        ],
      },
    ]

    const schemas = toolParametersToFormSchemas(parameters)
    expect(schemas[0].show_on).toEqual([])
    expect(schemas[1].show_on).toEqual([{ variable: 'mode', value: 'pro' }])
    expect(schemas[1].reset_on_change).toEqual(['mode'])
    expect(schemas[1].options?.[0].show_on).toEqual([{ variable: 'mode', value: 'pro' }])
  })

  it('should normalize missing show_on and reset_on_change to empty arrays', () => {
    const parameters: ToolParameter[] = [
      {
        name: 'only',
        label: { en_US: 'Only', zh_Hans: 'Only' },
        human_description: { en_US: '', zh_Hans: '' },
        type: 'string',
        form: 'llm',
        llm_description: '',
        required: false,
        multiple: false,
        default: '',
        options: [{ label: { en_US: 'A', zh_Hans: 'A' }, value: 'a' }],
      },
    ]
    const schemas = toolParametersToFormSchemas(parameters)
    expect(schemas[0].show_on).toEqual([])
    expect(schemas[0].reset_on_change).toEqual([])
    expect(schemas[0].options?.[0].show_on).toEqual([])
  })
})

describe('flattenToolSettingStoredEntry / getPlainValue', () => {
  it('should normalize nested generateFormValue rows', () => {
    const row = {
      value: { type: VarKindType.constant, value: 'pro' },
    }
    expect(flattenToolSettingStoredEntry(row)).toEqual({
      type: VarKindType.constant,
      value: 'pro',
    })
  })

  it('should pass through flat ResourceVarInputs rows', () => {
    expect(flattenToolSettingStoredEntry({
      type: VarKindType.constant,
      value: 'free',
    })).toEqual({
      type: VarKindType.constant,
      value: 'free',
    })
  })

  it('should coerce legacy primitives to constant inputs', () => {
    expect(flattenToolSettingStoredEntry('pro')).toEqual({
      type: VarKindType.constant,
      value: 'pro',
    })
    expect(flattenToolSettingStoredEntry(true)).toEqual({
      type: VarKindType.constant,
      value: true,
    })
  })

  it('should map getPlainValue over mixed stored shapes', () => {
    const plain = getPlainValue({
      mode: { value: { type: VarKindType.constant, value: 'pro' } },
      legacy: 'free' as unknown as { value: unknown },
    } as Record<string, { value: unknown }>)
    expect(plain.mode).toEqual({ type: VarKindType.constant, value: 'pro' })
    expect(plain.legacy).toEqual({ type: VarKindType.constant, value: 'free' })
  })
})

describe('serializeResourceVarInputsForDynamicOptions', () => {
  it('should omit the current dynamic field and undefined reset values from parameter_values', () => {
    const serialized = serializeResourceVarInputsForDynamicOptions({
      category: { type: VarKindType.constant, value: 'docs' },
      channel: { type: VarKindType.constant, value: 'old-channel' },
      reset_field: { type: VarKindType.constant, value: undefined },
    }, 'channel')

    expect(serialized).toEqual({
      category: 'docs',
    })
  })
})

describe('getDynamicOptionsResetKey', () => {
  it('should change only when reset_on_change dependency values change', () => {
    const first = getDynamicOptionsResetKey({
      category: { type: VarKindType.constant, value: 'docs' },
      channel: { type: VarKindType.constant, value: 'old-channel' },
    }, ['category'])
    const sameDependency = getDynamicOptionsResetKey({
      category: { type: VarKindType.constant, value: 'docs' },
      channel: { type: VarKindType.constant, value: 'new-channel' },
    }, ['category'])
    const changedDependency = getDynamicOptionsResetKey({
      category: { type: VarKindType.constant, value: 'chat' },
      channel: { type: VarKindType.constant, value: 'new-channel' },
    }, ['category'])

    expect(sameDependency).toBe(first)
    expect(changedDependency).not.toBe(first)
  })
})
