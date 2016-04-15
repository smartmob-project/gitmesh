==============================
gitmesh -- a front-end for Git
==============================

**Disclaimer**: this project is currently only a thought experiment!

This project's goal is to build a distributed support for modern Git workflows.

While Git has been a DVCS from the start, the fork & pull request model is
typical of centralized hosting systems.

In my wildest dream, this project would serve as a proof of concept for the
architecture required to replace GitHub with a distributed implementation where
anybody can self-host their own repositories without losing the ability to use
the now widely appreciated power of pull requests.

The minimal requirements for this system are:

- people can trivially customize their Git workflow using Git server hooks for
  implementing things like:

  - branch update history;
  - repository, branch & tag permissions;
  - deploy on push.

- people can browse a mesh of these servers using a "true" REST API.
