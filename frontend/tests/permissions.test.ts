import { describe, expect, it } from "vitest";
import { offeredTransitions } from "../src/lib/permissions";

describe("transitions offered per role (SRS §17.2, §22.2)", () => {
  it("offers investigators every legal transition", () => {
    expect(offeredTransitions("INVESTIGATOR", "IN_REVIEW", false)).toEqual(["ESCALATED", "RESOLVED", "FALSE_POSITIVE"]);
    expect(offeredTransitions("ADMIN", "RESOLVED", false)).toEqual(["CLOSED"]);
    expect(offeredTransitions("INVESTIGATOR", "CLOSED", true)).toEqual([]);
  });
  it("never offers analysts resolution, and nothing to non-participants", () => {
    expect(offeredTransitions("ANALYST", "IN_REVIEW", true)).toEqual(["ESCALATED"]);
    expect(offeredTransitions("ANALYST", "OPEN", true)).toEqual(["IN_REVIEW"]);
    expect(offeredTransitions("ANALYST", "OPEN", false)).toEqual([]);
    expect(offeredTransitions("ANALYST", "ESCALATED", true)).toEqual([]);
  });
});
