Contributing
------------

We're always interested in improvements in byro, and **your** help is welcome! We'll review
your contributions and give feedback on your changes, and help you if you're not sure how to
solve a problem.

You'll need to have a GitHub_ account to contribute to byro, and should know how to pull, push,
and commit using git.

If you have some improvement already in mind, please `open an issue`_ for it. Otherwise, look at
our `open issues`_ and choose one you want to resolve. Don't hesitate to comment on the issue if
anything is unclear.

First off, `fork byro`, and then clone your repository (GitHub will provide instructions).
Once you have cloned your repository and opened it, create a new feature branch including
the issue ID::

    git checkout -b issue/123

If your issue requires code changes, complete the :doc:`development setup </developer/setup>`,
then continue here. If you want to change the documentation, please read up on the
:doc:`documentation setup </developer/documentation>`.

We have a couple of style checkers both for code and for documentation, as documented in the
setup docs. We check them in our Continuous Integration for every commit and pull request,
but you should run the tests and checks locally as well, and consider your pull request
ready once those tests pass.

Please write helpful, well-formatted commit messages – you can find a guide here_. Once you
have committed your work, add yourself to the
``src/byro/office/templates/office/settings/about.html`` file, and push your branch::

  git push -u origin issue/123

and open a pull request. This will cause our Continuous Integration to check your changes for
any issues (breaking tests, code style issues, documentation style issues, …).
Please give us five to seven days to get back to you with a review or a direct merge.


.. _GitHub: https://github.com
.. _open an issue: https://github.com/byro/byro/issues/new
.. _open issues: https://github.com/byro/byro/issues
.. _fork byor: https://github.com/byro/byro/fork
.. _here: https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
