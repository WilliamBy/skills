---
name: remote-dev
description: Use this skill whenever work needs a remote development environment: connecting to a cloud VM or company cluster, running commands remotely, moving files or build artifacts, inspecting files from a remote host, or reaching a service deployed there. Also use it when the user explicitly asks for remote-dev setup. Read and maintain the project-local `.devenv` so the environment, approved access method, credential references, build and transfer choices, and safety constraints are gathered once and reused on later calls.
---

# Remote development environment

Treat the remote environment as unknown until its type, target, route, identity, and permitted actions are established. Use `.devenv` as the project-local source of truth for durable environment facts and user decisions. Complete the requested task through the narrowest authorized route, and report what was actually verified.

## Start here on every invocation

1. Locate the project root and `.devenv`. Read `.devenv` before choosing a host, cluster, account, namespace, build location, transfer route, or service endpoint. Follow the schema in [references/devenv-format.md](references/devenv-format.md).
2. Check whether `.devenv` is ignored by the repository's active ignore rules (`git check-ignore`). If it is not ignored, add the exact `.devenv` entry to the project's `.gitignore` when that file is writable; preserve its existing contents and verify the rule. If no ignore mechanism is available or the ignore file cannot be changed, explain the exposure and ask the user to add an ignore rule or choose a safe local config path. Until the file is protected from Git, do not write environment details or credentials references to it. After protection, record the user's choice in `.devenv` so it is not asked again. Never put a secret value in `.devenv`.
3. Compare the requested operation with the recorded environment, credential references, project mapping, workflow decisions, and guardrails. Reuse complete, current information. Ask only for missing or expired information needed for this task; record the answer or a durable preference in `.devenv` so it is not asked again.
4. Treat a changed account, endpoint, cluster context, host key, repository, permission level, or security boundary as drift. Verify it with the user or an authoritative local configuration before proceeding, then update the record.
5. If `.devenv` is absent or lacks the required facts, run the first-use setup below. Do not guess the provider or company infrastructure from names, DNS suffixes, or prior unrelated projects.

## First-use setup

Gather only facts needed to connect and do the requested work. Ask in one compact set of questions where possible:

- Environment kind: cloud VM/ECS, Kubernetes or another development cluster, bastion/jump host, managed cloud IDE, or another system.
- Target and route: provider/account or organization, region, host or cluster API/context, VPN/bastion requirements, and the approved project/repository location. Avoid requesting broad account inventories.
- Authentication: which supported mechanism is available and which local credential-store reference to use. Prefer SSO or short-lived role credentials, the cloud provider CLI, an SSH agent/key, or an approved secret manager over a reusable password. Do not ask the user to paste a password, token, private key, or kubeconfig into chat.
- Project and workflow: local and remote repository paths; where builds and tests should run; required runtime/toolchain; how artifacts reach the environment (for example, a registry reachable by both sides, approved file transfer, or an existing artifact store); and how services should be accessed.
- Authority and limits: read-only versus permitted writes, allowed namespaces/hosts, privilege escalation policy, cost/resource limits, data-handling restrictions, and actions that require a fresh confirmation.

If the user has already supplied a secret in chat, do not copy it to files, commands, output, or logs. Treat it as exposed, recommend revoking or rotating it, and switch to a secret-store reference or a protected local prompt. Never request a secret through ordinary chat when a secure credential mechanism is available.

Create `.devenv` only after recording the gathered non-secret facts and credential references. Do not invent unanswered values. Mark them `unknown` or `needs_user_input` and ask only when a missing value blocks the requested operation. Record decisions and their scope, such as “build images locally; push to registry X; deploy from cluster context Y,” instead of asking the same workflow question on the next call.

## Credentials and local secrets

- Keep `.devenv` free of passwords, access tokens, private key material, client secrets, kubeconfig contents, cloud credentials, and connection strings containing credentials.
- Store secrets in the operating system credential store, SSH agent, cloud CLI login, or the organization's approved secret manager. Put only a stable lookup reference and authentication method in `.devenv`.
- Use existing credential helpers and short-lived identity wherever possible. Retrieve a secret only immediately before the authorized operation, pass it through a protected input channel or standard credential helper, and clear temporary material promptly. Do not place secrets in command-line arguments, shell history, process listings, source files, container build arguments/layers, screenshots, or diagnostic output.
- Do not implement home-grown encryption or store an encryption key beside ciphertext. If the user explicitly requires an encrypted secret file, use an established tool such as age with its decryption identity held separately in an approved OS secret store; document the recovery and rotation path in `.devenv`. Do not proceed with a design where loss of the key makes the environment unrecoverable or where the key is committed with the ciphertext.
- Keep machine-specific credentials out of Git. Recheck ignore rules whenever the credential/config file names change, and inspect `git status` before finishing. Do not stage or commit `.devenv`, encrypted secrets, temporary credentials, or generated kubeconfigs.
- If a credential reference is missing, expired, or rejected, report the reference and the authentication step that failed without printing the secret. Ask the user to refresh it through the secure store; do not silently fall back to another identity.

## Connect and work

1. **Resolve the target.** Confirm the recorded host/account or cluster context, project, namespace, and identity. For SSH, verify host-key fingerprints through a trusted channel; do not disable host-key checking to bypass a mismatch. For Kubernetes, inspect the active context and namespace before any command that can change resources.
2. **Establish a baseline.** Use bounded read-only commands first to verify identity, OS/tool versions, repository revision and working tree, current namespace, resource/service status, and relevant limits. Distinguish local output from remote output. Stop if the observed target differs from `.devenv` or the user's request.
3. **Choose execution location.** Apply the saved build/test policy. If no policy exists and both locations are viable, ask once where builds, tests, and image builds belong; record the answer. Confirm constraints such as source access, architecture, network access, data locality, and local versus remote resource cost.
4. **Move files and artifacts deliberately.** Follow the saved direction, destination, registry, and transfer mechanism. Verify the destination and artifact digest or version after transfer. Avoid copying secrets or unrelated user data. For images, prefer a registry reachable by both the build side and target environment; use scoped, short-lived registry credentials and verify the image reference/digest before deployment.
5. **Reach remote services privately.** Use the saved access path, such as an authenticated endpoint, VPN, SSH tunnel, or Kubernetes port-forward. Keep services private unless public exposure is explicitly requested and authorized. Verify the endpoint identity and report the exact URL/port and access scope without leaking tokens.
6. **Make changes within scope.** Perform the requested operation and verify its concrete result. Before destructive, externally visible, costly, or broad changes (including provisioning, deletion, restart/rollout, scaling, production writes, IAM/firewall changes, or changing shared cluster state), show the target and effect and obtain fresh user confirmation unless that exact action and scope were already explicitly authorized. Never infer production permission from a development credential.
7. **Collect remote files safely.** Confirm the source path and local destination from `.devenv` or the user. Retrieve only the requested files, preserve useful metadata where appropriate, and scan/redact secrets before displaying, archiving, or attaching output.
8. **Close the loop.** Verify the operation from the relevant host, cluster, or service. Remove temporary tunnels, port-forwards, copied credentials, and scratch files created for the task. Record durable new decisions, changed paths, environment drift, credential-reference changes, and verification status in `.devenv`. Do not store a transcript or secret-bearing command output there.

## Completion report

Report the target and identity used at a safe level of detail, actions performed, verification evidence, files or artifact references transferred, and any remaining blocker. Distinguish a successful connection from a successful task, a requested deployment from a verified rollout, and a created alert/configuration from confirmed delivery when relevant. Mention any unverified assumption and update `.devenv` with durable facts before finishing.
