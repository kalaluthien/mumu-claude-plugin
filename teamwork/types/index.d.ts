export type BoardIssue = {
  number: number; title: string; url: string; kind: 'backlog' | 'task'
  holder: string; wait: string; progress: string; goal: string; done: string[]; tasks: BoardIssue[]
  after: number[]; closed: { number: number; title: string; url: string; after: number[] }[]
}

declare module 'claude-code' {
  interface PluginState {
    teamwork: { board: BoardIssue[]; expanded: number[] }
  }
}
