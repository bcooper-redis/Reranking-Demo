import { describe, expect, it, vi } from "vitest";

import { getReadiness } from "../api/health";

describe("runtime health API", () => {
  it("returns readiness data from the API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ready",
          redis: "connected",
          environment: "local",
        }),
        {
          status: 200,
        },
      ),
    );

    await expect(getReadiness()).resolves.toMatchObject({ redis: "connected" });
    fetchMock.mockRestore();
  });
});
