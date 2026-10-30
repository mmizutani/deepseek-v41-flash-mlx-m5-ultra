# Server process tracking

Background `up` records the child's PID, executable path and start time. `down` checks that identity before sending
signals, including before escalating to SIGKILL. A stale, corrupt or legacy integer-only PID file is not authority
to signal a process. `status` may therefore report no tracked PID while the endpoint remains healthy.

When upgrading from integer-only PID files, an already-running server remains usable, but `down` refuses to stop it
without a verified identity. Stop that existing instance through its original supervisor or after manually verifying
its process, then start it with the updated `up` command. Do not delete tracking for an unidentified live process.

If startup fails after the child exits, its tracking is removed. A live child that exceeds the readiness timeout
keeps its record so `down` can still identify and stop it.
