export type DocumentInfo = {
  id: string; filename: string; byte_size: number; chunk_count: number; created_at: string;
};
export type Health = {
  status: string; mode: "demo" | "openai"; embedding_space: string; max_upload_bytes: number;
};
export type Source = {
  id: number; chunk_id: number; document_id: string; filename: string;
  page: number; chunk_index: number; text: string; score: number;
};
export type Answer = {
  answer: string; sources: Source[]; mode: "demo" | "openai"; refused: boolean; elapsed_ms: number;
};

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail: unknown = payload.detail;
    const message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map((item: { msg?: string }) => item.msg).join("; ")
      : "The request failed. Please try again.";
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
