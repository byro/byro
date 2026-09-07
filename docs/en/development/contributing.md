# Contributing

We're always interested in improvements in byro, and **your** help is welcome!
We'll review your contributions and give feedback on your changes, and help you
if you're not sure how to solve a problem.

You'll need to have a [GitHub](https://github.com) account to contribute to
byro, and should know how to pull, push, and commit using git.

If you have some improvement already in mind, please
[open an issue](https://github.com/byro/byro/issues/new) for it. Otherwise,
look at our [open issues](https://github.com/byro/byro/issues) and choose one
you want to resolve. Don't hesitate to comment on the issue if anything is
unclear.

First off, [fork byro](https://github.com/byro/byro/fork), and then clone your
repository (GitHub will provide instructions). Once you have cloned your
repository and opened it, create a new feature branch including the issue ID:

```console
$ git checkout -b issue/123
```

If your issue requires code changes, complete the
[development setup](setup.md), then continue here. If you want to change the
documentation, please read up on [Working on the documentation](documentation.md).

We have a couple of style checkers both for code and for documentation, as
documented in the setup docs. We check them in our Continuous Integration for
every commit and pull request, but you should run the tests and checks locally
as well, and consider your pull request ready once those tests pass.

Please write helpful, well-formatted commit messages – you can find a guide
[here](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).
Once you have committed your work, add yourself to the
`src/byro/office/templates/office/settings/about.html` file, and push your
branch:

```console
$ git push -u origin issue/123
```

and open a pull request. This will cause our Continuous Integration to check
your changes for any issues (breaking tests, code style issues, documentation
style issues, …). Please give us five to seven days to get back to you with a
review or a direct merge.

## Documentation

If your pull request changes visible behavior (a new setting, a new workflow,
a changed command), a matching documentation change belongs in the same pull
request, not a later one. New or changed documentation content is written in
German first (the leading language) and carried over into English in the
same pull request; `docs/check_parity.py` fails CI if a page exists in only
one language. The full editorial standard (terminology, tone, links,
license) is described in
[Working on the documentation](documentation.md).

## New plugins

This workflow is for changes **to byro itself**. A new plugin is not
submitted as a pull request against this repository, but published as its
own Python package with its own release (see
[Creating a plugin](plugins/creating-a-plugin.md)). If you want your plugin
listed in the catalog `byroctl plugin add` knows about,
[Plugin catalog](releasing.md#plugin-catalog) describes how.

## Licensing of contributions

byro is licensed under the GNU Affero General Public License, version 3.0 only
(`AGPL-3.0-only`). The documentation in the `docs/` directory is licensed
under the Creative Commons Attribution-ShareAlike 4.0 International License
(`CC-BY-SA-4.0`). The [LICENSE](https://github.com/byro/byro/blob/main/LICENSE)
file explains the details, including the licensing history of older,
Apache-2.0 licensed versions and the licenses of bundled third-party
components.

Unless explicitly stated otherwise, contributions submitted for inclusion in
byro are licensed under the AGPL-3.0-only, and contributions to the
documentation in `docs/` are licensed under the CC-BY-SA-4.0. By submitting a
contribution, for example by opening a pull request, you confirm that you have
the necessary rights to submit it under the respective license. If your
contribution includes code, text, images or other material from other
projects, make sure that its license is compatible with the AGPL-3.0-only or
the CC-BY-SA-4.0 respectively, keep the original copyright and license notices
intact, and point this out in your pull request.
