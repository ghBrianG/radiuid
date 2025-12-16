# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| < 3.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in RadiUID, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email **security@blbcgroup.com** with details of the vulnerability
3. Include steps to reproduce the issue if possible

You can expect:
- Acknowledgment within 48 hours
- Status updates as the issue is investigated
- Credit in the release notes (unless you prefer anonymity)

## Security Considerations

RadiUID handles sensitive data and credentials. When deploying:

- **Firewall API Keys**: Store securely in the configuration file with restricted permissions (`chmod 600 /etc/radiuid/radiuid.yaml`)
- **RADIUS Shared Secrets**: Protect the FreeRADIUS clients configuration file
- **TLS Configuration**: Use TLS 1.2 (default) for firewall API communication; avoid TLS 1.0/1.1 unless required for legacy devices
- **Log Files**: RADIUS logs may contain usernames and IP addresses; secure accordingly
- **Service Account**: Run the RadiUID service with minimal required privileges
