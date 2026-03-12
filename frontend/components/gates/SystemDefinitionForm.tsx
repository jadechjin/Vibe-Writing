"use client"

import { useState, useEffect, useMemo, type CSSProperties, type ChangeEvent } from "react"

import type { SystemDetail } from "../../hooks/useProjects"
import type { SystemUpdateInput } from "../../hooks/useSystem"
import type { Blocker } from "../../hooks/useProjectStatus"

// ---- Props ----

export type SystemDefinitionFormProps = Readonly<{
  initialData: SystemDetail | null
  blockers: Blocker[]
  onSave: (data: SystemUpdateInput) => void
  isReadOnly: boolean
  isUpdating?: boolean
}>

// ---- Field config ----

type FieldKey =
  | "researchGoal"
  | "samplesSubjects"
  | "variablesControls"
  | "outputMetrics"
  | "methodsSummary"
  | "systemCardJson"

type FieldConfig = {
  key: FieldKey
  label: string
  placeholder: string
  rows: number
}

const FIELD_CONFIGS: FieldConfig[] = [
  {
    key: "researchGoal",
    label: "研究目标",
    placeholder: "描述该体系的研究目标...",
    rows: 3,
  },
  {
    key: "samplesSubjects",
    label: "样本 / 受试对象",
    placeholder: "描述使用的样本或受试对象...",
    rows: 3,
  },
  {
    key: "variablesControls",
    label: "变量与对照",
    placeholder: "描述实验变量与对照设置...",
    rows: 3,
  },
  {
    key: "outputMetrics",
    label: "产出指标",
    placeholder: "描述预期产出指标...",
    rows: 3,
  },
  {
    key: "methodsSummary",
    label: "方法概述",
    placeholder: "概述实验方法...",
    rows: 4,
  },
  {
    key: "systemCardJson",
    label: "体系卡片 (JSON)",
    placeholder: '{\n  "key": "value"\n}',
    rows: 6,
  },
]

const TEXT_FIELDS: FieldKey[] = [
  "researchGoal",
  "samplesSubjects",
  "variablesControls",
  "outputMetrics",
  "methodsSummary",
]

// ---- Helpers ----

function extractMissingFields(blockers: Blocker[]): string[] {
  if (blockers.length === 0) return []

  const details = blockers[0]?.details
  if (!details) return []

  const raw =
    (details.missing_fields as string[] | undefined) ??
    (details.missingFields as string[] | undefined)

  return Array.isArray(raw) ? raw : []
}

function initFormValues(data: SystemDetail | null): Record<FieldKey, string> {
  return {
    researchGoal: data?.researchGoal ?? "",
    samplesSubjects: data?.samplesSubjects ?? "",
    variablesControls: data?.variablesControls ?? "",
    outputMetrics: data?.outputMetrics ?? "",
    methodsSummary: data?.methodsSummary ?? "",
    systemCardJson: data?.systemCardJson
      ? JSON.stringify(data.systemCardJson, null, 2)
      : "",
  }
}

function isValidJson(value: string): boolean {
  if (value.trim() === "") return false
  try {
    JSON.parse(value)
    return true
  } catch {
    return false
  }
}

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
}

const headerStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#f8fafc",
}

const fieldGroupStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
}

const labelBaseStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#cbd5e1",
}

const labelMissingStyle: CSSProperties = {
  ...labelBaseStyle,
  color: "#f87171",
}

const textareaBaseStyle: CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "rgba(15, 23, 42, 0.6)",
  color: "#e2e8f0",
  fontSize: "14px",
  lineHeight: 1.6,
  fontFamily: "inherit",
  resize: "vertical",
  outline: "none",
  transition: "border-color 0.15s ease",
}

const textareaMissingStyle: CSSProperties = {
  ...textareaBaseStyle,
  borderColor: "rgba(239, 68, 68, 0.6)",
  boxShadow: "0 0 0 1px rgba(239, 68, 68, 0.25)",
}

const textareaDisabledExtra: CSSProperties = {
  opacity: 0.55,
  cursor: "not-allowed",
}

const missingHintStyle: CSSProperties = {
  fontSize: "12px",
  color: "#f87171",
  marginTop: "2px",
}

const errorTextStyle: CSSProperties = {
  fontSize: "12px",
  color: "#fbbf24",
  marginTop: "2px",
}

const buttonContainerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  paddingTop: "8px",
}

const buttonBaseStyle: CSSProperties = {
  padding: "10px 24px",
  borderRadius: "12px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.2)",
  fontSize: "14px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
  transition: "background 0.15s ease, opacity 0.15s ease",
}

const buttonDisabledStyle: CSSProperties = {
  ...buttonBaseStyle,
  opacity: 0.4,
  cursor: "not-allowed",
}

// ---- Component ----

export function SystemDefinitionForm({
  initialData,
  blockers,
  onSave,
  isReadOnly,
  isUpdating = false,
}: SystemDefinitionFormProps) {
  const [values, setValues] = useState<Record<FieldKey, string>>(() =>
    initFormValues(initialData),
  )
  const [jsonError, setJsonError] = useState<string | null>(null)

  // Re-initialize when initialData changes
  useEffect(() => {
    setValues(initFormValues(initialData))
  }, [initialData])

  const missingFields = useMemo(() => extractMissingFields(blockers), [blockers])

  const isMissing = (key: FieldKey): boolean => missingFields.includes(key)

  // Validation
  const textFieldsValid = TEXT_FIELDS.every((key) => values[key].trim().length > 0)
  const jsonFieldValid = isValidJson(values.systemCardJson)
  const canSubmit = textFieldsValid && jsonFieldValid && !isReadOnly && !isUpdating

  function handleChange(key: FieldKey) {
    return (e: ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value
      setValues((prev) => ({ ...prev, [key]: newValue }))

      if (key === "systemCardJson") {
        if (newValue.trim() === "") {
          setJsonError(null)
        } else {
          try {
            JSON.parse(newValue)
            setJsonError(null)
          } catch (err) {
            setJsonError(
              err instanceof Error ? err.message : "无效 JSON",
            )
          }
        }
      }
    }
  }

  function handleSave() {
    if (!canSubmit) return

    const payload: SystemUpdateInput = {
      researchGoal: values.researchGoal || null,
      samplesSubjects: values.samplesSubjects || null,
      variablesControls: values.variablesControls || null,
      outputMetrics: values.outputMetrics || null,
      methodsSummary: values.methodsSummary || null,
      systemCardJson: JSON.parse(values.systemCardJson) as Record<string, unknown>,
    }

    onSave(payload)
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>体系定义</div>

      {FIELD_CONFIGS.map((field) => {
        const missing = isMissing(field.key)
        const isJson = field.key === "systemCardJson"

        return (
          <div key={field.key} style={fieldGroupStyle}>
            <label style={missing ? labelMissingStyle : labelBaseStyle}>
              {field.label}
              {missing ? " *" : ""}
            </label>

            <textarea
              value={values[field.key]}
              onChange={handleChange(field.key)}
              placeholder={field.placeholder}
              rows={field.rows}
              disabled={isReadOnly}
              style={{
                ...(missing ? textareaMissingStyle : textareaBaseStyle),
                ...(isReadOnly ? textareaDisabledExtra : {}),
                ...(isJson ? { fontFamily: "monospace" } : {}),
              }}
            />

            {missing ? (
              <div style={missingHintStyle}>此字段为门禁通过的必填项。</div>
            ) : null}

            {isJson && jsonError ? (
              <div style={errorTextStyle}>JSON 错误：{jsonError}</div>
            ) : null}
          </div>
        )
      })}

      {!isReadOnly ? (
        <div style={buttonContainerStyle}>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSubmit}
            style={canSubmit ? buttonBaseStyle : buttonDisabledStyle}
          >
            {isUpdating ? "保存中..." : "保存定义"}
          </button>
        </div>
      ) : null}
    </div>
  )
}
