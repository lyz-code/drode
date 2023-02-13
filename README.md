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

## Donations

<noscript><a href="https://liberapay.com/Lyz/donate"><img alt="Donate using
Liberapay" src="https://liberapay.com/assets/widgets/donate.svg"></a></noscript>
or
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/T6T3GP0V8)

If you are using some of my open-source tools, have enjoyed them, and want to
say "thanks", this is a very strong way to do it.

If your product/company depends on these tools, you can sponsor me to ensure I
keep happily maintaining them.

If these tools are helping you save money, time, effort, or frustrations; or
they are helping you make money, be more productive, efficient, secure, enjoy a
bit more your work, or get your product ready faster, this is a great way to
show your appreciation. Thanks for that!

And by sponsoring me, you are helping make these tools, that already help you,
sustainable and healthy.

## License

GPLv3
