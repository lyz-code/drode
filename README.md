# Drode

[![Actions Status](https://github.com/lyz-code/drode/workflows/Tests/badge.svg)](https://github.com/lyz-code/drode/actions)
[![Actions Status](https://github.com/lyz-code/drode/workflows/Build/badge.svg)](https://github.com/lyz-code/drode/actions)
[![Coverage Status](https://coveralls.io/repos/github/lyz-code/drode/badge.svg?branch=main)](https://coveralls.io/github/lyz-code/drode?branch=main)

`drode` is a wrapper over the Drone and AWS APIs to make deployments more user
friendly.

It assumes that the projects are configured to continuous deliver all
commits to staging. Then those commits can be promoted to production or to
staging for upgrades and rollbacks.

It has the following features:

* Prevent failed jobs to be promoted to production.
* Promote jobs with less arguments than the drone command line.
* Wait for a drone build to end, then raise the terminal bell.

## Help

See [documentation](https://lyz-code.github.io/drode) for more details.

## Installing

```bash
pip install drode
```

## Contributing

For guidance on setting up a development environment, and how to make
a contribution to *drode*, see [Contributing to
drode](https://lyz-code.github.io/drode/contributing).

## License

GPLv3
