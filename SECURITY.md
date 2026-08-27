# Security Policy

## Reporting a vulnerability

Report security issues privately to **merwanroudane920@gmail.com**. Please do
not open a public issue for a vulnerability.

Include what you can: affected version, reproduction steps, and impact. You can
expect an acknowledgement within seven days.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Scope

SmartPrep reads data that is frequently untrusted, so the following are treated
as security concerns rather than ordinary bugs:

- **Unsafe deserialisation.** Loading a file must never execute code contained
  in it.
- **Path traversal.** File paths supplied in data must never escape the
  intended directory.
- **Report injection.** Cell values are rendered into reports and must be
  escaped. A crafted value must not inject markup or script into generated
  HTML.
- **Sensitive data leakage.** Values classified as sensitive must not appear in
  logs, error messages, exception text or report samples.
- **External transmission.** SmartPrep does not send data anywhere. Any future
  feature that could must be opt-in, off by default, and must not transmit raw
  values without explicit consent.

## Not in scope

- Denial of service from deliberately pathological input sizes.
- Statistical disclosure risk in aggregate outputs, which is a modelling
  concern rather than a software vulnerability.
