# Contributing to Infinitude Direct

Thank you for your interest in contributing! This project is in **pre-alpha**, so there's plenty to help with.

## Getting Started

1. Fork the repository and clone it locally.
2. Create a branch for your change: `git checkout -b my-feature`
3. Make your changes and test them.
4. Commit with a clear message and open a pull request.

## Development Setup

### Integration (`custom_components/infinitude_direct`)

- Requires a running Home Assistant instance (dev container or core).
- The integration communicates with an Infinitude proxy — you'll need one running locally or on your network.

### Add-on (`infinitude/`)

- Built on the `nebulous/infinitude` Docker image.
- Test locally with `docker build -t infinitude-direct ./infinitude`.

## Reporting Bugs

- Use the [issue tracker](https://github.com/vbulkin/infinitude-modern-wrap/issues).
- Include your HA version, integration version, and relevant logs.

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR.
- Follow existing code style.
- Update the README if your change affects user-facing behavior.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
