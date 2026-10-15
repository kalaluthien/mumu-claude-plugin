export type BoardIssue = { number: number; title: string; url: string; wait: string; tasks: BoardIssue[] }

declare module 'claude-code' {
  interface PluginState {
    teamwork: { board: BoardIssue[] }
  }
}
