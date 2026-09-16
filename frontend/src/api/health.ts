export type Readiness = {
  status: "ready" | "unavailable";
  redis: "connected" | "unavailable";
  environment: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getReadiness(signal?: AbortSignal): Promise<Readiness> {
  const response = await fetch(`${apiBaseUrl}/health/ready`, { signal });
  if (!response.ok) {
    throw new Error(`API readiness request failed with ${response.status}`);
  }
  return (await response.json()) as Readiness;
}
