<!-- original, deliberately weak -->
# tiny-queue

![build](https://img.shields.io/badge/build-passing-green)

## Install

1. Run `tq init` in your project dir, this creates `tq.db` and the jobs table.
2. `git clone https://github.com/example/tiny-queue && cd tiny-queue`
3. `pip install -e .`
4. Make sure the lease timeout is set (see below) or dead jobs will pile up.

That's it, you should be good to go.

## Usage

Push a job:

```
tq push "python scripts/resize.py --img 42"
```

Then run a worker:

```
tq work
```

The worker grabs the next pending job, takes a lease on it and runs it as a shell command. If it exits non-zero the job is marked failed and goes back in the queue. Failed jobs get retried up to 5 times before they are moved to dead.

You can run as many `tq work` processes as you want, they won't step on each other (mostly).

## Config

Config is read from `tq.toml` in the current dir or from env vars, env wins. `TQ_DB` sets the path to the db file, default is `./tq.db`. `TQ_LEASE` is the lease timeout in seconds, default 300, a lease is how long a worker owns a job before another worker is allowed to take it over, so if your jobs take longer than 5 minutes you need to bump this or two workers will end up running the same job which is probably not what you want unless your jobs are idempotent which they should be anyway. `TQ_POLL` is how often an idle worker checks for new jobs, default 1s, setting it lower will hammer the db. `TQ_MAX_ATTEMPTS` is 3 and a job that has failed 3 times is dead and won't be picked up again, dead jobs stay in the table so you can look at them with `tq list --dead` or just open the db in sqlite3 and query it, the schema is pretty obvious. There's also `TQ_LOG` which can be `debug`, `info` or `warn`, default is `info`, debug prints every SQL statement so it's noisy. Workers handle SIGTERM by finishing the current job and then exiting, SIGKILL obviously doesn't let them do that so the job will sit there until its lease runs out and then get picked up again by someone else. Output of jobs goes to stdout of the worker, if you want it somewhere else redirect it.

## Resetting

If things get stuck you can run

```
tq work --reset
```

This does the right thing with stuck and dead jobs before starting the worker. For the exact behavior see the code in `tq/worker.py`, it's short.

Be careful running it while other workers are up.

## Other commands

- `tq list` - show jobs (`--dead`, `--failed`, `--pending`)
- `tq drop <id>` - delete a job
- `tq stats` - counts per state

## Known issues

- Windows not tested
- Sometimes `database is locked` under heavy load, just retry
- Jobs with quotes in them can be weird, escape them

## Contributing

PRs welcome. Run `pytest` before sending one. Please keep it tiny, that's the point.

## License

MIT
