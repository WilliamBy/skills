# `.devenv` format

Use JSON so an agent can read and update the file consistently without depending on a YAML parser. Keep one current record per project. Preserve user decisions when refreshing observations; update stale facts with a verification date and source. Unknown values stay explicit rather than being guessed.

```json
{
  "schema_version": 1,
  "updated_at": null,
  "environment": {
    "kind": "unknown",
    "provider_or_org": null,
    "account_or_project": null,
    "region": null,
    "host": null,
    "cluster_context": null,
    "namespace": null,
    "remote_os": null,
    "shell": null,
    "verified_at": null,
    "verified_from": null
  },
  "access": {
    "route": [],
    "authentication": {
      "method": null,
      "principal": null,
      "credential_store": null,
      "credential_ref": null,
      "expires_at": null
    },
    "host_key_fingerprint": null
  },
  "project": {
    "local_root": null,
    "remote_root": null,
    "repository": null,
    "allowed_targets": []
  },
  "workflow": {
    "build_location": null,
    "test_location": null,
    "image_build_location": null,
    "artifact_route": null,
    "registry": null,
    "service_access": null,
    "file_transfer": null
  },
  "guardrails": {
    "allowed_actions": [],
    "confirmation_required": [],
    "privilege_policy": null,
    "cost_limits": null,
    "data_handling": null,
    "network_egress": null
  },
  "decisions": [],
  "open_questions": [],
  "last_session": {
    "date": null,
    "target": null,
    "result": null,
    "verification": null,
    "cleanup": null
  },
  "security": {
    "gitignore_checked_at": null,
    "gitignore_result": "unknown",
    "user_intent": null
  }
}
```

## Field guidance

- `environment.kind` identifies the actual target class, for example `cloud_vm`, `kubernetes`, `bastion`, `managed_ide`, or `other`. `provider_or_org` and `account_or_project` should be sufficient to disambiguate the target without copying a full account inventory.
- `access.route` records the route in order, for example `VPN -> bastion -> SSH host` or `cloud CLI -> SSO role -> cluster context`. `credential_ref` names a keychain/secret-manager entry or SSH-agent identity; it never contains the credential itself. Keep a host fingerprint when SSH is used.
- `project.allowed_targets` scopes the systems, namespaces, or hosts that this project may touch. An empty list means no target has been approved yet; it does not mean every target is allowed.
- `workflow` records where commands, builds, tests, and image builds run, how artifacts move, and how services/files are reached. Include registry names and image references, not registry passwords.
- `guardrails` preserves explicit permissions and boundaries. Record consequential approval once only when its scope is unambiguous; a new target or broader effect requires a new confirmation.
- `decisions` is an array of durable choices with a short `decision`, `scope`, `date`, and optionally `reason`. Keep the latest applicable choice clear and mark superseded entries as such rather than silently erasing context.
- `open_questions` contains unresolved facts, their impact, and whether they block the current operation. Remove or resolve entries when answered.
- `last_session` is a compact checkpoint, not a command transcript. Record outcomes and verification, never raw logs or secret-bearing commands.
- `security.gitignore_result` may be `ignored`, `not_ignored`, `no_git_repo`, or `unknown`. `user_intent` records an explicit decision if the project cannot use `.gitignore` or the user chooses another safe handling.

The sample values above are placeholders. Replace them with observed or user-provided facts; do not copy them as if they described a real environment. Never add secret values, secret-bearing URLs, private keys, tokens, passwords, or kubeconfig contents to this file.
