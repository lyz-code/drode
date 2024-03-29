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

# Installing

To install `drode`, simply:

```bash
pip install drode
```

`drode` configuration is done through the yaml file located at
`~/.local/share/drode/config.yaml`. The [default
template](https://github.com/lyz-code/drode/blob/main/assets/config.yaml) is
provided at installation time.

It is assumed that Drone environmental variables `DRONE_SERVER` and
`DRONE_TOKEN` are configured as well as the AWS CLI credentials. Please refer to
their documentation in case of doubt. To check if everything works as expected
use `drode verify`:

```bash
$: drode verify
  [INFO] Drode: 0.1.0
  [INFO] Drone: OK
  [INFO] AWS: OK
```

# A simple example

Let's see `drode` in action.

Imagine a push in `main` triggers a drone job.

Drone jobs can take from seconds to dozens of minutes. Keeping a constant eye on
the job status introduces several undesired context changes. You can use the
`wait` subcommand to release your mind of that burden. It will periodically
check the job status and rise the terminal bell once it's finished. You can
specify a job number, It monitors the last job by default, but you can specify
any job number.

```bash
$: drode wait
  [INFO] Waiting for job #213 started by a promote event by lyz.
  # (... some time ...)
  [INFO] Job #213 has finished with status success
```

Once the push job has finished successfully, we can promote it to the production
environment.

```bash
$: drode promote
  [INFO] You're about to promote job #213 of the project drode_website to production
  [INFO] With commit 347579b: Add drode promote documentation

Are you sure? [y/n]: y
  [INFO] Job #214 has started.
```

`drode promote` promotes to production the last successful job originated by
a push event in `main`. You are given the information of the job and are
prompted if you want to continue. Only `y` or `yes` will complete the
deployment.

Optionally you can specify which job number to deploy in which environment with
something like `drode promote 210 staging`.

With the `-w` flag, `drode promote` will launch the job and then `wait` for it
to finish.

If you try to promote a failed job, you'll get the following error:

```bash
  [ERROR] You can't promote job #200 to production as it's status is failure
```

`drode` is also able to give insights of the instances related to a project. If
you've configured the `aws` section of the project configuration, it will be
shown after executing the `status` subcommand.

```bash
$: drode status
# Production
Active LaunchConfiguration: production-project_1-238-32gosdkon3hlglkshonbllsdk32023950lskenbl
Instance             IP           Status             Created           LaunchConfiguration
-------------------  -----------  -----------------  ----------------  -----------------------------------
i-gasklk3bnl23880sl  192.71.1.42  Healthy/InService  2020-06-09T04:02  production-project_1-238-32gosdkon3h
i-2osdkgh3nbbbl0sk3  192.83.3.86  Healthy/InService  2020-06-09T04:03  production-project_1-238-32gosdkon3h

# Staging
Active LaunchConfiguration: staging-icijweb-240-237e9e9fb759bab18cc52ad5b7c407e9975831d3
Instance             IP            Status             Created           LaunchConfiguration
-------------------  ------------  -----------------  ----------------  -----------------------------------
i-32okgadslk3jos03l  192.21.2.158  Healthy/InService  2020-06-09T18:50  staging-project_1-238-32gosdkon3h
```

# Multiple projects support

If you have more than one project configured, `drode` needs to know which one to
act upon. Instead of defining it through command flags, we use the `set`
command.

```bash
drode set project_1
```

To check the active project use `drode active`.

# References

As most open sourced programs, `drode` is standing on the shoulders of
giants, namely:

[Pytest](https://docs.pytest.org/en/latest)
: Testing framework, enhanced by the awesome
    [pytest-cases](https://smarie.github.io/python-pytest-cases/) library that made
    the parametrization of the tests a lovely experience.

[Mypy](https://mypy.readthedocs.io/en/stable/)
: Python static type checker.

[Flakeheaven](https://github.com/flakeheaven/flakeheaven)
: Python linter with [lots of
    checks](https://lyz-code.github.io/blue-book/devops/flakeheaven#plugins).

[Black](https://black.readthedocs.io/en/stable/)
: Python formatter to keep a nice style without effort.

[Autoimport](https://lyz-code.github.io/autoimport)
: Python formatter to automatically fix wrong import statements.

[isort](https://github.com/timothycrosley/isort)
: Python formatter to order the import statements.

[PDM](https://pdm.fming.dev/)
: Command line tool to manage the dependencies.

[Mkdocs](https://www.mkdocs.org/)
: To build this documentation site, with the
[Material theme](https://squidfunk.github.io/mkdocs-material).

[Safety](https://github.com/pyupio/safety)
: To check the installed dependencies for known security vulnerabilities.

[Bandit](https://bandit.readthedocs.io/en/latest/)
: To finds common security issues in Python code.

[Yamlfix](https://github.com/lyz-code/yamlfix)
: YAML fixer.

# Contributing

For guidance on setting up a development environment, and how to make
a contribution to *drode*, see [Contributing to
drode](https://lyz-code.github.io/drode/contributing).

## Donations

<a href="https://liberapay.com/Lyz/donate"><img alt="Donate using
Liberapay" src="https://liberapay.com/assets/widgets/donate.svg"></a>
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

