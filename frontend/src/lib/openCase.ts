import { caseService } from "../api/cases";
import type { Priority } from "../api/types";

const PRIORITY_BY_TIER: Record<string, Priority> = { CRITICAL: "CRITICAL", HIGH: "HIGH", MEDIUM: "MEDIUM", LOW: "LOW" };

/** Open a case with one account as its first subject. Two API calls; the server audits both. */
export async function openCaseForAccount(accountId: string, label: string, tier: string | null | undefined): Promise<string> {
  const created = await caseService.create({ title: `Review account ${label}`, priority: PRIORITY_BY_TIER[tier ?? ""] ?? "MEDIUM" });
  await caseService.addSubject(created.case_id, "ACCOUNT", accountId);
  return created.case_id;
}
