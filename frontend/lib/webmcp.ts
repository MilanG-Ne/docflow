export type Tool = {
  name: string;
  description: string;
  inputSchema: object;
  annotations: { readOnlyHint: boolean; untrustedContentHint: boolean };
  execute: (input: unknown) => unknown;
};
type ModelContext = {
  registerTool: (
    tool: Tool,
    options: { signal: AbortSignal },
  ) => void | Promise<void>;
};
export function registerTools(tools: Tool[]): () => void {
  const context = (document as Document & { modelContext?: ModelContext })
    .modelContext;
  if (!context?.registerTool) return () => {};
  const controller = new AbortController();
  for (const tool of tools) {
    try {
      void Promise.resolve(
        context.registerTool(tool, { signal: controller.signal }),
      ).catch((error) =>
        console.warn('DocFlow tool registration failed', error),
      );
    } catch (error) {
      console.warn('DocFlow tool registration failed', error);
    }
  }
  return () => controller.abort();
}
export function validateId(input: unknown): string {
  if (
    !input ||
    typeof input !== 'object' ||
    Array.isArray(input) ||
    Object.keys(input).length !== 1 ||
    !('proposal_id' in input) ||
    typeof input.proposal_id !== 'string' ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      input.proposal_id,
    )
  )
    throw new Error('Expected an object containing a valid proposal_id UUID');
  return input.proposal_id;
}
