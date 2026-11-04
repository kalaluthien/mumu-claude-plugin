export type BoardIssue = {
  number: number; title: string; url: string
  holder: string; wait: string; progress: string; goal: string; detail: string[]; done: { met: boolean | null; kind: string; name: string; detail: string }[]; next: string; tasks: BoardIssue[]
  guide: string; pad: string; home: number | null; ancestors: number[]; lines: { title: string[]; status: string[]; notes: string[] }
  blockers: { number: number; closed: boolean }[]; closed: { number: number; title: string; url: string; stopped: boolean; blockers: { number: number; closed: boolean }[] }[]; earlier: boolean
}

declare module 'claude-code' {
  interface PluginState {
    teamwork: { board: BoardIssue[]; expanded: number[]; failure: string; loaded: boolean }
  }
}
