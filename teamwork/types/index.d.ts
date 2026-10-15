export type BoardIssue = {
  number: number; title: string; url: string; kind: 'backlog' | 'task'
  holder: string; wait: string; progress: string; goal: string; done: string[]; next: string; tasks: BoardIssue[]
  blockers: { number: number; closed: boolean }[]; closed: { number: number; title: string; url: string; blockers: { number: number; closed: boolean }[] }[]; earlier: boolean
}

declare module 'claude-code' {
  interface PluginState {
    teamwork: { board: BoardIssue[]; expanded: number[] }
  }
}
