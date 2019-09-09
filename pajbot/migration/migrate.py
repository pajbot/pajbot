import importlib
import pkgutil
import re

import logging

from pajbot.migration.revision import Revision

MODULE_NAME_REGEX = re.compile(r"^(\d*)(?:\D(.+))?$")

log = logging.getLogger("pajbot")


class Migration:
    def __init__(self, migratable, revisions_package, context=None):
        self.migratable = migratable
        self.revisions_package = revisions_package
        self.context = context

    def run(self, target_revision_id=None):
        with self.migratable.create_resource() as resource:
            revisions = self.get_revisions()
            current_revision_id = self.migratable.get_current_revision(resource)
            log.debug("migrate: current revision ID is %s", current_revision_id)

            if current_revision_id is not None:
                revisions_to_run = [rev for rev in revisions if rev.id > current_revision_id]
            else:
                revisions_to_run = revisions

            # don't run all revisions, only up to the specified revision_id
            if target_revision_id is not None:
                revisions_to_run = [rev for rev in revisions_to_run if rev.id <= target_revision_id]

            log.debug("migrate: %s revisions to run", len(revisions_to_run))

            for rev in revisions_to_run:
                log.debug("migrate: running migration %s: %s", rev.id, rev.name)
                rev.up_action(resource, self.context)
                self.migratable.set_revision(resource, rev.id)

    def get_revisions(self):
        package = self.revisions_package

        if isinstance(package, str):
            package = importlib.import_module(package)

        revisions = []
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if ispkg:
                continue

            module = importer.find_module(modname).load_module(modname)
            id_in_module = getattr(module, "ID", None)
            name_in_module = getattr(module, "NAME", None)
            up_action = getattr(module, "up", None)

            module_name_match = MODULE_NAME_REGEX.search(modname)

            id = None
            name = None

            if module_name_match is not None:
                id_group = module_name_match.group(1)
                if id_group is not None:
                    id = int(id_group)

                name = module_name_match.group(2)

            if id_in_module is not None:
                id = int(id_in_module)

            if name_in_module is not None:
                name = str(name_in_module)

            if id is None:
                raise ValueError(
                    "Module {} does not specify ID= and ".format(modname)
                    + "its filename does not begin with a number. Cannot proceed."
                )

            if name is None:
                raise ValueError(
                    "Module {} does not specify NAME= and ".format(modname)
                    + "its filename does not specify a name. Cannot proceed."
                )

            if up_action is None:
                raise ValueError("Module {} does not specify `def up()`. Cannot proceed. ".format(modname))

            if any(rev.id == id for rev in revisions):
                raise ValueError("ID {} was defined twice. Cannot proceed.".format(id))

            revision = Revision(id, name, up_action)

            revisions.append(revision)

        if len(revisions) <= 0:
            raise ValueError("No revisions found under {}.".format(package.__path__))

        revisions.sort(key=lambda rev: rev.id)

        return revisions
