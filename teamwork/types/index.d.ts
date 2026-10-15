export type BoardIssue = {
  number: number; title: string; url: string; kind: 'backlog' | 'task'
  goal: string; done: string[]; holder: string; tasks: BoardIssue[]
}

declare module 'claude-code' {
  interface PluginState {
    teamwork: { board: BoardIssue[] }
  }
}
