# `.devenv/remote.md` format

Write `.devenv/remote.md` as plain Markdown. One current record per project.
Keep heading names stable so later agents can find sections without guessing,
preserve user decisions when refreshing observations, and replace stale facts
with a new date and source. Mark unknown values explicitly as `unknown` or
`needs_user_input` rather than guessing.

## Template

<!-- markdownlint-disable MD013 -->

```markdown
# Remote development environment

<!-- Maintained by the remote-dev skill. Never put a secret in this file. -->

- Updated: 2026-11-13
- Record status: partial | complete | needs_user_input

## Environment

| Field | Value |
| --- | --- |
| Kind | unknown <!-- cloud_vm / kubernetes / bastion / managed_ide / other --> |
| Provider or org | unknown |
| Account or project | unknown |
| Region | unknown |
| Host | unknown |
| Cluster context | unknown |
| Namespace | unknown |
| Remote OS / shell | unknown / unknown |
| Verified at | unknown |
| Verified from | unknown |

## Access

- Route: unknown <!-- e.g. VPN -> bastion -> SSH host, or cloud CLI -> SSO role -> cluster context -->
- Host key fingerprint (SHA256): unknown
- Ports / tunnel / port-forward policy: unknown

## Authentication

- Method: needs_user_input <!-- password | ssh_key | sso | cloud_cli | secret_manager -->
- Principal (user / service account): unknown
- Credential store: unknown <!-- OS keychain, SSH agent, cloud CLI login, approved secret manager -->
- Credential reference: unknown <!-- key/entry name only, never the secret -->
- Passphrase-protected key: unknown <!-- for ssh_key only -->
- Key rotation owner / cadence: unknown
- Expires at: unknown
- Password handling: none <!-- if method is password: "user enters at protected prompt", or a secret-manager reference -->
- Notes: unknown

## Project

| Field | Value |
| --- | --- |
| Local root | unknown |
| Remote root | unknown |
| Repository | unknown |
| Allowed targets | none yet <!-- hosts, namespaces, clusters, or registries approved for this project --> |

## Workflow

- Build location: unknown
- Test location: unknown
- Image build location: unknown
- Artifact route: unknown
- Registry / image reference: unknown
- Service access: unknown
- File transfer: unknown

## Guardrails

- Allowed actions: unknown
- Confirmation required: unknown
- Privilege policy: unknown
- Cost / resource limits: unknown
- Data handling: unknown
- Network egress: unknown

## Decisions

<!-- Append one bullet per durable choice, newest last. Mark superseded entries instead of deleting them. -->

- 2026-11-13 — Authentication method: `<password|ssh_key>`; scope: `<environment>`; reason: `<why>`.

## Open questions

- [ ] `needs_user_input` — `<missing fact>`; blocks: `<operation or "nothing yet">`.

## Last session

- Date: unknown
- Target: unknown
- Authentication method used: unknown
- Result: unknown
- Verification: unknown
- Cleanup: unknown

## Security

- `.devenv/` ignored by Git: unknown <!-- ignored | not_ignored | no_git_repo -->
- Ignore rule checked at: unknown
- `AGENTS.md` references `.devenv/`: unknown <!-- yes | no | not_writable -->
- User handling decision: unknown <!-- set only if .gitignore cannot be used or another location was chosen -->
```

<!-- markdownlint-enable MD013 -->

## Field guidance

- **Environment.** `Kind` identifies the actual target class: `cloud_vm`,
  `kubernetes`, `bastion`, `managed_ide`, or `other`. `Provider or org` and
  `Account or project` must be enough to disambiguate the target without copying
  an account inventory. `Verified at` / `Verified from` record when and how the
  facts were last confirmed.
- **Access.** `Route` records the hops in order. Keep the SSH host fingerprint.
  Describe tunnel or port-forward rules instead of ad-hoc commands.
- **Authentication.** `Method` is the first-use decision and must be `password`
  or `ssh_key` unless the environment genuinely uses SSO or a cloud CLI
  identity; record whatever the user confirmed, not a guessed default.
  `Credential reference` names a keychain, agent, or secret-manager entry; it
  never contains the credential itself. For `password`, also state how the
  password is supplied at connect time (protected interactive prompt or
  secret-manager reference) and never store the value. Changing method is drift:
  re-confirm before using it.
- **Project.** `Allowed targets` scopes the systems, namespaces, or hosts this
  project may touch. An empty list means no target has been approved yet; it
  does not mean every target is allowed.
- **Workflow.** Record where commands, builds, tests, and image builds run, how
  artifacts move, and how services/files are reached. Include registry names and
  image references, not registry passwords.
- **Guardrails.** Preserve explicit permissions and boundaries. Record a
  consequential approval once only when its scope is unambiguous; a new target
  or broader effect requires a new confirmation.
- **Decisions.** Append durable choices with date, decision, scope, and
  optionally reason. Keep the latest applicable choice clear and mark superseded
  entries rather than silently erasing context.
- **Open questions.** List unresolved facts, their blocking impact, and remove
  them once answered.
- **Last session.** A compact checkpoint, not a command transcript. Record
  outcomes and verification, never raw logs or secret-bearing commands.
- **Security.** `ignored by Git` may be `ignored`, `not_ignored`, or
  `no_git_repo`. `AGENTS.md references .devenv/` records whether the handbook
  link exists. `User handling decision` records an explicit decision if the
  project cannot use `.gitignore` or the user chose another safe handling.

## Updating rules

- Prefer targeted edits: change the affected field or section and bump
  `Updated`. Do not rewrite the whole file when one fact changed.
- Keep the heading names and section order from the template; add new facts as
  bullets or table rows inside the matching section instead of new top-level
  headings.
- Append to `Decisions` and `Last session`; do not accumulate command history.
- Never add passwords, tokens, private keys, kubeconfig contents, or
  secret-bearing URLs. A credential reference is a lookup name, not the secret.
- After any authentication-method or target change, update `Updated`, the
  relevant fields, and `Last session`; add a `Decisions` entry when the user
  made the choice.
- If `.devenv/remote.md` is protected by Git ignore and `AGENTS.md` points at
  it, keep both facts in `Security` so the setup checks are not repeated.
