import type { SectionDraftDetail } from "../../hooks/useDrafts"
import type { ClaimDetail, OutlineDetail } from "../../hooks/useEvidence"
import type { SystemDetail } from "../../hooks/useProjects"

type VersionedRecord = {
  version: number
  updatedAt: string
}

export type SystemSectionDetail = SystemDetail["sections"][number]

function getTimestampValue(value: string): number {
  const parsedValue = Date.parse(value)

  return Number.isNaN(parsedValue) ? 0 : parsedValue
}

function isRecordNewer<T extends VersionedRecord>(candidate: T, current: T): boolean {
  if (candidate.version !== current.version) {
    return candidate.version > current.version
  }

  return getTimestampValue(candidate.updatedAt) > getTimestampValue(current.updatedAt)
}

export function selectLatestVersionedRecord<T extends VersionedRecord>(
  records: readonly T[] | null | undefined,
): T | null {
  let latestRecord: T | null = null

  for (const record of records ?? []) {
    if (!latestRecord || isRecordNewer(record, latestRecord)) {
      latestRecord = record
    }
  }

  return latestRecord
}

export function selectLatestVersionedRecordsByKey<T extends VersionedRecord>(
  records: readonly T[] | null | undefined,
  getKey: (record: T) => string,
): Map<string, T> {
  const latestRecordByKey = new Map<string, T>()

  for (const record of records ?? []) {
    const recordKey = getKey(record)
    const currentRecord = latestRecordByKey.get(recordKey)

    if (!currentRecord || isRecordNewer(record, currentRecord)) {
      latestRecordByKey.set(recordKey, record)
    }
  }

  return latestRecordByKey
}

export function getLatestClaims(claims: readonly ClaimDetail[] | null | undefined): ClaimDetail[] {
  return Array.from(selectLatestVersionedRecordsByKey(claims, (claim) => claim.claimId).values()).sort(
    (left, right) => {
      if (left.status === right.status) {
        return left.claimId.localeCompare(right.claimId)
      }

      if (left.status === "approved") {
        return -1
      }

      if (right.status === "approved") {
        return 1
      }

      return left.claimId.localeCompare(right.claimId)
    },
  )
}

export function getLatestOutline(
  outlines: readonly OutlineDetail[] | null | undefined,
): OutlineDetail | null {
  return selectLatestVersionedRecord(outlines)
}

export function getLatestDraftsBySection(
  drafts: readonly SectionDraftDetail[] | null | undefined,
): Map<string, SectionDraftDetail> {
  return selectLatestVersionedRecordsByKey(drafts, (draft) => draft.sectionKey)
}

export function getOrderedSystemSections(
  systemDetail: Pick<SystemDetail, "sections"> | null | undefined,
): SystemSectionDetail[] {
  return [...(systemDetail?.sections ?? [])].sort((left, right) => left.orderNo - right.orderNo)
}
