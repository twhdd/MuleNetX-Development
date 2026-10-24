/**
 * What the UI offers per role (SRS §22.2). Offering is a convenience; the server enforces every rule
 * and the UI shows its 403/409 answers.
 */
import type { CaseStatus, Role } from "../api/types";

export const TRANSITIONS: Record<CaseStatus, CaseStatus[]> = {
  OPEN: ["IN_REVIEW"],
  IN_REVIEW: ["ESCALATED", "RESOLVED", "FALSE_POSITIVE"],
  ESCALATED: ["IN_REVIEW", "RESOLVED", "FALSE_POSITIVE"],
  RESOLVED: ["CLOSED"],
  FALSE_POSITIVE: ["CLOSED"],
  CLOSED: [],
};

/** Transitions a role may attempt; for ANALYST, participant-only ones are offered only to participants. */
export function offeredTransitions(role: Role, from: CaseStatus, participant: boolean): CaseStatus[] {
  const all = TRANSITIONS[from];
  if (role !== "ANALYST") return all;
  if (!participant) return [];
  return all.filter((to) => (from === "OPEN" && to === "IN_REVIEW") || (from === "IN_REVIEW" && to === "ESCALATED"));
}

export const can = {
  ingest: (role?: Role) => role === "ADMIN",
  controlPipelines: (role?: Role) => role === "ADMIN",
  readAudit: (role?: Role) => role === "ADMIN",
  manageUsers: (role?: Role) => role === "ADMIN",
  assignCases: (role?: Role) => role === "ADMIN" || role === "INVESTIGATOR",
  editCase: (role: Role | undefined, participant: boolean) => role === "ADMIN" || role === "INVESTIGATOR" || (role === "ANALYST" && participant),
};
