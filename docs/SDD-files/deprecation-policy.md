# Versioning & Deprecation Policy

Skein maintains two independent version streams:

- **Software version:** semantic versioning (`MAJOR.MINOR.PATCH`).
- **Graph schema version:** independent contract version; breaking schema changes increment MAJOR.

A deprecated CLI command/tool receives a warning for at least one minor release before removal where practical. Schema migrations must provide an explicit migration path. Release notes identify behavior, API, and schema compatibility separately.
