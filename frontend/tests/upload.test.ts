// @vitest-environment node
// Node's own FormData/File (jsdom's FormData is not serialisable by Node's fetch)
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { pipelineService } from "../src/api/pipeline";
import { beforeEach } from "vitest";
import { server } from "./server";

// relative URLs need an origin outside the browser
beforeEach(() => {
  const inner = globalThis.fetch;
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    inner(typeof input === "string" && input.startsWith("/") ? `http://localhost${input}` : input, init);
  return () => {
    globalThis.fetch = inner;
  };
});

describe("pipeline upload", () => {
  it("always sends the CSV part as text/csv, whatever the browser labelled it", async () => {
    let partType = "";
    server.use(
      http.post("http://localhost/api/v1/ingestion", async ({ request }) => {
        const file = (await request.formData()).get("file") as File;
        partType = file.type;
        return HttpResponse.json({ dataset_id: "d", dataset_key: "k", ingestion_run_id: "i", pipeline_run_id: "p", status: "CREATED" }, { status: 202 });
      }),
    );
    const excel = new File(["step,type\n"], "paysim.csv", { type: "application/vnd.ms-excel" });
    await pipelineService.upload({ file: excel, name: "n", dataset_version: "v1", source: "paysim", schema_version: "paysim-1", adapter: "paysim-v1" });
    expect(partType).toBe("text/csv");
  });
});
